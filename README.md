# IPTV Player for XUI
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![GitHub Release](https://img.shields.io/github/v/release/VodenoFF/IPTV_Player?include_prereleases)](https://github.com/VodenoFF/IPTV_Player/releases)
[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/downloads/)



## Table of Contents
- [Overview](#overview)
- [Key Features](#key-features)
- [Security Implementation](#security-implementation)
- [System Requirements](#system-requirements)
- [Installation Guide](#installation-guide)
- [Dependencies](#dependencies)
- [Build Instructions](#build-instructions)
- [User Guide](#user-guide)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)
- [Architecture](#architecture)
- [Contributing](#contributing)
- [License](#license)
- [Acknowledgments](#acknowledgments)
- [Support](#support)
- [About](#about)

## Overview

IPTV Player for XUI is a sophisticated, lightweight application designed to deliver a premium viewing experience for XUI IPTV content providers. Built with Python and CustomTkinter, it combines clean architecture with an intuitive user interface to make streaming effortless and enjoyable.

## Key Features

- **Elegant User Interface**: Modern, responsive design with customizable dark/light themes for extended viewing comfort
- **XUI IPTV Optimization**: Engineered specifically for XUI IPTV test providers with native API integration
- **Enterprise-grade Security**: Advanced credential encryption system to protect user authentication data
- **Intuitive Content Navigation**: Category-based channel organization with hierarchical display
- **High-performance Playback**: Optimized streaming with MPV backend for minimal buffering and maximum quality
- **Customizable Experience**: Fine-tune video and playback settings to match your viewing preferences
- **Comprehensive Audio Controls**: Advanced volume management with intuitive interface elements
- **Enhanced Viewing Modes**: Seamless fullscreen implementation for distraction-free viewing
- **Streamlined Authentication**: Secure credential storage with "Remember me" functionality
- **Planned Enhancements**:
  - Intelligent favorites system with personalized recommendations
  - Advanced search capability with filtering and sorting options
  - Comprehensive EPG (Electronic Program Guide) integration with alerts and reminders

## Security Implementation

- Industry-standard Fernet encryption for credential protection
- Sophisticated key generation with secure storage architecture
- Zero plain-text password retention throughout the application lifecycle
- Multi-layered encrypted configuration system
- Isolated secure storage in user-specific protected directories

## System Requirements

1. **Runtime Environment**: Python 3.8 or newer (for source installations)
2. **Media Engine**: MPV player installed on your system:
   - **Windows**: Official installation from [MPV website](https://mpv.io/installation/)
   - **Linux**: Package manager installation: `sudo apt install mpv` (Debian-based) or `sudo dnf install mpv` (Fedora-based)
   - **macOS**: Homebrew installation: `brew install mpv`

## Installation Guide

### Option 1: Binary Installation (Recommended)

1. Download the latest release package from the [official Releases page](https://github.com/VodenoFF/IPTV_Player/releases)
2. Extract the distribution archive to your preferred installation location
3. Launch the application by executing `IPTV_Player.exe`

### Option 2: Source Installation

1. Clone the repository to your local environment:
```bash
git clone https://github.com/VodenoFF/IPTV_Player
cd IPTV_Player
```

2. Install all required dependencies:
```bash
pip install -r requirements.txt
```

3. Launch the application:
```bash
python iptv_player.py
```

## Dependencies

- **customtkinter==5.2.2**: Advanced UI framework for the application interface
- **python-mpv==1.0.5**: High-performance MPV integration for superior video playback
- **requests==2.31.0**: Robust HTTP client for reliable API communication
- **pillow==10.2.0**: Comprehensive image processing for UI elements and channel icons
- **cryptography==42.0.2**: Enterprise-grade encryption for credential management
- **pyinstaller==6.4.0**: Professional packaging system for executable creation

## Build Instructions

### Prerequisites
- All system requirements listed above
- PyInstaller package (automatically included in requirements.txt)

### Process
1. Install the complete dependency set:
```bash
pip install -r requirements.txt
```

2. Execute the build script:
```bash
python build.py
```

3. Locate the compiled application in the `dist/IPTV_Player` directory

## User Guide

### Getting Started
1. Launch the IPTV Player application
2. Enter your XUI IPTV provider credentials in the secure login form
3. Enable "Remember me" for convenient future access (credentials are securely encrypted)
4. Navigate content categories using the sidebar navigation
5. Select desired channels to begin media playback
6. Utilize on-screen controls or keyboard shortcuts for enhanced viewing control

### Keyboard Command Reference
| Key | Function |
|-----|----------|
| **Space** | Toggle Play/Pause |
| **F** | Toggle Fullscreen Mode |
| **M** | Toggle Audio Mute |
| **Up/Down** | Adjust Volume Level |
| **Left/Right** | Navigate Between Channels |
| **Esc** | Exit Fullscreen Mode |

## Configuration

### Data Storage Architecture
- All user configuration is securely stored in the system's protected application data location:
  - **Windows**: `%APPDATA%\IPTV_Player\`
  - **Linux/macOS**: `~/.IPTV_Player/`

### Configuration Files
- **credentials.json**: Encrypted authentication data
- **settings.json**: User preferences and application configuration
- **[hidden].key**: Encryption key file (system-protected)

## Troubleshooting

### Media Playback Issues
- Verify MPV is correctly installed and accessible from system PATH
- Confirm the MPV DLL is present in the application's lib directory (Windows)
- Check system codec availability for the stream format

### Authentication Problems
- Validate XUI IPTV provider credentials accuracy
- Verify network connectivity to authentication servers
- Confirm provider service status and subscription validity

### Credential Storage Issues
- Ensure application has appropriate write permissions for configuration directory
- Try elevated privileges for initial configuration (Windows)
- Verify security software is not blocking application file access

### Stream Performance Concerns
- Test network connection stability and bandwidth
- Verify stream availability from content provider
- Confirm subscription status and access rights

## Architecture

### Project Structure
```
IPTV_Player/
├── iptv_player.py    # Application entry point and core logic
├── build.py          # Distribution build system
├── requirements.txt  # Dependency specification
├── LICENSE           # MIT License documentation
├── README.md         # Project documentation
└── lib/              # External libraries and dependencies
    └── mpv-2.dll     # MPV integration library for Windows
```

## Contributing

We welcome contributions from the community to enhance IPTV Player functionality.

1. Fork the official repository
2. Create a focused feature branch (`git checkout -b feature/enhancement-name`)
3. Implement your changes with appropriate tests
4. Commit with clear, descriptive messages (`git commit -m 'Add new feature: enhancement description'`)
5. Push to your branch (`git push origin feature/enhancement-name`)
6. Submit a detailed Pull Request for review


## License

This project is distributed under the terms of the MIT License - see the [LICENSE](LICENSE) file for complete details.

## Acknowledgments

- [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) for the sophisticated UI framework
- [MPV](https://mpv.io/) for the industry-leading media playback engine
- [python-mpv](https://github.com/jaseg/python-mpv) for robust Python integration with MPV

## Support

For assistance with installation or usage:
- Submit issues on our [GitHub Issue Tracker](https://github.com/VodenoFF/IPTV_Player/issues)
- Join our community discussions on [GitHub Discussions](https://github.com/VodenoFF/IPTV_Player/discussions)

## About

Developed and maintained by [VodenoFF](https://github.com/VodenoFF) 