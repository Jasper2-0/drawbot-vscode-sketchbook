"""
Tests for LivePreviewServer - FastAPI application with core endpoints.
"""
import json
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.core.preview_cache import PreviewCache
from src.server.live_preview_server import LivePreviewServer, create_app


class TestLivePreviewServer:
    """Test suite for LivePreviewServer functionality."""

    def test_health_endpoint_response(self):
        """Test /health endpoint returns server status."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            cache_dir = project_path / "cache"

            server = LivePreviewServer(project_path, cache_dir)
            app = create_app(server)
            client = TestClient(app)

            response = client.get("/health")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert "uptime" in data
            assert "memory_usage_mb" in data
            assert "active_sketches" in data

    def test_serve_preview_image(self):
        """Test GET /preview/{sketch_name}.png serves cached images."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            cache_dir = project_path / "cache"

            # Create a cached preview
            cache = PreviewCache(cache_dir)
            image_data = b"\x89PNG\r\n\x1a\n" + b"fake_png_data" * 100
            cache_result = cache.store_preview("test_sketch", image_data)

            server = LivePreviewServer(project_path, cache_dir)
            app = create_app(server)
            client = TestClient(app)

            # Extract filename from preview URL
            filename = cache_result.preview_url.split("/")[-1].split("?")[0]
            response = client.get(f"/preview/{filename}")

            assert response.status_code == 200
            assert response.headers["content-type"] == "image/png"
            assert response.content == image_data

    def test_sketch_status_endpoint(self):
        """Test GET /status/{sketch_name} returns execution status."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            cache_dir = project_path / "cache"

            # Create a test sketch
            sketch_file = project_path / "status_test_sketch.py"
            sketch_file.write_text(
                """
import drawBot as drawbot
drawbot.size(200, 200)
drawbot.fill(1, 0, 0)
drawbot.rect(50, 50, 100, 100)
drawbot.saveImage("output.png")
"""
            )

            server = LivePreviewServer(project_path, cache_dir)
            app = create_app(server)
            client = TestClient(app)

            # Execute sketch first
            server.execute_sketch("status_test_sketch")

            response = client.get("/status/status_test_sketch")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] in ["success", "error", "executing"]
            assert "last_updated" in data
            assert "execution_time" in data

    def test_sketch_list_endpoint(self):
        """Test GET / returns available sketches."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            cache_dir = project_path / "cache"

            # Create multiple sketch files
            sketch_names = ["sketch_a", "sketch_b", "sketch_c"]
            for name in sketch_names:
                sketch_file = project_path / f"{name}.py"
                sketch_file.write_text('print("hello")')

            server = LivePreviewServer(project_path, cache_dir)
            app = create_app(server)
            client = TestClient(app)

            response = client.get("/")

            assert response.status_code == 200
            assert response.headers["content-type"] == "text/html; charset=utf-8"

            # Check that sketch names appear in the HTML
            content = response.text
            for name in sketch_names:
                assert name in content

    def test_404_for_invalid_sketch(self):
        """Test proper 404 handling for non-existent sketches."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            cache_dir = project_path / "cache"

            server = LivePreviewServer(project_path, cache_dir)
            app = create_app(server)
            client = TestClient(app)

            # Test invalid sketch status
            response = client.get("/status/nonexistent_sketch")
            assert response.status_code == 404

            # Test invalid preview image
            response = client.get("/preview/nonexistent_image.png")
            assert response.status_code == 404

    def test_cache_headers_on_images(self):
        """Test ETag and cache headers on preview images."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            cache_dir = project_path / "cache"

            # Create cached preview
            cache = PreviewCache(cache_dir)
            image_data = b"\x89PNG\r\n\x1a\n" + b"test_image_data"
            cache_result = cache.store_preview("cache_test_sketch", image_data)

            server = LivePreviewServer(project_path, cache_dir)
            app = create_app(server)
            client = TestClient(app)

            filename = cache_result.preview_url.split("/")[-1].split("?")[0]
            response = client.get(f"/preview/{filename}")

            assert response.status_code == 200
            assert "etag" in response.headers
            assert "cache-control" in response.headers

            # Test conditional request with ETag
            etag = response.headers["etag"]
            response2 = client.get(
                f"/preview/{filename}", headers={"if-none-match": etag}
            )
            assert response2.status_code == 304  # Not Modified

    def test_sketch_page_endpoint(self):
        """Test GET /sketch/{sketch_name} returns preview page."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            cache_dir = project_path / "cache"

            # Create a test sketch
            sketch_file = project_path / "page_test_sketch.py"
            sketch_file.write_text('print("test sketch")')

            server = LivePreviewServer(project_path, cache_dir)
            app = create_app(server)
            client = TestClient(app)

            response = client.get("/sketch/page_test_sketch")

            assert response.status_code == 200
            assert response.headers["content-type"] == "text/html; charset=utf-8"

            content = response.text
            assert "page_test_sketch" in content
            assert "Live Preview" in content

    def test_execute_sketch_endpoint(self):
        """Test POST /execute/{sketch_name} triggers sketch execution."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            cache_dir = project_path / "cache"

            # Create a test sketch
            sketch_file = project_path / "execute_test_sketch.py"
            sketch_file.write_text(
                """
import drawBot as drawbot
drawbot.size(150, 150)
drawbot.fill(0, 1, 0)
drawbot.oval(25, 25, 100, 100)
drawbot.saveImage("output.png")
"""
            )

            server = LivePreviewServer(project_path, cache_dir)
            app = create_app(server)
            client = TestClient(app)

            response = client.post("/execute/execute_test_sketch")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] in ["success", "error"]
            if data["status"] == "success":
                assert "preview_url" in data
                assert "execution_time" in data

    def test_server_metrics_endpoint(self):
        """Test GET /metrics returns server performance metrics."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            cache_dir = project_path / "cache"

            server = LivePreviewServer(project_path, cache_dir)
            app = create_app(server)
            client = TestClient(app)

            response = client.get("/metrics")

            assert response.status_code == 200
            data = response.json()
            assert "cache_stats" in data
            assert "server_stats" in data
            assert "execution_stats" in data

    def test_error_handling_for_broken_sketch(self):
        """Test error response for sketches with syntax errors."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            cache_dir = project_path / "cache"

            # Create broken sketch
            sketch_file = project_path / "broken_sketch.py"
            sketch_file.write_text(
                """
import drawBot as drawbot
drawbot.size(200, 200
# Missing closing parenthesis
"""
            )

            server = LivePreviewServer(project_path, cache_dir)
            app = create_app(server)
            client = TestClient(app)

            response = client.post("/execute/broken_sketch")

            assert response.status_code == 200  # Server handles error gracefully
            data = response.json()
            assert data["status"] == "error"
            assert "error" in data
            assert "SyntaxError" in data["error"]

    def test_concurrent_sketch_execution(self):
        """Test handling of concurrent sketch execution requests."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            cache_dir = project_path / "cache"

            # Create test sketches
            for i in range(3):
                sketch_file = project_path / f"concurrent_sketch_{i}.py"
                sketch_file.write_text(
                    f"""
import time
import drawBot as drawbot

time.sleep(0.1)  # Simulate processing time

drawbot.size(100, 100)
drawbot.fill({i/10}, 0.5, 0.8)
drawbot.rect(10, 10, 80, 80)
drawbot.saveImage("output.png")
"""
                )

            server = LivePreviewServer(project_path, cache_dir)
            app = create_app(server)
            client = TestClient(app)

            import concurrent.futures
            import threading

            def execute_sketch(sketch_name):
                return client.post(f"/execute/{sketch_name}")

            # Execute sketches concurrently
            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                futures = [
                    executor.submit(execute_sketch, f"concurrent_sketch_{i}")
                    for i in range(3)
                ]
                results = [
                    future.result()
                    for future in concurrent.futures.as_completed(futures)
                ]

            # All requests should complete successfully
            assert len(results) == 3
            assert all(result.status_code == 200 for result in results)

    def test_static_file_serving_security(self):
        """Test that static file serving prevents path traversal."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            cache_dir = project_path / "cache"

            server = LivePreviewServer(project_path, cache_dir)
            app = create_app(server)
            client = TestClient(app)

            # Try path traversal attacks
            malicious_paths = [
                "../../../etc/passwd",
                "..%2F..%2F..%2Fetc%2Fpasswd",
                "....//....//....//etc/passwd",
            ]

            for path in malicious_paths:
                response = client.get(f"/preview/{path}")
                assert response.status_code in [
                    404,
                    400,
                ], f"Path traversal not blocked: {path}"
