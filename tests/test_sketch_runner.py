"""
Tests for sketch execution and runtime management.
"""
import tempfile
from pathlib import Path
import pytest
import time
from unittest.mock import Mock, patch, MagicMock


class TestSketchRunner:
    """Test suite for sketch execution operations."""
    
    def test_executes_simple_sketch(self):
        """Test running a basic sketch successfully."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            sketch_path = project_path / 'test_sketch.py'
            
            # Create a simple valid sketch
            sketch_content = """
import drawbot
drawbot.size(400, 400)
drawbot.fill(1, 0, 0)
drawbot.rect(10, 10, 100, 100)
drawbot.saveImage('output.png')
"""
            sketch_path.write_text(sketch_content)
            
            from src.core.sketch_runner import SketchRunner
            
            runner = SketchRunner(project_path)
            result = runner.run_sketch(sketch_path)
            
            assert result.success is True
            assert result.error is None
            assert result.execution_time > 0
            assert result.output_path is not None
    
    def test_captures_execution_errors(self):
        """Test error handling during sketch execution."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            sketch_path = project_path / 'error_sketch.py'
            
            # Create a sketch with syntax error
            sketch_content = """
import drawbot
drawbot.size(400, 400
drawbot.rect(10, 10, 100, 100)  # Missing closing parenthesis
"""
            sketch_path.write_text(sketch_content)
            
            from src.core.sketch_runner import SketchRunner
            
            runner = SketchRunner(project_path)
            result = runner.run_sketch(sketch_path)
            
            assert result.success is False
            assert result.error is not None
            assert "SyntaxError" in result.error or "invalid syntax" in result.error
    
    def test_handles_runtime_errors(self):
        """Test handling of runtime errors in sketches."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            sketch_path = project_path / 'runtime_error_sketch.py'
            
            # Create a sketch with runtime error
            sketch_content = """
import drawbot
drawbot.size(400, 400)
undefined_variable += 1  # NameError
drawbot.rect(10, 10, 100, 100)
"""
            sketch_path.write_text(sketch_content)
            
            from src.core.sketch_runner import SketchRunner
            
            runner = SketchRunner(project_path)
            result = runner.run_sketch(sketch_path)
            
            assert result.success is False
            assert result.error is not None
            assert "NameError" in result.error
    
    def test_handles_infinite_loops(self):
        """Test timeout protection for runaway sketches."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            sketch_path = project_path / 'infinite_loop_sketch.py'
            
            # Create a sketch with infinite loop
            sketch_content = """
import drawbot
import time
drawbot.size(400, 400)
while True:
    time.sleep(0.1)  # Infinite loop
"""
            sketch_path.write_text(sketch_content)
            
            from src.core.sketch_runner import SketchRunner
            
            runner = SketchRunner(project_path, timeout=2.0)  # 2 second timeout
            start_time = time.time()
            result = runner.run_sketch(sketch_path)
            elapsed_time = time.time() - start_time
            
            assert result.success is False
            assert "timeout" in result.error.lower() or "timed out" in result.error.lower()
            assert elapsed_time < 3.0  # Should timeout before 3 seconds
    
    def test_manages_execution_context(self):
        """Test isolated execution environment."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            
            # First sketch
            sketch1_path = project_path / 'sketch1.py'
            sketch1_content = """
global_var = "from sketch 1"
import drawbot
drawbot.size(400, 400)
"""
            sketch1_path.write_text(sketch1_content)
            
            # Second sketch that tries to access first sketch's variable
            sketch2_path = project_path / 'sketch2.py'
            sketch2_content = """
import drawbot
drawbot.size(400, 400)
try:
    print(global_var)  # Should not be accessible
except NameError:
    result = "isolated"
"""
            sketch2_path.write_text(sketch2_content)
            
            from src.core.sketch_runner import SketchRunner
            
            runner = SketchRunner(project_path)
            
            # Run first sketch
            result1 = runner.run_sketch(sketch1_path)
            assert result1.success is True
            
            # Run second sketch - should be isolated
            result2 = runner.run_sketch(sketch2_path)
            assert result2.success is True
    
    def test_tracks_execution_time(self):
        """Test performance monitoring."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            sketch_path = project_path / 'timed_sketch.py'
            
            # Create a sketch with deliberate delay
            sketch_content = """
import drawbot
import time
drawbot.size(400, 400)
time.sleep(0.1)  # 100ms delay
drawbot.rect(10, 10, 100, 100)
"""
            sketch_path.write_text(sketch_content)
            
            from src.core.sketch_runner import SketchRunner
            
            runner = SketchRunner(project_path)
            result = runner.run_sketch(sketch_path)
            
            assert result.success is True
            assert result.execution_time >= 0.1  # Should be at least 100ms
            assert result.execution_time < 1.0   # But not too long
    
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
            assert "not found" in result.error.lower() or "no such file" in result.error.lower()
    
    def test_captures_print_output(self):
        """Test capturing print statements from sketches."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            sketch_path = project_path / 'print_sketch.py'
            
            # Create a sketch with print statements
            sketch_content = """
import drawbot
print("Starting sketch")
drawbot.size(400, 400)
print("Canvas created")
drawbot.rect(10, 10, 100, 100)
print("Rectangle drawn")
"""
            sketch_path.write_text(sketch_content)
            
            from src.core.sketch_runner import SketchRunner
            
            runner = SketchRunner(project_path)
            result = runner.run_sketch(sketch_path)
            
            assert result.success is True
            assert result.stdout is not None
            assert "Starting sketch" in result.stdout
            assert "Canvas created" in result.stdout
            assert "Rectangle drawn" in result.stdout
    
    def test_sets_working_directory(self):
        """Test that sketch runs with correct working directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            sketch_path = project_path / 'cwd_sketch.py'
            
            # Create a sketch that checks current working directory
            sketch_content = """
import os
import drawbot
current_dir = os.getcwd()
with open('cwd_test.txt', 'w') as f:
    f.write(current_dir)
drawbot.size(400, 400)
"""
            sketch_path.write_text(sketch_content)
            
            from src.core.sketch_runner import SketchRunner
            
            runner = SketchRunner(project_path)
            result = runner.run_sketch(sketch_path)
            
            assert result.success is True
            
            # Check that file was created in project directory
            test_file = project_path / 'cwd_test.txt'
            assert test_file.exists()
    
    def test_run_with_custom_output_dir(self):
        """Test running sketch with custom output directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            output_dir = project_path / 'custom_output'
            output_dir.mkdir()
            
            sketch_path = project_path / 'output_sketch.py'
            sketch_content = """
import drawbot
drawbot.size(400, 400)
drawbot.fill(1, 0, 0)
drawbot.rect(10, 10, 100, 100)
drawbot.saveImage('custom_output.png')
"""
            sketch_path.write_text(sketch_content)
            
            from src.core.sketch_runner import SketchRunner
            
            runner = SketchRunner(project_path)
            result = runner.run_sketch(sketch_path, output_dir=output_dir)
            
            assert result.success is True
            assert result.output_path is not None
            assert str(output_dir) in str(result.output_path)
    
    def test_gets_execution_result_metadata(self):
        """Test that execution results contain proper metadata."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            sketch_path = project_path / 'meta_sketch.py'
            
            sketch_content = """
import drawbot
drawbot.size(200, 300)
drawbot.rect(0, 0, 100, 100)
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