"""
Operators for commit operations in Difference Machine.
"""

import bpy
from bpy.types import Operator
from bpy.props import StringProperty
from pathlib import Path

from ..forester.commands import (
    find_repository,
    init_repository,
    create_commit,
    create_mesh_only_commit,
    auto_compress_mesh_commits,
    create_branch,
    get_branch_commits,
    list_branches,
    switch_branch,
    delete_branch,
)
from ..forester.core.refs import get_branch_ref, get_current_branch
from ..forester.core.metadata import Metadata
from .mesh_io import export_mesh_to_json
from .operator_helpers import get_repository_path, process_meshes_sequentially


class DF_OT_create_project_commit(Operator):
    """Create a full project commit."""
    bl_idname = "df.create_project_commit"
    bl_label = "Create Project Commit"
    bl_description = "Create a commit of the entire working directory"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        """Execute the operator."""
        # Find repository
        if not bpy.data.filepath:
            self.report({'ERROR'}, "Please save the Blender file first")
            return {'CANCELLED'}
        
        blend_file = Path(bpy.data.filepath)
        # Determine project root (directory containing .blend file)
        project_root = blend_file.parent
        
        # Check if repository exists
        repo_path = find_repository(project_root)
        if not repo_path:
            # Initialize repository
            try:
                init_repository(project_root)
                repo_path = project_root
                self.report({'INFO'}, "Repository initialized")
            except Exception as e:
                self.report({'ERROR'}, f"Failed to initialize repository: {str(e)}")
                return {'CANCELLED'}
        
        # Check if branches exist
        branches = list_branches(repo_path)
        if len(branches) == 0:
            self.report({'ERROR'}, 
                "No branches found. Please create a branch first.\n"
                "Go to Branch Management panel and click 'Create New Branch'.")
            return {'CANCELLED'}
        
        # Get current branch from repository
        branch_name = get_current_branch(repo_path) or "main"
        
        # Get properties
        props = context.scene.df_commit_props
        
        # Ensure branch exists (create if needed)
        branch_ref = get_branch_ref(repo_path, branch_name)
        if branch_ref is None:
            # Branch doesn't exist, create it
            try:
                create_branch(repo_path, branch_name)
                # Update metadata to set current branch
                metadata_path = repo_path / ".DFM" / "metadata.json"
                if metadata_path.exists():
                    metadata = Metadata(metadata_path)
                    metadata.load()
                    metadata.current_branch = branch_name
                    metadata.save()
                self.report({'INFO'}, f"Branch '{branch_name}' created")
            except ValueError:
                # Branch might already exist (race condition), that's okay
                pass
        
        # Get author from preferences (always use settings, fallback to "Unknown" if empty)
        from .operator_helpers import get_addon_preferences
        prefs = get_addon_preferences(context)
        author = prefs.default_author if prefs.default_author else "Unknown"
        
        # Create commit
        try:
            commit_hash = create_commit(
                repo_path=repo_path,
                message=props.message or "No message",
                author=author
            )
            
            if commit_hash:
                self.report({'INFO'}, f"Commit created: {commit_hash[:16]}...")
                return {'FINISHED'}
            else:
                self.report({'INFO'}, "No changes to commit")
                return {'CANCELLED'}
        except Exception as e:
            self.report({'ERROR'}, f"Failed to create commit: {str(e)}")
            import traceback
            traceback.print_exc()
            return {'CANCELLED'}


class DF_OT_create_mesh_commit(Operator):
    """Create a mesh-only commit from selected objects."""
    bl_idname = "df.create_mesh_commit"
    bl_label = "Create Mesh Commit"
    bl_description = "Create a commit only for selected mesh objects"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        """Execute the operator."""
        # Get selected mesh objects
        selected_objects = [obj for obj in context.selected_objects if obj.type == 'MESH']
        
        if not selected_objects:
            self.report({'ERROR'}, "No mesh objects selected")
            return {'CANCELLED'}
        
        # Find repository
        if not bpy.data.filepath:
            self.report({'ERROR'}, "Please save the Blender file first")
            return {'CANCELLED'}
        
        blend_file = Path(bpy.data.filepath)
        # Determine project root
        project_root = blend_file.parent
        
        # Check if repository exists
        repo_path = find_repository(project_root)
        if not repo_path:
            # Initialize repository
            try:
                init_repository(project_root)
                repo_path = project_root
                self.report({'INFO'}, "Repository initialized")
            except Exception as e:
                self.report({'ERROR'}, f"Failed to initialize repository: {str(e)}")
                return {'CANCELLED'}
        
        # Check if branches exist
        branches = list_branches(repo_path)
        if len(branches) == 0:
            self.report({'ERROR'}, 
                "No branches found. Please create a branch first.\n"
                "Go to Branch Management panel and click 'Create New Branch'.")
            return {'CANCELLED'}
        
        # Get current branch from repository
        branch_name = get_current_branch(repo_path) or "main"
        props = context.scene.df_commit_props
        export_options = props.get_export_options()
        
        # Get author from preferences (always use settings, fallback to "Unknown" if empty)
        from .operator_helpers import get_addon_preferences
        prefs = get_addon_preferences(context)
        default_author = prefs.default_author if prefs.default_author else "Unknown"
        
        # Ensure branch exists (create if needed)
        branch_ref = get_branch_ref(repo_path, branch_name)
        if branch_ref is None:
            # Branch doesn't exist, create it
            try:
                create_branch(repo_path, branch_name)
                # Update metadata to set current branch
                metadata_path = repo_path / ".DFM" / "metadata.json"
                if metadata_path.exists():
                    metadata = Metadata(metadata_path)
                    metadata.load()
                    metadata.current_branch = branch_name
                    metadata.save()
                self.report({'INFO'}, f"Branch '{branch_name}' created")
            except ValueError:
                # Branch might already exist (race condition), that's okay
                pass
        
        # Export meshes sequentially using single-mesh export function from mesh_io
        # Each mesh is processed one at a time to avoid conflicts and ensure proper error handling
        mesh_data_list = []
        for obj in selected_objects:
            try:
                # Use single-mesh export function from mesh_io.py
                mesh_data = export_mesh_to_json(obj, export_options)
                mesh_data['mesh_name'] = obj.name
                mesh_data_list.append(mesh_data)
            except Exception as e:
                self.report({'WARNING'}, f"Failed to export {obj.name}: {str(e)}")
                continue
        
        if not mesh_data_list:
            self.report({'ERROR'}, "No meshes could be exported")
            return {'CANCELLED'}
        
        # Create mesh-only commit
        try:
            commit_hash = create_mesh_only_commit(
                repo_path=repo_path,
                mesh_data_list=mesh_data_list,
                export_options=export_options,
                message=props.message or "No message",
                author=default_author
            )
            
            if commit_hash:
                self.report({'INFO'}, f"Mesh commit created: {commit_hash[:16]}...")
                
                # Auto-compress if enabled
                if props.auto_compress:
                    mesh_names = [data['mesh_name'] for data in mesh_data_list]
                    deleted = auto_compress_mesh_commits(
                        repo_path=repo_path,
                        mesh_names=mesh_names,
                        keep_last_n=prefs.auto_compress_keep_last_n
                    )
                    if deleted > 0:
                        self.report({'INFO'}, f"Compressed {deleted} old commits")
                
                return {'FINISHED'}
            else:
                self.report({'INFO'}, "No changes to commit")
                return {'CANCELLED'}
        except Exception as e:
            self.report({'ERROR'}, f"Failed to create commit: {str(e)}")
            import traceback
            traceback.print_exc()
            return {'CANCELLED'}


class DF_OT_refresh_history(Operator):
    """Refresh commit history."""
    bl_idname = "df.refresh_history"
    bl_label = "Refresh History"
    bl_description = "Refresh the commit history list"
    bl_options = {'REGISTER'}

    def execute(self, context):
        """Execute the operator."""
        # Find repository
        blend_file = Path(bpy.data.filepath)
        if not blend_file:
            self.report({'ERROR'}, "Please save the Blender file first")
            return {'CANCELLED'}
        
        repo_path = find_repository(blend_file.parent)
        if not repo_path:
            # Clear commits list
            context.scene.df_commits.clear()
            return {'FINISHED'}
        
        # Get current branch from repository
        branch_name = get_current_branch(repo_path) or "main"
        
        # Get commits from forester
        try:
            commits_data = get_branch_commits(repo_path, branch_name)
            
            # Clear existing list
            context.scene.df_commits.clear()
            
            # Add commits to list (newest first)
            for commit_data in reversed(commits_data):
                commit_item = context.scene.df_commits.add()
                commit_item.hash = commit_data['hash']
                commit_item.message = commit_data.get('message', 'No message')
                commit_item.author = commit_data.get('author', 'Unknown')
                commit_item.timestamp = commit_data['timestamp']
                commit_item.commit_type = commit_data.get('commit_type', 'project')
                
                # Format selected mesh names
                selected_names = commit_data.get('selected_mesh_names', [])
                if isinstance(selected_names, str):
                    import json
                    try:
                        selected_names = json.loads(selected_names)
                    except:
                        selected_names = []
                if selected_names:
                    commit_item.selected_mesh_names = ", ".join(selected_names)
            
            self.report({'INFO'}, f"Loaded {len(commits_data)} commits")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Failed to load commits: {str(e)}")
            import traceback
            traceback.print_exc()
            return {'CANCELLED'}


class DF_OT_refresh_branches(Operator):
    """Refresh branch list."""
    bl_idname = "df.refresh_branches"
    bl_label = "Refresh Branches"
    bl_description = "Refresh the branch list"
    bl_options = {'REGISTER'}

    def execute(self, context):
        """Execute the operator."""
        # Find repository
        blend_file = Path(bpy.data.filepath)
        if not blend_file:
            self.report({'ERROR'}, "Please save the Blender file first")
            return {'CANCELLED'}
        
        repo_path = find_repository(blend_file.parent)
        if not repo_path:
            # Clear branches list
            context.scene.df_branches.clear()
            return {'FINISHED'}
        
        # Get branches from forester
        try:
            branches_data = list_branches(repo_path)
            current_branch = get_current_branch(repo_path)
            
            # Clear existing list
            context.scene.df_branches.clear()
            
            # Add branches to list
            for branch_data in branches_data:
                branch_item = context.scene.df_branches.add()
                branch_item.name = branch_data['name']
                branch_item.is_current = branch_data.get('current', False) or (branch_data['name'] == current_branch)
                
                # Get commit count and last commit
                commits = get_branch_commits(repo_path, branch_data['name'])
                branch_item.commit_count = len(commits)
                
                if commits:
                    last_commit = commits[-1]  # Last commit (newest)
                    branch_item.last_commit_hash = last_commit.get('hash', '')
                    branch_item.last_commit_message = last_commit.get('message', 'No message')
                else:
                    branch_item.last_commit_hash = ''
                    branch_item.last_commit_message = 'No commits'
            
            self.report({'INFO'}, f"Loaded {len(branches_data)} branches")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Failed to load branches: {str(e)}")
            import traceback
            traceback.print_exc()
            return {'CANCELLED'}


class DF_OT_create_branch(Operator):
    """Create a new branch."""
    bl_idname = "df.create_branch"
    bl_label = "Create Branch"
    bl_description = "Create a new branch"
    bl_options = {'REGISTER'}

    branch_name: StringProperty(
        name="Branch Name",
        description="Name of the new branch",
        default="",
    )

    def invoke(self, context, event):
        """Invoke the operator (show dialog)."""
        # Check if file is saved and repository exists
        from .operator_helpers import check_repository_state
        file_saved, repo_exists, _, error_msg = check_repository_state(context)
        
        if not file_saved:
            self.report({'ERROR'}, error_msg or "Please save the Blender file first")
            return {'CANCELLED'}
        
        if not repo_exists:
            # Check if .DFM directory exists
            if bpy.data.filepath:
                blend_file = Path(bpy.data.filepath)
                dfm_dir = blend_file.parent / ".DFM"
                if not dfm_dir.exists():
                    self.report({'ERROR'}, 
                        "Repository not initialized.\n"
                        "Please create a project folder and save the Blender file in it.\n"
                        "Then the repository will be initialized automatically.")
                    return {'CANCELLED'}
            
            self.report({'ERROR'}, error_msg or "Repository not found")
            return {'CANCELLED'}
        
        return context.window_manager.invoke_props_dialog(self)

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
        
        if not self.branch_name:
            self.report({'ERROR'}, "Branch name cannot be empty")
            return {'CANCELLED'}
        
        try:
            create_branch(repo_path, self.branch_name)
            self.report({'INFO'}, f"Branch '{self.branch_name}' created")
            # Refresh branches list
            bpy.ops.df.refresh_branches()
            return {'FINISHED'}
        except ValueError as e:
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}
        except Exception as e:
            self.report({'ERROR'}, f"Failed to create branch: {str(e)}")
            return {'CANCELLED'}


class DF_OT_switch_branch(Operator):
    """Switch to a different branch."""
    bl_idname = "df.switch_branch"
    bl_label = "Switch Branch"
    bl_description = "Switch to a different branch"
    bl_options = {'REGISTER'}

    branch_name: StringProperty(name="Branch Name", default="")

    def invoke(self, context, event):
        """Invoke the operator - use selected branch if no name provided."""
        # If branch_name not provided, use selected branch from list
        if not self.branch_name:
            branches = context.scene.df_branches
            if (branches and 
                hasattr(context.scene, 'df_branch_list_index') and
                context.scene.df_branch_list_index >= 0 and 
                context.scene.df_branch_list_index < len(branches)):
                self.branch_name = branches[context.scene.df_branch_list_index].name
            else:
                self.report({'ERROR'}, "No branch selected")
                return {'CANCELLED'}
        
        return self.execute(context)

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
        
        if not self.branch_name:
            self.report({'ERROR'}, "Branch name not specified")
            return {'CANCELLED'}
        
        try:
            switch_branch(repo_path, self.branch_name)
            
            # Update props
            context.scene.df_commit_props.branch = self.branch_name
            
            self.report({'INFO'}, f"Switched to branch '{self.branch_name}'")
            # Refresh branches and history
            bpy.ops.df.refresh_branches()
            bpy.ops.df.refresh_history()
            return {'FINISHED'}
        except ValueError as e:
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}
        except Exception as e:
            self.report({'ERROR'}, f"Failed to switch branch: {str(e)}")
            return {'CANCELLED'}


class DF_OT_delete_branch(Operator):
    """Delete a branch."""
    bl_idname = "df.delete_branch"
    bl_label = "Delete Branch"
    bl_description = "Delete a branch"
    bl_options = {'REGISTER'}

    branch_name: StringProperty(name="Branch Name")

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
        
        # Check if this is the last branch
        branches = list_branches(repo_path)
        if len(branches) <= 1:
            self.report({'ERROR'}, "Cannot delete the last branch")
            return {'CANCELLED'}
        
        # Check if this is the current branch
        current_branch = get_current_branch(repo_path)
        if self.branch_name == current_branch:
            self.report({'ERROR'}, f"Cannot delete current branch '{self.branch_name}'. Switch to another branch first.")
            return {'CANCELLED'}
        
        try:
            delete_branch(repo_path, self.branch_name, force=False)
            self.report({'INFO'}, f"Branch '{self.branch_name}' deleted")
            # Refresh branches list
            bpy.ops.df.refresh_branches()
            return {'FINISHED'}
        except ValueError as e:
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}
        except Exception as e:
            self.report({'ERROR'}, f"Failed to delete branch: {str(e)}")
            return {'CANCELLED'}

