# 3D Assets Manager for Falcon BMS

A professional desktop application for managing, analyzing, and tracking 3D assets and textures in Falcon BMS. Built with modern Python and customtkinter, it provides a user-friendly interface for working with BMS model data.

<div align="center">
  <img src="https://github.com/AsafBSh/3D_Assets_Manager/blob/main/assets/F16_Logo.png?raw=true" alt="3D Assets Manager Logo" width="200"/>
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
customtkinter==5.2.1
pillow==10.1.0
pandas==2.1.3
lxml==4.9.3
loguru==0.7.2 
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
3d_assets_manager/
├── bms_manager.py     # Main application
├── data_manager.py    # Data processing
├── data_classes.py    # Data structures
├── frames.py         # UI components
├── assets/           # Images and icons
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
