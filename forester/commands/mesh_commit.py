"""
Mesh-only commit command for Forester.
Creates commits only for selected meshes.
"""

import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from ..core.database import ForesterDB
from ..core.ignore import IgnoreRules
from ..core.metadata import Metadata
from ..core.storage import ObjectStorage
from ..core.refs import get_current_branch, get_current_head_commit, set_branch_ref
from ..models.tree import Tree, TreeEntry
from ..models.commit import Commit
from ..models.mesh import Mesh
from ..models.blob import Blob
from ..core.hashing import compute_hash


def create_mesh_only_commit(
    repo_path: Path,
    mesh_data_list: List[Dict[str, Any]],  # List of {mesh_name, mesh_json, material_json}
    export_options: Dict[str, bool],
    message: str,
    author: str = "Unknown",
    tag: Optional[str] = None
) -> Optional[str]:
    """
    Create a mesh-only commit from selected meshes.
    
    Args:
        repo_path: Path to repository root
        mesh_data_list: List of mesh data dicts with keys:
            - mesh_name: str (name from Blender)
            - mesh_json: dict (mesh data)
            - material_json: dict (material data)
        export_options: Export options dict (vertices, faces, uv, normals, materials)
        message: Commit message
        author: Author name
        tag: Optional tag
        
    Returns:
        Commit hash if successful, None otherwise
    """
    dfm_dir = repo_path / ".DFM"
    if not dfm_dir.exists():
        raise ValueError(f"Repository not initialized at {repo_path}")
    
    if not mesh_data_list:
        return None  # No meshes to commit
    
    # Get current branch
    branch = get_current_branch(repo_path)
    if not branch:
        raise ValueError("No current branch set")
    
    # Get parent commit
    parent_hash = get_current_head_commit(repo_path)
    
    # Initialize components
    db_path = dfm_dir / "forester.db"
    db = ForesterDB(db_path)
    db.connect()
    
    try:
        storage = ObjectStorage(dfm_dir)
        working_dir = repo_path / "working"
        if not working_dir.exists():
            working_dir = repo_path
        
        tree_entries = []
        mesh_hashes = []
        selected_mesh_names = []
        
        # Process each mesh
        for mesh_data in mesh_data_list:
            mesh_name = mesh_data['mesh_name']
            mesh_json = mesh_data['mesh_json']
            material_json = mesh_data.get('material_json', {})
            
            # Filter mesh_json based on export_options
            filtered_mesh_json = filter_mesh_data(mesh_json, export_options)
            
            # Create mesh object
            combined = {
                "mesh": filtered_mesh_json,
                "material": material_json
            }
            combined_json = json.dumps(combined, sort_keys=True)
            mesh_hash = compute_hash(combined_json.encode('utf-8'))
            
            # Check if mesh already exists
            if not db.mesh_exists(mesh_hash):
                # Save mesh to storage
                mesh_storage_data = {
                    "mesh_json": filtered_mesh_json,
                    "material_json": material_json
                }
                storage_path = storage.save_mesh(mesh_storage_data, mesh_hash)
                
                # Add to database
                import time
                created_at = int(time.time())
                db.add_mesh(
                    mesh_hash=mesh_hash,
                    path=str(storage_path),
                    mesh_json_path=str(storage_path / "mesh.json"),
                    material_json_path=str(storage_path / "material.json"),
                    created_at=created_at
                )
            
            mesh_hashes.append(mesh_hash)
            selected_mesh_names.append(mesh_name)
            
            # Create blobs for mesh.json and material.json files
            # Use mesh_hash as directory name for uniqueness
            mesh_dir_name = mesh_hash[:16]  # Use first 16 chars of hash
            
            # Create blob for mesh.json
            mesh_json_bytes = json.dumps(filtered_mesh_json, indent=2, ensure_ascii=False).encode('utf-8')
            mesh_json_hash = compute_hash(mesh_json_bytes)
            mesh_json_blob = Blob.from_file_data(mesh_json_bytes, mesh_json_hash, dfm_dir, db, storage)
            
            # Create blob for material.json
            material_json_bytes = json.dumps(material_json, indent=2, ensure_ascii=False).encode('utf-8')
            material_json_hash = compute_hash(material_json_bytes)
            material_json_blob = Blob.from_file_data(material_json_bytes, material_json_hash, dfm_dir, db, storage)
            
            # Add to tree entries
            mesh_path = f"meshes/{mesh_dir_name}/mesh.json"
            material_path = f"meshes/{mesh_dir_name}/material.json"
            
            tree_entries.append(TreeEntry(
                path=mesh_path,
                type="blob",
                hash=mesh_json_blob.hash,
                size=mesh_json_blob.size
            ))
            
            tree_entries.append(TreeEntry(
                path=material_path,
                type="blob",
                hash=material_json_blob.hash,
                size=material_json_blob.size
            ))
        
        # Create tree object (only with mesh files)
        tree = Tree(hash="", entries=tree_entries)
        tree.hash = tree.compute_hash()
        
        # Check if tree already exists (no changes)
        if db.tree_exists(tree.hash):
            if parent_hash:
                parent_commit = Commit.from_storage(parent_hash, db, storage)
                if parent_commit and parent_commit.tree_hash == tree.hash:
                    # No changes detected
                    db.close()
                    return None
        
        # Save tree
        tree.save_to_storage(db, storage)
        
        # Create commit object
        commit = Commit.create(
            tree=tree,
            branch=branch,
            message=message,
            author=author,
            parent_hash=parent_hash,
            mesh_hashes=mesh_hashes,
            commit_type="mesh_only",
            selected_mesh_names=selected_mesh_names,
            export_options=export_options
        )
        
        # Save commit
        commit.save_to_storage(db, storage)
        
        # Update branch reference
        set_branch_ref(repo_path, branch, commit.hash)
        
        # Update metadata
        metadata_path = dfm_dir / "metadata.json"
        metadata = Metadata(metadata_path)
        metadata.load()
        metadata.head = commit.hash
        metadata.save()
        
        return commit.hash
        
    finally:
        db.close()


def filter_mesh_data(mesh_json: Dict[str, Any], export_options: Dict[str, bool]) -> Dict[str, Any]:
    """
    Filter mesh data based on export options.
    
    Args:
        mesh_json: Full mesh JSON data
        export_options: Export options dict
        
    Returns:
        Filtered mesh JSON
    """
    filtered = {}
    
    if export_options.get('vertices', True):
        if 'vertices' in mesh_json:
            filtered['vertices'] = mesh_json['vertices']
    
    if export_options.get('faces', True):
        if 'faces' in mesh_json:
            filtered['faces'] = mesh_json['faces']
    
    if export_options.get('uv', True):
        if 'uv' in mesh_json:
            filtered['uv'] = mesh_json['uv']
    
    if export_options.get('normals', True):
        if 'normals' in mesh_json:
            filtered['normals'] = mesh_json['normals']
    
    if export_options.get('materials', True):
        if 'materials' in mesh_json:
            filtered['materials'] = mesh_json['materials']
    
    # Always include basic metadata
    if 'metadata' in mesh_json:
        filtered['metadata'] = mesh_json['metadata']
    
    return filtered


def auto_compress_mesh_commits(
    repo_path: Path,
    mesh_names: List[str],
    keep_last_n: int = 5
) -> int:
    """
    Delete old mesh-only commits for specified meshes.
    Keep only last N commits per mesh.
    
    Args:
        repo_path: Path to repository root
        mesh_names: List of mesh names to compress
        keep_last_n: Keep last N commits per mesh
        
    Returns:
        Number of commits deleted
    """
    dfm_dir = repo_path / ".DFM"
    if not dfm_dir.exists():
        return 0
    
    db_path = dfm_dir / "forester.db"
    with ForesterDB(db_path) as db:
        # Get all mesh-only commits
        cursor = db.conn.cursor()
        cursor.execute("""
            SELECT hash, selected_mesh_names, timestamp 
            FROM commits 
            WHERE commit_type = 'mesh_only'
            ORDER BY timestamp DESC
        """)
        
        commits = cursor.fetchall()
        
        # Group commits by mesh name
        mesh_commits = {name: [] for name in mesh_names}
        
        for commit in commits:
            try:
                selected_names = json.loads(commit['selected_mesh_names']) if commit['selected_mesh_names'] else []
                for mesh_name in mesh_names:
                    if mesh_name in selected_names:
                        mesh_commits[mesh_name].append({
                            'hash': commit['hash'],
                            'timestamp': commit['timestamp']
                        })
            except (json.JSONDecodeError, TypeError):
                continue
        
        # Delete old commits (keep last N)
        deleted_count = 0
        for mesh_name, commit_list in mesh_commits.items():
            if len(commit_list) > keep_last_n:
                # Sort by timestamp (newest first)
                commit_list.sort(key=lambda x: x['timestamp'], reverse=True)
                # Delete old ones
                for commit in commit_list[keep_last_n:]:
                    db.delete_commit(commit['hash'])
                    deleted_count += 1
        
        return deleted_count



