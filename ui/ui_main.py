"""
Main UI module for Difference Machine add-on.
Contains panels and menus registration.
"""

import bpy
from bpy.types import Panel


class DIFFERENCE_MACHINE_PT_main_panel(Panel):
    """Main panel for Difference Machine."""
    bl_label = "Difference Machine"
    bl_idname = "DIFFERENCE_MACHINE_PT_main_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Difference Machine"

    def draw(self, context):
        """Draw the panel UI."""
        layout = self.layout
        layout.label(text="Version control system for 3D models")


def register():
    """Register UI classes."""
    bpy.utils.register_class(DIFFERENCE_MACHINE_PT_main_panel)


def unregister():
    """Unregister UI classes."""
    bpy.utils.unregister_class(DIFFERENCE_MACHINE_PT_main_panel)

