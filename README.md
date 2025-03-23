# Cisco Catalyst Centre CLI Tools

A command-line interface (CLI) tool for managing Cisco Catalyst Centre (formerly DNA Center) networks. This tool provides a user-friendly interface for common network management tasks.

## Features

- **Site Hierarchy Management**
  - List site hierarchy
  - Add new sites (Area, Building, Floor)
  - View site details

- **Fabric Configuration** (requires Fabric enabled)
  - List SDA segments
  - View segment details

- **Device Management**
  - List network devices
  - View device details

- **Configuration Management**
  - Edit configuration settings
  - View current configuration

## Prerequisites

- Python 3.8 or higher
- Cisco Catalyst Centre (formerly DNA Center) instance
- Network access to the Catalyst Centre instance

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/dnac.git
   cd dnac
   ```

2. Install required packages:
   ```bash
   pip install -r requirements.txt
   ```

3. Create a configuration file:
   ```bash
   cp config.yaml.example config.yaml
   ```

4. Edit `config.yaml` with your Catalyst Centre details:
   ```yaml
   server:
     host: "your-dnac-host"
     verify_ssl: false  # Set to true if using valid SSL certificate
   
   auth:
     username: "your-username"
     password: "your-password"
   ```

## Usage

Run the application:
```bash
./run.sh
```

### Menu Navigation

- Use arrow keys (↑/↓) to navigate menu items
- Press Enter to select an option
- Press Esc or 'q' to quit
- Some options require Fabric to be enabled on your Catalyst Centre instance

### Menu Structure

1. **Site Hierarchy**
   - List Hierarchy
   - Add Site

2. **Fabric Configuration** (requires Fabric enabled)
   - List SDA Segments

3. **Device Management**
   - List Network Devices

4. **Configuration**
   - Edit Configuration

5. **Exit**

## Development

### Project Structure

```
dnac/
├── dnac/
│   ├── cli/           # CLI interface components
│   ├── core/          # Core functionality
│   ├── ui/            # UI components
│   └── scripts/       # Individual script modules
├── scripts/           # Standalone scripts
├── config.yaml        # Configuration file
├── requirements.txt   # Python dependencies
└── run.sh            # Launch script
```

### Adding New Features

1. Create a new script in the `scripts/` directory
2. Add the script to the menu system in `dnac/cli/menu.py`
3. Update the README with new feature documentation

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under The Unlicense - see below for details:

```
This is free and unencumbered software released into the public domain.

Anyone is free to copy, modify, publish, use, compile, sell, or
distribute this software, either in source code form or as a compiled
binary, for any purpose, commercial or non-commercial, and by any
means.

In jurisdictions that recognize copyright laws, the author or authors
of this software dedicate any and all copyright interest in the
software to the public domain. We make this dedication for the benefit
of the public at large and to the detriment of our heirs and
successors. We intend this dedication to be an overt act of
relinquishment in perpetuity of all present and future rights to this
software under copyright law.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
IN NO EVENT SHALL THE AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR
OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
OTHER DEALINGS IN THE SOFTWARE.

For more information, please refer to <https://unlicense.org>
```

## Author

Steven Coutts
