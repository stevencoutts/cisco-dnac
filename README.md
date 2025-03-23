# dnac

A modern Python client library for Cisco Catalyst Centre's REST API. This library provides a type-safe, feature-rich interface for interacting with Cisco Catalyst Centre, with support for authentication, request/response serialization, and task management.

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

- `menu.py`: Interactive terminal menu for running other scripts
- `segment.py`: Display SDA segments
- `devices.py`: List network devices from Catalyst Centre with detailed information
- `pool-import.py`: Add global IP pools and assign them to virtual networks from CSV file
- `cfs-import.py`: Configure Campus fabric edge ports from CSV file
- `template.py`: Provision a user template without using network profiles

### Using the menu.py Script

The `menu.py` script provides an interactive terminal-based menu system for running other scripts in the repository.

1. Make sure you have the required configuration in your `config.yaml` file (see devices.py section for details)

2. Run the menu:
```bash
python menu.py
```

3. Navigation:
   - Use ↑↓ arrow keys to navigate between options
   - Press Enter to select an option
   - Press 'q' to quit
   - When viewing script output:
     - Use ↑↓ to scroll through the output
     - Press 'q' to return to the main menu

The menu provides easy access to:
- List Network Devices
- List SDA Segments
- Exit

### Using the devices.py Script

The `devices.py` script retrieves and displays network devices from Cisco Catalyst Centre.

1. Create or update your `config.yaml` file:
```yaml
# Catalyst Centre Server Configuration
server:
  host: "https://sandboxdnac.cisco.com"
  port: 443
  verify_ssl: false
  timeout: 30

# Authentication
auth:
  username: "devnetuser"
  password: "Cisco123!"
```

2. Run the script:
```bash
python devices.py
```

3. Optional arguments:
   - `-c, --config`: Specify a custom config file path
   - `-v, --verbose`: Enable verbose output for debugging

The script will display:
- List of all network devices with hostname, IP, platform, serial number, etc.
- Detailed information about the first device
- Interface information for the first device

## Development

### Prerequisites

- Python 3.7 or higher
- pip (Python package installer)

### Setting Up Development Environment

1. Clone the repository:
```bash
git clone https://github.com/yourusername/dnac.git
cd dnac
```

2. Create and activate virtual environment:
```bash
# Using the setup script
./setup.sh

# Or manually
python3 -m venv venv
source venv/bin/activate  # On Unix/macOS
# or
.\venv\Scripts\activate  # On Windows
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

### Development Tools

The project uses several development tools to ensure code quality:

#### Code Formatting
```bash
# Format code using Black
black .
```

#### Type Checking
```bash
# Check types using MyPy
mypy .
```

#### Linting
```bash
# Lint code using Flake8
flake8
```

#### Testing
```bash
# Run tests using pytest
pytest
```

### Project Structure

```
dnac/
├── venv/                  # Virtual environment (not in git)
├── dna.py                # Main library code
├── requirements.txt      # Project dependencies
├── setup.sh             # Environment setup script
├── .gitignore           # Git ignore rules
└── tests/               # Test directory
```

### Dependencies

The project requires the following main dependencies:
- `requests>=2.31.0`: For HTTP requests
- `typing-extensions>=4.8.0`: For type hints
- `pytest>=7.4.0`: For testing
- `black>=23.11.0`: For code formatting
- `flake8>=6.1.0`: For linting
- `mypy>=1.7.0`: For type checking

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
