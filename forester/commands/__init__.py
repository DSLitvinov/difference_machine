"""
Forester commands module.
Contains all CLI commands for repository management.
"""

from .init import init_repository, is_repository, find_repository
from .commit import create_commit, has_uncommitted_changes
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
)
from .delete_commit import (
    delete_commit,
)

__all__ = [
    "init_repository",
    "is_repository",
    "find_repository",
    "create_commit",
    "has_uncommitted_changes",
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
    "delete_commit",
]

