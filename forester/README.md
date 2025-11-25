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

### Status

```bash
forester status
```

## Repository Structure

```
project/
├── .DFM/
│   ├── forester.db          # SQLite database
│   ├── metadata.json        # Repository metadata
│   ├── .dfmignore          # Ignore rules
│   ├── HEAD                # Current HEAD reference
│   ├── refs/
│   │   └── branches/        # Branch references
│   ├── objects/
│   │   ├── blobs/          # File objects
│   │   ├── trees/          # Directory structures
│   │   ├── commits/        # Commit objects
│   │   └── meshes/         # Mesh objects
│   ├── stash/              # Stash storage
│   └── temp_view/          # Temporary commit views
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
- **Stash**: Temporarily save uncommitted changes
- **Deduplication**: Files and meshes are stored once, referenced multiple times
- **Mesh Support**: Special handling for 3D mesh data (JSON format)

## Notes

- The `meshes/` directory in working is not tracked as files, but meshes are stored separately
- Use `--force` flag to discard uncommitted changes when checking out
- Stash automatically saves current state before applying another stash (if there are changes)

## API

Forester can also be used as a Python library:

```python
from forester.commands import init_repository, create_commit, create_branch

# Initialize repository
init_repository(Path("/path/to/project"))

# Create commit
create_commit(Path("/path/to/project"), "Message", "Author")

# Create branch
create_branch(Path("/path/to/project"), "feature1")
```

