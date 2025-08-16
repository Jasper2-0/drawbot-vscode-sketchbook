"""
LivePreviewManager - WebSocket connection management for live preview.
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from fastapi import WebSocket, WebSocketDisconnect
from websockets.exceptions import ConnectionClosed

from ..core.preview_cache import PreviewCache


@dataclass
class ConnectionInfo:
    """Information about a WebSocket connection."""

    websocket: WebSocket
    sketch_name: str
    connected_at: datetime
    last_ping: Optional[datetime] = None


class LivePreviewManager:
    """Manages WebSocket connections and real-time preview updates."""

    def __init__(self, project_path: Path, cache_dir: Path):
        """Initialize live preview manager.

        Args:
            project_path: Path to project directory
            cache_dir: Path to preview cache directory
        """
        self.project_path = Path(project_path)
        self.cache_dir = Path(cache_dir)

        # WebSocket connection management
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self.connection_info: Dict[WebSocket, ConnectionInfo] = {}

        # Connection statistics
        self.total_connections = 0
        self.connection_start_time = time.time()

        # Logging
        self.logger = logging.getLogger(__name__)

        # Initialize cache for preview metadata
        self.cache = PreviewCache(cache_dir)

    async def connect_client(self, sketch_name: str, websocket: WebSocket):
        """Connect a client to a sketch room.

        Args:
            sketch_name: Name of sketch to watch
            websocket: WebSocket connection
        """
        try:
            # Accept the WebSocket connection
            await websocket.accept()

            # Add to active connections
            if sketch_name not in self.active_connections:
                self.active_connections[sketch_name] = []

            self.active_connections[sketch_name].append(websocket)

            # Store connection info
            self.connection_info[websocket] = ConnectionInfo(
                websocket=websocket,
                sketch_name=sketch_name,
                connected_at=datetime.now(),
            )

            self.total_connections += 1

            self.logger.info(
                f"Client connected to sketch '{sketch_name}'. "
                f"Total clients for sketch: {len(self.active_connections[sketch_name])}"
            )

            # Send connection confirmation
            await self._send_to_client(
                websocket,
                {
                    "type": "connection_confirmed",
                    "sketch": sketch_name,
                    "timestamp": datetime.now().isoformat(),
                },
            )

            # Send current preview if available
            current_preview = self.cache.get_current_preview(sketch_name)
            self.logger.debug(
                f"Current preview: {current_preview}, type: {type(current_preview)}"
            )
            if current_preview:
                self.logger.debug(
                    f"Sending preview with file_path: {current_preview.file_path}"
                )
                await self._send_to_client(
                    websocket,
                    {
                        "type": "preview_updated",
                        "sketch": sketch_name,
                        "image_url": f"/preview/{current_preview.file_path.name}?v={current_preview.version}",
                        "status": "success",
                        "timestamp": current_preview.created_at.isoformat(),
                    },
                )

        except Exception as e:
            import traceback

            self.logger.error(f"Error connecting client to sketch '{sketch_name}': {e}")
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            await self._cleanup_connection(websocket)

    async def disconnect_client(self, sketch_name: str, websocket: WebSocket):
        """Disconnect a client from a sketch room.

        Args:
            sketch_name: Name of sketch
            websocket: WebSocket connection to disconnect
        """
        await self._cleanup_connection(websocket)

        self.logger.info(
            f"Client disconnected from sketch '{sketch_name}'. "
            f"Remaining clients: {len(self.active_connections.get(sketch_name, []))}"
        )

    async def _cleanup_connection(self, websocket: WebSocket):
        """Clean up a WebSocket connection.

        Args:
            websocket: WebSocket to clean up
        """
        # Remove from connection info
        if websocket in self.connection_info:
            connection_info = self.connection_info[websocket]
            self.logger.debug(f"Connection info type: {type(connection_info)}")
            self.logger.debug(f"Connection info value: {connection_info}")
            if hasattr(connection_info, "sketch_name"):
                sketch_name = connection_info.sketch_name
            else:
                self.logger.error(
                    f"connection_info has no sketch_name attribute! Type: {type(connection_info)}"
                )
                sketch_name = None
            del self.connection_info[websocket]

            # Remove from active connections
            if sketch_name and sketch_name in self.active_connections:
                if websocket in self.active_connections[sketch_name]:
                    self.active_connections[sketch_name].remove(websocket)

                # Clean up empty sketch rooms
                if not self.active_connections[sketch_name]:
                    del self.active_connections[sketch_name]

        # Close WebSocket if still open
        try:
            if (
                hasattr(websocket, "client_state")
                and websocket.client_state.name == "OPEN"
            ):
                await websocket.close()
        except Exception:
            pass  # Ignore errors during cleanup

    async def broadcast_to_sketch(self, sketch_name: str, message: Dict[str, Any]):
        """Broadcast a message to all clients watching a sketch.

        Args:
            sketch_name: Name of sketch
            message: Message to broadcast
        """
        if sketch_name not in self.active_connections:
            return

        # Add timestamp to message
        message["timestamp"] = datetime.now().isoformat()

        # Serialize message
        message_str = json.dumps(message)

        # Send to all clients (with error handling)
        clients_to_remove = []

        for websocket in self.active_connections[sketch_name]:
            try:
                await self._send_to_client_raw(websocket, message_str)
            except (WebSocketDisconnect, ConnectionClosed, Exception) as e:
                self.logger.warning(f"Failed to send message to client: {e}")
                clients_to_remove.append(websocket)

        # Clean up failed connections
        for websocket in clients_to_remove:
            await self._cleanup_connection(websocket)

    async def _send_to_client(self, websocket: WebSocket, message: Dict[str, Any]):
        """Send a message to a specific client.

        Args:
            websocket: WebSocket connection
            message: Message to send
        """
        message_str = json.dumps(message)
        await self._send_to_client_raw(websocket, message_str)

    async def _send_to_client_raw(self, websocket: WebSocket, message_str: str):
        """Send a raw message string to a client.

        Args:
            websocket: WebSocket connection
            message_str: JSON message string
        """
        try:
            # Always use send_text for FastAPI WebSockets
            await websocket.send_text(message_str)
        except Exception as e:
            # Try mock WebSocket format for tests
            try:
                if hasattr(websocket, "send"):
                    await websocket.send_text(message_str)
                else:
                    raise e
            except Exception:
                raise e  # Re-raise original error

    async def handle_client_message(self, websocket: WebSocket, message: str):
        """Handle incoming message from client.

        Args:
            websocket: WebSocket connection
            message: Raw message string from client
        """
        try:
            data = json.loads(message)
            message_type = data.get("type")

            if message_type == "ping":
                # Update last ping time
                if websocket in self.connection_info:
                    connection_info = self.connection_info[websocket]
                    if hasattr(connection_info, "last_ping"):
                        connection_info.last_ping = datetime.now()

                # Send pong response
                await self._send_to_client(
                    websocket, {"type": "pong", "timestamp": datetime.now().isoformat()}
                )

            elif message_type == "force_refresh":
                # Client requesting force refresh
                if websocket in self.connection_info:
                    connection_info = self.connection_info[websocket]
                    if hasattr(connection_info, "sketch_name"):
                        sketch_name = connection_info.sketch_name

                        # Send current preview
                        current_preview = self.cache.get_current_preview(sketch_name)
                        if current_preview:
                            await self._send_to_client(
                                websocket,
                                {
                                    "type": "preview_updated",
                                    "sketch": sketch_name,
                                    "image_url": f"/preview/{current_preview.file_path.name}?v={current_preview.version}",
                                    "status": "success",
                                    "timestamp": current_preview.created_at.isoformat(),
                                },
                            )
                        else:
                            await self._send_to_client(
                                websocket,
                                {
                                    "type": "no_preview",
                                    "sketch": sketch_name,
                                    "message": "No preview available",
                                },
                            )

            else:
                self.logger.warning(f"Unknown message type: {message_type}")

        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON message from client: {e}")
            await self._send_to_client(
                websocket, {"type": "error", "error": "Invalid JSON message"}
            )
        except Exception as e:
            self.logger.error(f"Error handling client message: {e}")

    def get_connection_stats(self) -> Dict[str, Any]:
        """Get connection statistics.

        Returns:
            Dictionary with connection statistics
        """
        active_connections = sum(
            len(clients) for clients in self.active_connections.values()
        )
        uptime = time.time() - self.connection_start_time

        return {
            "total_connections": self.total_connections,
            "active_connections": active_connections,
            "active_sketches": len(self.active_connections),
            "uptime_seconds": uptime,
            "sketches": list(self.active_connections.keys()),
        }

    def get_sketch_stats(self, sketch_name: str) -> Dict[str, Any]:
        """Get statistics for a specific sketch.

        Args:
            sketch_name: Name of sketch

        Returns:
            Dictionary with sketch statistics
        """
        if sketch_name not in self.active_connections:
            return {
                "sketch_name": sketch_name,
                "connected_clients": 0,
                "connections": [],
            }

        connections = []
        for websocket in self.active_connections[sketch_name]:
            if websocket in self.connection_info:
                info = self.connection_info[websocket]
                connections.append(
                    {
                        "connected_at": info.connected_at.isoformat(),
                        "last_ping": (
                            info.last_ping.isoformat() if info.last_ping else None
                        ),
                    }
                )

        return {
            "sketch_name": sketch_name,
            "connected_clients": len(self.active_connections[sketch_name]),
            "connections": connections,
        }

    def is_watching_sketch(self, sketch_name: str) -> bool:
        """Check if any clients are watching a sketch.

        Args:
            sketch_name: Name of sketch to check

        Returns:
            True if sketch has active connections
        """
        return (
            sketch_name in self.active_connections
            and len(self.active_connections[sketch_name]) > 0
        )

    def get_watched_sketches(self) -> List[str]:
        """Get list of sketches being watched.

        Returns:
            List of sketch names with active connections
        """
        return list(self.active_connections.keys())

    async def shutdown(self):
        """Shutdown the preview manager and close all connections."""
        self.logger.info("Shutting down LivePreviewManager...")

        # Close all WebSocket connections
        all_websockets = []
        for clients in self.active_connections.values():
            all_websockets.extend(clients)

        for websocket in all_websockets:
            try:
                await self._send_to_client(
                    websocket,
                    {"type": "server_shutdown", "message": "Server is shutting down"},
                )
                await websocket.close()
            except Exception:
                pass  # Ignore errors during shutdown

        # Clear all connections
        self.active_connections.clear()
        self.connection_info.clear()

        self.logger.info("LivePreviewManager shutdown complete")
