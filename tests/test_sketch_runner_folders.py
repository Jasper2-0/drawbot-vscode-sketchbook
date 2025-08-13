"""
Tests for sketch runner with folder-based sketches.
"""
import tempfile
from pathlib import Path
import pytest
import time


class TestSketchRunnerFolders:
    """Test suite for sketch runner folder functionality."""
    
    def test_runs_sketch_from_folder(self):
        """Test running a sketch.py file from a sketch folder."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            sketches_dir = project_path / 'sketches'
            sketches_dir.mkdir()
            
            # Create sketch folder structure
            sketch_folder = sketches_dir / 'my_sketch'
            sketch_folder.mkdir()
            sketch_file = sketch_folder / 'sketch.py'
            
            sketch_content = """
print("Running from folder")
result = 3 * 4
print(f"Calculation: {result}")
with open('output.txt', 'w') as f:
    f.write(f"Result from folder: {result}")
"""
            sketch_file.write_text(sketch_content)
            
            from src.core.sketch_runner import SketchRunner
            
            runner = SketchRunner(project_path)
            result = runner.run_sketch(sketch_file)
            
            assert result.success is True
            assert result.error is None
            assert "Running from folder" in result.stdout
            assert "Calculation: 12" in result.stdout
            
            # Check output was created in project directory
            output_file = project_path / 'output.txt'
            assert output_file.exists()
            assert "Result from folder: 12" in output_file.read_text()
    
    def test_runs_sketch_with_data_folder(self):
        """Test running a sketch that uses files from a data folder."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            sketches_dir = project_path / 'sketches'
            sketches_dir.mkdir()
            
            # Create sketch folder with data
            sketch_folder = sketches_dir / 'data_sketch'
            sketch_folder.mkdir()
            data_folder = sketch_folder / 'data'
            data_folder.mkdir()
            
            # Create data file
            config_file = data_folder / 'config.txt'
            config_file.write_text('color=red,size=100')
            
            # Create sketch that reads data
            sketch_file = sketch_folder / 'sketch.py'
            sketch_content = """
import os
from pathlib import Path

# Try to read from data folder relative to sketch
sketch_dir = Path(__file__).parent
data_file = sketch_dir / 'data' / 'config.txt'

if data_file.exists():
    config = data_file.read_text()
    print(f"Loaded config: {config}")
    
    # Process config
    parts = config.split(',')
    for part in parts:
        key, value = part.split('=')
        print(f"Setting {key} to {value}")
else:
    print("Data file not found")
    
with open('result.txt', 'w') as f:
    f.write('Sketch completed with data')
"""
            sketch_file.write_text(sketch_content)
            
            from src.core.sketch_runner import SketchRunner
            
            runner = SketchRunner(project_path)
            result = runner.run_sketch(sketch_file)
            
            assert result.success is True
            assert "Loaded config: color=red,size=100" in result.stdout
            assert "Setting color to red" in result.stdout
            assert "Setting size to 100" in result.stdout
            
            # Check output
            output_file = project_path / 'result.txt'
            assert output_file.exists()
            assert "Sketch completed with data" in output_file.read_text()
    
    def test_validates_folder_based_sketch(self):
        """Test syntax validation for sketch.py in folders."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            sketches_dir = project_path / 'sketches'
            sketches_dir.mkdir()
            
            # Valid sketch in folder
            valid_folder = sketches_dir / 'valid_sketch'
            valid_folder.mkdir()
            valid_sketch = valid_folder / 'sketch.py'
            valid_sketch.write_text("""
print("Valid sketch")
x = 42
y = x * 2
""")
            
            from src.core.sketch_runner import SketchRunner
            
            runner = SketchRunner(project_path)
            result = runner.validate_sketch_before_run(valid_sketch)
            
            assert result.success is True
            assert result.error is None
    
    def test_handles_sketch_folder_errors(self):
        """Test error handling for sketch folders."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            sketches_dir = project_path / 'sketches'
            sketches_dir.mkdir()
            
            # Invalid sketch in folder
            invalid_folder = sketches_dir / 'invalid_sketch'
            invalid_folder.mkdir()
            invalid_sketch = invalid_folder / 'sketch.py'
            invalid_sketch.write_text("""
print("Invalid sketch")
undefined_var.method()  # NameError
""")
            
            from src.core.sketch_runner import SketchRunner
            
            runner = SketchRunner(project_path)
            result = runner.run_sketch(invalid_sketch)
            
            assert result.success is False
            assert result.error is not None
            assert "NameError" in result.error
    
    def test_sketch_folder_with_additional_modules(self):
        """Test sketch folder with additional Python modules."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            sketches_dir = project_path / 'sketches'
            sketches_dir.mkdir()
            
            # Create sketch folder
            sketch_folder = sketches_dir / 'modular_sketch'
            sketch_folder.mkdir()
            
            # Create helper module
            helper_file = sketch_folder / 'helper.py'
            helper_file.write_text("""
def calculate(x, y):
    return x * y + 10

def format_result(result):
    return f"Final result: {result}"
""")
            
            # Create main sketch that uses helper
            sketch_file = sketch_folder / 'sketch.py'
            sketch_content = """
import sys
from pathlib import Path

# Add sketch folder to path so we can import helper
sketch_dir = Path(__file__).parent
sys.path.insert(0, str(sketch_dir))

import helper

print("Starting modular sketch")
result = helper.calculate(5, 6)
formatted = helper.format_result(result)
print(formatted)

with open('modular_output.txt', 'w') as f:
    f.write(formatted)
"""
            sketch_file.write_text(sketch_content)
            
            from src.core.sketch_runner import SketchRunner
            
            runner = SketchRunner(project_path)
            result = runner.run_sketch(sketch_file)
            
            assert result.success is True
            assert "Starting modular sketch" in result.stdout
            assert "Final result: 40" in result.stdout  # 5*6+10 = 40
            
            # Check output
            output_file = project_path / 'modular_output.txt'
            assert output_file.exists()
            assert "Final result: 40" in output_file.read_text()
    
    def test_sketch_folder_working_directory(self):
        """Test that sketch runs with project as working directory, not sketch folder."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            sketches_dir = project_path / 'sketches'
            sketches_dir.mkdir()
            
            # Create sketch folder
            sketch_folder = sketches_dir / 'wd_test'
            sketch_folder.mkdir()
            
            sketch_file = sketch_folder / 'sketch.py'
            sketch_content = """
import os
from pathlib import Path

cwd = Path.cwd()
sketch_file_path = Path(__file__)
sketch_dir = sketch_file_path.parent

print(f"Current working directory: {cwd}")
print(f"Sketch file location: {sketch_file_path}")
print(f"Sketch directory: {sketch_dir}")

# Create a file in current working directory (should be project root)
with open('wd_test_output.txt', 'w') as f:
    f.write(f"CWD: {cwd}")
    f.write(f"\\nSketch dir: {sketch_dir}")
"""
            sketch_file.write_text(sketch_content)
            
            from src.core.sketch_runner import SketchRunner
            
            runner = SketchRunner(project_path)
            result = runner.run_sketch(sketch_file)
            
            assert result.success is True
            
            # Check that output was created in project directory, not sketch folder
            output_file = project_path / 'wd_test_output.txt'
            assert output_file.exists()
            
            # Verify working directory was project root
            content = output_file.read_text()
            assert str(project_path) in content
            assert str(sketch_folder) in content  # Sketch dir should be different from CWD