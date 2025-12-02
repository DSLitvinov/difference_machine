"""
Forester commands module.
Contains all CLI commands for repository management.
"""

from .init import init_repository, is_repository, find_repository
from .commit import create_commit, has_uncommitted_changes, get_commit_screenshot
from .branch import (
    create_branch,
    list_branches,
    delete_branch,
    get_branch_commits,
    switch_branch,
)
from .checkout import (
    checkout,
    checkout_branch,
    checkout_commit,
)
from .stash import (
    create_stash,
    list_stashes,
    apply_stash,
    delete_stash,
)
from .mesh_commit import (
    create_mesh_only_commit,
    auto_compress_mesh_commits,
    register_material_update_hook,
    unregister_material_update_hook,
)
from .delete_commit import (
    delete_commit,
)
from .rebuild_database import (
    rebuild_database,
)
from .garbage_collect import (
    garbage_collect,
)
from .locking import (
    lock_file,
    unlock_file,
    is_file_locked,
    list_locks,
    lock_files,
    unlock_files,
    check_commit_conflicts,
)
from .review import (
    add_comment,
    get_comments,
    resolve_comment,
    delete_comment,
    set_approval,
    get_approval,
    get_all_approvals,
)

__all__ = [
    "init_repository",
    "is_repository",
    "find_repository",
    "create_commit",
    "has_uncommitted_changes",
    "get_commit_screenshot",
    "lock_file",
    "unlock_file",
    "is_file_locked",
    "list_locks",
    "lock_files",
    "unlock_files",
    "check_commit_conflicts",
    "add_comment",
    "get_comments",
    "resolve_comment",
    "delete_comment",
    "set_approval",
    "get_approval",
    "get_all_approvals",
    "create_branch",
    "list_branches",
    "delete_branch",
    "get_branch_commits",
    "switch_branch",
    "checkout",
    "checkout_branch",
    "checkout_commit",
    "create_stash",
    "list_stashes",
    "apply_stash",
    "delete_stash",
    "create_mesh_only_commit",
    "auto_compress_mesh_commits",
    "register_material_update_hook",
    "unregister_material_update_hook",
    "delete_commit",
    "rebuild_database",
    "garbage_collect",
]

