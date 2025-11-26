import bpy
from bpy.types import AddonPreferences
from bpy.props import StringProperty, IntProperty


class DifferenceMachinePreferences(AddonPreferences):
    bl_idname = __package__

    default_author: StringProperty(
        name="Default Author",
        description="Default author name for commits",
        default="Unknown",
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
        box.prop(self, "auto_compress_keep_last_n")


def register():
    bpy.utils.register_class(DifferenceMachinePreferences)


def unregister():
    bpy.utils.unregister_class(DifferenceMachinePreferences)

