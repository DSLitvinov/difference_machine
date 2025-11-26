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
from .mesh_io import (
    load_mesh_from_commit,
    import_mesh_to_blender,
    import_node_tree_structure,
)
from .operator_helpers import get_repository_path, get_active_mesh_object
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
    bl_description = "Checkout this commit into the working directory (will discard uncommitted changes)"
    bl_options = {'REGISTER'}

    commit_hash: StringProperty(name="Commit Hash")

    def invoke(self, context, event):
        """Invoke with confirmation dialog."""
        return context.window_manager.invoke_confirm(self, event)

    def execute(self, context):
        """Execute the operator."""
        # Find repository
        repo_path, error = get_repository_path(self)
        if not repo_path:
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


class DF_OT_open_project_state(Operator):
    """Checkout commit and open project .blend from its working state."""
    bl_idname = "df.open_project_state"
    bl_label = "Open Project State from This Commit"
    bl_description = "Checkout this commit and open the corresponding .blend file from the working directory (unsaved changes will be lost)"
    bl_options = {'REGISTER'}

    commit_hash: StringProperty(name="Commit Hash")

    def invoke(self, context, event):
        """Show confirmation dialog before discarding current scene."""
        return context.window_manager.invoke_confirm(self, event)

    def execute(self, context):
        """Checkout commit and open the corresponding .blend file."""
        # Find repository
        repo_path, error = get_repository_path(self)
        if not repo_path:
            return {'CANCELLED'}
        
        # Get current .blend file (to know filename)
        blend_file = Path(bpy.data.filepath)

        # Step 1: checkout commit into working directory
        try:
            success, error = checkout_commit(repo_path, self.commit_hash, force=True)

            if not success:
                self.report({'ERROR'}, f"Failed to checkout: {error}")
                return {'CANCELLED'}
        except Exception as e:
            self.report({'ERROR'}, f"Failed to checkout commit: {str(e)}")
            import traceback
            traceback.print_exc()
            return {'CANCELLED'}

        # Step 2: locate target .blend in working directory
        working_dir = repo_path / "working"
        if not working_dir.exists():
            working_dir = repo_path

        target_blend = working_dir / blend_file.name
        if not target_blend.exists():
            self.report({'ERROR'}, f"Blend file '{blend_file.name}' not found in working directory after checkout")
            return {'CANCELLED'}

        # Step 3: open the .blend file (Blender will handle its own unsaved-changes prompt)
        try:
            bpy.ops.wm.open_mainfile(filepath=str(target_blend))
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Failed to open .blend file: {str(e)}")
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
        repo_path, error = get_repository_path(self)
        if not repo_path:
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




class DF_OT_load_mesh_version(Operator):
    """Load mesh version from commit."""
    bl_idname = "df.load_mesh_version"
    bl_label = "Load Mesh Version"
    bl_description = "Load mesh version from commit"
    bl_options = {'REGISTER', 'UNDO'}

    commit_hash: StringProperty(name="Commit Hash")
    mesh_name: StringProperty(name="Mesh Name")

    def execute(self, context):
        """Execute the operator."""
        # Find repository
        repo_path, error = get_repository_path(self)
        if not repo_path:
            return {'CANCELLED'}
        
        # Load mesh from commit
        try:
            mesh_json, material_json, mesh_storage_path = load_mesh_from_commit(repo_path, self.commit_hash, self.mesh_name)
            
            if not mesh_json:
                self.report({'ERROR'}, f"Mesh '{self.mesh_name}' not found in commit")
                return {'CANCELLED'}
            
            # Import to Blender (always create new object for Load)
            obj = import_mesh_to_blender(context, mesh_json, material_json, self.mesh_name, mode='NEW', 
                                      mesh_storage_path=mesh_storage_path)
            
            self.report({'INFO'}, f"Loaded mesh '{self.mesh_name}' from commit")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Failed to load mesh: {str(e)}")
            import traceback
            traceback.print_exc()
            return {'CANCELLED'}


class DF_OT_replace_mesh(Operator):
    """Replace current mesh with version from commit."""
    bl_idname = "df.replace_mesh"
    bl_label = "Replace Mesh"
    bl_description = "Replace current mesh with version from this commit"
    bl_options = {'REGISTER', 'UNDO'}

    commit_hash: StringProperty(name="Commit Hash")

    def invoke(self, context, event):
        """Invoke with confirmation dialog."""
        return context.window_manager.invoke_confirm(self, event)

    def execute(self, context):
        """Execute the operator."""
        # Get active mesh object
        active_obj, error = get_active_mesh_object(self)
        if not active_obj:
            return {'CANCELLED'}
        
        mesh_name = active_obj.name
        
        # Find repository
        repo_path, error = get_repository_path(self)
        if not repo_path:
            return {'CANCELLED'}
        
        # Load mesh from commit
        try:
            mesh_json, material_json, mesh_storage_path = load_mesh_from_commit(repo_path, self.commit_hash, mesh_name)
            
            if not mesh_json:
                self.report({'ERROR'}, f"Mesh '{mesh_name}' not found in commit")
                return {'CANCELLED'}
            
            # Import to Blender (replace mode)
            import_mesh_to_blender(context, mesh_json, material_json, mesh_name, mode='SELECTED', 
                                 mesh_storage_path=mesh_storage_path)
            
            self.report({'INFO'}, f"Replaced mesh '{mesh_name}' with version from commit")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Failed to replace mesh: {str(e)}")
            import traceback
            traceback.print_exc()
            return {'CANCELLED'}


class DF_OT_compare_mesh(Operator):
    """Compare current mesh with version from commit."""
    bl_idname = "df.compare_mesh"
    bl_label = "Compare Mesh"
    bl_description = "Compare current mesh with version from this commit"
    bl_options = {'REGISTER', 'UNDO'}

    commit_hash: StringProperty(name="Commit Hash")
    offset_distance: bpy.props.FloatProperty(
        name="Offset Distance",
        description="Distance to offset the comparison version",
        default=2.0,
        min=0.0,
        max=10.0
    )

    def execute(self, context):
        """Execute the operator."""
        # Get active mesh object
        active_obj, error = get_active_mesh_object(self)
        if not active_obj:
            return {'CANCELLED'}
        
        mesh_name = active_obj.name
        original_obj = active_obj
        
        # Check if comparison is already active
        scene = context.scene
        comparison_obj_name = getattr(scene, 'df_comparison_object_name', None)
        if comparison_obj_name and comparison_obj_name in bpy.data.objects:
            # Toggle OFF: Remove comparison object
            comparison_obj = bpy.data.objects[comparison_obj_name]
            bpy.data.objects.remove(comparison_obj, do_unlink=True)
            scene.df_comparison_object_name = ""
            scene.df_comparison_active = False
            scene.df_comparison_commit_hash = ""
            scene.df_original_object_name = ""
            self.report({'INFO'}, "Comparison mode disabled")
            return {'FINISHED'}
        
        # Find repository
        repo_path, error = get_repository_path(self)
        if not repo_path:
            return {'CANCELLED'}
        
        # Load mesh from commit
        try:
            mesh_json, material_json, mesh_storage_path = load_mesh_from_commit(repo_path, self.commit_hash, mesh_name)
            
            if not mesh_json:
                self.report({'ERROR'}, f"Mesh '{mesh_name}' not found in commit")
                return {'CANCELLED'}
            
            # Import to Blender (new object for comparison)
            comparison_obj = import_mesh_to_blender(
                context, mesh_json, material_json, 
                f"{mesh_name}_compare", mode='NEW',
                mesh_storage_path=mesh_storage_path
            )
            
            # Offset comparison object
            comparison_obj.location.x = original_obj.location.x + self.offset_distance
            comparison_obj.location.y = original_obj.location.y
            comparison_obj.location.z = original_obj.location.z
            
            # Store comparison state
            scene.df_comparison_object_name = comparison_obj.name
            scene.df_comparison_active = True
            scene.df_original_object_name = original_obj.name
            scene.df_comparison_commit_hash = self.commit_hash
            
            # Restore focus to original object
            for obj in context.selected_objects:
                obj.select_set(False)
            original_obj.select_set(True)
            context.view_layer.objects.active = original_obj
            
            self.report({'INFO'}, f"Comparison mode enabled (offset +{self.offset_distance})")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Failed to compare mesh: {str(e)}")
            import traceback
            traceback.print_exc()
            return {'CANCELLED'}

