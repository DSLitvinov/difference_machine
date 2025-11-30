# Forester API Quick Start Guide

**Quick reference for the most common operations.**

---

## Installation

```python
from pathlib import Path
from forester.api import *
```

---

## Repository Setup

```python
# Initialize repository
init_repo(Path("/path/to/project"))

# Check if path is repository
if is_repo(Path("/path/to/project")):
    print("Valid repository")

# Find repository root
repo_path = find_repo(Path.cwd())
```

---

## Commits

```python
# Create commit
commit_hash = commit(repo_path, "Message", "Author")

# Check for changes
if has_changes(repo_path):
    print("Uncommitted changes detected")

# Get commit info
info = get_commit_info(repo_path, commit_hash)
print(info['message'])

# Get screenshot
screenshot = get_screenshot(repo_path, commit_hash)
with open("screenshot.png", "wb") as f:
    f.write(screenshot)

# Delete commit
success, error = delete_commit_api(repo_path, commit_hash)
```

---

## Branches

```python
# Create branch
create_branch_repo(repo_path, "feature-name")

# List branches
branches = get_branches(repo_path)

# Switch branch
switch_to_branch(repo_path, "feature-name")

# Get branch commits
commits = get_branch_commits_api(repo_path, "main")

# Delete branch
delete_branch_repo(repo_path, "old-branch")
```

---

## Checkout

```python
# Full checkout
success, error = checkout_files(repo_path, "main", force=True)

# Selective checkout (only textures)
success, error = checkout_files(
    repo_path,
    "main",
    file_patterns=["textures/*.png"]
)

# Checkout specific meshes
success, error = checkout_files(
    repo_path,
    "commit_hash",
    mesh_names=["Mesh1", "Mesh2"]
)
```

---

## File Locking

```python
# Lock single file
lock_file_api(repo_path, "meshes/model.json", "user_name")

# Lock multiple files
results = lock_files_api(
    repo_path,
    ["file1.json", "file2.json"],
    "user_name",
    expires_after_seconds=3600
)

# Check if locked
lock_info = check_file_locked(repo_path, "meshes/model.json")
if lock_info:
    print(f"Locked by {lock_info['locked_by']}")

# Unlock
unlock_file_api(repo_path, "meshes/model.json", "user_name")

# Check conflicts before commit
conflicts = check_conflicts(repo_path, files_list, "user_name")
```

---

## Stash

```python
# Create stash
stash_hash = stash_changes(repo_path, "WIP message")

# List stashes
stashes = get_stashes(repo_path)

# Apply stash
success, error = apply_stash_api(repo_path, stash_hash, force=True)

# Delete stash
delete_stash_api(repo_path, stash_hash)
```

---

## Review Tools

```python
# Add comment
comment_id = comment_on_asset(
    repo_path,
    "asset_hash",
    "mesh",  # or "blob", "commit"
    "Author",
    "Comment text",
    x=100.0,
    y=200.0
)

# Get comments
comments = get_asset_comments(repo_path, "asset_hash", "mesh")

# Resolve comment
resolve_comment_api(repo_path, comment_id)

# Approve asset
approve_asset(repo_path, "asset_hash", "mesh", "Reviewer", "approved")

# Get approvals
approvals = get_asset_approvals(repo_path, "asset_hash", "mesh")
```

---

## Maintenance

```python
# Rebuild database
success, error = rebuild_db(repo_path, backup=True)

# Garbage collection (dry run)
success, error, stats = garbage_collect_api(repo_path, dry_run=True)
print(f"Would delete {stats['blobs_deleted']} blobs")

# Actual garbage collection
success, error, stats = garbage_collect_api(repo_path, dry_run=False)
```

---

## Common Patterns

### Basic Workflow

```python
repo_path = Path("/path/to/project")

# Initialize
init_repo(repo_path)

# Create commit
commit_hash = commit(repo_path, "Initial commit", "Author")

# Create branch
create_branch_repo(repo_path, "feature")

# Switch and work
switch_to_branch(repo_path, "feature")
commit(repo_path, "Feature work", "Author")

# Merge back
switch_to_branch(repo_path, "main")
checkout_files(repo_path, "feature", force=True)
```

### Collaborative Workflow

```python
# Lock files before editing
lock_files_api(repo_path, ["file1.json"], "user_name")

# Make changes...

# Check for conflicts
conflicts = check_conflicts(repo_path, ["file1.json"], "user_name")
if not conflicts:
    commit(repo_path, "Changes", "user_name")

# Unlock
unlock_files_api(repo_path, ["file1.json"], "user_name")
```

### Review Workflow

```python
# Reviewer adds comment
comment_id = comment_on_asset(repo_path, asset_hash, "mesh", "Reviewer", "Fix needed")

# Developer fixes and responds
resolve_comment_api(repo_path, comment_id)

# Approve
approve_asset(repo_path, asset_hash, "mesh", "Reviewer", "approved", "Looks good!")
```

---

## Error Handling

```python
# Most functions return tuples: (success, error)
success, error = checkout_files(repo_path, "main")
if not success:
    if error == "uncommitted_changes":
        print("Use force=True to discard changes")
    else:
        print(f"Error: {error}")

# Some return Optional values
commit_hash = commit(repo_path, "Message", "Author")
if commit_hash:
    print(f"Created: {commit_hash[:16]}")
else:
    print("No changes to commit")
```

---

## Data Types

### Commit Info

```python
{
    'hash': str,
    'author': str,
    'message': str,
    'timestamp': int,
    'branch': str,
    'commit_type': str,  # 'project' or 'mesh_only'
    'screenshot_hash': Optional[str]
}
```

### Branch Info

```python
{
    'name': str,
    'commit_count': int,
    'last_commit': Optional[str],
    'is_current': bool
}
```

### Lock Info

```python
{
    'file_path': str,
    'lock_type': str,  # 'exclusive' or 'shared'
    'locked_by': str,
    'locked_at': int,
    'expires_at': Optional[int],
    'branch': str
}
```

---

## Tips

- Use `force=True` to discard uncommitted changes when needed
- File patterns support glob: `["textures/*.png", "**/*.json"]`
- Locks expire automatically based on `expires_after_seconds`
- Screenshots are automatically captured on commit
- Selective checkout is useful for large repositories

---

**For detailed documentation, see [API_REFERENCE.md](API_REFERENCE.md)**

