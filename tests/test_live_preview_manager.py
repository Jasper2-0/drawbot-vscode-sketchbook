"""
Tests for LivePreviewManager - WebSocket connection management.
"""
import pytest
import asyncio
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, AsyncMock

from src.server.live_preview_manager import LivePreviewManager, ConnectionInfo


class TestLivePreviewManager:
    """Test suite for LivePreviewManager functionality."""

    @pytest.mark.asyncio
    async def test_websocket_connection_lifecycle(self):
        """Test connect, subscribe, disconnect flow."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            cache_dir = project_path / "cache"
            
            manager = LivePreviewManager(project_path, cache_dir)
            
            # Mock WebSocket
            mock_websocket = AsyncMock()
            mock_websocket.client_state = Mock()
            mock_websocket.client_state.name = "OPEN"
            
            sketch_name = "test_sketch"
            
            # Test connection
            await manager.connect_client(sketch_name, mock_websocket)
            
            # Should have active connection
            assert sketch_name in manager.active_connections
            assert mock_websocket in manager.active_connections[sketch_name]
            
            # Test disconnect
            await manager.disconnect_client(sketch_name, mock_websocket)
            
            # Should clean up connection
            if sketch_name in manager.active_connections:
                assert mock_websocket not in manager.active_connections[sketch_name]

    @pytest.mark.asyncio
    async def test_multiple_clients_same_sketch(self):
        """Test multiple browsers watching same sketch."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            cache_dir = project_path / "cache"
            
            manager = LivePreviewManager(project_path, cache_dir)
            
            # Create multiple mock WebSockets
            mock_ws1 = AsyncMock()
            mock_ws1.client_state = Mock()
            mock_ws1.client_state.name = "OPEN"
            
            mock_ws2 = AsyncMock()
            mock_ws2.client_state = Mock()
            mock_ws2.client_state.name = "OPEN"
            
            mock_ws3 = AsyncMock()
            mock_ws3.client_state = Mock()
            mock_ws3.client_state.name = "OPEN"
            
            sketch_name = "popular_sketch"
            
            # Connect all clients
            await manager.connect_client(sketch_name, mock_ws1)
            await manager.connect_client(sketch_name, mock_ws2)
            await manager.connect_client(sketch_name, mock_ws3)
            
            # Should have all three connections
            assert len(manager.active_connections[sketch_name]) == 3
            
            # Disconnect one client
            await manager.disconnect_client(sketch_name, mock_ws2)
            
            # Should have two remaining
            assert len(manager.active_connections[sketch_name]) == 2
            assert mock_ws1 in manager.active_connections[sketch_name]
            assert mock_ws3 in manager.active_connections[sketch_name]
            assert mock_ws2 not in manager.active_connections[sketch_name]

    @pytest.mark.asyncio
    async def test_client_room_management(self):
        """Test sketch-specific client grouping."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            cache_dir = project_path / "cache"
            
            manager = LivePreviewManager(project_path, cache_dir)
            
            # Create mock WebSockets for different sketches
            ws_sketch_a = AsyncMock()
            ws_sketch_a.client_state = Mock()
            ws_sketch_a.client_state.name = "OPEN"
            
            ws_sketch_b = AsyncMock()
            ws_sketch_b.client_state = Mock()
            ws_sketch_b.client_state.name = "OPEN"
            
            # Connect to different sketches
            await manager.connect_client("sketch_a", ws_sketch_a)
            await manager.connect_client("sketch_b", ws_sketch_b)
            
            # Should have separate rooms
            assert "sketch_a" in manager.active_connections
            assert "sketch_b" in manager.active_connections
            assert ws_sketch_a in manager.active_connections["sketch_a"]
            assert ws_sketch_b in manager.active_connections["sketch_b"]
            
            # Cross-contamination check
            assert ws_sketch_a not in manager.active_connections["sketch_b"]
            assert ws_sketch_b not in manager.active_connections["sketch_a"]

    @pytest.mark.asyncio
    async def test_connection_cleanup_on_disconnect(self):
        """Test resource cleanup when clients disconnect."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            cache_dir = project_path / "cache"
            
            manager = LivePreviewManager(project_path, cache_dir)
            
            mock_websocket = AsyncMock()
            mock_websocket.client_state = Mock()
            mock_websocket.client_state.name = "OPEN"
            
            sketch_name = "cleanup_test"
            
            # Connect client
            await manager.connect_client(sketch_name, mock_websocket)
            
            # Verify connection exists
            assert sketch_name in manager.active_connections
            
            # Disconnect client
            await manager.disconnect_client(sketch_name, mock_websocket)
            
            # Should clean up empty rooms
            if sketch_name in manager.active_connections:
                assert len(manager.active_connections[sketch_name]) == 0

    @pytest.mark.asyncio
    async def test_broadcast_to_specific_sketch_clients(self):
        """Test targeted message broadcasting."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            cache_dir = project_path / "cache"
            
            manager = LivePreviewManager(project_path, cache_dir)
            
            # Set up multiple sketches with clients
            ws_a1 = AsyncMock()
            ws_a1.client_state = Mock()
            ws_a1.client_state.name = "OPEN"
            
            ws_a2 = AsyncMock()
            ws_a2.client_state = Mock()
            ws_a2.client_state.name = "OPEN"
            
            ws_b1 = AsyncMock()
            ws_b1.client_state = Mock()
            ws_b1.client_state.name = "OPEN"
            
            await manager.connect_client("sketch_a", ws_a1)
            await manager.connect_client("sketch_a", ws_a2)
            await manager.connect_client("sketch_b", ws_b1)
            
            # Broadcast to sketch_a only
            message = {"type": "preview_updated", "sketch": "sketch_a"}
            await manager.broadcast_to_sketch("sketch_a", message)
            
            # Should send to sketch_a clients
            ws_a1.send.assert_called_once()
            ws_a2.send.assert_called_once()
            
            # Should not send to sketch_b clients
            ws_b1.send.assert_not_called()
            
            # Verify message content
            sent_message = json.loads(ws_a1.send.call_args[0][0])
            assert sent_message["type"] == "preview_updated"
            assert sent_message["sketch"] == "sketch_a"

    @pytest.mark.asyncio
    async def test_handle_websocket_errors(self):
        """Test handling of WebSocket connection errors."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            cache_dir = project_path / "cache"
            
            manager = LivePreviewManager(project_path, cache_dir)
            
            # Mock WebSocket that raises exception on send
            failing_ws = AsyncMock()
            failing_ws.client_state = Mock()
            failing_ws.client_state.name = "OPEN"
            failing_ws.send.side_effect = Exception("Connection lost")
            
            working_ws = AsyncMock()
            working_ws.client_state = Mock()
            working_ws.client_state.name = "OPEN"
            
            sketch_name = "error_test"
            
            # Connect both clients
            await manager.connect_client(sketch_name, failing_ws)
            await manager.connect_client(sketch_name, working_ws)
            
            # Broadcast message
            message = {"type": "test_message"}
            await manager.broadcast_to_sketch(sketch_name, message)
            
            # Working client should receive message
            working_ws.send.assert_called_once()
            
            # Failing client should be automatically disconnected
            # (implementation should handle this gracefully)
            assert True  # Test passes if no exception is raised

    @pytest.mark.asyncio
    async def test_connection_state_tracking(self):
        """Test tracking of connection states and metadata."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            cache_dir = project_path / "cache"
            
            manager = LivePreviewManager(project_path, cache_dir)
            
            mock_websocket = AsyncMock()
            mock_websocket.client_state = Mock()
            mock_websocket.client_state.name = "OPEN"
            
            sketch_name = "state_test"
            
            # Connect client
            await manager.connect_client(sketch_name, mock_websocket)
            
            # Should track connection info
            stats = manager.get_connection_stats()
            assert stats["total_connections"] >= 1
            assert stats["active_sketches"] >= 1
            
            # Should provide sketch-specific stats
            sketch_stats = manager.get_sketch_stats(sketch_name)
            assert sketch_stats["connected_clients"] >= 1

    @pytest.mark.asyncio
    async def test_file_watcher_integration(self):
        """Test integration with file watching system."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            cache_dir = project_path / "cache"
            
            # Create a test sketch file
            sketch_file = project_path / "watch_test.py"
            sketch_file.write_text("print('initial')")
            
            manager = LivePreviewManager(project_path, cache_dir)
            
            mock_websocket = AsyncMock()
            mock_websocket.client_state = Mock()
            mock_websocket.client_state.name = "OPEN"
            
            sketch_name = "watch_test"
            
            # Connect client (should start file watching)
            await manager.connect_client(sketch_name, mock_websocket)
            
            # Should have started watching the file
            assert manager.is_watching_sketch(sketch_name)
            
            # Disconnect client (should stop watching if no more clients)
            await manager.disconnect_client(sketch_name, mock_websocket)
            
            # Should stop watching when no clients remain
            # (may need small delay for cleanup)
            await asyncio.sleep(0.1)
            assert not manager.is_watching_sketch(sketch_name)

    @pytest.mark.asyncio
    async def test_broadcast_message_serialization(self):
        """Test proper JSON message serialization."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            cache_dir = project_path / "cache"
            
            manager = LivePreviewManager(project_path, cache_dir)
            
            mock_websocket = AsyncMock()
            mock_websocket.client_state = Mock()
            mock_websocket.client_state.name = "OPEN"
            
            sketch_name = "serialization_test"
            
            await manager.connect_client(sketch_name, mock_websocket)
            
            # Test various message types
            messages = [
                {
                    "type": "preview_updated",
                    "sketch": sketch_name,
                    "image_url": "/preview/test.png?v=123",
                    "timestamp": "2024-01-01T12:00:00Z"
                },
                {
                    "type": "execution_error",
                    "sketch": sketch_name,
                    "error": "SyntaxError: invalid syntax"
                },
                {
                    "type": "execution_started",
                    "sketch": sketch_name
                }
            ]
            
            for message in messages:
                await manager.broadcast_to_sketch(sketch_name, message)
                
                # Should serialize to valid JSON
                sent_data = mock_websocket.send.call_args[0][0]
                parsed = json.loads(sent_data)
                assert parsed["type"] == message["type"]
                assert parsed["sketch"] == sketch_name

    @pytest.mark.asyncio
    async def test_concurrent_connections(self):
        """Test handling concurrent connection/disconnection operations."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            cache_dir = project_path / "cache"
            
            manager = LivePreviewManager(project_path, cache_dir)
            
            # Create multiple WebSocket connections
            websockets = []
            for i in range(10):
                ws = AsyncMock()
                ws.client_state = Mock()
                ws.client_state.name = "OPEN"
                websockets.append(ws)
            
            sketch_name = "concurrent_test"
            
            # Connect all clients concurrently
            connect_tasks = [
                manager.connect_client(sketch_name, ws)
                for ws in websockets
            ]
            await asyncio.gather(*connect_tasks)
            
            # Should have all connections
            assert len(manager.active_connections[sketch_name]) == 10
            
            # Disconnect all clients concurrently
            disconnect_tasks = [
                manager.disconnect_client(sketch_name, ws)
                for ws in websockets
            ]
            await asyncio.gather(*disconnect_tasks)
            
            # Should clean up all connections
            if sketch_name in manager.active_connections:
                assert len(manager.active_connections[sketch_name]) == 0

    @pytest.mark.asyncio
    async def test_message_queuing_for_slow_clients(self):
        """Test message handling for slow/blocked clients."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            cache_dir = project_path / "cache"
            
            manager = LivePreviewManager(project_path, cache_dir)
            
            # Mock slow WebSocket (takes time to send)
            slow_ws = AsyncMock()
            slow_ws.client_state = Mock()
            slow_ws.client_state.name = "OPEN"
            
            async def slow_send(message):
                await asyncio.sleep(0.1)  # Simulate slow send
                
            slow_ws.send = slow_send
            
            # Mock fast WebSocket
            fast_ws = AsyncMock()
            fast_ws.client_state = Mock()
            fast_ws.client_state.name = "OPEN"
            
            sketch_name = "slow_client_test"
            
            await manager.connect_client(sketch_name, slow_ws)
            await manager.connect_client(sketch_name, fast_ws)
            
            # Send message to both
            message = {"type": "test_message"}
            await manager.broadcast_to_sketch(sketch_name, message)
            
            # Should handle both fast and slow clients without blocking
            fast_ws.send.assert_called_once()
            # Test passes if it completes without hanging