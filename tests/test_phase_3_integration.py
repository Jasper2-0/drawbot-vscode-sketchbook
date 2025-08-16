"""
Phase 3 Integration Tests - End-to-end testing of live preview with WebSockets.
"""
import asyncio
import json
import tempfile
import time
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from src.server.file_watch_integration import FileWatchIntegration
from src.server.live_preview_manager import LivePreviewManager
from src.server.live_preview_server import LivePreviewServer, create_app


class TestPhase3Integration:
    """Integration tests for Phase 3 live preview functionality."""

    @pytest.mark.asyncio
    async def test_websocket_connection_and_message_flow(self):
        """Test WebSocket connection and basic message handling."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            cache_dir = project_path / "cache"

            # Create test sketch
            sketch_file = project_path / "ws_test.py"
            sketch_file.write_text(
                """
import drawBot as drawbot
drawbot.size(200, 200)
drawbot.fill(1, 0, 0)
drawbot.rect(50, 50, 100, 100)
drawbot.saveImage("output.png")
"""
            )

            # Initialize server
            server = LivePreviewServer(project_path, cache_dir)
            app = create_app(server)

            # Test WebSocket using TestClient
            with TestClient(app) as client:
                # Use WebSocket context manager
                with client.websocket_connect("/live/ws_test") as websocket:
                    # Should receive connection confirmation
                    data = websocket.receive_json()
                    assert data["type"] == "connection_confirmed"
                    assert data["sketch"] == "ws_test"

                    # Send ping message
                    websocket.send_json({"type": "ping"})

                    # Should receive pong
                    response = websocket.receive_json()
                    assert response["type"] == "pong"

    @pytest.mark.asyncio
    async def test_live_preview_manager_integration(self):
        """Test LivePreviewManager with real components."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            cache_dir = project_path / "cache"

            # Create test sketch
            sketch_file = project_path / "manager_test.py"
            sketch_file.write_text(
                """
import drawBot as drawbot
drawbot.size(150, 150)
drawbot.fill(0, 1, 0)
drawbot.oval(25, 25, 100, 100)
drawbot.saveImage("output.png")
"""
            )

            # Initialize components
            manager = LivePreviewManager(project_path, cache_dir)

            # Mock WebSocket for testing
            mock_websocket = AsyncMock()
            mock_websocket.client_state.name = "OPEN"

            # Test connection
            await manager.connect_client("manager_test", mock_websocket)

            # Should have active connection
            assert manager.is_watching_sketch("manager_test")

            # Test broadcasting
            await manager.broadcast_to_sketch(
                "manager_test", {"type": "test_message", "content": "Hello from test"}
            )

            # Should have sent message
            mock_websocket.send.assert_called()
            sent_message = json.loads(mock_websocket.send.call_args[0][0])
            assert sent_message["type"] == "test_message"

            # Cleanup
            await manager.disconnect_client("manager_test", mock_websocket)
            await manager.shutdown()

    @pytest.mark.asyncio
    async def test_file_watch_integration_with_preview_manager(self):
        """Test FileWatchIntegration with LivePreviewManager."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            cache_dir = project_path / "cache"

            # Create test sketch
            sketch_file = project_path / "watch_integration_test.py"
            sketch_file.write_text(
                """
import drawBot as drawbot
drawbot.size(100, 100)
drawbot.fill(0.5, 0.5, 0.9)
drawbot.rect(10, 10, 80, 80)
drawbot.saveImage("output.png")
"""
            )

            # Mock preview manager
            mock_manager = AsyncMock()

            # Initialize integration
            integration = FileWatchIntegration(project_path, cache_dir, mock_manager)

            # Start watching
            await integration.start_watching_sketch("watch_integration_test")

            # Verify watching started
            assert integration.is_watching_sketch("watch_integration_test")

            # Modify file
            sketch_file.write_text(
                """
import drawBot as drawbot
drawbot.size(100, 100)
drawbot.fill(0.9, 0.5, 0.5)  # Changed color
drawbot.rect(10, 10, 80, 80)
drawbot.saveImage("output.png")
"""
            )

            # Wait for file change processing
            await asyncio.sleep(0.5)

            # Should have broadcast execution messages
            assert mock_manager.broadcast_to_sketch.call_count >= 1

            # Check for execution started message
            calls = mock_manager.broadcast_to_sketch.call_args_list
            message_types = [call[0][1]["type"] for call in calls]
            assert "execution_started" in message_types

            # Cleanup
            await integration.stop_watching_sketch("watch_integration_test")
            await integration.shutdown()

    @pytest.mark.asyncio
    async def test_complete_live_preview_workflow(self):
        """Test complete workflow: file change → execution → WebSocket broadcast."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            cache_dir = project_path / "cache"

            # Create test sketch
            sketch_file = project_path / "complete_workflow_test.py"
            sketch_file.write_text(
                """
import drawBot as drawbot
drawbot.size(120, 120)
drawbot.fill(1, 0.5, 0)
drawbot.oval(10, 10, 100, 100)
drawbot.saveImage("output.png")
"""
            )

            # Initialize full server
            server = LivePreviewServer(project_path, cache_dir)

            # Mock WebSocket
            mock_websocket = AsyncMock()
            mock_websocket.client_state.name = "OPEN"

            sketch_name = "complete_workflow_test"

            # Connect client (starts file watching)
            await server.preview_manager.connect_client(sketch_name, mock_websocket)
            await server.file_watch_integration.start_watching_sketch(sketch_name)

            # Give system time to initialize
            await asyncio.sleep(0.1)

            # Modify sketch file
            sketch_file.write_text(
                """
import drawBot as drawbot
drawbot.size(120, 120)
drawbot.fill(0, 1, 0.5)  # Changed to green
drawbot.oval(10, 10, 100, 100)
drawbot.saveImage("output.png")
"""
            )

            # Wait for processing
            await asyncio.sleep(0.8)

            # Should have received multiple WebSocket messages
            assert mock_websocket.send.call_count >= 2

            # Parse sent messages
            sent_messages = []
            for call in mock_websocket.send.call_args_list:
                message_str = call[0][0]
                sent_messages.append(json.loads(message_str))

            # Check message flow
            message_types = [msg["type"] for msg in sent_messages]

            # Should include execution flow messages
            assert "connection_confirmed" in message_types
            assert "execution_started" in message_types

            # Should have success or error (but not both for same execution)
            has_success = "preview_updated" in message_types
            has_error = "execution_error" in message_types
            assert has_success or has_error, "Should have either success or error"

            # Cleanup
            await server.preview_manager.disconnect_client(sketch_name, mock_websocket)
            await server.file_watch_integration.stop_watching_sketch(sketch_name)
            await server.preview_manager.shutdown()
            await server.file_watch_integration.shutdown()

    @pytest.mark.asyncio
    async def test_multiple_clients_same_sketch(self):
        """Test multiple WebSocket clients watching same sketch."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            cache_dir = project_path / "cache"

            sketch_file = project_path / "multi_client_test.py"
            sketch_file.write_text(
                """
import drawBot as drawbot
drawbot.size(80, 80)
drawbot.fill(0.8, 0.2, 0.8)
drawbot.rect(10, 10, 60, 60)
drawbot.saveImage("output.png")
"""
            )

            server = LivePreviewServer(project_path, cache_dir)

            # Create multiple mock WebSockets
            mock_ws1 = AsyncMock()
            mock_ws1.client_state.name = "OPEN"
            mock_ws2 = AsyncMock()
            mock_ws2.client_state.name = "OPEN"
            mock_ws3 = AsyncMock()
            mock_ws3.client_state.name = "OPEN"

            sketch_name = "multi_client_test"

            # Connect all clients
            await server.preview_manager.connect_client(sketch_name, mock_ws1)
            await server.preview_manager.connect_client(sketch_name, mock_ws2)
            await server.preview_manager.connect_client(sketch_name, mock_ws3)

            # Start watching
            await server.file_watch_integration.start_watching_sketch(sketch_name)

            await asyncio.sleep(0.05)

            # Modify file
            sketch_file.write_text(sketch_file.read_text() + "\n# trigger change")

            await asyncio.sleep(0.5)

            # All clients should receive messages
            assert mock_ws1.send.call_count >= 1
            assert mock_ws2.send.call_count >= 1
            assert mock_ws3.send.call_count >= 1

            # Messages should be identical
            ws1_messages = [
                json.loads(call[0][0]) for call in mock_ws1.send.call_args_list
            ]
            ws2_messages = [
                json.loads(call[0][0]) for call in mock_ws2.send.call_args_list
            ]

            # Should have same number of messages
            assert len(ws1_messages) == len(ws2_messages)

            # Cleanup
            await server.preview_manager.disconnect_client(sketch_name, mock_ws1)
            await server.preview_manager.disconnect_client(sketch_name, mock_ws2)
            await server.preview_manager.disconnect_client(sketch_name, mock_ws3)
            await server.file_watch_integration.stop_watching_sketch(sketch_name)
            await server.preview_manager.shutdown()
            await server.file_watch_integration.shutdown()

    @pytest.mark.asyncio
    async def test_error_handling_in_live_preview(self):
        """Test error handling and broadcasting in live preview."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            cache_dir = project_path / "cache"

            # Create sketch with syntax error
            sketch_file = project_path / "error_test.py"
            sketch_file.write_text(
                """
import drawBot as drawbot
drawbot.size(100, 100)
drawbot.rect(10, 10, 50, 50
# Missing closing parenthesis
"""
            )

            server = LivePreviewServer(project_path, cache_dir)

            mock_websocket = AsyncMock()
            mock_websocket.client_state.name = "OPEN"

            sketch_name = "error_test"

            # Connect and start watching
            await server.preview_manager.connect_client(sketch_name, mock_websocket)
            await server.file_watch_integration.start_watching_sketch(sketch_name)

            await asyncio.sleep(0.05)

            # Trigger file change (already has error)
            sketch_file.write_text(sketch_file.read_text() + "\n# change")

            await asyncio.sleep(0.5)

            # Should receive error message
            assert mock_websocket.send.call_count >= 1

            # Check for error message
            sent_messages = []
            for call in mock_websocket.send.call_args_list:
                sent_messages.append(json.loads(call[0][0]))

            message_types = [msg["type"] for msg in sent_messages]
            assert "execution_error" in message_types

            # Find error message
            error_messages = [
                msg for msg in sent_messages if msg["type"] == "execution_error"
            ]
            assert len(error_messages) > 0
            assert "error" in error_messages[0]

            # Cleanup
            await server.preview_manager.disconnect_client(sketch_name, mock_websocket)
            await server.file_watch_integration.stop_watching_sketch(sketch_name)
            await server.preview_manager.shutdown()
            await server.file_watch_integration.shutdown()

    @pytest.mark.asyncio
    async def test_websocket_disconnection_cleanup(self):
        """Test proper cleanup when WebSocket clients disconnect."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            cache_dir = project_path / "cache"

            sketch_file = project_path / "disconnect_test.py"
            sketch_file.write_text("print('test')")

            server = LivePreviewServer(project_path, cache_dir)

            mock_websocket = AsyncMock()
            mock_websocket.client_state.name = "OPEN"

            sketch_name = "disconnect_test"

            # Connect client
            await server.preview_manager.connect_client(sketch_name, mock_websocket)
            await server.file_watch_integration.start_watching_sketch(sketch_name)

            # Verify connection
            assert server.preview_manager.is_watching_sketch(sketch_name)
            assert server.file_watch_integration.is_watching_sketch(sketch_name)

            # Disconnect client
            await server.preview_manager.disconnect_client(sketch_name, mock_websocket)

            # Should clean up file watching when no clients remain
            assert not server.preview_manager.is_watching_sketch(sketch_name)

            # Cleanup
            await server.preview_manager.shutdown()
            await server.file_watch_integration.shutdown()

    @pytest.mark.asyncio
    async def test_server_shutdown_handling(self):
        """Test graceful shutdown of live preview components."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            cache_dir = project_path / "cache"

            sketch_file = project_path / "shutdown_test.py"
            sketch_file.write_text("print('shutdown test')")

            server = LivePreviewServer(project_path, cache_dir)

            mock_websocket = AsyncMock()
            mock_websocket.client_state.name = "OPEN"

            # Set up active connections
            await server.preview_manager.connect_client("shutdown_test", mock_websocket)
            await server.file_watch_integration.start_watching_sketch("shutdown_test")

            # Verify active state
            assert len(server.preview_manager.get_watched_sketches()) > 0
            assert len(server.file_watch_integration.get_watched_sketches()) > 0

            # Shutdown
            await server.preview_manager.shutdown()
            await server.file_watch_integration.shutdown()

            # Should clean up all resources
            assert len(server.preview_manager.get_watched_sketches()) == 0
            assert len(server.file_watch_integration.get_watched_sketches()) == 0

    def test_phase_3_api_endpoints(self):
        """Test new API endpoints added in Phase 3."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            cache_dir = project_path / "cache"

            sketch_file = project_path / "api_test.py"
            sketch_file.write_text("print('api test')")

            server = LivePreviewServer(project_path, cache_dir)
            app = create_app(server)
            client = TestClient(app)

            # Test live stats endpoint
            response = client.get("/live-stats")
            assert response.status_code == 200

            data = response.json()
            assert "connections" in data
            assert "file_watching" in data
            assert "watched_sketches" in data["file_watching"]
            assert "total_watched" in data["file_watching"]
