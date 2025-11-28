"""
Main UI module for Difference Machine add-on.
Contains panels and menus registration.
"""
import bpy
from .ui_panels import (
    DF_PT_commit_panel,
    DF_PT_history_panel,
    DF_PT_branch_panel,
)
from .ui_lists import (
    DF_UL_branch_list,
    DF_UL_commit_list,
)
from ..operators.commit_operators import (
    DF_OT_create_project_commit,
    DF_OT_create_mesh_commit,
    DF_OT_refresh_history,
    DF_OT_refresh_branches,
    DF_OT_create_branch,
    DF_OT_switch_branch,
    DF_OT_delete_branch,
    DF_OT_init_project,
    DF_OT_rebuild_database,
)
from ..operators.history_operators import (
    DF_OT_select_commit,
    DF_OT_checkout_commit,
    DF_OT_delete_commit,
    DF_OT_replace_mesh,
    DF_OT_compare_mesh,
    DF_OT_load_mesh_version,
    DF_OT_open_project_state,
    DF_OT_compare_project,
    DF_OT_switch_comparison_axis,
)
from ..operators.branch_operators import (
    DF_OT_sort_branches,
)
from ..operators.export_operators import (
    DF_OT_toggle_export_component,
)
# Classes list for registration
classes = [
    # UI Lists
    DF_UL_branch_list,
    DF_UL_commit_list,
    # Panels
    DF_PT_commit_panel,
    DF_PT_history_panel,
    DF_PT_branch_panel,
    # Operators
    DF_OT_create_project_commit,
    DF_OT_create_mesh_commit,
    DF_OT_refresh_history,
    DF_OT_refresh_branches,
    DF_OT_create_branch,
    DF_OT_switch_branch,
    DF_OT_delete_branch,
    DF_OT_init_project,
    DF_OT_rebuild_database,
    # History operators
    DF_OT_select_commit,
    DF_OT_checkout_commit,
    DF_OT_delete_commit,
    DF_OT_replace_mesh,
    DF_OT_compare_mesh,
    DF_OT_load_mesh_version,
    DF_OT_open_project_state,
    DF_OT_compare_project,
    DF_OT_switch_comparison_axis,
    # Branch operators
    DF_OT_sort_branches,
    # Export operators
    DF_OT_toggle_export_component,
]


def register():
    """Register UI classes and properties"""
    try:
        # Register UI classes
        for cls in classes:
            bpy.utils.register_class(cls)
    except Exception as e:
        print(f"Error registering UI classes: {e}")
        raise


def unregister():
    try:
        # Unregister UI classes
        for cls in reversed(classes):
            bpy.utils.unregister_class(cls)
    except Exception as e:
        print(f"Error unregistering UI classes: {e}")
        raise
