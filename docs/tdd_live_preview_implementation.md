# TDD Implementation Plan: Live Preview Web Server

**Project**: DrawBot VSCode Sketchbook - Live Preview Feature
**Approach**: Web server + WebSocket real-time updates
**Timeline**: 4 phases, incremental delivery
**Test Strategy**: TDD with comprehensive unit and integration tests

---

## 🎯 Phase 1: Core Preview Engine (Week 1)

### Objective
Build the foundational preview execution system that can generate static previews.

### Components to Build
1. **PreviewEngine** - Coordinates sketch execution and image generation
2. **PreviewCache** - Manages preview image storage and cleanup
3. **ImageConverter** - PDF to PNG conversion pipeline

### Test Cases

#### PreviewEngine Tests
```python
class TestPreviewEngine:
    def test_execute_simple_sketch_success(self):
        # Test basic sketch execution and preview generation

    def test_execute_sketch_with_syntax_error(self):
        # Test error handling for broken sketches

    def test_execute_sketch_timeout_protection(self):
        # Test timeout mechanism for infinite loops

    def test_concurrent_execution_cancellation(self):
        # Test that new executions cancel previous ones

    def test_resource_cleanup_after_execution(self):
        # Test memory and file cleanup

    def test_virtual_environment_detection(self):
        # Test proper Python executable selection
```

#### PreviewCache Tests
```python
class TestPreviewCache:
    def test_store_and_retrieve_preview(self):
        # Test basic preview storage and retrieval

    def test_version_management(self):
        # Test versioned preview storage

    def test_automatic_cleanup_old_previews(self):
        # Test LRU eviction and age-based cleanup

    def test_disk_space_limit_enforcement(self):
        # Test maximum cache size limits

    def test_concurrent_access_safety(self):
        # Test thread-safe cache operations
```

#### ImageConverter Tests
```python
class TestImageConverter:
    def test_convert_pdf_to_png(self):
        # Test basic PDF to PNG conversion

    def test_handle_invalid_pdf_data(self):
        # Test graceful handling of corrupted PDFs

    def test_conversion_with_different_sizes(self):
        # Test handling various canvas sizes

    def test_conversion_performance_benchmarks(self):
        # Test conversion speed meets requirements (<100ms)

    def test_memory_usage_during_conversion(self):
        # Test memory efficiency
```

### Success Criteria
- ✅ Can execute sketch and generate PNG preview
- ✅ Proper error handling for all sketch execution failures
- ✅ Resource cleanup prevents memory leaks
- ✅ Preview cache manages disk usage efficiently
- ✅ All tests pass with >90% code coverage

### Integration Target
```python
# End-to-end test for Phase 1
def test_phase_1_integration():
    engine = PreviewEngine()
    cache = PreviewCache()

    # Execute sketch and get preview
    result = engine.execute_sketch("test_sketch.py", cache)
    assert result.success
    assert result.preview_url.endswith(".png")
    assert Path(result.preview_path).exists()
```

---

## 🌐 Phase 2: Web Server Foundation (Week 2)

### Objective
Build FastAPI web server with static preview serving and basic health endpoints.

### Components to Build
1. **LivePreviewServer** - FastAPI application with core endpoints
2. **SecurityMiddleware** - Path validation and security enforcement
3. **ServerManager** - Server lifecycle and port management

### Test Cases

#### LivePreviewServer Tests
```python
class TestLivePreviewServer:
    def test_health_endpoint_response(self):
        # Test /health endpoint returns server status

    def test_serve_preview_image(self):
        # Test GET /preview/{sketch_name}.png

    def test_sketch_status_endpoint(self):
        # Test GET /status/{sketch_name}

    def test_sketch_list_endpoint(self):
        # Test GET / returns available sketches

    def test_404_for_invalid_sketch(self):
        # Test proper 404 handling

    def test_cache_headers_on_images(self):
        # Test ETag and cache headers
```

#### SecurityMiddleware Tests
```python
class TestSecurityMiddleware:
    def test_path_traversal_prevention(self):
        # Test blocking ../../../etc/passwd type attacks

    def test_allowed_sketch_directory_enforcement(self):
        # Test only approved directories accessible

    def test_localhost_binding_only(self):
        # Test server only binds to 127.0.0.1

    def test_request_rate_limiting(self):
        # Test basic DoS protection
```

#### ServerManager Tests
```python
class TestServerManager:
    def test_find_available_port(self):
        # Test automatic port detection

    def test_existing_server_detection(self):
        # Test detection of running servers

    def test_graceful_shutdown(self):
        # Test cleanup on SIGTERM/SIGINT

    def test_pid_file_management(self):
        # Test PID file creation and cleanup
```

### Success Criteria
- ✅ Web server serves static previews reliably
- ✅ Security middleware prevents path traversal attacks
- ✅ Port conflict resolution works automatically
- ✅ Health monitoring endpoints provide useful diagnostics
- ✅ Server starts/stops cleanly with proper cleanup

### Integration Target
```python
# End-to-end test for Phase 2
async def test_phase_2_integration():
    async with TestClient(app) as client:
        # Generate a preview
        engine.execute_sketch("test_sketch.py")

        # Serve via web server
        response = await client.get("/preview/test_sketch.png")
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/png"
```

---

## 🔄 Phase 3: Live Updates with WebSockets (Week 3)

### Objective
Add real-time preview updates using WebSockets and file watching.

### Components to Build
1. **LivePreviewManager** - WebSocket connection management
2. **FileWatchIntegration** - Bridge between FileWatcher and preview system
3. **WebSocketBroadcaster** - Real-time update distribution

### Test Cases

#### LivePreviewManager Tests
```python
class TestLivePreviewManager:
    def test_websocket_connection_lifecycle(self):
        # Test connect, subscribe, disconnect flow

    def test_multiple_clients_same_sketch(self):
        # Test multiple browsers watching same sketch

    def test_client_room_management(self):
        # Test sketch-specific client grouping

    def test_connection_cleanup_on_disconnect(self):
        # Test resource cleanup when clients disconnect

    def test_broadcast_to_specific_sketch_clients(self):
        # Test targeted message broadcasting
```

#### FileWatchIntegration Tests
```python
class TestFileWatchIntegration:
    def test_file_change_triggers_preview_update(self):
        # Test file change → execution → broadcast flow

    def test_debounced_rapid_file_changes(self):
        # Test rapid saves only trigger one update

    def test_execution_error_handling_during_watch(self):
        # Test WebSocket error broadcasts

    def test_watch_start_stop_with_clients(self):
        # Test FileWatcher lifecycle management

    def test_multiple_sketch_watching(self):
        # Test watching multiple sketches simultaneously
```

#### WebSocketBroadcaster Tests
```python
class TestWebSocketBroadcaster:
    def test_broadcast_preview_update_message(self):
        # Test preview update WebSocket messages

    def test_broadcast_execution_error_message(self):
        # Test error state WebSocket messages

    def test_connection_resilience(self):
        # Test handling of dropped connections

    def test_message_serialization(self):
        # Test JSON message format consistency
```

### Success Criteria
- ✅ File changes trigger automatic preview updates
- ✅ WebSocket connections handle multiple concurrent clients
- ✅ Real-time updates arrive within 500ms of file save
- ✅ Error states broadcast properly to all connected clients
- ✅ System handles client disconnections gracefully

### Integration Target
```python
# End-to-end test for Phase 3
async def test_phase_3_integration():
    # Start live preview for sketch
    manager = LivePreviewManager()

    # Connect WebSocket client
    async with websockets.connect("ws://localhost:8080/live/test_sketch") as ws:
        # Modify sketch file
        sketch_file.write_text('updated sketch content')

        # Should receive update message
        message = await asyncio.wait_for(ws.recv(), timeout=2.0)
        data = json.loads(message)
        assert data["type"] == "preview_updated"
        assert "image_url" in data
```

---

## 🚀 Phase 4: CLI Integration & Polish (Week 4)

### Objective
Complete CLI interface and production-ready features.

### Components to Build
1. **LiveCommand** - CLI command implementation
2. **EnvironmentDiagnostics** - Setup validation and guidance
3. **BrowserLauncher** - Cross-platform browser opening
4. **ProductionReadiness** - Logging, monitoring, error recovery

### Test Cases

#### LiveCommand Tests
```python
class TestLiveCommand:
    def test_auto_detect_sketch_in_current_directory(self):
        # Test automatic sketch detection

    def test_explicit_sketch_specification(self):
        # Test `sketchbook live sketch_name.py`

    def test_port_specification_option(self):
        # Test --port flag

    def test_no_browser_option(self):
        # Test --no-browser flag

    def test_existing_server_detection_and_options(self):
        # Test connecting to existing vs new server

    def test_command_line_help_and_documentation(self):
        # Test help text and usage examples
```

#### EnvironmentDiagnostics Tests
```python
class TestEnvironmentDiagnostics:
    def test_detect_missing_drawbot_installation(self):
        # Test DrawBot installation validation

    def test_detect_virtual_environment_issues(self):
        # Test venv detection and guidance

    def test_detect_missing_dependencies(self):
        # Test FastAPI/PIL dependency validation

    def test_provide_setup_guidance(self):
        # Test user-friendly setup instructions

    def test_validate_sketch_file_accessibility(self):
        # Test sketch file permissions and syntax
```

#### BrowserLauncher Tests
```python
class TestBrowserLauncher:
    def test_launch_default_browser_cross_platform(self):
        # Test browser opening on Mac/Windows/Linux

    def test_handle_browser_launch_failure(self):
        # Test graceful fallback when browser fails

    def test_custom_browser_specification(self):
        # Test --browser flag for specific browser

    def test_generate_proper_preview_urls(self):
        # Test URL generation with correct ports/paths
```

### Success Criteria
- ✅ `sketchbook live` command works intuitively from sketch directories
- ✅ Environment diagnostics help users resolve setup issues
- ✅ Browser opens automatically to correct preview URL
- ✅ Clear error messages and recovery suggestions for all failure modes
- ✅ Production-ready logging and monitoring
- ✅ Comprehensive documentation and examples

### Integration Target
```python
# End-to-end test for Phase 4
def test_complete_live_preview_workflow():
    # Start from sketch directory
    os.chdir("sketches/test_sketch")

    # Run live command
    result = subprocess.run(["sketchbook", "live"], capture_output=True)
    assert result.returncode == 0
    assert "Preview server: http://localhost" in result.stdout

    # Verify server is running and accessible
    response = requests.get("http://localhost:8080/sketch/test_sketch")
    assert response.status_code == 200
    assert "Live Preview" in response.text
```

---

## 🧪 Cross-Phase Testing Strategy

### Unit Tests
- **Target**: >90% code coverage for all components
- **Focus**: Individual component functionality and error handling
- **Tools**: pytest, pytest-asyncio, pytest-cov

### Integration Tests
- **Target**: End-to-end workflow validation
- **Focus**: Component interaction and data flow
- **Tools**: TestClient for FastAPI, temporary directories, mock sketches

### Performance Tests
- **Target**: <100ms preview update latency, <50MB memory usage
- **Focus**: Resource usage, execution speed, memory leaks
- **Tools**: memory_profiler, pytest-benchmark, continuous monitoring

### Manual Testing Checklist
- [ ] Works across Mac/Windows/Linux
- [ ] Handles network issues gracefully
- [ ] Browser auto-opens to correct URL
- [ ] Multiple sketch preview sessions
- [ ] Error states display clearly
- [ ] Resource cleanup on exit

---

## 📦 Dependencies & Setup

### New Dependencies
```toml
# Add to pyproject.toml
[tool.poetry.dependencies]
fastapi = "^0.104.0"
uvicorn = "^0.24.0"
websockets = "^12.0"
pillow = "^10.0.0"
aiofiles = "^23.0.0"
psutil = "^5.9.0"

[tool.poetry.group.dev.dependencies]
pytest-asyncio = "^0.21.0"
httpx = "^0.25.0"  # for testing FastAPI
pytest-benchmark = "^4.0.0"
memory-profiler = "^0.61.0"
```

### Existing Components to Leverage
- ✅ **FileWatcher**: Already implemented and tested
- ✅ **SketchRunner**: Robust execution engine
- ✅ **DrawBotWrapper**: PDF generation capabilities
- ✅ **Project structure**: Sketch discovery and validation

---

## 🎯 Success Metrics

### Technical Metrics
- **Latency**: File save → preview update <500ms
- **Memory**: Server memory usage <50MB baseline
- **Reliability**: >99% uptime during development sessions
- **Performance**: Support 5+ concurrent sketch previews

### User Experience Metrics
- **Setup Time**: <30 seconds from `sketchbook live` to working preview
- **Error Recovery**: Clear guidance for 100% of common failure modes
- **Cross-platform**: Works identically on Mac/Windows/Linux
- **Integration**: Non-intrusive with existing sketch workflow

---

This TDD implementation plan provides a structured, incremental approach to building the live preview feature. Each phase delivers working functionality while building toward the complete vision. The comprehensive test strategy ensures reliability and maintainability from day one.
