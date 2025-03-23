# dnac

A modern Python client library for Cisco DNA Center's REST API. This library provides a type-safe, feature-rich interface for interacting with Cisco DNA Center, with support for authentication, request/response serialization, and task management.

## Features

- Type-safe API with comprehensive type hints
- Modern Python features (f-strings, dataclasses, generics)
- Robust error handling with custom exceptions
- Task management with automatic retries and backoff
- JSON response handling with attribute access
- Support for both synchronous and context manager usage
- Comprehensive logging support
- URL validation and security features

## Installation

```bash
pip install dnac
```

## Basic Usage

```python
from dnac import Dnac

# Create a client instance
dnac = Dnac('https://10.0.0.1/')

# Login with credentials
dnac.login('admin', 'password')

# Make API calls
print(dnac.get('network-device/count'))

# Close the session
dnac.close()
```

Or use the context manager for automatic cleanup:

```python
with Dnac('10.0.0.1') as dnac:
    dnac.login('admin', 'password')
    print(dnac.get('network-device/count'))
```

## Error Handling

The library provides custom exceptions for better error handling:

```python
from dnac import Dnac, TaskError, TimeoutError

try:
    with Dnac('10.0.0.1') as dnac:
        dnac.login('admin', 'password')
        # Wait for a task to complete
        result = dnac.wait_on_task('task-id')
except TaskError as e:
    print(f"Task failed: {e}")
    print(f"Response: {e.response}")
except TimeoutError as e:
    print(f"Task timed out: {e}")
```

## Task Management

The library provides robust task management with automatic retries and backoff:

```python
# Wait for a task to complete with custom timeout and retry settings
result = dnac.wait_on_task(
    task_id='task-id',
    timeout=300,  # 5 minutes
    interval=2,   # Initial check interval
    backoff=1.15  # Exponential backoff factor
)
```

## Sample Scripts

The repository includes several sample scripts demonstrating common use cases:

- `segment.py`: Display SDA segments
- `pool-import.py`: Add global IP pools and assign them to virtual networks from CSV file
- `cfs-import.py`: Configure Campus fabric edge ports from CSV file
- `template.py`: Provision a user template without using network profiles

## Development

### Requirements

- Python 3.7+
- requests
- typing-extensions (for Python < 3.8)

### Running Tests

```bash
python -m pytest tests/
```

### Code Style

The project uses:
- Black for code formatting
- Flake8 for linting
- MyPy for type checking

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Author

Tim Dorssers
