# Forester Python API Reference

**Version:** 2.0  
**Last Updated:** 2025-01-XX

---

## Quick Start

```python
from pathlib import Path
from forester.api import init_repo, commit, get_branches

# Initialize repository
repo_path = Path("/path/to/project")
init_repo(repo_path)

# Create commit
commit_hash = commit(repo_path, "Initial commit", "John Doe")
print(f"Created: {commit_hash[:16]}")

# List branches
branches = get_branches(repo_path)
for branch in branches:
    print(f"{branch['name']}: {branch['commit_count']} commits")
```

---

## Table of Contents

1. [Repository Management](#repository-management)
2. [Commits](#commits)
3. [Branches](#branches)
4. [Checkout](#checkout)
5. [File Locking](#file-locking)
6. [Stash](#stash)
7. [Review Tools](#review-tools)
8. [Maintenance](#maintenance)
9. [Data Structures](#data-structures)

---

## Repository Management

### `init_repo(path, force=False) -> bool`

Initialize a new Forester repository.

**Parameters:**
- `path` (Path): Path to project directory
- `force` (bool): Reinitialize if repository exists (default: `False`)

**Returns:**
- `bool`: `True` if successful

**Raises:**
- `FileExistsError`: If repository exists and `force=False`
- `ValueError`: If path is not a directory

**Example:**
```python
from pathlib import Path
from forester.api import init_repo

success = init_repo(Path("/path/to/project"))
```

---

### `find_repo(path) -> Optional[Path]`

Find repository root from given path.

**Parameters:**
- `path` (Path): Starting path (can be subdirectory)

**Returns:**
- `Optional[Path]`: Repository root path or `None` if not found

**Example:**
```python
from forester.api import find_repo

repo_path = find_repo(Path.cwd())
if repo_path:
    print(f"Repository: {repo_path}")
```

---

### `is_repo(path) -> bool`

Check if path is a Forester repository.

**Parameters:**
- `path` (Path): Path to check

**Returns:**
- `bool`: `True` if path contains `.DFM/` directory with `forester.db`

**Example:**
```python
from forester.api import is_repo

if is_repo(Path("/path/to/project")):
    print("Valid repository")
```

---

## Commits

### `commit(path, message, author="Unknown", check_locks=True) -> Optional[str]`

Create a new commit from current working directory.

**Parameters:**
- `path` (Path): Repository path
- `message` (str): Commit message
- `author` (str): Author name (default: `"Unknown"`)
- `check_locks` (bool): Check for file locks before committing (default: `True`)

**Returns:**
- `Optional[str]`: Commit hash or `None` if no changes

**Raises:**
- `ValueError`: If repository not initialized, no changes, or files are locked

**Example:**
```python
from forester.api import commit

commit_hash = commit(repo_path, "Added new mesh", "John Doe")
if commit_hash:
    print(f"Committed: {commit_hash[:16]}")
```

---

### `has_changes(path) -> bool`

Check if there are uncommitted changes.

**Parameters:**
- `path` (Path): Repository path

**Returns:**
- `bool`: `True` if there are uncommitted changes

**Example:**
```python
from forester.api import has_changes

if has_changes(repo_path):
    print("You have uncommitted changes")
```

---

### `get_commit_info(path, commit_hash) -> Optional[Dict[str, Any]]`

Get commit information.

**Parameters:**
- `path` (Path): Repository path
- `commit_hash` (str): Commit hash

**Returns:**
- `Optional[Dict[str, Any]]`: Commit information dictionary or `None`

**Dictionary fields:**
- `hash` (str): Commit hash
- `author` (str): Author name
- `message` (str): Commit message
- `timestamp` (int): Unix timestamp
- `branch` (str): Branch name
- `commit_type` (str): `'project'` or `'mesh_only'`
- `screenshot_hash` (Optional[str]): Screenshot blob hash

**Example:**
```python
from forester.api import get_commit_info

info = get_commit_info(repo_path, "abc123...")
if info:
    print(f"Author: {info['author']}")
    print(f"Message: {info['message']}")
```

---

### `get_screenshot(path, commit_hash) -> Optional[bytes]`

Get screenshot image data for a commit.

**Parameters:**
- `path` (Path): Repository path
- `commit_hash` (str): Commit hash

**Returns:**
- `Optional[bytes]`: PNG image data as bytes or `None`

**Example:**
```python
from forester.api import get_screenshot

screenshot_data = get_screenshot(repo_path, "abc123...")
if screenshot_data:
    with open("screenshot.png", "wb") as f:
        f.write(screenshot_data)
```

---

### `delete_commit_api(path, commit_hash, force=False) -> Tuple[bool, Optional[str]]`

Delete a commit.

**Parameters:**
- `path` (Path): Repository path
- `commit_hash` (str): Commit hash to delete
- `force` (bool): Force deletion even if referenced by branches (default: `False`)

**Returns:**
- `Tuple[bool, Optional[str]]`: `(success, error_message)`

**Example:**
```python
from forester.api import delete_commit_api

success, error = delete_commit_api(repo_path, "abc123...")
if success:
    print("Commit deleted")
```

---

## Branches

### `create_branch_repo(path, branch_name, from_branch=None) -> bool`

Create a new branch.

**Parameters:**
- `path` (Path): Repository path
- `branch_name` (str): Branch name
- `from_branch` (Optional[str]): Source branch (`None` = current branch)

**Returns:**
- `bool`: `True` if successful

**Raises:**
- `ValueError`: If branch already exists

**Example:**
```python
from forester.api import create_branch_repo

create_branch_repo(repo_path, "feature/new-mesh")
```

---

### `get_branches(path) -> List[Dict[str, Any]]`

List all branches.

**Parameters:**
- `path` (Path): Repository path

**Returns:**
- `List[Dict[str, Any]]`: List of branch dictionaries

**Branch dictionary fields:**
- `name` (str): Branch name
- `commit_count` (int): Number of commits
- `last_commit` (Optional[str]): Last commit hash
- `is_current` (bool): `True` if this is the current branch

**Example:**
```python
from forester.api import get_branches

branches = get_branches(repo_path)
for branch in branches:
    print(f"{branch['name']}: {branch['commit_count']} commits")
```

---

### `switch_to_branch(path, branch_name) -> bool`

Switch to a branch.

**Parameters:**
- `path` (Path): Repository path
- `branch_name` (str): Branch name

**Returns:**
- `bool`: `True` if successful

**Raises:**
- `ValueError`: If branch doesn't exist

**Example:**
```python
from forester.api import switch_to_branch

switch_to_branch(repo_path, "feature/new-mesh")
```

---

### `delete_branch_repo(path, branch_name, force=False) -> bool`

Delete a branch.

**Parameters:**
- `path` (Path): Repository path
- `branch_name` (str): Branch name to delete
- `force` (bool): Force deletion even if it's the current branch (default: `False`)

**Returns:**
- `bool`: `True` if successful

**Raises:**
- `ValueError`: If branch doesn't exist or is current branch (unless `force=True`)

**Example:**
```python
from forester.api import delete_branch_repo

delete_branch_repo(repo_path, "old-feature")
```

---

### `get_branch_commits_api(path, branch_name) -> List[Dict[str, Any]]`

Get all commits in a branch.

**Parameters:**
- `path` (Path): Repository path
- `branch_name` (str): Branch name

**Returns:**
- `List[Dict[str, Any]]`: List of commit dictionaries, ordered from oldest to newest

**Example:**
```python
from forester.api import get_branch_commits_api

commits = get_branch_commits_api(repo_path, "main")
for commit in commits:
    print(f"{commit['hash'][:16]}: {commit['message']}")
```

---

## Checkout

### `checkout_files(path, target, force=False, file_patterns=None, mesh_names=None) -> Tuple[bool, Optional[str]]`

Checkout files from a commit or branch (with selective checkout).

**Parameters:**
- `path` (Path): Repository path
- `target` (str): Branch name or commit hash
- `force` (bool): Discard uncommitted changes (default: `False`)
- `file_patterns` (Optional[List[str]]): File path patterns to selectively checkout (e.g., `["textures/*"]`)
- `mesh_names` (Optional[List[str]]): Mesh names to selectively checkout (for `mesh_only` commits)

**Returns:**
- `Tuple[bool, Optional[str]]`: `(success, error_message)`
  - `error_message` can be `"uncommitted_changes"` if there are uncommitted changes

**Example:**
```python
from forester.api import checkout_files

# Checkout only texture files
success, error = checkout_files(
    repo_path,
    "main",
    file_patterns=["textures/*.png", "textures/*.jpg"]
)

# Checkout specific meshes
success, error = checkout_files(
    repo_path,
    "abc123...",
    mesh_names=["Mesh1", "Mesh2"]
)
```

---

## File Locking

### `lock_file_api(path, file_path, locked_by, lock_type="exclusive", branch=None, expires_after_seconds=None) -> bool`

Lock a single file.

**Parameters:**
- `path` (Path): Repository path
- `file_path` (str): Path to file to lock
- `locked_by` (str): Username/identifier
- `lock_type` (str): Type of lock - `'exclusive'` or `'shared'` (default: `'exclusive'`)
- `branch` (Optional[str]): Branch name (`None` = current branch)
- `expires_after_seconds` (Optional[int]): Lock expiration time (`None` = never)

**Returns:**
- `bool`: `True` if locked, `False` if already locked

**Example:**
```python
from forester.api import lock_file_api

if lock_file_api(repo_path, "meshes/model.json", "john_doe",
                 expires_after_seconds=3600):
    print("File locked successfully")
```

---

### `lock_files_api(path, file_paths, locked_by, lock_type="exclusive", branch=None, expires_after_seconds=None) -> Dict[str, bool]`

Lock multiple files.

**Parameters:**
- `path` (Path): Repository path
- `file_paths` (List[str]): List of file paths to lock
- `locked_by` (str): Username/identifier
- `lock_type` (str): Type of lock - `'exclusive'` or `'shared'` (default: `'exclusive'`)
- `branch` (Optional[str]): Branch name (`None` = current branch)
- `expires_after_seconds` (Optional[int]): Lock expiration time (`None` = never)

**Returns:**
- `Dict[str, bool]`: Dictionary mapping `file_path -> success`

**Example:**
```python
from forester.api import lock_files_api

results = lock_files_api(
    repo_path,
    ["meshes/model1.json", "textures/tex1.png"],
    "john_doe",
    expires_after_seconds=3600
)
for file_path, success in results.items():
    print(f"{file_path}: {'locked' if success else 'failed'}")
```

---

### `unlock_file_api(path, file_path, locked_by, branch=None) -> bool`

Unlock a single file.

**Parameters:**
- `path` (Path): Repository path
- `file_path` (str): Path to file to unlock
- `locked_by` (str): Username/identifier (must match lock owner)
- `branch` (Optional[str]): Branch name (`None` = current branch)

**Returns:**
- `bool`: `True` if unlocked, `False` if not locked or not owned

**Example:**
```python
from forester.api import unlock_file_api

unlock_file_api(repo_path, "meshes/model.json", "john_doe")
```

---

### `unlock_files_api(path, file_paths, locked_by, branch=None) -> Dict[str, bool]`

Unlock multiple files.

**Parameters:**
- `path` (Path): Repository path
- `file_paths` (List[str]): List of file paths to unlock
- `locked_by` (str): Username/identifier (must match lock owner)
- `branch` (Optional[str]): Branch name (`None` = current branch)

**Returns:**
- `Dict[str, bool]`: Dictionary mapping `file_path -> success`

**Example:**
```python
from forester.api import unlock_files_api

results = unlock_files_api(
    repo_path,
    ["meshes/model1.json", "textures/tex1.png"],
    "john_doe"
)
```

---

### `check_file_locked(path, file_path, branch=None) -> Optional[Dict[str, Any]]`

Check if a single file is locked.

**Parameters:**
- `path` (Path): Repository path
- `file_path` (str): Path to file to check
- `branch` (Optional[str]): Branch name (`None` = current branch)

**Returns:**
- `Optional[Dict[str, Any]]`: Lock information dictionary or `None` if not locked

**Lock dictionary fields:**
- `file_path` (str): File path
- `lock_type` (str): `'exclusive'` or `'shared'`
- `locked_by` (str): Username/identifier
- `locked_at` (int): Unix timestamp
- `expires_at` (Optional[int]): Expiration timestamp (`None` if never expires)
- `branch` (str): Branch name

**Example:**
```python
from forester.api import check_file_locked

lock_info = check_file_locked(repo_path, "meshes/model.json")
if lock_info:
    print(f"Locked by {lock_info['locked_by']}")
```

---

### `get_locks(path, branch=None, locked_by=None) -> List[Dict[str, Any]]`

List all active locks.

**Parameters:**
- `path` (Path): Repository path
- `branch` (Optional[str]): Filter by branch
- `locked_by` (Optional[str]): Filter by user

**Returns:**
- `List[Dict[str, Any]]`: List of lock dictionaries

**Example:**
```python
from forester.api import get_locks

locks = get_locks(repo_path, branch="main")
for lock in locks:
    print(f"{lock['file_path']} locked by {lock['locked_by']}")
```

---

### `check_conflicts(path, file_paths, locked_by=None, branch=None) -> List[Dict[str, Any]]`

Check if files are locked by other users (for commit conflicts).

**Parameters:**
- `path` (Path): Repository path
- `file_paths` (List[str]): List of file paths to check
- `locked_by` (Optional[str]): Current user (locks by this user are ignored)
- `branch` (Optional[str]): Branch name (`None` = current branch)

**Returns:**
- `List[Dict[str, Any]]`: List of locked files with lock information

**Example:**
```python
from forester.api import check_conflicts

conflicts = check_conflicts(
    repo_path,
    ["file1.json", "file2.json"],
    locked_by="john_doe"
)
if conflicts:
    print(f"{len(conflicts)} files are locked")
```

---

## Stash

### `stash_changes(path, message=None) -> Optional[str]`

Create a stash from current working directory.

**Parameters:**
- `path` (Path): Repository path
- `message` (Optional[str]): Stash message

**Returns:**
- `Optional[str]`: Stash hash or `None` if no changes

**Example:**
```python
from forester.api import stash_changes

stash_hash = stash_changes(repo_path, "WIP: new feature")
if stash_hash:
    print(f"Stashed: {stash_hash[:16]}")
```

---

### `get_stashes(path) -> List[Dict[str, Any]]`

List all stashes.

**Parameters:**
- `path` (Path): Repository path

**Returns:**
- `List[Dict[str, Any]]`: List of stash dictionaries

**Stash dictionary fields:**
- `hash` (str): Stash hash
- `message` (str): Stash message
- `timestamp` (int): Unix timestamp
- `branch` (str): Branch name

**Example:**
```python
from forester.api import get_stashes

stashes = get_stashes(repo_path)
for stash in stashes:
    print(f"{stash['hash'][:16]}: {stash['message']}")
```

---

### `apply_stash_api(path, stash_hash, force=False) -> Tuple[bool, Optional[str]]`

Apply a stash.

**Parameters:**
- `path` (Path): Repository path
- `stash_hash` (str): Stash hash
- `force` (bool): Discard uncommitted changes (default: `False`)

**Returns:**
- `Tuple[bool, Optional[str]]`: `(success, error_message)`

**Example:**
```python
from forester.api import apply_stash_api

success, error = apply_stash_api(repo_path, "abc123...")
if success:
    print("Stash applied")
```

---

### `delete_stash_api(path, stash_hash) -> bool`

Delete a stash.

**Parameters:**
- `path` (Path): Repository path
- `stash_hash` (str): Stash hash to delete

**Returns:**
- `bool`: `True` if successful

**Raises:**
- `ValueError`: If stash doesn't exist

**Example:**
```python
from forester.api import delete_stash_api

delete_stash_api(repo_path, "abc123...")
```

---

## Review Tools

### `comment_on_asset(path, asset_hash, asset_type, author, text, x=None, y=None) -> int`

Add comment to asset (mesh, blob, commit).

**Parameters:**
- `path` (Path): Repository path
- `asset_hash` (str): Hash of the asset
- `asset_type` (str): Type - `'mesh'`, `'blob'`, or `'commit'`
- `author` (str): Author name
- `text` (str): Comment text
- `x` (Optional[float]): X coordinate for annotation
- `y` (Optional[float]): Y coordinate for annotation

**Returns:**
- `int`: Comment ID

**Example:**
```python
from forester.api import comment_on_asset

comment_id = comment_on_asset(
    repo_path,
    "abc123...",
    "mesh",
    "John Doe",
    "This mesh needs fixing"
)
```

---

### `get_asset_comments(path, asset_hash, asset_type, include_resolved=False) -> List[Dict[str, Any]]`

Get comments for asset.

**Parameters:**
- `path` (Path): Repository path
- `asset_hash` (str): Hash of the asset
- `asset_type` (str): Type - `'mesh'`, `'blob'`, or `'commit'`
- `include_resolved` (bool): Include resolved comments (default: `False`)

**Returns:**
- `List[Dict[str, Any]]`: List of comment dictionaries

**Comment dictionary fields:**
- `id` (int): Comment ID
- `author` (str): Author name
- `text` (str): Comment text
- `created_at` (int): Unix timestamp
- `x` (Optional[float]): X coordinate
- `y` (Optional[float]): Y coordinate
- `resolved` (bool): `True` if resolved

**Example:**
```python
from forester.api import get_asset_comments

comments = get_asset_comments(repo_path, "abc123...", "mesh")
for comment in comments:
    print(f"{comment['author']}: {comment['text']}")
```

---

### `resolve_comment_api(path, comment_id) -> bool`

Mark comment as resolved.

**Parameters:**
- `path` (Path): Repository path
- `comment_id` (int): Comment ID to resolve

**Returns:**
- `bool`: `True` if successful

**Example:**
```python
from forester.api import resolve_comment_api

resolve_comment_api(repo_path, 123)
```

---

### `delete_comment_api(path, comment_id) -> bool`

Delete a comment.

**Parameters:**
- `path` (Path): Repository path
- `comment_id` (int): Comment ID to delete

**Returns:**
- `bool`: `True` if successful

**Example:**
```python
from forester.api import delete_comment_api

delete_comment_api(repo_path, 123)
```

---

### `approve_asset(path, asset_hash, asset_type, approver, status="approved", comment=None) -> bool`

Set approval status for asset.

**Parameters:**
- `path` (Path): Repository path
- `asset_hash` (str): Hash of the asset
- `asset_type` (str): Type - `'mesh'`, `'blob'`, or `'commit'`
- `approver` (str): Approver name
- `status` (str): Status - `'pending'`, `'approved'`, or `'rejected'` (default: `'approved'`)
- `comment` (Optional[str]): Optional comment

**Returns:**
- `bool`: `True` if successful

**Example:**
```python
from forester.api import approve_asset

approve_asset(
    repo_path,
    "abc123...",
    "mesh",
    "Reviewer1",
    "approved",
    "Looks good!"
)
```

---

### `get_asset_approvals(path, asset_hash, asset_type) -> List[Dict[str, Any]]`

Get all approvals for asset.

**Parameters:**
- `path` (Path): Repository path
- `asset_hash` (str): Hash of the asset
- `asset_type` (str): Type - `'mesh'`, `'blob'`, or `'commit'`

**Returns:**
- `List[Dict[str, Any]]`: List of approval dictionaries

**Approval dictionary fields:**
- `approver` (str): Approver name
- `status` (str): `'pending'`, `'approved'`, or `'rejected'`
- `comment` (Optional[str]): Optional comment
- `created_at` (int): Unix timestamp

**Example:**
```python
from forester.api import get_asset_approvals

approvals = get_asset_approvals(repo_path, "abc123...", "mesh")
for approval in approvals:
    print(f"{approval['approver']}: {approval['status']}")
```

---

### `get_approval_status(path, asset_hash, asset_type, approver=None) -> Optional[Dict[str, Any]]`

Get approval status from a specific approver.

**Parameters:**
- `path` (Path): Repository path
- `asset_hash` (str): Hash of the asset
- `asset_type` (str): Type - `'mesh'`, `'blob'`, or `'commit'`
- `approver` (Optional[str]): Filter by approver (`None` = get latest)

**Returns:**
- `Optional[Dict[str, Any]]`: Approval dictionary or `None`

**Example:**
```python
from forester.api import get_approval_status

approval = get_approval_status(repo_path, "abc123...", "mesh", "Reviewer1")
if approval:
    print(f"Status: {approval['status']}")
```

---

## Maintenance

### `rebuild_db(path, backup=True) -> Tuple[bool, Optional[str]]`

Rebuild database from file system storage.

Useful for recovering from database corruption.

**Parameters:**
- `path` (Path): Repository path
- `backup` (bool): Create backup of existing database before rebuilding (default: `True`)

**Returns:**
- `Tuple[bool, Optional[str]]`: `(success, error_message)`

**Example:**
```python
from forester.api import rebuild_db

success, error = rebuild_db(repo_path, backup=True)
if success:
    print("Database rebuilt successfully")
```

---

### `garbage_collect_api(path, dry_run=False) -> Tuple[bool, Optional[str], Dict[str, Any]]`

Remove unused objects from storage.

Scans for objects (blobs, trees, commits, meshes) that are not referenced by any commits and removes them.

**Parameters:**
- `path` (Path): Repository path
- `dry_run` (bool): If `True`, only report what would be deleted without actually deleting (default: `False`)

**Returns:**
- `Tuple[bool, Optional[str], Dict[str, Any]]`: `(success, error_message, statistics_dict)`

**Statistics dictionary:**
```python
{
    'commits_deleted': int,
    'trees_deleted': int,
    'blobs_deleted': int,
    'meshes_deleted': int,
    'commits_kept': int,
    'trees_kept': int,
    'blobs_kept': int,
    'meshes_kept': int
}
```

**Example:**
```python
from forester.api import garbage_collect_api

# Dry run
success, error, stats = garbage_collect_api(repo_path, dry_run=True)
if success:
    print(f"Would delete {stats['blobs_deleted']} blobs")

# Actually perform garbage collection
success, error, stats = garbage_collect_api(repo_path, dry_run=False)
if success:
    print(f"Deleted {stats['blobs_deleted']} blobs")
```

---

## Data Structures

### Commit Dictionary

```python
{
    'hash': str,                  # Commit hash
    'author': str,                # Author name
    'message': str,               # Commit message
    'timestamp': int,             # Unix timestamp
    'branch': str,                # Branch name
    'commit_type': str,           # 'project' or 'mesh_only'
    'screenshot_hash': Optional[str]  # Screenshot blob hash
}
```

### Branch Dictionary

```python
{
    'name': str,                  # Branch name
    'commit_count': int,          # Number of commits
    'last_commit': Optional[str], # Last commit hash
    'is_current': bool            # True if this is the current branch
}
```

### Lock Dictionary

```python
{
    'file_path': str,             # File path
    'lock_type': str,             # 'exclusive' or 'shared'
    'locked_by': str,             # Username/identifier
    'locked_at': int,             # Unix timestamp
    'expires_at': Optional[int],  # Expiration timestamp (None if never expires)
    'branch': str                 # Branch name
}
```

### Comment Dictionary

```python
{
    'id': int,                    # Comment ID
    'author': str,                # Author name
    'text': str,                  # Comment text
    'created_at': int,            # Unix timestamp
    'x': Optional[float],         # X coordinate (optional)
    'y': Optional[float],         # Y coordinate (optional)
    'resolved': bool              # True if resolved
}
```

### Approval Dictionary

```python
{
    'approver': str,              # Approver name
    'status': str,                # 'pending', 'approved', or 'rejected'
    'comment': Optional[str],     # Optional comment
    'created_at': int             # Unix timestamp
}
```

### Stash Dictionary

```python
{
    'hash': str,                  # Stash hash
    'message': str,               # Stash message
    'timestamp': int,             # Unix timestamp
    'branch': str                 # Branch name
}
```

---

## Error Handling

### Common Exceptions

- `ValueError`: Invalid parameters, repository not found, operation not allowed
- `FileExistsError`: Repository already exists (when initializing)
- `FileNotFoundError`: File or directory not found

### Return Values

Many functions return tuples `(success, error_message)`:
- `success` (bool): `True` if operation succeeded
- `error_message` (Optional[str]): Error description or `None` if successful

**Example:**
```python
success, error = checkout_files(repo_path, "main")
if not success:
    if error == "uncommitted_changes":
        print("You have uncommitted changes. Use force=True to discard them.")
    else:
        print(f"Error: {error}")
```

---

## Complete Examples

### Basic Workflow

```python
from pathlib import Path
from forester.api import (
    init_repo,
    commit,
    create_branch_repo,
    switch_to_branch,
    checkout_files,
    get_branches,
)

# Initialize repository
repo_path = Path("/path/to/project")
init_repo(repo_path)

# Create initial commit
commit_hash = commit(repo_path, "Initial commit", "John Doe")
print(f"Created commit: {commit_hash[:16]}")

# Create feature branch
create_branch_repo(repo_path, "feature/new-mesh")
switch_to_branch(repo_path, "feature/new-mesh")

# ... make changes ...

# Commit changes
commit_hash = commit(repo_path, "Added new mesh", "John Doe")

# Switch back to main and merge
switch_to_branch(repo_path, "main")
checkout_files(repo_path, "feature/new-mesh", force=True)

# List branches
branches = get_branches(repo_path)
for branch in branches:
    print(f"{branch['name']}: {branch['commit_count']} commits")
```

### File Locking Workflow

```python
from forester.api import (
    lock_files_api,
    unlock_files_api,
    check_conflicts,
    commit,
)

# Lock files before editing
lock_results = lock_files_api(
    repo_path,
    ["meshes/model.json", "textures/texture.png"],
    "john_doe",
    expires_after_seconds=3600
)

# Check for conflicts before committing
files_to_commit = ["meshes/model.json", "textures/texture.png"]
conflicts = check_conflicts(repo_path, files_to_commit, locked_by="john_doe")
if conflicts:
    print(f"Warning: {len(conflicts)} files are locked by others")

# ... make changes ...

# Commit changes
commit_hash = commit(repo_path, "Updated model", "john_doe")

# Unlock files
unlock_files_api(repo_path, files_to_commit, "john_doe")
```

### Review Workflow

```python
from forester.api import (
    comment_on_asset,
    get_asset_comments,
    approve_asset,
    get_asset_approvals,
    resolve_comment_api,
)

# Add comment to mesh
comment_id = comment_on_asset(
    repo_path,
    "mesh_hash_abc123...",
    "mesh",
    "Reviewer1",
    "This mesh has too many polygons",
    x=100.5,
    y=200.3
)

# Get all comments
comments = get_asset_comments(repo_path, "mesh_hash_abc123...", "mesh")
for comment in comments:
    print(f"{comment['author']}: {comment['text']}")

# Approve asset
approve_asset(
    repo_path,
    "mesh_hash_abc123...",
    "mesh",
    "Reviewer2",
    "approved",
    "Looks good after optimization"
)

# Get all approvals
approvals = get_asset_approvals(repo_path, "mesh_hash_abc123...", "mesh")
for approval in approvals:
    print(f"{approval['approver']}: {approval['status']}")

# Resolve comment after fix
resolve_comment_api(repo_path, comment_id)
```

---

## Quick Reference

| Function | Category | Returns |
|----------|----------|---------|
| `init_repo()` | Repository | `bool` |
| `find_repo()` | Repository | `Optional[Path]` |
| `is_repo()` | Repository | `bool` |
| `commit()` | Commits | `Optional[str]` |
| `has_changes()` | Commits | `bool` |
| `get_commit_info()` | Commits | `Optional[Dict]` |
| `get_screenshot()` | Commits | `Optional[bytes]` |
| `delete_commit_api()` | Commits | `Tuple[bool, str]` |
| `create_branch_repo()` | Branches | `bool` |
| `get_branches()` | Branches | `List[Dict]` |
| `switch_to_branch()` | Branches | `bool` |
| `delete_branch_repo()` | Branches | `bool` |
| `get_branch_commits_api()` | Branches | `List[Dict]` |
| `checkout_files()` | Checkout | `Tuple[bool, str]` |
| `lock_file_api()` | Locking | `bool` |
| `lock_files_api()` | Locking | `Dict[str, bool]` |
| `unlock_file_api()` | Locking | `bool` |
| `unlock_files_api()` | Locking | `Dict[str, bool]` |
| `check_file_locked()` | Locking | `Optional[Dict]` |
| `get_locks()` | Locking | `List[Dict]` |
| `check_conflicts()` | Locking | `List[Dict]` |
| `stash_changes()` | Stash | `Optional[str]` |
| `get_stashes()` | Stash | `List[Dict]` |
| `apply_stash_api()` | Stash | `Tuple[bool, str]` |
| `delete_stash_api()` | Stash | `bool` |
| `comment_on_asset()` | Review | `int` |
| `get_asset_comments()` | Review | `List[Dict]` |
| `resolve_comment_api()` | Review | `bool` |
| `delete_comment_api()` | Review | `bool` |
| `approve_asset()` | Review | `bool` |
| `get_asset_approvals()` | Review | `List[Dict]` |
| `get_approval_status()` | Review | `Optional[Dict]` |
| `rebuild_db()` | Maintenance | `Tuple[bool, str]` |
| `garbage_collect_api()` | Maintenance | `Tuple[bool, str, Dict]` |

---

**End of API Reference**

