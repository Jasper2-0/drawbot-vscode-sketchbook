"""
LivePreviewServer - FastAPI application with core endpoints for live preview.
"""

import asyncio
import hashlib
import mimetypes
import os
import re
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
from ..core.thumbnail_generator import TaskPriority, ThumbnailGenerator
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

        # Initialize thumbnail generator
        self.thumbnail_generator = ThumbnailGenerator(self.preview_engine)

        # Set up thumbnail completion callback for WebSocket broadcasts
        self.thumbnail_generator.add_completion_callback(self._on_thumbnail_completed)

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

                        # Add thumbnail information
                        if (
                            current_preview.thumbnail_path
                            and current_preview.thumbnail_path.exists()
                        ):
                            sketch_info["has_thumbnail"] = True
                            sketch_info[
                                "thumbnail_url"
                            ] = f"/thumbnail/{current_preview.thumbnail_path.name}"
                        else:
                            sketch_info["has_thumbnail"] = False
                            sketch_info["thumbnail_url"] = None
                    else:
                        sketch_info["has_thumbnail"] = False
                        sketch_info["thumbnail_url"] = None

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

                            # Add thumbnail information
                            if (
                                current_preview.thumbnail_path
                                and current_preview.thumbnail_path.exists()
                            ):
                                sketch_info["has_thumbnail"] = True
                                sketch_info[
                                    "thumbnail_url"
                                ] = f"/thumbnail/{current_preview.thumbnail_path.name}"
                            else:
                                sketch_info["has_thumbnail"] = False
                                sketch_info["thumbnail_url"] = None
                        else:
                            sketch_info["has_thumbnail"] = False
                            sketch_info["thumbnail_url"] = None

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

                                    # Add thumbnail information
                                    if (
                                        current_preview.thumbnail_path
                                        and current_preview.thumbnail_path.exists()
                                    ):
                                        sketch_info["has_thumbnail"] = True
                                        sketch_info[
                                            "thumbnail_url"
                                        ] = f"/thumbnail/{current_preview.thumbnail_path.name}"
                                    else:
                                        sketch_info["has_thumbnail"] = False
                                        sketch_info["thumbnail_url"] = None
                                else:
                                    sketch_info["has_thumbnail"] = False
                                    sketch_info["thumbnail_url"] = None

                                sketches.append(sketch_info)

        # Sort by category first, then by modification time (newest first)
        sketches.sort(key=lambda s: (s["category"], s["modified_at"]), reverse=True)

        return sketches

    def _on_thumbnail_completed(self, result):
        """Handle thumbnail completion by broadcasting to WebSocket clients.

        Args:
            result: TaskResult from thumbnail generator
        """
        # Broadcast thumbnail update to all connected clients
        if hasattr(self, "preview_manager"):
            try:
                # Create async task to broadcast to all clients watching this sketch
                asyncio.create_task(
                    self.preview_manager.broadcast_to_sketch(
                        result.sketch_name,
                        {
                            "type": "thumbnail_updated",
                            "sketch_name": result.sketch_name,
                            "success": result.success,
                            "thumbnail_url": result.thumbnail_url,
                            "error": result.error,
                            "timestamp": datetime.now().isoformat(),
                        },
                    )
                )
            except Exception as e:
                # Don't let broadcast errors crash the system
                print(f"Failed to broadcast thumbnail update: {e}")

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

    @app.on_event("startup")
    async def startup_event():
        """Initialize background services on server startup."""
        # Start thumbnail generator
        await server.thumbnail_generator.start()

        # Queue initial thumbnail generation for existing sketches
        sketches = server.get_available_sketches()
        if sketches:
            server.thumbnail_generator.queue_multiple_sketches(
                sketches,
                user_sketch_priority=TaskPriority.HIGH,
                example_priority=TaskPriority.MEDIUM,
            )

    @app.on_event("shutdown")
    async def shutdown_event():
        """Clean up background services on server shutdown."""
        await server.thumbnail_generator.stop()

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

        # Check for multi-page files
        multi_page_files = server.preview_engine.get_multi_page_files(sketch_name)
        is_multi_page = multi_page_files is not None and len(multi_page_files) > 1

        # Minimal debug for multi-page detection
        if sketch_name == "multi_page_test":
            print(
                f"DEBUG: multi_page_files={multi_page_files} is_multi_page={is_multi_page}"
            )

        # Prepare context for template
        context = {
            "request": request,
            "sketch_name": sketch_name,
            "current_preview": current_preview,
            "is_multi_page": is_multi_page,
        }

        # Debug context
        if sketch_name == "multi_page_test":
            print(f"DEBUG: context is_multi_page={context['is_multi_page']}")

        if current_preview:
            context[
                "image_url"
            ] = f"/preview/{current_preview.file_path.name}?v={current_preview.version}"

        # Add multi-page URLs if available
        if is_multi_page:
            page_urls = []
            for i, page_file in enumerate(multi_page_files, 1):
                page_urls.append(
                    {
                        "page_number": i,
                        "url": f"/page/{sketch_name}/{page_file.name}",
                        "filename": page_file.name,
                    }
                )
            context["page_urls"] = page_urls
            context["total_pages"] = len(multi_page_files)

            # Debug page URLs
            if sketch_name == "multi_page_test":
                print(f"DEBUG: page_urls={[p['url'] for p in page_urls]}")

        return templates.TemplateResponse("sketch_preview.html", context)

    @app.get("/page/{sketch_name}/{page_filename}")
    async def serve_page_image(sketch_name: str, page_filename: str, request: Request):
        """Serve individual page images for multi-page sketches."""
        # Validate sketch exists
        validation = server.security_middleware.validate_sketch_path(sketch_name)
        if not validation.valid:
            raise HTTPException(
                status_code=404, detail=f"Sketch not found: {sketch_name}"
            )

        # Validate page filename format and security
        if not re.match(r"^[a-zA-Z0-9_]+_page_\d+\.png$", page_filename):
            raise HTTPException(status_code=400, detail="Invalid page filename format")

        # Build page file path
        # Handle path resolution - if project_path already ends with 'sketches', use it directly
        if Path(server.project_path).name == "sketches":
            sketches_dir = Path(server.project_path)
        else:
            sketches_dir = Path(server.project_path) / "sketches"

        # First, try to find page file in the sketch's own folder (folder-based structure)
        sketch_folder = sketches_dir / sketch_name
        page_file_path = sketch_folder / page_filename

        if not (page_file_path.exists() and page_file_path.is_file()):
            # Fall back to flat structure: look in root sketches directory
            page_file_path = sketches_dir / page_filename

            if not (page_file_path.exists() and page_file_path.is_file()):
                raise HTTPException(status_code=404, detail="Page file not found")

        # Verify this page belongs to the requested sketch
        if not page_filename.startswith(f"{sketch_name}_page_"):
            raise HTTPException(status_code=403, detail="Access denied")

        return FileResponse(
            page_file_path,
            media_type="image/png",
            headers={
                "Cache-Control": "public, max-age=3600",
                "ETag": f'"{page_file_path.stat().st_mtime}"',
            },
        )

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

    @app.get("/thumbnail/{filename}")
    async def serve_thumbnail_image(filename: str, request: Request):
        """Serve cached thumbnail images."""
        # Security: validate filename
        if ".." in filename or "/" in filename or "\\" in filename:
            raise HTTPException(status_code=400, detail="Invalid filename")

        image_path = server.cache_dir / filename

        if not image_path.exists() or not image_path.is_file():
            raise HTTPException(status_code=404, detail="Thumbnail not found")

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
                "Cache-Control": "public, max-age=3600",  # Cache thumbnails for 1 hour
                "Last-Modified": datetime.fromtimestamp(file_stat.st_mtime).strftime(
                    "%a, %d %b %Y %H:%M:%S GMT"
                ),
            },
        )

    @app.post("/generate-thumbnail/{sketch_name}")
    async def generate_thumbnail(sketch_name: str):
        """Generate thumbnail for a specific sketch."""
        # Validate sketch exists
        validation = server.security_middleware.validate_sketch_path(sketch_name)
        if not validation.valid:
            raise HTTPException(
                status_code=404, detail=f"Sketch not found: {sketch_name}"
            )

        # Generate thumbnail using the preview engine
        thumbnail_url = server.preview_engine.generate_thumbnail(sketch_name)

        if thumbnail_url:
            return {
                "success": True,
                "sketch_name": sketch_name,
                "thumbnail_url": thumbnail_url,
                "timestamp": datetime.now().isoformat(),
            }
        else:
            return {
                "success": False,
                "sketch_name": sketch_name,
                "error": "Failed to generate thumbnail - sketch may not have a preview yet",
                "timestamp": datetime.now().isoformat(),
            }

    @app.get("/thumbnail-status")
    async def get_thumbnail_status():
        """Get thumbnail generation queue status."""
        return server.thumbnail_generator.get_queue_status()

    @app.post("/queue-thumbnails")
    async def queue_thumbnail_generation():
        """Queue thumbnail generation for all sketches without thumbnails."""
        sketches = server.get_available_sketches()

        # Queue sketches for thumbnail generation
        queued_count = server.thumbnail_generator.queue_multiple_sketches(
            sketches,
            user_sketch_priority=TaskPriority.HIGH,
            example_priority=TaskPriority.MEDIUM,
        )

        return {
            "success": True,
            "queued_count": queued_count,
            "total_sketches": len(sketches),
            "timestamp": datetime.now().isoformat(),
        }

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
