"""
Tests for PreviewEngine - Core preview execution system.
"""
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.core.preview_cache import PreviewCache
from src.core.preview_engine import PreviewEngine, PreviewResult


class TestPreviewEngine:
    """Test suite for PreviewEngine functionality."""

    def test_execute_simple_sketch_success(self):
        """Test basic sketch execution and preview generation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            sketch_file = project_path / "test_sketch.py"
            sketch_file.write_text(
                """
import drawBot as drawbot
drawbot.size(400, 400)
drawbot.fill(1, 0, 0)
drawbot.rect(50, 50, 100, 100)
drawbot.saveImage('output.png')
"""
            )

            cache = PreviewCache(temp_dir)
            engine = PreviewEngine(project_path, cache)

            result = engine.execute_sketch(sketch_file)

            assert result.success
            assert result.error is None
            assert result.preview_url is not None
            assert result.preview_path.exists()
            assert result.execution_time > 0

    def test_execute_sketch_with_syntax_error(self):
        """Test error handling for broken sketches."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            sketch_file = project_path / "broken_sketch.py"
            sketch_file.write_text(
                """
import drawBot as drawbot
drawbot.size(400, 400
# Missing closing parenthesis - syntax error
"""
            )

            cache = PreviewCache(temp_dir)
            engine = PreviewEngine(project_path, cache)

            result = engine.execute_sketch(sketch_file)

            assert not result.success
            assert result.error is not None
            assert "SyntaxError" in result.error
            assert result.preview_url is None

    def test_execute_sketch_timeout_protection(self):
        """Test timeout mechanism for infinite loops."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            sketch_file = project_path / "infinite_loop_sketch.py"
            sketch_file.write_text(
                """
import time
while True:
    time.sleep(0.1)
"""
            )

            cache = PreviewCache(temp_dir)
            engine = PreviewEngine(project_path, cache, timeout=1.0)  # 1 second timeout

            start_time = time.time()
            result = engine.execute_sketch(sketch_file)
            execution_time = time.time() - start_time

            assert not result.success
            assert "timeout" in result.error.lower()
            assert execution_time < 2.0  # Should timeout within 1 second + buffer

    def test_concurrent_execution_cancellation(self):
        """Test that new executions cancel previous ones."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            sketch_file1 = project_path / "slow_sketch1.py"
            sketch_file2 = project_path / "quick_sketch2.py"

            sketch_file1.write_text(
                """
import time
time.sleep(2)  # Slow sketch
import drawBot as drawbot
drawbot.size(400, 400)
drawbot.saveImage('output.png')
"""
            )

            sketch_file2.write_text(
                """
import drawBot as drawbot
drawbot.size(400, 400)
drawbot.fill(0, 1, 0)
drawbot.rect(0, 0, 100, 100)
drawbot.saveImage('output.png')
"""
            )

            cache = PreviewCache(temp_dir)
            engine = PreviewEngine(project_path, cache)

            # Start slow execution
            import threading

            result1 = None

            def slow_execution():
                nonlocal result1
                result1 = engine.execute_sketch(sketch_file1)

            thread1 = threading.Thread(target=slow_execution)
            thread1.start()

            # Brief delay then start quick execution
            time.sleep(0.1)
            result2 = engine.execute_sketch(sketch_file2)

            # Quick execution should succeed
            assert result2.success

            thread1.join(timeout=3)
            # First execution should be cancelled/failed
            if result1:
                assert not result1.success or "cancelled" in result1.error.lower()

    def test_resource_cleanup_after_execution(self):
        """Test memory and file cleanup."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            sketch_file = project_path / "test_sketch.py"
            sketch_file.write_text(
                """
import drawBot as drawbot
drawbot.size(400, 400)
drawbot.fill(1, 0.5, 0)
drawbot.oval(50, 50, 300, 300)
drawbot.saveImage('output.png')
"""
            )

            cache = PreviewCache(temp_dir)
            engine = PreviewEngine(project_path, cache)

            # Track temp files before execution
            temp_files_before = list(Path(temp_dir).glob("**/*"))

            result = engine.execute_sketch(sketch_file)

            # Should succeed
            assert result.success

            # Check that only expected files remain (preview + cache files)
            temp_files_after = list(Path(temp_dir).glob("**/*"))

            # Should not accumulate excessive temp files
            assert (
                len(temp_files_after) <= len(temp_files_before) + 3
            )  # Allow for preview + metadata

    def test_virtual_environment_detection(self):
        """Test proper Python executable selection."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)

            cache = PreviewCache(temp_dir)
            engine = PreviewEngine(project_path, cache)

            # Should detect current Python executable
            python_exe = engine._get_python_executable()

            assert python_exe is not None
            assert Path(python_exe).exists()
            # Should prefer venv python if available, otherwise system python
            assert "python" in str(python_exe).lower()

    def test_execute_sketch_with_runtime_error(self):
        """Test handling of runtime errors in sketches."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            sketch_file = project_path / "runtime_error_sketch.py"
            sketch_file.write_text(
                """
import drawBot as drawbot
drawbot.size(400, 400)
# This will cause a runtime error
x = 1 / 0
"""
            )

            cache = PreviewCache(temp_dir)
            engine = PreviewEngine(project_path, cache)

            result = engine.execute_sketch(sketch_file)

            assert not result.success
            assert result.error is not None
            assert (
                "ZeroDivisionError" in result.error
                or "division by zero" in result.error
            )

    def test_execute_nonexistent_sketch(self):
        """Test handling of missing sketch files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            sketch_file = project_path / "nonexistent.py"

            cache = PreviewCache(temp_dir)
            engine = PreviewEngine(project_path, cache)

            result = engine.execute_sketch(sketch_file)

            assert not result.success
            assert "not found" in result.error.lower()

    def test_sketch_with_no_output(self):
        """Test handling of sketches that don't generate output files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            sketch_file = project_path / "no_output_sketch.py"
            sketch_file.write_text(
                """
# This sketch doesn't create any output
print("Hello, world!")
"""
            )

            cache = PreviewCache(temp_dir)
            engine = PreviewEngine(project_path, cache)

            result = engine.execute_sketch(sketch_file)

            # Should still succeed but with no preview
            assert result.success
            assert result.preview_url is None
            assert result.preview_path is None
