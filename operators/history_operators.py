"""
Operators for commit history operations.
"""

import bpy
import logging
from bpy.types import Operator
from bpy.props import StringProperty, IntProperty
from pathlib import Path

from ..forester.commands import (
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
from .operator_helpers import (
    get_repository_path,
    get_active_mesh_object,
    cleanup_old_preview_temp,
    cleanup_old_compare_temp,
    copy_project_textures_for_compare,
)
logger = logging.getLogger(__name__)
class DF_OT_select_commit(Operator):
    """Select a commit in the history list."""
    bl_idname = "df.select_commit"
    bl_label = "Select Commit"
    bl_description = "Select a commit and load it to temporary folder"
    bl_options = {'REGISTER'}

    commit_index: IntProperty(name="Commit Index")

    def execute(self, context):
        """Execute the operator."""
        commits = context.scene.df_commits
        
        if 0 <= self.commit_index < len(commits):
            commit = commits[self.commit_index]
            
            # Toggle selection
            commit.is_selected = not commit.is_selected
            
            # Deselect others
            for i, c in enumerate(commits):
                if i != self.commit_index:
                    c.is_selected = False
            
            context.scene.df_commit_props.selected_commit_index = self.commit_index if commit.is_selected else -1
            
            # Load commit to temporary folder (like Compare does) for project commits
            # Load when selected OR when index changes (for UIList selection)
            if commit.commit_type == "project":
                try:
                    repo_path, error = get_repository_path(self)
                    if repo_path:
                        # Load commit to temporary folder
                        self._load_commit_to_temp(repo_path, commit.hash, context)
                except Exception as e:
                    logger.warning(f"Failed to load commit to temp folder: {e}", exc_info=True)
            elif not commit.is_selected and commit.commit_type != "project":
                # Clean up temp folder when deselecting non-project commits
                self._cleanup_preview_temp(context)
        
        return {'FINISHED'}
    
    def _load_commit_to_temp(self, repo_path: Path, commit_hash: str, context):
        """Load commit to temporary folder (similar to compare_project)."""
        import shutil
        from ..forester.core.database import ForesterDB
        from ..forester.core.storage import ObjectStorage
        from ..forester.models.commit import Commit
        from ..forester.commands.checkout import restore_files_from_tree, restore_meshes_from_commit
        
        dfm_dir = repo_path / ".DFM"
        temp_dir = dfm_dir / "preview_temp"
        temp_dir.mkdir(exist_ok=True)
        
        # Clean up previous preview if exists
        prev_temp_dir = getattr(context.scene, 'df_preview_temp_dir', '')
        if prev_temp_dir:
            prev_path = Path(prev_temp_dir)
            if prev_path.exists() and prev_path != dfm_dir:
                try:
                    shutil.rmtree(prev_path)
                except Exception:
                    pass
        
        # Create unique temp directory for this commit
        temp_working_dir = temp_dir / f"commit_{commit_hash[:16]}"
        
        # Clean up if exists
        if temp_working_dir.exists():
            shutil.rmtree(temp_working_dir)
        temp_working_dir.mkdir(parents=True)
        
        # Clean up all other old preview_temp directories (keep current one)
        cleanup_old_preview_temp(repo_path, keep_current=str(temp_working_dir))
        
        db_path = dfm_dir / "forester.db"
        with ForesterDB(db_path) as db:
            storage = ObjectStorage(dfm_dir)
            commit = Commit.from_storage(commit_hash, db, storage)
            
            if not commit:
                return
            
            # Get tree from commit
            tree = commit.get_tree(db, storage)
            if not tree:
                return
            
            # Restore files from tree
            restore_files_from_tree(tree, temp_working_dir, storage, db)
            
            # Restore meshes from commit
            restore_meshes_from_commit(commit, temp_working_dir, storage, dfm_dir)
            
            # Store temp directory path in scene
            context.scene.df_preview_temp_dir = str(temp_working_dir)
            context.scene.df_preview_commit_hash = commit_hash
    
    def _cleanup_preview_temp(self, context):
        """Clean up preview temporary directory."""
        import shutil
        prev_temp_dir = getattr(context.scene, 'df_preview_temp_dir', '')
        if prev_temp_dir:
            prev_path = Path(prev_temp_dir)
            if prev_path.exists():
                try:
                    shutil.rmtree(prev_path)
                except Exception:
                    pass
            context.scene.df_preview_temp_dir = ""
            context.scene.df_preview_commit_hash = ""


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
                # Refresh branches list (HEAD may have changed)
                bpy.ops.df.refresh_branches(update_index=False)
                # Refresh history
                bpy.ops.df.refresh_history()
                return {'FINISHED'}
            else:
                self.report({'ERROR'}, f"Failed to checkout: {error}")
                return {'CANCELLED'}
        except (ValueError, FileNotFoundError) as e:
            self.report({'ERROR'}, f"Failed to checkout commit: {str(e)}")
            logger.error(f"Failed to checkout commit: {e}", exc_info=True)
            return {'CANCELLED'}
        except Exception as e:
            self.report({'ERROR'}, f"Failed to checkout commit: {str(e)}")
            logger.error(f"Unexpected error during checkout: {e}", exc_info=True)
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
        except (ValueError, FileNotFoundError) as e:
            self.report({'ERROR'}, f"Failed to checkout commit: {str(e)}")
            logger.error(f"Failed to checkout commit: {e}", exc_info=True)
            return {'CANCELLED'}
        except Exception as e:
            self.report({'ERROR'}, f"Failed to checkout commit: {str(e)}")
            logger.error(f"Unexpected error during checkout: {e}", exc_info=True)
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
        except (OSError, ValueError, PermissionError) as e:
            self.report({'ERROR'}, f"Failed to open .blend file: {str(e)}")
            logger.error(f"Failed to open .blend file: {e}", exc_info=True)
            return {'CANCELLED'}
        except Exception as e:
            self.report({'ERROR'}, f"Failed to open .blend file: {str(e)}")
            logger.error(f"Unexpected error opening .blend file: {e}", exc_info=True)
            return {'CANCELLED'}


class DF_OT_compare_project(Operator):
    """Checkout commit to temporary folder and open in new Blender window."""
    bl_idname = "df.compare_project"
    bl_label = "Compare"
    bl_description = "Checkout this commit to temporary folder and open in new Blender window"
    bl_options = {'REGISTER'}

    commit_hash: StringProperty(name="Commit Hash")

    def invoke(self, context, event):
        """Invoke operator - check if comparison is already active."""
        scene = context.scene
        # Check if this commit is already being compared
        if (getattr(scene, 'df_project_comparison_active', False) and 
            getattr(scene, 'df_project_comparison_commit_hash', '') == self.commit_hash):
            # Toggle OFF: Close Blender and clean up
            return self.execute(context)
        
        # Execute directly to start comparison
        return self.execute(context)

    def execute(self, context):
        """Checkout commit to temp folder and open in new Blender window, or close if already active."""
        import subprocess
        import shutil
        
        scene = context.scene
        
        # Check if comparison is already active for this commit - toggle OFF
        if (getattr(scene, 'df_project_comparison_active', False) and 
            getattr(scene, 'df_project_comparison_commit_hash', '') == self.commit_hash):
            # Toggle OFF: Clean up temporary files
            temp_dir_str = getattr(scene, 'df_project_comparison_temp_dir', '')
            if temp_dir_str:
                temp_working_dir = Path(temp_dir_str)
                
                # Clean up temporary directory
                if temp_working_dir.exists():
                    try:
                        shutil.rmtree(temp_working_dir)
                        self.report({'INFO'}, "Temporary files removed")
                    except (OSError, PermissionError) as e:
                        self.report({'WARNING'}, f"Could not remove temp directory: {str(e)}")
                        logger.warning(f"Could not remove temp directory: {e}", exc_info=True)
                    except Exception as e:
                        self.report({'WARNING'}, f"Could not remove temp directory: {str(e)}")
                        logger.error(f"Unexpected error removing temp directory: {e}", exc_info=True)
                
                # Clear comparison state
                scene.df_project_comparison_active = False
                scene.df_project_comparison_commit_hash = ""
                scene.df_project_comparison_temp_dir = ""
                
                return {'FINISHED'}
        
        # Toggle ON: Start comparison
        # Find repository
        repo_path, error = get_repository_path(self)
        if not repo_path:
            return {'CANCELLED'}
        
        # Get current .blend file (to know filename)
        blend_file = Path(bpy.data.filepath)
        if not blend_file:
            self.report({'ERROR'}, "Please save the Blender file first")
            return {'CANCELLED'}
        
        # Create temporary directory for checkout
        dfm_dir = repo_path / ".DFM"
        compare_temp_dir = dfm_dir / "compare_temp"
        compare_temp_dir.mkdir(exist_ok=True)
        
        # Create unique temp directory for this commit
        temp_working_dir = compare_temp_dir / f"commit_{self.commit_hash[:16]}"
        
        # Clean up if exists
        if temp_working_dir.exists():
            shutil.rmtree(temp_working_dir)
        temp_working_dir.mkdir(parents=True)

        # Clean up other old compare_temp directories (keep current one)
        try:
            cleanup_old_compare_temp(repo_path, keep_current=str(temp_working_dir))
        except Exception as e:
            logger.warning(f"Failed to clean up old compare_temp directories: {e}", exc_info=True)
        
        # Step 1: Restore commit to temporary directory
        try:
            from ..forester.core.database import ForesterDB
            from ..forester.core.storage import ObjectStorage
            from ..forester.models.commit import Commit
            from ..forester.commands.checkout import restore_files_from_tree, restore_meshes_from_commit
            
            db_path = dfm_dir / "forester.db"
            db = ForesterDB(db_path)
            db.connect()
            
            try:
                storage = ObjectStorage(dfm_dir)
                commit = Commit.from_storage(self.commit_hash, db, storage)
                
                if not commit:
                    self.report({'ERROR'}, f"Commit {self.commit_hash} not found")
                    return {'CANCELLED'}
                
                # Get tree from commit
                tree = commit.get_tree(db, storage)
                if not tree:
                    self.report({'ERROR'}, f"Tree for commit {self.commit_hash} not found")
                    return {'CANCELLED'}
                
                # Restore files from tree to temp directory
                restore_files_from_tree(tree, temp_working_dir, storage, db)

                # Copy project textures from original project root into compare_temp
                # This makes textures available when .blend is opened from compare_temp,
                # even if some blobs were missing in the commit.
                try:
                    project_root = blend_file.parent
                    copy_project_textures_for_compare(project_root, temp_working_dir)
                except Exception as e:
                    logger.warning(f"Failed to copy project textures for compare: {e}", exc_info=True)

                # Restore meshes from commit (mesh-only data, if present)
                restore_meshes_from_commit(commit, temp_working_dir, storage, dfm_dir)
                
            finally:
                db.close()
            
        except (ValueError, FileNotFoundError) as e:
            self.report({'ERROR'}, f"Failed to checkout commit: {str(e)}")
            logger.error(f"Failed to checkout commit: {e}", exc_info=True)
            # Clean up on error
            if temp_working_dir.exists():
                try:
                    shutil.rmtree(temp_working_dir)
                except Exception:
                    pass
            return {'CANCELLED'}
        except Exception as e:
            self.report({'ERROR'}, f"Failed to checkout commit: {str(e)}")
            logger.error(f"Unexpected error during checkout: {e}", exc_info=True)
            # Clean up on error
            if temp_working_dir.exists():
                try:
                    shutil.rmtree(temp_working_dir)
                except Exception:
                    pass
            return {'CANCELLED'}
        
        # Step 2: Locate target .blend in temp directory (search recursively)
        target_blend = None
        blend_file_name = blend_file.name
        
        # First try root directory
        target_blend = temp_working_dir / blend_file_name
        if not target_blend.exists():
            # Search recursively for .blend file
            for found_file in temp_working_dir.rglob("*.blend"):
                if found_file.name == blend_file_name:
                    target_blend = found_file
                    break
        
        if not target_blend or not target_blend.exists():
            self.report({'ERROR'}, f"Blend file '{blend_file_name}' not found after checkout")
            return {'CANCELLED'}
        
        # Step 3: Find Blender executable and open in new window
        try:
            # Get Blender executable path
            blender_exe = bpy.app.binary_path
            if not blender_exe:
                # Fallback: try to find blender in PATH
                import shutil
                blender_exe = shutil.which("blender")
                if not blender_exe:
                    self.report({'ERROR'}, "Could not find Blender executable")
                    return {'CANCELLED'}
            
            # Convert path to absolute and ensure it's a string
            target_blend_str = str(target_blend.resolve())
            
            # Launch new Blender instance
            process = subprocess.Popen([blender_exe, target_blend_str], 
                           stdout=subprocess.DEVNULL, 
                           stderr=subprocess.DEVNULL)
            
            # Store comparison state
            scene.df_project_comparison_active = True
            scene.df_project_comparison_commit_hash = self.commit_hash
            scene.df_project_comparison_temp_dir = str(temp_working_dir)
            
            self.report({'INFO'}, f"Opening commit in new Blender window")
            return {'FINISHED'}
            
        except (OSError, ValueError, PermissionError) as e:
            self.report({'ERROR'}, f"Failed to open Blender: {str(e)}")
            logger.error(f"Failed to open Blender: {e}", exc_info=True)
            # Clean up on error
            if temp_working_dir.exists():
                try:
                    shutil.rmtree(temp_working_dir)
                except Exception:
                    pass
            return {'CANCELLED'}
        except Exception as e:
            self.report({'ERROR'}, f"Failed to open Blender: {str(e)}")
            logger.error(f"Unexpected error opening Blender: {e}", exc_info=True)
            # Clean up on error
            if temp_working_dir.exists():
                try:
                    shutil.rmtree(temp_working_dir)
                except Exception:
                    pass
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
                # Refresh branches list (commit count may have changed)
                bpy.ops.df.refresh_branches(update_index=False)
                # Refresh history
                bpy.ops.df.refresh_history()
                return {'FINISHED'}
            else:
                self.report({'ERROR'}, f"Failed to delete commit: {error}")
                return {'CANCELLED'}
        except (ValueError, FileNotFoundError) as e:
            self.report({'ERROR'}, f"Failed to delete commit: {str(e)}")
            logger.error(f"Failed to delete commit: {e}", exc_info=True)
            return {'CANCELLED'}
        except Exception as e:
            self.report({'ERROR'}, f"Failed to delete commit: {str(e)}")
            logger.error(f"Unexpected error deleting commit: {e}", exc_info=True)
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
            blend_path, metadata, mesh_storage_path = load_mesh_from_commit(repo_path, self.commit_hash, self.mesh_name)
            
            if not blend_path:
                self.report({'ERROR'}, f"Mesh '{self.mesh_name}' not found in commit")
                return {'CANCELLED'}
            
            # Import from .blend file
            # Используем имя из metadata, так как оно может отличаться от mesh_name
            actual_mesh_name = metadata.get('object_name', self.mesh_name)
            from ..operators.mesh_io import import_mesh_from_blend
            obj = import_mesh_from_blend(blend_path, actual_mesh_name, context)
            
            if not obj:
                self.report({'ERROR'}, f"Failed to load mesh from .blend file")
                return {'CANCELLED'}
            
            # Load textures from metadata
            material_json = metadata.get('material_json', {})
            if material_json and 'textures' in material_json and mesh_storage_path:
                from ..operators.mesh_io import load_textures_to_material
                if obj.material_slots and obj.material_slots[0].material:
                    load_textures_to_material(obj.material_slots[0].material, material_json['textures'], mesh_storage_path)
            
            self.report({'INFO'}, f"Loaded mesh '{self.mesh_name}' from commit")
            return {'FINISHED'}
        except (ValueError, FileNotFoundError, KeyError) as e:
            self.report({'ERROR'}, f"Failed to load mesh: {str(e)}")
            logger.error(f"Failed to load mesh: {e}", exc_info=True)
            return {'CANCELLED'}
        except Exception as e:
            self.report({'ERROR'}, f"Failed to load mesh: {str(e)}")
            logger.error(f"Unexpected error loading mesh: {e}", exc_info=True)
            return {'CANCELLED'}


class DF_OT_select_mesh_from_commit(Operator):
    """Select mesh object by name in viewport."""
    bl_idname = "df.select_mesh_from_commit"
    bl_label = "Select Mesh"
    bl_description = "Select mesh object in viewport"
    bl_options = {'REGISTER', 'UNDO'}

    mesh_name: StringProperty(name="Mesh Name")

    def execute(self, context):
        """Execute the operator."""
        if not self.mesh_name:
            self.report({'ERROR'}, "Mesh name not specified")
            return {'CANCELLED'}
        
        # Find object by name
        if self.mesh_name not in bpy.data.objects:
            self.report({'WARNING'}, f"Object '{self.mesh_name}' not found in scene")
            return {'CANCELLED'}
        
        obj = bpy.data.objects[self.mesh_name]
        
        # Deselect all objects
        bpy.ops.object.select_all(action='DESELECT')
        
        # Select and activate the object
        obj.select_set(True)
        context.view_layer.objects.active = obj
        
        # Frame selected object in viewport
        if context.space_data and context.space_data.type == 'VIEW_3D':
            bpy.ops.view3d.view_selected()
        
        self.report({'INFO'}, f"Selected: {self.mesh_name}")
        return {'FINISHED'}


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
            blend_path, metadata, mesh_storage_path = load_mesh_from_commit(repo_path, self.commit_hash, mesh_name)
            
            if not blend_path:
                self.report({'ERROR'}, f"Mesh '{mesh_name}' not found in commit")
                return {'CANCELLED'}
            
            # Import from .blend file and replace selected object
            # Используем имя из metadata, так как оно может отличаться от mesh_name
            actual_mesh_name = metadata.get('object_name', mesh_name)
            from ..operators.mesh_io import import_mesh_from_blend
            
            # Сначала загружаем объект из .blend
            imported_obj = import_mesh_from_blend(blend_path, actual_mesh_name, context)
            
            if not imported_obj:
                self.report({'ERROR'}, f"Failed to load mesh from .blend file")
                return {'CANCELLED'}
            
            # Копируем данные в выбранный объект
            active_obj = context.active_object
            if active_obj and active_obj.type == 'MESH':
                # Копируем mesh data
                active_obj.data = imported_obj.data.copy()
                # Копируем материалы
                # Очищаем материалы через data.materials (material_slots не поддерживает clear)
                active_obj.data.materials.clear()
                for slot in imported_obj.material_slots:
                    if slot.material:
                        active_obj.data.materials.append(slot.material)
                
                # Удаляем импортированный объект
                bpy.data.objects.remove(imported_obj, do_unlink=True)
                
                # Загружаем текстуры
                material_json = metadata.get('material_json', {})
                if material_json and 'textures' in material_json and mesh_storage_path:
                    from ..operators.mesh_io import load_textures_to_material
                    if active_obj.material_slots and active_obj.material_slots[0].material:
                        load_textures_to_material(active_obj.material_slots[0].material, material_json['textures'], mesh_storage_path)
            else:
                # Если нет активного объекта, просто используем импортированный
                pass
            
            self.report({'INFO'}, f"Replaced mesh '{mesh_name}' with version from commit")
            return {'FINISHED'}
        except (ValueError, FileNotFoundError, KeyError) as e:
            self.report({'ERROR'}, f"Failed to replace mesh: {str(e)}")
            logger.error(f"Failed to replace mesh: {e}", exc_info=True)
            return {'CANCELLED'}
        except Exception as e:
            self.report({'ERROR'}, f"Failed to replace mesh: {str(e)}")
            logger.error(f"Unexpected error replacing mesh: {e}", exc_info=True)
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
    axis: bpy.props.EnumProperty(
        name="Axis",
        description="Axis for comparison object offset",
        items=[
            ('X', 'X', 'Offset along X axis'),
            ('Y', 'Y', 'Offset along Y axis'),
            ('Z', 'Z', 'Offset along Z axis'),
        ],
        default='X',
    )
    
    def invoke(self, context, event):
        """Invoke operator directly without dialog."""
        # Check if comparison is already active - if so, just toggle off
        scene = context.scene
        comparison_obj_name = getattr(scene, 'df_comparison_object_name', None)
        if comparison_obj_name and comparison_obj_name in bpy.data.objects:
            # Toggle OFF: Remove comparison object
            return self.execute(context)
        
        # Get axis from scene property (selected via buttons in panel)
        if hasattr(scene, 'df_comparison_axis'):
            self.axis = scene.df_comparison_axis
        else:
            self.axis = 'X'  # Default to X
        
        # Execute directly without dialog
        return self.execute(context)

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
            blend_path, metadata, mesh_storage_path = load_mesh_from_commit(repo_path, self.commit_hash, mesh_name)
            
            if not blend_path:
                self.report({'ERROR'}, f"Mesh '{mesh_name}' not found in commit")
                return {'CANCELLED'}
            
            # Import from .blend file
            # Используем имя из metadata, так как оно может отличаться от mesh_name
            actual_mesh_name = metadata.get('object_name', mesh_name)
            from ..operators.mesh_io import import_mesh_from_blend
            comparison_obj = import_mesh_from_blend(blend_path, actual_mesh_name, context)
            
            if not comparison_obj:
                self.report({'ERROR'}, f"Failed to load mesh from .blend file")
                return {'CANCELLED'}
            
            # Переименовываем для сравнения
            comparison_obj.name = f"{mesh_name}_compare"
            
            # Загружаем текстуры из метаданных
            material_json = metadata.get('material_json', {})
            
            # Если material_json это строка, парсим её
            if isinstance(material_json, str):
                try:
                    import json
                    material_json = json.loads(material_json) if material_json else {}
                except (json.JSONDecodeError, ValueError) as e:
                    logger.warning(f"Failed to parse material_json as JSON: {e}")
                    material_json = {}
            
            logger.debug(f"Compare mesh: material_json type={type(material_json)}, has textures={'textures' in material_json if isinstance(material_json, dict) else False}")
            logger.debug(f"Compare mesh: mesh_storage_path={mesh_storage_path}")
            
            if material_json and isinstance(material_json, dict) and 'textures' in material_json and mesh_storage_path:
                textures_list = material_json['textures']
                if not isinstance(textures_list, list):
                    logger.warning(f"Compare mesh: textures is not a list, type={type(textures_list)}")
                    textures_list = []
                else:
                    logger.debug(f"Compare mesh: Found {len(textures_list)} textures to load")
                
                from ..operators.mesh_io import load_textures_to_material
                if comparison_obj.material_slots and len(comparison_obj.material_slots) > 0:
                    mat = comparison_obj.material_slots[0].material
                    if mat:
                        # Создаем материал с префиксом для сравнения (если еще не создан)
                        if not mat.name.startswith("_compare_"):
                            new_mat = mat.copy()
                            new_mat.name = f"_compare_{mat.name}"
                            comparison_obj.data.materials[0] = new_mat
                            mat = new_mat
                        
                        logger.debug(f"Compare mesh: Loading textures to material '{mat.name}'")
                        load_textures_to_material(mat, textures_list, mesh_storage_path)
                    else:
                        logger.warning("Compare mesh: Material slot has no material")
                else:
                    logger.warning("Compare mesh: No material slots found")
            else:
                logger.warning(f"Compare mesh: Cannot load textures - material_json={bool(material_json)}, is_dict={isinstance(material_json, dict) if material_json else False}, has_textures={'textures' in material_json if isinstance(material_json, dict) else False}, mesh_storage_path={bool(mesh_storage_path)}")
            
            # Offset comparison object based on selected axis
            comparison_obj.location.x = original_obj.location.x
            comparison_obj.location.y = original_obj.location.y
            comparison_obj.location.z = original_obj.location.z
            
            if self.axis == 'X':
                comparison_obj.location.x = original_obj.location.x + self.offset_distance
            elif self.axis == 'Y':
                comparison_obj.location.y = original_obj.location.y + self.offset_distance
            elif self.axis == 'Z':
                comparison_obj.location.z = original_obj.location.z + self.offset_distance
            
            # Store comparison state
            scene.df_comparison_object_name = comparison_obj.name
            scene.df_comparison_active = True
            scene.df_original_object_name = original_obj.name
            scene.df_comparison_commit_hash = self.commit_hash
            scene.df_comparison_axis = self.axis
            
            # Compute diff automatically
            try:
                from .mesh_io import export_mesh_to_json
                export_options = {
                    'vertices': True,
                    'faces': True,
                    'uv': True,
                    'normals': True,
                    'materials': True,
                }
                current_mesh_data = export_mesh_to_json(original_obj, export_options)
                current_mesh_json = current_mesh_data['mesh_json']
                current_material_json = current_mesh_data['material_json']
                
                # Extract mesh_json and material_json from metadata
                import json
                old_mesh_json_raw = metadata.get('mesh_json')
                old_material_json_raw = metadata.get('material_json')
                
                # Normalize mesh_json
                old_mesh_json = {}
                if old_mesh_json_raw is not None:
                    if isinstance(old_mesh_json_raw, dict):
                        old_mesh_json = old_mesh_json_raw
                    elif isinstance(old_mesh_json_raw, str):
                        if old_mesh_json_raw.strip():  # Not empty string
                            try:
                                old_mesh_json = json.loads(old_mesh_json_raw)
                            except (json.JSONDecodeError, ValueError) as e:
                                logger.warning(f"Failed to parse old_mesh_json as JSON: {e}")
                                old_mesh_json = {}
                
                # Normalize material_json
                old_material_json = {}
                if old_material_json_raw is not None:
                    if isinstance(old_material_json_raw, dict):
                        old_material_json = old_material_json_raw
                    elif isinstance(old_material_json_raw, str):
                        if old_material_json_raw.strip():  # Not empty string
                            try:
                                old_material_json = json.loads(old_material_json_raw)
                            except (json.JSONDecodeError, ValueError) as e:
                                logger.warning(f"Failed to parse old_material_json as JSON: {e}")
                                old_material_json = {}
                
                # If mesh_json is still empty, try to load from separate file
                if not old_mesh_json and mesh_storage_path:
                    mesh_json_path = mesh_storage_path / "mesh.json"
                    if mesh_json_path.exists():
                        try:
                            with open(mesh_json_path, 'r', encoding='utf-8') as f:
                                old_mesh_json = json.load(f)
                            logger.info(f"Loaded mesh_json from separate file: {mesh_json_path}")
                        except Exception as e:
                            logger.warning(f"Failed to load mesh.json from {mesh_json_path}: {e}")
                
                # If material_json is still empty, try to load from separate file
                if not old_material_json and mesh_storage_path:
                    material_json_path = mesh_storage_path / "material.json"
                    if material_json_path.exists():
                        try:
                            with open(material_json_path, 'r', encoding='utf-8') as f:
                                old_material_json = json.load(f)
                            logger.info(f"Loaded material_json from separate file: {material_json_path}")
                        except Exception as e:
                            logger.warning(f"Failed to load material.json from {material_json_path}: {e}")
                
                # Final check - mesh_json must be a non-empty dict
                if not old_mesh_json or not isinstance(old_mesh_json, dict) or len(old_mesh_json) == 0:
                    logger.warning(f"No valid old_mesh_json found. Type: {type(old_mesh_json_raw)}, Value: {repr(old_mesh_json_raw)[:100] if old_mesh_json_raw else 'None'}")
                    logger.warning("Skipping diff computation")
                else:
                    diff = compute_mesh_diff(
                        mesh_name=mesh_name,
                        old_mesh_json=old_mesh_json,
                        old_material_json=old_material_json,
                        new_mesh_json=current_mesh_json,
                        new_material_json=current_material_json,
                        tolerance=0.001
                    )
                    
                    # Store diff in scene properties
                    scene['df_diff_result'] = diff.to_dict()
                    scene['df_diff_mesh_name'] = mesh_name
                    scene['df_diff_commit_hash'] = self.commit_hash
                    
                    # Report diff statistics
                    stats = diff.statistics
                    logger.info(f"Diff computed: +{stats.vertices_added_count} "
                               f"-{stats.vertices_removed_count} "
                               f"~{stats.vertices_modified_count} vertices")
            except Exception as e:
                logger.warning(f"Failed to compute diff during comparison: {e}", exc_info=True)
                # Don't fail the comparison if diff computation fails
            
            # Restore focus to original object
            for obj in context.selected_objects:
                obj.select_set(False)
            original_obj.select_set(True)
            context.view_layer.objects.active = original_obj
            
            self.report({'INFO'}, f"Comparison mode enabled (offset +{self.offset_distance} on {self.axis} axis)")
            return {'FINISHED'}
        except (ValueError, FileNotFoundError, KeyError) as e:
            self.report({'ERROR'}, f"Failed to compare mesh: {str(e)}")
            logger.error(f"Failed to compare mesh: {e}", exc_info=True)
            return {'CANCELLED'}
        except Exception as e:
            self.report({'ERROR'}, f"Failed to compare mesh: {str(e)}")
            logger.error(f"Unexpected error comparing mesh: {e}", exc_info=True)
            return {'CANCELLED'}


class DF_OT_switch_comparison_axis(Operator):
    """Switch comparison axis and recreate comparison object."""
    bl_idname = "df.switch_comparison_axis"
    bl_label = "Switch Comparison Axis"
    bl_description = "Switch comparison axis and recreate comparison object"
    bl_options = {'REGISTER', 'UNDO'}

    axis: StringProperty(name="Axis", default='X')

    def execute(self, context):
        """Execute the operator."""
        scene = context.scene
        
        # Update axis property
        scene.df_comparison_axis = self.axis
        
        # Check if comparison is active
        comparison_obj_name = getattr(scene, 'df_comparison_object_name', None)
        if not comparison_obj_name or comparison_obj_name not in bpy.data.objects:
            # If no comparison object, just update the axis property
            self.report({'INFO'}, f"Comparison axis set to {self.axis}")
            return {'FINISHED'}
        
        # Get original object
        original_obj_name = getattr(scene, 'df_original_object_name', None)
        if not original_obj_name or original_obj_name not in bpy.data.objects:
            self.report({'ERROR'}, "Original object not found")
            return {'CANCELLED'}
        
        original_obj = bpy.data.objects[original_obj_name]
        comparison_obj = bpy.data.objects[comparison_obj_name]
        commit_hash = getattr(scene, 'df_comparison_commit_hash', None)
        
        if not commit_hash:
            self.report({'ERROR'}, "Commit hash not found")
            return {'CANCELLED'}
        
        # Get mesh name (remove _compare suffix if present)
        mesh_name = comparison_obj.name
        if mesh_name.endswith('_compare'):
            mesh_name = mesh_name[:-8]  # Remove '_compare'
        
        # Get offset distance from current position
        offset_distance = 2.0
        if self.axis == 'X':
            offset_distance = abs(comparison_obj.location.x - original_obj.location.x)
        elif self.axis == 'Y':
            offset_distance = abs(comparison_obj.location.y - original_obj.location.y)
        elif self.axis == 'Z':
            offset_distance = abs(comparison_obj.location.z - original_obj.location.z)
        
        if offset_distance == 0:
            offset_distance = 2.0  # Default distance
        
        # Find repository
        repo_path, error = get_repository_path(self)
        if not repo_path:
            return {'CANCELLED'}
        
        # Load mesh from commit
        try:
            blend_path, metadata, mesh_storage_path = load_mesh_from_commit(repo_path, commit_hash, mesh_name)
            
            if not blend_path:
                self.report({'ERROR'}, f"Mesh '{mesh_name}' not found in commit")
                return {'CANCELLED'}
            
            # Remove old comparison object
            bpy.data.objects.remove(comparison_obj, do_unlink=True)
            
            # Import from .blend file
            # Используем имя из metadata, так как оно может отличаться от mesh_name
            actual_mesh_name = metadata.get('object_name', mesh_name)
            from ..operators.mesh_io import import_mesh_from_blend
            comparison_obj = import_mesh_from_blend(blend_path, actual_mesh_name, context)
            
            if not comparison_obj:
                self.report({'ERROR'}, f"Failed to load mesh from .blend file")
                return {'CANCELLED'}
            
            # Переименовываем для сравнения
            comparison_obj.name = f"{mesh_name}_compare"
            
            # Загружаем текстуры из метаданных
            material_json = metadata.get('material_json', {})
            if material_json and 'textures' in material_json and mesh_storage_path:
                from ..operators.mesh_io import load_textures_to_material
                if comparison_obj.material_slots and comparison_obj.material_slots[0].material:
                    # Создаем материал с префиксом для сравнения
                    mat = comparison_obj.material_slots[0].material
                    if not mat.name.startswith("_compare_"):
                        new_mat = mat.copy()
                        new_mat.name = f"_compare_{mat.name}"
                        comparison_obj.data.materials[0] = new_mat
                        load_textures_to_material(new_mat, material_json['textures'], mesh_storage_path)
            
            # Offset comparison object based on selected axis
            comparison_obj.location.x = original_obj.location.x
            comparison_obj.location.y = original_obj.location.y
            comparison_obj.location.z = original_obj.location.z
            
            if self.axis == 'X':
                comparison_obj.location.x = original_obj.location.x + offset_distance
            elif self.axis == 'Y':
                comparison_obj.location.y = original_obj.location.y + offset_distance
            elif self.axis == 'Z':
                comparison_obj.location.z = original_obj.location.z + offset_distance
            
            # Update comparison state
            scene.df_comparison_object_name = comparison_obj.name
            
            # Restore focus to original object
            for obj in context.selected_objects:
                obj.select_set(False)
            original_obj.select_set(True)
            context.view_layer.objects.active = original_obj
            
            self.report({'INFO'}, f"Comparison axis switched to {self.axis} (offset +{offset_distance})")
            return {'FINISHED'}
        except (ValueError, FileNotFoundError, KeyError) as e:
            self.report({'ERROR'}, f"Failed to switch comparison axis: {str(e)}")
            logger.error(f"Failed to switch comparison axis: {e}", exc_info=True)
            return {'CANCELLED'}
        except Exception as e:
            self.report({'ERROR'}, f"Failed to switch comparison axis: {str(e)}")
            logger.error(f"Unexpected error switching comparison axis: {e}", exc_info=True)
            return {'CANCELLED'}
