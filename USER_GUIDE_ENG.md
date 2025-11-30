Sure! Here's the English translation of the provided **USER_GUIDE_RU.md**:

---

# Difference Machine Add-on User Guide

## Table of Contents
- [Installation and First Launch](#installation-and-first-launch)
- [Main Panels](#main-panels)
- [Working with the Repository](#working-with-the-repository)
- [Creating Commits](#creating-commits)
- [Branch Management](#branch-management)
- [Viewing History and Restoring Versions](#viewing-history-and-restoring-versions)
- [Comparing Versions](#comparing-versions)
- [Add-on Settings](#add-on-settings)
- [Useful Tips](#useful-tips)

---

## Installation and First Launch

### Installation
1. Open Blender.
2. Go to `Edit > Preferences > Extensions`.
3. Click `Install...` and select the add-on folder.
4. Enable the add-on in the extensions list.

### First Launch
1. Save your `.blend` file to your project folder (e.g., via `File > Save As...`).
2. Open the sidebar in the 3D Viewport (`N` key).
3. Switch to the **"Difference Machine"** tab.

### Project Initialization
1. Open the **"Branch Management"** panel.
2. If the repository is not initialized, click **"Init Project"**.
   - This creates a `.DFM` folder in your project directory containing the version database.

---

## Main Panels

The add-on features three main panels (accessible under the **Difference Machine** tab in the sidebar `N`):

1. **Branch Management**  
   - View branch list  
   - Create, switch, and delete branches  
   - Project initialization button (if repository not created)

2. **Create Commit**  
   - Create commits for selected objects  
   - Create full project commits  
   - Configure component export settings

3. **Load Commit**  
   - View commit history  
   - Restore mesh versions  
   - Compare versions  
   - Delete commits

---

## Working with the Repository

### Requirements
- **Important**: Your `.blend` file must be saved to disk.
- The repository is automatically initialized upon the first commit or when clicking **"Init Project"**.

### Repository Structure
After initialization, the following will be created in your project folder:
- `.DFM/` – folder containing version data
  - `forester.db` – SQLite metadata database
  - `objects/` – object storage (commits, trees, blobs, meshes)
  - `refs/branches/` – branch references
  - `preview_temp/` – temporary files for preview (automatically cleaned)

---

## Creating Commits

### Committing Selected Objects (Mesh-only Commit)

**When to use:**
- To save changes to specific meshes only
- For quick intermediate saves during modeling
- When working exclusively with geometry and materials

**How to create:**
1. Select one or more mesh objects in the scene.
2. Open the **"Create Commit"** panel.
3. Choose **"Selected Object"** mode.
4. Configure export components:
   - **Export All Components** – export everything
   - Or individually select:
     - **Geometry** – vertices, faces
     - **Materials** – materials and shader nodes
     - **Transform** – object transforms
     - **UV Layout** – UV maps
5. Enter a commit message (e.g., "Added details to sword").
6. Click **"Create Commit"**.
   - The message field automatically clears after successful commit creation.

**Features:**
- Only selected objects, their materials, and textures are saved.
- Other scene objects are **not** included.
- Multiple commits can be created for different objects.

### Full Project Commit

**When to use:**
- To save the entire project state
- For key development milestones
- As a full backup of your project

**How to create:**
1. Open the **"Create Commit"** panel.
2. Choose **"Full Project"** mode.
3. Enter a commit message.
4. Click **"Create Commit"**.
   - The message field automatically clears after successful commit creation.

**Features:**
- Saves all project files (`.blend` files, textures, etc.)
- Creates a complete snapshot of the project
- Can be used to fully restore the project from the commit

---

## Branch Management

### Viewing Branches
1. Open the **"Branch Management"** panel.
2. Click **"Refresh Branches"** to update the list.
   - Displays:
     - Branch name
     - Number of commits
     - Latest commit message and hash
   - The current branch is marked with a special indicator.

### Creating a New Branch
1. In **"Branch Management"**, click **"Create New Branch"**.
2. Enter a branch name in the dialog.
   - The new branch is created from the current branch.

**Usage Tips:**
- Use separate branches for different model variants (e.g., `main`, `v2-detail`, `low-poly`, `texture-variants`).
- Enables parallel development on different versions.

### Switching Branches
1. Select a branch from the list.
2. Click **"Switch Branch"**.
   - HEAD updates, and the working directory is checked out to that branch.

**Important:**
- Unsaved changes may be lost during branch switching.

### Deleting a Branch
1. Select a **non-current** branch from the list.
2. Click **"Delete Branch"** and confirm.

**Limitations:**
- Cannot delete the current branch.
- Cannot delete the last remaining branch.

---

## Viewing History and Restoring Versions

### Viewing Commit History
1. Open the **"Load Commit"** panel.
2. Click **"Refresh"** to update the list.
   - Shows all commits in the current branch:
     - Commit hash
     - Message
     - Author
     - Timestamp
     - Commit type (`project` or `mesh_only`)
     - For `mesh_only`: detailed information about all meshes in the commit
       - Object name (clickable to select in viewport)
       - Vertices count
       - Faces count

### Restoring a Mesh from a Commit (Mesh-only)

**Viewing Mesh Information:**
- When you select a `mesh_only` commit, the panel displays detailed information about all meshes in the commit:
  - Object name (clickable - clicking selects the object in the viewport)
  - Vertices count
  - Faces count
- This helps you quickly identify which meshes are included in the commit.

**Option 1: Replace Mesh**
1. Select a mesh in the scene (must match the name in the commit).
2. Choose a `mesh_only` commit.
3. Click **"Replace This Mesh"**.
   - The current mesh is replaced with the version from the commit.

**Option 2: Compare**  
See [Comparing Versions](#comparing-versions).

**Quick Selection:**
- Click on any mesh name in the commit details to automatically select that object in the viewport.

### Restoring a Full Project (Full Project Commit)

**Checkout to Working Directory:**
1. Select a `project`-type commit.
2. Click **"Checkout to Working Directory"**.
   - All project files are restored from the commit.

**Open Project State:**
1. Select a `project`-type commit.
2. Click **"Open Project"**.
   - Blender opens the `.blend` file from the working directory after checkout.

**Important:**  
These operations overwrite the working directory. Unsaved changes will be lost.

### Deleting a Commit
1. Select a commit from the list.
2. Click **"Delete This Version"** and confirm.

**Limitations:**
- Commits referenced by branches are protected from deletion.
- Physical files are **not** deleted immediately (use Garbage Collection).

---

## Comparing Versions

### Mesh Comparison

**How to use:**
1. Select a mesh in the scene (name must match the commit).
2. Choose a `mesh_only` commit.
3. Click **"Compare"**.
   - A comparison object appears in the scene.

**Controls:**
- **X, Y, Z buttons**: Adjust offset along the selected axis.
- **"Compare" button**: Press again to remove the comparison object.

**Comparison Mode:**
- While the comparison object is active, other operations (commits, branches) are disabled.
- Only viewing and axis offset adjustments are allowed.

### Project Comparison

**How to use:**
1. Select a `project`-type commit.
2. Click **"Compare"**.
   - The commit is copied to a temporary folder and opened in a **new Blender window**.

**Controls:**
- Press **"Compare"** again to close the comparison window.
- Changes in the comparison window are **not auto-saved**.

---

## Add-on Settings  
(Available via `Edit > Preferences > Extensions > Difference Machine`)

### Commit Settings
- **Default Author**: Default name used for all commits.

### Auto-compress Settings
- **Auto-compress Mesh-only Commits**: Automatically delete old `mesh_only` commits.
- **Keep Last N Commits**: Number of recent commits to retain (default: 5).

**When to use:**
- If creating many intermediate mesh versions.
- To save disk space.
- Only enable if you’re confident old versions aren’t needed.

### Garbage Collection
**Manual:**
- **Garbage Collect Now**: Delete all unreferenced objects.
- **Dry Run (Preview)**: Preview what will be deleted (no actual deletion).

**Automatic:**
- Enable **"Auto Garbage Collect"**.
- Set interval (hours/days/weeks).

**What gets deleted:**
- Commits not referenced by any branch.
- Trees, blobs, and meshes not linked to any commit.
- **Protected**: Objects referenced by branches or stashes.

### Database Maintenance
- **Rebuild Database**: Reconstruct the database from storage files.
  - Use if the database is corrupted or lost.

---

## Useful Tips

### Workflow
- Initialize the project **before** starting work.
- Always save your `.blend` file before any operation.
- Use branches for experiments and variants.
- Use `mesh_only` commits for quick geometry saves.
- Use `project` commits for important milestones.
- Run Garbage Collection regularly.

### Repository Size Optimization
- Enable **Auto-compress** for `mesh_only` commits.
- Enable **Auto Garbage Collect**.
- Regularly delete unnecessary commits and branches.

### Safety
- Never delete commits referenced by branches.
- Create a backup branch before major changes.
- Always run **Dry Run** before Garbage Collection.

### Textures
- The add-on automatically tracks textures.
- Modified textures are copied into the commit.
- Unchanged textures are deduplicated (referenced from previous versions).

### CLI (Command Line)
Advanced users can use the `forester` CLI:
- `forester show <hash>` – view changes in a commit
- `forester log` – view commit history
- `forester branch` – manage branches  
See `README.md` for details.

---

## Frequently Asked Questions (FAQ)

**Q: Where are version data stored?**  
A: In the `.DFM` folder at the project root. Database: `forester.db`; objects: `objects/`.

**Q: Can I move the project folder?**  
A: Yes—just copy the entire project folder (including `.DFM`). The add-on will detect the repository automatically.

**Q: What if the database is corrupted?**  
A: Use **Rebuild Database** in the add-on settings.

**Q: How do I delete the repository?**  
A: Simply delete the `.DFM` folder. You can reinitialize with **"Init Project"**.

**Q: Does it work with multiple `.blend` files in one project?**  
A: Yes—`project` commits save all files; `mesh_only` commits work per active file.

**Q: Can I use it alongside Git?**  
A: Yes, but add `.DFM/` to your `.gitignore`—it’s a large binary version store specific to Blender.

---

## Support

If you encounter issues:
- Ensure your `.blend` file is **saved**.
- Confirm the repository is **initialized**.
- Use the **"Refresh"** button to update lists.
- Check Blender’s console for logs (if available).

**Author:** Dmitry Litvinov  
**Email:** [nopomuk@yandex.ru](mailto:nopomuk@yandex.ru)

--- 

Let me know if you'd like this as a downloadable `.md` file or need any part clarified!