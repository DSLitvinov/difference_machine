"""
Mesh diff model for Forester.
Represents differences between two versions of a mesh.
"""

from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass, field


@dataclass
class GeometryDiff:
    """Changes in mesh geometry."""
    
    # Vertices
    vertices_added: List[int] = field(default_factory=list)  # Indices of added vertices
    vertices_removed: List[int] = field(default_factory=list)  # Indices of removed vertices
    vertices_modified: Dict[int, Tuple[List[float], List[float]]] = field(default_factory=dict)  # {index: (old_pos, new_pos)}
    vertices_moved: Dict[int, float] = field(default_factory=dict)  # {index: distance_moved}
    
    # Faces
    faces_added: List[List[int]] = field(default_factory=list)  # Added faces (vertex indices)
    faces_removed: List[List[int]] = field(default_factory=list)  # Removed faces (vertex indices)
    faces_modified: Dict[int, List[int]] = field(default_factory=dict)  # {old_index: new_vertex_indices}
    
    # UV coordinates
    uv_changed: Dict[int, Tuple[List[float], List[float]]] = field(default_factory=dict)  # {vertex_index: (old_uv, new_uv)}
    
    # Normals
    normals_changed: Dict[int, Tuple[List[float], List[float]]] = field(default_factory=dict)  # {vertex_index: (old_normal, new_normal)}


@dataclass
class MaterialDiff:
    """Changes in materials."""
    
    # Base properties
    properties_changed: Dict[str, Tuple[Any, Any]] = field(default_factory=dict)  # {property_name: (old_value, new_value)}
    
    # Textures
    textures_added: List[str] = field(default_factory=list)  # Hashes of added textures
    textures_removed: List[str] = field(default_factory=list)  # Hashes of removed textures
    textures_modified: List[str] = field(default_factory=list)  # Hashes of modified textures
    
    # Node tree
    nodes_added: List[Dict[str, Any]] = field(default_factory=list)  # Added nodes
    nodes_removed: List[Dict[str, Any]] = field(default_factory=list)  # Removed nodes
    nodes_modified: Dict[str, Dict[str, Tuple[Any, Any]]] = field(default_factory=dict)  # {node_name: {property: (old, new)}}
    links_changed: List[Dict[str, Any]] = field(default_factory=list)  # Changed links between nodes


@dataclass
class DiffStatistics:
    """Statistics about changes."""
    
    vertices_added_count: int = 0
    vertices_removed_count: int = 0
    vertices_modified_count: int = 0
    faces_added_count: int = 0
    faces_removed_count: int = 0
    faces_modified_count: int = 0
    
    # Percentage changes
    geometry_change_percent: float = 0.0  # How much geometry changed (0-100)
    material_change_percent: float = 0.0  # How much material changed (0-100)
    
    # Metrics
    max_vertex_displacement: float = 0.0  # Maximum vertex displacement
    avg_vertex_displacement: float = 0.0  # Average vertex displacement
    
    # Material statistics
    textures_added_count: int = 0
    textures_removed_count: int = 0
    textures_modified_count: int = 0
    nodes_added_count: int = 0
    nodes_removed_count: int = 0
    nodes_modified_count: int = 0


@dataclass
class MeshDiff:
    """Result of comparing two mesh versions."""
    
    mesh_name: str
    geometry_diff: GeometryDiff
    material_diff: MaterialDiff
    statistics: DiffStatistics
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'mesh_name': self.mesh_name,
            'geometry_diff': {
                'vertices_added': self.geometry_diff.vertices_added,
                'vertices_removed': self.geometry_diff.vertices_removed,
                'vertices_modified': {
                    str(k): v for k, v in self.geometry_diff.vertices_modified.items()
                },
                'vertices_moved': {
                    str(k): v for k, v in self.geometry_diff.vertices_moved.items()
                },
                'faces_added': self.geometry_diff.faces_added,
                'faces_removed': self.geometry_diff.faces_removed,
                'faces_modified': {
                    str(k): v for k, v in self.geometry_diff.faces_modified.items()
                },
            },
            'material_diff': {
                'properties_changed': {
                    k: v for k, v in self.material_diff.properties_changed.items()
                },
                'textures_added': self.material_diff.textures_added,
                'textures_removed': self.material_diff.textures_removed,
                'textures_modified': self.material_diff.textures_modified,
            },
            'statistics': {
                'vertices_added_count': self.statistics.vertices_added_count,
                'vertices_removed_count': self.statistics.vertices_removed_count,
                'vertices_modified_count': self.statistics.vertices_modified_count,
                'faces_added_count': self.statistics.faces_added_count,
                'faces_removed_count': self.statistics.faces_removed_count,
                'faces_modified_count': self.statistics.faces_modified_count,
                'geometry_change_percent': self.statistics.geometry_change_percent,
                'material_change_percent': self.statistics.material_change_percent,
                'max_vertex_displacement': self.statistics.max_vertex_displacement,
                'avg_vertex_displacement': self.statistics.avg_vertex_displacement,
                'textures_added_count': self.statistics.textures_added_count,
                'textures_removed_count': self.statistics.textures_removed_count,
                'textures_modified_count': self.statistics.textures_modified_count,
                'nodes_added_count': self.statistics.nodes_added_count,
                'nodes_removed_count': self.statistics.nodes_removed_count,
                'nodes_modified_count': self.statistics.nodes_modified_count,
            }
        }

