"""
PreviewEngine - Core preview execution system for live preview functionality.
"""

import asyncio
import gc
import os
import subprocess
import sys
import tempfile
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from .image_converter import ConversionResult, ImageConverter
from .preview_cache import CacheResult, PreviewCache
from .sketch_runner import ExecutionResult, SketchRunner


@dataclass
class PreviewResult:
    """Result of preview generation."""

    success: bool
    error: Optional[str] = None
    execution_time: float = 0.0
    preview_url: Optional[str] = None
    preview_path: Optional[Path] = None
    sketch_path: Optional[Path] = None
    timestamp: Optional[datetime] = None
    version: Optional[int] = None


class PreviewEngine:
    """Manages sketch execution and preview generation with safety and monitoring."""

    def __init__(self, project_path: Path, cache: PreviewCache, timeout: float = 30.0):
        """Initialize preview engine.

        Args:
            project_path: Path to the project directory
            cache: PreviewCache instance for storing generated previews
            timeout: Maximum execution time in seconds
        """
        self.project_path = project_path
        self.cache = cache
        self.timeout = timeout

        # Initialize components
        self.sketch_runner = SketchRunner(project_path, timeout)
        self.image_converter = ImageConverter(retina_scale=3.0)

        # Execution management
        self.current_execution: Optional[asyncio.Task] = None
        self.execution_lock = threading.Lock()

    def execute_sketch(
        self, sketch_path: Path, sketch_name: Optional[str] = None
    ) -> PreviewResult:
        """Execute a sketch and generate preview image.

        Args:
            sketch_path: Path to the sketch file to execute
            sketch_name: Optional logical name for caching (defaults to path stem)

        Returns:
            PreviewResult containing execution status and preview information
        """
        start_time = time.time()
        timestamp = datetime.now()

        # Cancel any running execution
        self._cancel_current_execution()

        try:
            # Force garbage collection before execution
            gc.collect()

            # Validate sketch file exists
            if not sketch_path.exists():
                return PreviewResult(
                    success=False,
                    error=f"Sketch file not found: {sketch_path}",
                    timestamp=timestamp,
                    sketch_path=sketch_path,
                )

            # Execute sketch safely
            execution_result = self.sketch_runner.run_sketch(sketch_path)

            if not execution_result.success:
                execution_time = time.time() - start_time
                return PreviewResult(
                    success=False,
                    error=execution_result.error,
                    execution_time=execution_time,
                    sketch_path=sketch_path,
                    timestamp=timestamp,
                )

            # Convert output to preview image if available
            preview_result = self._generate_preview_image(
                sketch_path, execution_result, sketch_name
            )

            execution_time = time.time() - start_time
            preview_result.execution_time = execution_time
            preview_result.sketch_path = sketch_path
            preview_result.timestamp = timestamp

            return preview_result

        except Exception as e:
            execution_time = time.time() - start_time
            return PreviewResult(
                success=False,
                error=f"Preview generation failed: {str(e)}",
                execution_time=execution_time,
                sketch_path=sketch_path,
                timestamp=timestamp,
            )
        finally:
            # Force cleanup even on errors
            gc.collect()

    def _cancel_current_execution(self):
        """Cancel any currently running execution."""
        with self.execution_lock:
            if self.current_execution and not self.current_execution.done():
                self.current_execution.cancel()

    def _generate_preview_image(
        self,
        sketch_path: Path,
        execution_result: ExecutionResult,
        sketch_name: Optional[str] = None,
    ) -> PreviewResult:
        """Generate preview image from sketch execution result.

        Args:
            sketch_path: Path to the executed sketch
            execution_result: Result from sketch execution
            sketch_name: Optional logical name for caching

        Returns:
            PreviewResult with preview image information
        """
        # Use provided sketch name or fall back to path stem
        cache_key = sketch_name if sketch_name is not None else sketch_path.stem

        # If no output was generated, return success but no preview
        if (
            not execution_result.output_path
            or not execution_result.output_path.exists()
        ):
            return PreviewResult(success=True, preview_url=None, preview_path=None)

        try:
            # Check if output is a direct image format (PNG, GIF, JPEG, etc.)
            image_formats = {".png", ".gif", ".jpg", ".jpeg", ".webp", ".bmp"}
            file_ext = execution_result.output_path.suffix.lower()

            if file_ext in image_formats:
                # Direct image output - store in cache
                with open(execution_result.output_path, "rb") as f:
                    image_data = f.read()

                cache_result = self.cache.store_preview(cache_key, image_data)
                if cache_result.success:
                    return PreviewResult(
                        success=True,
                        preview_url=cache_result.preview_url,
                        preview_path=cache_result.preview_path,
                        version=cache_result.version,
                    )
                else:
                    return PreviewResult(
                        success=False,
                        error=f"Failed to cache preview: {cache_result.error}",
                    )

            # Check if output is a PDF (typical DrawBot output)
            elif file_ext == ".pdf":
                # Read PDF data
                with open(execution_result.output_path, "rb") as f:
                    pdf_data = f.read()

                # Convert PDF to PNG
                conversion_result = self.image_converter.convert_pdf_to_png(
                    pdf_data, self.cache.cache_dir
                )

                if not conversion_result.success:
                    return PreviewResult(
                        success=False,
                        error=f"PDF conversion failed: {conversion_result.error}",
                    )

                # Store converted PNG in cache
                with open(conversion_result.png_path, "rb") as f:
                    image_data = f.read()

                cache_result = self.cache.store_preview(cache_key, image_data)
                if cache_result.success:
                    # Clean up temporary conversion file
                    try:
                        conversion_result.png_path.unlink()
                    except:
                        pass  # Ignore cleanup errors

                    return PreviewResult(
                        success=True,
                        preview_url=cache_result.preview_url,
                        preview_path=cache_result.preview_path,
                        version=cache_result.version,
                    )
                else:
                    return PreviewResult(
                        success=False,
                        error=f"Failed to cache preview: {cache_result.error}",
                    )

            else:
                # Unsupported output format
                return PreviewResult(
                    success=False,
                    error=f"Unsupported output format: {execution_result.output_path.suffix}",
                )

        except Exception as e:
            return PreviewResult(
                success=False, error=f"Preview image generation failed: {str(e)}"
            )

    def _get_python_executable(self) -> str:
        """Get the appropriate Python executable, preferring virtual environment if available."""
        return self.sketch_runner._get_python_executable()

    def validate_sketch_before_execution(self, sketch_path: Path) -> PreviewResult:
        """Validate sketch syntax before execution.

        Args:
            sketch_path: Path to sketch file

        Returns:
            PreviewResult indicating validation success/failure
        """
        validation_result = self.sketch_runner.validate_sketch_before_run(sketch_path)

        return PreviewResult(
            success=validation_result.success,
            error=validation_result.error,
            sketch_path=sketch_path,
        )

    def get_cache_statistics(self) -> Dict[str, Any]:
        """Get preview cache statistics."""
        return self.cache.get_statistics()

    def cleanup_cache(self):
        """Trigger cache cleanup."""
        self.cache.cleanup_old_previews()
