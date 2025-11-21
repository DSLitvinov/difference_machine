bl_info = {
    "name": "Difference Engine",
    "author": "Dmitry Litvinov <nopomuk@yandex.ru>",
    "version": (0, 0, 1),
    "blender": (5, 0, 0),
    "location": "View3D > UI > Difference Machine",
    "description": "Version control system for 3D models",
    "category": "3D View",
    "doc_url": "https://github.com/DSLitvinov/difference_machine",
}

from .ui import ui_main

def register():
    ui_main.register()
    # Operator classes are registered through ui_main

def unregister():
    ui_main.unregister()

if __name__ == "__main__":
    register()