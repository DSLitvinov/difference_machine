"""
Tests for viewport screenshot capture functionality.
"""

import unittest
import bpy
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.viewport_capture import capture_viewport_screenshot


class TestViewportCapture(unittest.TestCase):
    """Test viewport screenshot capture."""
    
    def test_capture_viewport_screenshot_exists(self):
        """Test that capture_viewport_screenshot function exists."""
        self.assertTrue(callable(capture_viewport_screenshot))
    
    def test_capture_viewport_screenshot_returns_bytes_or_none(self):
        """Test that capture_viewport_screenshot returns bytes or None."""
        if not bpy.data.filepath:
            self.skipTest("Blender file must be saved to test screenshot capture")
        
        # Get context
        context = bpy.context
        
        # Try to capture screenshot
        result = capture_viewport_screenshot(context)
        
        # Should return bytes or None
        self.assertIsInstance(result, (bytes, type(None)))
        
        if result is not None:
            # If screenshot captured, should be PNG data (starts with PNG signature)
            self.assertGreater(len(result), 8, "Screenshot data should be at least 8 bytes")
            self.assertEqual(result[:8], b'\x89PNG\r\n\x1a\n', "Screenshot should be PNG format")
            print(f"✓ Screenshot captured successfully: {len(result)} bytes")
        else:
            print("⚠ Screenshot capture returned None (may be expected if no viewport)")
    
    def test_capture_viewport_screenshot_has_3d_viewport(self):
        """Test that 3D viewport exists for screenshot."""
        context = bpy.context
        
        # Check if VIEW_3D area exists
        has_viewport = any(area.type == 'VIEW_3D' for area in context.screen.areas)
        
        if not has_viewport:
            self.skipTest("No 3D viewport found in current screen layout")
        
        # If viewport exists, capture should work (or return None if other error)
        result = capture_viewport_screenshot(context)
        self.assertIsInstance(result, (bytes, type(None)))
        
        if result is not None:
            # Verify PNG format
            self.assertGreater(len(result), 8)
            self.assertEqual(result[:8], b'\x89PNG\r\n\x1a\n')


if __name__ == '__main__':
    unittest.main()

