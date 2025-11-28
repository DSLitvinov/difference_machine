import bpy
from bpy.types import AddonPreferences
from bpy.props import StringProperty, IntProperty, BoolProperty
from pathlib import Path


class DifferenceMachinePreferences(AddonPreferences):
    bl_idname = __package__

    default_author: StringProperty(
        name="Default Author",
        description="Default author name for commits",
        default="Unknown",
    )

    auto_compress: BoolProperty(
        name="Auto-compress Mesh-only Commits",
        description="Automatically delete old mesh-only commits when creating new ones",
        default=False,
    )

    auto_compress_keep_last_n: IntProperty(
        name="Keep Last N Commits",
        description="Number of commits to keep when auto-compressing old versions",
        default=5,
        min=1,
        max=100,
    )

    def draw(self, context):
        layout = self.layout

        # Основные настройки
        box = layout.box()
        box.label(text="Commit Settings", icon='SETTINGS')
        box.prop(self, "default_author")

        box = layout.box()
        box.label(text="Auto-compress Settings", icon='PACKAGE')
        box.prop(self, "auto_compress", text="Auto-compress Mesh-only Commits")
        box.prop(self, "auto_compress_keep_last_n")
        
        # Database maintenance
        box = layout.box()
        box.label(text="Database Maintenance", icon='TOOL_SETTINGS')
        
        # Check if repository exists
        blend_file = Path(bpy.data.filepath) if bpy.data.filepath else None
        repo_exists = False
        if blend_file:
            try:
                from .forester.commands.init import find_repository
                repo_path = find_repository(blend_file.parent)
                repo_exists = repo_path is not None
            except Exception:
                pass
        
        if repo_exists:
            row = box.row()
            row.scale_y = 1.5
            op = row.operator("df.rebuild_database", text="Rebuild Database", icon='FILE_REFRESH')
            box.label(text="Rebuild database from storage", icon='INFO')
            box.label(text="(Use if database is corrupted)")
        else:
            box.label(text="Save Blender file to enable", icon='INFO')
            box.label(text="database maintenance tools")


def register():
    bpy.utils.register_class(DifferenceMachinePreferences)


def unregister():
    bpy.utils.unregister_class(DifferenceMachinePreferences)

