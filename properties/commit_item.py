"""
Property items for commit and branch lists.
"""

import bpy
from bpy.props import StringProperty, IntProperty, BoolProperty


class DFCommitItem(bpy.types.PropertyGroup):
    """Property group for a single commit in the list."""
    
    hash: StringProperty(name="Hash")
    message: StringProperty(name="Message")
    author: StringProperty(name="Author")
    timestamp: IntProperty(name="Timestamp")
    commit_type: StringProperty(name="Type", default="project")
    selected_mesh_names: StringProperty(name="Mesh Names")  # JSON string
    is_selected: BoolProperty(name="Selected", default=False)


class DFBranchItem(bpy.types.PropertyGroup):
    """Property group for a single branch in the list."""
    
    name: StringProperty(name="Name")
    commit_count: IntProperty(name="Commit Count", default=0)
    last_commit_hash: StringProperty(name="Last Commit Hash")
    last_commit_message: StringProperty(name="Last Commit Message")
    is_current: BoolProperty(name="Current", default=False)


def register():
    """Register property groups."""
    # Try to unregister first (for reload scenarios)
    try:
        bpy.utils.unregister_class(DFCommitItem)
    except (RuntimeError, ValueError):
        pass
    
    try:
        bpy.utils.unregister_class(DFBranchItem)
    except (RuntimeError, ValueError):
        pass
    
    # Register classes
    bpy.utils.register_class(DFCommitItem)
    bpy.utils.register_class(DFBranchItem)


def unregister():
    """Unregister property groups."""
    try:
        bpy.utils.unregister_class(DFBranchItem)
    except (RuntimeError, ValueError):
        pass
    
    try:
        bpy.utils.unregister_class(DFCommitItem)
    except (RuntimeError, ValueError):
        pass

