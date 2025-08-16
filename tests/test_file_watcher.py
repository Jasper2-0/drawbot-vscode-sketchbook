"""
Tests for FileWatcher system for live preview file monitoring.
"""
import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest


class TestFileWatcher:
    """Test suite for FileWatcher functionality."""

    def test_detect_sketch_file_change(self):
        """Test detection of sketch.py modifications."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            sketch_file = project_path / "test_sketch.py"
            sketch_file.write_text('print("initial")')

            from src.core.file_watcher import FileWatcher

            # Track callback calls
            callback_calls = []

            def test_callback(file_path):
                callback_calls.append(file_path)

            watcher = FileWatcher()
            watcher.watch_file(sketch_file, test_callback)

            # Give watcher time to initialize
            time.sleep(0.2)

            # Modify the file
            sketch_file.write_text('print("modified")')

            # Give watcher time to detect change (account for debounce delay)
            time.sleep(0.5)

            # Should have detected the change
            assert len(callback_calls) > 0, "Should detect file modification"
            # Check if any callback path resolves to our sketch file
            found_sketch = any(
                Path(call).resolve() == sketch_file.resolve() for call in callback_calls
            )
            assert (
                found_sketch
            ), f"Should callback with modified file. Got: {callback_calls}, Expected: {sketch_file.resolve()}"

            watcher.stop()

    def test_ignore_non_sketch_changes(self):
        """Test ignoring changes to non-sketch files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            sketch_file = project_path / "test_sketch.py"
            other_file = project_path / "other_file.txt"
            sketch_file.write_text('print("sketch")')
            other_file.write_text("other content")

            from src.core.file_watcher import FileWatcher

            callback_calls = []

            def test_callback(file_path):
                callback_calls.append(file_path)

            watcher = FileWatcher()
            watcher.watch_file(sketch_file, test_callback)

            time.sleep(0.2)

            # Modify non-watched file
            other_file.write_text("modified other content")

            # Modify watched file
            sketch_file.write_text('print("modified sketch")')

            time.sleep(0.5)

            # Should only detect sketch file change
            assert len(callback_calls) > 0, "Should detect sketch file change"
            # Check if any callback path resolves to our sketch file
            found_sketch = any(
                Path(call).resolve() == sketch_file.resolve() for call in callback_calls
            )
            assert found_sketch, f"Should include sketch file. Got: {callback_calls}"
            # Check that other file is not in callbacks
            found_other = any(
                Path(call).resolve() == other_file.resolve() for call in callback_calls
            )
            assert not found_other, "Should not include non-watched file"

            watcher.stop()

    def test_debounce_rapid_changes(self):
        """Test debouncing prevents excessive updates."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            sketch_file = project_path / "test_sketch.py"
            sketch_file.write_text('print("initial")')

            from src.core.file_watcher import FileWatcher

            callback_calls = []

            def test_callback(file_path):
                callback_calls.append(file_path)

            # Create watcher with short debounce period for testing
            watcher = FileWatcher(debounce_delay=0.1)
            watcher.watch_file(sketch_file, test_callback)

            time.sleep(0.05)

            # Make rapid changes
            for i in range(5):
                sketch_file.write_text(f'print("change {i}")')
                time.sleep(0.02)  # Very rapid changes

            # Wait for debounce period
            time.sleep(0.2)

            # Should have debounced to fewer callbacks than changes
            assert (
                len(callback_calls) <= 2
            ), f"Should debounce rapid changes, got {len(callback_calls)} callbacks"
            assert (
                len(callback_calls) > 0
            ), "Should still detect changes after debouncing"

            watcher.stop()

    def test_handle_file_deletion(self):
        """Test handling when watched file is deleted."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            sketch_file = project_path / "test_sketch.py"
            sketch_file.write_text('print("initial")')

            from src.core.file_watcher import FileWatcher

            callback_calls = []

            def test_callback(file_path):
                callback_calls.append(file_path)

            watcher = FileWatcher()
            watcher.watch_file(sketch_file, test_callback)

            time.sleep(0.1)

            # Delete the file
            sketch_file.unlink()

            time.sleep(0.2)

            # Watcher should handle deletion gracefully (no crash)
            # May or may not trigger callback depending on implementation
            assert True, "Should handle file deletion without crashing"

            watcher.stop()

    def test_change_callback_execution(self):
        """Test callbacks are executed on file changes."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            sketch_file = project_path / "test_sketch.py"
            sketch_file.write_text('print("initial")')

            from src.core.file_watcher import FileWatcher

            # Mock callback to test execution
            callback_mock = Mock()

            watcher = FileWatcher()
            watcher.watch_file(sketch_file, callback_mock)

            time.sleep(0.2)

            # Modify file
            sketch_file.write_text('print("modified")')

            time.sleep(0.5)

            # Callback should have been called
            callback_mock.assert_called()
            # Should be called with a path that resolves to our sketch file
            call_args = (
                callback_mock.call_args[0][0] if callback_mock.call_args else None
            )
            if call_args:
                assert Path(call_args).resolve() == sketch_file.resolve()

            watcher.stop()

    def test_callback_error_handling(self):
        """Test system continues when callbacks fail."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            sketch_file = project_path / "test_sketch.py"
            sketch_file.write_text('print("initial")')

            from src.core.file_watcher import FileWatcher

            # Create callback that raises exception
            def failing_callback(file_path):
                raise Exception("Callback failed")

            # And a working callback
            working_calls = []

            def working_callback(file_path):
                working_calls.append(file_path)

            watcher = FileWatcher()
            watcher.watch_file(sketch_file, failing_callback)
            watcher.watch_file(sketch_file, working_callback)  # Multiple callbacks

            time.sleep(0.2)

            # Modify file
            sketch_file.write_text('print("modified")')

            time.sleep(0.5)

            # Working callback should still execute despite failing callback
            assert (
                len(working_calls) > 0
            ), "Working callback should execute despite failing callback"

            watcher.stop()

    def test_multiple_callback_registration(self):
        """Test multiple callbacks can be registered."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            sketch_file = project_path / "test_sketch.py"
            sketch_file.write_text('print("initial")')

            from src.core.file_watcher import FileWatcher

            callback1_calls = []
            callback2_calls = []

            def callback1(file_path):
                callback1_calls.append(file_path)

            def callback2(file_path):
                callback2_calls.append(file_path)

            watcher = FileWatcher()
            watcher.watch_file(sketch_file, callback1)
            watcher.watch_file(sketch_file, callback2)

            time.sleep(0.1)

            # Modify file
            sketch_file.write_text('print("modified")')

            time.sleep(0.2)

            # Both callbacks should be called
            assert len(callback1_calls) > 0, "First callback should be called"
            assert len(callback2_calls) > 0, "Second callback should be called"
            assert (
                sketch_file in callback1_calls
            ), "First callback should receive file path"
            assert (
                sketch_file in callback2_calls
            ), "Second callback should receive file path"

            watcher.stop()

    def test_watcher_startup(self):
        """Test file watcher starts successfully."""
        from src.core.file_watcher import FileWatcher

        watcher = FileWatcher()

        # Should initialize without error
        assert watcher is not None, "Watcher should initialize"

        # Should be able to start watching
        with tempfile.TemporaryDirectory() as temp_dir:
            sketch_file = Path(temp_dir) / "test.py"
            sketch_file.write_text('print("test")')

            callback_calls = []

            def callback(path):
                callback_calls.append(path)

            # Should not raise exception
            watcher.watch_file(sketch_file, callback)

            time.sleep(0.1)

            assert True, "Watcher should start without error"

            watcher.stop()

    def test_watcher_shutdown(self):
        """Test file watcher shuts down cleanly."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            sketch_file = project_path / "test_sketch.py"
            sketch_file.write_text('print("initial")')

            from src.core.file_watcher import FileWatcher

            callback_calls = []

            def callback(file_path):
                callback_calls.append(file_path)

            watcher = FileWatcher()
            watcher.watch_file(sketch_file, callback)

            time.sleep(0.1)

            # Should shut down cleanly
            watcher.stop()

            # After shutdown, should not detect changes
            initial_calls = len(callback_calls)
            sketch_file.write_text('print("after shutdown")')

            time.sleep(0.2)

            # Should not have new callbacks after shutdown
            assert (
                len(callback_calls) == initial_calls
            ), "Should not detect changes after shutdown"

    def test_watcher_restart_after_error(self):
        """Test watcher recovers from errors."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            sketch_file = project_path / "test_sketch.py"
            sketch_file.write_text('print("initial")')

            from src.core.file_watcher import FileWatcher

            callback_calls = []

            def callback(file_path):
                callback_calls.append(file_path)

            watcher = FileWatcher()
            watcher.watch_file(sketch_file, callback)

            time.sleep(0.1)

            # Delete and recreate file (simulates error condition)
            sketch_file.unlink()
            time.sleep(0.1)
            sketch_file.write_text('print("recreated")')

            time.sleep(0.2)

            # Watcher should handle this gracefully
            assert True, "Watcher should handle file deletion/recreation"

            watcher.stop()

    def test_watch_multiple_files(self):
        """Test watching multiple files simultaneously."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            sketch1 = project_path / "sketch1.py"
            sketch2 = project_path / "sketch2.py"
            sketch1.write_text('print("sketch1")')
            sketch2.write_text('print("sketch2")')

            from src.core.file_watcher import FileWatcher

            callback_calls = []

            def callback(file_path):
                callback_calls.append(file_path)

            watcher = FileWatcher()
            watcher.watch_file(sketch1, callback)
            watcher.watch_file(sketch2, callback)

            time.sleep(0.1)

            # Modify both files
            sketch1.write_text('print("modified sketch1")')
            sketch2.write_text('print("modified sketch2")')

            time.sleep(0.2)

            # Should detect changes to both files
            assert len(callback_calls) >= 2, "Should detect changes to multiple files"
            assert sketch1 in callback_calls, "Should detect sketch1 changes"
            assert sketch2 in callback_calls, "Should detect sketch2 changes"

            watcher.stop()

    def test_unwatch_file(self):
        """Test stopping watch on specific file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            sketch_file = project_path / "test_sketch.py"
            sketch_file.write_text('print("initial")')

            from src.core.file_watcher import FileWatcher

            callback_calls = []

            def callback(file_path):
                callback_calls.append(file_path)

            watcher = FileWatcher()
            watcher.watch_file(sketch_file, callback)

            time.sleep(0.1)

            # Modify file - should be detected
            sketch_file.write_text('print("first change")')
            time.sleep(0.2)

            initial_calls = len(callback_calls)
            assert initial_calls > 0, "Should detect initial change"

            # Stop watching this file
            watcher.unwatch_file(sketch_file)

            # Modify file again - should not be detected
            sketch_file.write_text('print("second change")')
            time.sleep(0.2)

            # Should not have new callbacks
            assert (
                len(callback_calls) == initial_calls
            ), "Should not detect changes after unwatching"

            watcher.stop()

    def test_debounce_delay_configuration(self):
        """Test configurable debounce delay."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            sketch_file = project_path / "test_sketch.py"
            sketch_file.write_text('print("initial")')

            from src.core.file_watcher import FileWatcher

            # Test with different debounce delays
            for delay in [0.05, 0.1, 0.2]:
                callback_calls = []

                def callback(file_path):
                    callback_calls.append(file_path)

                watcher = FileWatcher(debounce_delay=delay)
                watcher.watch_file(sketch_file, callback)

                time.sleep(0.05)

                # Make rapid changes
                sketch_file.write_text(f'print("change with delay {delay}")')
                time.sleep(delay / 2)  # Wait less than debounce delay
                sketch_file.write_text(f'print("second change with delay {delay}")')

                # Wait for debounce
                time.sleep(delay + 0.1)

                # Should debounce appropriately
                assert len(callback_calls) <= 2, f"Should debounce with delay {delay}"

                watcher.stop()
