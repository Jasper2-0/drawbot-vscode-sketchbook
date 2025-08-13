"""
Simplified tests for sketch runner focusing on core functionality.
"""
import tempfile
from pathlib import Path
import pytest
import time


class TestSketchRunnerSimple:
    """Test suite for sketch runner core functionality."""
    
    def test_handles_non_existent_sketch(self):
        """Test error handling for missing sketch files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            non_existent_path = project_path / 'does_not_exist.py'
            
            from src.core.sketch_runner import SketchRunner
            
            runner = SketchRunner(project_path)
            result = runner.run_sketch(non_existent_path)
            
            assert result.success is False
            assert result.error is not None
            assert "not found" in result.error.lower()
            assert result.sketch_path == non_existent_path
    
    def test_validates_sketch_syntax(self):
        """Test syntax validation before execution."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            
            # Valid sketch
            valid_sketch = project_path / 'valid.py'
            valid_sketch.write_text("""
print("Hello World")
x = 42
y = x * 2
""")
            
            from src.core.sketch_runner import SketchRunner
            
            runner = SketchRunner(project_path)
            result = runner.validate_sketch_before_run(valid_sketch)
            
            assert result.success is True
            assert result.error is None
    
    def test_detects_syntax_errors(self):
        """Test detection of syntax errors."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            
            # Invalid sketch
            invalid_sketch = project_path / 'invalid.py'
            invalid_sketch.write_text("""
print("Hello World"
x = 42  # Missing closing parenthesis
""")
            
            from src.core.sketch_runner import SketchRunner
            
            runner = SketchRunner(project_path)
            result = runner.validate_sketch_before_run(invalid_sketch)
            
            assert result.success is False
            assert result.error is not None
            assert "SyntaxError" in result.error
    
    def test_executes_simple_python_sketch(self):
        """Test running a basic Python sketch without DrawBot."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            sketch_path = project_path / 'simple_sketch.py'
            
            # Create a simple sketch that doesn't use DrawBot
            sketch_content = """
print("Starting sketch")
result = 2 + 2
print(f"Calculation result: {result}")
with open('test_output.txt', 'w') as f:
    f.write(f"Result: {result}")
print("Sketch completed")
"""
            sketch_path.write_text(sketch_content)
            
            from src.core.sketch_runner import SketchRunner
            
            runner = SketchRunner(project_path)
            result = runner.run_sketch(sketch_path)
            
            assert result.success is True
            assert result.error is None
            assert result.execution_time > 0
            assert result.stdout is not None
            assert "Starting sketch" in result.stdout
            assert "Sketch completed" in result.stdout
            
            # Check that output file was created
            output_file = project_path / 'test_output.txt'
            assert output_file.exists()
            assert "Result: 4" in output_file.read_text()
    
    def test_handles_runtime_errors(self):
        """Test handling of runtime errors in sketches."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            sketch_path = project_path / 'error_sketch.py'
            
            # Create a sketch with runtime error
            sketch_content = """
print("Starting sketch")
undefined_variable += 1  # NameError
print("This should not be reached")
"""
            sketch_path.write_text(sketch_content)
            
            from src.core.sketch_runner import SketchRunner
            
            runner = SketchRunner(project_path)
            result = runner.run_sketch(sketch_path)
            
            assert result.success is False
            assert result.error is not None
            assert "NameError" in result.error
            assert result.stderr is not None
    
    def test_timeout_protection(self):
        """Test timeout protection for long-running sketches."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            sketch_path = project_path / 'slow_sketch.py'
            
            # Create a sketch that runs longer than timeout
            sketch_content = """
import time
print("Starting slow sketch")
time.sleep(3)  # Sleep for 3 seconds
print("This should not be reached due to timeout")
"""
            sketch_path.write_text(sketch_content)
            
            from src.core.sketch_runner import SketchRunner
            
            runner = SketchRunner(project_path, timeout=1.0)  # 1 second timeout
            start_time = time.time()
            result = runner.run_sketch(sketch_path)
            elapsed_time = time.time() - start_time
            
            assert result.success is False
            assert result.error is not None
            assert ("timeout" in result.error.lower() or "timed out" in result.error.lower())
            assert elapsed_time < 2.0  # Should complete in under 2 seconds
    
    def test_execution_result_metadata(self):
        """Test that execution results contain proper metadata."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            sketch_path = project_path / 'meta_sketch.py'
            
            sketch_content = """
print("Metadata test")
x = 1 + 1
print(f"Result: {x}")
"""
            sketch_path.write_text(sketch_content)
            
            from src.core.sketch_runner import SketchRunner
            
            runner = SketchRunner(project_path)
            result = runner.run_sketch(sketch_path)
            
            assert result.success is True
            assert result.sketch_path == sketch_path
            assert isinstance(result.execution_time, float)
            assert result.execution_time >= 0
            assert result.timestamp is not None
    
    def test_working_directory_isolation(self):
        """Test that sketches run in the project directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            sketch_path = project_path / 'cwd_sketch.py'
            
            # Create a sketch that creates a file in current directory
            sketch_content = """
import os
current_dir = os.getcwd()
with open('working_dir_test.txt', 'w') as f:
    f.write(current_dir)
print(f"Working directory: {current_dir}")
"""
            sketch_path.write_text(sketch_content)
            
            from src.core.sketch_runner import SketchRunner
            
            runner = SketchRunner(project_path)
            result = runner.run_sketch(sketch_path)
            
            assert result.success is True
            
            # Check that file was created in project directory
            test_file = project_path / 'working_dir_test.txt'
            assert test_file.exists()
            
            # Verify the working directory was correct
            recorded_dir = test_file.read_text()
            assert str(project_path) in recorded_dir
    
    def test_custom_output_directory(self):
        """Test running sketch with custom output directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            output_dir = project_path / 'custom_output'
            output_dir.mkdir()
            
            sketch_path = project_path / 'output_sketch.py'
            sketch_content = """
import os
print("Creating test output")
with open('test_file.txt', 'w') as f:
    f.write("Test output content")
print("Output created")
"""
            sketch_path.write_text(sketch_content)
            
            from src.core.sketch_runner import SketchRunner
            
            runner = SketchRunner(project_path)
            result = runner.run_sketch(sketch_path, output_dir=output_dir)
            
            assert result.success is True
            # The file should be created in the project directory (current working directory)
            # but output_dir parameter is available for future use
    
    def test_multiple_sketch_execution(self):
        """Test running multiple sketches in sequence."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            
            from src.core.sketch_runner import SketchRunner
            runner = SketchRunner(project_path)
            
            # Create and run multiple sketches
            for i in range(3):
                sketch_path = project_path / f'sketch_{i}.py'
                sketch_content = f"""
print("Running sketch {i}")
result = {i} * 2
with open('sketch_{i}_output.txt', 'w') as f:
    f.write(str(result))
print("Sketch {i} completed")
"""
                sketch_path.write_text(sketch_content)
                
                result = runner.run_sketch(sketch_path)
                
                assert result.success is True
                assert f"Running sketch {i}" in result.stdout
                assert f"Sketch {i} completed" in result.stdout
                
                # Check output file
                output_file = project_path / f'sketch_{i}_output.txt'
                assert output_file.exists()
                assert output_file.read_text() == str(i * 2)