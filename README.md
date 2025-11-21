# Difference Machine

Version control system for 3D models - Blender add-on.

## Description

Difference Machine is a Blender add-on that provides version control functionality for 3D models.

## Installation

1. Download or clone this repository
2. In Blender, go to `Edit > Preferences > Extensions`
3. Click `Install...` and select the add-on folder
4. Enable the add-on in the extensions list

## Usage

After installation, you can access Difference Machine from the 3D Viewport sidebar (N-panel) under the "Difference Machine" tab.

## Structure

```
difference_machine/
├── __init__.py              # Main entry point
├── blender_manifest.toml    # Blender 4.5+ manifest
├── operators/               # Operators (bpy.types.Operator classes)
├── ui/                      # User interface (panels, menus)
├── properties/              # Custom properties
├── utils/                   # Helper functions
└── data/                    # Static data (icons, presets)
```

## License

GPL-3.0-or-later

## Author

Dmitry Litvinov <nopomuk@yandex.ru>

