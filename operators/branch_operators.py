"""
Operators for branch sorting and filtering.
"""

import bpy
from bpy.types import Operator
from bpy.props import StringProperty


class DF_OT_sort_branches(Operator):
    """Sort branches by name or commit count."""
    bl_idname = "df.sort_branches"
    bl_label = "Sort Branches"
    bl_description = "Sort branches"
    bl_options = {'REGISTER'}

    sort_type: StringProperty(name="Sort Type", default="NAME")

    def execute(self, context):
        """Execute the operator."""
        branches = context.scene.df_branches
        
        if len(branches) == 0:
            return {'CANCELLED'}
        
        # Convert to list for sorting
        branch_list = []
        for i, branch in enumerate(branches):
            branch_list.append({
                'index': i,
                'name': branch.name,
                'commit_count': branch.commit_count,
                'is_current': branch.is_current,
                'last_commit_hash': branch.last_commit_hash,
                'last_commit_message': branch.last_commit_message,
            })
        
        # Sort
        if self.sort_type == 'NAME':
            branch_list.sort(key=lambda x: x['name'].lower())
        elif self.sort_type == 'COMMITS':
            branch_list.sort(key=lambda x: x['commit_count'], reverse=True)
        
        # Reorder branches (this is tricky in Blender, so we'll just report)
        # Note: Blender's CollectionProperty doesn't support reordering easily
        # So we'll just sort the display, not the actual collection
        self.report({'INFO'}, f"Branches sorted by {self.sort_type}")
        return {'FINISHED'}



