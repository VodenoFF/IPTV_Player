# IPTV Player

A modern IPTV player application with a clean user interface built using Python and CustomTkinter.


## Features
- Modern and clean user interface with dark/light mode support
- Secure credential storage with encryption
- Category-based channel organization
- Live IPTV stream playback with MPV backend
- Customizable video playback settings
- Volume control and mute functionality
- Fullscreen support
- Remember login credentials option
- Channel favorites and search (coming soon)
- EPG support (coming soon)

## Security Features
- Secure credential storage using Fernet encryption
- Secure key generation and storage
- No plain text password storage
- Encrypted configuration files
- Secure storage location in user's AppData directory

## Prerequisites

1. Python 3.8 or higher
2. MPV player installed on your system:
   - Windows: Download and install from [MPV website](https://mpv.io/installation/)
   - Linux: `sudo apt install mpv` (Ubuntu/Debian) or `sudo dnf install mpv` (Fedora)
   - macOS: `brew install mpv` (using Homebrew)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/VodenoFF/IPTV_Player
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
- pyinstaller==6.4.0: For creating standalone executables

## Running the Application

To run from source:
```bash
python iptv_player.py
```

To run the compiled executable:
1. Download the latest release from the releases page
2. Extract the archive
3. Run IPTV_Player.exe

## Building from Source

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

## Configuration and Data Storage
- All user data is stored in the AppData directory:
  - Windows: `%APPDATA%\IPTV_Player\`
  - Linux/Mac: `~/.IPTV_Player/`
- Configuration files:
  - credentials.json: Encrypted login credentials
  - settings.json: Application settings
  - .key: Encryption key file

## Security Notes
- Never share your `.key` file
- Keep your credentials.json and .key files secure
- The application uses Fernet encryption for storing sensitive data
- API communications use your original credentials for authentication
- All sensitive data is stored in the user's AppData directory

## Troubleshooting
1. If you encounter MPV-related errors:
   - Ensure MPV is properly installed on your system
   - Check if the MPV executable is in your system PATH
   - For Windows users, ensure the MPV DLL is in the lib directory

2. If you have login issues:
   - Verify your IPTV service credentials
   - Check your internet connection
   - Ensure the IPTV service is operational

3. If "Remember me" is not working:
   - Check if the application has write permissions in AppData
   - Try running the application as administrator once
   - Check if antivirus is blocking file access

## Development

### Project Structure
```
iptv-player/
├── iptv_player.py    # Main application file
├── build.py          # Build script
├── requirements.txt  # Python dependencies
├── LICENSE          # MIT License
├── README.md        # This file
└── lib/             # MPV library files
    └── mpv-2.dll    # MPV DLL for Windows
```

### Contributing
1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments
- [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) for the modern UI framework
- [MPV](https://mpv.io/) for the powerful video playback engine
- [python-mpv](https://github.com/jaseg/python-mpv) for the MPV Python bindings 