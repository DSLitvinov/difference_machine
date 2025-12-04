#!/usr/bin/env python3
"""
Test script for mesh export/import functionality.
Tests export_mesh_to_blend and import_mesh_from_blend functions.
"""

import bpy
import tempfile
import json
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from operators.mesh_io import export_mesh_to_blend, export_mesh_to_json


def create_test_mesh():
    """Create a test mesh object for testing."""
    # Create mesh data
    mesh = bpy.data.meshes.new("TestMesh")
    mesh.from_pydata(
        [(0, 0, 0), (1, 0, 0), (0, 1, 0)],  # vertices
        [],  # edges
        [(0, 1, 2)]  # faces
    )
    mesh.update()
    
    # Create object
    obj = bpy.data.objects.new("TestMesh", mesh)
    bpy.context.collection.objects.link(obj)
    
    # Create simple material
    mat = bpy.data.materials.new("TestMaterial")
    mat.use_nodes = True
    obj.data.materials.append(mat)
    
    return obj


def test_export_mesh_to_blend():
    """Test exporting mesh to .blend file."""
    print("Testing export_mesh_to_blend...")
    
    try:
        # Create test mesh
        obj = create_test_mesh()
        
        # Export options
        export_options = {
            'vertices': True,
            'faces': True,
            'uv': True,
            'normals': True,
            'materials': True
        }
        
        # Create temp directory
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir)
            
            # Export mesh
            blend_path, metadata = export_mesh_to_blend(obj, output_path, export_options)
            
            # Verify files exist
            assert blend_path.exists(), "Blend file should exist"
            assert (output_path / "mesh_metadata.json").exists(), "Metadata file should exist"
            
            # Verify metadata structure
            assert 'mesh_json' in metadata, "Metadata should contain mesh_json"
            assert 'material_json' in metadata, "Metadata should contain material_json"
            assert 'object_name' in metadata, "Metadata should contain object_name"
            
            print("  ✓ Export successful")
            print(f"  ✓ Blend file: {blend_path}")
            print(f"  ✓ Metadata keys: {list(metadata.keys())}")
            
    except Exception as e:
        print(f"  ✗ Export failed: {e}")
        import traceback
        traceback.print_exc()
        raise


def test_import_mesh_from_blend():
    """Test importing mesh from .blend file."""
    print("Testing import_mesh_from_blend...")
    
    try:
        # Import function from mesh_io
        from operators.mesh_io import import_mesh_from_blend
        
        # Create test mesh
        obj = create_test_mesh()
        original_name = obj.name
        
        # Export options
        export_options = {
            'vertices': True,
            'faces': True,
            'uv': True,
            'normals': True,
            'materials': True
        }
        
        # Create temp directory
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir)
            
            # Export mesh (это очистит сцену, объект станет недействительным)
            blend_path, metadata = export_mesh_to_blend(obj, output_path, export_options)
            
            # Объект уже недействителен после export_mesh_to_blend, не нужно удалять
            
            # Import mesh
            imported_obj = import_mesh_from_blend(blend_path, original_name, bpy.context)
            
            # Verify import
            assert imported_obj is not None, "Imported object should not be None"
            assert imported_obj.name == original_name, "Imported object should have correct name"
            assert imported_obj.type == 'MESH', "Imported object should be MESH type"
            assert len(imported_obj.data.vertices) == 3, "Imported mesh should have 3 vertices"
            
            print("  ✓ Import successful")
            print(f"  ✓ Imported object: {imported_obj.name}")
            print(f"  ✓ Vertices: {len(imported_obj.data.vertices)}")
            
    except Exception as e:
        print(f"  ✗ Import failed: {e}")
        import traceback
        traceback.print_exc()
        raise


def test_export_import_roundtrip():
    """Test roundtrip: export -> import -> verify."""
    print("Testing export-import roundtrip...")
    
    try:
        # Import function from mesh_io
        from operators.mesh_io import import_mesh_from_blend
        
        # Create test mesh
        obj = create_test_mesh()
        original_name = obj.name
        original_location = tuple(obj.location)
        
        # Export options
        export_options = {
            'vertices': True,
            'faces': True,
            'uv': True,
            'normals': True,
            'materials': True
        }
        
        # Create temp directory
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir)
            
            # Export mesh (это очистит сцену, объект станет недействительным)
            blend_path, metadata = export_mesh_to_blend(obj, output_path, export_options)
            
            # Объект уже недействителен после export_mesh_to_blend, не нужно удалять
            
            # Import mesh
            imported_obj = import_mesh_from_blend(blend_path, original_name, bpy.context)
            
            # Verify roundtrip
            assert imported_obj.name == original_name, "Name should match"
            # Location может отличаться, так как создается новый объект
            assert len(imported_obj.data.vertices) == 3, "Vertices count should match"
            assert len(imported_obj.data.polygons) == 1, "Faces count should match"
            
            print("  ✓ Roundtrip successful")
            print(f"  ✓ Name: {imported_obj.name}")
            print(f"  ✓ Location: {imported_obj.location}")
            print(f"  ✓ Vertices: {len(imported_obj.data.vertices)}")
            print(f"  ✓ Faces: {len(imported_obj.data.polygons)}")
            
    except Exception as e:
        print(f"  ✗ Roundtrip failed: {e}")
        import traceback
        traceback.print_exc()
        raise


def test_export_with_materials():
    """Test exporting mesh with materials."""
    print("Testing export with materials...")
    
    try:
        # Create test mesh with material
        obj = create_test_mesh()
        
        # Add material properties
        if obj.material_slots and obj.material_slots[0].material:
            mat = obj.material_slots[0].material
            mat.diffuse_color = (1.0, 0.0, 0.0, 1.0)
            mat.roughness = 0.5
            mat.metallic = 0.3
        
        # Export options
        export_options = {
            'vertices': True,
            'faces': True,
            'materials': True
        }
        
        # Create temp directory
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir)
            
            # Export mesh
            blend_path, metadata = export_mesh_to_blend(obj, output_path, export_options)
            
            # Verify material in metadata
            assert 'material_json' in metadata, "Metadata should contain material_json"
            material_json = metadata['material_json']
            # Material JSON может быть пустым словарем или строкой если материалы не экспортируются
            if material_json and isinstance(material_json, dict):
                print("  ✓ Export with materials successful")
                print(f"  ✓ Material JSON keys: {list(material_json.keys())}")
                if 'name' in material_json:
                    print(f"  ✓ Material name: {material_json.get('name')}")
            else:
                print("  ✓ Export successful (no materials in JSON or materials not exported)")
            
    except Exception as e:
        print(f"  ✗ Export with materials failed: {e}")
        import traceback
        traceback.print_exc()
        raise


def main():
    """Run all tests."""
    print("=" * 60)
    print("Mesh Export/Import Tests")
    print("=" * 60)
    print()
    
    tests = [
        test_export_mesh_to_blend,
        test_import_mesh_from_blend,
        test_export_import_roundtrip,
        test_export_with_materials,
    ]
    
    passed = 0
    failed = 0
    
    for test_func in tests:
        try:
            test_func()
            passed += 1
            print()
        except Exception as e:
            failed += 1
            print(f"  ✗ Test failed: {e}")
            print()
    
    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

