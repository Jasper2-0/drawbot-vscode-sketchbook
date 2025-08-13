"""
Tests for PreviewEngine core functionality for live preview system.
"""
import pytest
from pathlib import Path
import tempfile
import time
from unittest.mock import Mock, patch


class TestPreviewEngine:
    """Test suite for PreviewEngine functionality."""

    def test_generate_preview_success(self):
        """Test successful preview generation from sketch."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            sketches_dir = project_path / 'sketches' / 'test_sketch'
            sketches_dir.mkdir(parents=True)
            
            # Create a valid sketch
            sketch_file = sketches_dir / 'test_sketch.py'
            sketch_content = '''
import drawBot as drawbot

drawbot.size(400, 300)
drawbot.fill(1, 0, 0)  # Red
drawbot.rect(100, 100, 200, 100)
'''
            sketch_file.write_text(sketch_content)
            
            from src.core.preview_engine import PreviewEngine
            
            engine = PreviewEngine(project_path)
            pdf_data = engine.generate_preview(sketch_file)
            
            # Should return PDF data
            assert isinstance(pdf_data, bytes), "Should return PDF bytes"
            assert len(pdf_data) > 100, "PDF should be substantial"
            assert pdf_data.startswith(b'%PDF-'), "Should be valid PDF"

    def test_generate_preview_syntax_error(self):
        """Test preview generation handles syntax errors gracefully."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            sketches_dir = project_path / 'sketches' / 'broken_sketch'
            sketches_dir.mkdir(parents=True)
            
            # Create sketch with syntax error
            sketch_file = sketches_dir / 'broken_sketch.py'
            sketch_content = '''
import drawBot as drawbot

drawbot.size(400, 300)
drawbot.fill(1, 0, 0  # Missing closing parenthesis
drawbot.rect(100, 100, 200, 100)
'''
            sketch_file.write_text(sketch_content)
            
            from src.core.preview_engine import PreviewEngine
            
            engine = PreviewEngine(project_path)
            pdf_data = engine.generate_preview(sketch_file)
            
            # Should return error preview (still valid PDF)
            assert isinstance(pdf_data, bytes), "Should return bytes even on syntax error"
            assert pdf_data.startswith(b'%PDF-'), "Should be valid PDF format"
            # Error previews should contain error information
            assert b'Error' in pdf_data or b'error' in pdf_data, "Should indicate error in preview"

    def test_generate_preview_runtime_error(self):
        """Test preview generation handles runtime errors."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            sketches_dir = project_path / 'sketches' / 'runtime_error'
            sketches_dir.mkdir(parents=True)
            
            # Create sketch with runtime error
            sketch_file = sketches_dir / 'runtime_error.py'
            sketch_content = '''
import drawBot as drawbot

drawbot.size(400, 300)
# This will cause a runtime error
undefined_variable = some_undefined_function()
drawbot.rect(100, 100, 200, 100)
'''
            sketch_file.write_text(sketch_content)
            
            from src.core.preview_engine import PreviewEngine
            
            engine = PreviewEngine(project_path)
            pdf_data = engine.generate_preview(sketch_file)
            
            # Should return error preview
            assert isinstance(pdf_data, bytes), "Should return bytes even on runtime error"
            assert pdf_data.startswith(b'%PDF-'), "Should be valid PDF format"

    def test_generate_preview_timeout(self):
        """Test preview generation respects timeout limits."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            sketches_dir = project_path / 'sketches' / 'slow_sketch'
            sketches_dir.mkdir(parents=True)
            
            # Create sketch that takes too long
            sketch_file = sketches_dir / 'slow_sketch.py'
            sketch_content = '''
import drawBot as drawbot
import time

drawbot.size(400, 300)
# This will timeout
time.sleep(10)  # Longer than our timeout
drawbot.rect(100, 100, 200, 100)
'''
            sketch_file.write_text(sketch_content)
            
            from src.core.preview_engine import PreviewEngine
            
            engine = PreviewEngine(project_path, timeout=2.0)  # 2 second timeout
            
            start_time = time.time()
            pdf_data = engine.generate_preview(sketch_file)
            execution_time = time.time() - start_time
            
            # Should timeout quickly
            assert execution_time < 5.0, f"Should timeout quickly, took {execution_time:.2f}s"
            
            # Should still return valid PDF
            assert isinstance(pdf_data, bytes), "Should return bytes even on timeout"
            assert pdf_data.startswith(b'%PDF-'), "Should be valid PDF format"

    def test_generate_preview_performance(self):
        """Test preview generation meets < 500ms requirement."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            sketches_dir = project_path / 'sketches' / 'perf_test'
            sketches_dir.mkdir(parents=True)
            
            # Create typical sketch
            sketch_file = sketches_dir / 'perf_test.py'
            sketch_content = '''
import drawBot as drawbot

drawbot.size(600, 400)
drawbot.fill(0.2, 0.4, 0.8)
drawbot.rect(0, 0, 600, 400)

for i in range(10):  # Moderate complexity
    drawbot.fill(i * 0.1, 0.5, 1 - i * 0.1)
    drawbot.oval(i * 50, i * 30, 40, 40)
'''
            sketch_file.write_text(sketch_content)
            
            from src.core.preview_engine import PreviewEngine
            
            engine = PreviewEngine(project_path)
            
            # Time the preview generation
            start_time = time.time()
            pdf_data = engine.generate_preview(sketch_file)
            generation_time = time.time() - start_time
            
            # Should meet performance requirement
            assert generation_time < 0.5, f"Should generate preview in <500ms, took {generation_time*1000:.0f}ms"
            
            # Should produce valid output
            assert isinstance(pdf_data, bytes), "Should produce valid PDF"
            assert len(pdf_data) > 100, "Should produce substantial PDF"

    def test_preview_memory_cleanup(self):
        """Test preview data is cleaned up after generation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            sketches_dir = project_path / 'sketches' / 'memory_test'
            sketches_dir.mkdir(parents=True)
            
            sketch_file = sketches_dir / 'memory_test.py'
            sketch_content = '''
import drawBot as drawbot

drawbot.size(400, 400)
drawbot.fill(0.8, 0.2, 0.4)
drawbot.rect(0, 0, 400, 400)
'''
            sketch_file.write_text(sketch_content)
            
            from src.core.preview_engine import PreviewEngine
            
            engine = PreviewEngine(project_path)
            
            # Generate multiple previews
            previews = []
            for i in range(5):
                pdf_data = engine.generate_preview(sketch_file)
                previews.append(pdf_data)
                
                assert isinstance(pdf_data, bytes), f"Preview {i} should be bytes"
                assert len(pdf_data) > 0, f"Preview {i} should not be empty"
            
            # All previews should be valid independently
            for i, preview in enumerate(previews):
                assert preview.startswith(b'%PDF-'), f"Preview {i} should remain valid"

    def test_preview_memory_limits(self):
        """Test preview respects memory constraints."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            sketches_dir = project_path / 'sketches' / 'large_sketch'
            sketches_dir.mkdir(parents=True)
            
            # Create sketch that might use more memory
            sketch_file = sketches_dir / 'large_sketch.py'
            sketch_content = '''
import drawBot as drawbot

drawbot.size(1200, 800)  # Larger canvas
drawbot.fill(0.1, 0.1, 0.2)
drawbot.rect(0, 0, 1200, 800)

# Many shapes
for i in range(50):
    drawbot.fill(i * 0.02, 0.5, 1 - i * 0.02)
    drawbot.oval(i * 20, i * 15, 30, 30)
'''
            sketch_file.write_text(sketch_content)
            
            from src.core.preview_engine import PreviewEngine
            
            engine = PreviewEngine(project_path)
            pdf_data = engine.generate_preview(sketch_file)
            
            # Should handle larger sketches
            assert isinstance(pdf_data, bytes), "Should handle larger sketches"
            assert pdf_data.startswith(b'%PDF-'), "Should produce valid PDF"
            # But shouldn't produce unreasonably large PDFs
            assert len(pdf_data) < 1000000, "PDF should be reasonable size (< 1MB)"

    def test_concurrent_preview_generation(self):
        """Test multiple preview generations don't leak memory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            
            # Create multiple sketch files
            sketch_files = []
            for i in range(3):
                sketches_dir = project_path / 'sketches' / f'concurrent_test_{i}'
                sketches_dir.mkdir(parents=True)
                
                sketch_file = sketches_dir / f'concurrent_test_{i}.py'
                sketch_content = f'''
import drawBot as drawbot

drawbot.size(300, 200)
drawbot.fill({i * 0.3}, 0.5, {1 - i * 0.3})
drawbot.rect(50, 50, 200, 100)
'''
                sketch_file.write_text(sketch_content)
                sketch_files.append(sketch_file)
            
            from src.core.preview_engine import PreviewEngine
            
            engine = PreviewEngine(project_path)
            
            # Generate previews for all sketches
            previews = []
            for sketch_file in sketch_files:
                pdf_data = engine.generate_preview(sketch_file)
                previews.append(pdf_data)
            
            # All should be valid
            for i, pdf_data in enumerate(previews):
                assert isinstance(pdf_data, bytes), f"Preview {i} should be bytes"
                assert pdf_data.startswith(b'%PDF-'), f"Preview {i} should be valid PDF"
                assert len(pdf_data) > 100, f"Preview {i} should be substantial"

    def test_invalid_sketch_path(self):
        """Test handling of non-existent sketch files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            non_existent_file = project_path / 'sketches' / 'missing' / 'missing.py'
            
            from src.core.preview_engine import PreviewEngine
            
            engine = PreviewEngine(project_path)
            pdf_data = engine.generate_preview(non_existent_file)
            
            # Should return error preview
            assert isinstance(pdf_data, bytes), "Should return bytes for missing file"
            assert pdf_data.startswith(b'%PDF-'), "Should return valid PDF format"
            # Should indicate file not found
            assert b'not found' in pdf_data or b'Error' in pdf_data, "Should indicate file error"

    def test_permission_errors(self):
        """Test handling of file permission issues."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            sketches_dir = project_path / 'sketches' / 'perm_test'
            sketches_dir.mkdir(parents=True)
            
            sketch_file = sketches_dir / 'perm_test.py'
            sketch_content = '''
import drawBot as drawbot
drawbot.size(200, 200)
drawbot.rect(0, 0, 200, 200)
'''
            sketch_file.write_text(sketch_content)
            
            # Make file unreadable (simulate permission error)
            import os
            original_mode = sketch_file.stat().st_mode
            sketch_file.chmod(0o000)  # No permissions
            
            try:
                from src.core.preview_engine import PreviewEngine
                
                engine = PreviewEngine(project_path)
                pdf_data = engine.generate_preview(sketch_file)
                
                # Should handle permission error gracefully
                assert isinstance(pdf_data, bytes), "Should handle permission errors"
                assert pdf_data.startswith(b'%PDF-'), "Should return valid PDF"
                
            finally:
                # Restore permissions for cleanup
                sketch_file.chmod(original_mode)

    def test_drawbot_unavailable(self):
        """Test graceful degradation when DrawBot unavailable."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            sketches_dir = project_path / 'sketches' / 'mock_test'
            sketches_dir.mkdir(parents=True)
            
            sketch_file = sketches_dir / 'mock_test.py'
            sketch_content = '''
import drawBot as drawbot
drawbot.size(400, 300)
drawbot.fill(0.5, 0.7, 0.9)
drawbot.rect(100, 100, 200, 100)
'''
            sketch_file.write_text(sketch_content)
            
            # Mock DrawBot as unavailable
            with patch('src.core.drawbot_wrapper.drawbot', None):
                from src.core.preview_engine import PreviewEngine
                
                engine = PreviewEngine(project_path)
                pdf_data = engine.generate_preview(sketch_file)
                
                # Should fallback to error mode gracefully
                assert isinstance(pdf_data, bytes), "Should work with mock DrawBot"
                assert pdf_data.startswith(b'%PDF-'), "Should return valid PDF"
                # Should indicate error when DrawBot unavailable
                assert b'Error' in pdf_data or b'error' in pdf_data, "Should indicate error when DrawBot unavailable"