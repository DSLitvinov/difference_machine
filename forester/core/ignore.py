"""
Ignore rules parser for Forester.
Handles .dfmignore file parsing and matching.
"""

import re
from pathlib import Path
from typing import List, Set


class IgnoreRules:
    """
    Parser and matcher for .dfmignore rules.
    """
    
    def __init__(self, ignore_file: Path):
        """
        Initialize ignore rules from file.
        
        Args:
            ignore_file: Path to .dfmignore file
        """
        self.ignore_file = ignore_file
        self.patterns: List[re.Pattern] = []
        self.load_rules()
    
    def load_rules(self) -> None:
        """Load rules from .dfmignore file."""
        if not self.ignore_file.exists():
            # Use default rules if file doesn't exist
            default_rules = self.get_default_rules()
            self._compile_patterns(default_rules)
            return
        
        rules: List[str] = []
        
        with open(self.ignore_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue
                rules.append(line)
        
        # Add default rules if file is empty
        if not rules:
            rules = self.get_default_rules()
        
        self._compile_patterns(rules)
    
    def _compile_patterns(self, rules: List[str]) -> None:
        """Compile ignore patterns to regex."""
        self.patterns = []
        
        for rule in rules:
            # Convert glob pattern to regex
            pattern = self._glob_to_regex(rule)
            try:
                compiled = re.compile(pattern)
                self.patterns.append(compiled)
            except re.error:
                # Skip invalid patterns
                continue
    
    def _glob_to_regex(self, pattern: str) -> str:
        """
        Convert glob pattern to regex.
        
        Supports:
        - * matches any sequence of characters
        - ** matches any sequence including path separators
        - ? matches single character
        - [abc] character class
        - Leading / means root-relative
        - Trailing / means directory only
        """
        # Escape special regex characters
        pattern = re.escape(pattern)
        
        # Replace escaped glob patterns
        pattern = pattern.replace(r'\*\*', r'.*')  # ** matches anything
        pattern = pattern.replace(r'\*', r'[^/]*')  # * matches non-slash chars
        pattern = pattern.replace(r'\?', r'.')  # ? matches any char
        pattern = pattern.replace(r'\[', r'[').replace(r'\]', r']')  # Character classes
        
        # Handle leading / (root-relative)
        if pattern.startswith(r'\/'):
            pattern = '^' + pattern[2:]
        else:
            pattern = r'.*' + pattern  # Match anywhere in path
        
        # Handle trailing / (directory only)
        if pattern.endswith(r'\/'):
            pattern = pattern[:-2] + r'/.*'
        
        return pattern
    
    def should_ignore(self, path: Path, base_path: Path) -> bool:
        """
        Check if path should be ignored.
        
        Args:
            path: Path to check (absolute or relative)
            base_path: Base path of repository (for relative matching)
            
        Returns:
            True if path should be ignored
        """
        # Normalize path
        if path.is_absolute():
            try:
                rel_path = path.relative_to(base_path)
            except ValueError:
                # Path is outside repository
                return True
        else:
            rel_path = path
        
        # Convert to string with forward slashes (for cross-platform compatibility)
        path_str = str(rel_path).replace('\\', '/')
        
        # Check against all patterns
        for pattern in self.patterns:
            if pattern.search(path_str) or pattern.match(path_str):
                return True
        
        return False
    
    @staticmethod
    def get_default_rules() -> List[str]:
        """
        Get default ignore rules.
        
        Returns:
            List of default ignore patterns
        """
        return [
            # Forester directory
            '.DFM/',
            
            # Working meshes directory (not tracked)
            'meshes/',
            
            # Blender backup files
            '*.blend1',
            '*.blend2',
            '*.blend3',
            
            # OS files
            '.DS_Store',
            'Thumbs.db',
            'desktop.ini',
            
            # Temporary files
            '*.tmp',
            '*.temp',
            '*.swp',
            '*.swo',
            '*~',
            
            # Python cache
            '__pycache__/',
            '*.pyc',
            '*.pyo',
            
            # Other CG software files
            '*.max',
            '*.ma',
            '*.mb',
            '*.3ds',
        ]
    
    def create_default_file(self) -> None:
        """Create .dfmignore file with default rules."""
        if self.ignore_file.exists():
            return
        
        default_rules = self.get_default_rules()
        
        with open(self.ignore_file, 'w', encoding='utf-8') as f:
            f.write("# Forester ignore rules\n")
            f.write("# Lines starting with # are comments\n\n")
            
            for rule in default_rules:
                f.write(f"{rule}\n")

