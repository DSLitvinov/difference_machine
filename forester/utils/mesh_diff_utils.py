"""
Utilities for computing mesh differences.
"""

import math
import logging
from typing import Dict, List, Tuple, Any, Optional
from ..models.mesh_diff import (
    MeshDiff,
    GeometryDiff,
    MaterialDiff,
    DiffStatistics
)

logger = logging.getLogger(__name__)


def compute_geometry_diff(
    old_mesh_json: Dict[str, Any],
    new_mesh_json: Dict[str, Any],
    tolerance: float = 0.001
) -> GeometryDiff:
    """
    Compute differences between two mesh geometry versions.
    
    Args:
        old_mesh_json: Old mesh data
        new_mesh_json: New mesh data
        tolerance: Distance tolerance for vertex matching
        
    Returns:
        GeometryDiff object with all changes
    """
    diff = GeometryDiff()
    
    old_vertices = old_mesh_json.get('vertices', [])
    new_vertices = new_mesh_json.get('vertices', [])
    
    if not old_vertices and not new_vertices:
        return diff
    
    # Simple vertex matching: compare by index first, then by position
    # For more complex cases, we'd use KD-tree, but for now keep it simple
    old_vertex_count = len(old_vertices)
    new_vertex_count = len(new_vertices)
    
    # Build position map for old vertices
    old_positions = {tuple(v): i for i, v in enumerate(old_vertices)}
    
    # Match vertices
    vertex_mapping = {}  # {new_index: old_index}
    old_matched = set()
    
    for new_idx, new_vertex in enumerate(new_vertices):
        new_pos = tuple(new_vertex)
        
        # Try exact match first
        if new_pos in old_positions:
            old_idx = old_positions[new_pos]
            if old_idx not in old_matched:
                vertex_mapping[new_idx] = old_idx
                old_matched.add(old_idx)
                continue
        
        # Try to find closest vertex within tolerance
        best_match = None
        best_distance = float('inf')
        
        for old_idx, old_vertex in enumerate(old_vertices):
            if old_idx in old_matched:
                continue
            
            distance = math.sqrt(
                sum((a - b) ** 2 for a, b in zip(new_vertex, old_vertex))
            )
            
            if distance < tolerance and distance < best_distance:
                best_match = old_idx
                best_distance = distance
        
        if best_match is not None:
            vertex_mapping[new_idx] = best_match
            old_matched.add(best_match)
            
            # Check if vertex moved significantly
            if best_distance > tolerance * 0.1:
                old_pos = old_vertices[best_match]
                diff.vertices_modified[new_idx] = (old_pos, new_vertex)
                diff.vertices_moved[new_idx] = best_distance
        else:
            # New vertex
            diff.vertices_added.append(new_idx)
    
    # Find removed vertices
    diff.vertices_removed = [
        i for i in range(old_vertex_count) if i not in old_matched
    ]
    
    # Compare faces
    old_faces = old_mesh_json.get('faces', [])
    new_faces = new_mesh_json.get('faces', [])
    
    # Normalize face indices through vertex mapping
    def normalize_face(face: List[int], mapping: Dict[int, int]) -> Optional[Tuple[int, ...]]:
        """Normalize face vertex indices through mapping."""
        normalized = []
        for v_idx in face:
            if v_idx in mapping:
                normalized.append(mapping[v_idx])
            else:
                return None  # Face contains unmapped vertex
        return tuple(sorted(normalized)) if normalized else None
    
    # Build face sets for comparison
    old_face_set = {}
    for old_idx, old_face in enumerate(old_faces):
        normalized = normalize_face(old_face, {i: i for i in range(old_vertex_count)})
        if normalized:
            old_face_set[normalized] = old_idx
    
    new_face_set = {}
    for new_idx, new_face in enumerate(new_faces):
        normalized = normalize_face(new_face, vertex_mapping)
        if normalized:
            new_face_set[normalized] = new_idx
    
    # Find added and removed faces
    for normalized, new_idx in new_face_set.items():
        if normalized not in old_face_set:
            diff.faces_added.append(new_faces[new_idx])
    
    for normalized, old_idx in old_face_set.items():
        if normalized not in new_face_set:
            diff.faces_removed.append(old_faces[old_idx])
    
    # Compare UV coordinates
    old_uv = old_mesh_json.get('uv', [])
    new_uv = new_mesh_json.get('uv', [])
    
    if old_uv and new_uv:
        uv_count = min(len(old_uv), len(new_uv))
        for i in range(uv_count):
            if i in vertex_mapping:
                old_idx = vertex_mapping[i]
                if old_idx < len(old_uv):
                    old_uv_val = old_uv[old_idx]
                    new_uv_val = new_uv[i]
                    if old_uv_val != new_uv_val:
                        diff.uv_changed[i] = (old_uv_val, new_uv_val)
    
    # Compare normals
    old_normals = old_mesh_json.get('normals', [])
    new_normals = new_mesh_json.get('normals', [])
    
    if old_normals and new_normals:
        normal_count = min(len(old_normals), len(new_normals))
        for i in range(normal_count):
            if i in vertex_mapping:
                old_idx = vertex_mapping[i]
                if old_idx < len(old_normals):
                    old_normal = old_normals[old_idx]
                    new_normal = new_normals[i]
                    # Compare with tolerance
                    distance = math.sqrt(
                        sum((a - b) ** 2 for a, b in zip(old_normal, new_normal))
                    )
                    if distance > tolerance:
                        diff.normals_changed[i] = (old_normal, new_normal)
    
    return diff


def compute_material_diff(
    old_material_json: Dict[str, Any],
    new_material_json: Dict[str, Any]
) -> MaterialDiff:
    """
    Compute differences between two material versions.
    
    Args:
        old_material_json: Old material data
        new_material_json: New material data
        
    Returns:
        MaterialDiff object with all changes
    """
    diff = MaterialDiff()
    
    if not old_material_json and not new_material_json:
        return diff
    
    if not old_material_json:
        # All new material
        if new_material_json.get('node_tree'):
            diff.nodes_added.extend(new_material_json['node_tree'].get('nodes', []))
        if new_material_json.get('textures'):
            diff.textures_added.extend([
                t.get('file_hash', '') for t in new_material_json['textures']
                if t.get('file_hash')
            ])
        return diff
    
    if not new_material_json:
        # Material removed
        if old_material_json.get('node_tree'):
            diff.nodes_removed.extend(old_material_json['node_tree'].get('nodes', []))
        if old_material_json.get('textures'):
            diff.textures_removed.extend([
                t.get('file_hash', '') for t in old_material_json['textures']
                if t.get('file_hash')
            ])
        return diff
    
    # Compare base properties
    base_props = ['roughness', 'metallic', 'diffuse_color', 'specular_color', 'name']
    for prop in base_props:
        old_val = old_material_json.get(prop)
        new_val = new_material_json.get(prop)
        if old_val != new_val:
            diff.properties_changed[prop] = (old_val, new_val)
    
    # Compare textures by hash
    old_textures = old_material_json.get('textures', [])
    new_textures = new_material_json.get('textures', [])
    
    old_texture_hashes = {
        t.get('file_hash', ''): t for t in old_textures
        if t.get('file_hash')
    }
    new_texture_hashes = {
        t.get('file_hash', ''): t for t in new_textures
        if t.get('file_hash')
    }
    
    old_hashes = set(old_texture_hashes.keys())
    new_hashes = set(new_texture_hashes.keys())
    
    diff.textures_added = list(new_hashes - old_hashes)
    diff.textures_removed = list(old_hashes - new_hashes)
    
    # Check for modified textures (same hash but different properties)
    for hash_val in old_hashes & new_hashes:
        old_tex = old_texture_hashes[hash_val]
        new_tex = new_texture_hashes[hash_val]
        if old_tex != new_tex:
            diff.textures_modified.append(hash_val)
    
    # Compare node trees
    old_node_tree = old_material_json.get('node_tree', {})
    new_node_tree = new_material_json.get('node_tree', {})
    
    if old_node_tree and new_node_tree:
        old_nodes = {n['name']: n for n in old_node_tree.get('nodes', [])}
        new_nodes = {n['name']: n for n in new_node_tree.get('nodes', [])}
        
        old_node_names = set(old_nodes.keys())
        new_node_names = set(new_nodes.keys())
        
        diff.nodes_added = [new_nodes[name] for name in new_node_names - old_node_names]
        diff.nodes_removed = [old_nodes[name] for name in old_node_names - new_node_names]
        
        # Check for modified nodes
        for node_name in old_node_names & new_node_names:
            old_node = old_nodes[node_name]
            new_node = new_nodes[node_name]
            
            node_changes = {}
            # Compare node properties
            if old_node.get('type') != new_node.get('type'):
                node_changes['type'] = (old_node.get('type'), new_node.get('type'))
            
            if old_node.get('properties') != new_node.get('properties'):
                node_changes['properties'] = (old_node.get('properties'), new_node.get('properties'))
            
            if node_changes:
                diff.nodes_modified[node_name] = node_changes
        
        # Compare links
        old_links = old_node_tree.get('links', [])
        new_links = new_node_tree.get('links', [])
        
        def link_key(link):
            return (
                link.get('from_node'),
                link.get('from_socket'),
                link.get('to_node'),
                link.get('to_socket')
            )
        
        old_link_set = {link_key(link) for link in old_links}
        new_link_set = {link_key(link) for link in new_links}
        
        # Links added/removed
        added_links = new_link_set - old_link_set
        removed_links = old_link_set - new_link_set
        
        if added_links or removed_links:
            diff.links_changed = [
                {'added': list(added_links), 'removed': list(removed_links)}
            ]
    
    return diff


def compute_mesh_diff(
    mesh_name: str,
    old_mesh_json: Dict[str, Any],
    old_material_json: Dict[str, Any],
    new_mesh_json: Dict[str, Any],
    new_material_json: Dict[str, Any],
    tolerance: float = 0.001
) -> MeshDiff:
    """
    Compute complete diff between two mesh versions.
    
    Args:
        mesh_name: Name of the mesh
        old_mesh_json: Old mesh geometry data
        old_material_json: Old material data
        new_mesh_json: New mesh geometry data
        new_material_json: New material data
        tolerance: Distance tolerance for vertex matching
        
    Returns:
        MeshDiff object with all changes and statistics
    """
    # Compute geometry diff
    geometry_diff = compute_geometry_diff(old_mesh_json, new_mesh_json, tolerance)
    
    # Compute material diff
    material_diff = compute_material_diff(old_material_json, new_material_json)
    
    # Calculate statistics
    stats = DiffStatistics()
    
    # Geometry statistics
    stats.vertices_added_count = len(geometry_diff.vertices_added)
    stats.vertices_removed_count = len(geometry_diff.vertices_removed)
    stats.vertices_modified_count = len(geometry_diff.vertices_modified)
    stats.faces_added_count = len(geometry_diff.faces_added)
    stats.faces_removed_count = len(geometry_diff.faces_removed)
    stats.faces_modified_count = len(geometry_diff.faces_modified)
    
    # Calculate geometry change percentage
    old_vertex_count = len(old_mesh_json.get('vertices', []))
    new_vertex_count = len(new_mesh_json.get('vertices', []))
    total_vertex_count = max(old_vertex_count, new_vertex_count, 1)
    
    changed_vertices = (
        stats.vertices_added_count +
        stats.vertices_removed_count +
        stats.vertices_modified_count
    )
    stats.geometry_change_percent = (changed_vertices / total_vertex_count) * 100.0
    
    # Calculate vertex displacement metrics
    if geometry_diff.vertices_moved:
        displacements = list(geometry_diff.vertices_moved.values())
        stats.max_vertex_displacement = max(displacements)
        stats.avg_vertex_displacement = sum(displacements) / len(displacements)
    
    # Material statistics
    stats.textures_added_count = len(material_diff.textures_added)
    stats.textures_removed_count = len(material_diff.textures_removed)
    stats.textures_modified_count = len(material_diff.textures_modified)
    stats.nodes_added_count = len(material_diff.nodes_added)
    stats.nodes_removed_count = len(material_diff.nodes_removed)
    stats.nodes_modified_count = len(material_diff.nodes_modified)
    
    # Calculate material change percentage
    old_texture_count = len(old_material_json.get('textures', []))
    new_texture_count = len(new_material_json.get('textures', []))
    total_texture_count = max(old_texture_count, new_texture_count, 1)
    
    changed_textures = (
        stats.textures_added_count +
        stats.textures_removed_count +
        stats.textures_modified_count
    )
    
    old_node_count = len(old_material_json.get('node_tree', {}).get('nodes', []))
    new_node_count = len(new_material_json.get('node_tree', {}).get('nodes', []))
    total_node_count = max(old_node_count, new_node_count, 1)
    
    changed_nodes = (
        stats.nodes_added_count +
        stats.nodes_removed_count +
        stats.nodes_modified_count
    )
    
    # Weighted material change (textures + nodes)
    if total_texture_count > 0 or total_node_count > 0:
        texture_change = (changed_textures / total_texture_count) * 50.0 if total_texture_count > 0 else 0
        node_change = (changed_nodes / total_node_count) * 50.0 if total_node_count > 0 else 0
        stats.material_change_percent = texture_change + node_change
    else:
        stats.material_change_percent = 0.0
    
    return MeshDiff(
        mesh_name=mesh_name,
        geometry_diff=geometry_diff,
        material_diff=material_diff,
        statistics=stats
    )

