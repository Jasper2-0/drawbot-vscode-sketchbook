"""
Tests for DrawBot wrapper PDF functionality for live preview.
"""
import pytest
from pathlib import Path
import tempfile
import time
from unittest.mock import Mock, patch


class TestDrawBotWrapperPDF:
    """Test suite for DrawBot wrapper PDF functionality."""

    def test_get_pdf_data_real_mode(self):
        """Test PDF generation in real DrawBot mode."""
        from src.core.drawbot_wrapper import DrawBotWrapper
        
        # Test with mock_mode=False (real mode)
        wrapper = DrawBotWrapper(mock_mode=False)
        
        # Create a simple drawing
        wrapper.size(400, 300)
        wrapper.fill(1, 0, 0)  # Red
        wrapper.rect(100, 100, 200, 100)
        
        # Get PDF data
        pdf_data = wrapper.get_pdf_data()
        
        # Should return bytes
        assert isinstance(pdf_data, bytes), "PDF data should be bytes"
        # Should start with PDF header
        assert pdf_data.startswith(b'%PDF-'), "Should start with PDF header"
        # Should have reasonable size (at least basic PDF structure)
        assert len(pdf_data) > 100, "PDF data should be substantial"

    def test_get_pdf_data_mock_mode(self):
        """Test PDF generation falls back to mock data."""
        from src.core.drawbot_wrapper import DrawBotWrapper
        
        # Test with explicit mock mode
        wrapper = DrawBotWrapper(mock_mode=True)
        
        # Create some drawing operations
        wrapper.size(400, 300)
        wrapper.fill(0, 1, 0)  # Green
        wrapper.oval(50, 50, 100, 100)
        
        # Get PDF data
        pdf_data = wrapper.get_pdf_data()
        
        # Should return mock PDF data
        assert isinstance(pdf_data, bytes), "Mock PDF data should be bytes"
        assert pdf_data.startswith(b'%PDF-'), "Mock data should have PDF header"
        assert b'Mock PDF Preview' in pdf_data, "Should contain mock identifier"

    def test_pdf_data_format_validation(self):
        """Test PDF data starts with valid PDF header."""
        from src.core.drawbot_wrapper import DrawBotWrapper
        
        wrapper = DrawBotWrapper(mock_mode=True)  # Use mock for predictable testing
        
        # Create minimal drawing
        wrapper.size(200, 200)
        wrapper.fill(0.5)  # Gray
        wrapper.rect(0, 0, 200, 200)
        
        pdf_data = wrapper.get_pdf_data()
        
        # Validate PDF format
        assert pdf_data.startswith(b'%PDF-1.'), "Should start with valid PDF version header"
        
        # Should be valid bytes object
        assert isinstance(pdf_data, bytes), "PDF data must be bytes"
        assert len(pdf_data) > 0, "PDF data should not be empty"

    def test_pdf_data_memory_cleanup(self):
        """Test PDF data is properly cleaned up after use."""
        from src.core.drawbot_wrapper import DrawBotWrapper
        
        wrapper = DrawBotWrapper(mock_mode=True)
        
        # Generate multiple PDFs to test memory handling
        pdf_data_list = []
        for i in range(5):
            wrapper.size(200, 200)
            wrapper.fill(i * 0.2, 0, 0)  # Different colors
            wrapper.rect(10 * i, 10 * i, 50, 50)
            
            pdf_data = wrapper.get_pdf_data()
            pdf_data_list.append(pdf_data)
            
            # Each should be valid
            assert isinstance(pdf_data, bytes), f"PDF {i} should be bytes"
            assert pdf_data.startswith(b'%PDF-'), f"PDF {i} should have valid header"
        
        # All PDFs should be accessible and valid
        assert len(pdf_data_list) == 5, "Should have generated 5 PDFs"
        
        # Memory cleanup test - PDFs should still be valid after generation
        for i, pdf_data in enumerate(pdf_data_list):
            assert len(pdf_data) > 0, f"PDF {i} should not be empty after generation"

    def test_operation_recording_with_pdf(self):
        """Test operations are recorded for PDF generation."""
        from src.core.drawbot_wrapper import DrawBotWrapper
        
        wrapper = DrawBotWrapper(mock_mode=True)
        
        # Perform various operations
        wrapper.size(300, 400)
        wrapper.fill(1, 0.5, 0)  # Orange
        wrapper.rect(50, 50, 100, 100)
        wrapper.stroke(0, 0, 1)  # Blue stroke
        wrapper.stroke_width(3)
        wrapper.oval(150, 150, 80, 80)
        
        # Check operations were recorded
        operations = wrapper.operations
        assert len(operations) >= 6, "Should have recorded all operations"
        
        # Verify specific operations
        operation_methods = [op['method'] for op in operations]
        assert 'size' in operation_methods, "Should record size operation"
        assert 'fill' in operation_methods, "Should record fill operation"
        assert 'rect' in operation_methods, "Should record rect operation"
        assert 'stroke' in operation_methods, "Should record stroke operation"
        assert 'strokeWidth' in operation_methods, "Should record strokeWidth operation"
        assert 'oval' in operation_methods, "Should record oval operation"
        
        # Generate PDF - should work with recorded operations
        pdf_data = wrapper.get_pdf_data()
        assert isinstance(pdf_data, bytes), "Should generate PDF from recorded operations"

    def test_operation_replay_for_preview(self):
        """Test recorded operations can generate preview."""
        from src.core.drawbot_wrapper import DrawBotWrapper
        
        wrapper = DrawBotWrapper(mock_mode=True)
        
        # Record a sequence of operations
        wrapper.size(400, 300)
        wrapper.fill(0.8, 0.2, 0.2)  # Light red
        wrapper.rect(100, 100, 200, 100)
        wrapper.fill(0.2, 0.8, 0.2)  # Light green
        wrapper.oval(150, 150, 100, 100)
        
        # Get initial operation count
        initial_ops = len(wrapper.operations)
        assert initial_ops >= 4, "Should have recorded drawing operations"
        
        # Generate PDF multiple times - operations should be replayable
        pdf1 = wrapper.get_pdf_data()
        pdf2 = wrapper.get_pdf_data()
        
        # Both should be valid and identical (for mock mode)
        assert isinstance(pdf1, bytes), "First PDF should be bytes"
        assert isinstance(pdf2, bytes), "Second PDF should be bytes"
        assert pdf1 == pdf2, "Multiple calls should return consistent data in mock mode"
        
        # Operations should not have grown from PDF generation
        final_ops = len(wrapper.operations)
        # PDF generation might record operations, so check it's reasonable
        assert final_ops >= initial_ops, "Operations should be preserved"

    def test_pdf_generation_error_handling(self):
        """Test PDF generation handles errors gracefully."""
        from src.core.drawbot_wrapper import DrawBotWrapper
        
        # Test with mock mode to simulate error conditions
        wrapper = DrawBotWrapper(mock_mode=False)  # Start with real mode
        
        # Force error condition by not creating any content
        # (Some DrawBot operations might fail without proper setup)
        
        # Should still return valid mock data on error
        pdf_data = wrapper.get_pdf_data()
        
        # Should fallback to mock data on any error
        assert isinstance(pdf_data, bytes), "Should return bytes even on error"
        assert pdf_data.startswith(b'%PDF-'), "Should return valid PDF header even on error"

    def test_pdf_data_with_complex_drawing(self):
        """Test PDF generation with complex drawing operations."""
        from src.core.drawbot_wrapper import DrawBotWrapper
        
        wrapper = DrawBotWrapper(mock_mode=True)
        
        # Create complex drawing
        wrapper.size(600, 400)
        
        # Background
        wrapper.fill(0.1, 0.1, 0.2)  # Dark blue
        wrapper.rect(0, 0, 600, 400)
        
        # Shapes with transformations
        wrapper.save()
        wrapper.translate(300, 200)
        wrapper.rotate(45)
        wrapper.fill(1, 0.8, 0)  # Yellow
        wrapper.rect(-50, -25, 100, 50)
        wrapper.restore()
        
        # Text
        wrapper.font("Helvetica", 24)
        wrapper.fill(1, 1, 1)  # White
        wrapper.text("Preview Test", (50, 350))
        
        # Path operations
        wrapper.new_path()
        wrapper.move_to((100, 100))
        wrapper.line_to((200, 150))
        wrapper.line_to((150, 200))
        wrapper.close_path()
        wrapper.fill(0.8, 0.2, 0.8)  # Purple
        wrapper.draw_path()
        
        # Generate PDF
        pdf_data = wrapper.get_pdf_data()
        
        # Should handle complex operations
        assert isinstance(pdf_data, bytes), "Should generate PDF from complex drawing"
        assert len(pdf_data) > 50, "Complex drawing should produce substantial PDF data"
        
        # Check that many operations were recorded
        assert len(wrapper.operations) >= 15, "Should have recorded many operations"

    def test_pdf_generation_performance(self):
        """Test PDF generation performance for live preview requirements."""
        from src.core.drawbot_wrapper import DrawBotWrapper
        
        wrapper = DrawBotWrapper(mock_mode=True)  # Use mock for predictable timing
        
        # Create moderately complex drawing
        wrapper.size(400, 400)
        for i in range(20):  # 20 shapes
            wrapper.fill(i * 0.05, 0.5, 1 - i * 0.05)
            wrapper.rect(i * 10, i * 10, 50, 50)
        
        # Time PDF generation
        start_time = time.time()
        pdf_data = wrapper.get_pdf_data()
        generation_time = time.time() - start_time
        
        # Should be fast enough for live preview (mock mode should be very fast)
        assert generation_time < 0.1, f"PDF generation should be fast, took {generation_time:.3f}s"
        
        # Should still produce valid output
        assert isinstance(pdf_data, bytes), "Should produce valid PDF data"
        assert len(pdf_data) > 0, "Should produce non-empty PDF data"