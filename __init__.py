bl_info = {
    "name": "Difference Engine (Alfa).Ammonitida",
    "author": "Dmitry Litvinov <nopomuk@yandex.ru>",
    "version": (0, 5, 0),
    "blender": (4, 5, 0),
    "location": "View3D > UI > Difference Machine",
    "description": "Version control system for 3D models",
    "category": "3D View",
    "doc_url": "https://github.com/DSLitvinov/difference_machine",
}

from .ui import ui_main
from .properties import properties

def register():
    properties.register()
    ui_main.register()

def unregister():
    ui_main.unregister()
    properties.unregister()

if __name__ == "__main__":
    register()