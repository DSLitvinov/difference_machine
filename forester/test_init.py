#!/usr/bin/env python3
"""
Test script for Forester init command.
"""

import tempfile
import shutil
from pathlib import Path
import sys
import json

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from forester.commands.init import init_repository, is_repository, find_repository
from forester.core.metadata import Metadata
from forester.core.database import ForesterDB
from forester.core.ignore import IgnoreRules


def test_init_repository():
    """Test repository initialization."""
    print("Testing init_repository...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir) / "test_project"
        project_path.mkdir()
        
        # Test initialization
        result = init_repository(project_path)
        assert result is True, "init_repository should return True"
        print("  ✓ Repository initialized")
        
        # Check .DFM directory structure
        dfm_dir = project_path / ".DFM"
        assert dfm_dir.exists(), ".DFM directory should exist"
        assert (dfm_dir / "forester.db").exists(), "forester.db should exist"
        assert (dfm_dir / "metadata.json").exists(), "metadata.json should exist"
        assert (dfm_dir / ".dfmignore").exists(), ".dfmignore should exist"
        assert (dfm_dir / "HEAD").exists(), "HEAD file should exist"
        assert (dfm_dir / "refs" / "branches" / "main").exists(), "main branch ref should exist"
        assert (dfm_dir / "objects" / "blobs").exists(), "blobs directory should exist"
        assert (dfm_dir / "objects" / "trees").exists(), "trees directory should exist"
        assert (dfm_dir / "objects" / "commits").exists(), "commits directory should exist"
        assert (dfm_dir / "objects" / "meshes").exists(), "meshes directory should exist"
        assert (dfm_dir / "stash").exists(), "stash directory should exist"
        assert (dfm_dir / "temp_view").exists(), "temp_view directory should exist"
        print("  ✓ Directory structure created")
        
        # Test metadata
        metadata = Metadata(dfm_dir / "metadata.json")
        metadata.load()
        assert metadata.current_branch == "main", "Current branch should be 'main'"
        assert metadata.head is None, "HEAD should be None initially"
        assert metadata.get("version") == "1.0", "Version should be 1.0"
        print("  ✓ Metadata initialized correctly")
        
        # Test database
        with ForesterDB(dfm_dir / "forester.db") as db:
            # Check that tables exist by trying to query them
            cursor = db.conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            assert "commits" in tables, "commits table should exist"
            assert "trees" in tables, "trees table should exist"
            assert "blobs" in tables, "blobs table should exist"
            assert "meshes" in tables, "meshes table should exist"
            assert "stash" in tables, "stash table should exist"
        print("  ✓ Database schema created")
        
        # Test .dfmignore
        ignore_file = dfm_dir / ".dfmignore"
        assert ignore_file.exists(), ".dfmignore should exist"
        ignore_rules = IgnoreRules(ignore_file)
        assert ignore_rules.should_ignore(project_path / ".DFM" / "test", project_path), \
            "Should ignore .DFM directory"
        print("  ✓ .dfmignore created with default rules")
        
        # Test HEAD file
        head_file = dfm_dir / "HEAD"
        with open(head_file, 'r') as f:
            head_content = f.read().strip()
        assert head_content == "main", "HEAD should point to 'main'"
        print("  ✓ HEAD file created")
        
        # Test branch reference
        branch_ref = dfm_dir / "refs" / "branches" / "main"
        assert branch_ref.exists(), "main branch ref should exist"
        print("  ✓ Branch reference created")
    
    print("  ✓ All init tests passed!\n")


def test_is_repository():
    """Test is_repository function."""
    print("Testing is_repository...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir) / "test_project"
        project_path.mkdir()
        
        # Should return False before initialization
        assert not is_repository(project_path), "Should return False before init"
        print("  ✓ Returns False for non-repository")
        
        # Initialize repository
        init_repository(project_path)
        
        # Should return True after initialization
        assert is_repository(project_path), "Should return True after init"
        print("  ✓ Returns True for repository")
        
        # Should return False for subdirectory
        subdir = project_path / "subdir"
        subdir.mkdir()
        assert not is_repository(subdir), "Should return False for subdirectory"
        print("  ✓ Returns False for subdirectory")
    
    print("  ✓ All is_repository tests passed!\n")


def test_find_repository():
    """Test find_repository function."""
    print("Testing find_repository...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir) / "test_project"
        project_path.mkdir()
        
        # Should return None before initialization
        result = find_repository(project_path)
        assert result is None, "Should return None before init"
        print("  ✓ Returns None for non-repository")
        
        # Initialize repository
        init_repository(project_path)
        
        # Should find repository from project root
        result = find_repository(project_path)
        assert result == project_path, "Should find repository at project root"
        print("  ✓ Finds repository from root")
        
        # Should find repository from subdirectory
        subdir = project_path / "subdir" / "nested"
        subdir.mkdir(parents=True)
        result = find_repository(subdir)
        assert result == project_path, "Should find repository from subdirectory"
        print("  ✓ Finds repository from subdirectory")
    
    print("  ✓ All find_repository tests passed!\n")


def test_force_reinit():
    """Test force reinitialization."""
    print("Testing force reinitialization...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir) / "test_project"
        project_path.mkdir()
        
        # Initialize repository
        init_repository(project_path)
        
        # Modify metadata
        metadata = Metadata(project_path / ".DFM" / "metadata.json")
        metadata.load()
        metadata.set("test_key", "test_value")
        
        # Reinitialize with force
        init_repository(project_path, force=True)
        
        # Check that metadata was reset
        metadata.load()
        assert metadata.get("test_key") is None, "Metadata should be reset"
        assert metadata.current_branch == "main", "Branch should be reset to main"
        print("  ✓ Force reinitialization works")
    
    print("  ✓ All force reinit tests passed!\n")


def main():
    """Run all tests."""
    print("=" * 60)
    print("Forester Init Command Test Suite")
    print("=" * 60)
    print()
    
    try:
        test_init_repository()
        test_is_repository()
        test_find_repository()
        test_force_reinit()
        
        print("=" * 60)
        print("✓ All tests passed successfully!")
        print("=" * 60)
        return 0
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())




