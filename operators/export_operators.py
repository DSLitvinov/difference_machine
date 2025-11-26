"""
Operators for export options toggling.
"""

import bpy
from bpy.types import Operator
from bpy.props import StringProperty, BoolProperty


class DF_OT_toggle_export_component(Operator):
    """Toggle export component on/off."""
    bl_idname = "df.toggle_export_component"
    bl_label = "Toggle Export Component"
    bl_description = "Toggle export component"
    bl_options = {'REGISTER', 'INTERNAL'}

    component: StringProperty(name="Component")
    toggle: BoolProperty(name="Toggle")

    def execute(self, context):
        """Execute the operator."""
        props = context.scene.df_commit_props
        
        if self.component == 'geometry':
            props.export_geometry = self.toggle
        elif self.component == 'materials':
            props.export_materials = self.toggle
        elif self.component == 'transform':
            props.export_transform = self.toggle
        elif self.component == 'uv':
            props.export_uv = self.toggle
        
        return {'FINISHED'}



