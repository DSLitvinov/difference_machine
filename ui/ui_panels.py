import bpy
from bpy.types import Panel


class DF_PT_branch_panel(Panel):
    """Panel for Difference Machine."""
    bl_label = "Branch Manager"
    bl_idname = "DF_PT_branch_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Difference Machine"

    def draw(self, context):
        """Draw the panel UI."""
        layout = self.layout
        layout.label(text="List of branches")

class DF_PT_commit_panel(Panel):
    """Panel for Difference Machine."""
    bl_label = "Commit Manager"
    bl_idname = "DF_PT_commit_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Difference Machine"

    def draw(self, context):
        """Draw the panel UI."""
        layout = self.layout
        layout.label(text="List of commits")
