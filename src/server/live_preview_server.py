"""
LivePreviewServer - FastAPI application with core endpoints for live preview.
"""
import os
import time
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
import mimetypes
import hashlib

from fastapi import FastAPI, HTTPException, Response, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
import aiofiles
import psutil

from ..core.preview_engine import PreviewEngine, PreviewResult
from ..core.preview_cache import PreviewCache
from .security_middleware import SecurityMiddleware, SecurityConfig
from .live_preview_manager import LivePreviewManager
from .file_watch_integration import FileWatchIntegration


class LivePreviewServer:
    """FastAPI-based live preview server."""
    
    def __init__(self, project_path: Path, cache_dir: Path, host: str = "127.0.0.1", port: int = 8080):
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
            'total_executions': 0,
            'successful_executions': 0,
            'failed_executions': 0,
            'total_execution_time': 0.0
        }
        
        # Security configuration
        base_dir = self.project_path.parent  # Go up to project root
        self.security_config = SecurityConfig(
            allowed_sketch_directories=[
                self.project_path,  # sketches/
                base_dir / "examples"  # examples/
            ],
            bind_host=host,
            allowed_client_ips=["127.0.0.1", "::1", "testclient"]  # Add testclient for testing
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
            (base_dir / "examples", "example")
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
                        'name': sketch_name,
                        'file_path': str(sketch_file),
                        'size_bytes': stat.st_size,
                        'modified_at': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        'has_preview': current_preview is not None,
                        'preview_url': f"/sketch/{sketch_name}" if current_preview else None,
                        'source_type': source_type,
                        'category': source_type.title() + 's'
                    }
                    
                    if current_preview:
                        sketch_info['last_preview_generated'] = current_preview.created_at.isoformat()
                    
                    sketches.append(sketch_info)
            
            # Check for folder-based structure: directory/sketch_name/sketch_name.py
            for sketch_dir in scan_dir.iterdir():
                if sketch_dir.is_dir() and not sketch_dir.name.startswith('.'):
                    sketch_name = sketch_dir.name
                    sketch_file = sketch_dir / f"{sketch_name}.py"
                    
                    if sketch_file.exists() and sketch_file.is_file():
                        # Get basic file info
                        stat = sketch_file.stat()
                        
                        # Check if we have a cached preview
                        current_preview = self.cache.get_current_preview(sketch_name)
                        
                        sketch_info = {
                            'name': sketch_name,
                            'file_path': str(sketch_file),
                            'size_bytes': stat.st_size,
                            'modified_at': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                            'has_preview': current_preview is not None,
                            'preview_url': f"/sketch/{sketch_name}" if current_preview else None,
                            'source_type': source_type,
                            'category': source_type.title() + 's'
                        }
                        
                        if current_preview:
                            sketch_info['last_preview_generated'] = current_preview.created_at.isoformat()
                        
                        sketches.append(sketch_info)
            
            # Handle examples with nested structure (like examples/drawbotgrid/*.py)
            if source_type == "example":
                for category_dir in scan_dir.iterdir():
                    if category_dir.is_dir() and not category_dir.name.startswith('.'):
                        category_name = category_dir.name
                        for sketch_file in category_dir.glob("*.py"):
                            if sketch_file.is_file():
                                sketch_name = f"{category_name}_{sketch_file.stem}"
                                
                                # Get basic file info
                                stat = sketch_file.stat()
                                
                                # Check if we have a cached preview
                                current_preview = self.cache.get_current_preview(sketch_name)
                                
                                sketch_info = {
                                    'name': sketch_name,
                                    'display_name': f"{category_name}: {sketch_file.stem}",
                                    'file_path': str(sketch_file),
                                    'size_bytes': stat.st_size,
                                    'modified_at': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                                    'has_preview': current_preview is not None,
                                    'preview_url': f"/sketch/{sketch_name}" if current_preview else None,
                                    'source_type': source_type,
                                    'category': f"Examples: {category_name.title()}"
                                }
                                
                                if current_preview:
                                    sketch_info['last_preview_generated'] = current_preview.created_at.isoformat()
                                
                                sketches.append(sketch_info)
        
        # Sort by category first, then by modification time (newest first)
        sketches.sort(key=lambda s: (s['category'], s['modified_at']), reverse=True)
        
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
                success=False,
                error=f"Invalid sketch: {validation.error}"
            )
        
        # Update stats
        self.execution_stats['total_executions'] += 1
        
        try:
            # Execute sketch
            result = self.preview_engine.execute_sketch(validation.resolved_path)
            
            # Update stats
            if result.success:
                self.execution_stats['successful_executions'] += 1
            else:
                self.execution_stats['failed_executions'] += 1
            
            if result.execution_time:
                self.execution_stats['total_execution_time'] += result.execution_time
            
            return result
            
        except Exception as e:
            self.execution_stats['failed_executions'] += 1
            return PreviewResult(
                success=False,
                error=f"Execution failed: {str(e)}"
            )
    
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
            raise HTTPException(status_code=404, detail=f"Sketch not found: {sketch_name}")
        
        # Get current preview
        current_preview = self.cache.get_current_preview(sketch_name)
        
        status = {
            'sketch_name': sketch_name,
            'status': 'unknown',
            'last_updated': None,
            'execution_time': None,
            'error': None,
            'preview_url': None,
            'version': None
        }
        
        if current_preview:
            status.update({
                'status': 'success',
                'last_updated': current_preview.created_at.isoformat(),
                'preview_url': f"/preview/{current_preview.file_path.name}?v={current_preview.version}",
                'version': current_preview.version
            })
        
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
            'server_stats': {
                'uptime_seconds': uptime,
                'memory_usage_mb': memory_info.rss / (1024 * 1024),
                'cpu_percent': process.cpu_percent(),
                'active_sketches': cache_stats['total_sketches']
            },
            'execution_stats': self.execution_stats.copy(),
            'cache_stats': cache_stats
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
        version="2.0.0"
    )
    
    # Add security middleware
    app.add_middleware(server.security_middleware.get_middleware_class())
    
    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        metrics = server.get_server_metrics()
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "uptime": metrics['server_stats']['uptime_seconds'],
            "memory_usage_mb": round(metrics['server_stats']['memory_usage_mb'], 2),
            "active_sketches": metrics['server_stats']['active_sketches']
        }
    
    @app.get("/", response_class=HTMLResponse)
    async def sketch_list():
        """Main page showing available sketches."""
        sketches = server.get_available_sketches()
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>DrawBot Live Preview Studio</title>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <script src="https://cdn.tailwindcss.com"></script>
            <script>
                tailwind.config = {{
                    theme: {{
                        extend: {{
                            animation: {{
                                'float': 'float 6s ease-in-out infinite',
                                'pulse-slow': 'pulse 3s infinite',
                            }}
                        }}
                    }}
                }}
            </script>
            <style>
                @keyframes float {{
                    0%, 100% {{ transform: translateY(0px); }}
                    50% {{ transform: translateY(-10px); }}
                }}
            </style>
        </head>
        <body class="bg-gradient-to-br from-indigo-50 via-white to-cyan-50 min-h-screen">
            <!-- Hero Section -->
            <div class="relative overflow-hidden bg-gradient-to-r from-purple-600 to-blue-600 text-white">
                <div class="max-w-7xl mx-auto px-6 py-12">
                    <div class="text-center">
                        <h1 class="text-5xl font-bold mb-4 animate-float">
                            🎨 DrawBot Live Preview Studio
                        </h1>
                        <p class="text-xl text-purple-100 mb-8">
                            Real-time sketch development with instant visual feedback
                        </p>
                        
                        <!-- Stats Cards -->
                        <div class="grid grid-cols-1 md:grid-cols-4 gap-4 max-w-5xl mx-auto">
                            <div class="bg-white/10 backdrop-blur-sm rounded-xl p-6 border border-white/20">
                                <div class="text-3xl font-bold">{len([s for s in sketches if s.get('source_type') == 'sketch'])}</div>
                                <div class="text-purple-100">🎨 Your Sketches</div>
                            </div>
                            <div class="bg-white/10 backdrop-blur-sm rounded-xl p-6 border border-white/20">
                                <div class="text-3xl font-bold">{len([s for s in sketches if s.get('source_type') == 'example'])}</div>
                                <div class="text-purple-100">📚 Examples</div>
                            </div>
                            <div class="bg-white/10 backdrop-blur-sm rounded-xl p-6 border border-white/20">
                                <div class="text-3xl font-bold">{server.cache.get_statistics()['total_versions']}</div>
                                <div class="text-purple-100">Cached Versions</div>
                            </div>
                            <div class="bg-white/10 backdrop-blur-sm rounded-xl p-6 border border-white/20">
                                <div class="text-3xl font-bold">{server.execution_stats['successful_executions']}</div>
                                <div class="text-purple-100">Successful Runs</div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Main Content -->
            <div class="max-w-7xl mx-auto px-6 py-12">
        """
        
        if not sketches:
            html_content += """
                    <div class="col-span-full">
                        <div class="text-center py-20 bg-white rounded-2xl shadow-lg border border-gray-200">
                            <div class="text-8xl mb-6 animate-pulse-slow">🎨</div>
                            <h3 class="text-2xl font-bold text-gray-800 mb-4">No sketches found</h3>
                            <p class="text-gray-600 mb-8 max-w-md mx-auto">
                                Add Python files to your project directory to see them here. 
                                DrawBot sketches should use the .py extension.
                            </p>
                            <div class="bg-gradient-to-r from-blue-50 to-purple-50 rounded-xl p-6 max-w-lg mx-auto">
                                <h4 class="font-semibold text-gray-800 mb-2">Quick Start:</h4>
                                <p class="text-sm text-gray-600">
                                    Create a new sketch file in your sketches directory and it will appear here automatically.
                                </p>
                            </div>
                        </div>
                    </div>
            """
        else:
            # Group sketches by type
            user_sketches = [s for s in sketches if s.get('source_type') == 'sketch']
            examples = [s for s in sketches if s.get('source_type') == 'example']
            
            # User sketches section
            if user_sketches:
                html_content += """
                <div class="mb-12">
                    <div class="mb-8">
                        <h2 class="text-3xl font-bold text-gray-800 mb-2">🎨 Your Sketches</h2>
                        <p class="text-gray-600">Your creative work and personal projects</p>
                    </div>
                    
                    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
                """
                
                for sketch in user_sketches:
                    html_content += self._render_sketch_card(sketch)
                    
                html_content += """
                    </div>
                </div>
                """
            
            # Examples section  
            if examples:
                html_content += """
                <div class="mb-12">
                    <div class="mb-8">
                        <h2 class="text-3xl font-bold text-gray-800 mb-2">📚 Examples & Tutorials</h2>
                        <p class="text-gray-600">Learn DrawBot and explore creative techniques with these examples</p>
                    </div>
                    
                    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
                """
                
                for sketch in examples:
                    html_content += self._render_sketch_card(sketch)
                    
                html_content += """
                    </div>
                </div>
                """
    
    def _render_sketch_card(self, sketch):
        """Helper method to render a sketch card."""
        # Determine preview status with styling
        if sketch['has_preview']:
            preview_badge = '<div class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800"><span class="w-2 h-2 bg-green-500 rounded-full mr-1"></span>Preview Ready</div>'
            card_gradient = 'from-green-50 to-emerald-50'
        else:
            preview_badge = '<div class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-600"><span class="w-2 h-2 bg-gray-400 rounded-full mr-1"></span>No Preview</div>'
            card_gradient = 'from-blue-50 to-indigo-50'
        
        # Add category badge
        source_type = sketch.get('source_type', 'sketch')
        if source_type == 'example':
            category_badge = '<div class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-purple-100 text-purple-800 ml-2">📚 Example</div>'
            card_gradient = 'from-purple-50 to-pink-50'
        else:
            category_badge = '<div class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800 ml-2">🎨 Sketch</div>'
        
        # Determine display name
        display_name = sketch.get('display_name', sketch['name'])
        
        # Format file size nicely
        size_kb = sketch['size_bytes'] / 1024
        size_display = f"{size_kb:.1f} KB" if size_kb < 1024 else f"{size_kb/1024:.1f} MB"
        
        # Format date nicely
        date_display = sketch['modified_at'][:19].replace('T', ' ')
        
        return f"""
            <div class="group relative">
                <div class="bg-gradient-to-br {card_gradient} rounded-2xl shadow-lg border border-white/60 p-8 hover:shadow-2xl hover:scale-105 transition-all duration-300 h-full">
                    <div class="absolute top-4 right-4 flex flex-wrap gap-1">
                        {preview_badge}
                        {category_badge}
                    </div>
                    
                    <div class="mb-6">
                        <div class="text-6xl mb-4 opacity-20 group-hover:opacity-30 transition-opacity">🎨</div>
                        <h3 class="text-xl font-bold text-gray-800 mb-2">{display_name}</h3>
                        <div class="space-y-2 text-sm text-gray-600">
                            <div class="flex items-center gap-2">
                                <span class="text-blue-500">📁</span>
                                <span>{size_display}</span>
                            </div>
                            <div class="flex items-center gap-2">
                                <span class="text-purple-500">🕒</span>
                                <span>{date_display}</span>
                            </div>
                        </div>
                    </div>
                    
                    <a href="/sketch/{sketch['name']}" 
                       class="block w-full bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 text-white font-semibold py-3 px-6 rounded-xl shadow-lg hover:shadow-xl transition-all duration-200 text-center group-hover:scale-105">
                        <span class="flex items-center justify-center gap-2">
                            <span class="text-lg">🚀</span>
                            <span>Open Live Preview</span>
                        </span>
                    </a>
                </div>
            </div>
        """
        
        html_content += """
                </div>
            </div>
            
            <!-- Footer -->
            <footer class="bg-gradient-to-r from-gray-800 to-gray-900 text-white mt-20">
                <div class="max-w-7xl mx-auto px-6 py-12">
                    <div class="text-center">
                        <div class="text-4xl mb-4">🎨</div>
                        <h3 class="text-xl font-semibold mb-2">DrawBot Live Preview Studio</h3>
                        <p class="text-gray-400 mb-6">
                            Real-time sketch development with instant visual feedback
                        </p>
                        <div class="flex justify-center space-x-6 text-sm text-gray-400">
                            <a href="/metrics" class="hover:text-white transition-colors">📊 Metrics</a>
                            <span>•</span>
                            <span>Powered by DrawBot & FastAPI</span>
                            <span>•</span>
                            <span>Built with ❤️ for creative coding</span>
                        </div>
                    </div>
                </div>
            </footer>
        </body>
        </html>
        """
        
        # Return with no-cache headers
        return Response(
            content=html_content,
            media_type="text/html",
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )
    
    @app.get("/sketch/{sketch_name}", response_class=HTMLResponse)
    async def sketch_preview_page(sketch_name: str):
        """Live preview page for a specific sketch."""
        # Validate sketch exists
        validation = server.security_middleware.validate_sketch_path(sketch_name)
        if not validation.valid:
            raise HTTPException(status_code=404, detail=f"Sketch not found: {sketch_name}")
        
        # Get current preview
        current_preview = server.cache.get_current_preview(sketch_name)
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{sketch_name} - Live Preview</title>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <script src="https://cdn.tailwindcss.com"></script>
            <script>
                tailwind.config = {{
                    theme: {{
                        extend: {{
                            animation: {{
                                'pulse-slow': 'pulse 3s infinite',
                                'bounce-slow': 'bounce 2s infinite',
                            }}
                        }}
                    }}
                }}
            </script>
        </head>
        <body class="bg-gradient-to-br from-slate-50 to-slate-100 min-h-screen">
            <!-- WebSocket Status -->
            <div id="ws-status" class="fixed top-4 right-4 px-3 py-1 rounded-full text-xs font-medium z-50 transition-all duration-300">
                <span class="inline-block w-2 h-2 rounded-full mr-2"></span>
                <span>Connecting...</span>
            </div>
            
            <div class="container mx-auto max-w-6xl p-6">
                <!-- Header -->
                <div class="bg-white rounded-2xl shadow-lg border border-slate-200 p-8 mb-8">
                    <div class="flex items-center justify-between">
                        <div>
                            <h1 class="text-3xl font-bold text-slate-800 flex items-center gap-3">
                                🎨 <span class="bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">{sketch_name}</span>
                            </h1>
                            <p class="text-slate-600 mt-2">Live preview with automatic refresh</p>
                        </div>
                            <button onclick="executeSketch()" class="bg-gradient-to-r from-blue-500 to-blue-600 hover:from-blue-600 hover:to-blue-700 text-white font-semibold py-3 px-6 rounded-xl shadow-lg hover:shadow-xl transition-all duration-200 flex items-center gap-2">
                                <span class="text-lg">⚡</span> Execute Sketch
                            </button>
                            <button onclick="forceRefresh()" class="bg-gradient-to-r from-slate-500 to-slate-600 hover:from-slate-600 hover:to-slate-700 text-white font-semibold py-3 px-6 rounded-xl shadow-lg hover:shadow-xl transition-all duration-200 flex items-center gap-2">
                                <span class="text-lg">🔄</span> Refresh
                            </button>
                            <a href="/" class="bg-gradient-to-r from-purple-500 to-purple-600 hover:from-purple-600 hover:to-purple-700 text-white font-semibold py-3 px-6 rounded-xl shadow-lg hover:shadow-xl transition-all duration-200 flex items-center gap-2 no-underline">
                                <span class="text-lg">←</span> Back to List
                            </a>
                        </div>
                    </div>
                </div>
                
                <!-- Status Messages -->
                <div id="status" class="mb-6"></div>
                
                <!-- Preview Container -->
                <div class="bg-white rounded-2xl shadow-lg border border-slate-200 p-8 text-center">
                    <div class="mb-4">
                        <h2 class="text-xl font-semibold text-slate-700 flex items-center justify-center gap-2">
                            <span class="animate-pulse-slow">🖼️</span> Live Preview
                        </h2>
                    </div>
                    <div id="preview-content" class="flex flex-col items-center gap-4">
        """
        
        if current_preview:
            image_url = f"/preview/{current_preview.file_path.name}?v={current_preview.version}"
            html_content += f'''
                        <div class="relative inline-block">
                            <img src="{image_url}" alt="{sketch_name} preview" 
                                 class="rounded-xl shadow-2xl border-4 border-slate-100 hover:shadow-3xl transition-shadow duration-300" 
                                 id="preview-image">
                            <div class="absolute -top-2 -right-2 bg-green-500 text-white text-xs px-2 py-1 rounded-full shadow-lg">
                                ✨ Latest
                            </div>
                        </div>
                        <div class="text-sm text-slate-500 mt-4 bg-slate-50 px-4 py-2 rounded-lg">
                            <span class="font-medium">Last updated:</span> {current_preview.created_at.strftime('%Y-%m-%d %H:%M:%S')}
                        </div>
            '''
        else:
            html_content += '''
                        <div class="text-center py-12">
                            <div class="text-6xl mb-4 animate-bounce-slow">🎨</div>
                            <p class="text-slate-500 text-lg mb-6">No preview available yet</p>
                            <p class="text-slate-400">Click "Execute Sketch" to generate your first preview</p>
                        </div>
            '''
        
        html_content += """
                    </div>
                </div>
            </div>
            
            <script>
                let ws = null;
                let wsConnected = false;
                
                // WebSocket connection
                function connectWebSocket() {
                    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                    const wsUrl = `${protocol}//${window.location.host}/live/""" + sketch_name + """`;
                    
                    ws = new WebSocket(wsUrl);
                    
                    ws.onopen = function(event) {
                        wsConnected = true;
                        updateWSStatus(true);
                        updateStatus('🔗 Live preview connected', 'success');
                        console.log('WebSocket connected');
                    };
                    
                    ws.onmessage = function(event) {
                        const data = JSON.parse(event.data);
                        handleWebSocketMessage(data);
                    };
                    
                    ws.onclose = function(event) {
                        wsConnected = false;
                        updateStatus('🔌 Live preview disconnected', 'error');
                        console.log('WebSocket disconnected');
                        
                        // Attempt to reconnect after 3 seconds
                        setTimeout(connectWebSocket, 3000);
                    };
                    
                    ws.onerror = function(error) {
                        wsConnected = false;
                        updateWSStatus(false);
                        console.error('WebSocket error:', error);
                        updateStatus('❌ Connection error', 'error');
                    };
                    
                    ws.onclose = function(event) {
                        wsConnected = false;
                        updateWSStatus(false);
                        console.log('WebSocket disconnected');
                        updateStatus('🔌 Connection closed', 'error');
                    };
                }
                
                function handleWebSocketMessage(data) {
                    console.log('WebSocket message:', data);
                    
                    switch(data.type) {
                        case 'connection_confirmed':
                            updateStatus('✅ Live preview active', 'success');
                            break;
                            
                        case 'execution_started':
                            updateStatus('⚡ Executing sketch...', '');
                            break;
                            
                        case 'preview_updated':
                            if (data.status === 'success') {
                                updateStatus(`✅ Updated! (${data.execution_time?.toFixed(3) || '?'}s)`, 'success');
                                updatePreviewImage(data.image_url);
                            }
                            break;
                            
                        case 'execution_error':
                            updateStatus(`❌ Error: ${data.error}`, 'error');
                            showErrorPlaceholder(data.error);
                            break;
                            
                        case 'no_preview':
                            updateStatus('ℹ️ No preview available', '');
                            break;
                    }
                }
                
                function updateStatus(message, type) {
                    const statusDiv = document.getElementById('status');
                    let className = 'p-4 rounded-lg border-l-4 shadow-md mb-4';
                    let icon = '💡';
                    
                    if (type === 'success') {
                        className += ' bg-green-50 border-green-400 text-green-800';
                        icon = '✅';
                    } else if (type === 'error') {
                        className += ' bg-red-50 border-red-400 text-red-800';
                        icon = '❌';
                    } else {
                        className += ' bg-blue-50 border-blue-400 text-blue-800';
                        icon = '💡';
                    }
                    
                    statusDiv.innerHTML = `<div class="${className}">
                        <div class="flex items-center gap-2">
                            <span class="text-lg">${icon}</span>
                            <span class="font-medium">${message}</span>
                        </div>
                    </div>`;
                }
                
                function updateWSStatus(connected) {
                    const wsStatus = document.getElementById('ws-status');
                    const dot = wsStatus.querySelector('span:first-child');
                    const text = wsStatus.querySelector('span:last-child');
                    
                    if (connected) {
                        wsStatus.className = 'fixed top-4 right-4 px-3 py-1 rounded-full text-xs font-medium z-50 transition-all duration-300 bg-green-100 text-green-800 border border-green-200';
                        dot.className = 'inline-block w-2 h-2 rounded-full mr-2 bg-green-500 animate-pulse';
                        text.textContent = 'Connected';
                    } else {
                        wsStatus.className = 'fixed top-4 right-4 px-3 py-1 rounded-full text-xs font-medium z-50 transition-all duration-300 bg-red-100 text-red-800 border border-red-200';
                        dot.className = 'inline-block w-2 h-2 rounded-full mr-2 bg-red-500';
                        text.textContent = 'Disconnected';
                    }
                }
                
                function scaleImageForRetina(img) {
                    // Scale down high-resolution image by 1/3 for retina display
                    img.onload = function() {
                        const retinaScale = 3.0;
                        img.style.width = (this.naturalWidth / retinaScale) + 'px';
                        img.style.height = (this.naturalHeight / retinaScale) + 'px';
                    };
                }
                
                function updatePreviewImage(imageUrl) {
                    if (!imageUrl) return;
                    
                    const previewImg = document.getElementById('preview-image');
                    if (previewImg) {
                        previewImg.src = imageUrl + '&t=' + Date.now();
                        scaleImageForRetina(previewImg);
                    } else {
                        // Create new image element
                        const previewContent = document.getElementById('preview-content');
                        previewContent.innerHTML = `
                            <img src="${imageUrl}&t=${Date.now()}" alt=\"""" + sketch_name + """ preview" class="preview-image" id="preview-image">
                            <p>Live preview - saves automatically trigger updates</p>
                        `;
                        const newImg = document.getElementById('preview-image');
                        scaleImageForRetina(newImg);
                    }
                }
                
                function showErrorPlaceholder(errorMessage) {
                    const previewContent = document.getElementById('preview-content');
                    const errorDetails = errorMessage.split('\n');
                    const errorType = errorDetails[0].includes(':') ? errorDetails[0].split(':')[0] : 'Error';
                    const errorDescription = errorDetails[0].includes(':') ? errorDetails[0].split(':').slice(1).join(':').trim() : errorMessage;
                    
                    previewContent.innerHTML = `
                        <div class="error-placeholder bg-red-50 border-2 border-red-200 rounded-xl p-8 text-center">
                            <div class="text-6xl mb-4 opacity-60">🚫</div>
                            <h3 class="text-xl font-bold text-red-800 mb-3">Sketch Execution Failed</h3>
                            <div class="bg-white rounded-lg p-4 mb-4 border border-red-200">
                                <div class="text-sm font-mono text-red-700 mb-2">
                                    <span class="font-bold">${errorType}:</span> ${errorDescription}
                                </div>
                                ${errorDetails.length > 1 ? `
                                    <details class="text-xs text-red-600 mt-2">
                                        <summary class="cursor-pointer hover:text-red-800">Show full error details</summary>
                                        <pre class="mt-2 text-left whitespace-pre-wrap">${errorDetails.slice(1).join('\n')}</pre>
                                    </details>
                                ` : ''}
                            </div>
                            <div class="space-y-2 text-sm text-red-700">
                                <p class="font-medium">Common fixes:</p>
                                <ul class="text-left space-y-1 max-w-md mx-auto">
                                    <li>• Check for syntax errors (missing quotes, parentheses, indentation)</li>
                                    <li>• Verify DrawBot import: <code class="bg-red-100 px-1 rounded">import drawBot as drawbot</code></li>
                                    <li>• Ensure consistent variable naming throughout the script</li>
                                    <li>• Check that all functions are called correctly</li>
                                </ul>
                            </div>
                            <div class="mt-6 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
                                <p class="text-sm text-yellow-800">
                                    💡 <strong>Tip:</strong> Fix the Python errors in your sketch file, then press "Execute Sketch" to retry.
                                </p>
                            </div>
                        </div>
                    `;
                }
                
                async function executeSketch() {
                    try {
                        const response = await fetch(`/execute/""" + sketch_name + """`, {
                            method: 'POST'
                        });
                        
                        const result = await response.json();
                        
                        if (result.status === 'success') {
                            updateStatus(`✅ Manual execution: ${result.execution_time.toFixed(3)}s`, 'success');
                            if (result.preview_url) {
                                updatePreviewImage(result.preview_url);
                            }
                        } else {
                            updateStatus(`❌ Error: ${result.error}`, 'error');
                            showErrorPlaceholder(result.error);
                        }
                    } catch (error) {
                        updateStatus(`❌ Network error: ${error.message}`, 'error');
                    }
                }
                
                function forceRefresh() {
                    if (ws && wsConnected) {
                        ws.send(JSON.stringify({type: 'force_refresh'}));
                    } else {
                        updateStatus('❌ WebSocket not connected', 'error');
                    }
                }
                
                // Initialize WebSocket connection
                connectWebSocket();
                
                // Send ping every 30 seconds to keep connection alive
                setInterval(() => {
                    if (ws && wsConnected) {
                        ws.send(JSON.stringify({type: 'ping'}));
                    }
                }, 30000);
                
                // Scale initial image on page load
                document.addEventListener('DOMContentLoaded', function() {
                    const initialImg = document.getElementById('preview-image');
                    if (initialImg) {
                        scaleImageForRetina(initialImg);
                    }
                });
            </script>
        </body>
        </html>
        """
        
        # Return with no-cache headers
        return Response(
            content=html_content,
            media_type="text/html",
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )
    
    @app.post("/execute/{sketch_name}")
    async def execute_sketch(sketch_name: str):
        """Execute a sketch and return result."""
        result = server.execute_sketch(sketch_name)
        
        response_data = {
            'status': 'success' if result.success else 'error',
            'sketch_name': sketch_name,
            'timestamp': datetime.now().isoformat()
        }
        
        if result.success:
            response_data.update({
                'execution_time': result.execution_time,
                'preview_url': result.preview_url,
                'version': result.version
            })
        else:
            response_data['error'] = result.error
        
        return response_data
    
    @app.get("/status/{sketch_name}")
    async def get_sketch_status(sketch_name: str):
        """Get status of a specific sketch."""
        return server.get_sketch_status(sketch_name)
    
    @app.get("/preview/{filename}")
    async def serve_preview_image(filename: str, request: Request):
        """Serve cached preview images."""
        # Security: validate filename
        if '..' in filename or '/' in filename or '\\' in filename:
            raise HTTPException(status_code=400, detail="Invalid filename")
        
        image_path = server.cache_dir / filename
        
        if not image_path.exists() or not image_path.is_file():
            raise HTTPException(status_code=404, detail="Image not found")
        
        # Generate ETag based on file content
        file_stat = image_path.stat()
        etag = f'"{file_stat.st_mtime}-{file_stat.st_size}"'
        
        # Check If-None-Match header
        if_none_match = request.headers.get('if-none-match')
        if if_none_match == etag:
            return Response(status_code=304)
        
        # Determine content type
        content_type, _ = mimetypes.guess_type(str(image_path))
        if not content_type:
            content_type = 'application/octet-stream'
        
        return FileResponse(
            path=image_path,
            media_type=content_type,
            headers={
                'ETag': etag,
                'Cache-Control': 'no-cache, no-store, must-revalidate',
                'Pragma': 'no-cache',
                'Expires': '0',
                'Last-Modified': datetime.fromtimestamp(file_stat.st_mtime).strftime('%a, %d %b %Y %H:%M:%S GMT')
            }
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
            await websocket.close(code=1008, reason=f"Invalid sketch: {validation.error}")
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
                    await server.preview_manager.handle_client_message(websocket, message)
                    
            except WebSocketDisconnect:
                pass  # Normal disconnection
                
        except Exception as e:
            server.preview_manager.logger.error(f"WebSocket error for sketch '{sketch_name}': {e}")
        
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
            "total_watched": len(server.file_watch_integration.get_watched_sketches())
        }
        
        return {
            "connections": connection_stats,
            "file_watching": watch_stats
        }
    
    return app