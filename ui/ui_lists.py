"""
UI Lists for Difference Machine add-on.
"""

import bpy
from bpy.types import UIList


class DF_UL_branch_list(UIList):
    """UIList for displaying branches."""
    bl_idname = "DF_UL_branch_list"
    
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        """Draw a single branch item."""
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            # Current branch indicator (play icon for current branch)
            if item.is_current:
                layout.label(text="", icon='PLAY')
                # Branch name (highlighted for current)
                layout.label(text=item.name)
            else:
                layout.label(text="", icon='BLANK1')
                layout.label(text=item.name)
            
            # Commit count
            if item.commit_count > 0:
                layout.label(text=f"{item.commit_count} co...")
            else:
                layout.label(text="0 commits")
            
            # Info icon
            layout.label(text="", icon='INFO')
            
            # Last commit message (truncated)
            if item.last_commit_message:
                msg = item.last_commit_message[:20] + "..." if len(item.last_commit_message) > 20 else item.last_commit_message
                layout.label(text=f"Last: {msg}")
            else:
                layout.label(text="Last: —")
        
        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.label(text="", icon_value=icon)


class DF_UL_commit_list(UIList):
    """UIList for displaying commits."""
    bl_idname = "DF_UL_commit_list"
    
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        """Draw a single commit item."""
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            # Commit type indicator
            if item.commit_type == "mesh_only":
                layout.label(text="", icon='MESH_DATA')
            else:
                layout.label(text="", icon='FILE_FOLDER')
            
            # Date and message
            import datetime
            try:
                date_str = datetime.datetime.fromtimestamp(item.timestamp).strftime('%Y-%m-%d %H:%M')
            except:
                date_str = "Unknown"
            
            layout.label(text=f"{date_str}  {item.message[:40]}", icon='FILE')
            
            # Author
            layout.label(text=item.author, icon='USER')
        
        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.label(text="", icon_value=icon)

