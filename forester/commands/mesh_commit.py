"""
Mesh-only commit command for Forester.
Creates commits only for selected meshes.
"""

import json
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any, Callable
from ..core.database import ForesterDB
from ..core.ignore import IgnoreRules
from ..core.storage import ObjectStorage
from ..core.refs import get_current_branch, get_current_head_commit, set_branch_ref
from ..models.tree import Tree, TreeEntry
from ..models.commit import Commit
from ..models.mesh import Mesh
from ..models.blob import Blob
from ..models.texture import Texture
from ..core.hashing import compute_hash

logger = logging.getLogger(__name__)

# Global registry for material update hooks
# Plugins can register functions to update material_json after texture processing
_material_update_hooks: List[Callable[[Dict[str, Any], List[Dict[str, Any]]], Dict[str, Any]]] = []


def register_material_update_hook(hook_func: Callable[[Dict[str, Any], List[Dict[str, Any]]], Dict[str, Any]]) -> None:
    """
    Register a hook function to update material_json after texture processing.
    
    This allows plugins (Blender, Cinema 4D, etc.) to update their application-specific
    material structures with texture paths after Forester processes textures.
    
    Args:
        hook_func: Function that takes (material_json, texture_info_list) and returns updated material_json
                   Signature: def hook(material_json: Dict, textures: List[Dict]) -> Dict
    """
    if hook_func not in _material_update_hooks:
        _material_update_hooks.append(hook_func)
        logger.debug(f"Registered material update hook: {hook_func.__name__}")


def unregister_material_update_hook(hook_func: Callable[[Dict[str, Any], List[Dict[str, Any]]], Dict[str, Any]]) -> None:
    """
    Unregister a material update hook.
    
    Args:
        hook_func: Hook function to unregister
    """
    if hook_func in _material_update_hooks:
        _material_update_hooks.remove(hook_func)
        logger.debug(f"Unregistered material update hook: {hook_func.__name__}")


def _apply_material_update_hooks(material_json: Dict[str, Any], textures: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Apply all registered hooks to update material_json.
    
    Args:
        material_json: Material JSON dict
        textures: List of processed texture info dicts
        
    Returns:
        Updated material_json
    """
    if not _material_update_hooks:
        return material_json
    
    updated_material_json = material_json.copy()
    
    for hook in _material_update_hooks:
        try:
            updated_material_json = hook(updated_material_json, textures)
        except Exception as e:
            logger.warning(f"Material update hook '{hook.__name__}' failed: {e}", exc_info=True)
    
    return updated_material_json


def create_mesh_only_commit(
    repo_path: Path,
    mesh_data_list: List[Dict[str, Any]],  # List of {mesh_name, blend_path, metadata, obj}
    export_options: Dict[str, bool],
    message: str,
    author: str = "Unknown",
    screenshot_hash: Optional[str] = None,
    skip_hooks: bool = False
) -> Optional[str]:
    """
    Create a mesh-only commit from selected meshes.

    Args:
        repo_path: Path to repository root
        mesh_data_list: List of mesh data dicts with keys:
            - mesh_name: str (object name from source application)
            - blend_path: Path to .blend file
            - metadata: dict with mesh_json, material_json (for diff and textures)
            - obj: Blender object (for texture processing)
        export_options: Export options dict (vertices, faces, uv, normals, materials)
        message: Commit message
        author: Author name
        screenshot_hash: Optional screenshot blob hash
        skip_hooks: If True, skip pre-commit and post-commit hooks

    Returns:
        Commit hash if successful, None otherwise
        
    Note:
        Material update hooks registered via register_material_update_hook()
        will be called to update application-specific material structures
        after texture processing.
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

    # Run pre-commit hook
    if not skip_hooks:
        from ..core.hooks import run_pre_commit_hook
        try:
            run_pre_commit_hook(repo_path, branch, author, message, skip_hooks=False)
        except ValueError as e:
            raise ValueError(f"Pre-commit hook failed: {str(e)}")

    # Get parent commit
    parent_hash = get_current_head_commit(repo_path)

    # Initialize components
    db_path = dfm_dir / "forester.db"

    with ForesterDB(db_path) as db:
        storage = ObjectStorage(dfm_dir)
        working_dir = repo_path / "working"
        if not working_dir.exists():
            working_dir = repo_path

        tree_entries = []
        mesh_hashes = []
        selected_mesh_names = []
        versioned_textures = []  # List of (texture_hash, mesh_hash) tuples for linking to commit

        # Get previous commit for texture comparison
        previous_textures_map = {}
        if parent_hash:
            parent_commit = Commit.from_storage(parent_hash, db, storage)
            if parent_commit and parent_commit.mesh_hashes:
                # Build map of textures from previous commit
                for prev_mesh_hash in parent_commit.mesh_hashes:
                    prev_mesh = Mesh.from_storage(prev_mesh_hash, db, storage)
                    if prev_mesh and prev_mesh.material_json.get('textures'):
                        for tex in prev_mesh.material_json['textures']:
                            # Use image_name as key for comparison
                            key = tex.get('image_name') or tex.get('node_name', '')
                            if key:
                                previous_textures_map[key] = tex

        # Process each mesh
        for mesh_data in mesh_data_list:
            mesh_name = mesh_data['mesh_name']
            blend_path = Path(mesh_data['blend_path'])
            metadata = mesh_data['metadata']
            obj = mesh_data.get('obj')  # Blender object для обработки текстур
            
            mesh_json = metadata.get('mesh_json', {})
            material_json = metadata.get('material_json', {})

            # Process textures - copy only changed ones
            if material_json and 'textures' in material_json:
                # Get storage path for this mesh (will be created later)
                # We need to process textures before creating mesh hash
                textures = material_json['textures']
                processed_textures = []

                for texture_info in textures:
                    image_name = texture_info.get('image_name', '')
                    current_hash = texture_info.get('file_hash')

                    # Check if texture changed
                    needs_copy = True
                    if image_name in previous_textures_map:
                        prev_tex = previous_textures_map[image_name]
                        prev_hash = prev_tex.get('file_hash')

                        if prev_hash and current_hash and prev_hash == current_hash:
                            # Texture unchanged - use reference
                            needs_copy = False
                            texture_info['copied'] = False
                            texture_info['commit_path'] = prev_tex.get('commit_path')
                            # Keep original_path from previous if available
                            if prev_tex.get('original_path'):
                                texture_info['original_path'] = prev_tex['original_path']

                    if needs_copy and current_hash:
                        # Mark for copying (will be done after we know storage path)
                        texture_info['copied'] = True
                        texture_info['needs_copy'] = True

                    processed_textures.append(texture_info)

                material_json['textures'] = processed_textures

            # Filter mesh_json based on export_options (для метаданных)
            filtered_mesh_json = filter_mesh_data(mesh_json, export_options)
            
            # Обновляем метаданные с отфильтрованными данными
            filtered_metadata = metadata.copy()
            filtered_metadata['mesh_json'] = filtered_mesh_json

            # Compute hash from blend file + metadata
            from ..core.hashing import compute_file_hash
            blend_hash = compute_file_hash(blend_path)
            metadata_json = json.dumps(filtered_metadata, sort_keys=True)
            combined = blend_hash + metadata_json
            mesh_hash = compute_hash(combined.encode('utf-8'))

            # Check if mesh already exists
            if not db.mesh_exists(mesh_hash):
                # Save mesh to storage (blend file + metadata)
                mesh_storage_data = {
                    "blend_path": str(blend_path),
                    "metadata": filtered_metadata
                }
                storage_path = storage.save_mesh(mesh_storage_data, mesh_hash)

                # Copy textures that need copying
                if material_json and 'textures' in material_json:
                    textures_dir = storage_path / "textures"
                    textures_dir.mkdir(exist_ok=True)

                    import shutil
                    import os

                    for texture_info in material_json['textures']:
                        if texture_info.get('needs_copy'):
                            # Copy texture file
                            original_path = texture_info.get('original_path')
                            if original_path:
                                # Convert relative path to absolute with proper normalization
                                try:
                                    if os.path.isabs(original_path):
                                        abs_path = Path(original_path).resolve()
                                    else:
                                        # Resolve relative to working directory
                                        abs_path = (working_dir / original_path).resolve()
                                    # Additional safety check
                                    if not abs_path.exists():
                                        logger.warning(f"Texture path does not exist: {abs_path}")
                                        continue
                                except (OSError, ValueError) as e:
                                    logger.warning(f"Invalid texture path '{original_path}': {e}")
                                    continue

                                if abs_path.exists() and abs_path.is_file():
                                    texture_filename = abs_path.name
                                    dest_path = textures_dir / texture_filename
                                    shutil.copy2(abs_path, dest_path)
                                    texture_info['commit_path'] = f"textures/{texture_filename}"
                                    texture_info['copied'] = True

                            # Handle packed textures
                            elif texture_info.get('is_packed'):
                                # Packed textures need to be saved from Blender object
                                # This should be handled in the operator that calls this function
                                # For now, we'll skip packed textures in commit
                                texture_info['copied'] = False
                                texture_info['commit_path'] = None

                            # Remove temporary flag
                            texture_info.pop('needs_copy', None)

                    # Apply material update hooks (plugins can update their material structures)
                    if material_json and 'textures' in material_json:
                        material_json = _apply_material_update_hooks(
                            material_json,
                            material_json['textures']
                        )

                    # Update metadata with final texture info
                    filtered_metadata['material_json'] = material_json
                    # Re-save metadata with updated texture info
                    with open(storage_path / "mesh_metadata.json", 'w', encoding='utf-8') as f:
                        json.dump(filtered_metadata, f, indent=2, ensure_ascii=False)

                # Add to database (only for new meshes)
                import time
                created_at = int(time.time())
                db.add_mesh(
                    mesh_hash=mesh_hash,
                    path=str(storage_path),
                    mesh_json_path=str(storage_path / "mesh.json"),
                    material_json_path=str(storage_path / "material.json"),
                    created_at=created_at
                )
            else:
                # Mesh exists - load existing metadata and update node_data if needed
                mesh_info = db.get_mesh(mesh_hash)
                storage_path = Path(mesh_info['path'])

                # Check if textures need to be copied (they might have changed)
                # Load existing metadata first to check existing textures
                metadata_path = storage_path / "mesh_metadata.json"
                existing_metadata = None
                existing_material_json = None
                if metadata_path.exists():
                    with open(metadata_path, 'r', encoding='utf-8') as f:
                        existing_metadata = json.load(f)
                        existing_material_json = existing_metadata.get('material_json', {})

                # Check and copy changed textures
                if material_json and 'textures' in material_json and existing_material_json:
                    # Build map of existing textures by image_name
                    existing_textures_map = {}
                    if 'textures' in existing_material_json:
                        for tex in existing_material_json['textures']:
                            img_name = tex.get('image_name', '')
                            if img_name:
                                existing_textures_map[img_name] = tex

                    textures_dir = storage_path / "textures"
                    textures_dir.mkdir(exist_ok=True)

                    import shutil
                    import os

                    for texture_info in material_json['textures']:
                        image_name = texture_info.get('image_name', '')
                        current_hash = texture_info.get('file_hash')

                        # Check if texture changed compared to existing version
                        needs_copy_for_existing = False
                        if image_name in existing_textures_map:
                            existing_tex = existing_textures_map[image_name]
                            existing_hash = existing_tex.get('file_hash')
                            if existing_hash and current_hash and existing_hash != current_hash:
                                # Texture changed - needs copy
                                needs_copy_for_existing = True
                        else:
                            # New texture - needs copy
                            needs_copy_for_existing = True

                        if needs_copy_for_existing and current_hash:
                            # Copy texture file
                            original_path = texture_info.get('original_path')
                            if original_path:
                                try:
                                    if os.path.isabs(original_path):
                                        abs_path = Path(original_path).resolve()
                                    else:
                                        abs_path = (working_dir / original_path).resolve()
                                    if not abs_path.exists():
                                        logger.warning(f"Texture path does not exist: {abs_path}")
                                        continue
                                except (OSError, ValueError) as e:
                                    logger.warning(f"Invalid texture path '{original_path}': {e}")
                                    continue

                                if abs_path.exists() and abs_path.is_file():
                                    texture_filename = abs_path.name
                                    dest_path = textures_dir / texture_filename
                                    shutil.copy2(abs_path, dest_path)
                                    texture_info['commit_path'] = f"textures/{texture_filename}"
                                    texture_info['copied'] = True
                                    logger.debug(f"Copied changed texture: {texture_filename} to {dest_path}")
                                    
                                    # Version texture independently (will link to commit after commit creation)
                                    try:
                                        texture = Texture.from_file(abs_path, dfm_dir, db, storage)
                                        # Store texture hash for later linking
                                        versioned_textures.append((texture.hash, mesh_hash))
                                        logger.debug(f"Versioned texture: {texture.hash[:16]}...")
                                    except Exception as e:
                                        logger.warning(f"Failed to version texture {abs_path}: {e}", exc_info=True)
                        elif image_name in existing_textures_map:
                            # Texture unchanged - use existing commit_path
                            existing_tex = existing_textures_map[image_name]
                            texture_info['copied'] = False
                            texture_info['commit_path'] = existing_tex.get('commit_path')
                            if existing_tex.get('original_path'):
                                texture_info['original_path'] = existing_tex['original_path']

                # Apply material update hooks for existing meshes
                if existing_material_json and 'textures' in material_json:
                    # Apply hooks to update existing material_json with new texture paths
                    updated_material_json = _apply_material_update_hooks(
                        existing_material_json,
                        material_json['textures']
                    )
                    
                    # Save updated material.json if it was modified
                    if updated_material_json != existing_material_json:
                        # Update metadata with updated material_json
                        if existing_metadata:
                            existing_metadata['material_json'] = updated_material_json
                            with open(metadata_path, 'w', encoding='utf-8') as f:
                                json.dump(existing_metadata, f, indent=2, ensure_ascii=False)

            mesh_hashes.append(mesh_hash)
            selected_mesh_names.append(mesh_name)

            # Create blobs for mesh.blend and mesh_metadata.json files
            # Use mesh_hash as directory name for uniqueness
            mesh_dir_name = mesh_hash[:16]  # Use first 16 chars of hash

            # Create blob for mesh.blend
            with open(storage_path / "mesh.blend", 'rb') as f:
                blend_data = f.read()
            blend_hash = compute_hash(blend_data)
            blend_blob = Blob.from_file_data(blend_data, blend_hash, dfm_dir, db, storage)

            # Create blob for mesh_metadata.json
            metadata_bytes = json.dumps(filtered_metadata, indent=2, ensure_ascii=False).encode('utf-8')
            metadata_hash = compute_hash(metadata_bytes)
            metadata_blob = Blob.from_file_data(metadata_bytes, metadata_hash, dfm_dir, db, storage)

            # Add to tree entries
            mesh_blend_path = f"meshes/{mesh_dir_name}/mesh.blend"
            metadata_path = f"meshes/{mesh_dir_name}/mesh_metadata.json"

            tree_entries.append(TreeEntry(
                path=mesh_blend_path,
                type="blob",
                hash=blend_blob.hash,
                size=blend_blob.size
            ))

            tree_entries.append(TreeEntry(
                path=metadata_path,
                type="blob",
                hash=metadata_blob.hash,
                size=metadata_blob.size
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
            export_options=export_options,
            screenshot_hash=screenshot_hash
        )

        # Save commit
        commit.save_to_storage(db, storage)

        # Link versioned textures to commit
        for texture_hash, mesh_hash in versioned_textures:
            db.link_texture_to_commit(texture_hash, commit.hash, mesh_hash)
        if versioned_textures:
            logger.debug(f"Linked {len(versioned_textures)} textures to commit {commit.hash[:16]}...")

        # Update branch reference
        set_branch_ref(repo_path, branch, commit.hash)

        # Update HEAD in database
        db.set_head(commit.hash)

        # Run post-commit hook
        if not skip_hooks:
            from ..core.hooks import run_post_commit_hook
            run_post_commit_hook(repo_path, commit.hash, branch, author, message, skip_hooks=False)

        return commit.hash


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



