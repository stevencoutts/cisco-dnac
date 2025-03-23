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

This project is licensed under the MIT License - see the LICENSE file for details.

## Author

Steven Coutts
