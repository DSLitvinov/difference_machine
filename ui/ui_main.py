"""
Main UI module for Difference Machine add-on.
Contains panels and menus registration.
"""
import bpy
from .ui_panels import (
    DF_PT_branch_panel,
    DF_PT_commit_panel,
)

# Classes list for registration
classes = [
    DF_PT_branch_panel,
    DF_PT_commit_panel,
]


def register():
    """Register UI classes and properties"""
    try:
        # Register UI classes
        for cls in classes:
            bpy.utils.register_class(cls)
    except Exception as e:
        print(f"Error registering UI classes: {e}")
        raise


def unregister():
    try:
        # Unregister UI classes
        for cls in reversed(classes):
            bpy.utils.unregister_class(cls)
    except Exception as e:
        print(f"Error unregistering UI classes: {e}")
        raise
