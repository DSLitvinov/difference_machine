# Forester Python API Documentation

**Version:** 1.0  
**Last Updated:** 2025-01-XX

---

## Table of Contents

1. [Introduction](#introduction)
2. [Installation & Import](#installation--import)
3. [Repository Management](#repository-management)
4. [Commits](#commits)
5. [Branches](#branches)
6. [Checkout](#checkout)
7. [File Locking](#file-locking)
8. [Stash](#stash)
9. [Review Tools](#review-tools)
10. [Maintenance & Utilities](#maintenance--utilities)
11. [Data Structures](#data-structures)
12. [Error Handling](#error-handling)
13. [Examples](#examples)

---

## Introduction

Forester Python API provides a high-level interface for automating version control operations on 3D models and project files. It's designed for scripting, automation, and integration with external tools (like Qt-based UI applications).

### Key Features

- **Repository Management**: Initialize and manage Forester repositories
- **Version Control**: Create commits, manage branches, checkout files
- **File Locking**: Prevent conflicts in collaborative workflows
- **Review Tools**: Comments and approvals for assets
- **Selective Checkout**: Download only specific files or meshes
- **Stash Management**: Temporarily save uncommitted changes

---

## Installation & Import

### Import

```python
from pathlib import Path
from forester.api import (
    init_repo,
    commit,
    create_branch_repo,
    checkout_files,
    lock_files_api,
    # ... other functions
)
```

### Repository Path

Most API functions accept a `path` parameter which can be:
- Repository root directory (contains `.DFM/`)
- Any subdirectory within a repository

The API automatically finds the repository root.

---

## Repository Management

### `init_repo(path, force=False) -> bool`

Initialize a new Forester repository.

**Parameters:**
- `path` (Path): Path to project directory
- `force` (bool): Reinitialize even if repository exists (default: `False`)

**Returns:**
- `bool`: `True` if successful

**Raises:**
- `FileExistsError`: If repository exists and `force=False`
- `ValueError`: If path is not a directory

**Example:**
```python
from pathlib import Path
from forester.api import init_repo

# Initialize new repository
success = init_repo(Path("/path/to/project"))
if success:
    print("Repository initialized")
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
    print(f"Repository found at {repo_path}")
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
    print("This is a Forester repository")
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
- `Optional[str]`: Commit hash if successful, `None` if no changes detected

**Raises:**
- `ValueError`: If repository not initialized, no changes detected, or files are locked

**Example:**
```python
from forester.api import commit

commit_hash = commit(repo_path, "Added new mesh", "John Doe")
if commit_hash:
    print(f"Committed: {commit_hash[:16]}")
else:
    print("No changes to commit")
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

**Dictionary Structure:**
```python
{
    'hash': str,              # Full commit hash
    'author': str,             # Author name
    'message': str,            # Commit message
    'timestamp': int,          # Unix timestamp
    'branch': str,             # Branch name
    'commit_type': str,        # 'project' or 'mesh_only'
    'screenshot_hash': str,    # Screenshot blob hash (optional)
}
```

**Example:**
```python
from forester.api import get_commit_info

info = get_commit_info(repo_path, "abc123...")
if info:
    print(f"Author: {info['author']}")
    print(f"Message: {info['message']}")
    print(f"Timestamp: {info['timestamp']}")
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
- `force` (bool): Force deletion even if commit is referenced by branches (default: `False`)

**Returns:**
- `Tuple[bool, Optional[str]]`: `(success, error_message)`

**Example:**
```python
from forester.api import delete_commit_api

success, error = delete_commit_api(repo_path, "abc123...")
if success:
    print("Commit deleted")
else:
    print(f"Error: {error}")
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

success = create_branch_repo(repo_path, "feature/new-mesh")
if success:
    print("Branch created")
```

---

### `get_branches(path) -> List[Dict[str, Any]]`

List all branches.

**Parameters:**
- `path` (Path): Repository path

**Returns:**
- `List[Dict[str, Any]]`: List of branch information dictionaries

**Dictionary Structure:**
```python
{
    'name': str,              # Branch name
    'commit_count': int,      # Number of commits
    'last_commit': str,        # Last commit hash (optional)
    'is_current': bool,       # True if this is the current branch
}
```

**Example:**
```python
from forester.api import get_branches

branches = get_branches(repo_path)
for branch in branches:
    print(f"{branch['name']}: {branch['commit_count']} commits")
    if branch['is_current']:
        print("  (current)")
```

---

### `switch_to_branch(path, branch_name) -> bool`

Switch to a branch (without checkout).

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

success = switch_to_branch(repo_path, "feature/new-mesh")
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

success = delete_branch_repo(repo_path, "old-feature")
```

---

### `get_branch_commits_api(path, branch_name) -> List[Dict[str, Any]]`

Get all commits in a branch.

**Parameters:**
- `path` (Path): Repository path
- `branch_name` (str): Name of branch

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
  - `error_message` contains `"uncommitted_changes"` if there are uncommitted changes

**Example:**
```python
from forester.api import checkout_files

# Checkout only texture files
success, error = checkout_files(
    repo_path, 
    "main",
    file_patterns=["textures/*.png"]
)

# Checkout specific meshes
success, error = checkout_files(
    repo_path,
    "abc123...",
    mesh_names=["Mesh1", "Mesh2"]
)

# Full checkout
success, error = checkout_files(repo_path, "main", force=True)
```

**Pattern Matching:**
- `"textures/*"` - All files in textures directory
- `"*.json"` - All JSON files
- `"models/**"` - All files in models directory and subdirectories

---

## File Locking

### `lock_file_api(path, file_path, locked_by, lock_type="exclusive", branch=None, expires_after_seconds=None) -> bool`

Lock a single file.

**Parameters:**
- `path` (Path): Repository path
- `file_path` (str): Path to file to lock (relative to repository root)
- `locked_by` (str): Username/identifier
- `lock_type` (str): Type of lock (`"exclusive"` or `"shared"`) (default: `"exclusive"`)
- `branch` (Optional[str]): Branch name (`None` = current branch)
- `expires_after_seconds` (Optional[int]): Lock expiration time in seconds (`None` = never expires)

**Returns:**
- `bool`: `True` if locked, `False` if already locked by another user

**Example:**
```python
from forester.api import lock_file_api

if lock_file_api(repo_path, "meshes/model.json", "john_doe", expires_after_seconds=3600):
    print("File locked successfully")
else:
    print("File is already locked")
```

---

### `lock_files_api(path, file_paths, locked_by, lock_type="exclusive", branch=None, expires_after_seconds=None) -> Dict[str, bool]`

Lock multiple files.

**Parameters:**
- `path` (Path): Repository path
- `file_paths` (List[str]): List of file paths to lock
- `locked_by` (str): Username/identifier
- `lock_type` (str): Type of lock (`"exclusive"` or `"shared"`) (default: `"exclusive"`)
- `branch` (Optional[str]): Branch name (`None` = current branch)
- `expires_after_seconds` (Optional[int]): Lock expiration time in seconds (`None` = never expires)

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

if unlock_file_api(repo_path, "meshes/model.json", "john_doe"):
    print("File unlocked")
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

**Dictionary Structure:**
```python
{
    'file_path': str,          # File path
    'lock_type': str,          # 'exclusive' or 'shared'
    'locked_by': str,          # Username/identifier
    'locked_at': int,          # Unix timestamp
    'expires_at': Optional[int], # Expiration timestamp (None if never expires)
    'branch': str,             # Branch name
}
```

**Example:**
```python
from forester.api import check_file_locked

lock_info = check_file_locked(repo_path, "meshes/model.json")
if lock_info:
    print(f"Locked by {lock_info['locked_by']}")
    print(f"Lock type: {lock_info['lock_type']}")
```

---

### `get_locks(path, branch=None, locked_by=None) -> List[Dict[str, Any]]`

List all active locks.

**Parameters:**
- `path` (Path): Repository path
- `branch` (Optional[str]): Filter by branch (optional)
- `locked_by` (Optional[str]): Filter by user (optional)

**Returns:**
- `List[Dict[str, Any]]`: List of lock dictionaries

**Example:**
```python
from forester.api import get_locks

# Get all locks
locks = get_locks(repo_path)

# Get locks for specific branch
locks = get_locks(repo_path, branch="main")

# Get locks by specific user
locks = get_locks(repo_path, locked_by="john_doe")

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
    print(f"{len(conflicts)} files are locked by other users")
    for conflict in conflicts:
        print(f"  {conflict['file_path']} locked by {conflict['locked_by']}")
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

**Dictionary Structure:**
```python
{
    'hash': str,               # Stash hash
    'message': str,            # Stash message
    'timestamp': int,          # Unix timestamp
    'branch': str,             # Branch name
}
```

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
  - `error_message` contains `"uncommitted_changes"` if there are uncommitted changes

**Example:**
```python
from forester.api import apply_stash_api

success, error = apply_stash_api(repo_path, "abc123...")
if success:
    print("Stash applied")
else:
    print(f"Error: {error}")
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

success = delete_stash_api(repo_path, "abc123...")
```

---

## Review Tools

### `comment_on_asset(path, asset_hash, asset_type, author, text, x=None, y=None) -> int`

Add comment to asset (mesh, blob, commit).

**Parameters:**
- `path` (Path): Repository path
- `asset_hash` (str): Hash of the asset
- `asset_type` (str): Type (`"mesh"`, `"blob"`, or `"commit"`)
- `author` (str): Author name
- `text` (str): Comment text
- `x` (Optional[float]): X coordinate for annotation (optional)
- `y` (Optional[float]): Y coordinate for annotation (optional)

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
    "This mesh needs fixing",
    x=100.5,
    y=200.3
)
print(f"Comment added with ID: {comment_id}")
```

---

### `get_asset_comments(path, asset_hash, asset_type, include_resolved=False) -> List[Dict[str, Any]]`

Get comments for asset.

**Parameters:**
- `path` (Path): Repository path
- `asset_hash` (str): Hash of the asset
- `asset_type` (str): Type (`"mesh"`, `"blob"`, or `"commit"`)
- `include_resolved` (bool): Include resolved comments (default: `False`)

**Returns:**
- `List[Dict[str, Any]]`: List of comment dictionaries

**Dictionary Structure:**
```python
{
    'id': int,                 # Comment ID
    'author': str,             # Author name
    'text': str,               # Comment text
    'created_at': int,         # Unix timestamp
    'x': Optional[float],       # X coordinate (optional)
    'y': Optional[float],       # Y coordinate (optional)
    'resolved': bool,          # True if resolved
}
```

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

success = resolve_comment_api(repo_path, 123)
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

success = delete_comment_api(repo_path, 123)
```

---

### `approve_asset(path, asset_hash, asset_type, approver, status="approved", comment=None) -> bool`

Set approval status for asset.

**Parameters:**
- `path` (Path): Repository path
- `asset_hash` (str): Hash of the asset
- `asset_type` (str): Type (`"mesh"`, `"blob"`, or `"commit"`)
- `approver` (str): Approver name
- `status` (str): Status (`"pending"`, `"approved"`, or `"rejected"`) (default: `"approved"`)
- `comment` (Optional[str]): Optional comment

**Returns:**
- `bool`: `True` if successful

**Example:**
```python
from forester.api import approve_asset

success = approve_asset(
    repo_path, 
    "abc123...", 
    "mesh", 
    "John Doe",
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
- `asset_type` (str): Type (`"mesh"`, `"blob"`, or `"commit"`)

**Returns:**
- `List[Dict[str, Any]]`: List of approval dictionaries

**Dictionary Structure:**
```python
{
    'approver': str,           # Approver name
    'status': str,             # 'pending', 'approved', or 'rejected'
    'comment': Optional[str],  # Optional comment
    'created_at': int,         # Unix timestamp
}
```

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
- `asset_type` (str): Type (`"mesh"`, `"blob"`, or `"commit"`)
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

## Maintenance & Utilities

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
else:
    print(f"Error: {error}")
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

**Statistics Dictionary:**
```python
{
    'commits_deleted': int,
    'trees_deleted': int,
    'blobs_deleted': int,
    'meshes_deleted': int,
    'commits_kept': int,
    'trees_kept': int,
    'blobs_kept': int,
    'meshes_kept': int,
}
```

**Example:**
```python
from forester.api import garbage_collect_api

# Dry run - see what would be deleted
success, error, stats = garbage_collect_api(repo_path, dry_run=True)
if success:
    print(f"Would delete {stats['blobs_deleted']} blobs")

# Actually perform garbage collection
success, error, stats = garbage_collect_api(repo_path, dry_run=False)
if success:
    print(f"Deleted {stats['blobs_deleted']} blobs")
    print(f"Kept {stats['blobs_kept']} blobs")
```

---

## Data Structures

### Commit Dictionary

```python
{
    'hash': str,               # Full commit hash
    'author': str,             # Author name
    'message': str,            # Commit message
    'timestamp': int,          # Unix timestamp
    'branch': str,             # Branch name
    'commit_type': str,        # 'project' or 'mesh_only'
    'screenshot_hash': str,    # Screenshot blob hash (optional)
}
```

### Branch Dictionary

```python
{
    'name': str,               # Branch name
    'commit_count': int,       # Number of commits
    'last_commit': str,        # Last commit hash (optional)
    'is_current': bool,        # True if this is the current branch
}
```

### Lock Dictionary

```python
{
    'file_path': str,          # File path
    'lock_type': str,          # 'exclusive' or 'shared'
    'locked_by': str,          # Username/identifier
    'locked_at': int,          # Unix timestamp
    'expires_at': Optional[int], # Expiration timestamp (None if never expires)
    'branch': str,             # Branch name
}
```

### Comment Dictionary

```python
{
    'id': int,                 # Comment ID
    'author': str,             # Author name
    'text': str,               # Comment text
    'created_at': int,         # Unix timestamp
    'x': Optional[float],      # X coordinate (optional)
    'y': Optional[float],      # Y coordinate (optional)
    'resolved': bool,          # True if resolved
}
```

### Approval Dictionary

```python
{
    'approver': str,           # Approver name
    'status': str,             # 'pending', 'approved', or 'rejected'
    'comment': Optional[str],  # Optional comment
    'created_at': int,         # Unix timestamp
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

## Examples

### Complete Workflow Example

```python
from pathlib import Path
from forester.api import (
    init_repo,
    commit,
    create_branch_repo,
    switch_to_branch,
    checkout_files,
    lock_files_api,
    unlock_files_api,
    get_branches,
    get_commit_info,
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

# Lock files before editing
lock_results = lock_files_api(
    repo_path,
    ["meshes/model.json", "textures/texture.png"],
    "john_doe",
    expires_after_seconds=3600
)

# ... make changes to files ...

# Commit changes
commit_hash = commit(repo_path, "Added new mesh", "John Doe")

# Unlock files
unlock_files_api(repo_path, ["meshes/model.json", "textures/texture.png"], "john_doe")

# Switch back to main and merge
switch_to_branch(repo_path, "main")
checkout_files(repo_path, "feature/new-mesh", force=True)

# Get commit info
info = get_commit_info(repo_path, commit_hash)
print(f"Author: {info['author']}, Message: {info['message']}")
```

### Selective Checkout Example

```python
from forester.api import checkout_files

# Checkout only texture files
success, error = checkout_files(
    repo_path,
    "main",
    file_patterns=["textures/*.png", "textures/*.jpg"]
)

# Checkout specific meshes from mesh_only commit
success, error = checkout_files(
    repo_path,
    "abc123...",
    mesh_names=["Character", "Weapon", "Environment"]
)
```

### Review Workflow Example

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

### Stash Workflow Example

```python
from forester.api import (
    stash_changes,
    get_stashes,
    apply_stash_api,
    delete_stash_api,
)

# Save current work
stash_hash = stash_changes(repo_path, "WIP: new feature")
print(f"Stashed: {stash_hash[:16]}")

# List all stashes
stashes = get_stashes(repo_path)
for stash in stashes:
    print(f"{stash['hash'][:16]}: {stash['message']}")

# Apply stash later
success, error = apply_stash_api(repo_path, stash_hash, force=True)
if success:
    print("Stash applied")

# Delete stash
delete_stash_api(repo_path, stash_hash)
```

---

## Notes

- All file paths are relative to repository root
- Commit hashes are full SHA-256 hashes (64 characters)
- Timestamps are Unix timestamps (seconds since epoch)
- File locking is branch-aware (locks are per branch)
- Screenshots are stored as PNG blobs and linked to commits
- Selective checkout supports glob patterns (`*`, `**`, `?`)

---

**For more information, see the main [Forester README](forester/README.md).**

