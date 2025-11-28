import bpy
from bpy.types import AddonPreferences
from bpy.props import StringProperty, IntProperty, BoolProperty, EnumProperty
from pathlib import Path
import time


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
    
    # Garbage collection settings
    auto_garbage_collect: BoolProperty(
        name="Auto Garbage Collect",
        description="Automatically run garbage collection at specified intervals",
        default=False,
    )
    
    gc_interval_value: IntProperty(
        name="Interval",
        description="Interval value for automatic garbage collection",
        default=1,
        min=1,
        max=1000,
    )
    
    gc_interval_unit: EnumProperty(
        name="Unit",
        description="Time unit for garbage collection interval",
        items=[
            ('HOURS', "Hours", "Run garbage collection every N hours"),
            ('DAYS', "Days", "Run garbage collection every N days"),
            ('WEEKS', "Weeks", "Run garbage collection every N weeks"),
        ],
        default='DAYS',
    )
    
    gc_last_run: bpy.props.FloatProperty(
        name="Last Run",
        description="Timestamp of last garbage collection run",
        default=0.0,
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
        
        # Garbage collection settings
        box = layout.box()
        box.label(text="Garbage Collection", icon='BRUSH_DATA')
        
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
            # Manual garbage collect button
            row = box.row()
            row.scale_y = 1.5
            op = row.operator("df.garbage_collect", text="Garbage Collect Now", icon='BRUSH_DATA')
            op.dry_run = False
            
            # Dry run button
            row = box.row()
            row.scale_y = 1.2
            op = row.operator("df.garbage_collect", text="Dry Run (Preview)", icon='VIEWZOOM')
            op.dry_run = True
            
            box.separator()
            
            # Auto garbage collect settings
            box.prop(self, "auto_garbage_collect", text="Auto Garbage Collect")
            
            if self.auto_garbage_collect:
                row = box.row()
                row.prop(self, "gc_interval_value", text="Every")
                
                row = box.row()
                row.prop(self, "gc_interval_unit", expand=True)
                
                # Show last run time if available
                if self.gc_last_run > 0:
                    last_run_time = time.ctime(self.gc_last_run)
                    box.label(text=f"Last run: {last_run_time}", icon='TIME')
        else:
            box.label(text="Save Blender file to enable", icon='INFO')
            box.label(text="garbage collection tools")
        
        # Database maintenance
        box = layout.box()
        box.label(text="Database Maintenance", icon='TOOL_SETTINGS')
        
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

