"""
Helper functions for operators to reduce code duplication.
"""

import bpy
from pathlib import Path
from typing import Optional, Tuple
from ..forester.commands import find_repository


def get_addon_preferences(context):
    """Get addon preferences with fallback to default values."""
    try:
        # Get addon ID from the preferences module
        from .. import preferences
        addon_id = preferences.DifferenceMachinePreferences.bl_idname
        addon = context.preferences.addons.get(addon_id)
        if addon and hasattr(addon, 'preferences'):
            return addon.preferences
    except (KeyError, AttributeError, ImportError):
        pass
    
    # Fallback: return a simple object with default values
    class DefaultPreferences:
        default_author = "Unknown"
        auto_compress_keep_last_n = 5
    
    return DefaultPreferences()


def get_repository_path(operator=None) -> Tuple[Optional[Path], Optional[str]]:
    """
    Get repository path from current Blender file.
    
    Args:
        operator: Optional operator instance for error reporting
        
    Returns:
        Tuple of (repo_path, error_message)
        If successful: (Path, None)
        If error: (None, error_message)
    """
    blend_file = Path(bpy.data.filepath)
    if not blend_file:
        error_msg = "Please save the Blender file first"
        if operator:
            operator.report({'ERROR'}, error_msg)
        return None, error_msg
    
    repo_path = find_repository(blend_file.parent)
    if not repo_path:
        error_msg = "Not a Forester repository"
        if operator:
            operator.report({'ERROR'}, error_msg)
        return None, error_msg
    
    return repo_path, None


def get_active_mesh_object(operator=None) -> Tuple[Optional[bpy.types.Object], Optional[str]]:
    """
    Get active mesh object from context.
    
    Args:
        operator: Optional operator instance for error reporting
        
    Returns:
        Tuple of (mesh_object, error_message)
        If successful: (Object, None)
        If error: (None, error_message)
    """
    active_obj = bpy.context.active_object
    if not active_obj or active_obj.type != 'MESH':
        error_msg = "Please select a mesh object"
        if operator:
            operator.report({'ERROR'}, error_msg)
        return None, error_msg
    
    return active_obj, None


def process_meshes_sequentially(selected_objects, process_func, *args, **kwargs):
    """
    Process multiple meshes sequentially using a single-mesh processing function.
    
    Args:
        selected_objects: List of mesh objects to process
        process_func: Function that processes a single mesh object
                     Should accept (obj, *args, **kwargs) and return (success, result)
        *args, **kwargs: Additional arguments to pass to process_func
        
    Returns:
        List of results for successfully processed meshes
    """
    results = []
    for obj in selected_objects:
        try:
            success, result = process_func(obj, *args, **kwargs)
            if success:
                results.append(result)
        except Exception as e:
            print(f"Failed to process {obj.name}: {e}")
            continue
    return results

