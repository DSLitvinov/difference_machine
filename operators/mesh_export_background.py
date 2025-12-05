"""
Background script for exporting meshes to .blend files.
Runs in separate Blender process to avoid affecting current scene.

This script is called via subprocess from mesh_io.py to export meshes
in the background without modifying the user's current project.
"""
import bpy
import sys
import argparse
from pathlib import Path


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Export mesh to .blend file in background')
    
    parser.add_argument('--empty_blend', required=True,
                       help='Path to empty.blend template file')
    parser.add_argument('--output_file', required=True,
                       help='Path to output .blend file')
    parser.add_argument('--mesh_name', required=True,
                       help='Name of mesh object to export')
    parser.add_argument('--library_file', required=True,
                       help='Path to temporary library file with mesh data')
    parser.add_argument('--obj_location', nargs=3, type=float, default=[0, 0, 0],
                       help='Object location (x, y, z)')
    parser.add_argument('--obj_rotation', nargs=3, type=float, default=[0, 0, 0],
                       help='Object rotation (x, y, z) in radians')
    parser.add_argument('--obj_scale', nargs=3, type=float, default=[1, 1, 1],
                       help='Object scale (x, y, z)')
    
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1:])


def export_mesh_to_blend(args):
    """
    Export mesh from library to empty.blend and save.
    
    Args:
        args: Parsed command line arguments
    """
    # Open empty.blend
    bpy.ops.wm.open_mainfile(filepath=args.empty_blend)
    
    # Load mesh from library
    with bpy.data.libraries.load(args.library_file, link=False) as (data_from, data_to):
        # Load meshes (use first available mesh, as library contains only one mesh)
        if data_from.meshes:
            data_to.meshes = data_from.meshes
        
        # Load materials
        if data_from.materials:
            data_to.materials = data_from.materials
        
        # Load node groups
        if data_from.node_groups:
            data_to.node_groups = data_from.node_groups
        
        # Load images
        if data_from.images:
            data_to.images = data_from.images
    
    # Create object from loaded mesh
    if data_to.meshes:
        mesh = data_to.meshes[0]
        obj = bpy.data.objects.new(args.mesh_name, mesh)
        
        # Set transform
        obj.location = tuple(args.obj_location)
        obj.rotation_euler = tuple(args.obj_rotation)
        obj.scale = tuple(args.obj_scale)
        
        # Apply materials
        if data_to.materials:
            for mat in data_to.materials:
                mesh.materials.append(mat)
        
        # Add to scene
        bpy.context.collection.objects.link(obj)
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)
    
    # Save file
    output_path = Path(args.output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(output_path), check_existing=False)


if __name__ == "__main__":
    try:
        args = parse_args()
        export_mesh_to_blend(args)
    except Exception as e:
        print(f"Error in background export: {e}", file=sys.stderr)
        sys.exit(1)

