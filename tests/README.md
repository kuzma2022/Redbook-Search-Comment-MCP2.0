# Tests for Redbook-Search-Comment-MCP2.0

This directory contains tests for the Redbook-Search-Comment-MCP2.0 project.

## Test Structure

- `test_utils.py`: Tests for utility functions in `utils.py`
- `conftest.py`: Configuration file for pytest

## Running Tests

To run all tests:

```bash
python -m pytest
```

To run a specific test file:

```bash
python -m pytest tests/test_utils.py
```

To run tests with verbose output:

```bash
python -m pytest -v
```

## Test Coverage

The current test coverage focuses on the utility functions in `utils.py`:

- `clean_url`: Cleans a URL by removing query parameters and extracting the ID for specific Xiaohongshu URLs
- `is_same_url`: Checks if two URLs are the same after cleaning
- `extract_note_id`: Extracts the note ID from a Xiaohongshu URL
- `convert_url_format`: Converts a Xiaohongshu URL from one format to another

## Adding New Tests

When adding new tests, follow these guidelines:

1. Create a new test file in the `tests` directory with a name that starts with `test_`
2. Use the `pytest` framework for writing tests
3. Group related tests in classes that start with `Test`
4. Write test functions that start with `test_`
5. Use descriptive names for test functions that explain what is being tested
6. Include docstrings for test functions to explain the purpose of the test

## Mocking

For tests that require browser interaction, use the `unittest.mock` module to mock the browser and other dependencies. See `test_page_utils.py` for an example of how to mock the browser.

## Continuous Integration

In a production environment, these tests would be run as part of a continuous integration pipeline to ensure that changes to the codebase do not break existing functionality.