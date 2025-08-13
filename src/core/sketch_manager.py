"""
Sketch file management for DrawBot VSCode Sketchbook.
"""
import ast
import re
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime


class SketchManager:
    """Manages sketch files and operations."""
    
    DEFAULT_TEMPLATE = """# DrawBot Sketch
# Created: {timestamp}

import drawBot as drawbot

# Set canvas size
drawbot.size(400, 400)

# Set background color
drawbot.fill(1)  # White background
drawbot.rect(0, 0, drawbot.width(), drawbot.height())

# Your drawing code here
drawbot.fill(0)  # Black
drawbot.fontSize(24)
drawbot.text("Hello DrawBot!", (50, 200))

# Save the result
drawbot.saveImage("sketch_output.png")
"""
    
    def __init__(self, project_path: Path):
        """Initialize with project path.
        
        Args:
            project_path: Path to the project directory
        """
        self.project_path = project_path
        self.sketches_dir = project_path / 'sketches'
        self.templates_dir = project_path / 'templates'
    
    def create_sketch(self, name: str, template: Optional[str] = None) -> Path:
        """Create a new sketch folder with <folder_name>.py file.
        
        Args:
            name: Name for the sketch folder
            template: Optional template name to use
            
        Returns:
            Path to the created <folder_name>.py file
        """
        # Remove .py extension if provided (we always use <folder_name>.py)
        if name.endswith('.py'):
            name = name[:-3]
        
        sketch_folder = self.sketches_dir / name
        
        # Handle name conflicts by adding number suffix
        if sketch_folder.exists():
            base_name = name
            counter = 1
            while sketch_folder.exists():
                sketch_folder = self.sketches_dir / f"{base_name}_{counter}"
                counter += 1
        
        # Create the sketch folder
        sketch_folder.mkdir(parents=True, exist_ok=True)
        
        # Create <folder_name>.py file in the folder
        sketch_file = sketch_folder / f'{sketch_folder.name}.py'
        
        # Get template content
        if template:
            template_path = self.templates_dir / f"{template}.py"
            if template_path.exists():
                content = template_path.read_text()
            else:
                content = self.DEFAULT_TEMPLATE
        else:
            content = self.DEFAULT_TEMPLATE
        
        # Replace timestamp placeholder - only if it exists
        if '{timestamp}' in content:
            content = content.format(timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        
        # Create the <folder_name>.py file
        sketch_file.write_text(content)
        return sketch_file
    
    def validate_sketch_syntax(self, sketch_path: Path) -> bool:
        """Validate Python syntax of a sketch file.
        
        Args:
            sketch_path: Path to the sketch file
            
        Returns:
            True if syntax is valid, False otherwise
        """
        if not sketch_path.exists():
            return False
        
        if sketch_path.suffix != '.py':
            return False
        
        try:
            content = sketch_path.read_text(encoding='utf-8')
            ast.parse(content)
            return True
        except (SyntaxError, UnicodeDecodeError, OSError):
            return False
    
    def list_sketches_by_category(self, category: str) -> List[Path]:
        """List sketches in a specific category directory.
        
        Args:
            category: Name of the category subdirectory
            
        Returns:
            List of sketch file paths in the category
        """
        category_dir = self.sketches_dir / category
        if not category_dir.exists() or not category_dir.is_dir():
            return []
        
        return [f for f in category_dir.glob('*.py') if f.is_file()]
    
    def find_sketch(self, name: str) -> Optional[Path]:
        """Find a sketch by folder name.
        
        Args:
            name: Name of the sketch folder to find
            
        Returns:
            Path to the <folder_name>.py file if found, None otherwise
        """
        # Remove .py extension if provided (we look for folders, not files)
        if name.endswith('.py'):
            name = name[:-3]
        
        # Look for sketch folder with <folder_name>.py file
        sketch_folder = self.sketches_dir / name
        if sketch_folder.exists() and sketch_folder.is_dir():
            sketch_file = sketch_folder / f'{sketch_folder.name}.py'
            if sketch_file.exists() and sketch_file.is_file():
                return sketch_file
        
        return None
    
    def get_sketch_metadata(self, sketch_path: Path) -> Dict[str, Any]:
        """Extract metadata from sketch file docstring.
        
        Args:
            sketch_path: Path to the sketch file
            
        Returns:
            Dictionary containing extracted metadata
        """
        metadata = {
            'title': sketch_path.stem.replace('_', ' ').title(),
            'author': '',
            'description': '',
            'tags': []
        }
        
        if not sketch_path.exists():
            return metadata
        
        try:
            content = sketch_path.read_text(encoding='utf-8')
            
            # Look for docstring at the beginning of the file
            lines = content.strip().split('\n')
            if len(lines) > 0 and lines[0].strip().startswith('"""'):
                # Find the end of the docstring
                docstring_lines = []
                in_docstring = True
                
                for i, line in enumerate(lines):
                    if i == 0:
                        # First line, remove opening """
                        line = line.strip()[3:]
                        if line.endswith('"""'):
                            # Single line docstring
                            docstring_lines.append(line[:-3])
                            break
                        elif line:
                            docstring_lines.append(line)
                    else:
                        if line.strip().endswith('"""'):
                            # End of docstring
                            line = line.replace('"""', '').strip()
                            if line:
                                docstring_lines.append(line)
                            break
                        else:
                            docstring_lines.append(line.strip())
                
                # Parse docstring for metadata
                docstring_text = '\n'.join(docstring_lines)
                
                # Look for metadata patterns
                title_match = re.search(r'Title:\s*(.+)', docstring_text, re.IGNORECASE)
                if title_match:
                    metadata['title'] = title_match.group(1).strip()
                
                author_match = re.search(r'Author:\s*(.+)', docstring_text, re.IGNORECASE)
                if author_match:
                    metadata['author'] = author_match.group(1).strip()
                
                desc_match = re.search(r'Description:\s*(.+)', docstring_text, re.IGNORECASE)
                if desc_match:
                    metadata['description'] = desc_match.group(1).strip()
                
                tags_match = re.search(r'Tags:\s*(.+)', docstring_text, re.IGNORECASE)
                if tags_match:
                    tags_text = tags_match.group(1).strip()
                    metadata['tags'] = [tag.strip() for tag in tags_text.split(',')]
        
        except (OSError, UnicodeDecodeError):
            pass
        
        return metadata
    
    def list_all_sketches(self) -> List[Path]:
        """List all <folder_name>.py files in sketch folders.
        
        Returns:
            List of all <folder_name>.py file paths
        """
        if not self.sketches_dir.exists():
            return []
        
        sketches = []
        # Look for <folder_name>.py files in subdirectories
        for item in self.sketches_dir.iterdir():
            if item.is_dir():
                sketch_file = item / f'{item.name}.py'
                if sketch_file.exists() and sketch_file.is_file():
                    sketches.append(sketch_file)
        
        return sketches