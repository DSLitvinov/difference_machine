bl_info = {
    "name": "Difference Engine (Alfa).Ammonitida",
    "author": "Dmitry Litvinov <nopomuk@yandex.ru>",
    "version": (0, 5, 0),
    "blender": (4, 0, 0),
    "location": "View3D > UI > Difference Machine",
    "description": "Version control system for 3D models",
    "category": "3D View",
    "doc_url": "https://github.com/DSLitvinov/difference_machine",
}

import logging
from .ui import ui_main
from .properties import properties
from . import preferences
from .utils.logging_config import setup_logging

def register():
    # Setup logging
    setup_logging(log_level=logging.INFO)
    
    preferences.register()
    properties.register()
    ui_main.register()

def unregister():
    ui_main.unregister()
    properties.unregister()
    preferences.unregister()

if __name__ == "__main__":
    register()