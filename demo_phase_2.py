#!/usr/bin/env python3
"""
Demo script for Phase 2 - Web Server Foundation.
Shows the complete web server with live preview endpoints working.
"""
import tempfile
import time
from pathlib import Path
import threading
import requests
import signal
import sys

from src.server.live_preview_server import LivePreviewServer, create_app
import uvicorn


def create_demo_sketches(project_path: Path):
    """Create some demo sketches for testing."""
    
    # Simple geometric sketch
    geometric_sketch = project_path / "geometric_patterns.py"
    geometric_sketch.write_text('''
import drawBot as drawbot

# Create geometric patterns
drawbot.size(400, 400)

# Background
drawbot.fill(0.95, 0.95, 0.95)
drawbot.rect(0, 0, 400, 400)

# Colorful circles
colors = [
    (1, 0.3, 0.3),    # Red
    (0.3, 1, 0.3),    # Green  
    (0.3, 0.3, 1),    # Blue
    (1, 1, 0.3),      # Yellow
    (1, 0.3, 1),      # Magenta
    (0.3, 1, 1),      # Cyan
]

for i, (r, g, b) in enumerate(colors):
    x = (i % 3) * 120 + 60
    y = (i // 3) * 180 + 60
    
    drawbot.fill(r, g, b, 0.7)
    drawbot.oval(x, y, 80, 80)
    
    # Add small white circle in center
    drawbot.fill(1, 1, 1)
    drawbot.oval(x + 25, y + 25, 30, 30)

# Title
drawbot.fill(0.2, 0.2, 0.2)
drawbot.font("Helvetica-Bold", 24)
drawbot.text("Geometric Patterns", (100, 350))

drawbot.saveImage("output.png")
''')
    
    # Typography art sketch
    typography_sketch = project_path / "typography_art.py"
    typography_sketch.write_text('''
import drawBot as drawbot

# Typography art composition
drawbot.size(500, 300)

# Dark background
drawbot.fill(0.1, 0.1, 0.15)
drawbot.rect(0, 0, 500, 300)

# Large title
drawbot.fill(1, 1, 1)
drawbot.font("Helvetica-Bold", 48)
drawbot.text("LIVE", (50, 200))

# Colored accent
drawbot.fill(1, 0.4, 0.2)
drawbot.font("Helvetica-Bold", 48)
drawbot.text("PREVIEW", (200, 200))

# Subtitle
drawbot.fill(0.7, 0.7, 0.7)
drawbot.font("Helvetica", 18)
drawbot.text("Real-time DrawBot sketch rendering", (50, 160))

# Web server info
drawbot.fill(0.4, 0.8, 0.4)
drawbot.font("Helvetica-Bold", 14)
drawbot.text("Phase 2: Web Server Foundation", (50, 120))

# Tech stack
drawbot.fill(0.6, 0.6, 0.6)
drawbot.font("Helvetica", 12)
drawbot.text("FastAPI • Uvicorn • Security Middleware", (50, 100))

# URL
drawbot.fill(0.3, 0.6, 1)
drawbot.font("Monaco", 11)
drawbot.text("http://localhost:8080", (50, 80))

drawbot.saveImage("output.png")
''')
    
    # Error demonstration sketch (intentionally broken)
    error_sketch = project_path / "syntax_error_demo.py"
    error_sketch.write_text('''
import drawBot as drawbot

# This sketch has a syntax error for demo purposes
drawbot.size(300, 300)
drawbot.fill(1, 0, 0)
drawbot.rect(50, 50, 200, 200
# Missing closing parenthesis ^^^
''')
    
    print(f"✏️  Created demo sketches:")
    print(f"   📐 {geometric_sketch.name}")
    print(f"   🔤 {typography_sketch.name}")
    print(f"   ❌ {error_sketch.name} (intentionally broken)")
    
    return [geometric_sketch.stem, typography_sketch.stem, error_sketch.stem]


def test_api_endpoints(port: int):
    """Test the API endpoints."""
    base_url = f"http://localhost:{port}"
    
    print("\n🌐 Testing API endpoints...")
    
    try:
        # Test health endpoint
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.status_code == 200:
            health_data = response.json()
            print(f"   ✅ /health - Status: {health_data['status']}")
            print(f"      Memory: {health_data['memory_usage_mb']:.1f}MB")
        else:
            print(f"   ❌ /health - Status: {response.status_code}")
        
        # Test metrics endpoint
        response = requests.get(f"{base_url}/metrics", timeout=5)
        if response.status_code == 200:
            metrics_data = response.json()
            print(f"   ✅ /metrics - Cache: {metrics_data['cache_stats']['total_sketches']} sketches")
        else:
            print(f"   ❌ /metrics - Status: {response.status_code}")
        
        # Test sketch execution
        response = requests.post(f"{base_url}/execute/geometric_patterns", timeout=10)
        if response.status_code == 200:
            exec_data = response.json()
            if exec_data['status'] == 'success':
                print(f"   ✅ /execute/geometric_patterns - Time: {exec_data['execution_time']:.3f}s")
            else:
                print(f"   ⚠️  /execute/geometric_patterns - Error: {exec_data.get('error', 'Unknown')}")
        else:
            print(f"   ❌ /execute/geometric_patterns - Status: {response.status_code}")
        
        # Test error handling
        response = requests.post(f"{base_url}/execute/syntax_error_demo", timeout=10)
        if response.status_code == 200:
            exec_data = response.json()
            if exec_data['status'] == 'error':
                print(f"   ✅ /execute/syntax_error_demo - Error handling works")
            else:
                print(f"   ⚠️  /execute/syntax_error_demo - Expected error but got success")
        else:
            print(f"   ❌ /execute/syntax_error_demo - Status: {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"   ❌ API test failed: {e}")


def main():
    print("🎨 DrawBot Live Preview - Phase 2 Demo")
    print("=" * 50)
    
    # Set up temporary workspace
    with tempfile.TemporaryDirectory() as temp_dir:
        project_path = Path(temp_dir)
        cache_dir = project_path / "preview_cache"
        
        print(f"📁 Workspace: {project_path}")
        print(f"💾 Cache: {cache_dir}")
        
        # Create demo sketches
        sketch_names = create_demo_sketches(project_path)
        
        # Initialize server
        port = 8080
        server = LivePreviewServer(project_path, cache_dir, port=port)
        app = create_app(server)
        
        print(f"\n🚀 Starting web server on http://localhost:{port}")
        print("   Press Ctrl+C to stop the server")
        
        # Run server in background thread
        server_thread = threading.Thread(
            target=uvicorn.run,
            args=(app,),
            kwargs={
                "host": "127.0.0.1",
                "port": port,
                "log_level": "warning"  # Reduce log noise
            },
            daemon=True
        )
        
        server_thread.start()
        
        # Wait for server to start
        print("   Waiting for server to start...")
        time.sleep(2)
        
        # Test API endpoints
        test_api_endpoints(port)
        
        # Print usage instructions
        print(f"\n📖 Demo Features Available:")
        print(f"   🏠 Main page: http://localhost:{port}/")
        print(f"   📊 Health check: http://localhost:{port}/health")
        print(f"   📈 Metrics: http://localhost:{port}/metrics")
        print(f"   🎨 Live preview: http://localhost:{port}/sketch/geometric_patterns")
        print(f"   🔤 Typography demo: http://localhost:{port}/sketch/typography_art")
        print(f"   ❌ Error demo: http://localhost:{port}/sketch/syntax_error_demo")
        
        print(f"\n🎯 Phase 2 Features Demonstrated:")
        print(f"   ✅ FastAPI web server with multiple endpoints")
        print(f"   ✅ HTML pages with live preview interface")
        print(f"   ✅ JSON API for sketch execution and status")
        print(f"   ✅ Image serving with proper caching headers")
        print(f"   ✅ Security middleware with path validation")
        print(f"   ✅ Error handling and graceful degradation")
        print(f"   ✅ Server metrics and health monitoring")
        
        print(f"\n⏳ Server running... (Ctrl+C to stop)")
        
        # Set up signal handler for graceful shutdown
        def signal_handler(sig, frame):
            print(f"\n\n🛑 Shutting down server...")
            print(f"✅ Phase 2 Demo Complete!")
            print(f"🚀 Ready for Phase 3: Live Updates with WebSockets!")
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        
        # Keep main thread alive
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            signal_handler(None, None)


if __name__ == "__main__":
    main()