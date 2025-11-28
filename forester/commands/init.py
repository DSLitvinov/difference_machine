"""
Init command for Forester.
Initializes a new Forester repository.
"""

from pathlib import Path
from typing import Optional
from ..core.database import ForesterDB
from ..core.ignore import IgnoreRules
from ..core.storage import ObjectStorage


def init_repository(project_path: Path, force: bool = False) -> bool:
    """
    Initialize a new Forester repository.
    
    Args:
        project_path: Path to project directory (where .DFM/ will be created)
        force: If True, reinitialize even if repository already exists
        
    Returns:
        True if initialization successful, False otherwise
        
    Raises:
        ValueError: If project_path is not a directory
        FileExistsError: If repository already exists and force=False
    """
    # Validate project path
    if not project_path.exists():
        project_path.mkdir(parents=True, exist_ok=True)
    
    if not project_path.is_dir():
        raise ValueError(f"Project path must be a directory: {project_path}")
    
    # Check if repository already exists
    dfm_dir = project_path / ".DFM"
    if dfm_dir.exists() and not force:
        raise FileExistsError(f"Repository already exists at {dfm_dir}")
    
    # Create .DFM directory structure
    dfm_dir.mkdir(exist_ok=True)
    
    # Create subdirectories
    objects_dir = dfm_dir / "objects"
    for obj_type in ["blobs", "trees", "commits", "meshes"]:
        (objects_dir / obj_type).mkdir(parents=True, exist_ok=True)
    
    refs_dir = dfm_dir / "refs" / "branches"
    refs_dir.mkdir(parents=True, exist_ok=True)
    
    stash_dir = dfm_dir / "stash"
    stash_dir.mkdir(exist_ok=True)
    
    # Initialize database
    db_path = dfm_dir / "forester.db"
    with ForesterDB(db_path) as db:
        db.initialize_schema()
        # Initialize repository state (current branch and HEAD)
        db.set_branch_and_head("main", None)
    
    # Create .dfmignore file
    ignore_file = dfm_dir / ".dfmignore"
    ignore_rules = IgnoreRules(ignore_file)
    ignore_rules.create_default_file()
    
    # Create initial branch reference (points to NULL)
    branch_ref_file = refs_dir / "main"
    with open(branch_ref_file, 'w', encoding='utf-8') as f:
        f.write("\n")  # Empty file means no commit yet
    
    # Initialize object storage (ensures directories exist)
    storage = ObjectStorage(dfm_dir)
    
    return True


def is_repository(path: Path) -> bool:
    """
    Check if path is a Forester repository.
    
    Args:
        path: Path to check
        
    Returns:
        True if path contains .DFM/ directory with forester.db
    """
    dfm_dir = path / ".DFM"
    db_path = dfm_dir / "forester.db"
    return dfm_dir.exists() and db_path.exists()


def find_repository(start_path: Path) -> Optional[Path]:
    """
    Find Forester repository by walking up the directory tree.
    
    Args:
        start_path: Starting path to search from
        
    Returns:
        Path to repository root, or None if not found
    """
    current = start_path.resolve()
    
    while True:
        if is_repository(current):
            return current
        
        parent = current.parent
        if parent == current:  # Reached filesystem root
            break
        current = parent
    
    return None




