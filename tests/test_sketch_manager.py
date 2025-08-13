"""
Tests for sketch file management and operations.
"""
import os
import tempfile
import shutil
from pathlib import Path
import pytest
from datetime import datetime


class TestSketchManager:
    """Test suite for sketch management operations."""
    
    def test_creates_new_sketch(self):
        """Test creating a new sketch folder with <folder_name>.py file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            sketches_dir = project_path / 'sketches'
            sketches_dir.mkdir()
            
            from src.core.sketch_manager import SketchManager
            
            sm = SketchManager(project_path)
            sketch_path = sm.create_sketch('my_first_sketch')
            
            # Should return path to <folder_name>.py inside folder
            assert sketch_path.exists(), "Sketch file should be created"
            assert sketch_path.name == 'my_first_sketch.py', "Main file should be named my_first_sketch.py"
            assert sketch_path.parent.name == 'my_first_sketch', "Should be in sketch folder"
            assert sketch_path.parent.parent == sketches_dir, "Sketch folder should be in sketches directory"
            
            # Check folder structure
            sketch_folder = sketches_dir / 'my_first_sketch'
            assert sketch_folder.exists() and sketch_folder.is_dir(), "Should create sketch folder"
            assert (sketch_folder / 'my_first_sketch.py').exists(), "Should create my_first_sketch.py file"
            
            # Check basic template content
            content = sketch_path.read_text()
            assert 'import drawBot as drawbot' in content, "Should import drawbot"
            assert 'size(' in content, "Should set canvas size"
    
    def test_creates_sketch_from_template(self):
        """Test creating sketch folder from specific template."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            sketches_dir = project_path / 'sketches'
            templates_dir = project_path / 'templates'
            sketches_dir.mkdir()
            templates_dir.mkdir()
            
            # Create a custom template
            template_content = """# Custom Template
import drawbot as db

db.size(800, 600)
db.fill(1, 0, 0)  # Red
db.rect(100, 100, 200, 150)
db.saveImage('output.png')
"""
            template_path = templates_dir / 'basic_shapes.py'
            template_path.write_text(template_content)
            
            from src.core.sketch_manager import SketchManager
            
            sm = SketchManager(project_path)
            sketch_path = sm.create_sketch('red_rectangle', template='basic_shapes')
            
            # Should create folder structure with template content
            assert sketch_path.exists(), "Sketch file should be created"
            assert sketch_path.name == 'red_rectangle.py', "Main file should be red_rectangle.py"
            assert sketch_path.parent.name == 'red_rectangle', "Should be in named folder"
            
            content = sketch_path.read_text()
            assert 'Custom Template' in content
            assert 'fill(1, 0, 0)' in content
    
    def test_validates_sketch_syntax(self):
        """Test Python syntax validation for sketch files in folders."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            sketches_dir = project_path / 'sketches'
            sketches_dir.mkdir()
            
            from src.core.sketch_manager import SketchManager
            
            sm = SketchManager(project_path)
            
            # Valid sketch in folder
            valid_folder = sketches_dir / 'valid_sketch'
            valid_folder.mkdir()
            valid_sketch = valid_folder / 'valid_folder.py'
            valid_sketch.write_text("""
import drawbot
drawbot.size(400, 400)
drawbot.rect(10, 10, 100, 100)
""")
            
            assert sm.validate_sketch_syntax(valid_sketch) is True
            
            # Invalid sketch in folder
            invalid_folder = sketches_dir / 'invalid_sketch'
            invalid_folder.mkdir()
            invalid_sketch = invalid_folder / 'invalid_folder.py'
            invalid_sketch.write_text("""
import drawbot
drawbot.size(400, 400
drawbot.rect(10, 10, 100, 100)  # Missing closing parenthesis
""")
            
            assert sm.validate_sketch_syntax(invalid_sketch) is False
    
    def test_lists_sketches_by_category(self):
        """Test organizing and listing sketches by category."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            sketches_dir = project_path / 'sketches'
            sketches_dir.mkdir()
            
            # Create category directories
            animation_dir = sketches_dir / 'animation'
            static_dir = sketches_dir / 'static'
            animation_dir.mkdir()
            static_dir.mkdir()
            
            # Create sketches in categories
            (animation_dir / 'bouncing_ball.py').write_text('# Animation sketch')
            (animation_dir / 'rotating_square.py').write_text('# Rotation sketch')
            (static_dir / 'mandala.py').write_text('# Static mandala')
            
            from src.core.sketch_manager import SketchManager
            
            sm = SketchManager(project_path)
            
            animation_sketches = sm.list_sketches_by_category('animation')
            assert len(animation_sketches) == 2
            assert any('bouncing_ball.py' in str(sketch) for sketch in animation_sketches)
            assert any('rotating_square.py' in str(sketch) for sketch in animation_sketches)
            
            static_sketches = sm.list_sketches_by_category('static')
            assert len(static_sketches) == 1
            assert any('mandala.py' in str(sketch) for sketch in static_sketches)
    
    def test_finds_sketch_by_name(self):
        """Test sketch discovery and retrieval in folder structure."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            sketches_dir = project_path / 'sketches'
            sketches_dir.mkdir()
            
            # Create sketch folders
            circles_folder = sketches_dir / 'circles'
            triangles_folder = sketches_dir / 'triangles'
            circles_folder.mkdir()
            triangles_folder.mkdir()
            
            # Create <folder_name>.py files in folders
            sketch1 = circles_folder / 'circles.py'
            sketch2 = triangles_folder / 'triangles.py'
            sketch1.write_text('# Circle sketch')
            sketch2.write_text('# Triangle sketch')
            
            from src.core.sketch_manager import SketchManager
            
            sm = SketchManager(project_path)
            
            # Find by folder name
            found_sketch = sm.find_sketch('circles')
            assert found_sketch == sketch1
            
            # Find second sketch
            found_sketch2 = sm.find_sketch('triangles')
            assert found_sketch2 == sketch2
            
            # Non-existent sketch
            not_found = sm.find_sketch('non_existent')
            assert not_found is None
    
    def test_handles_invalid_sketch_files(self):
        """Test error handling for malformed sketches."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            sketches_dir = project_path / 'sketches'
            sketches_dir.mkdir()
            
            from src.core.sketch_manager import SketchManager
            
            sm = SketchManager(project_path)
            
            # Test non-existent sketch
            result = sm.validate_sketch_syntax(Path('non_existent.py'))
            assert result is False
            
            # Test non-Python file
            non_python = sketches_dir / 'image.png'
            non_python.write_bytes(b'\x89PNG')  # Fake PNG header
            
            result = sm.validate_sketch_syntax(non_python)
            assert result is False
    
    def test_creates_sketch_with_unique_name(self):
        """Test creating sketches with unique names when conflicts exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            sketches_dir = project_path / 'sketches'
            sketches_dir.mkdir()
            
            from src.core.sketch_manager import SketchManager
            
            sm = SketchManager(project_path)
            
            # Create first sketch
            sketch1 = sm.create_sketch('test_sketch')
            assert sketch1.name == 'test_sketch.py'
            assert sketch1.parent.name == 'test_sketch'
            
            # Create second sketch with same name
            sketch2 = sm.create_sketch('test_sketch')
            assert sketch2.name == 'test_sketch_1.py'  # Second sketch gets _1 suffix
            assert sketch2.parent.name != 'test_sketch'  # Folder should be modified
            assert 'test_sketch' in sketch2.parent.name
            assert sketch2.exists()
    
    def test_gets_sketch_metadata(self):
        """Test extracting metadata from sketch files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            sketches_dir = project_path / 'sketches'
            sketches_dir.mkdir()
            
            # Create sketch with metadata comments
            sketch_content = '''"""
Title: My Awesome Sketch
Author: Test User
Description: A beautiful generative art piece
Tags: art, generative, colorful
"""
import drawbot
drawbot.size(400, 400)
'''
            sketch_path = sketches_dir / 'awesome_sketch.py'
            sketch_path.write_text(sketch_content)
            
            from src.core.sketch_manager import SketchManager
            
            sm = SketchManager(project_path)
            metadata = sm.get_sketch_metadata(sketch_path)
            
            assert metadata['title'] == 'My Awesome Sketch'
            assert metadata['author'] == 'Test User'
            assert 'generative art piece' in metadata['description']
            assert 'art' in metadata['tags']
            assert 'generative' in metadata['tags']
    
    def test_lists_all_sketches(self):
        """Test listing all sketches in folder structure."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            sketches_dir = project_path / 'sketches'
            sketches_dir.mkdir()
            
            # Create sketch folders with sketch.py files
            sketch1_folder = sketches_dir / 'sketch1'
            sketch2_folder = sketches_dir / 'sketch2'
            sketch3_folder = sketches_dir / 'sketch3'
            
            sketch1_folder.mkdir()
            sketch2_folder.mkdir()
            sketch3_folder.mkdir()
            
            (sketch1_folder / 'sketch1.py').write_text('# Sketch 1')
            (sketch2_folder / 'sketch2.py').write_text('# Sketch 2')
            (sketch3_folder / 'sketch3.py').write_text('# Sketch 3')
            
            # Create non-sketch folders (should be ignored)
            (sketches_dir / 'readme.txt').write_text('Not a sketch')
            empty_folder = sketches_dir / 'empty'
            empty_folder.mkdir()
            
            from src.core.sketch_manager import SketchManager
            
            sm = SketchManager(project_path)
            all_sketches = sm.list_all_sketches()
            
            assert len(all_sketches) == 3
            # All should be <folder_name>.py files
            sketch_names = [sketch.name for sketch in all_sketches]
            expected_names = ['sketch1.py', 'sketch2.py', 'sketch3.py']
            assert sorted(sketch_names) == sorted(expected_names)
            
            # Check parent folders
            folder_names = [sketch.parent.name for sketch in all_sketches]
            assert 'sketch1' in folder_names
            assert 'sketch2' in folder_names
            assert 'sketch3' in folder_names
    
    def test_creates_sketch_with_data_folder(self):
        """Test that sketch folders can contain data subfolders."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            sketches_dir = project_path / 'sketches'
            sketches_dir.mkdir()
            
            from src.core.sketch_manager import SketchManager
            
            sm = SketchManager(project_path)
            sketch_path = sm.create_sketch('complex_sketch')
            
            # Manually create data folder structure (would be created by user)
            sketch_folder = sketch_path.parent
            data_folder = sketch_folder / 'data'
            data_folder.mkdir()
            
            # Add some mock data files
            (data_folder / 'image.png').write_bytes(b'fake image data')
            (data_folder / 'config.json').write_text('{"color": "red"}')
            
            assert data_folder.exists(), "Data folder should exist"
            assert (data_folder / 'image.png').exists(), "Data files should exist"
            assert (data_folder / 'config.json').exists(), "Config files should exist"
    
    def test_creates_sketch_with_output_folder(self):
        """Test that sketch folders can contain output subfolders."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            sketches_dir = project_path / 'sketches'
            sketches_dir.mkdir()
            
            from src.core.sketch_manager import SketchManager
            
            sm = SketchManager(project_path)
            sketch_path = sm.create_sketch('output_sketch')
            
            # Manually create output folder (would be created by sketch runner)
            sketch_folder = sketch_path.parent
            output_folder = sketch_folder / 'output'
            output_folder.mkdir()
            
            # Add some mock output files
            (output_folder / 'render_001.png').write_bytes(b'fake image')
            (output_folder / 'animation.gif').write_bytes(b'fake gif')
            
            assert output_folder.exists(), "Output folder should exist"
            assert (output_folder / 'render_001.png').exists(), "Output files should exist"
    
    def test_handles_duplicate_sketch_names(self):
        """Test creating sketches with duplicate names generates unique folders."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            sketches_dir = project_path / 'sketches'
            sketches_dir.mkdir()
            
            from src.core.sketch_manager import SketchManager
            
            sm = SketchManager(project_path)
            
            # Create first sketch
            sketch1_path = sm.create_sketch('test_sketch')
            assert sketch1_path.parent.name == 'test_sketch'
            
            # Create second sketch with same name
            sketch2_path = sm.create_sketch('test_sketch')
            assert sketch2_path.parent.name != 'test_sketch'  # Should be modified
            assert 'test_sketch' in sketch2_path.parent.name
            
            # Both should exist
            assert sketch1_path.exists()
            assert sketch2_path.exists()
    
    def test_find_sketch_ignores_non_sketch_folders(self):
        """Test that find_sketch only looks for folders with <folder_name>.py files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            sketches_dir = project_path / 'sketches'
            sketches_dir.mkdir()
            
            # Create valid sketch folder
            valid_folder = sketches_dir / 'valid_sketch'
            valid_folder.mkdir()
            (valid_folder / 'valid_sketch.py').write_text('# Valid sketch')
            
            # Create invalid folder (no <folder_name>.py)
            invalid_folder = sketches_dir / 'invalid_folder'
            invalid_folder.mkdir()
            (invalid_folder / 'other.py').write_text('# Not a sketch')
            
            # Create folder with wrong file name
            wrong_name_folder = sketches_dir / 'wrong_name'
            wrong_name_folder.mkdir()
            (wrong_name_folder / 'main.py').write_text('# Wrong name')
            
            from src.core.sketch_manager import SketchManager
            
            sm = SketchManager(project_path)
            
            # Should find valid sketch
            found = sm.find_sketch('valid_sketch')
            assert found is not None
            assert found.name == 'valid_sketch.py'
            
            # Should not find invalid folders
            not_found1 = sm.find_sketch('invalid_folder')
            assert not_found1 is None
            
            not_found2 = sm.find_sketch('wrong_name')
            assert not_found2 is None