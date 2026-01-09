# Testing Guidelines for SatWatch

## Overview

This document outlines how tests should be written for the SatWatch project. Cursor AI will reference this file when generating or modifying test code.

## Testing Framework

We use **pytest** as our testing framework. It's simple, powerful, and widely used in the Python community.

## Test File Organization

- Place all tests in a `tests/` directory
- Test files should be named `test_*.py` or `*_test.py`
- Mirror the source structure: `src/satwatch/tracker.py` → `tests/test_tracker.py`

## Writing Tests

### Basic Test Structure

```python
import pytest
from satwatch.tracker import calculate_position

def test_calculate_position_with_valid_tle():
    """Test that position calculation works with valid TLE data."""
    # Arrange: Set up test data
    tle_data = "ISS\n1 25544U 98067A..."
    
    # Act: Execute the function
    result = calculate_position(tle_data)
    
    # Assert: Verify the result
    assert result is not None
    assert -90 <= result['latitude'] <= 90
```

### Test Naming

- Use descriptive names: `test_function_name_scenario`
- Examples:
  - `test_download_iss_tle_success`
  - `test_download_iss_tle_network_error`
  - `test_calculate_position_invalid_tle`

### Testing External Dependencies

**Always mock external API calls** (like CelesTrak downloads):

```python
from unittest.mock import patch, Mock

@patch('requests.get')
def test_download_iss_tle_success(mock_get):
    """Test successful TLE download."""
    # Mock the response
    mock_response = Mock()
    mock_response.text = "ISS\n1 25544U..."
    mock_response.raise_for_status = Mock()
    mock_get.return_value = mock_response
    
    # Test the function
    result = download_iss_tle()
    assert "ISS" in result
```

### Error Handling Tests

Test that errors are handled gracefully:

```python
def test_download_iss_tle_network_error():
    """Test handling of network errors."""
    with patch('requests.get', side_effect=requests.RequestException):
        with pytest.raises(requests.RequestException):
            download_iss_tle()
```

## Running Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run a specific test file
pytest tests/test_tracker.py

# Run with coverage report
pytest --cov=src --cov-report=html
```

## Coverage Goals

- Aim for **80%+ coverage** on core functionality
- Focus on critical paths:
  - TLE parsing and validation
  - Position calculations
  - Error handling

## Test Fixtures

Use pytest fixtures for reusable test data:

```python
@pytest.fixture
def sample_tle():
    """Provide sample TLE data for tests."""
    return """ISS (ZARYA)
1 25544U 98067A   24123.4567890  .00001234  00000+0  12345-4 0  9999
2 25544  51.6442 123.4567 0001234  0.0000  0.0000 15.49123456 12345"""
```

## Best Practices

1. **One assertion per test** (when possible) - makes failures clearer
2. **Test edge cases** - empty strings, None values, boundary conditions
3. **Keep tests fast** - mock slow operations (network, file I/O)
4. **Test behavior, not implementation** - focus on what the function does, not how
5. **Use descriptive test names** - they serve as documentation

## Example Test File

When tests are created, they should follow the structure above. Example test file location:
- `tests/test_iss_tracker.py` - Tests for the ISS tracker script

**Note:** Test files will be created as the project expands. For now, the main script (`src/iss_tracker.py`) can be tested manually by running it.

