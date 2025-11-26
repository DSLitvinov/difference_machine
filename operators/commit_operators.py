"""
Operators for commit operations in Difference Machine.
"""

import bpy
from bpy.types import Operator
from bpy.props import StringProperty
import sys
from pathlib import Path

# Add forester to path
# Get the addon directory (difference_machine)
addon_dir = Path(__file__).parent.parent
forester_path = addon_dir / "forester"
if str(forester_path) not in sys.path:
    sys.path.insert(0, str(addon_dir))

from forester.commands import (
    find_repository,
    init_repository,
    create_commit,
    create_mesh_only_commit,
    auto_compress_mesh_commits,
    create_branch,
)
from forester.core.refs import get_branch_ref
from forester.core.metadata import Metadata


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
                            import os
                            from pathlib import Path
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
                
                # Экспортируем полную структуру node tree (без текстур, только структура)
                material_json['node_tree'] = export_node_tree_structure(mat.node_tree)
    
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


def export_node_tree_structure(node_tree):
    """
    Экспортирует структуру node tree без текстур (только связи и параметры).
    """
    nodes_data = []
    links_data = []
    
    for node in node_tree.nodes:
        # Пропускаем TEX_IMAGE узлы - они обрабатываются отдельно
        if node.type == 'TEX_IMAGE':
            # Сохраняем только базовую информацию о узле
            node_data = {
                'name': node.name,
                'type': node.type,
                'location': [float(node.location.x), float(node.location.y)],
                'inputs': [],
                'properties': {}
            }
            # Для TEX_IMAGE сохраняем только свойства, не значения
            if hasattr(node, 'interpolation'):
                node_data['properties']['interpolation'] = node.interpolation
            if hasattr(node, 'extension'):
                node_data['properties']['extension'] = node.extension
            if hasattr(node, 'color_space'):
                node_data['properties']['color_space'] = node.color_space
            nodes_data.append(node_data)
            continue
        
        node_data = {
            'name': node.name,
            'type': node.type,
            'location': [float(node.location.x), float(node.location.y)],
            'inputs': [],
            'properties': {}
        }
        
        # Экспортируем входы
        for input_socket in node.inputs:
            input_data = {
                'name': input_socket.name,
                'type': input_socket.type,
                'default_value': get_socket_default_value(input_socket)
            }
            node_data['inputs'].append(input_data)
        
        # Экспортируем свойства
        if hasattr(node, 'operation'):
            node_data['properties']['operation'] = node.operation
        if hasattr(node, 'blend_type'):
            node_data['properties']['blend_type'] = node.blend_type
        if hasattr(node, 'label'):
            node_data['properties']['label'] = node.label
        if hasattr(node, 'hide'):
            node_data['properties']['hide'] = node.hide
        if hasattr(node, 'mute'):
            node_data['properties']['mute'] = node.mute
        
        nodes_data.append(node_data)
    
    # Экспортируем связи
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


class DF_OT_create_project_commit(Operator):
    """Create a full project commit."""
    bl_idname = "df.create_project_commit"
    bl_label = "Create Project Commit"
    bl_description = "Create a commit of the entire working directory"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        """Execute the operator."""
        # Find repository
        blend_file = Path(bpy.data.filepath)
        if not blend_file:
            self.report({'ERROR'}, "Please save the Blender file first")
            return {'CANCELLED'}
        
        # Determine project root (directory containing .blend file)
        project_root = blend_file.parent
        
        # Check if repository exists
        repo_path = find_repository(project_root)
        if not repo_path:
            # Initialize repository
            try:
                init_repository(project_root)
                repo_path = project_root
                self.report({'INFO'}, "Repository initialized")
            except Exception as e:
                self.report({'ERROR'}, f"Failed to initialize repository: {str(e)}")
                return {'CANCELLED'}
        
        props = context.scene.df_commit_props
        branch_name = props.branch or "main"
        
        # Ensure branch exists (create if needed)
        branch_ref = get_branch_ref(repo_path, branch_name)
        if branch_ref is None:
            # Branch doesn't exist, create it
            try:
                create_branch(repo_path, branch_name)
                # Update metadata to set current branch
                metadata_path = repo_path / ".DFM" / "metadata.json"
                if metadata_path.exists():
                    metadata = Metadata(metadata_path)
                    metadata.load()
                    metadata.current_branch = branch_name
                    metadata.save()
                self.report({'INFO'}, f"Branch '{branch_name}' created")
            except ValueError:
                # Branch might already exist (race condition), that's okay
                pass
        
        # Create commit
        try:
            commit_hash = create_commit(
                repo_path=repo_path,
                message=props.message or "No message",
                author=props.author if props.author else "Unknown"
            )
            
            if commit_hash:
                self.report({'INFO'}, f"Commit created: {commit_hash[:16]}...")
                return {'FINISHED'}
            else:
                self.report({'INFO'}, "No changes to commit")
                return {'CANCELLED'}
        except Exception as e:
            self.report({'ERROR'}, f"Failed to create commit: {str(e)}")
            import traceback
            traceback.print_exc()
            return {'CANCELLED'}


class DF_OT_create_mesh_commit(Operator):
    """Create a mesh-only commit from selected objects."""
    bl_idname = "df.create_mesh_commit"
    bl_label = "Create Mesh Commit"
    bl_description = "Create a commit only for selected mesh objects"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        """Execute the operator."""
        # Get selected mesh objects
        selected_objects = [obj for obj in context.selected_objects if obj.type == 'MESH']
        
        if not selected_objects:
            self.report({'ERROR'}, "No mesh objects selected")
            return {'CANCELLED'}
        
        # Find repository
        blend_file = Path(bpy.data.filepath)
        if not blend_file:
            self.report({'ERROR'}, "Please save the Blender file first")
            return {'CANCELLED'}
        
        # Determine project root
        project_root = blend_file.parent
        
        # Check if repository exists
        repo_path = find_repository(project_root)
        if not repo_path:
            # Initialize repository
            try:
                init_repository(project_root)
                repo_path = project_root
                self.report({'INFO'}, "Repository initialized")
            except Exception as e:
                self.report({'ERROR'}, f"Failed to initialize repository: {str(e)}")
                return {'CANCELLED'}
        
        props = context.scene.df_commit_props
        branch_name = props.branch or "main"
        export_options = props.get_export_options()
        
        # Ensure branch exists (create if needed)
        branch_ref = get_branch_ref(repo_path, branch_name)
        if branch_ref is None:
            # Branch doesn't exist, create it
            try:
                create_branch(repo_path, branch_name)
                # Update metadata to set current branch
                metadata_path = repo_path / ".DFM" / "metadata.json"
                if metadata_path.exists():
                    metadata = Metadata(metadata_path)
                    metadata.load()
                    metadata.current_branch = branch_name
                    metadata.save()
                self.report({'INFO'}, f"Branch '{branch_name}' created")
            except ValueError:
                # Branch might already exist (race condition), that's okay
                pass
        
        # Export meshes
        mesh_data_list = []
        for obj in selected_objects:
            try:
                mesh_data = export_mesh_to_json(obj, export_options)
                mesh_data['mesh_name'] = obj.name
                mesh_data_list.append(mesh_data)
            except Exception as e:
                self.report({'WARNING'}, f"Failed to export {obj.name}: {str(e)}")
                continue
        
        if not mesh_data_list:
            self.report({'ERROR'}, "No meshes could be exported")
            return {'CANCELLED'}
        
        # Create mesh-only commit
        try:
            commit_hash = create_mesh_only_commit(
                repo_path=repo_path,
                mesh_data_list=mesh_data_list,
                export_options=export_options,
                message=props.message or "No message",
                author=props.author if props.author else "Unknown",
                tag=props.tag if props.tag else None
            )
            
            if commit_hash:
                self.report({'INFO'}, f"Mesh commit created: {commit_hash[:16]}...")
                
                # Auto-compress if enabled
                if props.auto_compress:
                    mesh_names = [data['mesh_name'] for data in mesh_data_list]
                    deleted = auto_compress_mesh_commits(
                        repo_path=repo_path,
                        mesh_names=mesh_names,
                        keep_last_n=props.keep_last_n_commits
                    )
                    if deleted > 0:
                        self.report({'INFO'}, f"Compressed {deleted} old commits")
                
                return {'FINISHED'}
            else:
                self.report({'INFO'}, "No changes to commit")
                return {'CANCELLED'}
        except Exception as e:
            self.report({'ERROR'}, f"Failed to create commit: {str(e)}")
            import traceback
            traceback.print_exc()
            return {'CANCELLED'}


class DF_OT_refresh_history(Operator):
    """Refresh commit history."""
    bl_idname = "df.refresh_history"
    bl_label = "Refresh History"
    bl_description = "Refresh the commit history list"
    bl_options = {'REGISTER'}

    def execute(self, context):
        """Execute the operator."""
        # Find repository
        blend_file = Path(bpy.data.filepath)
        if not blend_file:
            self.report({'ERROR'}, "Please save the Blender file first")
            return {'CANCELLED'}
        
        repo_path = find_repository(blend_file.parent)
        if not repo_path:
            # Clear commits list
            context.scene.df_commits.clear()
            return {'FINISHED'}
        
        props = context.scene.df_commit_props
        branch_name = props.branch or "main"
        
        # Get commits from forester
        from forester.commands import get_branch_commits
        from forester.core.refs import get_current_branch
        
        try:
            commits_data = get_branch_commits(repo_path, branch_name)
            
            # Clear existing list
            context.scene.df_commits.clear()
            
            # Add commits to list (newest first)
            for commit_data in reversed(commits_data):
                commit_item = context.scene.df_commits.add()
                commit_item.hash = commit_data['hash']
                commit_item.message = commit_data.get('message', 'No message')
                commit_item.author = commit_data.get('author', 'Unknown')
                commit_item.timestamp = commit_data['timestamp']
                commit_item.commit_type = commit_data.get('commit_type', 'project')
                
                # Format selected mesh names
                selected_names = commit_data.get('selected_mesh_names', [])
                if isinstance(selected_names, str):
                    import json
                    try:
                        selected_names = json.loads(selected_names)
                    except:
                        selected_names = []
                if selected_names:
                    commit_item.selected_mesh_names = ", ".join(selected_names)
            
            self.report({'INFO'}, f"Loaded {len(commits_data)} commits")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Failed to load commits: {str(e)}")
            import traceback
            traceback.print_exc()
            return {'CANCELLED'}


class DF_OT_refresh_branches(Operator):
    """Refresh branch list."""
    bl_idname = "df.refresh_branches"
    bl_label = "Refresh Branches"
    bl_description = "Refresh the branch list"
    bl_options = {'REGISTER'}

    def execute(self, context):
        """Execute the operator."""
        # Find repository
        blend_file = Path(bpy.data.filepath)
        if not blend_file:
            self.report({'ERROR'}, "Please save the Blender file first")
            return {'CANCELLED'}
        
        repo_path = find_repository(blend_file.parent)
        if not repo_path:
            # Clear branches list
            context.scene.df_branches.clear()
            return {'FINISHED'}
        
        # Get branches from forester
        from forester.commands import list_branches
        from forester.core.refs import get_current_branch
        
        try:
            branches_data = list_branches(repo_path)
            current_branch = get_current_branch(repo_path)
            
            # Clear existing list
            context.scene.df_branches.clear()
            
            # Add branches to list
            for branch_data in branches_data:
                branch_item = context.scene.df_branches.add()
                branch_item.name = branch_data['name']
                branch_item.is_current = branch_data.get('current', False) or (branch_data['name'] == current_branch)
                
                # Get commit count and last commit
                from forester.commands import get_branch_commits
                commits = get_branch_commits(repo_path, branch_data['name'])
                branch_item.commit_count = len(commits)
                
                if commits:
                    last_commit = commits[-1]  # Last commit (newest)
                    branch_item.last_commit_hash = last_commit.get('hash', '')
                    branch_item.last_commit_message = last_commit.get('message', 'No message')
                else:
                    branch_item.last_commit_hash = ''
                    branch_item.last_commit_message = 'No commits'
            
            self.report({'INFO'}, f"Loaded {len(branches_data)} branches")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Failed to load branches: {str(e)}")
            import traceback
            traceback.print_exc()
            return {'CANCELLED'}


class DF_OT_create_branch(Operator):
    """Create a new branch."""
    bl_idname = "df.create_branch"
    bl_label = "Create Branch"
    bl_description = "Create a new branch"
    bl_options = {'REGISTER'}

    branch_name: StringProperty(
        name="Branch Name",
        description="Name of the new branch",
        default="",
    )

    def invoke(self, context, event):
        """Invoke the operator (show dialog)."""
        return context.window_manager.invoke_props_dialog(self)

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
        
        if not self.branch_name:
            self.report({'ERROR'}, "Branch name cannot be empty")
            return {'CANCELLED'}
        
        try:
            create_branch(repo_path, self.branch_name)
            self.report({'INFO'}, f"Branch '{self.branch_name}' created")
            # Refresh branches list
            bpy.ops.df.refresh_branches()
            return {'FINISHED'}
        except ValueError as e:
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}
        except Exception as e:
            self.report({'ERROR'}, f"Failed to create branch: {str(e)}")
            return {'CANCELLED'}


class DF_OT_switch_branch(Operator):
    """Switch to a different branch."""
    bl_idname = "df.switch_branch"
    bl_label = "Switch Branch"
    bl_description = "Switch to a different branch"
    bl_options = {'REGISTER'}

    branch_name: StringProperty(name="Branch Name", default="")

    def invoke(self, context, event):
        """Invoke the operator - use selected branch if no name provided."""
        # If branch_name not provided, use selected branch from list
        if not self.branch_name:
            branches = context.scene.df_branches
            if (branches and 
                hasattr(context.scene, 'df_branch_list_index') and
                context.scene.df_branch_list_index >= 0 and 
                context.scene.df_branch_list_index < len(branches)):
                self.branch_name = branches[context.scene.df_branch_list_index].name
            else:
                self.report({'ERROR'}, "No branch selected")
                return {'CANCELLED'}
        
        return self.execute(context)

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
        
        if not self.branch_name:
            self.report({'ERROR'}, "Branch name not specified")
            return {'CANCELLED'}
        
        try:
            from forester.commands import switch_branch
            switch_branch(repo_path, self.branch_name)
            
            # Update props
            context.scene.df_commit_props.branch = self.branch_name
            
            self.report({'INFO'}, f"Switched to branch '{self.branch_name}'")
            # Refresh branches and history
            bpy.ops.df.refresh_branches()
            bpy.ops.df.refresh_history()
            return {'FINISHED'}
        except ValueError as e:
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}
        except Exception as e:
            self.report({'ERROR'}, f"Failed to switch branch: {str(e)}")
            return {'CANCELLED'}


class DF_OT_delete_branch(Operator):
    """Delete a branch."""
    bl_idname = "df.delete_branch"
    bl_label = "Delete Branch"
    bl_description = "Delete a branch"
    bl_options = {'REGISTER'}

    branch_name: StringProperty(name="Branch Name")

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
        
        try:
            from forester.commands import delete_branch
            delete_branch(repo_path, self.branch_name, force=False)
            self.report({'INFO'}, f"Branch '{self.branch_name}' deleted")
            # Refresh branches list
            bpy.ops.df.refresh_branches()
            return {'FINISHED'}
        except ValueError as e:
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}
        except Exception as e:
            self.report({'ERROR'}, f"Failed to delete branch: {str(e)}")
            return {'CANCELLED'}

