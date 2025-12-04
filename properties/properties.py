"""
Custom properties for Difference Machine add-on.
"""

import bpy
from bpy.props import (
    EnumProperty,
    StringProperty,
    BoolProperty,
    IntProperty,
    CollectionProperty,
)


class DFCommitProperties(bpy.types.PropertyGroup):
    """Properties for commit operations."""
    
    # Commit mode
    commit_mode: EnumProperty(
        name="Commit Mode",
        description="Type of commit to create",
        items=[
            ('FULL_PROJECT', "Full Project", "Commit entire working directory"),
            ('SELECTED_OBJECT', "Selected Object", "Commit only selected meshes"),
        ],
        default='FULL_PROJECT',
    )
    
    # Branch
    branch: StringProperty(
        name="Branch",
        description="Branch name",
        default="main",
    )
    
    # Commit message
    message: StringProperty(
        name="Message",
        description="Commit message",
        default="",
    )
    
    # Commit tag
    commit_tag: StringProperty(
        name="Tag",
        description="Optional tag for this commit",
        default="",
    )
    
    # Author
    author: StringProperty(
        name="Author",
        description="Author name",
        default="Unknown",
    )
    
    # Export all components toggle
    export_all: BoolProperty(
        name="Export All Components",
        description="Export all components",
        default=True,
    )
    
    # Export options (for mesh-only commits)
    export_geometry: BoolProperty(
        name="Geometry",
        description="Export geometry (vertices and faces)",
        default=True,
    )
    
    export_materials: BoolProperty(
        name="Materials",
        description="Export materials",
        default=True,
    )
    
    export_transform: BoolProperty(
        name="Transform",
        description="Export transform (normals)",
        default=True,
    )
    
    export_uv: BoolProperty(
        name="UV Layout",
        description="Export UV coordinates",
        default=True,
    )
    
    # Legacy properties for backward compatibility
    export_vertices: BoolProperty(
        name="Vertices",
        description="Export vertices",
        default=True,
    )
    
    export_faces: BoolProperty(
        name="Faces",
        description="Export faces",
        default=True,
    )
    
    export_normals: BoolProperty(
        name="Normals",
        description="Export normals",
        default=True,
    )
    
    # Auto-compress
    auto_compress: BoolProperty(
        name="Auto-compress Old Versions",
        description="Automatically delete old mesh-only commits",
        default=False,
    )
    
    keep_last_n_commits: IntProperty(
        name="Keep Last N Commits",
        description="Number of commits to keep per mesh when auto-compressing",
        default=5,
        min=1,
        max=100,
    )
    
    # Selected commit index (for history panel)
    selected_commit_index: IntProperty(
        name="Selected Commit Index",
        default=-1,
    )
    
    # Selected branch index (for branch panel)
    selected_branch_index: IntProperty(
        name="Selected Branch Index",
        default=-1,
    )
    
    # Branch search filter
    branch_search_filter: StringProperty(
        name="Branch Search",
        description="Filter branches by name",
        default="",
        options={'TEXTEDIT_UPDATE'},
    )
    
    def update_tag_filter(self, context):
        """Update callback for tag search filter - refreshes commit list."""
        # Auto-refresh history when filter changes
        # Use timer to avoid context issues during property update
        def refresh_after_update():
            try:
                bpy.ops.df.refresh_history()
            except:
                pass  # Silently fail if can't refresh
        
        # Schedule refresh for next frame
        bpy.app.timers.register(refresh_after_update, first_interval=0.1)
    
    # Tag search filter
    tag_search_filter: StringProperty(
        name="Tag Search",
        description="Filter commits by tag name",
        default="",
        options={'TEXTEDIT_UPDATE'},
        update=update_tag_filter,
    )
    
    def get_export_options(self) -> dict:
        """Get export options as dictionary."""
        # If export_all is enabled, all components are exported
        if self.export_all:
            return {
                'vertices': True,
                'faces': True,
                'uv': True,
                'normals': True,
                'materials': True,
            }
        
        # Otherwise, use individual toggles
        return {
            'vertices': self.export_geometry,  # Geometry includes vertices
            'faces': self.export_geometry,      # Geometry includes faces
            'uv': self.export_uv,
            'normals': self.export_transform,   # Transform includes normals
            'materials': self.export_materials,
        }


def update_commit_list_index(self, context):
    """Update callback for commit list index - loads commit to temp folder."""
    if hasattr(context.scene, 'df_commits') and context.scene.df_commits:
        index = context.scene.df_commit_list_index
        if 0 <= index < len(context.scene.df_commits):
            commit = context.scene.df_commits[index]
            # Only load project commits to temp folder
            if commit.commit_type == "project":
                # Load commit to temp folder directly (without toggling selection)
                try:
                    from pathlib import Path
                    from ..forester.commands import find_repository
                    from ..forester.core.database import ForesterDB
                    from ..forester.core.storage import ObjectStorage
                    from ..forester.models.commit import Commit
                    from ..forester.commands.checkout import restore_files_from_tree, restore_meshes_from_commit
                    import shutil
                    
                    # Find repository
                    blend_file = Path(bpy.data.filepath) if bpy.data.filepath else None
                    if not blend_file:
                        return
                    
                    repo_path = find_repository(blend_file.parent)
                    if not repo_path:
                        return
                    
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
                    temp_working_dir = temp_dir / f"commit_{commit.hash[:16]}"
                    
                    # Clean up if exists
                    if temp_working_dir.exists():
                        shutil.rmtree(temp_working_dir)
                    temp_working_dir.mkdir(parents=True)
                    
                    # Clean up all other old preview_temp directories (keep current one)
                    from ..operators.operator_helpers import cleanup_old_preview_temp
                    cleanup_old_preview_temp(repo_path, keep_current=str(temp_working_dir))
                    
                    db_path = dfm_dir / "forester.db"
                    with ForesterDB(db_path) as db:
                        storage = ObjectStorage(dfm_dir)
                        commit_obj = Commit.from_storage(commit.hash, db, storage)
                        
                        if not commit_obj:
                            return
                        
                        # Get tree from commit
                        tree = commit_obj.get_tree(db, storage)
                        if not tree:
                            return
                        
                        # Restore files from tree
                        restore_files_from_tree(tree, temp_working_dir, storage, db)
                        
                        # Restore meshes from commit
                        restore_meshes_from_commit(commit_obj, temp_working_dir, storage, dfm_dir)
                        
                        # Store temp directory path in scene
                        context.scene.df_preview_temp_dir = str(temp_working_dir)
                        context.scene.df_preview_commit_hash = commit.hash
                except Exception:
                    pass  # Silently fail if can't load


def register():
    """Register custom properties."""
    # Import and register item classes first
    from .commit_item import DFCommitItem, DFBranchItem
    
    # Try to unregister first (for reload scenarios)
    try:
        bpy.utils.unregister_class(DFCommitProperties)
    except (RuntimeError, ValueError):
        pass  # Class not registered yet
    
    try:
        bpy.utils.unregister_class(DFCommitItem)
    except (RuntimeError, ValueError):
        pass
    
    try:
        bpy.utils.unregister_class(DFBranchItem)
    except (RuntimeError, ValueError):
        pass
    
    # Register item classes
    bpy.utils.register_class(DFCommitItem)
    bpy.utils.register_class(DFBranchItem)
    
    # Register main properties class
    bpy.utils.register_class(DFCommitProperties)
    bpy.types.Scene.df_commit_props = bpy.props.PointerProperty(type=DFCommitProperties)
    
    # Register collections for commits and branches (after item classes are registered)
    bpy.types.Scene.df_commits = bpy.props.CollectionProperty(type=DFCommitItem)
    bpy.types.Scene.df_branches = bpy.props.CollectionProperty(type=DFBranchItem)
    
    # Index properties for UIList
    bpy.types.Scene.df_branch_list_index = bpy.props.IntProperty(name="Branch List Index", default=0)
    bpy.types.Scene.df_commit_list_index = bpy.props.IntProperty(
        name="Commit List Index", 
        default=0,
        update=update_commit_list_index
    )
    
    # Comparison state (for mesh comparison)
    bpy.types.Scene.df_comparison_active = bpy.props.BoolProperty(
        name="Comparison Active",
        default=False,
    )
    
    bpy.types.Scene.df_comparison_object_name = bpy.props.StringProperty(
        name="Comparison Object Name",
        default="",
    )
    
    bpy.types.Scene.df_original_object_name = bpy.props.StringProperty(
        name="Original Object Name",
        default="",
    )
    
    bpy.types.Scene.df_comparison_commit_hash = bpy.props.StringProperty(
        name="Comparison Commit Hash",
        default="",
    )
    
    bpy.types.Scene.df_comparison_axis = bpy.props.EnumProperty(
        name="Comparison Axis",
        description="Axis for comparison object offset",
        items=[
            ('X', 'X', 'Offset along X axis'),
            ('Y', 'Y', 'Offset along Y axis'),
            ('Z', 'Z', 'Offset along Z axis'),
        ],
        default='X',
    )
    
    # Project comparison state
    bpy.types.Scene.df_project_comparison_active = bpy.props.BoolProperty(
        name="Project Comparison Active",
        default=False,
    )
    
    bpy.types.Scene.df_project_comparison_commit_hash = bpy.props.StringProperty(
        name="Project Comparison Commit Hash",
        default="",
    )
    
    bpy.types.Scene.df_project_comparison_temp_dir = bpy.props.StringProperty(
        name="Project Comparison Temp Directory",
        default="",
    )
    
    # Preview commit state (for loading commit to temp folder on selection)
    bpy.types.Scene.df_preview_temp_dir = bpy.props.StringProperty(
        name="Preview Temp Directory",
        default="",
    )
    
    bpy.types.Scene.df_preview_commit_hash = bpy.props.StringProperty(
        name="Preview Commit Hash",
        default="",
    )
    
    # Diff visualization properties
    bpy.types.Scene.df_diff_color_scheme = bpy.props.EnumProperty(
        name="Diff Color Scheme",
        description="Color scheme for diff visualization",
        items=[
            ('displacement', 'Displacement', 'Color by vertex displacement magnitude'),
            ('added', 'Added', 'Green for added vertices'),
            ('removed', 'Removed', 'Red for removed vertices'),
            ('modified', 'Modified', 'Yellow for modified vertices'),
        ],
        default='displacement',
    )


def unregister():
    """Unregister custom properties."""
    from .commit_item import DFCommitItem, DFBranchItem
    
    # Unregister collections and index properties first
    if hasattr(bpy.types.Scene, 'df_commits'):
        try:
            del bpy.types.Scene.df_commits
        except:
            pass
    
    if hasattr(bpy.types.Scene, 'df_branches'):
        try:
            del bpy.types.Scene.df_branches
        except:
            pass
    
    if hasattr(bpy.types.Scene, 'df_branch_list_index'):
        try:
            del bpy.types.Scene.df_branch_list_index
        except:
            pass
    
    if hasattr(bpy.types.Scene, 'df_commit_list_index'):
        try:
            del bpy.types.Scene.df_commit_list_index
        except:
            pass
    
    if hasattr(bpy.types.Scene, 'df_commit_props'):
        try:
            del bpy.types.Scene.df_commit_props
        except:
            pass
    
    # Unregister comparison properties
    if hasattr(bpy.types.Scene, 'df_comparison_active'):
        try:
            del bpy.types.Scene.df_comparison_active
        except:
            pass
    
    if hasattr(bpy.types.Scene, 'df_comparison_object_name'):
        try:
            del bpy.types.Scene.df_comparison_object_name
        except:
            pass
    
    if hasattr(bpy.types.Scene, 'df_original_object_name'):
        try:
            del bpy.types.Scene.df_original_object_name
        except:
            pass
    
    if hasattr(bpy.types.Scene, 'df_comparison_commit_hash'):
        try:
            del bpy.types.Scene.df_comparison_commit_hash
        except:
            pass
    
    if hasattr(bpy.types.Scene, 'df_comparison_axis'):
        try:
            del bpy.types.Scene.df_comparison_axis
        except:
            pass
    
    # Unregister project comparison properties
    if hasattr(bpy.types.Scene, 'df_project_comparison_active'):
        try:
            del bpy.types.Scene.df_project_comparison_active
        except:
            pass
    
    if hasattr(bpy.types.Scene, 'df_project_comparison_commit_hash'):
        try:
            del bpy.types.Scene.df_project_comparison_commit_hash
        except:
            pass
    
    if hasattr(bpy.types.Scene, 'df_project_comparison_temp_dir'):
        try:
            del bpy.types.Scene.df_project_comparison_temp_dir
        except:
            pass
    
    # Unregister preview properties
    if hasattr(bpy.types.Scene, 'df_preview_temp_dir'):
        try:
            del bpy.types.Scene.df_preview_temp_dir
        except:
            pass
    
    if hasattr(bpy.types.Scene, 'df_preview_commit_hash'):
        try:
            del bpy.types.Scene.df_preview_commit_hash
        except:
            pass
    
    # Unregister classes
    try:
        bpy.utils.unregister_class(DFCommitProperties)
    except (RuntimeError, ValueError):
        pass
    
    try:
        bpy.utils.unregister_class(DFBranchItem)
    except (RuntimeError, ValueError):
        pass
    
    try:
        bpy.utils.unregister_class(DFCommitItem)
    except (RuntimeError, ValueError):
        pass
