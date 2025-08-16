"""
SecurityMiddleware - Path validation and security enforcement for live preview server.
"""
import re
import time
import ipaddress
from pathlib import Path
from typing import List, Optional, Dict, Set
from dataclasses import dataclass
from collections import defaultdict
import fnmatch

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response


@dataclass
class ValidationResult:
    """Result of security validation."""
    valid: bool
    error: Optional[str] = None
    resolved_path: Optional[Path] = None


@dataclass
class RateLimitResult:
    """Result of rate limiting check."""
    allowed: bool
    error: Optional[str] = None
    remaining_requests: int = 0


@dataclass
class IPValidationResult:
    """Result of IP validation."""
    allowed: bool
    error: Optional[str] = None


@dataclass
class SecurityConfig:
    """Configuration for security middleware."""
    allowed_sketch_directories: List[Path]
    allowed_sketch_patterns: List[str] = None
    max_requests_per_minute: int = 60
    max_request_size_mb: float = 10.0
    bind_host: str = "127.0.0.1"
    allowed_client_ips: List[str] = None
    
    def __post_init__(self):
        """Post-initialization processing."""
        if self.allowed_sketch_patterns is None:
            self.allowed_sketch_patterns = ["*"]  # Allow all by default
        
        if self.allowed_client_ips is None:
            self.allowed_client_ips = ["127.0.0.1", "::1"]  # Localhost only by default


class SecurityMiddleware:
    """Security middleware for live preview server."""
    
    def __init__(self, config: SecurityConfig):
        """Initialize security middleware.
        
        Args:
            config: Security configuration
        """
        self.config = config
        
        # Rate limiting tracking
        self.client_requests: Dict[str, List[float]] = defaultdict(list)
        self.rate_limit_window = 60.0  # 1 minute
        
        # Compiled IP networks for efficiency
        self.allowed_networks = []
        for ip_spec in config.allowed_client_ips:
            try:
                if '/' in ip_spec:
                    self.allowed_networks.append(ipaddress.ip_network(ip_spec, strict=False))
                else:
                    self.allowed_networks.append(ipaddress.ip_network(f"{ip_spec}/32", strict=False))
            except ValueError:
                # Skip invalid IP specifications
                continue
    
    def validate_sketch_path(self, sketch_name: str) -> ValidationResult:
        """Validate a sketch path for security.
        
        Args:
            sketch_name: Name or path of the sketch to validate
            
        Returns:
            ValidationResult with validation status
        """
        try:
            # Sanitize sketch name
            sanitized_name = self.sanitize_sketch_name(sketch_name)
            
            # Check for path traversal attempts
            if self._is_path_traversal(sanitized_name):
                return ValidationResult(
                    valid=False,
                    error="Path traversal attempt detected"
                )
            
            # Find sketch file in allowed directories
            for allowed_dir in self.config.allowed_sketch_directories:
                sketch_path = self._find_sketch_file(allowed_dir, sanitized_name)
                if sketch_path:
                    # Verify the resolved path is within allowed directory
                    if self._is_path_within_directory(sketch_path, allowed_dir):
                        # Check if sketch name matches allowed patterns
                        if self._matches_allowed_patterns(sanitized_name):
                            return ValidationResult(
                                valid=True,
                                resolved_path=sketch_path
                            )
                        else:
                            return ValidationResult(
                                valid=False,
                                error=f"Sketch name '{sanitized_name}' does not match allowed patterns"
                            )
            
            return ValidationResult(
                valid=False,
                error=f"Sketch '{sanitized_name}' not found in allowed directories"
            )
            
        except Exception as e:
            return ValidationResult(
                valid=False,
                error=f"Path validation error: {str(e)}"
            )
    
    def _find_sketch_file(self, directory: Path, sketch_name: str) -> Optional[Path]:
        """Find sketch file in directory.
        
        Supports both flat and folder-based sketch structures:
        - Flat: directory/sketch_name.py
        - Folder-based: directory/sketch_name/sketch_name.py
        
        Args:
            directory: Directory to search in
            sketch_name: Sketch name (without extension)
            
        Returns:
            Path to sketch file if found, None otherwise
        """
        # Try flat structure with .py extension
        sketch_file = directory / f"{sketch_name}.py"
        if sketch_file.exists() and sketch_file.is_file():
            return sketch_file
        
        # Try exact name (in case extension was provided)
        if sketch_name.endswith('.py'):
            sketch_file = directory / sketch_name
            if sketch_file.exists() and sketch_file.is_file():
                return sketch_file
        
        # Try folder-based structure: directory/sketch_name/sketch_name.py
        folder_sketch_file = directory / sketch_name / f"{sketch_name}.py"
        if folder_sketch_file.exists() and folder_sketch_file.is_file():
            return folder_sketch_file
        
        return None
    
    def _is_path_traversal(self, path: str) -> bool:
        """Check if path contains traversal attempts.
        
        Args:
            path: Path to check
            
        Returns:
            True if path traversal detected
        """
        # Normalize and check for common traversal patterns
        normalized = path.replace('\\', '/').lower()
        
        traversal_patterns = [
            '../',
            '..\\',
            '..%2f',
            '..%5c',
            '%2e%2e%2f',
            '%2e%2e%5c',
            '..../',
            '....\\'
        ]
        
        for pattern in traversal_patterns:
            if pattern in normalized:
                return True
        
        # Check for null bytes and other control characters
        if '\x00' in path or any(ord(c) < 32 for c in path if c not in '\t\n\r'):
            return True
        
        return False
    
    def _is_path_within_directory(self, file_path: Path, directory: Path) -> bool:
        """Check if file path is within allowed directory.
        
        Args:
            file_path: File path to check
            directory: Allowed directory
            
        Returns:
            True if file is within directory
        """
        try:
            file_path.resolve().relative_to(directory.resolve())
            return True
        except ValueError:
            return False
    
    def _matches_allowed_patterns(self, sketch_name: str) -> bool:
        """Check if sketch name matches allowed patterns.
        
        Args:
            sketch_name: Sketch name to check
            
        Returns:
            True if name matches any allowed pattern
        """
        for pattern in self.config.allowed_sketch_patterns:
            if fnmatch.fnmatch(sketch_name, pattern):
                return True
        return False
    
    def sanitize_sketch_name(self, sketch_name: str) -> str:
        """Sanitize sketch name to prevent injection.
        
        Args:
            sketch_name: Raw sketch name
            
        Returns:
            Sanitized sketch name
        """
        # Remove dangerous characters
        sanitized = re.sub(r"[<>'\"$`;\x00-\x1f\x7f-\x9f]", "", sketch_name)
        
        # Remove line breaks and control characters
        sanitized = re.sub(r"[\n\r\t]", "", sanitized)
        
        # Limit length
        if len(sanitized) > 100:
            sanitized = sanitized[:100]
        
        return sanitized.strip()
    
    def check_rate_limit(self, client_ip: str) -> RateLimitResult:
        """Check if client is within rate limits.
        
        Args:
            client_ip: Client IP address
            
        Returns:
            RateLimitResult with rate limit status
        """
        current_time = time.time()
        
        # Clean old requests outside the window
        self.client_requests[client_ip] = [
            req_time for req_time in self.client_requests[client_ip]
            if current_time - req_time < self.rate_limit_window
        ]
        
        # Check current request count
        request_count = len(self.client_requests[client_ip])
        
        if request_count >= self.config.max_requests_per_minute:
            return RateLimitResult(
                allowed=False,
                error=f"Rate limit exceeded: {request_count} requests in last minute",
                remaining_requests=0
            )
        
        # Add current request
        self.client_requests[client_ip].append(current_time)
        
        return RateLimitResult(
            allowed=True,
            remaining_requests=self.config.max_requests_per_minute - request_count - 1
        )
    
    def validate_client_ip(self, client_ip: str) -> IPValidationResult:
        """Validate client IP against allowlist.
        
        Args:
            client_ip: Client IP address
            
        Returns:
            IPValidationResult with validation status
        """
        # Special handling for test client
        if client_ip == "testclient" and "testclient" in self.config.allowed_client_ips:
            return IPValidationResult(allowed=True)
        
        try:
            client_addr = ipaddress.ip_address(client_ip)
            
            for allowed_network in self.allowed_networks:
                if client_addr in allowed_network:
                    return IPValidationResult(allowed=True)
            
            return IPValidationResult(
                allowed=False,
                error=f"IP address {client_ip} not in allowlist"
            )
            
        except ValueError:
            # Check if it's a special test value
            if client_ip in self.config.allowed_client_ips:
                return IPValidationResult(allowed=True)
            
            return IPValidationResult(
                allowed=False,
                error=f"Invalid IP address: {client_ip}"
            )
    
    def validate_content_type(self, content_type: str) -> ValidationResult:
        """Validate content type for requests.
        
        Args:
            content_type: Content type to validate
            
        Returns:
            ValidationResult with validation status
        """
        allowed_types = [
            "text/plain",
            "text/html",
            "application/json",
            "application/x-www-form-urlencoded",
            "multipart/form-data"
        ]
        
        # Extract base content type (remove charset, etc.)
        base_type = content_type.split(';')[0].strip().lower()
        
        if base_type in allowed_types:
            return ValidationResult(valid=True)
        
        return ValidationResult(
            valid=False,
            error=f"Content type '{content_type}' not allowed"
        )
    
    def validate_request_size(self, content_length: int) -> ValidationResult:
        """Validate request size.
        
        Args:
            content_length: Size of request in bytes
            
        Returns:
            ValidationResult with validation status
        """
        max_size_bytes = self.config.max_request_size_mb * 1024 * 1024
        
        if content_length > max_size_bytes:
            return ValidationResult(
                valid=False,
                error=f"Request size {content_length} bytes exceeds limit {max_size_bytes} bytes"
            )
        
        return ValidationResult(valid=True)
    
    def get_middleware_class(self):
        """Get FastAPI middleware class.
        
        Returns:
            Middleware class for FastAPI
        """
        middleware = self
        
        class SecurityHTTPMiddleware(BaseHTTPMiddleware):
            async def dispatch(self, request: Request, call_next):
                # Get client IP
                client_ip = request.client.host if request.client else "unknown"
                
                # Validate client IP
                ip_validation = middleware.validate_client_ip(client_ip)
                if not ip_validation.allowed:
                    return Response(
                        content=f"Access denied: {ip_validation.error}",
                        status_code=403
                    )
                
                # Check rate limits
                rate_limit = middleware.check_rate_limit(client_ip)
                if not rate_limit.allowed:
                    return Response(
                        content=f"Rate limit exceeded: {rate_limit.error}",
                        status_code=429,
                        headers={"Retry-After": "60"}
                    )
                
                # Validate request size
                content_length = int(request.headers.get("content-length", 0))
                size_validation = middleware.validate_request_size(content_length)
                if not size_validation.valid:
                    return Response(
                        content=f"Request too large: {size_validation.error}",
                        status_code=413
                    )
                
                # Process request
                response = await call_next(request)
                
                # Add security headers
                response.headers["X-Content-Type-Options"] = "nosniff"
                response.headers["X-Frame-Options"] = "DENY"
                response.headers["X-XSS-Protection"] = "1; mode=block"
                response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
                
                return response
        
        return SecurityHTTPMiddleware