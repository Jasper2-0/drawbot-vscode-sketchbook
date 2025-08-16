"""
Tests for PreviewCache - Preview image storage and cleanup system.
"""
import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.core.preview_cache import CacheEntry, PreviewCache


class TestPreviewCache:
    """Test suite for PreviewCache functionality."""

    def test_store_and_retrieve_preview(self):
        """Test basic preview storage and retrieval."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache = PreviewCache(temp_dir)

            # Create mock image data
            image_data = b"fake_png_data_12345"
            sketch_name = "test_sketch"

            # Store preview
            result = cache.store_preview(sketch_name, image_data)

            assert result.success
            assert result.preview_url is not None
            assert result.preview_path.exists()
            assert result.version > 0

            # Retrieve preview
            entry = cache.get_current_preview(sketch_name)
            assert entry is not None
            assert entry.version == result.version
            assert entry.file_path.exists()

            # Verify content
            stored_data = entry.file_path.read_bytes()
            assert stored_data == image_data

    def test_version_management(self):
        """Test versioned preview storage."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache = PreviewCache(temp_dir)
            sketch_name = "versioned_sketch"

            # Store multiple versions
            image_data_v1 = b"version_1_data"
            image_data_v2 = b"version_2_data"
            image_data_v3 = b"version_3_data"

            result_v1 = cache.store_preview(sketch_name, image_data_v1)
            time.sleep(0.01)  # Ensure different timestamps
            result_v2 = cache.store_preview(sketch_name, image_data_v2)
            time.sleep(0.01)
            result_v3 = cache.store_preview(sketch_name, image_data_v3)

            # Versions should be increasing
            assert result_v2.version > result_v1.version
            assert result_v3.version > result_v2.version

            # Current should be latest
            current = cache.get_current_preview(sketch_name)
            assert current.version == result_v3.version

            # Should be able to retrieve specific versions
            v1_entry = cache.get_preview_version(sketch_name, result_v1.version)
            assert v1_entry is not None
            assert v1_entry.file_path.read_bytes() == image_data_v1

    def test_automatic_cleanup_old_previews(self):
        """Test LRU eviction and age-based cleanup."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Set low max_versions for testing
            cache = PreviewCache(temp_dir, max_versions_per_sketch=3)
            sketch_name = "cleanup_test_sketch"

            # Store more versions than the limit
            versions = []
            for i in range(5):
                data = f"version_{i}_data".encode()
                result = cache.store_preview(sketch_name, data)
                versions.append(result.version)
                time.sleep(0.01)

            # Only the last 3 versions should remain
            remaining_versions = cache.get_available_versions(sketch_name)
            assert len(remaining_versions) <= 3

            # Latest versions should be kept
            assert versions[-1] in remaining_versions  # Most recent
            assert versions[-2] in remaining_versions  # Second most recent

            # Oldest versions should be cleaned up
            assert versions[0] not in remaining_versions
            assert versions[1] not in remaining_versions

    def test_disk_space_limit_enforcement(self):
        """Test maximum cache size limits."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Set very small cache size for testing
            cache = PreviewCache(temp_dir, max_total_size_mb=0.001)  # 1KB limit

            # Create large-ish image data
            large_image_data = b"x" * 2000  # 2KB

            # Store multiple large previews
            sketch_names = ["sketch_1", "sketch_2", "sketch_3"]
            for sketch_name in sketch_names:
                cache.store_preview(sketch_name, large_image_data)

            # Cache should enforce size limits
            total_size = cache.get_total_cache_size()
            assert (
                total_size <= 0.01
            )  # Should be close to or under limit (with some tolerance)

            # Some older entries should be evicted
            all_entries = []
            for sketch_name in sketch_names:
                current = cache.get_current_preview(sketch_name)
                if current:
                    all_entries.append(current)

            # Not all sketches should have entries (due to size limit)
            assert len(all_entries) < len(sketch_names)

    def test_concurrent_access_safety(self):
        """Test thread-safe cache operations."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache = PreviewCache(temp_dir)
            sketch_name = "concurrent_test_sketch"

            results = []
            errors = []

            def store_preview_worker(worker_id):
                try:
                    for i in range(10):
                        data = f"worker_{worker_id}_iteration_{i}".encode()
                        result = cache.store_preview(sketch_name, data)
                        results.append(result)
                        time.sleep(0.001)  # Small delay
                except Exception as e:
                    errors.append(e)

            # Run multiple workers concurrently
            threads = []
            for worker_id in range(3):
                thread = threading.Thread(
                    target=store_preview_worker, args=(worker_id,)
                )
                threads.append(thread)
                thread.start()

            # Wait for all workers to complete
            for thread in threads:
                thread.join()

            # Should not have any errors
            assert len(errors) == 0

            # All operations should have succeeded
            assert len(results) == 30  # 3 workers * 10 iterations
            assert all(result.success for result in results)

            # Final state should be consistent
            current = cache.get_current_preview(sketch_name)
            assert current is not None

    def test_cache_metadata_persistence(self):
        """Test cache metadata survives cache recreation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            sketch_name = "persistent_sketch"
            image_data = b"persistent_image_data"

            # Create cache and store preview
            cache1 = PreviewCache(temp_dir)
            result = cache1.store_preview(sketch_name, image_data)
            original_version = result.version

            # Recreate cache (simulates restart)
            cache2 = PreviewCache(temp_dir)

            # Should be able to retrieve the same preview
            entry = cache2.get_current_preview(sketch_name)
            assert entry is not None
            assert entry.version == original_version
            assert entry.file_path.read_bytes() == image_data

    def test_cache_directory_creation(self):
        """Test cache creates necessary directories."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Use non-existent subdirectory
            cache_dir = Path(temp_dir) / "nonexistent" / "cache"

            cache = PreviewCache(cache_dir)

            # Directory should be created
            assert cache_dir.exists()
            assert cache_dir.is_dir()

            # Should be able to store previews
            result = cache.store_preview("test", b"test_data")
            assert result.success

    def test_invalid_image_data_handling(self):
        """Test handling of invalid image data."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache = PreviewCache(temp_dir)

            # Test empty data
            result = cache.store_preview("empty_test", b"")
            assert not result.success
            assert "empty" in result.error.lower()

            # Test None data
            result = cache.store_preview("none_test", None)
            assert not result.success
            assert "invalid" in result.error.lower()

    def test_get_cache_statistics(self):
        """Test cache statistics reporting."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache = PreviewCache(temp_dir)

            # Initially empty
            stats = cache.get_statistics()
            assert stats["total_sketches"] == 0
            assert stats["total_versions"] == 0
            assert stats["total_size_mb"] == 0

            # Add some previews
            sketches = ["sketch_1", "sketch_2", "sketch_3"]
            for sketch in sketches:
                cache.store_preview(sketch, f"data_for_{sketch}".encode())
                # Add second version for sketch_1
                if sketch == "sketch_1":
                    cache.store_preview(sketch, f"updated_data_for_{sketch}".encode())

            # Check updated stats
            stats = cache.get_statistics()
            assert stats["total_sketches"] == 3
            assert stats["total_versions"] >= 4  # 3 sketches + 1 extra version
            assert stats["total_size_mb"] > 0

    def test_cache_url_generation(self):
        """Test preview URL generation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache = PreviewCache(temp_dir)
            sketch_name = "url_test_sketch"

            result = cache.store_preview(sketch_name, b"test_image_data")

            assert result.preview_url is not None
            assert sketch_name in result.preview_url
            assert result.preview_url.endswith(".png")
            assert (
                f"v={result.version}" in result.preview_url
            )  # Version in query string
