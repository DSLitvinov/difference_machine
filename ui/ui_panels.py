"""
UI panels for Difference Machine add-on.
"""

import bpy
from bpy.types import Panel


class DF_PT_commit_panel(Panel):
    """Panel for creating commits."""
    bl_label = "Create Commit"
    bl_idname = "DF_PT_commit_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Difference Machine"
    bl_order = 1

    def draw(self, context):
        """Draw the panel UI."""
        layout = self.layout
        props = context.scene.df_commit_props
        
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
                
                # Auto-compress (separated, only for Selected Object mode)
                layout.separator()
                box = layout.box()
                box.prop(props, "auto_compress", text="Auto-compress Old Versions", toggle=True)
                if props.auto_compress:
                    box.prop(props, "keep_last_n_commits")
        
        # Full Project mode
        else:
            # Show working directory status (if available)
            box = layout.box()
            box.label(text="Full Project Commit", icon='FILE_FOLDER')
            # TODO: Show file count, changes, etc.
        
        # Common fields
        layout.separator()
        
        # Branch
        row = layout.row()
        row.label(text="Branch:")
        row.prop(props, "branch", text="")
        
        # Tag
        row = layout.row()
        row.label(text="Tag:")
        row.prop(props, "tag", text="")
        
        # Message
        layout.prop(props, "message", text="Message")
        
        # Author
        layout.prop(props, "author", text="Author")
        
        # Create commit button
        layout.separator()
        if props.commit_mode == 'SELECTED_OBJECT':
            if selected_objects:
                layout.operator("df.create_mesh_commit", text="Create Commit", icon='EXPORT')
            else:
                # Disabled button when no objects selected
                row = layout.row()
                row.enabled = False
                row.operator("df.create_mesh_commit", text="Create Commit", icon='EXPORT')
        else:
            layout.operator("df.create_project_commit", text="Create Commit", icon='EXPORT')


class DF_PT_history_panel(Panel):
    """Panel for viewing commit history."""
    bl_label = "Version History"
    bl_idname = "DF_PT_history_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Difference Machine"
    bl_order = 2

    def draw(self, context):
        """Draw the panel UI."""
        layout = self.layout
        
        # Refresh button
        row = layout.row()
        row.operator("df.refresh_history", icon='FILE_REFRESH')
        
        # Branch selector
        props = context.scene.df_commit_props
        row = layout.row()
        row.label(text="Branch:")
        row.prop(props, "branch", text="")
        
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
                
                # Action buttons
                row = box.row(align=True)
                op = row.operator("df.checkout_commit", text="Load", icon='IMPORT')
                op.commit_hash = commit.hash
                op = row.operator("df.delete_commit", text="Delete", icon='TRASH')
                op.commit_hash = commit.hash


class DF_PT_branch_panel(Panel):
    """Panel for branch management."""
    bl_label = "Branch Management"
    bl_idname = "DF_PT_branch_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Difference Machine"
    bl_order = 3

    def draw(self, context):
        """Draw the panel UI."""
        layout = self.layout
        scene = context.scene
        props = context.scene.df_commit_props
        
        # Refresh button
        row = layout.row()
        row.operator("df.refresh_branches", text="Refresh Branches", icon='FILE_REFRESH')
        
        # Auto-refresh if list is empty and file is saved
        branches = scene.df_branches
        if len(branches) == 0 and bpy.data.filepath:
            # Try to auto-load
            try:
                bpy.ops.df.refresh_branches()
            except:
                pass
        
        # List branches using UIList
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
        
        # Branch operations
        layout.separator()
        
        col = layout.column(align=True)
        col.operator("df.create_branch", text="Create New Branch", icon='ADD')
        col.operator("df.switch_branch", text="Switch Branch", icon='ARROW_LEFTRIGHT')
        
        # Delete branch button (only if branch is selected)
        if (branches and 
            hasattr(scene, 'df_branch_list_index') and
            scene.df_branch_list_index >= 0 and 
            scene.df_branch_list_index < len(branches)):
            layout.separator()
            row = layout.row()
            row.scale_y = 1.2
            selected_branch = branches[scene.df_branch_list_index]
            op = row.operator("df.delete_branch", text="Delete Branch", icon='TRASH')
            op.branch_name = selected_branch.name
