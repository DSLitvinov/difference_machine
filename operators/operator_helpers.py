"""
Helper functions for operators to reduce code duplication.
"""

import bpy
import logging
from pathlib import Path
from typing import Optional, Tuple
from ..forester.commands import find_repository, list_branches, init_repository
from ..forester.core.refs import get_branch_ref, get_current_branch
from ..forester.core.database import ForesterDB

logger = logging.getLogger(__name__)


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
    if not bpy.data.filepath:
        error_msg = "Please save the Blender file first"
        if operator:
            operator.report({'ERROR'}, error_msg)
        return None, error_msg
    
    blend_file = Path(bpy.data.filepath)
    repo_path = find_repository(blend_file.parent)
    if not repo_path:
        error_msg = "Not a Forester repository"
        if operator:
            operator.report({'ERROR'}, error_msg)
        return None, error_msg
    
    return repo_path, None


def is_repository_initialized(context) -> bool:
    """
    Check if repository is initialized (has .DFM folder and database).
    
    Args:
        context: Blender context
        
    Returns:
        True if .DFM folder and forester.db exist, False otherwise
    """
    if not bpy.data.filepath:
        return False
    
    blend_file = Path(bpy.data.filepath)
    project_root = blend_file.parent
    dfm_dir = project_root / ".DFM"
    db_path = dfm_dir / "forester.db"
    
    return dfm_dir.exists() and db_path.exists()


def check_repository_state(context) -> Tuple[bool, bool, bool, Optional[str]]:
    """
    Check repository state: file saved, repository exists, branches exist.
    
    Args:
        context: Blender context
        
    Returns:
        Tuple of (file_saved, repo_exists, has_branches, error_message)
    """
    # Check if file is saved
    if not bpy.data.filepath:
        return (False, False, False, "Please save the Blender file first")
    
    blend_file = Path(bpy.data.filepath)
    
    # Check if repository exists
    project_root = blend_file.parent
    repo_path = find_repository(project_root)
    if not repo_path:
        # Check if .DFM directory exists
        dfm_dir = project_root / ".DFM"
        if not dfm_dir.exists():
            return (True, False, False, "Repository not initialized. Please create a project folder and save the Blender file in it.")
        return (True, False, False, "Repository not found")
    
    # Check if branches exist
    try:
        branches = list_branches(repo_path)
        has_branches = len(branches) > 0
        return (True, True, has_branches, None if has_branches else "No branches found. Please create a branch first.")
    except Exception as e:
        return (True, True, False, f"Error checking branches: {str(e)}")


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
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to process {obj.name}: {e}")
            continue
    return results


def ensure_repository_and_branch(context, operator) -> Tuple[Optional[Path], Optional[str]]:
    """
    Ensure repository exists and branch is ready for commit operations.
    
    Args:
        context: Blender context
        operator: Operator instance for error reporting
        
    Returns:
        Tuple of (repo_path, error_message)
        If successful: (Path, None)
        If error: (None, error_message)
    """
    # Check if file is saved
    if not bpy.data.filepath:
        error_msg = "Please save the Blender file first"
        operator.report({'ERROR'}, error_msg)
        return None, error_msg
    
    blend_file = Path(bpy.data.filepath)
    project_root = blend_file.parent
    
    # Check if repository exists
    repo_path = find_repository(project_root)
    if not repo_path:
        # Initialize repository
        try:
            init_repository(project_root)
            repo_path = project_root
            operator.report({'INFO'}, "Repository initialized")
        except (ValueError, OSError, PermissionError) as e:
            error_msg = f"Failed to initialize repository: {str(e)}"
            operator.report({'ERROR'}, error_msg)
            logger.error(f"Failed to initialize repository: {e}", exc_info=True)
            return None, error_msg
        except Exception as e:
            error_msg = f"Failed to initialize repository: {str(e)}"
            operator.report({'ERROR'}, error_msg)
            logger.error(f"Unexpected error initializing repository: {e}", exc_info=True)
            return None, error_msg
    
    # Check if branches exist
    try:
        from ..forester.commands import list_branches
        branches = list_branches(repo_path)
        if len(branches) == 0:
            error_msg = (
                "No branches found. Please create a branch first.\n"
                "Go to Branch Management panel and click 'Create New Branch'."
            )
            operator.report({'ERROR'}, error_msg)
            return None, error_msg
    except Exception as e:
        error_msg = f"Error checking branches: {str(e)}"
        operator.report({'ERROR'}, error_msg)
        logger.error(f"Error checking branches: {e}", exc_info=True)
        return None, error_msg
    
    # Get current branch and ensure it exists
    branch_name = get_current_branch(repo_path) or "main"
    branch_ref = get_branch_ref(repo_path, branch_name)
    
    if branch_ref is None:
        # Branch doesn't exist, create it
        try:
            from ..forester.commands import create_branch
            create_branch(repo_path, branch_name)
            # Update current branch in database
            db_path = repo_path / ".DFM" / "forester.db"
            if db_path.exists():
                with ForesterDB(db_path) as db:
                    db.set_current_branch(branch_name)
            operator.report({'INFO'}, f"Branch '{branch_name}' created")
        except ValueError:
            # Branch might already exist (race condition), that's okay
            logger.debug(f"Branch '{branch_name}' might already exist (race condition)")
        except Exception as e:
            logger.warning(f"Failed to create branch '{branch_name}': {e}")
    
    return repo_path, None


def validate_branch_name(name: str) -> Tuple[bool, Optional[str]]:
    """
    Validate branch name according to git-like rules.
    
    Args:
        name: Branch name to validate
        
    Returns:
        Tuple of (is_valid, error_message)
        If valid: (True, None)
        If invalid: (False, error_message)
    """
    if not name:
        return False, "Branch name cannot be empty"
    
    if len(name) > 255:
        return False, "Branch name too long (max 255 characters)"
    
    # Check for forbidden patterns
    forbidden_patterns = ['..', '~', '^', ':', '?', '*', '[', '\\']
    for pattern in forbidden_patterns:
        if pattern in name:
            return False, f"Branch name cannot contain '{pattern}'"
    
    # Check for leading/trailing dots or spaces
    if name.startswith('.') or name.endswith('.'):
        return False, "Branch name cannot start or end with '.'"
    
    if name.startswith(' ') or name.endswith(' '):
        return False, "Branch name cannot start or end with space"
    
    # Check for control characters
    if any(ord(c) < 32 for c in name):
        return False, "Branch name cannot contain control characters"
    
    return True, None

