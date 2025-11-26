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
                # Use proper pluralization
                commit_text = "commit" if item.commit_count == 1 else "commits"
                layout.label(text=f"{item.commit_count} {commit_text}")
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
            # Format: message + author + date time
            import datetime
            
            # Get date time
            try:
                date_str = datetime.datetime.fromtimestamp(item.timestamp).strftime('%Y-%m-%d %H:%M')
            except:
                date_str = "Unknown"
            
            # Format message (truncate if too long to fit in UI)
            message_text = item.message[:30] + "..." if len(item.message) > 30 else item.message
            
            # Build full text: message + author + date time
            # Format: "Message | Author | Date Time"
            full_text = f"{message_text} | {item.author} | {date_str}"
            
            # Commit type indicator
            if item.commit_type == "mesh_only":
                layout.label(text="", icon='MESH_DATA')
            else:
                layout.label(text="", icon='FILE_FOLDER')
            
            # Display full text
            layout.label(text=full_text, icon='FILE')
        
        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.label(text="", icon_value=icon)

