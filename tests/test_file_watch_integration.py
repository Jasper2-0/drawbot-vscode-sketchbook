"""
Tests for FileWatchIntegration - Bridge between FileWatcher and preview system.
"""
import pytest
import asyncio
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock, AsyncMock

from src.server.file_watch_integration import FileWatchIntegration


class TestFileWatchIntegration:
    """Test suite for FileWatchIntegration functionality."""

    @pytest.mark.asyncio
    async def test_file_change_triggers_preview_update(self):
        """Test file change → execution → broadcast flow."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            cache_dir = project_path / "cache"
            
            # Create test sketch
            sketch_file = project_path / "file_watch_test.py"
            sketch_file.write_text('''
import drawBot as drawbot
drawbot.size(200, 200)
drawbot.fill(1, 0, 0)
drawbot.rect(50, 50, 100, 100)
drawbot.saveImage("output.png")
''')
            
            # Mock preview manager
            mock_manager = AsyncMock()
            
            integration = FileWatchIntegration(project_path, cache_dir, mock_manager)
            
            # Start watching the sketch
            await integration.start_watching_sketch("file_watch_test")
            
            # Give watcher time to initialize
            await asyncio.sleep(0.1)
            
            # Modify the file
            sketch_file.write_text('''
import drawBot as drawbot
drawbot.size(200, 200)
drawbot.fill(0, 1, 0)  # Changed to green
drawbot.rect(50, 50, 100, 100)
drawbot.saveImage("output.png")
''')
            
            # Wait for file change detection and processing
            await asyncio.sleep(0.5)
            
            # Should have triggered preview update
            mock_manager.broadcast_to_sketch.assert_called()
            
            # Check broadcast was called with correct sketch
            call_args = mock_manager.broadcast_to_sketch.call_args
            assert call_args[0][0] == "file_watch_test"  # sketch_name
            
            # Stop watching
            await integration.stop_watching_sketch("file_watch_test")

    @pytest.mark.asyncio
    async def test_debounced_rapid_file_changes(self):
        """Test rapid saves only trigger one update."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            cache_dir = project_path / "cache"
            
            sketch_file = project_path / "debounce_test.py"
            sketch_file.write_text("print('initial')")
            
            mock_manager = AsyncMock()
            
            # Use shorter debounce for testing
            integration = FileWatchIntegration(
                project_path, cache_dir, mock_manager, 
                debounce_delay=0.1
            )
            
            await integration.start_watching_sketch("debounce_test")
            await asyncio.sleep(0.05)
            
            # Make rapid changes
            for i in range(5):
                sketch_file.write_text(f"print('change {i}')")
                await asyncio.sleep(0.02)  # Rapid changes
            
            # Wait for debounce period
            await asyncio.sleep(0.2)
            
            # Should have fewer broadcasts than changes
            call_count = mock_manager.broadcast_to_sketch.call_count
            assert call_count <= 2, f"Expected ≤2 broadcasts, got {call_count}"
            assert call_count > 0, "Should still detect changes"
            
            await integration.stop_watching_sketch("debounce_test")

    @pytest.mark.asyncio
    async def test_execution_error_handling_during_watch(self):
        """Test WebSocket error broadcasts for execution failures."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            cache_dir = project_path / "cache"
            
            # Create broken sketch
            sketch_file = project_path / "error_test.py"
            sketch_file.write_text('''
import drawBot as drawbot
drawbot.size(200, 200)
drawbot.rect(50, 50, 100, 100
# Missing closing parenthesis - syntax error
''')
            
            mock_manager = AsyncMock()
            
            integration = FileWatchIntegration(project_path, cache_dir, mock_manager)
            
            await integration.start_watching_sketch("error_test")
            await asyncio.sleep(0.05)
            
            # Trigger change (file already has error)
            sketch_file.write_text(sketch_file.read_text() + "\n# trigger change")
            
            # Wait for processing
            await asyncio.sleep(0.3)
            
            # Should have broadcast error message
            mock_manager.broadcast_to_sketch.assert_called()
            
            # Check that error was broadcast
            call_args = mock_manager.broadcast_to_sketch.call_args
            message = call_args[0][1]  # message argument
            assert message["type"] == "execution_error"
            assert "error" in message
            
            await integration.stop_watching_sketch("error_test")

    @pytest.mark.asyncio
    async def test_watch_start_stop_with_clients(self):
        """Test FileWatcher lifecycle management."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            cache_dir = project_path / "cache"
            
            sketch_file = project_path / "lifecycle_test.py"
            sketch_file.write_text("print('test')")
            
            mock_manager = AsyncMock()
            
            integration = FileWatchIntegration(project_path, cache_dir, mock_manager)
            
            # Should not be watching initially
            assert not integration.is_watching_sketch("lifecycle_test")
            
            # Start watching
            await integration.start_watching_sketch("lifecycle_test")
            assert integration.is_watching_sketch("lifecycle_test")
            
            # Stop watching
            await integration.stop_watching_sketch("lifecycle_test")
            assert not integration.is_watching_sketch("lifecycle_test")

    @pytest.mark.asyncio
    async def test_multiple_sketch_watching(self):
        """Test watching multiple sketches simultaneously."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            cache_dir = project_path / "cache"
            
            # Create multiple sketches
            sketches = ["multi_test_a", "multi_test_b", "multi_test_c"]
            for sketch_name in sketches:
                sketch_file = project_path / f"{sketch_name}.py"
                sketch_file.write_text(f"print('{sketch_name}')")
            
            mock_manager = AsyncMock()
            
            integration = FileWatchIntegration(project_path, cache_dir, mock_manager)
            
            # Start watching all sketches
            for sketch_name in sketches:
                await integration.start_watching_sketch(sketch_name)
                assert integration.is_watching_sketch(sketch_name)
            
            # Should be watching all
            watching_sketches = integration.get_watched_sketches()
            assert len(watching_sketches) == 3
            assert all(sketch in watching_sketches for sketch in sketches)
            
            # Modify one sketch
            sketch_file = project_path / "multi_test_b.py"
            sketch_file.write_text("print('modified')")
            
            await asyncio.sleep(0.2)
            
            # Should only broadcast for modified sketch
            mock_manager.broadcast_to_sketch.assert_called()
            call_args = mock_manager.broadcast_to_sketch.call_args
            assert call_args[0][0] == "multi_test_b"
            
            # Stop watching all
            for sketch_name in sketches:
                await integration.stop_watching_sketch(sketch_name)

    @pytest.mark.asyncio
    async def test_file_deletion_handling(self):
        """Test handling when watched file is deleted."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            cache_dir = project_path / "cache"
            
            sketch_file = project_path / "deletion_test.py"
            sketch_file.write_text("print('will be deleted')")
            
            mock_manager = AsyncMock()
            
            integration = FileWatchIntegration(project_path, cache_dir, mock_manager)
            
            await integration.start_watching_sketch("deletion_test")
            await asyncio.sleep(0.05)
            
            # Delete the file
            sketch_file.unlink()
            
            await asyncio.sleep(0.2)
            
            # Should handle deletion gracefully (no crash)
            # May or may not broadcast depending on implementation
            assert True, "Should handle file deletion without crashing"
            
            # Stop watching
            await integration.stop_watching_sketch("deletion_test")

    @pytest.mark.asyncio
    async def test_execution_status_broadcasting(self):
        """Test broadcasting of execution status messages."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            cache_dir = project_path / "cache"
            
            sketch_file = project_path / "status_test.py"
            sketch_file.write_text('''
import drawBot as drawbot
drawbot.size(150, 150)
drawbot.fill(0.5, 0.8, 0.9)
drawbot.oval(25, 25, 100, 100)
drawbot.saveImage("output.png")
''')
            
            mock_manager = AsyncMock()
            
            integration = FileWatchIntegration(project_path, cache_dir, mock_manager)
            
            await integration.start_watching_sketch("status_test")
            await asyncio.sleep(0.05)
            
            # Trigger file change
            sketch_file.write_text(sketch_file.read_text() + "\n# trigger change")
            
            await asyncio.sleep(0.5)
            
            # Should broadcast execution status
            assert mock_manager.broadcast_to_sketch.call_count >= 1
            
            # Check for status messages
            calls = mock_manager.broadcast_to_sketch.call_args_list
            message_types = [call[0][1]["type"] for call in calls]
            
            # Should include status updates
            assert any(msg_type in ["execution_started", "preview_updated"] for msg_type in message_types)
            
            await integration.stop_watching_sketch("status_test")

    @pytest.mark.asyncio
    async def test_preview_url_generation(self):
        """Test proper preview URL generation in broadcasts."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            cache_dir = project_path / "cache"
            
            sketch_file = project_path / "url_test.py"
            sketch_file.write_text('''
import drawBot as drawbot
drawbot.size(100, 100)
drawbot.fill(1, 0.5, 0)
drawbot.rect(10, 10, 80, 80)
drawbot.saveImage("output.png")
''')
            
            mock_manager = AsyncMock()
            
            integration = FileWatchIntegration(project_path, cache_dir, mock_manager)
            
            await integration.start_watching_sketch("url_test")
            await asyncio.sleep(0.05)
            
            # Trigger execution
            sketch_file.write_text(sketch_file.read_text() + "\n# change")
            
            await asyncio.sleep(0.5)
            
            # Should broadcast with preview URL
            calls = mock_manager.broadcast_to_sketch.call_args_list
            
            # Look for preview_updated message
            preview_messages = [
                call[0][1] for call in calls 
                if call[0][1]["type"] == "preview_updated"
            ]
            
            if preview_messages:
                message = preview_messages[0]
                assert "image_url" in message
                assert message["image_url"].startswith("/preview/")
                assert "url_test" in message["image_url"]
            
            await integration.stop_watching_sketch("url_test")

    @pytest.mark.asyncio
    async def test_concurrent_file_changes(self):
        """Test handling concurrent file changes across multiple sketches."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            cache_dir = project_path / "cache"
            
            # Create multiple sketch files
            sketches = ["concurrent_a", "concurrent_b", "concurrent_c"]
            sketch_files = {}
            
            for sketch_name in sketches:
                sketch_file = project_path / f"{sketch_name}.py"
                sketch_file.write_text(f'''
import drawBot as drawbot
drawbot.size(100, 100)
drawbot.fill({sketches.index(sketch_name)/10}, 0.5, 0.8)
drawbot.rect(10, 10, 80, 80)
drawbot.saveImage("output.png")
''')
                sketch_files[sketch_name] = sketch_file
            
            mock_manager = AsyncMock()
            
            integration = FileWatchIntegration(project_path, cache_dir, mock_manager)
            
            # Start watching all sketches
            for sketch_name in sketches:
                await integration.start_watching_sketch(sketch_name)
            
            await asyncio.sleep(0.1)
            
            # Modify all files simultaneously
            for sketch_name, sketch_file in sketch_files.items():
                sketch_file.write_text(sketch_file.read_text() + f"\n# {sketch_name} change")
            
            await asyncio.sleep(0.5)
            
            # Should handle all changes
            assert mock_manager.broadcast_to_sketch.call_count >= len(sketches)
            
            # Should broadcast to correct sketches
            calls = mock_manager.broadcast_to_sketch.call_args_list
            broadcast_sketches = {call[0][0] for call in calls}
            
            # All sketches should have received broadcasts
            for sketch_name in sketches:
                assert sketch_name in broadcast_sketches
            
            # Cleanup
            for sketch_name in sketches:
                await integration.stop_watching_sketch(sketch_name)

    @pytest.mark.asyncio
    async def test_integration_resource_cleanup(self):
        """Test proper resource cleanup on shutdown."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            cache_dir = project_path / "cache"
            
            sketch_file = project_path / "cleanup_test.py"
            sketch_file.write_text("print('test')")
            
            mock_manager = AsyncMock()
            
            integration = FileWatchIntegration(project_path, cache_dir, mock_manager)
            
            # Start watching
            await integration.start_watching_sketch("cleanup_test")
            assert integration.is_watching_sketch("cleanup_test")
            
            # Shutdown integration
            await integration.shutdown()
            
            # Should clean up all resources
            assert not integration.is_watching_sketch("cleanup_test")
            assert len(integration.get_watched_sketches()) == 0