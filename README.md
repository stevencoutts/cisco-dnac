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

## Core Examples

### Network Device Management

```python
# Get all network devices
devices = dnac.get('network-device').response

# Get device details by ID
device = dnac.get(f'network-device/{device_id}').response

# Get device interfaces
interfaces = dnac.get(f'interface/network-device/{device_id}').response

# Get device health
health = dnac.get(f'network-device/{device_id}/health').response
```

### Site Management

```python
# Get all sites
sites = dnac.get('site').response

# Get site hierarchy
site_hierarchy = dnac.get('site/{site_id}/hierarchy').response

# Create a new site
site_data = {
    "site": {
        "area": {
            "name": "Building 1",
            "parentName": "Global"
        },
        "building": {
            "name": "Floor 1",
            "parentName": "Building 1"
        },
        "floor": {
            "name": "Room 101",
            "parentName": "Floor 1"
        }
    }
}
response = dnac.post('site', data=site_data)
```

### Template Management

```python
# Get all templates
templates = dnac.get('template-programmer/template').response

# Get template details
template = dnac.get(f'template-programmer/template/{template_id}').response

# Deploy template to device
deploy_data = {
    "templateId": template_id,
    "targetInfo": [{
        "type": "MANAGED_DEVICE_UUID",
        "id": device_id,
        "params": {
            "hostname": "switch-1",
            "interface": "GigabitEthernet1/0/1"
        }
    }]
}
response = dnac.post('template-programmer/template/deploy', data=deploy_data)
```

### IP Address Management

```python
# Get IP pools
ip_pools = dnac.get('ippool', ver='v2').response

# Create new IP pool
pool_data = {
    "ipPoolName": "Guest-Pool",
    "ipPoolCidr": "10.0.0.0/24",
    "gateways": ["10.0.0.1"],
    "dhcpServerIps": ["10.0.0.2"],
    "dnsServerIps": ["8.8.8.8", "8.8.4.4"]
}
response = dnac.post('ippool', ver='v2', data=pool_data)

# Get IP address assignments
assignments = dnac.get('ip-address-assignment').response
```

### Task Management

```python
# Get task status
task_status = dnac.get(f'task/{task_id}').response

# Wait for task completion with custom settings
result = dnac.wait_on_task(
    task_id='task-id',
    timeout=300,  # 5 minutes
    interval=2,   # Initial check interval
    backoff=1.15  # Exponential backoff factor
)

# Get task history
task_history = dnac.get('task').response
```

### Error Handling

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
