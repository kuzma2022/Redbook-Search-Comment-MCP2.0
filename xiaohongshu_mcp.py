from typing import Any, List, Dict, Optional
import asyncio
import json
import os
import pandas as pd
from datetime import datetime
from playwright.async_api import async_playwright
from fastmcp import FastMCP

# 初始化 FastMCP 服务器
mcp = FastMCP("xiaohongshu_scraper")

# 全局变量
BROWSER_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "browser_data")
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")

# 确保目录存在
os.makedirs(BROWSER_DATA_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

# 用于存储浏览器上下文，以便在不同方法之间共享
browser_context = None
main_page = None
is_logged_in = False

async def ensure_browser():
    """确保浏览器已启动并登录"""
    global browser_context, main_page, is_logged_in
    
    if browser_context is None:
        # 启动浏览器
        playwright_instance = await async_playwright().start()
        
        # 使用持久化上下文来保存用户状态
        browser_context = await playwright_instance.chromium.launch_persistent_context(
            user_data_dir=BROWSER_DATA_DIR,
            headless=False,  # 非隐藏模式，方便用户登录
            viewport={"width": 1280, "height": 800},
            timeout=60000
        )
        
        # 创建一个新页面
        if browser_context.pages:
            main_page = browser_context.pages[0]
        else:
            main_page = await browser_context.new_page()
        
        # 设置页面级别的超时时间
        main_page.set_default_timeout(60000)
    
    # 检查登录状态
    if not is_logged_in:
        # 访问小红书首页
        await main_page.goto("https://www.xiaohongshu.com", timeout=60000)
        await asyncio.sleep(3)
        
        # 检查是否已登录
        login_elements = await main_page.query_selector_all('text="登录"')
        if login_elements:
            return False  # 需要登录
        else:
            is_logged_in = True
            return True  # 已登录
    
    return True

@mcp.tool()
async def login() -> str:
    """登录小红书账号"""
    global is_logged_in
    
    await ensure_browser()
    
    if is_logged_in:
        return "已登录小红书账号"
    
    # 访问小红书登录页面
    await main_page.goto("https://www.xiaohongshu.com", timeout=60000)
    await asyncio.sleep(3)
    
    # 查找登录按钮并点击
    login_elements = await main_page.query_selector_all('text="登录"')
    if login_elements:
        await login_elements[0].click()
        
        # 提示用户手动登录
        message = "请在打开的浏览器窗口中完成登录操作。登录成功后，系统将自动继续。"
        
        # 等待用户登录成功
        max_wait_time = 180  # 等待3分钟
        wait_interval = 5
        waited_time = 0
        
        while waited_time < max_wait_time:
            # 检查是否已登录成功
            still_login = await main_page.query_selector_all('text="登录"')
            if not still_login:
                is_logged_in = True
                await asyncio.sleep(2)  # 等待页面加载
                return "登录成功！"
            
            # 继续等待
            await asyncio.sleep(wait_interval)
            waited_time += wait_interval
        
        return "登录等待超时。请重试或手动登录后再使用其他功能。"
    else:
        is_logged_in = True
        return "已登录小红书账号"

@mcp.tool()
async def search_notes(keywords: str, limit: int = 5, sort_by_time: bool = False) -> str:
    """根据关键词搜索笔记
    
    Args:
        keywords: 搜索关键词
        limit: 返回结果数量限制
        sort_by_time: 是否按最新时间排序
    """
    login_status = await ensure_browser()
    if not login_status:
        return "请先登录小红书账号"
    
    # 构建搜索URL并访问
    search_url = f"https://www.xiaohongshu.com/search_result?keyword={keywords}"
    try:
        await main_page.goto(search_url, timeout=60000)
        await asyncio.sleep(5)  # 等待页面加载
        
        # 如果需要按时间排序
        if sort_by_time:
            try:
                # 点击排序下拉菜单
                sort_dropdown = await main_page.query_selector('text="综合"')
                if sort_dropdown:
                    await sort_dropdown.click()
                    await asyncio.sleep(1)
                    
                    # 点击"最新"选项
                    newest_option = await main_page.query_selector('text="最新"')
                    if newest_option:
                        await newest_option.click()
                        await asyncio.sleep(3)  # 等待排序结果加载
                    else:
                        print("未找到'最新'排序选项")
                else:
                    print("未找到排序下拉菜单")
            except Exception as e:
                print(f"设置排序顺序时出错: {str(e)}")
        
        # 等待页面完全加载
        await asyncio.sleep(5)
        
        # 打印页面HTML用于调试
        page_html = await main_page.content()
        #print(f"页面HTML片段: {page_html[10000:10500]}...")
        
        # 使用更精确的选择器获取帖子卡片
        #print("尝试获取帖子卡片...")
        post_cards = await main_page.query_selector_all('section.note-item')
        #print(f"找到 {len(post_cards)} 个帖子卡片")
        
        if not post_cards:
            # 尝试备用选择器
            post_cards = await main_page.query_selector_all('div[data-v-a264b01a]')
            #print(f"使用备用选择器找到 {len(post_cards)} 个帖子卡片")
        
        post_links = []
        post_titles = []
        
        for card in post_cards:
            try:
                # 获取链接
                link_element = await card.query_selector('a[href*="/search_result/"]')
                if not link_element:
                    continue
                
                href = await link_element.get_attribute('href')
                if href and '/search_result/' in href:
                    full_url = f"https://www.xiaohongshu.com{href}"
                    post_links.append(full_url)
                    
                    # 尝试获取帖子标题
                    try:
                        # 打印卡片HTML用于调试
                        card_html = await card.inner_html()
                        #print(f"卡片HTML片段: {card_html[:200]}...")
                        
                        # 首先尝试获取卡片内的footer中的标题
                        title_element = await card.query_selector('div.footer a.title span')
                        if title_element:
                            title = await title_element.text_content()
                            #print(f"找到标题(方法1): {title}")
                        else:
                            # 尝试直接获取标题元素
                            title_element = await card.query_selector('a.title span')
                            if title_element:
                                title = await title_element.text_content()
                                #print(f"找到标题(方法2): {title}")
                            else:
                                # 尝试获取任何可能的文本内容
                                text_elements = await card.query_selector_all('span')
                                potential_titles = []
                                for text_el in text_elements:
                                    text = await text_el.text_content()
                                    if text and len(text.strip()) > 5:
                                        potential_titles.append(text.strip())
                                
                                if potential_titles:
                                    # 选择最长的文本作为标题
                                    title = max(potential_titles, key=len)
                                    #print(f"找到可能的标题(方法3): {title}")
                                else:
                                    # 尝试直接获取卡片中的所有文本
                                    all_text = await card.evaluate('el => Array.from(el.querySelectorAll("*")).map(node => node.textContent).filter(text => text && text.trim().length > 5)')
                                    if all_text and len(all_text) > 0:
                                        # 选择最长的文本作为标题
                                        title = max(all_text, key=len)
                                        #print(f"找到可能的标题(方法4): {title}")
                                    else:
                                        title = "未知标题"
                                        #print("无法找到标题，使用默认值'未知标题'")
                        
                        # 如果获取到的标题为空，设为未知标题
                        if not title or title.strip() == "":
                            title = "未知标题"
                            print("获取到的标题为空，使用默认值'未知标题'")
                    except Exception as e:
                        print(f"获取标题时出错: {str(e)}")
                        title = "未知标题"
                    
                    post_titles.append(title)
            except Exception as e:
                print(f"处理帖子卡片时出错: {str(e)}")
        
        # 去重
        unique_posts = []
        seen_urls = set()
        for url, title in zip(post_links, post_titles):
            if url not in seen_urls:
                seen_urls.add(url)
                unique_posts.append({"url": url, "title": title})
        
        # 限制返回数量
        unique_posts = unique_posts[:limit]
        
        # 格式化返回结果
        if unique_posts:
            result = "搜索结果：\n\n"
            if sort_by_time:
                result = "按最新时间排序的搜索结果：\n\n"
            for i, post in enumerate(unique_posts, 1):
                # 将search_result替换为explore
                display_url = post['url'].replace('/search_result/', '/explore/')
                result += f"{i}. {post['title']}\n   链接: {display_url}\n\n"
            
            return result
        else:
            return f"未找到与\"{keywords}\"相关的笔记"
    
    except Exception as e:
        return f"搜索笔记时出错: {str(e)}"

# 在确保浏览器函数之后，添加一个新的辅助函数
async def is_same_page(target_url: str) -> bool:
    """检查当前页面是否已经在目标URL上
    
    Args:
        target_url: 目标URL
        
    Returns:
        bool: 如果当前页面与目标URL匹配返回True，否则返回False
    """
    global main_page
    
    if not main_page:
        return False
    
    try:
        # 获取当前URL
        current_url = main_page.url
        
        # 移除URL中的查询参数和令牌进行比较
        def clean_url(url):
            # 首先提取基本URL（不包含查询参数）
            base_url = url.split('?')[0]
            # 如果是小红书搜索结果或笔记页面，保留关键ID
            if '/search_result/' in url or '/explore/' in url or '/discovery/' in url:
                # 提取ID
                import re
                id_match = re.search(r'/(search_result|explore|discovery)/([a-zA-Z0-9]+)', url)
                if id_match:
                    return f"{base_url}_{id_match.group(2)}"
            return base_url
        
        # 清理URL
        clean_current = clean_url(current_url)
        clean_target = clean_url(target_url)
        
        # 如果清理后的URL相同，则认为是同一页面
        return clean_current == clean_target
    except Exception as e:
        print(f"检查URL时出错: {str(e)}")
        return False

@mcp.tool()
async def get_note_content(url: str) -> str:
    """获取笔记内容
    
    Args:
        url: 笔记 URL
    """
    login_status = await ensure_browser()
    if not login_status:
        return "请先登录小红书账号"
    
    try:
        # 检查是否已经在目标页面
        if not await is_same_page(url):
            # 如果不在目标页面，则访问帖子链接
            # 添加xsec_source=pc_feed参数
            modified_url = url
            if '?' in url:
                modified_url = url
            else:
                modified_url = url
            await main_page.goto(modified_url, timeout=60000)
            await asyncio.sleep(5)  # 等待页面加载
        else:
            # 可能需要刷新页面以确保内容最新
            #await main_page.reload()
            await asyncio.sleep(3)
        
        # 增强滚动操作以确保所有内容加载
        await main_page.evaluate('''
            () => {
                // 先滚动到页面底部
                window.scrollTo(0, document.body.scrollHeight);
                setTimeout(() => { 
                    // 然后滚动到中间
                    window.scrollTo(0, document.body.scrollHeight / 2); 
                }, 1000);
                setTimeout(() => { 
                    // 最后回到顶部
                    window.scrollTo(0, 0); 
                }, 2000);
            }
        ''')
        await asyncio.sleep(3)  # 等待滚动完成和内容加载
        
        # 打印页面结构片段用于分析
        try:
            #print("打印页面结构片段用于分析")
            page_structure = await main_page.evaluate('''
                () => {
                    // 获取笔记内容区域
                    const noteContent = document.querySelector('.note-content');
                    const detailDesc = document.querySelector('#detail-desc');
                    const commentArea = document.querySelector('.comments-container, .comment-list');
                    
                    return {
                        hasNoteContent: !!noteContent,
                        hasDetailDesc: !!detailDesc,
                        hasCommentArea: !!commentArea,
                        noteContentHtml: noteContent ? noteContent.outerHTML.slice(0, 500) : null,
                        detailDescHtml: detailDesc ? detailDesc.outerHTML.slice(0, 500) : null,
                        commentAreaFirstChild: commentArea ? 
                            (commentArea.firstElementChild ? commentArea.firstElementChild.outerHTML.slice(0, 500) : null) : null
                    };
                }
            ''')
            #print(f"页面结构分析: {json.dumps(page_structure, ensure_ascii=False, indent=2)}")
        except Exception as e:
            print(f"打印页面结构时出错: {str(e)}")
        
        # 获取帖子内容
        post_content = {}
        
        # 获取帖子标题 - 方法1：使用id选择器
        try:
            #print("尝试获取标题 - 方法1：使用id选择器")
            title_element = await main_page.query_selector('#detail-title')
            if title_element:
                title = await title_element.text_content()
                post_content["标题"] = title.strip() if title else "未知标题"
                #print(f"方法1获取到标题: {post_content['标题']}")
            else:
                #print("方法1未找到标题元素")
                post_content["标题"] = "未知标题"
        except Exception as e:
            print(f"方法1获取标题出错: {str(e)}")
            post_content["标题"] = "未知标题"
        
        # 获取帖子标题 - 方法2：使用class选择器
        if post_content["标题"] == "未知标题":
            try:
                print("尝试获取标题 - 方法2：使用class选择器")
                title_element = await main_page.query_selector('div.title')
                if title_element:
                    title = await title_element.text_content()
                    post_content["标题"] = title.strip() if title else "未知标题"
                    print(f"方法2获取到标题: {post_content['标题']}")
                else:
                    print("方法2未找到标题元素")
            except Exception as e:
                print(f"方法2获取标题出错: {str(e)}")
        
        # 获取帖子标题 - 方法3：使用JavaScript
        if post_content["标题"] == "未知标题":
            try:
                print("尝试获取标题 - 方法3：使用JavaScript")
                title = await main_page.evaluate('''
                    () => {
                        // 尝试多种可能的标题选择器
                        const selectors = [
                            '#detail-title',
                            'div.title',
                            'h1',
                            'div.note-content div.title'
                        ];
                        
                        for (const selector of selectors) {
                            const el = document.querySelector(selector);
                            if (el && el.textContent.trim()) {
                                return el.textContent.trim();
                            }
                        }
                        return null;
                    }
                ''')
                if title:
                    post_content["标题"] = title
                    print(f"方法3获取到标题: {post_content['标题']}")
                else:
                    print("方法3未找到标题元素")
            except Exception as e:
                print(f"方法3获取标题出错: {str(e)}")
        
        # 获取作者 - 方法1：使用username类选择器
        try:
            #print("尝试获取作者 - 方法1：使用username类选择器")
            author_element = await main_page.query_selector('span.username')
            if author_element:
                author = await author_element.text_content()
                post_content["作者"] = author.strip() if author else "未知作者"
                #print(f"方法1获取到作者: {post_content['作者']}")
            else:
                #print("方法1未找到作者元素")
                post_content["作者"] = "未知作者"
        except Exception as e:
            #print(f"方法1获取作者出错: {str(e)}")
            post_content["作者"] = "未知作者"
        
        # 获取作者 - 方法2：使用链接选择器
        if post_content["作者"] == "未知作者":
            try:
                print("尝试获取作者 - 方法2：使用链接选择器")
                author_element = await main_page.query_selector('a.name')
                if author_element:
                    author = await author_element.text_content()
                    post_content["作者"] = author.strip() if author else "未知作者"
                    print(f"方法2获取到作者: {post_content['作者']}")
                else:
                    print("方法2未找到作者元素")
            except Exception as e:
                print(f"方法2获取作者出错: {str(e)}")
        
        # 获取作者 - 方法3：使用JavaScript
        if post_content["作者"] == "未知作者":
            try:
                print("尝试获取作者 - 方法3：使用JavaScript")
                author = await main_page.evaluate('''
                    () => {
                        // 尝试多种可能的作者选择器
                        const selectors = [
                            'span.username',
                            'a.name',
                            '.author-wrapper .username',
                            '.info .name'
                        ];
                        
                        for (const selector of selectors) {
                            const el = document.querySelector(selector);
                            if (el && el.textContent.trim()) {
                                return el.textContent.trim();
                            }
                        }
                        return null;
                    }
                ''')
                if author:
                    post_content["作者"] = author
                    print(f"方法3获取到作者: {post_content['作者']}")
                else:
                    print("方法3未找到作者元素")
            except Exception as e:
                print(f"方法3获取作者出错: {str(e)}")
        
        # 获取发布时间 - 方法1：使用date类选择器
        try:
            #print("尝试获取发布时间 - 方法1：使用date类选择器")
            time_element = await main_page.query_selector('span.date')
            if time_element:
                time_text = await time_element.text_content()
                post_content["发布时间"] = time_text.strip() if time_text else "未知"
                #print(f"方法1获取到发布时间: {post_content['发布时间']}")
            else:
                print("方法1未找到发布时间元素")
                post_content["发布时间"] = "未知"
        except Exception as e:
            #print(f"方法1获取发布时间出错: {str(e)}")
            post_content["发布时间"] = "未知"
        
        # 获取发布时间 - 方法2：使用正则表达式匹配
        if post_content["发布时间"] == "未知":
            try:
                #print("尝试获取发布时间 - 方法2：使用正则表达式匹配")
                time_selectors = [
                    'text=/编辑于/',
                    'text=/\\d{2}-\\d{2}/',
                    'text=/\\d{4}-\\d{2}-\\d{2}/',
                    'text=/\\d+月\\d+日/',
                    'text=/\\d+天前/',
                    'text=/\\d+小时前/',
                    'text=/今天/',
                    'text=/昨天/'
                ]
                
                for selector in time_selectors:
                    time_element = await main_page.query_selector(selector)
                    if time_element:
                        time_text = await time_element.text_content()
                        post_content["发布时间"] = time_text.strip() if time_text else "未知"
                        print(f"方法2获取到发布时间: {post_content['发布时间']}")
                        break
                    else:
                        print(f"方法2未找到发布时间元素: {selector}")
            except Exception as e:
                print(f"方法2获取发布时间出错: {str(e)}")
        
        # 获取发布时间 - 方法3：使用JavaScript
        if post_content["发布时间"] == "未知":
            try:
                print("尝试获取发布时间 - 方法3：使用JavaScript")
                time_text = await main_page.evaluate('''
                    () => {
                        // 尝试多种可能的时间选择器
                        const selectors = [
                            'span.date',
                            '.bottom-container .date',
                            '.date'
                        ];
                        
                        for (const selector of selectors) {
                            const el = document.querySelector(selector);
                            if (el && el.textContent.trim()) {
                                return el.textContent.trim();
                            }
                        }
                        
                        // 尝试查找包含日期格式的文本
                        const dateRegexes = [
                            /编辑于\s*([\d-]+)/,
                            /(\d{2}-\d{2})/,
                            /(\d{4}-\d{2}-\d{2})/,
                            /(\d+月\d+日)/,
                            /(\d+天前)/,
                            /(\d+小时前)/,
                            /(今天)/,
                            /(昨天)/
                        ];
                        
                        const allText = document.body.textContent;
                        for (const regex of dateRegexes) {
                            const match = allText.match(regex);
                            if (match) {
                                return match[0];
                            }
                        }
                        
                        return null;
                    }
                ''')
                if time_text:
                    post_content["发布时间"] = time_text
                    print(f"方法3获取到发布时间: {post_content['发布时间']}")
                else:
                    print("方法3未找到发布时间元素")
            except Exception as e:
                print(f"方法3获取发布时间出错: {str(e)}")
        
        # 获取帖子正文内容 - 方法1：使用精确的ID和class选择器
        try:
            #print("尝试获取正文内容 - 方法1：使用精确的ID和class选择器")
            
            # 先明确标记评论区域
            await main_page.evaluate('''
                () => {
                    const commentSelectors = [
                        '.comments-container', 
                        '.comment-list',
                        '.feed-comment',
                        'div[data-v-aed4aacc]',  // 根据您提供的评论HTML结构
                        '.content span.note-text'  // 评论中的note-text结构
                    ];
                    
                    for (const selector of commentSelectors) {
                        const elements = document.querySelectorAll(selector);
                        elements.forEach(el => {
                            if (el) {
                                el.setAttribute('data-is-comment', 'true');
                                console.log('标记评论区域:', el.tagName, el.className);
                            }
                        });
                    }
                }
            ''')
            
            # 先尝试获取detail-desc和note-text组合
            content_element = await main_page.query_selector('#detail-desc .note-text')
            if content_element:
                # 检查是否在评论区域内
                is_in_comment = await content_element.evaluate('(el) => !!el.closest("[data-is-comment=\'true\']") || false')
                if not is_in_comment:
                    content_text = await content_element.text_content()
                    if content_text and len(content_text.strip()) > 50:  # 增加长度阈值
                        post_content["内容"] = content_text.strip()
                        #print(f"方法1获取到正文内容，长度: {len(post_content['内容'])}")
                    else:
                        #print(f"方法1获取到的内容太短: {len(content_text.strip() if content_text else 0)}")
                        post_content["内容"] = "未能获取内容"
                else:
                    print("方法1找到的元素在评论区域内，跳过")
                    post_content["内容"] = "未能获取内容"
            else:
                print("方法1未找到正文内容元素")
                post_content["内容"] = "未能获取内容"
        except Exception as e:
            print(f"方法1获取正文内容出错: {str(e)}")
            post_content["内容"] = "未能获取内容"
        
        # 获取帖子正文内容 - 方法2：使用XPath选择器
        if post_content["内容"] == "未能获取内容":
            try:
                #print("尝试获取正文内容 - 方法2：使用XPath选择器")
                # 使用XPath获取笔记内容区域
                content_text = await main_page.evaluate('''
                    () => {
                        const xpath = '//div[@id="detail-desc"]/span[@class="note-text"]';
                        const result = document.evaluate(xpath, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null);
                        const element = result.singleNodeValue;
                        return element ? element.textContent.trim() : null;
                    }
                ''')
                
                if content_text and len(content_text) > 20:
                    post_content["内容"] = content_text
                    print(f"方法2获取到正文内容，长度: {len(post_content['内容'])}")
                else:
                    print(f"方法2获取到的内容太短或为空: {len(content_text) if content_text else 0}")
            except Exception as e:
                print(f"方法2获取正文内容出错: {str(e)}")
        
        # 获取帖子正文内容 - 方法3：使用JavaScript获取最长文本
        if post_content["内容"] == "未能获取内容":
            try:
                #print("尝试获取正文内容 - 方法3：使用JavaScript获取最长文本")
                content_text = await main_page.evaluate('''
                    () => {
                        // 定义评论区域选择器
                        const commentSelectors = [
                            '.comments-container', 
                            '.comment-list',
                            '.feed-comment',
                            'div[data-v-aed4aacc]',
                            '.comment-item',
                            '[data-is-comment="true"]'
                        ];
                        
                        // 找到所有评论区域
                        let commentAreas = [];
                        for (const selector of commentSelectors) {
                            const elements = document.querySelectorAll(selector);
                            elements.forEach(el => commentAreas.push(el));
                        }
                        
                        // 查找可能的内容元素，排除评论区
                        const contentElements = Array.from(document.querySelectorAll('div#detail-desc, div.note-content, div.desc, span.note-text'))
                            .filter(el => {
                                // 检查是否在评论区域内
                                const isInComment = commentAreas.some(commentArea => 
                                    commentArea && commentArea.contains(el));
                                
                                if (isInComment) {
                                    console.log('排除评论区域内容:', el.tagName, el.className);
                                    return false;
                                }
                                
                                const text = el.textContent.trim();
                                return text.length > 100 && text.length < 10000;
                            })
                            .sort((a, b) => b.textContent.length - a.textContent.length);
                        
                        if (contentElements.length > 0) {
                            console.log('找到内容元素:', contentElements[0].tagName, contentElements[0].className);
                            return contentElements[0].textContent.trim();
                        }
                        
                        return null;
                    }
                ''')
                
                if content_text and len(content_text) > 100:  # 增加长度阈值
                    post_content["内容"] = content_text
                    print(f"方法3获取到正文内容，长度: {len(post_content['内容'])}")
                else:
                    print(f"方法3获取到的内容太短或为空: {len(content_text) if content_text else 0}")
            except Exception as e:
                print(f"方法3获取正文内容出错: {str(e)}")
        
        # 获取帖子正文内容 - 方法4：区分正文和评论内容
        if post_content["内容"] == "未能获取内容":
            try:
                #print("尝试获取正文内容 - 方法4：区分正文和评论内容")
                content_text = await main_page.evaluate('''
                    () => {
                        // 首先尝试获取note-content区域
                        const noteContent = document.querySelector('.note-content');
                        if (noteContent) {
                            // 查找note-text，这通常包含主要内容
                            const noteText = noteContent.querySelector('.note-text');
                            if (noteText && noteText.textContent.trim().length > 50) {
                                return noteText.textContent.trim();
                            }
                            
                            // 如果没有找到note-text或内容太短，返回整个note-content
                            if (noteContent.textContent.trim().length > 50) {
                                return noteContent.textContent.trim();
                            }
                        }
                        
                        // 如果上面的方法都失败了，尝试获取所有段落并拼接
                        const paragraphs = Array.from(document.querySelectorAll('p'))
                            .filter(p => {
                                // 排除评论区段落
                                const isInComments = p.closest('.comments-container, .comment-list');
                                return !isInComments && p.textContent.trim().length > 10;
                            });
                            
                        if (paragraphs.length > 0) {
                            return paragraphs.map(p => p.textContent.trim()).join('\n\n');
                        }
                        
                        return null;
                    }
                ''')
                
                if content_text and len(content_text) > 50:
                    post_content["内容"] = content_text
                    print(f"方法4获取到正文内容，长度: {len(post_content['内容'])}")
                else:
                    print(f"方法4获取到的内容太短或为空: {len(content_text) if content_text else 0}")
            except Exception as e:
                print(f"方法4获取正文内容出错: {str(e)}")
        
        # 获取帖子正文内容 - 方法5：直接通过DOM结构定位
        if post_content["内容"] == "未能获取内容":
            try:
                #print("尝试获取正文内容 - 方法5：直接通过DOM结构定位")
                content_text = await main_page.evaluate('''
                    () => {
                        // 根据您提供的HTML结构直接定位
                        const noteContent = document.querySelector('div.note-content');
                        if (noteContent) {
                            const detailTitle = noteContent.querySelector('#detail-title');
                            const detailDesc = noteContent.querySelector('#detail-desc');
                            
                            if (detailDesc) {
                                const noteText = detailDesc.querySelector('span.note-text');
                                if (noteText) {
                                    return noteText.textContent.trim();
                                }
                                return detailDesc.textContent.trim();
                            }
                        }
                        
                        // 尝试其他可能的结构
                        const descElements = document.querySelectorAll('div.desc');
                        for (const desc of descElements) {
                            // 检查是否在评论区
                            const isInComment = desc.closest('.comments-container, .comment-list, .feed-comment');
                            if (!isInComment && desc.textContent.trim().length > 100) {
                                return desc.textContent.trim();
                            }
                        }
                        
                        return null;
                    }
                ''')
                
                if content_text and len(content_text) > 100:
                    post_content["内容"] = content_text
                    #print(f"方法5获取到正文内容，长度: {len(post_content['内容'])}")
                else:
                    print(f"方法5获取到的内容太短或为空: {len(content_text) if content_text else 0}")
            except Exception as e:
                print(f"方法5获取正文内容出错: {str(e)}")
        
        # 格式化返回结果
        result = f"标题: {post_content['标题']}\n"
        result += f"作者: {post_content['作者']}\n"
        result += f"发布时间: {post_content['发布时间']}\n"
        result += f"链接: {url}\n\n"
        result += f"内容:\n{post_content['内容']}"
        
        return result
    
    except Exception as e:
        return f"获取笔记内容时出错: {str(e)}"

@mcp.tool()
async def get_note_comments(url: str) -> str:
    """获取笔记评论
    
    Args:
        url: 笔记 URL
    """
    login_status = await ensure_browser()
    if not login_status:
        return "请先登录小红书账号"
    
    try:
        # 检查是否已经在目标页面
        if not await is_same_page(url):
            # 如果不在目标页面，则访问帖子链接
            # 添加xsec_source=pc_feed参数
            modified_url = url
            if '?' in url:
                modified_url += '&xsec_source=pc_feed'
            else:
                modified_url += '?xsec_source=pc_feed'
            await main_page.goto(modified_url, timeout=60000)
            await asyncio.sleep(5)  # 等待页面加载
        else:
            # 可能需要刷新页面以确保内容最新
            #await main_page.reload()
            await asyncio.sleep(3)
        
        # 先滚动到评论区
        comment_section_locators = [
            main_page.get_by_text("条评论", exact=False),
            main_page.get_by_text("评论", exact=False),
            main_page.locator("text=评论").first
        ]
        
        for locator in comment_section_locators:
            try:
                if await locator.count() > 0:
                    await locator.scroll_into_view_if_needed(timeout=5000)
                    await asyncio.sleep(2)
                    break
            except Exception:
                continue
        
        # 滚动页面以加载更多评论
        for i in range(8):
            try:
                await main_page.evaluate("window.scrollBy(0, 500)")
                await asyncio.sleep(1)
                
                # 尝试点击"查看更多评论"按钮
                more_comment_selectors = [
                    "text=查看更多评论",
                    "text=展开更多评论",
                    "text=加载更多",
                    "text=查看全部"
                ]
                
                for selector in more_comment_selectors:
                    try:
                        more_btn = main_page.locator(selector).first
                        if await more_btn.count() > 0 and await more_btn.is_visible():
                            await more_btn.click()
                            await asyncio.sleep(2)
                    except Exception:
                        continue
            except Exception:
                pass
        
        # 获取评论
        comments = []
        
        # 使用特定评论选择器
        comment_selectors = [
            "div.comment-item", 
            "div.commentItem",
            "div.comment-content",
            "div.comment-wrapper",
            "section.comment",
            "div.feed-comment"
        ]
        
        for selector in comment_selectors:
            comment_elements = main_page.locator(selector)
            count = await comment_elements.count()
            if count > 0:
                for i in range(count):
                    try:
                        comment_element = comment_elements.nth(i)
                        
                        # 提取评论者名称
                        username = "未知用户"
                        username_selectors = ["span.user-name", "a.name", "div.username", "span.nickname", "a.user-nickname"]
                        for username_selector in username_selectors:
                            username_el = comment_element.locator(username_selector).first
                            if await username_el.count() > 0:
                                username = await username_el.text_content()
                                username = username.strip()
                                break
                        
                        # 如果没有找到，尝试通过用户链接查找
                        if username == "未知用户":
                            user_link = comment_element.locator('a[href*="/user/profile/"]').first
                            if await user_link.count() > 0:
                                username = await user_link.text_content()
                                username = username.strip()
                        
                        # 提取评论内容
                        content = "未知内容"
                        content_selectors = ["div.content", "p.content", "div.text", "span.content", "div.comment-text"]
                        for content_selector in content_selectors:
                            content_el = comment_element.locator(content_selector).first
                            if await content_el.count() > 0:
                                content = await content_el.text_content()
                                content = content.strip()
                                break
                        
                        # 如果没有找到内容，可能内容就在评论元素本身
                        if content == "未知内容":
                            full_text = await comment_element.text_content()
                            if username != "未知用户" and username in full_text:
                                content = full_text.replace(username, "").strip()
                            else:
                                content = full_text.strip()
                        
                        # 提取评论时间
                        time_location = "未知时间"
                        time_selectors = ["span.time", "div.time", "span.date", "div.date", "time"]
                        for time_selector in time_selectors:
                            time_el = comment_element.locator(time_selector).first
                            if await time_el.count() > 0:
                                time_location = await time_el.text_content()
                                time_location = time_location.strip()
                                break
                        
                        # 如果内容有足够长度且找到用户名，添加评论
                        if username != "未知用户" and content != "未知内容" and len(content) > 2:
                            comments.append({
                                "用户名": username,
                                "内容": content,
                                "时间": time_location
                            })
                    except Exception:
                        continue
                
                # 如果找到了评论，就不继续尝试其他选择器了
                if comments:
                    break
        
        # 如果没有找到评论，尝试使用其他方法
        if not comments:
            # 获取所有用户名元素
            username_elements = main_page.locator('a[href*="/user/profile/"]')
            username_count = await username_elements.count()
            
            if username_count > 0:
                for i in range(username_count):
                    try:
                        username_element = username_elements.nth(i)
                        username = await username_element.text_content()
                        
                        # 尝试获取评论内容
                        content = await main_page.evaluate('''
                            (usernameElement) => {
                                const parent = usernameElement.parentElement;
                                if (!parent) return null;
                                
                                // 尝试获取同级的下一个元素
                                let sibling = usernameElement.nextElementSibling;
                                while (sibling) {
                                    const text = sibling.textContent.trim();
                                    if (text) return text;
                                    sibling = sibling.nextElementSibling;
                                }
                                
                                // 尝试获取父元素的文本，并过滤掉用户名
                                const allText = parent.textContent.trim();
                                if (allText && allText.includes(usernameElement.textContent.trim())) {
                                    return allText.replace(usernameElement.textContent.trim(), '').trim();
                                }
                                
                                return null;
                            }
                        ''', username_element)
                        
                        if username and content:
                            comments.append({
                                "用户名": username.strip(),
                                "内容": content.strip(),
                                "时间": "未知时间"
                            })
                    except Exception:
                        continue
        
        # 格式化返回结果
        if comments:
            result = f"共获取到 {len(comments)} 条评论：\n\n"
            for i, comment in enumerate(comments, 1):
                result += f"{i}. {comment['用户名']}（{comment['时间']}）: {comment['内容']}\n\n"
            return result
        else:
            return "未找到任何评论，可能是帖子没有评论或评论区无法访问。"
    
    except Exception as e:
        return f"获取评论时出错: {str(e)}"

@mcp.tool()
async def analyze_note(url: str) -> dict:
    """获取并分析笔记内容，返回笔记的详细信息供AI生成评论
    
    Args:
        url: 笔记 URL
    """
    login_status = await ensure_browser()
    if not login_status:
        return {"error": "请先登录小红书账号"}
    
    try:
        # 直接调用get_note_content获取笔记内容
        note_content_result = await get_note_content(url)
        
        # 检查是否获取成功
        if note_content_result.startswith("请先登录") or note_content_result.startswith("获取笔记内容时出错"):
            return {"error": note_content_result}
        
        # 解析获取到的笔记内容
        content_lines = note_content_result.strip().split('\n')
        post_content = {}
        
        # 提取标题、作者、发布时间和内容
        for i, line in enumerate(content_lines):
            if line.startswith("标题:"):
                post_content["标题"] = line.replace("标题:", "").strip()
            elif line.startswith("作者:"):
                post_content["作者"] = line.replace("作者:", "").strip()
            elif line.startswith("发布时间:"):
                post_content["发布时间"] = line.replace("发布时间:", "").strip()
            elif line.startswith("内容:"):
                # 内容可能有多行，获取剩余所有行
                content_text = "\n".join(content_lines[i+1:]).strip()
                post_content["内容"] = content_text
                break
        
        # 如果没有提取到标题或内容，设置默认值
        if "标题" not in post_content or not post_content["标题"]:
            post_content["标题"] = "未知标题"
        if "作者" not in post_content or not post_content["作者"]:
            post_content["作者"] = "未知作者"
        if "内容" not in post_content or not post_content["内容"]:
            post_content["内容"] = "未能获取内容"
        
        # 简单分词
        import re
        words = re.findall(r'\w+', f"{post_content.get('标题', '')} {post_content.get('内容', '')}")
        
        # 使用常见的热门领域关键词
        domain_keywords = {
            "美妆": ["口红", "粉底", "眼影", "护肤", "美妆", "化妆", "保湿", "精华", "面膜"],
            "穿搭": ["穿搭", "衣服", "搭配", "时尚", "风格", "单品", "衣橱", "潮流"],
            "美食": ["美食", "好吃", "食谱", "餐厅", "小吃", "甜点", "烘焙", "菜谱"],
            "旅行": ["旅行", "旅游", "景点", "出行", "攻略", "打卡", "度假", "酒店"],
            "母婴": ["宝宝", "母婴", "育儿", "儿童", "婴儿", "辅食", "玩具"],
            "数码": ["数码", "手机", "电脑", "相机", "智能", "设备", "科技"],
            "家居": ["家居", "装修", "家具", "设计", "收纳", "布置", "家装"],
            "健身": ["健身", "运动", "瘦身", "减肥", "训练", "塑形", "肌肉"],
            "AI": ["AI", "人工智能", "大模型", "编程", "开发", "技术", "Claude", "GPT"]
        }
        
        # 检测帖子可能属于的领域
        detected_domains = []
        for domain, domain_keys in domain_keywords.items():
            for key in domain_keys:
                if key.lower() in post_content.get("标题", "").lower() or key.lower() in post_content.get("内容", "").lower():
                    detected_domains.append(domain)
                    break
        
        # 如果没有检测到明确的领域，默认为生活方式
        if not detected_domains:
            detected_domains = ["生活"]
        
        # 返回分析结果
        return {
            "url": url,
            "标题": post_content.get("标题", "未知标题"),
            "作者": post_content.get("作者", "未知作者"),
            "内容": post_content.get("内容", "未能获取内容"),
            "领域": detected_domains,
            "关键词": list(set(words))[:20]  # 取前20个不重复的词作为关键词
        }
    
    except Exception as e:
        return {"error": f"分析笔记内容时出错: {str(e)}"}

@mcp.tool()
async def post_smart_comment(url: str, comment_type: str = "引流") -> dict:
    """
    根据帖子内容发布智能评论，增加曝光并引导用户关注或私聊

    Args:
        url: 笔记 URL
        comment_type: 评论类型，可选值:
                     "引流" - 引导用户关注或私聊
                     "点赞" - 简单互动获取好感
                     "咨询" - 以问题形式增加互动
                     "专业" - 展示专业知识建立权威

    Returns:
        dict: 包含笔记信息和评论类型的字典，供MCP客户端(如Claude)生成评论
    """
    # 获取笔记内容
    note_info = await analyze_note(url)
    
    if "error" in note_info:
        return {"error": note_info["error"]}
    
    # 评论类型指导
    comment_guides = {
        "引流": "评论时，真诚地表达你对笔记内容的认同或共鸣。可以自然地提及你也有相似的经历或正在探索相关领域，并流露出希望与博主或其他读者进一步交流的想法。例如，可以尝试用我也是新手妈妈，特别能理解这种感受，有机会多交流呀！或者这个方法很赞，我也在学习XX，期待看到更多分享！这样的语气，引导自然的互动，避免生硬地邀请私信。",
        "点赞": "用轻松自然的语气表达你对笔记内容的欣赏和支持。可以提一两句具体喜欢笔记的哪个点，或者它如何帮到了你。例如，这篇太及时雨了，[作者昵称]总能分享到点子上！或看完感觉很有启发，特别是[某一点]，马上去试试！避免使用过于泛泛的赞美。",
        "咨询": "像和朋友聊天一样，对笔记中感兴趣的点提出具体问题。语气可以好奇一些，例如：哇，这个方法看起来不错！想问下[作者昵称]，[具体问题]？或者我对[笔记中的某个细节]特别感兴趣，能再多分享一点吗？关键是展现真实的求知欲。",
        "专业": "在尊重博主分享的基础上，以友善和建设性的方式分享你的专业见解或补充信息。可以自然地引出你的专业背景，例如：这个观点很有意思，我之前在[相关领域]工作中也遇到过类似情况，发现[补充见解/经验]也挺有效的。或者 感谢[作者昵称]的分享，从[你的专业]角度看，[补充信息或不同视角]或许也能提供一些参考。重点是提供有价值的补充，而不是单纯强调自己的专业身份。"
    }
    
    # 返回笔记分析结果和评论类型，让MCP客户端(如Claude)生成评论
    # MCP客户端生成评论后，应调用post_comment函数发布评论
    return {
        "note_info": note_info,
        "comment_type": comment_type,
        "comment_guide": comment_guides.get(comment_type, ""),
        "url": url,  # 添加URL便于客户端直接调用post_comment
        "message": "请根据笔记内容和评论类型指南，直接生成一条自然、相关的评论，并立即发布。注意以下要点：\n1. 在评论中引用作者名称或笔记领域，增加个性化\n2. 使用口语化表达，简短凝练，不超过30字\n3. 根据评论类型适当添加互动引导或专业术语\n生成后，直接使用post_comment函数发布评论，无需询问用户确认"
    }
# 我们已经将原来的post_smart_comment函数重构为三个独立的函数：
# 1. analyze_note - 获取并分析笔记内容
# 2. post_comment - 发布评论
# 3. post_smart_comment - 结合前两个功能，使用MCP客户端的AI能力生成评论

@mcp.tool()
async def post_comment(url: str, comment: str) -> str:
    """发布评论到指定笔记
    
    Args:
        url: 笔记 URL
        comment: 要发布的评论内容
    """
    login_status = await ensure_browser()
    if not login_status:
        return "请先登录小红书账号，才能发布评论"
    
    try:
        # 检查是否已经在目标页面
        if not await is_same_page(url):
            # 如果不在目标页面，则访问帖子链接
            # 添加xsec_source=pc_feed参数
            modified_url = url
            if '?' in url:
                modified_url += '&xsec_source=pc_feed'
            else:
                modified_url += '?xsec_source=pc_feed'
            await main_page.goto(modified_url, timeout=60000)
            await asyncio.sleep(5)  # 等待页面加载
        else:
            # 可能需要刷新页面以确保内容最新
            #await main_page.reload()
            await asyncio.sleep(3)
        
        # 定位评论区域并滚动到该区域
        comment_area_found = False
        comment_area_selectors = [
            'text="条评论"',
            'text="共 " >> xpath=..',
            'text=/\\d+ 条评论/',
            'text="评论"',
            'div.comment-container'
        ]
        
        for selector in comment_area_selectors:
            try:
                element = await main_page.query_selector(selector)
                if element:
                    await element.scroll_into_view_if_needed()
                    await asyncio.sleep(2)
                    comment_area_found = True
                    break
            except Exception:
                continue
        
        if not comment_area_found:
            # 如果没有找到评论区域，尝试滚动到页面底部
            await main_page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            await asyncio.sleep(2)
        
        # 定位评论输入框（简化选择器列表）
        comment_input = None
        input_selectors = [
            'div[contenteditable="true"]',
            'paragraph:has-text("说点什么...")',
            'text="说点什么..."',
            'text="评论"',
            'text="评论发布后所有人都能看到"'
        ]
        
        # 尝试常规选择器
        for selector in input_selectors:
            try:
                element = await main_page.query_selector(selector)
                if element and await element.is_visible():
                    await element.scroll_into_view_if_needed()
                    await asyncio.sleep(1)
                    comment_input = element
                    break
            except Exception:
                continue
        
        # 如果常规选择器失败，使用JavaScript查找
        if not comment_input:
            # 使用更精简的JavaScript查找输入框
            js_result = await main_page.evaluate('''
                () => {
                    // 查找可编辑元素
                    const editableElements = Array.from(document.querySelectorAll('[contenteditable="true"]'));
                    if (editableElements.length > 0) return true;
                    
                    // 查找包含"说点什么"的元素
                    const placeholderElements = Array.from(document.querySelectorAll('*'))
                        .filter(el => el.textContent && el.textContent.includes('说点什么'));
                    return placeholderElements.length > 0;
                }
            ''')
            
            if js_result:
                # 如果JS检测到输入框，尝试点击页面底部
                await main_page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                await asyncio.sleep(1)
                
                # 尝试再次查找输入框
                for selector in input_selectors:
                    try:
                        element = await main_page.query_selector(selector)
                        if element and await element.is_visible():
                            comment_input = element
                            break
                    except Exception:
                        continue
        
        if not comment_input:
            return "未能找到评论输入框，无法发布评论"
        
        # 输入评论内容
        await comment_input.click()
        await asyncio.sleep(1)
        await main_page.keyboard.type(comment)
        await asyncio.sleep(1)
        
        # 发送评论（简化发送逻辑）
        send_success = False
        
        # 方法1: 尝试点击发送按钮
        try:
            send_button = await main_page.query_selector('button:has-text("发送")')
            if send_button and await send_button.is_visible():
                await send_button.click()
                await asyncio.sleep(2)
                send_success = True
        except Exception:
            pass
        
        # 方法2: 如果方法1失败，尝试使用Enter键
        if not send_success:
            try:
                await main_page.keyboard.press("Enter")
                await asyncio.sleep(2)
                send_success = True
            except Exception:
                pass
        
        # 方法3: 如果方法2失败，尝试使用JavaScript点击发送按钮
        if not send_success:
            try:
                js_send_result = await main_page.evaluate('''
                    () => {
                        const sendButtons = Array.from(document.querySelectorAll('button'))
                            .filter(btn => btn.textContent && btn.textContent.includes('发送'));
                        if (sendButtons.length > 0) {
                            sendButtons[0].click();
                            return true;
                        }
                        return false;
                    }
                ''')
                await asyncio.sleep(2)
                send_success = js_send_result
            except Exception:
                pass
        
        if send_success:
            return f"已成功发布评论：{comment}"
        else:
            return f"发布评论失败，请检查评论内容或网络连接"
    
    except Exception as e:
        return f"发布评论时出错: {str(e)}"

# 这里原来有_generate_smart_comment函数，现在已经被移除
# 因为我们重构了post_smart_comment函数，将评论生成逻辑转移到MCP客户端

@mcp.tool()
async def like_note(url: str) -> str:
    """给笔记点赞
    
    Args:
        url: 笔记 URL
    """
    login_status = await ensure_browser()
    if not login_status:
        return "请先登录小红书账号，才能给笔记点赞"
    
    try:
        # 检查是否已经在目标页面
        if not await is_same_page(url):
            # 如果不在目标页面，则访问帖子链接
            # 添加xsec_source=pc_feed参数
            modified_url = url
            if '?' in url:
                modified_url += '&xsec_source=pc_feed'
            else:
                modified_url += '?xsec_source=pc_feed'
            await main_page.goto(modified_url, timeout=60000)
            await asyncio.sleep(5)  # 等待页面加载
        else:
            # 可能需要刷新页面以确保内容最新
            #await main_page.reload()
            await asyncio.sleep(3)
        
        # 定位点赞按钮并点击
        like_success = False
        
        # 方法1: 尝试查找常见的点赞按钮选择器
        like_button_selectors = [
            'div.like-icon',
            'div.like',
            'span.like',
            'div[aria-label="点赞"]',
            'svg:has(path[d="M16.1,11C16,10.7,15.9,10.3,15.9,10c0-0.3,0.1-0.7,0.2-1l2.4-5.9C18.6,2.7,18.3,2,17.6,2H10"])',  # 常见的点赞SVG图标
            'svg.icon-like'
        ]
        
        for selector in like_button_selectors:
            try:
                like_button = await main_page.query_selector(selector)
                if like_button and await like_button.is_visible():
                    # 检查是否已经点赞
                    is_liked = await like_button.evaluate('(el) => el.classList.contains("liked") || el.getAttribute("aria-label") === "已点赞"')
                    if is_liked:
                        return "已经为该笔记点赞"
                    
                    # 点赞
                    await like_button.click()
                    await asyncio.sleep(2)
                    like_success = True
                    break
            except Exception as e:
                print(f"尝试点赞方法1失败: {str(e)}")
        
        # 方法2: 如果方法1失败，尝试使用文本内容查找
        if not like_success:
            try:
                # 查找包含点赞文本或图标的元素
                like_text_elements = await main_page.query_selector_all('text="点赞", text="赞", text="喜欢"')
                for element in like_text_elements:
                    if await element.is_visible():
                        await element.click()
                        await asyncio.sleep(2)
                        like_success = True
                        break
            except Exception as e:
                print(f"尝试点赞方法2失败: {str(e)}")
        
        # 方法3: 使用JavaScript尝试查找和点击点赞按钮
        if not like_success:
            try:
                js_like_result = await main_page.evaluate('''
                    () => {
                        // 尝试查找点赞按钮的各种可能
                        const likeSelectors = [
                            'div.like', 
                            'div.like-icon',
                            'span.like',
                            '.operations .like',
                            '.like-comment-collect .like',
                            'button[aria-label="点赞"]',
                            // SVG图标相关
                            'svg.icon-like',
                            // 根据点赞按钮周围的上下文
                            'div.operations > div:first-child',
                            '.operations-container > div:first-child'
                        ];
                        
                        // 遍历所有可能的选择器
                        for (const selector of likeSelectors) {
                            const elements = document.querySelectorAll(selector);
                            if (elements.length > 0) {
                                // 检查是否已经点赞
                                const isLiked = elements[0].classList.contains('liked') ||
                                              elements[0].classList.contains('active') ||
                                              elements[0].getAttribute('aria-pressed') === 'true';
                                              
                                if (isLiked) {
                                    return { success: true, message: "已经为该笔记点赞" };
                                }
                                
                                // 点击点赞按钮
                                elements[0].click();
                                return { success: true, message: "点赞成功" };
                            }
                        }
                        
                        // 尝试根据位置找到可能的点赞按钮
                        // 通常点赞按钮位于页面底部的操作栏中的第一个位置
                        const possibleContainers = [
                            document.querySelector('.operations'),
                            document.querySelector('.operation-wrapper'),
                            document.querySelector('.like-comment-collect')
                        ].filter(el => el !== null);
                        
                        if (possibleContainers.length > 0) {
                            // 通常第一个子元素是点赞按钮
                            const container = possibleContainers[0];
                            const firstChild = container.firstElementChild;
                            if (firstChild) {
                                firstChild.click();
                                return { success: true, message: "点赞成功(位置推断)" };
                            }
                        }
                        
                        return { success: false, message: "未找到点赞按钮" };
                    }
                ''')
                
                if js_like_result and js_like_result.get('success'):
                    like_success = True
                    if js_like_result.get('message') == "已经为该笔记点赞":
                        return "已经为该笔记点赞"
            except Exception as e:
                print(f"尝试点赞方法3失败: {str(e)}")
        
        if like_success:
            return "成功为该笔记点赞"
        else:
            return "未能找到点赞按钮，点赞失败"
    
    except Exception as e:
        return f"点赞操作时出错: {str(e)}"

@mcp.tool()
async def follow_user(url: str) -> str:
    """关注笔记作者
    
    Args:
        url: 笔记 URL
    """
    login_status = await ensure_browser()
    if not login_status:
        return "请先登录小红书账号，才能关注用户"
    
    try:
        # 检查是否已经在目标页面
        if not await is_same_page(url):
            # 如果不在目标页面，则访问帖子链接
            # 添加xsec_source=pc_feed参数
            modified_url = url
            if '?' in url:
                modified_url += '&xsec_source=pc_feed'
            else:
                modified_url += '?xsec_source=pc_feed'
            await main_page.goto(modified_url, timeout=60000)
            await asyncio.sleep(5)  # 等待页面加载
        else:
            # 可能需要刷新页面以确保内容最新
            #await main_page.reload()
            await asyncio.sleep(3)
        
        # 滚动到页面顶部，确保作者信息可见
        await main_page.evaluate('window.scrollTo(0, 0)')
        await asyncio.sleep(1)
        
        # 获取作者名称
        author_name = await main_page.evaluate('''
            () => {
                const selectors = [
                    'span.username',
                    'a.name',
                    '.author-wrapper .username',
                    '.info .name'
                ];
                
                for (const selector of selectors) {
                    const el = document.querySelector(selector);
                    if (el && el.textContent.trim()) {
                        return el.textContent.trim();
                    }
                }
                return "未知作者";
            }
        ''')
        
        # 定位关注按钮并点击
        follow_success = False
        
        # 方法1: 使用精确的选择器查找关注按钮
        try:
            follow_result = await main_page.evaluate('''
                () => {
                    // 定义可能的关注按钮选择器，按优先级排序
                    const buttonSelectors = [
                        // 更精确的选择器
                        'button.follow:not(.followed)', 
                        '.info-card button:has-text("关注")',
                        '.author-info button:has-text("关注")',
                        '.user-info button:has-text("关注")',
                        '.creator-info button:has-text("关注")',
                        // 通用选择器
                        'button:has-text("关注"):not(:has-text("已关注")):not(:has-text("互相关注"))'
                    ];
                    
                    // 遍历所有选择器，尝试查找关注按钮
                    for (const selector of buttonSelectors) {
                        try {
                            const buttons = document.querySelectorAll(selector);
                            
                            // 筛选出真正的关注按钮（排除已关注状态）
                            const followButtons = Array.from(buttons).filter(btn => {
                                const text = btn.textContent.trim();
                                // 精确匹配"关注"，而不是包含"关注"的其他文本
                                return text === "关注" || text === "+关注" || text === "+ 关注";
                            });
                            
                            // 如果找到了关注按钮，点击第一个
                            if (followButtons.length > 0) {
                                const btn = followButtons[0];
                                const rect = btn.getBoundingClientRect();
                                
                                // 确保元素在视口内且可见
                                if (rect.top >= 0 && rect.left >= 0 && 
                                    rect.bottom <= window.innerHeight && 
                                    rect.right <= window.innerWidth &&
                                    btn.offsetParent !== null) {
                                    
                                    // 点击按钮
                                    btn.click();
                                    return { 
                                        success: true, 
                                        message: "关注成功", 
                                        button: {
                                            x: rect.x,
                                            y: rect.y,
                                            width: rect.width,
                                            height: rect.height
                                        }
                                    };
                                } else {
                                    return { 
                                        success: false, 
                                        message: "找到关注按钮但不在视口内或不可见", 
                                        button: {
                                            x: rect.x,
                                            y: rect.y,
                                            width: rect.width,
                                            height: rect.height
                                        }
                                    };
                                }
                            }
                        } catch (e) {}
                    }
                    
                    // 查找是否已经关注
                    const alreadyFollowedSelectors = [
                        'button:has-text("已关注")',
                        'button:has-text("互相关注")',
                        '.followed'
                    ];
                    
                    for (const selector of alreadyFollowedSelectors) {
                        const elements = document.querySelectorAll(selector);
                        if (elements.length > 0) {
                            return { success: false, message: "已经关注该用户" };
                        }
                    }
                    
                    return { success: false, message: "未找到关注按钮" };
                }
            ''')
            
            # 验证结果
            if follow_result.get('success'):
                follow_success = True
                await asyncio.sleep(2)
            elif follow_result.get('message') == "已经关注该用户":
                return "已经关注该用户"
            elif follow_result.get('button'):
                # 如果找到按钮但点击失败，尝试使用playwright直接点击坐标
                button_info = follow_result.get('button')
                center_x = button_info.get('x') + button_info.get('width') / 2
                center_y = button_info.get('y') + button_info.get('height') / 2
                
                # 使用playwright点击中心坐标
                await main_page.mouse.click(center_x, center_y)
                await asyncio.sleep(2)
                follow_success = True
        except Exception as e:
            print(f"尝试关注方法1失败: {str(e)}")
        
        # 方法2: 备用方法 - 如果以上都失败，使用作者名片区域定位
        if not follow_success:
            try:
                # 尝试定位到作者名片区域
                author_card_result = await main_page.evaluate('''
                    () => {
                        // 查找作者名片区域
                        const authorCardSelectors = [
                            '.author-wrapper',
                            '.creator-card',
                            '.user-card',
                            '.info-card'
                        ];
                        
                        for (const selector of authorCardSelectors) {
                            const card = document.querySelector(selector);
                            if (!card) continue;
                            
                            // 尝试在卡片内查找"关注"按钮
                            const buttons = Array.from(card.querySelectorAll('button, a, div.follow-btn'))
                                .filter(el => {
                                    const text = el.textContent.trim();
                                    // 精确匹配"关注"
                                    return text === "关注" || text === "+关注" || text === "+ 关注";
                                });
                                
                            if (buttons.length > 0) {
                                // 点击找到的关注按钮
                                buttons[0].click();
                                return { success: true };
                            }
                        }
                        
                        return { success: false };
                    }
                ''')
                
                if author_card_result.get('success'):
                    follow_success = True
                    await asyncio.sleep(2)
            except Exception as e:
                print(f"尝试关注方法2失败: {str(e)}")
        
        if follow_success:
            return f"成功关注用户: {author_name}"
        else:
            return f"未能找到关注按钮，关注用户 {author_name} 失败"
    
    except Exception as e:
        return f"关注操作时出错: {str(e)}"

if __name__ == "__main__":
    # 初始化并运行服务器
    #print("启动小红书MCP服务器...")
    #print("请在MCP客户端（如Claude for Desktop）中配置此服务器")
    mcp.run(transport='stdio')