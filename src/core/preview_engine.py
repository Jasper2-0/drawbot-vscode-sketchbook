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
from typing import Any, Dict, List, Optional

# Note: ImageConverter removed - we now use DrawBot's native PNG output only
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
    thumbnail_url: Optional[str] = None
    thumbnail_path: Optional[Path] = None
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
            # Check for multi-page output first
            if execution_result.output_files and len(execution_result.output_files) > 1:
                # Multi-page output - use first page as primary preview
                # TODO: Later we can enhance this to show all pages in sequence
                primary_file = execution_result.output_files[0]
                
                with open(primary_file, "rb") as f:
                    image_data = f.read()

                cache_result = self.cache.store_preview(cache_key, image_data)
                if cache_result.success:
                    # Try to generate thumbnail immediately
                    thumbnail_url = self.cache.generate_thumbnail_for_entry(cache_key)
                    
                    return PreviewResult(
                        success=True,
                        preview_url=cache_result.preview_url,
                        preview_path=cache_result.preview_path,
                        thumbnail_url=thumbnail_url,
                        thumbnail_path=cache_result.thumbnail_path,
                        version=cache_result.version,
                    )
                else:
                    return PreviewResult(
                        success=False,
                        error=f"Failed to cache preview: {cache_result.error}",
                    )
            
            # Single file output
            else:
                # Check if output is a direct image format (PNG, GIF, JPEG, etc.)
                image_formats = {".png", ".gif", ".jpg", ".jpeg", ".webp", ".bmp"}
                file_ext = execution_result.output_path.suffix.lower()

                if file_ext in image_formats:
                    # Direct image output - store in cache
                    with open(execution_result.output_path, "rb") as f:
                        image_data = f.read()

                    cache_result = self.cache.store_preview(cache_key, image_data)
                    if cache_result.success:
                        # Try to generate thumbnail immediately
                        thumbnail_url = self.cache.generate_thumbnail_for_entry(cache_key)
                        
                        return PreviewResult(
                            success=True,
                            preview_url=cache_result.preview_url,
                            preview_path=cache_result.preview_path,
                            thumbnail_url=thumbnail_url,
                            thumbnail_path=cache_result.thumbnail_path,
                            version=cache_result.version,
                        )
                    else:
                        return PreviewResult(
                            success=False,
                            error=f"Failed to cache preview: {cache_result.error}",
                        )

                # For PDF files, look for auto-extracted pages
                elif file_ext == ".pdf":
                    extracted_pages = self._extract_pdf_pages(execution_result.output_path, cache_key)
                    if extracted_pages:
                        # Use first page as primary preview
                        with open(extracted_pages[0], "rb") as f:
                            image_data = f.read()

                        cache_result = self.cache.store_preview(cache_key, image_data)
                        if cache_result.success:
                            # Try to generate thumbnail immediately
                            thumbnail_url = self.cache.generate_thumbnail_for_entry(cache_key)
                            
                            return PreviewResult(
                                success=True,
                                preview_url=cache_result.preview_url,
                                preview_path=cache_result.preview_path,
                                thumbnail_url=thumbnail_url,
                                thumbnail_path=cache_result.thumbnail_path,
                                version=cache_result.version,
                            )
                        else:
                            return PreviewResult(
                                success=False,
                                error=f"Failed to cache preview: {cache_result.error}",
                            )
                    else:
                        # No extracted pages found, return error with helpful message
                        return PreviewResult(
                            success=False,
                            error="Multi-page PDF detected but individual pages were not extracted. Please ensure your sketch uses drawbot.newPage() for multiple pages.",
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

    def _extract_pdf_pages(self, pdf_path: Path, cache_key: str) -> Optional[List[Path]]:
        """Extract individual pages from PDF by looking for auto-generated page files.
        
        Args:
            pdf_path: Path to the PDF file
            cache_key: Cache key for naming extracted pages
            
        Returns:
            List of paths to extracted page PNG files, or None if extraction failed
        """
        try:
            # Look for auto-generated page files in the same directory as the PDF
            pdf_dir = pdf_path.parent
            page_pattern = pdf_dir / f"{cache_key}_page_*.png"
            
            # Find all page files
            page_files = list(pdf_dir.glob(f"{cache_key}_page_*.png"))
            
            if page_files:
                # Sort by page number
                page_files.sort(key=lambda f: int(f.stem.split('_page_')[-1]))
                return page_files
            
            # If no auto-generated pages found, return None for now
            # In the future, we could add actual PDF extraction here
            return None
            
        except Exception as e:
            return None

    def get_multi_page_files(self, sketch_name: str) -> Optional[List[Path]]:
        """Get all page files for a multi-page sketch.
        
        Args:
            sketch_name: Name of the sketch
            
        Returns:
            List of paths to page files, or None if not multi-page
        """
        try:
            # Determine the correct sketches directory
            # If project_path ends with 'sketches', use it directly
            # Otherwise, append 'sketches' to it
            if self.project_path.name == "sketches":
                sketches_dir = self.project_path
            else:
                sketches_dir = self.project_path / "sketches"
                
            page_pattern = f"{sketch_name}_page_*.png"
            
            # First, try to find page files in the sketch's own folder (folder-based structure)
            sketch_folder = sketches_dir / sketch_name
            if sketch_folder.exists() and sketch_folder.is_dir():
                page_files = list(sketch_folder.glob(page_pattern))
                if page_files:
                    # Sort by page number
                    page_files.sort(key=lambda f: int(f.stem.split('_page_')[-1]))
                    return page_files
            
            # Fall back to flat structure: look in root sketches directory
            page_files = list(sketches_dir.glob(page_pattern))
            
            if page_files:
                # Sort by page number
                page_files.sort(key=lambda f: int(f.stem.split('_page_')[-1]))
                return page_files
            
            return None
        except Exception:
            return None

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

    def generate_thumbnail(self, sketch_name: str, version: Optional[int] = None) -> Optional[str]:
        """Generate thumbnail for an existing cached preview.
        
        Args:
            sketch_name: Name of the sketch
            version: Specific version, or None for current version
            
        Returns:
            Thumbnail URL if successful, None otherwise
        """
        return self.cache.generate_thumbnail_for_entry(sketch_name, version)

    def get_available_sketches_with_thumbnails(self) -> List[Dict[str, Any]]:
        """Get all sketches with their thumbnail information.
        
        Returns:
            List of sketch dictionaries with thumbnail URLs
        """
        sketches = []
        
        # Get all cache entries
        for sketch_name, entry_list in self.cache.entries.items():
            if entry_list:
                current_entry = entry_list[0]  # Most recent
                
                sketch_info = {
                    "name": sketch_name,
                    "has_preview": True,
                    "preview_url": f"/preview/{current_entry.file_path.name}",
                    "version": current_entry.version,
                    "created_at": current_entry.created_at.isoformat(),
                    "file_size_bytes": current_entry.file_size_bytes,
                }
                
                # Add thumbnail info if available
                if current_entry.thumbnail_path and current_entry.thumbnail_path.exists():
                    sketch_info["thumbnail_url"] = f"/thumbnail/{current_entry.thumbnail_path.name}"
                    sketch_info["has_thumbnail"] = True
                else:
                    sketch_info["has_thumbnail"] = False
                
                sketches.append(sketch_info)
        
        return sketches
