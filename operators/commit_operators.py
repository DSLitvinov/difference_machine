"""
Operators for commit operations in Difference Machine.
"""

import bpy
import logging
from bpy.types import Operator
from bpy.props import StringProperty
from pathlib import Path

logger = logging.getLogger(__name__)

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
from ..forester.core.database import ForesterDB
from .mesh_io import export_mesh_to_json
from .operator_helpers import get_repository_path, process_meshes_sequentially, is_repository_initialized


class DF_OT_create_project_commit(Operator):
    """Create a full project commit."""
    bl_idname = "df.create_project_commit"
    bl_label = "Create Project Commit"
    bl_description = "Create a commit of the entire working directory"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        """Execute the operator."""
        # Ensure repository and branch are ready
        from .operator_helpers import ensure_repository_and_branch
        repo_path, error = ensure_repository_and_branch(context, self)
        if not repo_path:
            return {'CANCELLED'}
        
        # Get current branch from repository
        branch_name = get_current_branch(repo_path) or "main"
        
        # Get properties
        props = context.scene.df_commit_props
        
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
                # Refresh branches list (commit count may have changed)
                bpy.ops.df.refresh_branches(update_index=False)
                # Refresh commit history
                bpy.ops.df.refresh_history()
                return {'FINISHED'}
            else:
                self.report({'INFO'}, "No changes to commit")
                return {'CANCELLED'}
        except (ValueError, FileNotFoundError, PermissionError) as e:
            self.report({'ERROR'}, f"Failed to create commit: {str(e)}")
            logger.error(f"Failed to create project commit: {e}", exc_info=True)
            return {'CANCELLED'}
        except Exception as e:
            self.report({'ERROR'}, f"Failed to create commit: {str(e)}")
            logger.error(f"Unexpected error creating project commit: {e}", exc_info=True)
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
                # Update current branch in database
                db_path = repo_path / ".DFM" / "forester.db"
                if db_path.exists():
                    with ForesterDB(db_path) as db:
                        db.set_current_branch(branch_name)
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
                
                # Refresh branches list (commit count may have changed)
                bpy.ops.df.refresh_branches(update_index=False)
                # Refresh commit history
                bpy.ops.df.refresh_history()
                
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
        
        # Get current branch from database (source of truth)
        branch_name = get_current_branch(repo_path)
        if not branch_name:
            branch_name = "main"  # Fallback
        
        # Get commits from database for current branch
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
            
            self.report({'INFO'}, f"Loaded {len(commits_data)} commits from branch '{branch_name}'")
            return {'FINISHED'}
        except (ValueError, FileNotFoundError) as e:
            self.report({'ERROR'}, f"Failed to load commits: {str(e)}")
            logger.error(f"Failed to load commits: {e}", exc_info=True)
            return {'CANCELLED'}
        except Exception as e:
            self.report({'ERROR'}, f"Failed to load commits: {str(e)}")
            logger.error(f"Unexpected error loading commits: {e}", exc_info=True)
            return {'CANCELLED'}


class DF_OT_refresh_branches(Operator):
    """Refresh branch list."""
    bl_idname = "df.refresh_branches"
    bl_label = "Refresh Branches"
    bl_description = "Refresh the branch list"
    bl_options = {'REGISTER'}

    update_index: bpy.props.BoolProperty(name="Update Index", default=True)

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
            # Get current branch from database (source of truth)
            current_branch = get_current_branch(repo_path)
            if not current_branch:
                current_branch = "main"  # Fallback
            
            branches_data = list_branches(repo_path)
            
            # Clear existing list
            context.scene.df_branches.clear()
            
            # Add branches to list
            current_branch_index = 0  # Default to first branch
            for idx, branch_data in enumerate(branches_data):
                branch_item = context.scene.df_branches.add()
                branch_item.name = branch_data['name']
                branch_item.branch_index = idx  # Store index in database list (not displayed)
                # Use current_branch from database to determine is_current
                branch_item.is_current = (branch_data['name'] == current_branch)
                
                # Track index of current branch
                if branch_item.is_current:
                    current_branch_index = idx
                
                # Get commit count and last commit from database
                commits = get_branch_commits(repo_path, branch_data['name'])
                branch_item.commit_count = len(commits)
                
                if commits:
                    last_commit = commits[-1]  # Last commit (newest)
                    branch_item.last_commit_hash = last_commit.get('hash', '')
                    branch_item.last_commit_message = last_commit.get('message', 'No message')
                else:
                    branch_item.last_commit_hash = ''
                    branch_item.last_commit_message = 'No commits'
            
            # Update the list index to point to the current branch (only if requested)
            if self.update_index and hasattr(context.scene, 'df_branch_list_index'):
                context.scene.df_branch_list_index = current_branch_index
            
            self.report({'INFO'}, f"Loaded {len(branches_data)} branches")
            return {'FINISHED'}
        except (ValueError, FileNotFoundError) as e:
            self.report({'ERROR'}, f"Failed to load branches: {str(e)}")
            logger.error(f"Failed to load branches: {e}", exc_info=True)
            return {'CANCELLED'}
        except Exception as e:
            self.report({'ERROR'}, f"Failed to load branches: {str(e)}")
            logger.error(f"Unexpected error loading branches: {e}", exc_info=True)
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
            # Refresh branches list to update indices
            bpy.ops.df.refresh_branches(update_index=True)
            # Refresh commit history to update UI
            bpy.ops.df.refresh_history()
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
        # Если branch_name не указан, используем выбранную ветку из списка
        if not self.branch_name:
            branches = context.scene.df_branches
            if not branches or len(branches) == 0:
                self.report({'ERROR'}, "No branches available. Please refresh the list.")
                return {'CANCELLED'}
            
            selected_index = getattr(context.scene, 'df_branch_list_index', -1)
            if selected_index < 0 or selected_index >= len(branches):
                self.report({'ERROR'}, f"No branch selected. Index: {selected_index}, Branches: {len(branches)}")
                return {'CANCELLED'}
            
            selected_branch = branches[selected_index]
            self.branch_name = selected_branch.name
            
            if not self.branch_name:
                self.report({'ERROR'}, f"Selected branch has no name at index {selected_index}")
                return {'CANCELLED'}
            
            # ВАЖНО: Логируем для отладки
            logger.debug(f"Invoke: selected branch name from UI: '{self.branch_name}'")
        
        return self.execute(context)

    def execute(self, context):
        """Execute the operator."""
        blend_file = Path(bpy.data.filepath)
        if not blend_file:
            self.report({'ERROR'}, "Please save the Blender file first")
            return {'CANCELLED'}
        
        repo_path = find_repository(blend_file.parent)
        if not repo_path:
            self.report({'ERROR'}, "Not a Forester repository")
            return {'CANCELLED'}
        
        # ВАЖНО: Сохраняем имя ветки в локальную переменную перед проверками
        # чтобы избежать проблем с сохранением состояния между вызовами
        target_branch_name = self.branch_name
        
        if not target_branch_name:
            self.report({'ERROR'}, "Branch name not specified")
            return {'CANCELLED'}
        
        try:
            # ВАЖНО: Получаем текущую ветку непосредственно из репозитория
            # Не полагаемся на кешированные значения
            # Используем новое соединение с БД для гарантии актуальных данных
            current_branch = get_current_branch(repo_path)
            
            # Отладочная информация
            logger.debug(f"Execute: current_branch='{current_branch}', switching to='{target_branch_name}'")
            
            # Проверяем, не пытаемся ли переключиться на ту же ветку
            # ВАЖНО: Сравниваем строки, учитывая что current_branch может быть None
            if current_branch and current_branch == target_branch_name:
                logger.debug(f"Already on branch '{target_branch_name}', skipping switch")
                self.report({'INFO'}, f"Already on branch '{target_branch_name}'")
                # Но все равно обновляем UI на случай изменений
                self._update_ui(context, repo_path)
                # ВАЖНО: Сбрасываем branch_name после использования
                self.branch_name = ""
                return {'CANCELLED'}
            
            # Переключаем ветку
            logger.debug(f"Calling switch_branch('{target_branch_name}')")
            switch_branch(repo_path, target_branch_name)
            
            # ВАЖНО: Сразу после переключения получаем текущую ветку из БД
            # Используем новое соединение для гарантии чтения актуальных данных
            # Не используем задержки - полагаемся на правильную работу транзакций БД
            new_current_branch = get_current_branch(repo_path)
            logger.debug(f"After switch - current branch: '{new_current_branch}', expected: '{target_branch_name}'")
            
            # Проверяем, что переключение прошло успешно
            if new_current_branch != target_branch_name:
                # Если не совпадает, пробуем еще раз (может быть проблема с транзакцией)
                # Закрываем все соединения и открываем новое
                import gc
                gc.collect()  # Принудительная сборка мусора для закрытия соединений
                
                new_current_branch = get_current_branch(repo_path)
                logger.debug(f"After gc.collect() - current branch: '{new_current_branch}'")
                
                if new_current_branch != target_branch_name:
                    self.report({'ERROR'}, 
                        f"Failed to switch branch. Current branch is '{new_current_branch}' instead of '{target_branch_name}'")
                    logger.error(f"Branch switch failed: expected '{target_branch_name}', got '{new_current_branch}'")
                    # Сбрасываем branch_name
                    self.branch_name = ""
                    return {'CANCELLED'}
            
            self.report({'INFO'}, f"Switched to branch '{target_branch_name}'")
            
            # Обновляем UI
            self._update_ui(context, repo_path)
            
            # ВАЖНО: Сбрасываем branch_name после успешного переключения
            # чтобы следующее переключение не использовало старое значение
            self.branch_name = ""
            
            return {'FINISHED'}
            
        except ValueError as e:
            self.report({'ERROR'}, str(e))
            logger.error(f"ValueError during branch switch: {e}", exc_info=True)
            return {'CANCELLED'}
        except Exception as e:
            self.report({'ERROR'}, f"Failed to switch branch: {str(e)}")
            logger.error(f"Unexpected error during branch switch: {e}", exc_info=True)
            return {'CANCELLED'}

    def _update_ui(self, context, repo_path):
        """Update UI after branch switch."""
        # ВАЖНО: Получаем актуальную текущую ветку из БД
        current_branch = get_current_branch(repo_path)
        
        # Обновляем свойство ветки в сцене актуальным значением
        if current_branch:
            context.scene.df_commit_props.branch = current_branch
        
        # Принудительно обновляем список веток
        # ВАЖНО: update_index=True обновит индекс на текущую ветку
        bpy.ops.df.refresh_branches(update_index=True)
        
        # Обновляем историю для новой ветки
        bpy.ops.df.refresh_history()
        
        # Обновляем все области экрана, а не только текущую
        for area in context.screen.areas:
            area.tag_redraw()

        
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
            # Refresh branches list to update indices
            bpy.ops.df.refresh_branches(update_index=True)
            # Refresh commit history to update UI (commits may have been deleted)
            bpy.ops.df.refresh_history()
            return {'FINISHED'}
        except ValueError as e:
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}
        except Exception as e:
            self.report({'ERROR'}, f"Failed to delete branch: {str(e)}")
            return {'CANCELLED'}


class DF_OT_init_project(Operator):
    """Initialize a new Forester repository."""
    bl_idname = "df.init_project"
    bl_label = "Init Project"
    bl_description = "Initialize a new Forester repository in the current project folder"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        """Execute the operator."""
        if not bpy.data.filepath:
            self.report({'ERROR'}, "Please save the Blender file first")
            return {'CANCELLED'}
        
        blend_file = Path(bpy.data.filepath)
        project_root = blend_file.parent
        
        # Check if repository already exists
        if is_repository_initialized(context):
            self.report({'WARNING'}, "Repository already initialized")
            return {'CANCELLED'}
        
        try:
            init_repository(project_root)
            self.report({'INFO'}, "Repository initialized successfully")
            # Refresh branches after initialization
            bpy.ops.df.refresh_branches()
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Failed to initialize repository: {str(e)}")
            return {'CANCELLED'}


class DF_OT_rebuild_database(Operator):
    """Rebuild database from storage."""
    bl_idname = "df.rebuild_database"
    bl_label = "Rebuild Database"
    bl_description = "Rebuild database from file system storage (use if database is corrupted)"
    bl_options = {'REGISTER'}
    
    def invoke(self, context, event):
        """Invoke with confirmation dialog."""
        return context.window_manager.invoke_confirm(self, event)
    
    def execute(self, context):
        """Execute the operator."""
        blend_file = Path(bpy.data.filepath)
        if not blend_file:
            self.report({'ERROR'}, "Please save the Blender file first")
            return {'CANCELLED'}
        
        repo_path = find_repository(blend_file.parent)
        if not repo_path:
            self.report({'ERROR'}, "Not a Forester repository")
            return {'CANCELLED'}
        
        try:
            from ..forester.commands.rebuild_database import rebuild_database
            
            self.report({'INFO'}, "Rebuilding database from storage...")
            success, error = rebuild_database(repo_path, backup=True)
            
            if success:
                self.report({'INFO'}, "Database rebuilt successfully")
                # Refresh UI
                bpy.ops.df.refresh_branches()
                bpy.ops.df.refresh_history()
                return {'FINISHED'}
            else:
                self.report({'ERROR'}, f"Failed to rebuild database: {error}")
                return {'CANCELLED'}
        except Exception as e:
            self.report({'ERROR'}, f"Failed to rebuild database: {str(e)}")
            logger.error(f"Failed to rebuild database: {e}", exc_info=True)
            return {'CANCELLED'}

