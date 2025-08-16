"""
Tests for SecurityMiddleware - Path validation and security enforcement.
"""
import pytest
import tempfile
from pathlib import Path
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.server.security_middleware import SecurityMiddleware, SecurityConfig


class TestSecurityMiddleware:
    """Test suite for SecurityMiddleware functionality."""

    def test_path_traversal_prevention(self):
        """Test blocking ../../../etc/passwd type attacks."""
        with tempfile.TemporaryDirectory() as temp_dir:
            allowed_dirs = [Path(temp_dir)]
            config = SecurityConfig(allowed_sketch_directories=allowed_dirs)
            middleware = SecurityMiddleware(config)
            
            # Test various path traversal attempts
            malicious_paths = [
                "../../../etc/passwd",
                "..\\..\\..\\windows\\system32\\config\\sam",
                "....//....//....//etc/passwd",
                "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
                "..%252f..%252f..%252fetc%252fpasswd",
                "..\\..\\..\\..\\..\\..\\..\\..\\..\\..\\..\\"
            ]
            
            for malicious_path in malicious_paths:
                result = middleware.validate_sketch_path(malicious_path)
                assert not result.valid, f"Path traversal not blocked: {malicious_path}"
                assert "path traversal" in result.error.lower()

    def test_allowed_sketch_directory_enforcement(self):
        """Test only approved directories are accessible."""
        with tempfile.TemporaryDirectory() as temp_dir:
            allowed_dir = Path(temp_dir) / "allowed"
            forbidden_dir = Path(temp_dir) / "forbidden"
            
            allowed_dir.mkdir()
            forbidden_dir.mkdir()
            
            # Create test files
            allowed_sketch = allowed_dir / "allowed_sketch.py"
            forbidden_sketch = forbidden_dir / "forbidden_sketch.py"
            allowed_sketch.write_text("print('allowed')")
            forbidden_sketch.write_text("print('forbidden')")
            
            config = SecurityConfig(allowed_sketch_directories=[allowed_dir])
            middleware = SecurityMiddleware(config)
            
            # Test allowed path
            result = middleware.validate_sketch_path("allowed_sketch")
            assert result.valid, "Allowed sketch should be accessible"
            assert result.resolved_path == allowed_sketch
            
            # Test forbidden path by trying to access the forbidden file directly
            result = middleware.validate_sketch_path(str(forbidden_sketch))
            assert not result.valid, "Forbidden sketch should not be accessible"

    def test_localhost_binding_enforcement(self):
        """Test security config enforces localhost binding."""
        config = SecurityConfig()
        
        # Default should be localhost only
        assert config.bind_host == "127.0.0.1"
        assert config.bind_host != "0.0.0.0"
        
        # Test that we can override for testing but get warning
        config_open = SecurityConfig(bind_host="0.0.0.0")
        assert config_open.bind_host == "0.0.0.0"

    def test_request_rate_limiting(self):
        """Test basic DoS protection."""
        config = SecurityConfig(max_requests_per_minute=5)
        middleware = SecurityMiddleware(config)
        
        # Simulate requests from same IP
        client_ip = "192.168.1.100"
        
        # First 5 requests should be allowed
        for i in range(5):
            result = middleware.check_rate_limit(client_ip)
            assert result.allowed, f"Request {i+1} should be allowed"
        
        # 6th request should be blocked
        result = middleware.check_rate_limit(client_ip)
        assert not result.allowed, "6th request should be rate limited"
        assert "rate limit" in result.error.lower()

    def test_multiple_client_rate_limiting(self):
        """Test rate limiting is per-client."""
        config = SecurityConfig(max_requests_per_minute=3)
        middleware = SecurityMiddleware(config)
        
        clients = ["192.168.1.100", "192.168.1.101", "192.168.1.102"]
        
        # Each client should get their own rate limit
        for client_ip in clients:
            for i in range(3):
                result = middleware.check_rate_limit(client_ip)
                assert result.allowed, f"Client {client_ip} request {i+1} should be allowed"
            
            # 4th request should be blocked for each client
            result = middleware.check_rate_limit(client_ip)
            assert not result.allowed, f"Client {client_ip} should be rate limited"

    def test_whitelist_sketch_validation(self):
        """Test sketch name validation against whitelist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)
            
            # Create valid sketches
            valid_sketches = ["sketch_a.py", "sketch_b.py", "valid_name.py"]
            for sketch in valid_sketches:
                (project_dir / sketch).write_text("print('test')")
            
            config = SecurityConfig(
                allowed_sketch_directories=[project_dir],
                allowed_sketch_patterns=["sketch_*", "valid_*"]
            )
            middleware = SecurityMiddleware(config)
            
            # Test valid sketches
            assert middleware.validate_sketch_path("sketch_a").valid
            assert middleware.validate_sketch_path("sketch_b").valid
            assert middleware.validate_sketch_path("valid_name").valid
            
            # Test invalid pattern (if we had this sketch)
            invalid_result = middleware.validate_sketch_path("invalid_name")
            # Should be invalid due to pattern mismatch
            assert not invalid_result.valid

    def test_file_extension_validation(self):
        """Test only .py files are allowed as sketches."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)
            
            # Create files with different extensions
            test_files = {
                "valid_sketch.py": True,
                "malicious_script.sh": False,
                "config_file.json": False,
                "image_file.png": False,
                "text_file.txt": False
            }
            
            for filename, should_be_valid in test_files.items():
                (project_dir / filename).write_text("content")
            
            config = SecurityConfig(allowed_sketch_directories=[project_dir])
            middleware = SecurityMiddleware(config)
            
            for filename, should_be_valid in test_files.items():
                sketch_name = filename.rsplit('.', 1)[0]  # Remove extension
                result = middleware.validate_sketch_path(sketch_name)
                
                if should_be_valid:
                    assert result.valid, f"{filename} should be valid"
                else:
                    # Should not find .py file for this name
                    assert not result.valid, f"{filename} should not be valid"

    def test_security_headers_middleware(self):
        """Test security headers are added to responses."""
        app = FastAPI()
        config = SecurityConfig()
        middleware = SecurityMiddleware(config)
        
        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}
        
        # Apply middleware
        app.add_middleware(middleware.get_middleware_class())
        
        client = TestClient(app)
        response = client.get("/test")
        
        # Check security headers
        assert "X-Content-Type-Options" in response.headers
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        
        assert "X-Frame-Options" in response.headers
        assert response.headers["X-Frame-Options"] == "DENY"
        
        assert "X-XSS-Protection" in response.headers
        assert response.headers["X-XSS-Protection"] == "1; mode=block"

    def test_content_type_validation(self):
        """Test content type validation for uploads."""
        config = SecurityConfig()
        middleware = SecurityMiddleware(config)
        
        # Test valid content types
        valid_types = [
            "text/plain",
            "application/json",
            "text/html"
        ]
        
        for content_type in valid_types:
            result = middleware.validate_content_type(content_type)
            assert result.valid, f"Content type {content_type} should be valid"
        
        # Test invalid content types
        invalid_types = [
            "application/x-executable",
            "application/octet-stream",
            "text/x-script.python"
        ]
        
        for content_type in invalid_types:
            result = middleware.validate_content_type(content_type)
            assert not result.valid, f"Content type {content_type} should be invalid"

    def test_ip_allowlist_enforcement(self):
        """Test IP allowlist enforcement."""
        allowed_ips = ["127.0.0.1", "192.168.1.0/24"]
        config = SecurityConfig(allowed_client_ips=allowed_ips)
        middleware = SecurityMiddleware(config)
        
        # Test allowed IPs
        allowed_test_ips = ["127.0.0.1", "192.168.1.100", "192.168.1.255"]
        for ip in allowed_test_ips:
            result = middleware.validate_client_ip(ip)
            assert result.allowed, f"IP {ip} should be allowed"
        
        # Test blocked IPs
        blocked_test_ips = ["10.0.0.1", "172.16.0.1", "8.8.8.8"]
        for ip in blocked_test_ips:
            result = middleware.validate_client_ip(ip)
            assert not result.allowed, f"IP {ip} should be blocked"

    def test_sketch_name_sanitization(self):
        """Test sketch name sanitization prevents injection."""
        config = SecurityConfig()
        middleware = SecurityMiddleware(config)
        
        # Test malicious sketch names
        malicious_names = [
            "sketch'; DROP TABLE users; --",
            "sketch<script>alert('xss')</script>",
            "sketch\x00null_byte",
            "sketch\n\rline_breaks",
            "sketch$(rm -rf /)",
            "sketch`command`substitution"
        ]
        
        for name in malicious_names:
            sanitized = middleware.sanitize_sketch_name(name)
            
            # Should remove malicious characters
            assert "'" not in sanitized
            assert "<" not in sanitized
            assert ">" not in sanitized
            assert "\x00" not in sanitized
            assert "\n" not in sanitized
            assert "\r" not in sanitized
            assert "$" not in sanitized
            assert "`" not in sanitized

    def test_maximum_request_size_enforcement(self):
        """Test maximum request size limits."""
        config = SecurityConfig(max_request_size_mb=1)  # 1MB limit
        middleware = SecurityMiddleware(config)
        
        # Test small request (should pass)
        small_data = b"x" * 1000  # 1KB
        result = middleware.validate_request_size(len(small_data))
        assert result.valid, "Small request should be allowed"
        
        # Test large request (should fail)
        large_data = b"x" * (2 * 1024 * 1024)  # 2MB
        result = middleware.validate_request_size(len(large_data))
        assert not result.valid, "Large request should be blocked"
        assert "size limit" in result.error.lower()

    def test_security_middleware_integration(self):
        """Test complete security middleware integration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)
            sketch_file = project_dir / "integration_test.py"
            sketch_file.write_text("print('integration test')")
            
            app = FastAPI()
            config = SecurityConfig(
                allowed_sketch_directories=[project_dir],
                max_requests_per_minute=10
            )
            middleware = SecurityMiddleware(config)
            
            @app.get("/test/{sketch_name}")
            async def test_endpoint(sketch_name: str):
                # Simulate sketch validation
                validation = middleware.validate_sketch_path(sketch_name)
                if not validation.valid:
                    return {"error": validation.error}, 400
                return {"sketch": sketch_name, "valid": True}
            
            # Apply security middleware
            app.add_middleware(middleware.get_middleware_class())
            
            client = TestClient(app)
            
            # Test valid request
            response = client.get("/test/integration_test")
            assert response.status_code == 200
            
            # Test invalid request
            response = client.get("/test/../../../etc/passwd")
            assert response.status_code != 200  # Should be blocked