"""
Operators for commit history operations.
"""

import bpy
from bpy.types import Operator
from bpy.props import StringProperty, IntProperty
import sys
from pathlib import Path

# Add forester to path
addon_dir = Path(__file__).parent.parent
if str(addon_dir) not in sys.path:
    sys.path.insert(0, str(addon_dir))

from forester.commands import (
    find_repository,
    checkout_commit,
    get_branch_commits,
    delete_commit,
)
from forester.core.database import ForesterDB
from forester.core.storage import ObjectStorage
from forester.models.commit import Commit
from forester.models.mesh import Mesh
import json


class DF_OT_select_commit(Operator):
    """Select a commit in the history list."""
    bl_idname = "df.select_commit"
    bl_label = "Select Commit"
    bl_description = "Select a commit"
    bl_options = {'REGISTER'}

    commit_index: IntProperty(name="Commit Index")

    def execute(self, context):
        """Execute the operator."""
        commits = context.scene.df_commits
        
        if 0 <= self.commit_index < len(commits):
            # Toggle selection
            commits[self.commit_index].is_selected = not commits[self.commit_index].is_selected
            
            # Deselect others
            for i, commit in enumerate(commits):
                if i != self.commit_index:
                    commit.is_selected = False
            
            context.scene.df_commit_props.selected_commit_index = self.commit_index if commits[self.commit_index].is_selected else -1
        
        return {'FINISHED'}


class DF_OT_checkout_commit(Operator):
    """Checkout a specific commit."""
    bl_idname = "df.checkout_commit"
    bl_label = "Checkout Commit"
    bl_description = "Checkout this commit (will discard uncommitted changes)"
    bl_options = {'REGISTER'}

    commit_hash: StringProperty(name="Commit Hash")

    def invoke(self, context, event):
        """Invoke with confirmation dialog."""
        return context.window_manager.invoke_confirm(self, event)

    def execute(self, context):
        """Execute the operator."""
        # Find repository
        blend_file = Path(bpy.data.filepath)
        if not blend_file:
            self.report({'ERROR'}, "Please save the Blender file first")
            return {'CANCELLED'}
        
        repo_path = find_repository(blend_file.parent)
        if not repo_path:
            self.report({'ERROR'}, "Not a Forester repository")
            return {'CANCELLED'}
        
        # Checkout commit
        try:
            success, error = checkout_commit(repo_path, self.commit_hash, force=True)
            
            if success:
                self.report({'INFO'}, f"Checked out commit: {self.commit_hash[:16]}...")
                # Refresh history
                bpy.ops.df.refresh_history()
                return {'FINISHED'}
            else:
                self.report({'ERROR'}, f"Failed to checkout: {error}")
                return {'CANCELLED'}
        except Exception as e:
            self.report({'ERROR'}, f"Failed to checkout commit: {str(e)}")
            import traceback
            traceback.print_exc()
            return {'CANCELLED'}


class DF_OT_delete_commit(Operator):
    """Delete a commit."""
    bl_idname = "df.delete_commit"
    bl_label = "Delete Commit"
    bl_description = "Delete this commit"
    bl_options = {'REGISTER'}

    commit_hash: StringProperty(name="Commit Hash")

    def invoke(self, context, event):
        """Invoke with confirmation dialog."""
        return context.window_manager.invoke_confirm(self, event)

    def execute(self, context):
        """Execute the operator."""
        # Find repository
        blend_file = Path(bpy.data.filepath)
        if not blend_file:
            self.report({'ERROR'}, "Please save the Blender file first")
            return {'CANCELLED'}
        
        repo_path = find_repository(blend_file.parent)
        if not repo_path:
            self.report({'ERROR'}, "Not a Forester repository")
            return {'CANCELLED'}
        
        # Delete commit
        try:
            success, error = delete_commit(repo_path, self.commit_hash, force=True)
            
            if success:
                self.report({'INFO'}, f"Deleted commit: {self.commit_hash[:16]}...")
                # Refresh history
                bpy.ops.df.refresh_history()
                return {'FINISHED'}
            else:
                self.report({'ERROR'}, f"Failed to delete commit: {error}")
                return {'CANCELLED'}
        except Exception as e:
            self.report({'ERROR'}, f"Failed to delete commit: {str(e)}")
            import traceback
            traceback.print_exc()
            return {'CANCELLED'}


def load_mesh_from_commit(repo_path: Path, commit_hash: str, mesh_name: str) -> tuple:
    """
    Load mesh from commit with storage path for texture loading.
    
    Returns:
        Tuple of (mesh_json, material_json, mesh_storage_path) or (None, None, None) if not found
    """
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
    
    Args:
        node_tree: Blender node tree
        node_tree_data: Данные node tree из JSON
        textures_info: Список информации о текстурах (опционально)
        mesh_storage_path: Путь к директории меша для загрузки текстур (опционально)
    """
    import os
    import bpy
    
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
        node_type = original_type
        
        # Convert node type to Blender format
        if not node_type.startswith('ShaderNode'):
            # Special case for TEX_IMAGE
            if node_type == 'TEX_IMAGE':
                node_type = 'ShaderNodeTexImage'
            else:
                # Convert: BSDF_PRINCIPLED -> ShaderNodeBsdfPrincipled
                parts = node_type.split('_')
                formatted_name = ''.join(word.capitalize() for word in parts)
                node_type = f'ShaderNode{formatted_name}'
        
        try:
            node = node_tree.nodes.new(type=node_type)
            node.name = node_data.get('name', node.name)
            
            # Set location
            if 'location' in node_data:
                loc = node_data['location']
                if len(loc) >= 2:
                    node.location = (float(loc[0]), float(loc[1]))
            
            # Handle image texture nodes FIRST (before other properties)
            # Like in difference_engine: read texture data from node_data directly
            if original_type == 'TEX_IMAGE' and textures_dir and textures_dir.exists():
                # Build candidate paths (like in difference_engine)
                candidate_paths = []
                
                # 1. Try copied_texture from node_data (primary method, like in difference_engine)
                if 'copied_texture' in node_data:
                    copied_tex = node_data['copied_texture']
                    # Handle both cases: just filename or path with "textures/"
                    if copied_tex.startswith('textures/'):
                        # Remove "textures/" prefix and use just filename
                        copied_tex = copied_tex.replace('textures/', '', 1)
                    candidate_paths.append(os.path.join(str(textures_dir), copied_tex))
                
                # 2. Try texture_info from texture_map (for backward compatibility)
                node_name = node_data.get('name', node.name)
                texture_info = texture_map.get(node_name)
                if texture_info:
                    if texture_info.get('copied') and texture_info.get('commit_path'):
                        candidate_paths.append(str(textures_dir / texture_info['commit_path']))
                    if texture_info.get('original_path'):
                        original_basename = os.path.basename(texture_info['original_path'])
                        candidate_paths.append(str(textures_dir / original_basename))
                
                # 3. Try image_file from node_data (like in difference_engine)
                if 'image_file' in node_data:
                    candidate_paths.append(os.path.join(str(textures_dir), os.path.basename(node_data['image_file'])))
                    candidate_paths.append(bpy.path.abspath(node_data['image_file']))
                
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
                            # Force reload to ensure up-to-date display (like in difference_engine)
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
            
            # Set properties (AFTER image is loaded for TEX_IMAGE nodes)
            if 'properties' in node_data:
                props = node_data['properties']
                if 'operation' in props and hasattr(node, 'operation'):
                    node.operation = props['operation']
                if 'blend_type' in props and hasattr(node, 'blend_type'):
                    node.blend_type = props['blend_type']
                if 'interpolation' in props and hasattr(node, 'interpolation'):
                    node.interpolation = props['interpolation']
                if 'extension' in props and hasattr(node, 'extension'):
                    node.extension = props['extension']
                if 'color_space' in props and hasattr(node, 'color_space'):
                    node.color_space = props['color_space']
            
            # Set input default values (skip for TEX_IMAGE as it doesn't have standard inputs)
            if original_type != 'TEX_IMAGE' and 'inputs' in node_data:
                for i, input_data in enumerate(node_data['inputs']):
                    if i < len(node.inputs):
                        default_value = input_data.get('default_value')
                        if default_value is not None:
                            try:
                                if isinstance(default_value, list):
                                    node.inputs[i].default_value = tuple(default_value)
                                else:
                                    node.inputs[i].default_value = default_value
                            except (TypeError, AttributeError, ValueError):
                                pass  # Skip if can't set value
            
            created_nodes[node_data.get('name', node.name)] = node
        except Exception as e:
            print(f"Failed to create node {node_type} (original: {original_type}): {e}")
            import traceback
            traceback.print_exc()
            continue
    
    # Create links
    for link_data in node_tree_data.get('links', []):
        try:
            from_node = created_nodes.get(link_data['from_node'])
            to_node = created_nodes.get(link_data['to_node'])
            
            if from_node and to_node:
                from_socket = None
                to_socket = None
                
                # Find sockets
                for output in from_node.outputs:
                    if output.name == link_data['from_socket']:
                        from_socket = output
                        break
                
                for input_socket in to_node.inputs:
                    if input_socket.name == link_data['to_socket']:
                        to_socket = input_socket
                        break
                
                if from_socket and to_socket:
                    node_tree.links.new(from_socket, to_socket)
        except Exception as e:
            print(f"Failed to create link: {e}")


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
            import bpy
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


class DF_OT_load_mesh_version(Operator):
    """Load mesh version from commit."""
    bl_idname = "df.load_mesh_version"
    bl_label = "Load Mesh Version"
    bl_description = "Load mesh version from commit"
    bl_options = {'REGISTER', 'UNDO'}

    commit_hash: StringProperty(name="Commit Hash")
    mesh_name: StringProperty(name="Mesh Name")

    def execute(self, context):
        """Execute the operator."""
        # Find repository
        blend_file = Path(bpy.data.filepath)
        if not blend_file:
            self.report({'ERROR'}, "Please save the Blender file first")
            return {'CANCELLED'}
        
        repo_path = find_repository(blend_file.parent)
        if not repo_path:
            self.report({'ERROR'}, "Not a Forester repository")
            return {'CANCELLED'}
        
        # Load mesh from commit
        try:
            mesh_json, material_json, mesh_storage_path = load_mesh_from_commit(repo_path, self.commit_hash, self.mesh_name)
            
            if not mesh_json:
                self.report({'ERROR'}, f"Mesh '{self.mesh_name}' not found in commit")
                return {'CANCELLED'}
            
            # Import to Blender (always create new object for Load)
            obj = import_mesh_to_blender(context, mesh_json, material_json, self.mesh_name, mode='NEW', 
                                      mesh_storage_path=mesh_storage_path)
            
            self.report({'INFO'}, f"Loaded mesh '{self.mesh_name}' from commit")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Failed to load mesh: {str(e)}")
            import traceback
            traceback.print_exc()
            return {'CANCELLED'}


class DF_OT_replace_mesh(Operator):
    """Replace current mesh with version from commit."""
    bl_idname = "df.replace_mesh"
    bl_label = "Replace Mesh"
    bl_description = "Replace current mesh with version from this commit"
    bl_options = {'REGISTER', 'UNDO'}

    commit_hash: StringProperty(name="Commit Hash")

    def invoke(self, context, event):
        """Invoke with confirmation dialog."""
        return context.window_manager.invoke_confirm(self, event)

    def execute(self, context):
        """Execute the operator."""
        active_obj = context.active_object
        if not active_obj or active_obj.type != 'MESH':
            self.report({'ERROR'}, "Please select a mesh object")
            return {'CANCELLED'}
        
        mesh_name = active_obj.name
        
        # Find repository
        blend_file = Path(bpy.data.filepath)
        if not blend_file:
            self.report({'ERROR'}, "Please save the Blender file first")
            return {'CANCELLED'}
        
        repo_path = find_repository(blend_file.parent)
        if not repo_path:
            self.report({'ERROR'}, "Not a Forester repository")
            return {'CANCELLED'}
        
        # Load mesh from commit
        try:
            mesh_json, material_json, mesh_storage_path = load_mesh_from_commit(repo_path, self.commit_hash, mesh_name)
            
            if not mesh_json:
                self.report({'ERROR'}, f"Mesh '{mesh_name}' not found in commit")
                return {'CANCELLED'}
            
            # Import to Blender (replace mode)
            import_mesh_to_blender(context, mesh_json, material_json, mesh_name, mode='SELECTED', 
                                 mesh_storage_path=mesh_storage_path)
            
            self.report({'INFO'}, f"Replaced mesh '{mesh_name}' with version from commit")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Failed to replace mesh: {str(e)}")
            import traceback
            traceback.print_exc()
            return {'CANCELLED'}


class DF_OT_compare_mesh(Operator):
    """Compare current mesh with version from commit."""
    bl_idname = "df.compare_mesh"
    bl_label = "Compare Mesh"
    bl_description = "Compare current mesh with version from this commit"
    bl_options = {'REGISTER', 'UNDO'}

    commit_hash: StringProperty(name="Commit Hash")
    offset_distance: bpy.props.FloatProperty(
        name="Offset Distance",
        description="Distance to offset the comparison version",
        default=2.0,
        min=0.0,
        max=10.0
    )

    def execute(self, context):
        """Execute the operator."""
        active_obj = context.active_object
        if not active_obj or active_obj.type != 'MESH':
            self.report({'ERROR'}, "Please select a mesh object")
            return {'CANCELLED'}
        
        mesh_name = active_obj.name
        original_obj = active_obj
        
        
        # Check if comparison is already active
        scene = context.scene
        comparison_obj_name = getattr(scene, 'df_comparison_object_name', None)
        if comparison_obj_name and comparison_obj_name in bpy.data.objects:
            # Toggle OFF: Remove comparison object
            comparison_obj = bpy.data.objects[comparison_obj_name]
            bpy.data.objects.remove(comparison_obj, do_unlink=True)
            scene.df_comparison_object_name = ""
            scene.df_comparison_active = False
            self.report({'INFO'}, "Comparison mode disabled")
            return {'FINISHED'}
        
        # Find repository
        blend_file = Path(bpy.data.filepath)
        if not blend_file:
            self.report({'ERROR'}, "Please save the Blender file first")
            return {'CANCELLED'}
        
        repo_path = find_repository(blend_file.parent)
        if not repo_path:
            self.report({'ERROR'}, "Not a Forester repository")
            return {'CANCELLED'}
        
        # Load mesh from commit
        try:
            mesh_json, material_json, mesh_storage_path = load_mesh_from_commit(repo_path, self.commit_hash, mesh_name)
            
            if not mesh_json:
                self.report({'ERROR'}, f"Mesh '{mesh_name}' not found in commit")
                return {'CANCELLED'}
            
            # Import to Blender (new object for comparison)
            comparison_obj = import_mesh_to_blender(
                context, mesh_json, material_json, 
                f"{mesh_name}_compare", mode='NEW',
                mesh_storage_path=mesh_storage_path
            )
            
            # Offset comparison object
            comparison_obj.location.x = original_obj.location.x + self.offset_distance
            comparison_obj.location.y = original_obj.location.y
            comparison_obj.location.z = original_obj.location.z
            
            # Store comparison state
            scene.df_comparison_object_name = comparison_obj.name
            scene.df_comparison_active = True
            scene.df_original_object_name = original_obj.name
            
            # Restore focus to original object
            for obj in context.selected_objects:
                obj.select_set(False)
            original_obj.select_set(True)
            context.view_layer.objects.active = original_obj
            
            self.report({'INFO'}, f"Comparison mode enabled (offset +{self.offset_distance})")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Failed to compare mesh: {str(e)}")
            import traceback
            traceback.print_exc()
            return {'CANCELLED'}

