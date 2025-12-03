# Forester

Git-like version control system for 3D models.

## Installation

Forester is part of the Difference Machine Blender add-on. To use it from command line:

```bash
# Set PYTHONPATH to the add-on directory
export PYTHONPATH=/path/to/difference_machine

# Run forester commands
python3 -m forester <command>
```

## Usage

### Initialize Repository

```bash
forester init [path]
forester init --force  # Reinitialize existing repository
```

### Create Commit

```bash
forester commit -m "Commit message" -a "Author Name"
```

### Branch Management

```bash
# Create branch
forester branch create <name> [--from <branch>]

# List branches
forester branch list

# Switch branch (without checkout)
forester branch switch <name>

# Delete branch
forester branch delete <name> [--force]
```

### Checkout

```bash
# Checkout branch
forester checkout <branch> [--force]

# Checkout commit (detached HEAD)
forester checkout <commit_hash> [--force]
```

### Stash Management

```bash
# Create stash
forester stash create [-m "message"]

# List stashes
forester stash list

# Apply stash
forester stash apply <hash> [--force]

# Delete stash
forester stash delete <hash>
```

### Tag Management

```bash
# Create tag (on current HEAD)
forester tag create <tag_name>

# Create tag on specific commit
forester tag create <tag_name> <commit_hash>

# List all tags
forester tag list

# Show tag information
forester tag show <tag_name>

# Delete tag
forester tag delete <tag_name>
```

### Status

```bash
forester status
```

### Hooks

Forester supports Git-like hooks for automation. Hooks are scripts located in `.DFM/hooks/` directory.

#### Available Hooks

- **pre-commit**: Runs before commit creation. Can block commit if it returns non-zero exit code.
- **post-commit**: Runs after commit creation. Cannot block commit.
- **pre-checkout**: Runs before checkout. Can block checkout if it returns non-zero exit code.
- **post-checkout**: Runs after checkout. Cannot block checkout.

#### Hook Environment Variables

Hooks receive the following environment variables:

**Pre-commit / Post-commit hooks:**
- `DFM_BRANCH` - Current branch name
- `DFM_AUTHOR` - Commit author
- `DFM_MESSAGE` - Commit message
- `DFM_REPO_PATH` - Repository root path
- `DFM_COMMIT_HASH` - Commit hash (post-commit only)

**Pre-checkout / Post-checkout hooks:**
- `DFM_TARGET` - Branch name or commit hash being checked out
- `DFM_REPO_PATH` - Repository root path

#### Example Hooks

**Pre-commit hook** (`.DFM/hooks/pre-commit`):
```bash
#!/bin/bash
# Check commit message length
if [ ${#DFM_MESSAGE} -lt 10 ]; then
    echo "Error: Commit message too short (minimum 10 characters)"
    exit 1
fi
```

**Post-commit hook** (`.DFM/hooks/post-commit`):
```bash
#!/bin/bash
# Send notification after commit
echo "Commit $DFM_COMMIT_HASH created by $DFM_AUTHOR on branch $DFM_BRANCH"
```

#### Skipping Hooks

Use `--no-verify` flag to skip hooks:

```bash
forester commit -m "Message" --no-verify
forester checkout main --no-verify
```

## Repository Structure

```
project/
├── .DFM/
│   ├── forester.db          # SQLite database
│   ├── metadata.json        # Repository metadata
│   ├── .dfmignore          # Ignore rules
│   ├── hooks/              # Hook scripts
│   │   ├── pre-commit      # Pre-commit hook (optional)
│   │   ├── post-commit     # Post-commit hook (optional)
│   │   ├── pre-checkout    # Pre-checkout hook (optional)
│   │   └── post-checkout   # Post-checkout hook (optional)
│   ├── refs/
│   │   └── branches/        # Branch references
│   ├── objects/
│   │   ├── blobs/          # File objects
│   │   ├── trees/          # Directory structures
│   │   ├── commits/        # Commit objects
│   │   └── meshes/         # Mesh objects
│   └── stash/              # Stash storage
└── working/                 # Working directory
    ├── *.blend             # Blender files
    ├── textures/           # Textures
    ├── references/          # Reference files
    └── meshes/             # Working meshes (not tracked)
```

## Features

- **Version Control**: Track changes to files and 3D meshes
- **Branching**: Create and manage multiple branches
- **Commits**: Create snapshots of your project state
- **Tags**: Mark important commits with tags
- **Stash**: Temporarily save uncommitted changes
- **Hooks**: Pre-commit/post-commit hooks for automation
- **Deduplication**: Files and meshes are stored once, referenced multiple times
- **Mesh Support**: Special handling for 3D mesh data (JSON format)

## Notes

- The `meshes/` directory in working is not tracked as files, but meshes are stored separately
- Use `--force` flag to discard uncommitted changes when checking out
- Stash automatically saves current state before applying another stash (if there are changes)

## API

Forester can also be used as a Python library:

```python
from forester.commands import init_repository, create_commit, create_branch, create_tag

# Initialize repository
init_repository(Path("/path/to/project"))

# Create commit
create_commit(Path("/path/to/project"), "Message", "Author")

# Create branch
create_branch(Path("/path/to/project"), "feature1")

# Create tag
create_tag(Path("/path/to/project"), "v1.0", commit_hash="abc123...")
```



