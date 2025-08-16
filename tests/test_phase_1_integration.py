"""
Phase 1 Integration Tests - End-to-end testing of core preview functionality.
"""
import tempfile
import time
from pathlib import Path

import pytest

from src.core.image_converter import ImageConverter
from src.core.preview_cache import PreviewCache
from src.core.preview_engine import PreviewEngine


class TestPhase1Integration:
    """Integration tests for Phase 1 components working together."""

    def test_complete_preview_pipeline_success(self):
        """Test complete pipeline: sketch execution → preview generation → caching."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            cache_dir = project_path / "cache"

            # Create a test sketch that generates output
            sketch_file = project_path / "integration_test_sketch.py"
            sketch_file.write_text(
                """
import drawBot as drawbot

# Create a simple drawing
drawbot.size(400, 400)
drawbot.fill(0.2, 0.8, 0.2)  # Green
drawbot.rect(50, 50, 300, 300)

drawbot.fill(1, 1, 1)  # White
drawbot.font("Helvetica", 24)
drawbot.text("Integration Test", (100, 200))

# Save as PNG (direct output)
drawbot.saveImage("output.png")
"""
            )

            # Initialize components
            cache = PreviewCache(cache_dir)
            engine = PreviewEngine(project_path, cache)

            # Execute sketch and generate preview
            result = engine.execute_sketch(sketch_file)

            # Verify successful execution
            assert result.success, f"Preview generation failed: {result.error}"
            assert result.error is None
            assert result.execution_time > 0
            assert result.sketch_path == sketch_file
            assert result.timestamp is not None

            # Verify preview was generated and cached
            assert result.preview_url is not None
            assert result.preview_path is not None
            assert result.preview_path.exists()
            assert result.version is not None

            # Verify cache entry exists
            cache_entry = cache.get_current_preview("integration_test_sketch")
            assert cache_entry is not None
            assert cache_entry.version == result.version
            assert cache_entry.file_path == result.preview_path

            # Verify image file is valid PNG
            with open(result.preview_path, "rb") as f:
                png_data = f.read()
                assert png_data.startswith(b"\x89PNG"), "Output should be valid PNG"
                assert len(png_data) > 1000, "PNG should have reasonable size"

    def test_sketch_with_pdf_output_conversion(self):
        """Test pipeline with PDF output that needs conversion."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            cache_dir = project_path / "cache"

            # Create sketch that outputs PDF
            sketch_file = project_path / "pdf_output_sketch.py"
            sketch_file.write_text(
                """
import drawBot as drawbot

# Create drawing
drawbot.size(300, 300)
drawbot.fill(0.8, 0.2, 0.2)  # Red
drawbot.oval(25, 25, 250, 250)

drawbot.fill(1, 1, 1)  # White
drawbot.font("Helvetica-Bold", 18)
drawbot.text("PDF Test", (100, 150))

# Save as PDF (requires conversion)
drawbot.saveImage("output.pdf")
"""
            )

            # Initialize components
            cache = PreviewCache(cache_dir)
            engine = PreviewEngine(project_path, cache)

            # Execute sketch
            result = engine.execute_sketch(sketch_file)

            # Should succeed with conversion
            assert result.success, f"PDF conversion failed: {result.error}"
            assert result.preview_url is not None
            assert result.preview_path is not None
            assert result.preview_path.exists()
            assert result.preview_path.suffix == ".png"

            # Verify converted image
            with open(result.preview_path, "rb") as f:
                png_data = f.read()
                assert png_data.startswith(b"\x89PNG"), "Converted output should be PNG"

    def test_error_handling_integration(self):
        """Test error handling throughout the pipeline."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            cache_dir = project_path / "cache"

            # Create sketch with syntax error
            sketch_file = project_path / "error_sketch.py"
            sketch_file.write_text(
                """
import drawBot as drawbot

drawbot.size(400, 400)
# Syntax error - missing closing parenthesis
drawbot.rect(50, 50, 100, 100
"""
            )

            cache = PreviewCache(cache_dir)
            engine = PreviewEngine(project_path, cache)

            # Execute sketch
            result = engine.execute_sketch(sketch_file)

            # Should fail gracefully
            assert not result.success
            assert result.error is not None
            assert "SyntaxError" in result.error
            assert result.preview_url is None
            assert result.preview_path is None

            # Cache should remain clean (no broken entries)
            cache_entry = cache.get_current_preview("error_sketch")
            assert cache_entry is None

    def test_multiple_sketch_versions_caching(self):
        """Test versioning and caching of multiple sketch iterations."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            cache_dir = project_path / "cache"

            sketch_file = project_path / "versioned_sketch.py"
            cache = PreviewCache(cache_dir, max_versions_per_sketch=3)
            engine = PreviewEngine(project_path, cache)

            versions = []

            # Create multiple versions
            for i in range(5):
                sketch_content = f"""
import drawBot as drawbot

drawbot.size(200, 200)
drawbot.fill({i/10}, 0.5, 0.8)
drawbot.rect(10, 10, 180, 180)

drawbot.fill(1, 1, 1)
drawbot.font("Helvetica", 16)
drawbot.text("Version {i}", (50, 100))

drawbot.saveImage("output.png")
"""
                sketch_file.write_text(sketch_content)

                # Small delay to ensure different timestamps
                time.sleep(0.01)

                result = engine.execute_sketch(sketch_file)
                assert result.success, f"Version {i} failed: {result.error}"
                versions.append(result.version)

            # Should have limited number of versions due to cleanup
            available_versions = cache.get_available_versions("versioned_sketch")
            assert (
                len(available_versions) <= 3
            ), "Should respect max_versions_per_sketch"

            # Latest version should be available
            assert versions[-1] in available_versions, "Latest version should be kept"

            # Oldest versions should be cleaned up
            assert (
                versions[0] not in available_versions
            ), "Oldest versions should be cleaned"

    def test_cache_statistics_and_cleanup(self):
        """Test cache statistics and cleanup functionality."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            cache_dir = project_path / "cache"

            # Set small cache limits for testing
            cache = PreviewCache(cache_dir, max_total_size_mb=0.01)  # 10KB limit
            engine = PreviewEngine(project_path, cache)

            # Initial statistics
            stats = cache.get_statistics()
            assert stats["total_sketches"] == 0
            assert stats["total_versions"] == 0
            assert stats["total_size_mb"] == 0

            # Create multiple sketches to exceed size limit
            sketch_names = ["sketch_a", "sketch_b", "sketch_c"]

            for sketch_name in sketch_names:
                sketch_file = project_path / f"{sketch_name}.py"
                sketch_file.write_text(
                    f"""
import drawBot as drawbot

drawbot.size(400, 400)
drawbot.fill(0.5, 0.5, 0.5)
drawbot.rect(0, 0, 400, 400)

drawbot.fill(1, 1, 1)
drawbot.font("Helvetica", 24)
drawbot.text("{sketch_name}", (150, 200))

drawbot.saveImage("output.png")
"""
                )

                result = engine.execute_sketch(sketch_file)
                assert result.success

            # Cache should enforce size limits through cleanup
            final_stats = cache.get_statistics()
            assert (
                final_stats["total_size_mb"] <= final_stats["max_size_mb"] * 1.1
            )  # Allow small tolerance

            # Some sketches should remain
            assert final_stats["total_sketches"] > 0
            assert final_stats["total_versions"] > 0

    def test_concurrent_preview_generation(self):
        """Test concurrent preview generation safety."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            cache_dir = project_path / "cache"

            # Create multiple sketch files
            sketch_files = []
            for i in range(3):
                sketch_file = project_path / f"concurrent_sketch_{i}.py"
                sketch_file.write_text(
                    f"""
import time
import drawBot as drawbot

# Small delay to simulate processing time
time.sleep(0.1)

drawbot.size(200, 200)
drawbot.fill({i/10}, 0.5, 0.8)
drawbot.rect(20, 20, 160, 160)

drawbot.fill(1, 1, 1)
drawbot.font("Helvetica", 14)
drawbot.text("Sketch {i}", (70, 100))

drawbot.saveImage("output.png")
"""
                )
                sketch_files.append(sketch_file)

            cache = PreviewCache(cache_dir)
            engine = PreviewEngine(project_path, cache)

            import concurrent.futures
            import threading

            def generate_preview(sketch_file):
                return engine.execute_sketch(sketch_file)

            # Execute sketches concurrently
            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                futures = [executor.submit(generate_preview, sf) for sf in sketch_files]
                results = [
                    future.result()
                    for future in concurrent.futures.as_completed(futures)
                ]

            # All should succeed
            assert len(results) == 3
            assert all(
                result.success for result in results
            ), "All concurrent executions should succeed"

            # All should have unique versions
            versions = [result.version for result in results]
            assert len(set(versions)) == 3, "All executions should have unique versions"

            # Cache should contain all sketches
            final_stats = cache.get_statistics()
            assert final_stats["total_sketches"] == 3
            assert final_stats["total_versions"] == 3

    def test_resource_cleanup_after_operations(self):
        """Test that resources are properly cleaned up after operations."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            cache_dir = project_path / "cache"

            sketch_file = project_path / "cleanup_test_sketch.py"
            sketch_file.write_text(
                """
import drawBot as drawbot

drawbot.size(300, 300)
drawbot.fill(0.3, 0.7, 0.9)
drawbot.oval(50, 50, 200, 200)

drawbot.saveImage("output.png")
"""
            )

            cache = PreviewCache(cache_dir)
            engine = PreviewEngine(project_path, cache)

            # Track files before execution
            files_before = set(project_path.rglob("*"))

            # Execute sketch multiple times
            for i in range(3):
                result = engine.execute_sketch(sketch_file)
                assert result.success

            # Check file cleanup
            files_after = set(project_path.rglob("*"))
            new_files = files_after - files_before

            # Should only have cache files, no temp files should remain
            cache_files = [f for f in new_files if cache_dir in f.parents]
            temp_files = [
                f for f in new_files if cache_dir not in f.parents and f.suffix != ".py"
            ]

            assert len(cache_files) > 0, "Should have cache files"
            assert (
                len(temp_files) <= 1
            ), "Should not accumulate temp files (max 1 output file)"
