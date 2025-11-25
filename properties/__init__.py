"""
Properties module for Difference Machine add-on.
Contains custom property definitions.
"""

from . import properties
from . import commit_item

__all__ = ["properties", "commit_item"]

def register():
    # Register item classes first, then properties
    commit_item.register()
    properties.register()

def unregister():
    # Unregister in reverse order
    properties.unregister()
    commit_item.unregister()

