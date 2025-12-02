bl_info = {
    "name": "Difference Engine (Alfa).Ammonitida",
    "author": "Dmitry Litvinov <nopomuk@yandex.ru>",
    "version": (0, 5, 0),
    "blender": (4, 0, 0),
    "location": "View3D > UI > Difference Machine",
    "description": "Version control system for 3D models",
    "category": "3D View",
    "doc_url": "https://github.com/DSLitvinov/difference_machine",
}

import logging
import bpy
from pathlib import Path
from .ui import ui_main
from .properties import properties
from . import preferences
from .utils.logging_config import setup_logging

logger = logging.getLogger(__name__)

def register():
    # Setup logging
    setup_logging(log_level=logging.INFO)
    
    # Clean up old preview_temp directories on addon load
    try:
        if bpy.data.filepath:
            from .operators.operator_helpers import cleanup_old_preview_temp
            from .forester.commands import find_repository
            
            blend_file = Path(bpy.data.filepath)
            repo_path = find_repository(blend_file.parent)
            if repo_path:
                # Keep current preview if it exists in scene properties
                current_preview = None
                try:
                    if hasattr(bpy.types.Scene, 'df_preview_temp_dir'):
                        # Try to get from any available scene
                        for scene in bpy.data.scenes:
                            if hasattr(scene, 'df_preview_temp_dir') and scene.df_preview_temp_dir:
                                current_preview = scene.df_preview_temp_dir
                                break
                except Exception:
                    pass  # Ignore if context is not available
                
                # Clean up old preview_temp directories, keeping current one if it exists
                cleanup_old_preview_temp(repo_path, keep_current=current_preview)
    except Exception:
        pass  # Silently fail if cleanup can't be performed
    
    preferences.register()
    properties.register()
    ui_main.register()

def unregister():
    ui_main.unregister()
    properties.unregister()
    preferences.unregister()

if __name__ == "__main__":
    register()