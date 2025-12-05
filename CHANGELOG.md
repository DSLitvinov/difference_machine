# Changelog

All notable changes to the Difference Machine project will be documented in this file.

## [Unreleased]

### Added
- **Background Mesh Export**: Mesh-only commits now use background Blender process
  - Exports meshes without modifying current project scene
  - Uses `empty.blend` template file from `empty_files/` directory
  - Runs separate Blender instance in `--background` mode via subprocess
  - Ensures project stability and prevents scene corruption during commit creation
  - Implementation: `operators/mesh_export_background.py` (background script)
  - Modified: `operators/mesh_io.py` - `_save_mesh_to_blend()` now uses background process
  - Added: `get_empty_blend_path()` function to locate template file
  - Benefits:
    - No scene modification during mesh export
    - No need to restore project after commit
    - Better stability and reliability
    - Compatible with future 3D package addons (similar pattern can be used)
- **Mesh Diff Analysis**: Added comprehensive 3D mesh difference analysis system
  - **Geometry Diff**: Compare geometry changes between mesh versions
    - Vertex matching with tolerance-based comparison
    - Detection of added/removed/modified vertices
    - Face topology comparison
    - UV and normal changes tracking
  - **Material Diff**: Compare material changes between versions
    - Texture changes (added/removed/modified by hash)
    - Node tree comparison (nodes and links)
    - Material property changes
  - **Diff Statistics**: Detailed metrics about changes
    - Count of added/removed/modified vertices and faces
    - Percentage change metrics for geometry and materials
    - Vertex displacement metrics (max and average)
    - Texture and node change counts
  - **Visualization**: Vertex color-based visualization of changes
    - Multiple color schemes: displacement, added, removed, modified
    - Automatic viewport mode switching to vertex colors
    - Color-coded change highlighting
  - **UI Panel**: New "Mesh Diff" panel in sidebar
    - Compute diff between current mesh and commit version
    - Display detailed statistics
    - Apply visualization with color scheme selection
    - Clear diff data
  - **Integration**: Automatic diff computation when using Compare feature
    - Diff is automatically computed and stored when comparing meshes
    - Statistics available immediately after comparison
  - Available in Mesh Diff panel (4th panel in Difference Machine tab)
  - Models: `forester/models/mesh_diff.py` (MeshDiff, GeometryDiff, MaterialDiff, DiffStatistics)
  - Utilities: `forester/utils/mesh_diff_utils.py` (compute functions)
- **Independent Texture Versioning**: Textures are versioned separately from meshes
  - Separate texture storage in `.DFM/objects/textures/`
  - Texture deduplication at texture level (one texture can be used by many meshes)
  - Texture history tracking independent from mesh commits
  - Automatic texture versioning during commit creation
  - Database tables: `textures`, `texture_commits` for texture-commit relationships
  - Content-addressable storage with SHA-256 hashing
  - PIL/Pillow integration for image metadata extraction (with fallback)
  - **Models**: `forester/models/texture.py` (Texture model)
  - **Storage**: Extended ObjectStorage with texture operations
    - `save_texture()`, `load_texture()`, `texture_exists()`
  - **Database**: Extended ForesterDB with texture methods
    - `add_texture()`, `get_texture()`, `texture_exists()`
    - `link_texture_to_commit()`, `get_textures_for_commit()`
- **Database Rebuild Mechanism**: Added `rebuild_database` command to reconstruct corrupted database from file system storage
  - Automatically scans storage directories and rebuilds database tables
  - Creates backup of existing database before rebuilding
  - Available in Preferences > Database Maintenance
  - CLI command: `forester rebuild`

- **Garbage Collection**: Added comprehensive garbage collection system
  - Manual garbage collection with dry-run preview mode
  - Automatic garbage collection with configurable intervals (hours/days/weeks)
  - Safely removes unreferenced commits, trees, blobs, and meshes
  - Preserves objects referenced by branches and stashes
  - Available in Preferences > Garbage Collection
  - CLI command: `forester gc`

- **Auto-compress Mesh-only Commits**: Added automatic compression feature
  - Automatically deletes old mesh-only commits when creating new ones
  - Configurable number of commits to keep (default: 5)
  - Available in Preferences > Auto-compress Settings

- **Centralized Logging System**: Created `utils/logging_config.py` for unified logging
  - Replaced all `print()` statements with proper logging
  - Configurable log levels and formatting
  - Better error tracking with tracebacks

- **Input Validation**: Added validation module for branch names
  - Created `forester/utils/validation.py` with `validate_branch_name` function
  - Prevents invalid branch names (empty, whitespace-only, invalid characters)

- **UI Auto-refresh**: Automatic UI updates after operations
  - Commit list refreshes after branch operations
  - Branch list refreshes after commit operations
  - Prevents stale UI state

- **CLI Commands `show` and `log`**: Added commands for viewing commit information
  - `forester show <commit_hash>`: Display commit details and changed files
    - By default shows only modified (`M`), added (`+`), and deleted (`-`) files compared to parent commit
    - Use `--full` flag to show all files in the commit
    - Displays file sizes and change indicators
  - `forester log [branch]`: Display commit history for a branch
    - Shows commit hash, message, author, and timestamp
    - Use `-v` or `--verbose` for detailed output
    - Defaults to current branch if no branch specified

- **Automatic Preview Temp Cleanup**: Added automatic cleanup of old preview_temp directories
  - Automatically removes old temporary commit preview directories when creating new ones
  - Cleans up all old preview_temp directories on addon startup (except current active one)
  - Prevents accumulation of temporary files from commit preview operations
  - Logs cleanup operations with freed disk space information
  - Reduces repository size by removing unused temporary commit snapshots

### Changed
- **Mesh Export Process**: Changed mesh-only commit creation to use background process
  - Previously used `read_homefile()` which cleared current scene
  - Now uses subprocess to run Blender in background with `empty.blend` template
  - Current project scene is never modified during mesh export
  - Eliminates need for scene restoration after commit creation
  - More reliable and stable commit creation process
- **Branch Switching**: Fixed critical bug where "Already on branch" message appeared incorrectly
  - Improved database synchronization with `PRAGMA wal_checkpoint(TRUNCATE)`
  - Fresh database connections for branch state checks
  - Better error handling and debug logging

- **Commit Display in CLI**: Improved `forester show` command to show only changed files by default
  - Compares commit tree with parent commit to identify changes
  - Shows added, modified, and deleted files with clear indicators
  - Helps users quickly understand what changed in each commit
  - Use `--full` flag for complete file list (useful for first commit or full audit)

- **Repository Size Optimization**: Automatic cleanup of temporary files
  - Preview temporary directories are now automatically cleaned up
  - Prevents `.DFM` folder from growing unnecessarily large
  - Only active preview directory is kept during operations

- **Code Quality Improvements**:
  - Replaced all `print()` statements with `logger` calls
  - Improved error handling with specific exception types
  - Added `exc_info=True` to error logging for full tracebacks
  - Extracted "magic numbers" into named constants
  - Improved path handling for cross-platform compatibility

- **Database Operations**: 
  - Ensured all `ForesterDB` instances use context managers (`with` statements)
  - Added `get_all_stashes()` method to database
  - Improved transaction handling and visibility

- **Commit Deletion**: Consolidated commit utility functions
  - Moved `is_commit_head`, `is_commit_referenced_by_branches`, `get_all_commits_used_by_branches` from `commit_utils.py` to `delete_commit.py`
  - Removed duplicate code and improved maintainability

- **Garbage Collection Path Handling**: Improved robustness of file deletion
  - Added `_safe_delete_file()` and `_safe_delete_directory()` helper functions
  - Collect files/directories before deletion to avoid `rglob` iteration issues
  - Better handling of missing parent directories
  - Fixed `WinError 3` (path not found) errors on Windows

### Fixed
- **Branch Switching Bug**: Fixed issue where operator always reported "Already on branch" after first successful switch
  - Root cause: Stale database state and cached branch information
  - Solution: Fresh database connections and explicit state synchronization

- **RecursionError**: Fixed infinite recursion in UI refresh calls
  - Removed mutual calls between `DF_OT_refresh_history` and `DF_OT_refresh_branches`
  - Each operator now only refreshes its own UI list

- **Database Resource Leaks**: Fixed potential database connection leaks
  - Ensured all database operations use context managers
  - Proper connection cleanup

- **Path Handling on Windows**: Fixed path-related errors during garbage collection
  - Improved `_extract_hash_from_path` to handle missing directories
  - Better error handling for file system operations
  - Safe directory removal with existence checks

- **Inefficient Database Queries**: Optimized `get_commits_using_blob` method
  - Changed to use `SELECT DISTINCT tree_hash` for better performance

### Removed
- **Duplicate Code**: Removed `forester/utils/commit_utils.py` after consolidating functions into `delete_commit.py`

### Refactored
- **Operator Helpers**: Created `ensure_repository_and_branch` helper function to reduce code duplication
- **Commit Utilities**: Consolidated commit-related utility functions into `delete_commit.py`
- **Error Handling**: Standardized error handling patterns across all operators
- **Constants**: Extracted magic numbers into named constants (e.g., in `hashing.py`)

## Technical Improvements

### Code Organization
- Created `utils/logging_config.py` for centralized logging configuration
- Created `forester/utils/validation.py` for input validation
- Consolidated commit utilities into `forester/commands/delete_commit.py`
- Improved module structure and separation of concerns

### Database Improvements
- Added `PRAGMA wal_checkpoint(TRUNCATE)` for better synchronization
- Improved transaction handling
- Added `get_all_stashes()` method
- Better connection management with context managers

### Storage Improvements
- Added safe file and directory deletion functions
- Improved path extraction and validation
- Better error handling for missing files/directories

### UI Improvements
- Automatic refresh after operations
- Better error messages
- Improved user feedback

## Migration Notes

### For Users
- **New Preferences**: Check Preferences > Extensions > Difference Machine for new settings:
  - Auto-compress Mesh-only Commits
  - Auto Garbage Collect
  - Database Maintenance tools

- **Database Rebuild**: If you encounter database corruption, use Preferences > Database Maintenance > Rebuild Database

- **Garbage Collection**: Periodically run garbage collection to clean up unused objects. Enable automatic garbage collection in preferences for convenience.

### For Developers
- **Logging**: All `print()` statements have been replaced with `logger` calls. Use `logging.getLogger(__name__)` in new modules.

- **Database Access**: Always use `ForesterDB` with context managers:
  ```python
  with ForesterDB(db_path) as db:
      # database operations
  ```

- **Validation**: Use `validate_branch_name()` from `forester.utils.validation` for branch name validation.

- **Commit Utilities**: Commit-related utility functions are now in `forester.commands.delete_commit`:
  - `is_commit_head()`
  - `is_commit_referenced_by_branches()`
  - `get_all_commits_used_by_branches()`

