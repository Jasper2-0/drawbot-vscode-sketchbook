"""
LivePreviewServer - FastAPI application with core endpoints for live preview.
"""

import asyncio
import hashlib
import mimetypes
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiofiles
import psutil
from fastapi import (
    FastAPI,
    HTTPException,
    Request,
    Response,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from ..core.preview_cache import PreviewCache
from ..core.preview_engine import PreviewEngine, PreviewResult
from .file_watch_integration import FileWatchIntegration
from .live_preview_manager import LivePreviewManager
from .security_middleware import SecurityConfig, SecurityMiddleware


class LivePreviewServer:
    """FastAPI-based live preview server."""

    def __init__(
        self,
        project_path: Path,
        cache_dir: Path,
        host: str = "127.0.0.1",
        port: int = 8080,
    ):
        """Initialize live preview server.

        Args:
            project_path: Path to project directory containing sketches
            cache_dir: Path to preview cache directory
            host: Host to bind to (default localhost only)
            port: Port to bind to
        """
        self.project_path = Path(project_path)
        self.cache_dir = Path(cache_dir)
        self.host = host
        self.port = port

        # Initialize core components
        self.cache = PreviewCache(cache_dir)
        self.preview_engine = PreviewEngine(project_path, self.cache)

        # Initialize live preview components
        self.preview_manager = LivePreviewManager(project_path, cache_dir)
        self.file_watch_integration = FileWatchIntegration(
            project_path, cache_dir, self.preview_manager
        )

        # Server state
        self.start_time = time.time()
        self.execution_stats = {
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "total_execution_time": 0.0,
        }

        # Security configuration
        base_dir = self.project_path.parent  # Go up to project root
        self.security_config = SecurityConfig(
            allowed_sketch_directories=[
                self.project_path,  # sketches/
                base_dir / "examples",  # examples/
            ],
            bind_host=host,
            allowed_client_ips=[
                "127.0.0.1",
                "::1",
                "testclient",
            ],  # Add testclient for testing
        )
        self.security_middleware = SecurityMiddleware(self.security_config)

    def get_available_sketches(self) -> List[Dict[str, Any]]:
        """Get list of available sketches from both sketches/ and examples/ directories.

        Supports both flat (.py files directly in directory/) and
        folder-based (directory/sketch_name/sketch_name.py) structures.

        Returns:
            List of sketch information dictionaries with source type
        """
        sketches = []

        # Scan both sketches and examples directories
        base_dir = self.project_path.parent  # Go up to project root
        directories_to_scan = [
            (base_dir / "sketches", "sketch"),
            (base_dir / "examples", "example"),
        ]

        for scan_dir, source_type in directories_to_scan:
            if not scan_dir.exists():
                continue

            # Check for flat structure: *.py files directly in directory/
            for sketch_file in scan_dir.glob("*.py"):
                if sketch_file.is_file():
                    sketch_name = sketch_file.stem

                    # Get basic file info
                    stat = sketch_file.stat()

                    # Check if we have a cached preview
                    current_preview = self.cache.get_current_preview(sketch_name)

                    sketch_info = {
                        "name": sketch_name,
                        "file_path": str(sketch_file),
                        "size_bytes": stat.st_size,
                        "modified_at": datetime.fromtimestamp(
                            stat.st_mtime
                        ).isoformat(),
                        "has_preview": current_preview is not None,
                        "preview_url": (
                            f"/sketch/{sketch_name}" if current_preview else None
                        ),
                        "source_type": source_type,
                        "category": source_type.title() + "s",
                    }

                    if current_preview:
                        sketch_info[
                            "last_preview_generated"
                        ] = current_preview.created_at.isoformat()

                    sketches.append(sketch_info)

            # Check for folder-based structure: directory/sketch_name/sketch_name.py
            for sketch_dir in scan_dir.iterdir():
                if sketch_dir.is_dir() and not sketch_dir.name.startswith("."):
                    sketch_name = sketch_dir.name
                    sketch_file = sketch_dir / f"{sketch_name}.py"

                    if sketch_file.exists() and sketch_file.is_file():
                        # Get basic file info
                        stat = sketch_file.stat()

                        # Check if we have a cached preview
                        current_preview = self.cache.get_current_preview(sketch_name)

                        sketch_info = {
                            "name": sketch_name,
                            "file_path": str(sketch_file),
                            "size_bytes": stat.st_size,
                            "modified_at": datetime.fromtimestamp(
                                stat.st_mtime
                            ).isoformat(),
                            "has_preview": current_preview is not None,
                            "preview_url": (
                                f"/sketch/{sketch_name}" if current_preview else None
                            ),
                            "source_type": source_type,
                            "category": source_type.title() + "s",
                        }

                        if current_preview:
                            sketch_info[
                                "last_preview_generated"
                            ] = current_preview.created_at.isoformat()

                        sketches.append(sketch_info)

            # Handle examples with nested structure (like examples/drawbotgrid/*.py)
            if source_type == "example":
                for category_dir in scan_dir.iterdir():
                    if category_dir.is_dir() and not category_dir.name.startswith("."):
                        category_name = category_dir.name
                        for sketch_file in category_dir.glob("*.py"):
                            if sketch_file.is_file():
                                sketch_name = f"{category_name}_{sketch_file.stem}"

                                # Get basic file info
                                stat = sketch_file.stat()

                                # Check if we have a cached preview
                                current_preview = self.cache.get_current_preview(
                                    sketch_name
                                )

                                sketch_info = {
                                    "name": sketch_name,
                                    "display_name": f"{category_name}: {sketch_file.stem}",
                                    "file_path": str(sketch_file),
                                    "size_bytes": stat.st_size,
                                    "modified_at": datetime.fromtimestamp(
                                        stat.st_mtime
                                    ).isoformat(),
                                    "has_preview": current_preview is not None,
                                    "preview_url": (
                                        f"/sketch/{sketch_name}"
                                        if current_preview
                                        else None
                                    ),
                                    "source_type": source_type,
                                    "category": f"Examples: {category_name.title()}",
                                }

                                if current_preview:
                                    sketch_info[
                                        "last_preview_generated"
                                    ] = current_preview.created_at.isoformat()

                                sketches.append(sketch_info)

        # Sort by category first, then by modification time (newest first)
        sketches.sort(key=lambda s: (s["category"], s["modified_at"]), reverse=True)

        return sketches

    def execute_sketch(self, sketch_name: str) -> PreviewResult:
        """Execute a sketch and generate preview.

        Args:
            sketch_name: Name of sketch to execute

        Returns:
            PreviewResult with execution status
        """
        # Validate sketch path
        validation = self.security_middleware.validate_sketch_path(sketch_name)
        if not validation.valid:
            return PreviewResult(
                success=False, error=f"Invalid sketch: {validation.error}"
            )

        # Update stats
        self.execution_stats["total_executions"] += 1

        try:
            # Execute sketch - ensure absolute path
            sketch_path = validation.resolved_path
            if not sketch_path.is_absolute():
                sketch_path = self.project_path.parent / sketch_path

            result = self.preview_engine.execute_sketch(sketch_path, sketch_name)

            # Update stats
            if result.success:
                self.execution_stats["successful_executions"] += 1
            else:
                self.execution_stats["failed_executions"] += 1

            if result.execution_time:
                self.execution_stats["total_execution_time"] += result.execution_time

            return result

        except Exception as e:
            self.execution_stats["failed_executions"] += 1
            return PreviewResult(success=False, error=f"Execution failed: {str(e)}")

    def get_sketch_status(self, sketch_name: str) -> Dict[str, Any]:
        """Get current status of a sketch.

        Args:
            sketch_name: Name of sketch

        Returns:
            Dictionary with sketch status information
        """
        # Validate sketch exists
        validation = self.security_middleware.validate_sketch_path(sketch_name)
        if not validation.valid:
            raise HTTPException(
                status_code=404, detail=f"Sketch not found: {sketch_name}"
            )

        # Get current preview
        current_preview = self.cache.get_current_preview(sketch_name)

        status = {
            "sketch_name": sketch_name,
            "status": "unknown",
            "last_updated": None,
            "execution_time": None,
            "error": None,
            "preview_url": None,
            "version": None,
        }

        if current_preview:
            status.update(
                {
                    "status": "success",
                    "last_updated": current_preview.created_at.isoformat(),
                    "preview_url": f"/preview/{current_preview.file_path.name}?v={current_preview.version}",
                    "version": str(current_preview.version),
                }
            )

        return status

    def get_server_metrics(self) -> Dict[str, Any]:
        """Get server performance metrics.

        Returns:
            Dictionary with server metrics
        """
        # Get process info
        process = psutil.Process()
        memory_info = process.memory_info()

        # Calculate uptime
        uptime = time.time() - self.start_time

        # Get cache stats
        cache_stats = self.cache.get_statistics()

        return {
            "server_stats": {
                "uptime_seconds": uptime,
                "memory_usage_mb": memory_info.rss / (1024 * 1024),
                "cpu_percent": process.cpu_percent(),
                "active_sketches": cache_stats["total_sketches"],
            },
            "execution_stats": self.execution_stats.copy(),
            "cache_stats": cache_stats,
        }


def create_app(server: LivePreviewServer) -> FastAPI:
    """Create FastAPI application with all endpoints.

    Args:
        server: LivePreviewServer instance

    Returns:
        Configured FastAPI application
    """
    app = FastAPI(
        title="DrawBot Live Preview Server",
        description="Real-time preview server for DrawBot sketches",
        version="2.0.0",
    )

    # Set up templates and static files
    templates_dir = Path(__file__).parent / "templates"
    static_dir = Path(__file__).parent / "static"

    templates = Jinja2Templates(directory=str(templates_dir))
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    # Add security middleware
    app.add_middleware(server.security_middleware.get_middleware_class())

    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        metrics = server.get_server_metrics()
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "uptime": metrics["server_stats"]["uptime_seconds"],
            "memory_usage_mb": round(metrics["server_stats"]["memory_usage_mb"], 2),
            "active_sketches": metrics["server_stats"]["active_sketches"],
        }

    @app.get("/", response_class=HTMLResponse)
    async def sketch_list(request: Request):
        """Main page showing available sketches."""
        sketches = server.get_available_sketches()

        # Prepare data for template
        user_sketches = [s for s in sketches if s.get("source_type") == "sketch"]
        examples = [s for s in sketches if s.get("source_type") == "example"]

        # Add display formatting to sketches
        for sketch in sketches:
            # Format file size nicely
            size_kb = sketch["size_bytes"] / 1024
            sketch["size_display"] = (
                f"{size_kb:.1f} KB" if size_kb < 1024 else f"{size_kb/1024:.1f} MB"
            )
            # Format date nicely
            sketch["date_display"] = sketch["modified_at"][:19].replace("T", " ")
            # Add relative path for display
            try:
                file_path = Path(sketch["file_path"])
                sketch["relative_path"] = str(
                    file_path.relative_to(file_path.parent.parent)
                )
            except (ValueError, OSError):
                sketch["relative_path"] = sketch["name"]

        context = {
            "request": request,
            "sketches": sketches,
            "user_sketches": user_sketches,
            "examples": examples,
            "user_sketches_count": len(user_sketches),
            "examples_count": len(examples),
            "cache_stats": server.cache.get_statistics(),
            "execution_stats": server.execution_stats,
        }

        return templates.TemplateResponse("dashboard.html", context)

    @app.get("/sketch/{sketch_name}", response_class=HTMLResponse)
    async def sketch_preview_page(request: Request, sketch_name: str):
        """Live preview page for a specific sketch."""
        # Validate sketch exists
        validation = server.security_middleware.validate_sketch_path(sketch_name)
        if not validation.valid:
            raise HTTPException(
                status_code=404, detail=f"Sketch not found: {sketch_name}"
            )

        # Get current preview
        current_preview = server.cache.get_current_preview(sketch_name)

        # Prepare context for template
        context = {
            "request": request,
            "sketch_name": sketch_name,
            "current_preview": current_preview,
        }

        if current_preview:
            context[
                "image_url"
            ] = f"/preview/{current_preview.file_path.name}?v={current_preview.version}"

        return templates.TemplateResponse("sketch_preview.html", context)

    @app.post("/execute/{sketch_name}")
    async def execute_sketch(sketch_name: str):
        """Execute a sketch and return result."""
        result = server.execute_sketch(sketch_name)

        response_data = {
            "status": "success" if result.success else "error",
            "sketch_name": sketch_name,
            "timestamp": datetime.now().isoformat(),
        }

        if result.success:
            response_data.update(
                {
                    "execution_time": str(result.execution_time),
                    "preview_url": result.preview_url,
                    "version": str(result.version),
                }
            )
        else:
            response_data["error"] = result.error

        return response_data

    @app.get("/status/{sketch_name}")
    async def get_sketch_status(sketch_name: str):
        """Get status of a specific sketch."""
        return server.get_sketch_status(sketch_name)

    @app.get("/code/{sketch_name}")
    async def get_sketch_code(sketch_name: str):
        """Get the source code of a sketch."""
        # Validate sketch exists
        validation = server.security_middleware.validate_sketch_path(sketch_name)
        if not validation.valid:
            raise HTTPException(
                status_code=404, detail=f"Sketch not found: {sketch_name}"
            )

        try:
            # Read the sketch file
            async with aiofiles.open(validation.resolved_path, "r") as f:
                code = await f.read()
            return Response(content=code, media_type="text/plain")
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to read sketch: {str(e)}"
            )

    @app.get("/preview/{filename}")
    async def serve_preview_image(filename: str, request: Request):
        """Serve cached preview images."""
        # Security: validate filename
        if ".." in filename or "/" in filename or "\\" in filename:
            raise HTTPException(status_code=400, detail="Invalid filename")

        image_path = server.cache_dir / filename

        if not image_path.exists() or not image_path.is_file():
            raise HTTPException(status_code=404, detail="Image not found")

        # Generate ETag based on file content
        file_stat = image_path.stat()
        etag = f'"{file_stat.st_mtime}-{file_stat.st_size}"'

        # Check If-None-Match header
        if_none_match = request.headers.get("if-none-match")
        if if_none_match == etag:
            return Response(status_code=304)

        # Determine content type
        content_type, _ = mimetypes.guess_type(str(image_path))
        if not content_type:
            content_type = "application/octet-stream"

        return FileResponse(
            path=image_path,
            media_type=content_type,
            headers={
                "ETag": etag,
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0",
                "Last-Modified": datetime.fromtimestamp(file_stat.st_mtime).strftime(
                    "%a, %d %b %Y %H:%M:%S GMT"
                ),
            },
        )

    @app.get("/metrics")
    async def get_metrics():
        """Get server performance metrics."""
        return server.get_server_metrics()

    @app.websocket("/live/{sketch_name}")
    async def websocket_live_preview(websocket: WebSocket, sketch_name: str):
        """WebSocket endpoint for live preview updates."""
        # Validate sketch name
        validation = server.security_middleware.validate_sketch_path(sketch_name)
        if not validation.valid:
            await websocket.close(
                code=1008, reason=f"Invalid sketch: {validation.error}"
            )
            return

        try:
            # Connect client to preview manager
            await server.preview_manager.connect_client(sketch_name, websocket)

            # Start watching the sketch file if not already watching
            if not server.file_watch_integration.is_watching_sketch(sketch_name):
                await server.file_watch_integration.start_watching_sketch(sketch_name)

            try:
                # Handle WebSocket messages
                while True:
                    message = await websocket.receive_text()
                    await server.preview_manager.handle_client_message(
                        websocket, message
                    )

            except WebSocketDisconnect:
                pass  # Normal disconnection

        except Exception as e:
            server.preview_manager.logger.error(
                f"WebSocket error for sketch '{sketch_name}': {e}"
            )

        finally:
            # Clean up connection
            await server.preview_manager.disconnect_client(sketch_name, websocket)

            # Stop watching sketch if no more clients
            if not server.preview_manager.is_watching_sketch(sketch_name):
                await server.file_watch_integration.stop_watching_sketch(sketch_name)

    @app.get("/live-stats")
    async def get_live_stats():
        """Get live preview connection statistics."""
        connection_stats = server.preview_manager.get_connection_stats()
        watch_stats = {
            "watched_sketches": server.file_watch_integration.get_watched_sketches(),
            "total_watched": len(server.file_watch_integration.get_watched_sketches()),
        }

        return {"connections": connection_stats, "file_watching": watch_stats}

    return app
