# Difference Machine

Version control system for 3D models - Blender add-on.

## Description

Difference Machine is a Blender add-on that provides Git-like version control functionality for 3D models. It allows you to track changes to your meshes, materials, and textures, create commits, manage branches, and compare different versions of your models.

## Features

### Commit Management
- **Create Commits**: Create full project commits or mesh-only commits for selected objects
- **Commit History**: View commit history with author, timestamp, and commit details
- **Delete Commits**: Remove unwanted commits from history
- **Open Project State**: Restore entire project state from any commit

### Branch Management
- **Create Branches**: Create new branches for parallel development
- **Switch Branches**: Switch between branches to work on different versions
- **Delete Branches**: Delete branches (with protection for current and last branch)
- **Branch List**: View all branches with commit counts and last commit info

### Mesh Operations
- **Compare Meshes**: Compare current mesh with version from commit
  - Select axis (X, Y, Z) for comparison object offset
  - Visual side-by-side comparison
- **Replace Mesh**: Replace current mesh with version from commit
- **Load Mesh Version**: Load mesh from specific commit
- **Export Options**: Control what gets exported (vertices, faces, UV, normals, materials, transform)

### Material & Texture Handling
- **Material Export/Import**: Full material node tree export and import
- **Texture Management**: Automatic texture tracking and copying
  - Only changed textures are copied to commits
  - Texture path resolution with multiple fallback strategies
  - Support for packed and external textures

### Comparison Mode
- When comparison object is active:
  - Only viewing is available (no commit/branch operations)
  - Axis selection buttons (X, Y, Z) for repositioning comparison object
  - Compare button toggles comparison on/off

### Repository Maintenance
- **Database Rebuild**: Rebuild corrupted database from file system storage
- **Garbage Collection**: Remove unused objects (commits, trees, blobs, meshes) not referenced by any branches
  - Manual garbage collection with dry-run preview
  - Automatic garbage collection with configurable intervals (hours/days/weeks)
- **Auto-compress**: Automatically delete old mesh-only commits when creating new ones
  - Configurable number of commits to keep

## Installation

1. Download or clone this repository
2. In Blender, go to `Edit > Preferences > Extensions`
3. Click `Install...` and select the add-on folder
4. Enable the add-on in the extensions list

## Usage

After installation, you can access Difference Machine from the 3D Viewport sidebar (N-panel) under the "Difference Machine" tab.

### Panels

1. **Branch Management**: Manage branches, create, switch, and delete branches
2. **Create Commit**: Create new commits (project or mesh-only) with export options
3. **Load Commit**: View commit history, load/replace meshes, compare versions

### Preferences

Access add-on preferences via `Edit > Preferences > Extensions > Difference Machine`:

- **Commit Settings**: Set default author name
- **Auto-compress Settings**: Enable automatic compression of mesh-only commits
- **Garbage Collection**: 
  - Manual garbage collection (with dry-run option)
  - Automatic garbage collection with configurable intervals
- **Database Maintenance**: Rebuild database from storage if corrupted

### Basic Workflow

1. **Initialize Repository**: The add-on automatically initializes a repository when you create your first commit
2. **Create Commits**: Select mesh objects and create a commit with a message
3. **Compare Versions**: Use the Compare feature to see differences between versions
4. **Manage Branches**: Create branches for different variations of your model
5. **Restore Versions**: Load or replace meshes from previous commits

## Structure

```
difference_machine/
├── __init__.py              # Main entry point
├── blender_manifest.toml    # Blender 4.0+ manifest
├── operators/               # Operators (bpy.types.Operator classes)
│   ├── commit_operators.py  # Commit creation and management
│   ├── history_operators.py # History viewing, compare, replace
│   ├── branch_operators.py  # Branch operations
│   ├── mesh_io.py          # Mesh export/import utilities
│   └── operator_helpers.py # Common helper functions
├── ui/                      # User interface (panels, menus)
│   ├── ui_panels.py        # Main UI panels
│   ├── ui_lists.py         # UI lists for commits and branches
│   └── ui_main.py          # UI registration
├── properties/              # Custom properties
│   ├── properties.py       # Scene properties
│   └── commit_item.py      # Commit and branch item properties
├── forester/               # Version control engine
│   ├── commands/           # Core commands (init, commit, branch, etc.)
│   ├── core/               # Core functionality (database, storage, etc.)
│   └── models/             # Data models (Commit, Mesh, Tree, etc.)
└── utils/                  # Helper functions
```

## Technical Details

- **Storage**: Uses SQLite database for metadata and content-addressable object storage for mesh/material data
- **Hashing**: SHA-256 hashing for content-addressable storage
- **Texture Handling**: Automatic texture deduplication and path resolution
- **Material Export**: Full node tree structure export with texture references
- **Database Recovery**: Automatic database rebuild from file system storage
- **Garbage Collection**: Safe removal of unreferenced objects with reference checking
- **Logging**: Comprehensive logging system for debugging and error tracking

## License

GPL-3.0-or-later

## Author

Dmitry Litvinov <nopomuk@yandex.ru>
