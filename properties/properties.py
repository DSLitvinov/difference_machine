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
    bpy.types.Scene.df_commit_list_index = bpy.props.IntProperty(name="Commit List Index", default=0)
    
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
