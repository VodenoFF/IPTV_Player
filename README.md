# IPTV Player

A modern IPTV player application with a clean user interface built using Python and CustomTkinter.

## Features
- Modern and clean user interface
- Secure credential storage with encryption
- Category-based channel organization
- Live IPTV stream playback
- Channel favorites and search (coming soon)
- EPG support (coming soon)

## Security Features
- Secure credential storage using Fernet encryption
- Secure key generation and storage
- No plain text password storage
- Encrypted configuration files

## Prerequisites

1. Python 3.8 or higher
2. MPV player installed on your system:
   - Windows: Download and install from [MPV website](https://mpv.io/installation/)
   - Linux: `sudo apt install mpv` (Ubuntu/Debian) or `sudo dnf install mpv` (Fedora)
   - macOS: `brew install mpv` (using Homebrew)

## Installation

1. Clone the repository:
```bash
git clone [repository-url]
cd iptv-player
```

2. Install the required dependencies:
```bash
pip install -r requirements.txt
```

## Dependencies
- customtkinter==5.2.2: Modern UI framework
- python-mpv==1.0.5: MPV player interface
- requests==2.31.0: HTTP client for API communication
- pillow==10.2.0: Image processing
- cryptography==42.0.2: Secure credential storage

## Running the Application

To run the application, simply execute:
```bash
python iptv_player.py
```

## Configuration
- The application automatically creates necessary configuration files on first run
- Credentials are securely stored in an encrypted format
- A secure encryption key is generated and stored in `.key` file
- Settings are saved in `settings.json`

## Requirements
- Python 3.8+
- MPV player installed
- Internet connection for IPTV streams
- Valid IPTV service credentials

## Security Notes
- Never share your `.key` file
- Keep your credentials.json and .key files secure
- The application uses Fernet encryption for storing sensitive data
- API communications use your original credentials for authentication

## Troubleshooting
1. If you encounter MPV-related errors:
   - Ensure MPV is properly installed on your system
   - Check if the MPV executable is in your system PATH
   - For Windows users, ensure the MPV DLL is in the lib directory

2. If you have login issues:
   - Verify your IPTV service credentials
   - Check your internet connection
   - Ensure the IPTV service is operational

## Contributing
Contributions are welcome! Please feel free to submit a Pull Request.

## License
[Add your license information here]

## Building the Executable

### Prerequisites for Building
- All the regular prerequisites
- PyInstaller (installed automatically with requirements.txt)

### Build Steps
1. Install all requirements:
```bash
pip install -r requirements.txt
```

2. Run the build script:
```bash
python build.py
```

3. The executable will be created in the `dist/IPTV_Player` directory

### Notes for Windows Users
- Make sure MPV is installed and the `mpv-2.dll` is in the `lib` directory
- The executable requires the MPV DLL to be present in the lib folder
- You can create a shortcut to the executable for easier access

### Notes for Linux/macOS Users
- Make sure MPV is installed system-wide
- The executable will use the system's MPV installation 