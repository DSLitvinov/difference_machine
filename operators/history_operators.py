"""
Operators for commit history operations.
"""

import bpy
from bpy.types import Operator
from bpy.props import StringProperty, IntProperty
import sys
from pathlib import Path

# Add forester to path
addon_dir = Path(__file__).parent.parent
if str(addon_dir) not in sys.path:
    sys.path.insert(0, str(addon_dir))

from forester.commands import (
    find_repository,
    checkout_commit,
    get_branch_commits,
    delete_commit,
)


class DF_OT_select_commit(Operator):
    """Select a commit in the history list."""
    bl_idname = "df.select_commit"
    bl_label = "Select Commit"
    bl_description = "Select a commit"
    bl_options = {'REGISTER'}

    commit_index: IntProperty(name="Commit Index")

    def execute(self, context):
        """Execute the operator."""
        commits = context.scene.df_commits
        
        if 0 <= self.commit_index < len(commits):
            # Toggle selection
            commits[self.commit_index].is_selected = not commits[self.commit_index].is_selected
            
            # Deselect others
            for i, commit in enumerate(commits):
                if i != self.commit_index:
                    commit.is_selected = False
            
            context.scene.df_commit_props.selected_commit_index = self.commit_index if commits[self.commit_index].is_selected else -1
        
        return {'FINISHED'}


class DF_OT_checkout_commit(Operator):
    """Checkout a specific commit."""
    bl_idname = "df.checkout_commit"
    bl_label = "Checkout Commit"
    bl_description = "Checkout this commit (will discard uncommitted changes)"
    bl_options = {'REGISTER'}

    commit_hash: StringProperty(name="Commit Hash")

    def invoke(self, context, event):
        """Invoke with confirmation dialog."""
        return context.window_manager.invoke_confirm(self, event)

    def execute(self, context):
        """Execute the operator."""
        # Find repository
        blend_file = Path(bpy.data.filepath)
        if not blend_file:
            self.report({'ERROR'}, "Please save the Blender file first")
            return {'CANCELLED'}
        
        repo_path = find_repository(blend_file.parent)
        if not repo_path:
            self.report({'ERROR'}, "Not a Forester repository")
            return {'CANCELLED'}
        
        # Checkout commit
        try:
            success, error = checkout_commit(repo_path, self.commit_hash, force=True)
            
            if success:
                self.report({'INFO'}, f"Checked out commit: {self.commit_hash[:16]}...")
                # Refresh history
                bpy.ops.df.refresh_history()
                return {'FINISHED'}
            else:
                self.report({'ERROR'}, f"Failed to checkout: {error}")
                return {'CANCELLED'}
        except Exception as e:
            self.report({'ERROR'}, f"Failed to checkout commit: {str(e)}")
            import traceback
            traceback.print_exc()
            return {'CANCELLED'}


class DF_OT_delete_commit(Operator):
    """Delete a commit."""
    bl_idname = "df.delete_commit"
    bl_label = "Delete Commit"
    bl_description = "Delete this commit"
    bl_options = {'REGISTER'}

    commit_hash: StringProperty(name="Commit Hash")

    def invoke(self, context, event):
        """Invoke with confirmation dialog."""
        return context.window_manager.invoke_confirm(self, event)

    def execute(self, context):
        """Execute the operator."""
        # Find repository
        blend_file = Path(bpy.data.filepath)
        if not blend_file:
            self.report({'ERROR'}, "Please save the Blender file first")
            return {'CANCELLED'}
        
        repo_path = find_repository(blend_file.parent)
        if not repo_path:
            self.report({'ERROR'}, "Not a Forester repository")
            return {'CANCELLED'}
        
        # Delete commit
        try:
            success, error = delete_commit(repo_path, self.commit_hash, force=True)
            
            if success:
                self.report({'INFO'}, f"Deleted commit: {self.commit_hash[:16]}...")
                # Refresh history
                bpy.ops.df.refresh_history()
                return {'FINISHED'}
            else:
                self.report({'ERROR'}, f"Failed to delete commit: {error}")
                return {'CANCELLED'}
        except Exception as e:
            self.report({'ERROR'}, f"Failed to delete commit: {str(e)}")
            import traceback
            traceback.print_exc()
            return {'CANCELLED'}

