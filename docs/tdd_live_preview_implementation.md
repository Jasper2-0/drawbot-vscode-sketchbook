# TDD Implementation Plan: Live Preview System

## Overview

This document outlines the Test-Driven Development approach for implementing the live preview functionality in DrawBot VSCode Sketchbook. The implementation follows the established TDD patterns used in the core system.

**Target Feature**: `sketchbook live <sketch_name>` command that opens VSCode with dual panels - source code and real-time PDF preview.

## 🎯 Implementation Goals

- **Performance**: < 500ms refresh time for typical sketches
- **Architecture**: In-memory PDF generation with WebSocket real-time updates
- **Integration**: Seamless VSCode dual-panel experience
- **Reliability**: Comprehensive error handling and graceful degradation
- **Testability**: 100% test coverage following existing patterns

---

## 📋 Test Implementation Plan

### Phase 1: Enhanced DrawBot PDF Support

#### Test Suite: `test_drawbot_wrapper_pdf.py`

**Test Categories**:

1. **PDF Data Generation Tests**
   ```python
   def test_get_pdf_data_real_mode():
       """Test PDF generation in real DrawBot mode"""
       
   def test_get_pdf_data_mock_mode():
       """Test PDF generation falls back to mock data"""
       
   def test_pdf_data_format_validation():
       """Test PDF data starts with valid PDF header"""
       
   def test_pdf_data_memory_cleanup():
       """Test PDF data is properly cleaned up after use"""
   ```

2. **Enhanced Operation Recording**
   ```python
   def test_operation_recording_with_pdf():
       """Test operations are recorded for PDF generation"""
       
   def test_operation_replay_for_preview():
       """Test recorded operations can generate preview"""
   ```

**Implementation Target**: Enhanced `DrawBotWrapper` with reliable PDF data generation

---

### Phase 2: Preview Engine Core

#### Test Suite: `test_preview_engine.py`

**Test Categories**:

1. **Preview Generation Tests**
   ```python
   def test_generate_preview_success():
       """Test successful preview generation from sketch"""
       
   def test_generate_preview_syntax_error():
       """Test preview generation handles syntax errors gracefully"""
       
   def test_generate_preview_runtime_error():
       """Test preview generation handles runtime errors"""
       
   def test_generate_preview_timeout():
       """Test preview generation respects timeout limits"""
       
   def test_generate_preview_performance():
       """Test preview generation meets < 500ms requirement"""
   ```

2. **Memory Management Tests**
   ```python
   def test_preview_memory_cleanup():
       """Test preview data is cleaned up after generation"""
       
   def test_preview_memory_limits():
       """Test preview respects memory constraints"""
       
   def test_concurrent_preview_generation():
       """Test multiple preview generations don't leak memory"""
   ```

3. **Error Handling Tests**
   ```python
   def test_invalid_sketch_path():
       """Test handling of non-existent sketch files"""
       
   def test_permission_errors():
       """Test handling of file permission issues"""
       
   def test_drawbot_unavailable():
       """Test graceful degradation when DrawBot unavailable"""
   ```

**Implementation Target**: `PreviewEngine` class in `src/core/preview_engine.py`

---

### Phase 3: File Watching System

#### Test Suite: `test_file_watcher.py`

**Test Categories**:

1. **File Change Detection Tests**
   ```python
   def test_detect_sketch_file_change():
       """Test detection of sketch.py modifications"""
       
   def test_ignore_non_sketch_changes():
       """Test ignoring changes to non-sketch files"""
       
   def test_debounce_rapid_changes():
       """Test debouncing prevents excessive updates"""
       
   def test_handle_file_deletion():
       """Test handling when watched file is deleted"""
   ```

2. **Callback System Tests**
   ```python
   def test_change_callback_execution():
       """Test callbacks are executed on file changes"""
       
   def test_callback_error_handling():
       """Test system continues when callbacks fail"""
       
   def test_multiple_callback_registration():
       """Test multiple callbacks can be registered"""
   ```

3. **Lifecycle Management Tests**
   ```python
   def test_watcher_startup():
       """Test file watcher starts successfully"""
       
   def test_watcher_shutdown():
       """Test file watcher shuts down cleanly"""
       
   def test_watcher_restart_after_error():
       """Test watcher recovers from errors"""
   ```

**Implementation Target**: `FileWatcher` class in `src/core/file_watcher.py`

---

### Phase 4: Preview Server & WebSocket Communication

#### Test Suite: `test_preview_server.py`

**Test Categories**:

1. **Server Lifecycle Tests**
   ```python
   def test_server_startup():
       """Test preview server starts on available port"""
       
   def test_server_shutdown():
       """Test preview server shuts down gracefully"""
       
   def test_server_port_collision():
       """Test server finds alternative port when needed"""
   ```

2. **WebSocket Communication Tests**
   ```python
   def test_websocket_connection():
       """Test WebSocket clients can connect"""
       
   def test_websocket_pdf_broadcast():
       """Test PDF data is broadcast to connected clients"""
       
   def test_websocket_error_broadcast():
       """Test error messages are broadcast to clients"""
       
   def test_websocket_client_disconnect():
       """Test server handles client disconnections"""
   ```

3. **Integration Tests**
   ```python
   def test_file_change_to_websocket():
       """Test file changes trigger WebSocket updates"""
       
   def test_preview_generation_to_broadcast():
       """Test preview generation results in WebSocket broadcast"""
       
   def test_concurrent_client_handling():
       """Test server handles multiple connected clients"""
   ```

**Implementation Target**: `PreviewServer` class in `src/core/preview_server.py`

---

### Phase 5: CLI Integration

#### Test Suite: `test_cli_live_command.py`

**Test Categories**:

1. **Command Validation Tests**
   ```python
   def test_live_command_valid_sketch():
       """Test live command with valid sketch name"""
       
   def test_live_command_invalid_sketch():
       """Test live command with non-existent sketch"""
       
   def test_live_command_help():
       """Test live command help output"""
   ```

2. **Session Management Tests**
   ```python
   def test_live_session_startup():
       """Test live session starts all required components"""
       
   def test_live_session_shutdown():
       """Test live session shuts down cleanly on interrupt"""
       
   def test_live_session_error_recovery():
       """Test live session handles component failures"""
   ```

3. **VSCode Integration Tests**
   ```python
   def test_vscode_launch():
       """Test VSCode is launched with correct parameters"""
       
   def test_vscode_not_available():
       """Test graceful handling when VSCode unavailable"""
       
   def test_workspace_setup():
       """Test VSCode workspace is configured correctly"""
   ```

**Implementation Target**: Enhanced `src/cli/main.py` with `live` command

---

### Phase 6: Integration & Error Handling

#### Test Suite: `test_live_preview_integration.py`

**Test Categories**:

1. **End-to-End Workflow Tests**
   ```python
   def test_complete_live_preview_workflow():
       """Test complete workflow from command to preview update"""
       
   def test_sketch_edit_to_preview_update():
       """Test editing sketch triggers preview refresh"""
       
   def test_error_sketch_to_error_display():
       """Test syntax errors are displayed in preview"""
   ```

2. **Performance Integration Tests**
   ```python
   def test_preview_refresh_performance():
       """Test end-to-end refresh meets < 500ms target"""
       
   def test_memory_usage_over_time():
       """Test memory usage remains stable over extended sessions"""
       
   def test_large_sketch_handling():
       """Test system handles complex sketches appropriately"""
   ```

3. **Robustness Tests**
   ```python
   def test_network_interruption():
       """Test system handles WebSocket connection issues"""
       
   def test_file_system_errors():
       """Test system handles file permission/disk space issues"""
       
   def test_drawbot_crash_recovery():
       """Test system recovers from DrawBot crashes"""
   ```

---

## 🏗️ Implementation Sequence

### Step 1: Foundation Enhancement
1. **Write tests** for enhanced DrawBot PDF support
2. **Implement** enhanced `DrawBotWrapper.get_pdf_data()` 
3. **Run tests** until all pass
4. **Refactor** for performance and clarity

### Step 2: Core Preview Engine
1. **Write tests** for `PreviewEngine` functionality
2. **Implement** `PreviewEngine` class with in-memory execution
3. **Integration** with existing `SketchRunner` 
4. **Run tests** and iterate until stable

### Step 3: File Monitoring
1. **Write tests** for file watching functionality
2. **Implement** `FileWatcher` with debouncing
3. **Integration** with `PreviewEngine`
4. **Test performance** and memory usage

### Step 4: Communication Layer
1. **Write tests** for WebSocket server
2. **Implement** `PreviewServer` with broadcast capability
3. **Integration** with file watcher and preview engine
4. **Test concurrent connections** and error handling

### Step 5: CLI Integration
1. **Write tests** for live command
2. **Implement** `sketchbook live` command
3. **Integration** with preview server and VSCode
4. **Test session management** and cleanup

### Step 6: System Integration
1. **Write integration tests** for complete workflow
2. **Performance testing** against < 500ms target
3. **Error scenario testing** for robustness
4. **Documentation** and examples

---

## 🧪 Testing Strategy

### Mock Strategy
- **DrawBot**: Use existing mock mode for headless testing
- **VSCode**: Mock VSCode launch and webview communication
- **WebSocket**: Mock WebSocket clients for server testing
- **File System**: Mock file operations for error scenario testing

### Performance Testing
- **Benchmark suite** for preview generation timing
- **Memory profiling** for leak detection
- **Concurrent load testing** for server stability
- **Real-world sketch testing** with complex examples

### Integration Testing
- **Docker environment** for consistent testing
- **Continuous integration** with existing test suite
- **Cross-platform testing** (where applicable)
- **User acceptance testing** with real sketches

---

## 📊 Success Criteria

### Functional Requirements
- ✅ All tests pass with 100% coverage
- ✅ `sketchbook live <sketch>` launches dual-panel VSCode
- ✅ File changes trigger real-time preview updates
- ✅ PDF preview maintains vector accuracy
- ✅ Error scenarios handled gracefully

### Performance Requirements
- ✅ Preview refresh < 500ms for typical sketches
- ✅ Memory usage remains stable during extended sessions
- ✅ System handles multiple concurrent preview sessions

### Quality Requirements
- ✅ No regressions in existing functionality
- ✅ Code follows existing project patterns and style
- ✅ Comprehensive error handling and logging
- ✅ Documentation covers usage and troubleshooting

---

## 🔄 Continuous Integration

### Test Automation
```bash
# Run preview-specific tests
pytest tests/test_*preview* -v

# Run performance benchmarks  
pytest tests/test_preview_performance.py --benchmark

# Run integration tests
pytest tests/test_live_preview_integration.py -v
```

### Quality Gates
- **All tests pass** before code merge
- **Performance benchmarks** meet targets
- **Memory usage** within acceptable limits
- **Code coverage** maintains 100% for new components

This TDD implementation plan ensures the live preview system is built with the same rigor and reliability as the existing codebase, following established patterns while introducing innovative real-time capabilities.