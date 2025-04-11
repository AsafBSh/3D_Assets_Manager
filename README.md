# 3D Assets Manager for Falcon BMS

A professional desktop application for managing, analyzing, and tracking 3D assets and textures in Falcon BMS. Built with modern Python and customtkinter, it provides a user-friendly interface for working with BMS model data.

<div align="center">
  <img src="assets/F16_logo.png" alt="3D Assets Manager Logo" width="200"/>
</div>

## 🌟 Key Features

- **3D Assets Analysis**
  - Browse and analyze models with their variants
  - Track BML versions and model states
  - View detailed model information and relationships
  - Filter and search by type, name, or CT number

- **Texture Management**
  - Track texture usage across models
  - Identify high-resolution and PBR textures
  - Monitor texture availability and status
  - View texture relationships with parent models

- **Advanced Features**
  - PBR texture analysis and validation
  - Unused texture identification
  - Parent model tracking and analysis
  - Cockpit model support

## 🚀 Getting Started

### Prerequisites

- Python 3.8 or higher
- Falcon BMS installation with:
  - Falcon4_CT.xml
  - ParentsDetailsReport.txt
  - KoreaObj and KoreaObj_HiRes folders

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/f4bms-3d-assets-manager.git
cd f4bms-3d-assets-manager
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# Unix/MacOS:
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## 💻 Usage

1. Launch the application:
```bash
python bms_manager.py
```

2. Select your Falcon4_CT.xml file using the Browse button
3. Navigate through the sections:
   - **Dashboard**: Overview and quick access
   - **3D Assets**: Model analysis and tracking
   - **Parents**: Parent model relationships
   - **Textures**: Texture usage and status
   - **PBR Textures**: PBR material analysis
   - **Unused Textures**: Identify unused resources

## 📁 Project Structure

```
f4bms-3d-assets-manager/
├── bms_manager.py     # Main application
├── data_manager.py    # Data processing
├── data_classes.py    # Data structures
├── frames.py         # UI components
├── assets/           # Images and icons
├── docs/            # Documentation
└── logs/            # Application logs
```

## 🔧 Development

The application is built with:
- customtkinter for modern UI
- ttk for tree views
- PIL for image processing
- loguru for logging

### Logging

- All operations are logged to `logs/bms_manager.log`
- Automatic log rotation at 10MB
- Comprehensive error tracking

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see [LICENSE](LICENSE) for details.

## 🙏 Acknowledgments

- Falcon BMS development team
- Python customtkinter community
- All contributors and users

## 📞 Support

For support, please:
- Open an issue in the GitHub repository
- Check the documentation in the docs folder
- Review existing issues before creating new ones 
