"""
Mesh import/export functionality for Difference Machine.
Contains functions for exporting and importing meshes with materials and textures.
"""

import bpy
import os
import json
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple


# Node type mapping for special cases where simple conversion doesn't work
NODE_TYPE_MAP = {
    # Common node types that don't follow the simple pattern
    'CURVE_FLOAT': 'ShaderNodeFloatCurve',
    'CURVE_RGB': 'ShaderNodeRGBCurve',
    'CURVE_VEC': 'ShaderNodeVectorCurve',
    'MAP_RANGE': 'ShaderNodeMapRange',
    'RGB': 'ShaderNodeRGB',
    'VALUE': 'ShaderNodeValue',
    'VALTORGB': 'ShaderNodeValToRGB',  # ColorRamp
    'RGBTOBW': 'ShaderNodeRGBToBW',
    # Add more special cases as needed
}


# ========== EXPORT FUNCTIONS ==========

def export_mesh_to_json(obj, export_options):
    """
    Export Blender mesh object to JSON format with texture tracking.
    
    Args:
        obj: Blender mesh object
        export_options: Dict with export options
        
    Returns:
        Dict with mesh_json and material_json
    """
    mesh = obj.data
    mesh_json = {}
    material_json = {}
    
    # Vertices
    if export_options.get('vertices', True):
        mesh_json['vertices'] = [[v.co.x, v.co.y, v.co.z] for v in mesh.vertices]
    
    # Faces
    if export_options.get('faces', True):
        if mesh.polygons:
            mesh_json['faces'] = [[v for v in face.vertices] for face in mesh.polygons]
        elif mesh.loops:
            # Fallback for older mesh format
            mesh_json['faces'] = []
    
    # UV coordinates
    if export_options.get('uv', True) and mesh.uv_layers.active:
        uv_layer = mesh.uv_layers.active.data
        mesh_json['uv'] = [[uv.uv.x, uv.uv.y] for uv in uv_layer]
    
    # Normals
    if export_options.get('normals', True):
        mesh_json['normals'] = [[v.normal.x, v.normal.y, v.normal.z] for v in mesh.vertices]
    
    # Materials with texture tracking
    if export_options.get('materials', True) and obj.material_slots:
        if obj.material_slots[0].material:
            mat = obj.material_slots[0].material
            material_json = {
                'name': mat.name,
                'use_nodes': mat.use_nodes,
                'diffuse_color': list(mat.diffuse_color[:4]),
                'specular_color': list(mat.specular_color[:3]),
                'roughness': float(mat.roughness),
                'metallic': float(mat.metallic),
                'textures': []  # Список текстур с путями и хешами
            }
            
            if mat.use_nodes and mat.node_tree:
                # Собираем все текстуры из node tree
                textures = []
                for node in mat.node_tree.nodes:
                    if node.type == 'TEX_IMAGE' and node.image:
                        texture_info = {
                            'node_name': node.name,
                            'image_name': node.image.name,
                            'original_path': node.image.filepath,
                            'file_hash': None,  # Будет вычислен при создании коммита
                            'copied': False,  # Будет установлено при создании коммита
                            'commit_path': None  # Путь к текстуре в коммите (если скопирована)
                        }
                        
                        # Вычисляем хеш файла текстуры
                        if node.image.filepath:
                            abs_path = bpy.path.abspath(node.image.filepath)
                            if os.path.exists(abs_path):
                                from forester.core.hashing import compute_file_hash
                                try:
                                    texture_info['file_hash'] = compute_file_hash(Path(abs_path))
                                except Exception:
                                    pass  # Не удалось вычислить хеш
                        
                        # Если текстура упакована в blend файл
                        if node.image.packed_file:
                            texture_info['is_packed'] = True
                            texture_info['packed_size'] = len(node.image.packed_file.data)
                        else:
                            texture_info['is_packed'] = False
                        
                        textures.append(texture_info)
                
                material_json['textures'] = textures
                
                # Экспортируем полную структуру node tree с информацией о текстурах
                material_json['node_tree'] = export_node_tree_structure(mat.node_tree, textures)
    
    # Metadata
    mesh_json['metadata'] = {
        'object_name': obj.name,
        'vertex_count': len(mesh.vertices),
        'face_count': len(mesh.polygons) if mesh.polygons else 0,
    }
    
    return {
        'mesh_json': mesh_json,
        'material_json': material_json,
    }


def export_node_tree_structure(node_tree, textures_info=None):
    """
    Экспортирует структуру node tree с информацией о текстурах для TEX_IMAGE узлов.
    Основано на коде из difference_engine для полной совместимости.
    
    Args:
        node_tree: Blender node tree
        textures_info: Список информации о текстурах (опционально)
    """
    nodes_data = []
    links_data = []
    
    # Build texture lookup map by node name
    texture_map = {}
    if textures_info:
        for tex_info in textures_info:
            node_name = tex_info.get('node_name')
            if node_name:
                texture_map[node_name] = tex_info
    
    for node in node_tree.nodes:
        node_data = {
            'name': node.name,
            'type': node.type,
            'location': [float(node.location.x), float(node.location.y)],
            'width': float(node.width),
            'inputs': [],
            'outputs': [],
            'properties': {}
        }
        
        # Export common node properties
        _export_node_properties(node, node_data)
        
        # Export Node Group reference
        if node.type == 'GROUP' and hasattr(node, 'node_tree') and node.node_tree:
            node_data['properties']['node_tree_name'] = node.node_tree.name
        
        # Export ColorRamp (ValToRGB) data
        if node.type == 'VALTORGB' and hasattr(node, 'color_ramp'):
            _export_color_ramp(node, node_data)
        
        # Export Curve data (Float, RGB, Vector curves)
        if node.type in ('CURVE_FLOAT', 'CURVE_RGB', 'CURVE_VEC'):
            _export_curve_data(node, node_data)
        
        # Handle image texture nodes with enhanced validation
        if node.type == 'TEX_IMAGE' and node.image:
            _export_image_texture(node, node_data, texture_map)
        
        # Export input sockets
        _export_input_sockets(node, node_data)
        
        # Export output sockets
        _export_output_sockets(node, node_data)
        
        nodes_data.append(node_data)
    
    # Export node links
    for link in node_tree.links:
        links_data.append({
            'from_node': link.from_node.name,
            'from_socket': link.from_socket.name,
            'to_node': link.to_node.name,
            'to_socket': link.to_socket.name
        })
    
    return {
        'nodes': nodes_data,
        'links': links_data
    }


def _export_node_properties(node, node_data):
    """Export common node properties"""
    try:
        if hasattr(node, 'operation'):  # Math, VectorMath, etc.
            node_data['properties']['operation'] = node.operation
        if hasattr(node, 'blend_type'):  # Mix nodes
            node_data['properties']['blend_type'] = node.blend_type
        if hasattr(node, 'interpolation'):  # Image Texture
            node_data['properties']['interpolation'] = node.interpolation
        if hasattr(node, 'extension'):  # Image Texture
            node_data['properties']['extension'] = node.extension
        if hasattr(node, 'color_space'):  # Image Texture
            node_data['properties']['color_space'] = node.color_space
        if hasattr(node, 'label'):
            node_data['properties']['label'] = node.label
        if hasattr(node, 'hide'):
            node_data['properties']['hide'] = node.hide
        if hasattr(node, 'mute'):
            node_data['properties']['mute'] = node.mute
    except Exception as e:
        print(f"Warning: Failed to export properties for node {node.name}: {e}")


def _export_color_ramp(node, node_data):
    """Export ColorRamp data"""
    try:
        ramp = node.color_ramp
        ramp_data = {
            'color_mode': ramp.color_mode,
            'interpolation': ramp.interpolation,
            'elements': []
        }
        for element in ramp.elements:
            ramp_data['elements'].append({
                'position': float(element.position),
                'color': [float(element.color[0]), float(element.color[1]), 
                         float(element.color[2]), float(element.color[3])]
            })
        node_data['properties']['color_ramp'] = ramp_data
    except Exception as e:
        print(f"Warning: Failed to export color ramp for node {node.name}: {e}")


def _export_curve_data(node, node_data):
    """Export curve data"""
    try:
        if hasattr(node, 'mapping'):
            mapping = node.mapping
            curves_data = {
                'use_clip': mapping.use_clip if hasattr(mapping, 'use_clip') else True,
                'curves': []
            }
            for curve in mapping.curves:
                curve_points = []
                for point in curve.points:
                    curve_points.append({
                        'location': [float(point.location[0]), float(point.location[1])],
                        'handle_type': point.handle_type
                    })
                curves_data['curves'].append(curve_points)
            node_data['properties']['mapping'] = curves_data
    except Exception as e:
        print(f"Warning: Failed to export curve data for node {node.name}: {e}")


def _export_image_texture(node, node_data, texture_map):
    """Export image texture with enhanced validation"""
    try:
        node_data['image'] = node.image.name
        node_data['image_file'] = node.image.filepath
        
        # Добавляем информацию о текстуре из texture_map (для совместимости с импортом)
        texture_info = texture_map.get(node.name)
        if texture_info:
            # Если текстура была скопирована в коммит, сохраняем путь
            if texture_info.get('copied') and texture_info.get('commit_path'):
                commit_path = texture_info['commit_path']
                # Убираем префикс "textures/" если есть
                if commit_path.startswith('textures/'):
                    commit_path = commit_path.replace('textures/', '', 1)
                node_data['copied_texture'] = commit_path
            # Сохраняем оригинальный путь к файлу
            if texture_info.get('original_path'):
                node_data['image_file'] = texture_info['original_path']
        
        # Handle packed images
        if node.image.packed_file:
            node_data['was_packed'] = True
        else:
            node_data['was_packed'] = False
            
    except Exception as e:
        print(f"Warning: Failed to export image texture for node {node.name}: {e}")


def _export_input_sockets(node, node_data):
    """Export input sockets"""
    try:
        for input_socket in node.inputs:
            # Handle default_value which might be a Blender type (Vector, Color, etc.)
            default_val = getattr(input_socket, 'default_value', None)
            
            # Convert default values safely
            safe_default = None
            if default_val is not None:
                try:
                    # Try to convert to list (works for Vector, Color, etc.)
                    if hasattr(default_val, '__len__') and not isinstance(default_val, str):
                        safe_default = [float(v) for v in default_val]
                    else:
                        # Single value (float, int, bool)
                        safe_default = float(default_val) if isinstance(default_val, (int, float)) else default_val
                except (TypeError, ValueError):
                    safe_default = None
            
            input_data = {
                'name': input_socket.name,
                'type': input_socket.type,
                'default_value': safe_default
            }
            node_data['inputs'].append(input_data)
    except Exception as e:
        print(f"Warning: Failed to export input sockets for node {node.name}: {e}")


def _export_output_sockets(node, node_data):
    """Export output sockets"""
    try:
        for output_socket in node.outputs:
            output_data = {
                'name': output_socket.name,
                'type': output_socket.type
            }
            node_data['outputs'].append(output_data)
    except Exception as e:
        print(f"Warning: Failed to export output sockets for node {node.name}: {e}")


def get_socket_default_value(socket):
    """
    Получает значение по умолчанию из сокета, конвертируя в JSON-совместимый формат.
    """
    try:
        default_val = getattr(socket, 'default_value', None)
        if default_val is None:
            return None
        
        # Конвертируем в список для векторов, цветов и т.д.
        if hasattr(default_val, '__len__') and not isinstance(default_val, str):
            return [float(v) for v in default_val]
        else:
            # Одиночное значение (float, int, bool)
            return float(default_val) if isinstance(default_val, (int, float)) else default_val
    except Exception:
        return None


# ========== IMPORT FUNCTIONS ==========

def load_mesh_from_commit(repo_path: Path, commit_hash: str, mesh_name: str) -> Tuple[Optional[Dict], Optional[Dict], Optional[Path]]:
    """
    Load mesh from commit with storage path for texture loading.
    
    Returns:
        Tuple of (mesh_json, material_json, mesh_storage_path) or (None, None, None) if not found
    """
    from forester.core.database import ForesterDB
    from forester.core.storage import ObjectStorage
    from forester.models.commit import Commit
    from forester.models.mesh import Mesh
    
    dfm_dir = repo_path / ".DFM"
    db_path = dfm_dir / "forester.db"
    db = ForesterDB(db_path)
    db.connect()
    
    try:
        storage = ObjectStorage(dfm_dir)
        commit = Commit.from_storage(commit_hash, db, storage)
        
        if not commit or commit.commit_type != "mesh_only":
            return None, None, None
        
        if not commit.mesh_hashes or not commit.selected_mesh_names:
            return None, None, None
        
        # Find mesh by name
        mesh_index = None
        for i, name in enumerate(commit.selected_mesh_names):
            if name == mesh_name:
                mesh_index = i
                break
        
        if mesh_index is None or mesh_index >= len(commit.mesh_hashes):
            return None, None, None
        
        mesh_hash = commit.mesh_hashes[mesh_index]
        mesh = Mesh.from_storage(mesh_hash, db, storage)
        
        if not mesh:
            return None, None, None
        
        # Get storage path for texture loading
        mesh_info = db.get_mesh(mesh_hash)
        mesh_storage_path = Path(mesh_info['path']) if mesh_info else None
        
        # Ensure material_json has updated node_data with texture info
        # This is needed because material.json might have been saved before node_data was updated
        if mesh_storage_path and mesh.material_json:
            material_json_path = mesh_storage_path / "material.json"
            if material_json_path.exists():
                # Reload material.json from disk to get latest version with updated node_data
                try:
                    with open(material_json_path, 'r', encoding='utf-8') as f:
                        updated_material_json = json.load(f)
                    # Use updated version if it has node_tree
                    if 'node_tree' in updated_material_json:
                        mesh.material_json = updated_material_json
                except Exception as e:
                    print(f"Warning: Could not reload material.json: {e}")
        
        return mesh.mesh_json, mesh.material_json, mesh_storage_path
    finally:
        db.close()


def import_mesh_to_blender(context, mesh_json, material_json, obj_name: str, mode: str = 'NEW', 
                          mesh_storage_path: Path = None):
    """
    Import mesh JSON data to Blender with texture loading.
    
    Args:
        context: Blender context
        mesh_json: Mesh JSON data
        material_json: Material JSON data
        obj_name: Object name
        mode: 'NEW' to create new object, 'SELECTED' to replace selected object
        mesh_storage_path: Path to mesh storage directory (for loading textures)
    """
    if mode == 'NEW':
        # Create new mesh and object
        mesh = bpy.data.meshes.new(obj_name)
        obj = bpy.data.objects.new(obj_name, mesh)
    else:
        # Replace selected object
        obj = context.active_object
        if not obj or obj.type != 'MESH':
            raise ValueError("No mesh object selected")
        mesh = obj.data
        # Clear existing geometry
        mesh.clear_geometry()
    
    # Import vertices
    if 'vertices' in mesh_json:
        vertices = [tuple(v) for v in mesh_json['vertices']]
        
        # Import faces - правильное создание полигонов
        faces = []
        if 'faces' in mesh_json:
            # Преобразуем индексы вершин в правильный формат для from_pydata
            faces = [tuple(f) for f in mesh_json['faces']]
        
        # Создаем меш из вершин и полигонов
        mesh.from_pydata(vertices, [], faces)
        
        # Обновляем нормали для корректного отображения
        mesh.update()
        
        # Создаем UV слой если есть UV данные
        if 'uv' in mesh_json and mesh_json['uv'] and len(mesh_json['uv']) > 0:
            # Создаем UV слой если его нет
            if not mesh.uv_layers:
                mesh.uv_layers.new(name="UVMap")
            
            uv_layer = mesh.uv_layers.active
            if uv_layer:
                # Убедимся что количество UV координат соответствует количеству вершин в полигонах
                for poly in mesh.polygons:
                    for loop_index in poly.loop_indices:
                        if loop_index < len(uv_layer.data) and loop_index < len(mesh_json['uv']):
                            uv_layer.data[loop_index].uv = tuple(mesh_json['uv'][loop_index])
    
    # Import materials with textures
    if material_json and 'name' in material_json:
        # Clear existing materials
        mesh.materials.clear()
        
        # Create or get material
        mat_name = material_json['name']
        if mat_name in bpy.data.materials:
            mat = bpy.data.materials[mat_name]
        else:
            mat = bpy.data.materials.new(name=mat_name)
        
        mat.use_nodes = material_json.get('use_nodes', True)
        
        # Restore basic properties
        if 'diffuse_color' in material_json:
            mat.diffuse_color = material_json['diffuse_color']
        if 'specular_color' in material_json:
            mat.specular_color = material_json['specular_color']
        if 'roughness' in material_json:
            mat.roughness = material_json['roughness']
        if 'metallic' in material_json:
            mat.metallic = material_json['metallic']
        
        # Restore node tree structure with textures loaded during node creation
        if mat.use_nodes and 'node_tree' in material_json and material_json['node_tree']:
            textures_info = material_json.get('textures', []) if 'textures' in material_json else None
            import_node_tree_structure(mat.node_tree, material_json['node_tree'], 
                                     textures_info=textures_info, 
                                     mesh_storage_path=mesh_storage_path)
        
        mesh.materials.append(mat)
    
    # Final mesh update
    mesh.update()
    
    if mode == 'NEW':
        # Link to scene
        context.collection.objects.link(obj)
        context.view_layer.objects.active = obj
        obj.select_set(True)
    
    return obj


def import_node_tree_structure(node_tree, node_tree_data, textures_info=None, mesh_storage_path=None):
    """
    Импортирует структуру node tree с загрузкой текстур.
    Основано на коде из difference_engine для полной совместимости.
    
    Args:
        node_tree: Blender node tree
        node_tree_data: Данные node tree из JSON
        textures_info: Список информации о текстурах (опционально)
        mesh_storage_path: Путь к директории меша для загрузки текстур (опционально)
    """
    # Check if node_tree is valid
    if not node_tree:
        print("Error: node_tree is None or invalid")
        return
    
    # Clear existing nodes (like in difference_engine)
    node_tree.nodes.clear()
    
    # Track created nodes for linking
    created_nodes = {}
    
    # Build texture lookup map by node name
    texture_map = {}
    if textures_info and mesh_storage_path:
        for tex_info in textures_info:
            node_name = tex_info.get('node_name')
            if node_name:
                texture_map[node_name] = tex_info
    
    # Get textures directory
    textures_dir = None
    if mesh_storage_path:
        textures_dir = mesh_storage_path / "textures"
    
    # Create nodes
    for node_data in node_tree_data.get('nodes', []):
        original_type = node_data.get('type', 'BSDF_PRINCIPLED')
        
        # Convert node type from internal format to class name
        if original_type.startswith('ShaderNode'):
            # Already in correct format
            node_type = original_type
        elif original_type in NODE_TYPE_MAP:
            # Use explicit mapping for special cases
            node_type = NODE_TYPE_MAP[original_type]
        else:
            # Convert using simple pattern: BSDF_PRINCIPLED -> ShaderNodeBsdfPrincipled
            # Special case for TEX_IMAGE
            if original_type == 'TEX_IMAGE':
                node_type = 'ShaderNodeTexImage'
            else:
                parts = original_type.split('_')
                formatted_name = ''.join(word.capitalize() for word in parts)
                node_type = f'ShaderNode{formatted_name}'
        
        try:
            node = node_tree.nodes.new(type=node_type)
        except Exception as e:
            print(f"Failed to create node type '{node_type}' (from '{original_type}'): {e}")
            continue
        
        # Set node properties safely
        if 'name' in node_data:
            node.name = node_data['name']
            
        if 'location' in node_data:
            loc = node_data['location']
            if isinstance(loc, (list, tuple)) and len(loc) >= 2:
                node.location = [float(loc[0]), float(loc[1])]  # Only use X, Y
                
        if 'width' in node_data:
            width = node_data['width']
            if isinstance(width, (int, float)):
                node.width = float(width)
        
        # Handle image texture nodes FIRST (before other properties that depend on image being loaded)
        if original_type == 'TEX_IMAGE':
            _import_image_texture(node, node_data, texture_map, textures_dir)
        
        # Restore node properties (AFTER image is loaded for TEX_IMAGE nodes)
        if 'properties' in node_data:
            _import_node_properties(node, node_data['properties'])
        
        # Set input default values
        if 'inputs' in node_data:
            for i, input_data in enumerate(node_data['inputs']):
                if i < len(node.inputs):
                    default_value = input_data.get('default_value')
                    if default_value is not None:
                        try:
                            if isinstance(default_value, list):
                                node.inputs[i].default_value = tuple(default_value)
                            else:
                                node.inputs[i].default_value = default_value
                        except (TypeError, AttributeError, ValueError) as e:
                            # Some sockets might not accept the value or wrong size
                            pass
        
        created_nodes[node_data.get('name', node.name)] = node
    
    # Create node links (connections between nodes)
    for link_data in node_tree_data.get('links', []):
        try:
            from_node = created_nodes.get(link_data['from_node'])
            to_node = created_nodes.get(link_data['to_node'])
            
            if from_node and to_node:
                from_socket = None
                to_socket = None
                
                # Find the output socket
                for output in from_node.outputs:
                    if output.name == link_data['from_socket']:
                        from_socket = output
                        break
                
                # Find the input socket
                for input_socket in to_node.inputs:
                    if input_socket.name == link_data['to_socket']:
                        to_socket = input_socket
                        break
                
                # Create the link
                if from_socket and to_socket:
                    node_tree.links.new(from_socket, to_socket)
        except Exception as e:
            print(f"Failed to create link: {e}")


def _import_image_texture(node, node_data, texture_map, textures_dir):
    """Import image texture node with multiple path resolution strategies"""
    if not textures_dir or not textures_dir.exists():
        return
    
    # Build candidate paths (like in difference_engine)
    candidate_paths = []
    node_name = node_data.get('name', node.name)
    texture_info = texture_map.get(node_name)
    
    # 1. Try copied_texture from node_data (primary method, like in difference_engine)
    if 'copied_texture' in node_data:
        copied_tex = node_data['copied_texture']
        # Handle both cases: just filename or path with "textures/"
        if copied_tex.startswith('textures/'):
            # Remove "textures/" prefix and use just filename
            copied_tex = copied_tex.replace('textures/', '', 1)
        candidate_paths.append(os.path.join(str(textures_dir), copied_tex))
    
    # 2. Try texture_info from texture_map (for backward compatibility)
    if texture_info:
        if texture_info.get('copied') and texture_info.get('commit_path'):
            commit_path = texture_info['commit_path']
            if commit_path.startswith('textures/'):
                commit_path = commit_path.replace('textures/', '', 1)
            candidate_paths.append(str(textures_dir / commit_path))
        if texture_info.get('original_path'):
            original_basename = os.path.basename(texture_info['original_path'])
            candidate_paths.append(str(textures_dir / original_basename))
    
    # 3. Try image_file from node_data (like in difference_engine)
    if 'image_file' in node_data:
        image_file = node_data['image_file']
        candidate_paths.append(os.path.join(str(textures_dir), os.path.basename(image_file)))
        candidate_paths.append(bpy.path.abspath(image_file))
    
    # 4. Try original path from texture_info (for backward compatibility)
    if texture_info and texture_info.get('original_path'):
        abs_path = bpy.path.abspath(texture_info['original_path'])
        candidate_paths.append(abs_path)
    
    # Resolve first existing path
    resolved_path = None
    for candidate in candidate_paths:
        if candidate and isinstance(candidate, str) and os.path.exists(candidate) and os.path.isfile(candidate):
            resolved_path = candidate
            break
    
    if not resolved_path:
        print(f"Warning: Texture not found for node '{node_name}'. Tried: {candidate_paths}")
    else:
        try:
            file_size_mb = os.path.getsize(resolved_path) / (1024 * 1024)
            if file_size_mb > 50:
                print(f"Warning: Loading large texture: {os.path.basename(resolved_path)} ({file_size_mb:.1f} MB)")
            
            # Reuse cached image by filename when possible (like in difference_engine)
            cached_name = os.path.basename(resolved_path)
            image = bpy.data.images.get(cached_name)
            if image:
                print(f"Reusing cached texture: {cached_name}")
                image.filepath = resolved_path
                # Force reload to ensure up-to-date display
                image.reload()
            else:
                image = bpy.data.images.load(resolved_path)
                print(f"Loaded new texture from {resolved_path}")
            
            # Assign image to node
            if hasattr(node, 'image'):
                node.image = image
                print(f"Assigned texture {cached_name} to node {node.name}")
            else:
                print(f"Error: Node {node.name} doesn't have 'image' attribute!")
        except Exception as e:
            print(f"Failed to load texture {resolved_path}: {e}")
            import traceback
            traceback.print_exc()


def _import_node_properties(node, props):
    """Import node properties including ColorRamp, Curve, Node Groups"""
    # Common properties
    if 'operation' in props and hasattr(node, 'operation'):
        node.operation = props['operation']
    if 'blend_type' in props and hasattr(node, 'blend_type'):
        node.blend_type = props['blend_type']
    if 'interpolation' in props and hasattr(node, 'interpolation'):
        try:
            node.interpolation = props['interpolation']
        except Exception as e:
            print(f"Warning: Failed to set interpolation: {e}")
    if 'extension' in props and hasattr(node, 'extension'):
        try:
            node.extension = props['extension']
        except Exception as e:
            print(f"Warning: Failed to set extension: {e}")
    if 'color_space' in props and hasattr(node, 'color_space'):
        try:
            node.color_space = props['color_space']
        except Exception as e:
            print(f"Warning: Failed to set color_space: {e}")
    if 'label' in props:
        node.label = props['label']
    if 'hide' in props:
        node.hide = props['hide']
    if 'mute' in props:
        node.mute = props['mute']
    
    # Node Group restoration
    if 'node_tree_name' in props and hasattr(node, 'node_tree'):
        node_tree_name = props['node_tree_name']
        # Try to find the node group in the blend file
        if node_tree_name in bpy.data.node_groups:
            node.node_tree = bpy.data.node_groups[node_tree_name]
            print(f"Restored Group node reference: {node_tree_name}")
        else:
            print(f"Warning: Node group '{node_tree_name}' not found in blend file - Group node will be empty")
    
    # ColorRamp restoration
    if 'color_ramp' in props and hasattr(node, 'color_ramp'):
        ramp_data = props['color_ramp']
        ramp = node.color_ramp
        
        # Set ramp properties
        if 'color_mode' in ramp_data:
            ramp.color_mode = ramp_data['color_mode']
        if 'interpolation' in ramp_data:
            ramp.interpolation = ramp_data['interpolation']
        
        # Restore color stops
        if 'elements' in ramp_data:
            # Clear existing elements (keep at least 2)
            while len(ramp.elements) > 2:
                ramp.elements.remove(ramp.elements[0])
            
            # Add new elements
            elements_data = ramp_data['elements']
            for i, elem_data in enumerate(elements_data):
                if i < len(ramp.elements):
                    # Update existing
                    elem = ramp.elements[i]
                else:
                    # Create new
                    elem = ramp.elements.new(elem_data['position'])
                
                elem.position = elem_data['position']
                if 'color' in elem_data:
                    elem.color = elem_data['color']
    
    # Curve restoration (Float, RGB, Vector)
    if 'mapping' in props and hasattr(node, 'mapping'):
        curves_data = props['mapping']
        mapping = node.mapping
        
        if 'use_clip' in curves_data and hasattr(mapping, 'use_clip'):
            mapping.use_clip = curves_data['use_clip']
        
        if 'curves' in curves_data:
            for curve_idx, curve_points in enumerate(curves_data['curves']):
                if curve_idx < len(mapping.curves):
                    curve = mapping.curves[curve_idx]
                    
                    # Clear existing points
                    while len(curve.points) > 0:
                        curve.points.remove(curve.points[0])
                    
                    # Add points
                    for point_data in curve_points:
                        point = curve.points.new(point_data['location'][0], 
                                                point_data['location'][1])
                        if 'handle_type' in point_data:
                            point.handle_type = point_data['handle_type']
            
            # Update the mapping
            mapping.update()


def load_textures_to_material(material, textures_info, mesh_storage_path):
    """
    Загружает текстуры в материал.
    
    Args:
        material: Blender material
        textures_info: Список информации о текстурах из material_json
        mesh_storage_path: Путь к директории меша (где хранятся текстуры)
    """
    if not material.node_tree:
        print("Material has no node tree")
        return
    
    print(f"Loading textures for material: {material.name}")
    print(f"Mesh storage path: {mesh_storage_path}")
    print(f"Textures info count: {len(textures_info)}")
    
    # Debug: print all nodes in material
    print(f"Nodes in material: {[n.name + ' (' + n.type + ')' for n in material.node_tree.nodes]}")
    
    for texture_info in textures_info:
        node_name = texture_info.get('node_name')
        if not node_name:
            print(f"Skipping texture: no node_name")
            continue
        
        print(f"Looking for texture node: {node_name}")
        
        # Находим узел текстуры в node tree
        texture_node = None
        for node in material.node_tree.nodes:
            if node.name == node_name and node.type == 'TEX_IMAGE':
                texture_node = node
                print(f"Found texture node: {node.name}")
                break
        
        if not texture_node:
            print(f"Warning: Texture node '{node_name}' not found in material node tree")
            continue
        
        # Определяем путь к текстуре
        texture_path = None
        if texture_info.get('copied') and texture_info.get('commit_path'):
            # Текстура скопирована в коммит
            texture_path = mesh_storage_path / texture_info['commit_path']
            print(f"Using copied texture path: {texture_path}")
        elif texture_info.get('original_path'):
            # Используем оригинальный путь
            texture_path = Path(bpy.path.abspath(texture_info['original_path']))
            print(f"Using original texture path: {texture_path}")
        
        # Загружаем текстуру
        if texture_path and texture_path.exists() and texture_path.is_file():
            # Проверяем, не загружена ли уже эта текстура
            image_name = texture_info.get('image_name', texture_path.name)
            image = bpy.data.images.get(image_name)
            
            if not image:
                try:
                    print(f"Loading texture: {texture_path}")
                    image = bpy.data.images.load(str(texture_path))
                    image.name = image_name
                    print(f"Texture loaded: {image.name}")
                except Exception as e:
                    print(f"Failed to load texture {texture_path}: {e}")
                    import traceback
                    traceback.print_exc()
                    continue
            else:
                # Обновляем путь если изменился
                if image.filepath != str(texture_path):
                    image.filepath = str(texture_path)
                    image.reload()
                print(f"Using existing texture: {image.name}")
            
            # Назначаем текстуру узлу
            if hasattr(texture_node, 'image'):
                texture_node.image = image
                print(f"Assigned texture {image.name} to node {texture_node.name}")
            else:
                print(f"Error: Texture node {texture_node.name} has no 'image' attribute")
        else:
            if texture_path:
                print(f"Warning: Texture path does not exist: {texture_path}")
            else:
                print(f"Warning: No texture path found for node {node_name}")

