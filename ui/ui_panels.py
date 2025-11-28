"""
UI panels for Difference Machine add-on.
"""

import bpy
from bpy.types import Panel
from pathlib import Path

def get_current_branch_name(context):
    """Get current branch name from repository or return default."""
    try:
        blend_file = Path(bpy.data.filepath)
        if not blend_file:
            return "main"
        
        from ..forester.core.refs import get_current_branch
        from ..forester.core.storage import find_repository
        
        project_root = blend_file.parent
        repo_path = find_repository(project_root)
        if repo_path:
            branch_name = get_current_branch(repo_path)
            return branch_name if branch_name else "main"
    except:
        pass
    
    # Fallback to props or default
    props = context.scene.df_commit_props
    return props.branch if props.branch else "main"


class DF_PT_commit_panel(Panel):
    """Panel for creating commits."""
    bl_label = "Create Commit"
    bl_idname = "DF_PT_commit_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Difference Machine"
    bl_order = 2

    @classmethod
    def poll(cls, context):
        """Show panel only if repository is initialized."""
        from ..operators.operator_helpers import is_repository_initialized
        return is_repository_initialized(context)

    def draw(self, context):
        """Draw the panel UI."""
        layout = self.layout
        props = context.scene.df_commit_props
        
        # Проверяем, является ли активный объект объектом сравнения
        active_obj = context.active_object
        scene = context.scene
        comparison_obj_name = getattr(scene, 'df_comparison_object_name', None)
        is_comparison_object = (active_obj and 
                               active_obj.type == 'MESH' and 
                               comparison_obj_name and 
                               active_obj.name == comparison_obj_name)
        
        if is_comparison_object:
            # Если активен объект сравнения, показываем только информационное сообщение
            box = layout.box()
            box.label(text="Comparison mode active", icon='INFO')
            box.label(text="Only viewing is available")
            return
        
        # Commit mode switcher
        row = layout.row()
        row.prop(props, "commit_mode", expand=True)
        
        # Get selected mesh objects (needed for both modes)
        selected_objects = [obj for obj in context.selected_objects if obj.type == 'MESH']
        
        # Selected Object mode
        if props.commit_mode == 'SELECTED_OBJECT':
            if not selected_objects:
                box = layout.box()
                box.label(text="Select mesh objects to commit", icon='INFO')
            else:
                # Show selected objects info
                for obj in selected_objects:
                    box = layout.box()
                    row = box.row()
                    row.label(text=f"Object: {obj.name}", icon='MESH_DATA')
                    
                    if obj.data:
                        row = box.row()
                        row.label(text=f"Vertices: {len(obj.data.vertices)}")
                        row.label(text=f"Faces: {len(obj.data.polygons)}")
                
                # Export Options
                box = layout.box()
                box.label(text="Export Options", icon='SETTINGS')
                
                # Export All Components checkbox
                box.prop(props, "export_all", text="Export All Components")
                
                # Component buttons grid (2x2)
                if not props.export_all:
                    grid = box.grid_flow(row_major=True, columns=2, align=True)
                    
                    # Geometry button
                    row = grid.row(align=True)
                    row.scale_y = 1.5
                    op = row.operator("df.toggle_export_component", text="Geometry", icon='MESH_DATA', depress=props.export_geometry)
                    op.component = 'geometry'
                    op.toggle = not props.export_geometry
                    
                    # Materials button
                    row = grid.row(align=True)
                    row.scale_y = 1.5
                    op = row.operator("df.toggle_export_component", text="Materials", icon='MATERIAL', depress=props.export_materials)
                    op.component = 'materials'
                    op.toggle = not props.export_materials
                    
                    # Transform button
                    row = grid.row(align=True)
                    row.scale_y = 1.5
                    op = row.operator("df.toggle_export_component", text="Transform", icon='ORIENTATION_GLOBAL', depress=props.export_transform)
                    op.component = 'transform'
                    op.toggle = not props.export_transform
                    
                    # UV Layout button
                    row = grid.row(align=True)
                    row.scale_y = 1.5
                    op = row.operator("df.toggle_export_component", text="UV Layout", icon='UV', depress=props.export_uv)
                    op.component = 'uv'
                    op.toggle = not props.export_uv
                
        # Full Project mode
        else:
            # Show working directory status (if available)
            box = layout.box()
            box.label(text="Full Project Commit", icon='FILE_FOLDER')
            # TODO: Show file count, changes, etc.
        
        # Common fields
        layout.separator()
        
        # Branch (display as text)
        row = layout.row()
        row.label(text="Branch:")
        current_branch = get_current_branch_name(context)
        row.label(text=current_branch)
        
        # Message
        layout.prop(props, "message", text="Message")
        
        # Create commit button (no error messages, no disabled states)
        layout.separator()
        
        if props.commit_mode == 'SELECTED_OBJECT':
            if selected_objects:
                row = layout.row()
                row.operator("df.create_mesh_commit", text="Create Commit", icon='EXPORT')
            else:
                row = layout.row()
                row.operator("df.create_mesh_commit", text="Create Commit", icon='EXPORT')
        else:
            row = layout.row()
            row.operator("df.create_project_commit", text="Create Commit", icon='EXPORT')



class DF_PT_branch_panel(Panel):
    """Panel for branch management."""
    bl_label = "Branch Management"
    bl_idname = "DF_PT_branch_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Difference Machine"
    bl_order = 1

    def draw(self, context):
        """Draw the panel UI."""
        layout = self.layout
        scene = context.scene
        props = context.scene.df_commit_props
        
        # Проверяем, является ли активный объект объектом сравнения
        active_obj = context.active_object
        comparison_obj_name = getattr(scene, 'df_comparison_object_name', None)
        is_comparison_object = (active_obj and 
                               active_obj.type == 'MESH' and 
                               comparison_obj_name and 
                               active_obj.name == comparison_obj_name)
        
        # Check repository state
        from ..operators.operator_helpers import check_repository_state, is_repository_initialized
        file_saved, repo_exists, has_branches, error_msg = check_repository_state(context)
        repo_initialized = is_repository_initialized(context)
        
        # Refresh button (всегда доступен для просмотра)
        row = layout.row()
        row.operator("df.refresh_branches", text="Refresh Branches", icon='FILE_REFRESH')
        
        # Init project button (show only if repository not initialized)
        if not repo_initialized:
            layout.separator()
            row = layout.row()
            row.scale_y = 1.2
            row.operator("df.init_project", text="Init Project", icon='FILE_NEW')
        
        # Show error message only if file not saved
        if not file_saved:
            layout.separator()
            box = layout.box()
            box.label(text="Please save the Blender file first", icon='ERROR')
        
        # Auto-refresh if list is empty and file is saved and repo initialized
        branches = scene.df_branches
        if len(branches) == 0 and bpy.data.filepath and repo_initialized:
            # Try to auto-load
            try:
                bpy.ops.df.refresh_branches()
            except:
                pass
        
        # List branches using UIList (only if repo initialized)
        if repo_initialized:
            if len(branches) == 0:
                box = layout.box()
                box.label(text="No branches found", icon='INFO')
                box.label(text="Click Refresh to load")
            else:
                # UIList for branches (stretchable)
                row = layout.row()
                row.template_list(
                    "DF_UL_branch_list", "",
                    scene, "df_branches",
                    scene, "df_branch_list_index",
                    rows=6  # Default 6 rows, stretchable
                )
        
        # Branch operations (скрываем для объекта сравнения, показываем только если repo initialized)
        if not is_comparison_object and repo_initialized:
            layout.separator()
            
            col = layout.column(align=True)
            # Buttons always enabled (no disabled states)
            create_row = col.row()
            create_row.operator("df.create_branch", text="Create New Branch", icon='ADD')
            
            switch_row = col.row()
            switch_row.operator("df.switch_branch", text="Switch Branch", icon='ARROW_LEFTRIGHT')
            
            # Delete branch button (only if branch is selected)
            if (branches and 
                hasattr(scene, 'df_branch_list_index') and
                scene.df_branch_list_index >= 0 and 
                scene.df_branch_list_index < len(branches)):
                layout.separator()
                selected_branch = branches[scene.df_branch_list_index]
                
                # Can delete if more than one branch and not current
                can_delete = (len(branches) > 1 and not selected_branch.is_current)
                
                row = layout.row()
                row.enabled = can_delete
                row.scale_y = 1.2
                op = row.operator("df.delete_branch", text="Delete Branch", icon='TRASH')
                op.branch_name = selected_branch.name
                
                if not can_delete:
                    layout.separator()
                    info_row = layout.row()
                    if len(branches) <= 1:
                        info_row.label(text="Cannot delete the last branch", icon='INFO')
                    elif selected_branch.is_current:
                        info_row.label(text="Cannot delete current branch", icon='INFO')
        else:
            # Показываем информационное сообщение для объекта сравнения
            layout.separator()
            box = layout.box()
            box.label(text="Comparison mode active", icon='INFO')
            box.label(text="Only viewing is available")

class DF_PT_history_panel(Panel):
    """Panel for viewing commit history."""
    bl_label = "Load Commit"
    bl_idname = "DF_PT_history_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Difference Machine"
    bl_order = 3

    @classmethod
    def poll(cls, context):
        """Show panel only if repository is initialized."""
        from ..operators.operator_helpers import is_repository_initialized
        return is_repository_initialized(context)

    def draw(self, context):
        """Draw the panel UI."""
        layout = self.layout
        
        # Проверяем, является ли активный объект объектом сравнения
        active_obj = context.active_object
        scene = context.scene
        comparison_obj_name = getattr(scene, 'df_comparison_object_name', None)
        is_comparison_object = (active_obj and 
                               active_obj.type == 'MESH' and 
                               comparison_obj_name and 
                               active_obj.name == comparison_obj_name)
        
        # Refresh button (всегда доступен для просмотра)
        row = layout.row()
        row.operator("df.refresh_history", icon='FILE_REFRESH')
        
        # Branch (display as text)
        props = context.scene.df_commit_props
        row = layout.row()
        row.label(text="Branch:")
        current_branch = get_current_branch_name(context)
        row.label(text=current_branch)
        
        # Auto-refresh if list is empty and file is saved
        commits = context.scene.df_commits
        if len(commits) == 0 and bpy.data.filepath:
            # Try to auto-load
            try:
                bpy.ops.df.refresh_history()
            except:
                pass
        
        # List commits using UIList
        if len(commits) == 0:
            box = layout.box()
            box.label(text="No commits found", icon='INFO')
            box.label(text="Click Refresh to load")
        else:
            # UIList for commits
            row = layout.row()
            row.template_list(
                "DF_UL_commit_list", "",
                context.scene, "df_commits",
                context.scene, "df_commit_list_index",
                rows=5
            )
            
            # Selected commit details
            if commits and 0 <= context.scene.df_commit_list_index < len(commits):
                commit = commits[context.scene.df_commit_list_index]
                box = layout.box()
                
                # Commit details
                if commit.selected_mesh_names:
                    box.label(text=f"Meshes: {commit.selected_mesh_names}")
                box.label(text=f"Author: {commit.author}")
                box.label(text=f"Hash: {commit.hash[:16]}...")
                
                # Проверяем, является ли активный объект объектом сравнения
                scene = context.scene
                active_obj = context.active_object
                comparison_obj_name = getattr(scene, 'df_comparison_object_name', None)
                comparison_commit_hash = getattr(scene, 'df_comparison_commit_hash', None)
                is_comparison_object = (active_obj and 
                                       active_obj.type == 'MESH' and 
                                       comparison_obj_name and 
                                       active_obj.name == comparison_obj_name)
                
                # Action buttons - для mesh_only коммитов показываем Replace и Compare
                if commit.commit_type == "mesh_only":
                    # Проверка: показываем кнопки только если выбранный объект есть в коммите
                    mesh_names_str = commit.selected_mesh_names or ""
                    
                    # Парсим selected_mesh_names (может быть JSON строка или обычная строка)
                    try:
                        import json
                        if mesh_names_str.startswith('['):
                            mesh_names = json.loads(mesh_names_str)
                        else:
                            # Если это строка с запятыми
                            mesh_names = [name.strip() for name in mesh_names_str.split(',') if name.strip()]
                    except:
                        mesh_names = [mesh_names_str] if mesh_names_str else []
                    
                    # Если активен объект сравнения, показываем кнопки только для коммита, который использовался для его создания
                    if is_comparison_object:
                        if commit.hash == comparison_commit_hash:
                            # Показываем только кнопку Compare в зажатом состоянии
                            layout.separator()
                            row = layout.row(align=True)
                            row.scale_y = 1.5
                            op = row.operator("df.compare_mesh", text="Compare", icon='SPLIT_HORIZONTAL', depress=True)
                            op.commit_hash = comparison_commit_hash
                            
                            # Кнопки выбора осей
                            layout.separator()
                            box = layout.box()
                            box.label(text="Axis Selection:", icon='AXIS_FRONT')
                            row = box.row(align=True)
                            row.scale_y = 1.3
                            
                            current_axis = getattr(scene, 'df_comparison_axis', 'X')
                            
                            # X axis button
                            op = row.operator("df.switch_comparison_axis", text="X", depress=(current_axis == 'X'))
                            op.axis = 'X'
                            
                            # Y axis button
                            op = row.operator("df.switch_comparison_axis", text="Y", depress=(current_axis == 'Y'))
                            op.axis = 'Y'
                            
                            # Z axis button
                            op = row.operator("df.switch_comparison_axis", text="Z", depress=(current_axis == 'Z'))
                            op.axis = 'Z'
                        # Для других коммитов не показываем кнопки
                    else:
                        # Проверяем, есть ли активный объект в списке мешей коммита
                        show_buttons = False
                        if active_obj and active_obj.type == 'MESH' and active_obj.name in mesh_names:
                            show_buttons = True
                        
                        if show_buttons:
                            # Replace и Compare в одной строке
                            layout.separator()
                            row = layout.row(align=True)
                            row.scale_y = 1.5
                            op = row.operator("df.replace_mesh", text="Replace This Mesh", icon='FILE_REFRESH')
                            op.commit_hash = commit.hash
                            
                            # Compare button with pressed state
                            is_comparison_active = getattr(context.scene, 'df_comparison_active', False)
                            op = row.operator("df.compare_mesh", text="Compare", icon='SPLIT_HORIZONTAL', depress=is_comparison_active)
                            op.commit_hash = commit.hash
                            
                            # Кнопки выбора осей (показываем всегда, когда можно создать объект сравнения)
                            layout.separator()
                            box = layout.box()
                            box.label(text="Axis Selection:", icon='AXIS_FRONT')
                            row = box.row(align=True)
                            row.scale_y = 1.3
                            
                            current_axis = getattr(scene, 'df_comparison_axis', 'X')
                            
                            # X axis button
                            op = row.operator("df.switch_comparison_axis", text="X", depress=(current_axis == 'X'))
                            op.axis = 'X'
                            
                            # Y axis button
                            op = row.operator("df.switch_comparison_axis", text="Y", depress=(current_axis == 'Y'))
                            op.axis = 'Y'
                            
                            # Z axis button
                            op = row.operator("df.switch_comparison_axis", text="Z", depress=(current_axis == 'Z'))
                            op.axis = 'Z'
                        else:
                            # Показываем сообщение, если объект не выбран или не совпадает
                            layout.separator()
                            box = layout.box()
                            if not active_obj or active_obj.type != 'MESH':
                                box.label(text="Select a mesh object to load/replace", icon='INFO')
                            elif mesh_names:
                                box.label(text=f"Select one of: {', '.join(mesh_names)}", icon='INFO')
                            else:
                                box.label(text="No meshes in this commit", icon='INFO')
                    
                    # Delete button (скрываем для объекта сравнения)
                    if not is_comparison_object:
                        layout.separator()
                        row = layout.row()
                        row.scale_y = 1.2
                        op = row.operator("df.delete_commit", text="Delete This Version", icon='TRASH')
                        op.commit_hash = commit.hash
                else:
                    # Для обычных коммитов - Checkout, Open project state, Compare и Delete
                    # Скрываем кнопки, если активен объект сравнения
                    if not is_comparison_object:
                        # Checkout button (explicit checkout to working directory)
                        layout.separator()
                        row = layout.row()
                        row.scale_y = 1.5
                        op = row.operator("df.checkout_commit", text="Checkout to Working Directory", icon='CHECKMARK')
                        op.commit_hash = commit.hash
                        
                        # Open project state и Compare в одной строке
                        layout.separator()
                        row = layout.row(align=True)
                        row.scale_y = 1.2
                        op = row.operator("df.open_project_state", text="Open Project", icon='FILE_FOLDER')
                        op.commit_hash = commit.hash
                        
                        # Check if project comparison is active for this commit
                        is_project_comparison_active = (
                            getattr(scene, 'df_project_comparison_active', False) and
                            getattr(scene, 'df_project_comparison_commit_hash', '') == commit.hash
                        )
                        
                        op = row.operator("df.compare_project", text="Compare", icon='SPLIT_HORIZONTAL', depress=is_project_comparison_active)
                        op.commit_hash = commit.hash
                        
                        layout.separator()
                        row = layout.row()
                        row.scale_y = 1.2
                        op = row.operator("df.delete_commit", text="Delete This Version", icon='TRASH')
                        op.commit_hash = commit.hash
