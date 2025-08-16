"""
Tests for DrawBot API wrapper and integration.
"""
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest


class TestDrawBotWrapper:
    """Test suite for DrawBot wrapper operations."""

    def test_initializes_canvas(self):
        """Test canvas initialization with size parameters."""
        with patch("src.core.drawbot_wrapper.drawbot") as mock_drawbot:
            from src.core.drawbot_wrapper import DrawBotWrapper

            wrapper = DrawBotWrapper()
            wrapper.size(800, 600)

            mock_drawbot.size.assert_called_once_with(800, 600)

    def test_draws_basic_shapes(self):
        """Test drawing rectangles, ovals, and polygons."""
        with patch("src.core.drawbot_wrapper.drawbot") as mock_drawbot:
            from src.core.drawbot_wrapper import DrawBotWrapper

            wrapper = DrawBotWrapper()

            # Test rectangle
            wrapper.rect(10, 20, 100, 50)
            mock_drawbot.rect.assert_called_with(10, 20, 100, 50)

            # Test oval
            wrapper.oval(30, 40, 80, 60)
            mock_drawbot.oval.assert_called_with(30, 40, 80, 60)

            # Test polygon
            points = [(0, 0), (100, 0), (50, 100)]
            wrapper.polygon(*points)
            mock_drawbot.polygon.assert_called_with(*points)

    def test_handles_drawbot_errors(self):
        """Test error handling when DrawBot operations fail."""
        from src.core.drawbot_wrapper import DrawBotWrapper

        with patch("src.core.drawbot_wrapper.drawbot") as mock_drawbot:
            # Mock DrawBot to raise an exception
            mock_drawbot.rect.side_effect = Exception("DrawBot error")

            wrapper = DrawBotWrapper()

            # Should handle the error gracefully by switching to mock mode
            wrapper.rect(0, 0, 100, 100)  # Should not raise exception

            # Should have switched to mock mode after error
            assert (
                wrapper.mock_mode == True
            ), "Should switch to mock mode on DrawBot error"

    def test_captures_output(self):
        """Test capturing DrawBot output for preview."""
        from src.core.drawbot_wrapper import DrawBotWrapper

        with patch("src.core.drawbot_wrapper.drawbot") as mock_drawbot:
            # Mock PDF data - needs to be longer than 50 bytes to avoid fallback
            mock_pdf_data = b"%PDF-1.4 fake pdf data with enough content to pass validation checks and not trigger mock mode fallback"
            mock_drawbot.pdfImage.return_value = mock_pdf_data

            wrapper = DrawBotWrapper()
            wrapper.size(400, 400)

            # Capture output
            pdf_data = wrapper.get_pdf_data()

            assert pdf_data == mock_pdf_data
            mock_drawbot.pdfImage.assert_called_once()

    def test_exports_to_formats(self):
        """Test exporting to PNG, PDF, SVG formats."""
        from src.core.drawbot_wrapper import DrawBotWrapper

        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("src.core.drawbot_wrapper.drawbot") as mock_drawbot:
                wrapper = DrawBotWrapper()
                wrapper.size(400, 400)

                # Test PNG export
                png_path = Path(temp_dir) / "output.png"
                wrapper.save_image(str(png_path), format="png")
                mock_drawbot.saveImage.assert_called_with(str(png_path))

                # Test PDF export
                pdf_path = Path(temp_dir) / "output.pdf"
                wrapper.save_image(str(pdf_path), format="pdf")
                mock_drawbot.saveImage.assert_called_with(str(pdf_path))

                # Test SVG export
                svg_path = Path(temp_dir) / "output.svg"
                wrapper.save_image(str(svg_path), format="svg")
                mock_drawbot.saveImage.assert_called_with(str(svg_path))

    def test_manages_drawing_state(self):
        """Test save/restore drawing state functionality."""
        from src.core.drawbot_wrapper import DrawBotWrapper

        with patch("src.core.drawbot_wrapper.drawbot") as mock_drawbot:
            wrapper = DrawBotWrapper()

            wrapper.save()
            mock_drawbot.save.assert_called_once()

            wrapper.restore()
            mock_drawbot.restore.assert_called_once()

    def test_handles_color_operations(self):
        """Test fill and stroke color operations."""
        from src.core.drawbot_wrapper import DrawBotWrapper

        with patch("src.core.drawbot_wrapper.drawbot") as mock_drawbot:
            wrapper = DrawBotWrapper()

            # Test fill color
            wrapper.fill(1, 0, 0, 0.5)  # Semi-transparent red
            mock_drawbot.fill.assert_called_with(1, 0, 0, 0.5)

            # Test stroke color
            wrapper.stroke(0, 1, 0)  # Green stroke
            mock_drawbot.stroke.assert_called_with(0, 1, 0)

            # Test stroke width
            wrapper.stroke_width(2.5)
            mock_drawbot.strokeWidth.assert_called_with(2.5)

    def test_handles_text_operations(self):
        """Test text rendering and font operations."""
        from src.core.drawbot_wrapper import DrawBotWrapper

        with patch("src.core.drawbot_wrapper.drawbot") as mock_drawbot:
            wrapper = DrawBotWrapper()

            # Test font size
            wrapper.font_size(24)
            mock_drawbot.fontSize.assert_called_with(24)

            # Test font selection
            wrapper.font("Helvetica", 18)
            mock_drawbot.font.assert_called_with("Helvetica", 18)

            # Test text drawing
            wrapper.text("Hello World", (100, 200))
            mock_drawbot.text.assert_called_with("Hello World", (100, 200))

    def test_handles_transformations(self):
        """Test geometric transformations."""
        from src.core.drawbot_wrapper import DrawBotWrapper

        with patch("src.core.drawbot_wrapper.drawbot") as mock_drawbot:
            wrapper = DrawBotWrapper()

            # Test scale
            wrapper.scale(1.5, 2.0)
            mock_drawbot.scale.assert_called_with(1.5, 2.0)

            # Test rotation
            wrapper.rotate(45)
            mock_drawbot.rotate.assert_called_with(45)

            # Test translation
            wrapper.translate(100, 50)
            mock_drawbot.translate.assert_called_with(100, 50)

    def test_handles_path_operations(self):
        """Test bezier path creation and drawing."""
        from src.core.drawbot_wrapper import DrawBotWrapper

        with patch("src.core.drawbot_wrapper.drawbot") as mock_drawbot:
            wrapper = DrawBotWrapper()

            # Test path creation
            wrapper.new_path()
            mock_drawbot.newPath.assert_called_once()

            # Test path operations
            wrapper.move_to((50, 50))
            mock_drawbot.moveTo.assert_called_with((50, 50))

            wrapper.line_to((150, 100))
            mock_drawbot.lineTo.assert_called_with((150, 100))

            wrapper.curve_to((200, 150), (250, 200), (300, 150))
            mock_drawbot.curveTo.assert_called_with((200, 150), (250, 200), (300, 150))

            wrapper.close_path()
            mock_drawbot.closePath.assert_called_once()

            wrapper.draw_path()
            mock_drawbot.drawPath.assert_called_once()

    def test_new_page_operations(self):
        """Test multi-page document operations."""
        from src.core.drawbot_wrapper import DrawBotWrapper

        with patch("src.core.drawbot_wrapper.drawbot") as mock_drawbot:
            wrapper = DrawBotWrapper()

            wrapper.new_page()
            mock_drawbot.newPage.assert_called_once()

    def test_canvas_properties(self):
        """Test getting canvas dimensions."""
        from src.core.drawbot_wrapper import DrawBotWrapper

        with patch("src.core.drawbot_wrapper.drawbot") as mock_drawbot:
            mock_drawbot.width.return_value = 800
            mock_drawbot.height.return_value = 600

            wrapper = DrawBotWrapper()

            assert wrapper.width() == 800
            assert wrapper.height() == 600

    def test_mock_mode(self):
        """Test mock mode for testing without DrawBot installed."""
        from src.core.drawbot_wrapper import DrawBotWrapper

        # Test that wrapper can work in mock mode
        wrapper = DrawBotWrapper(mock_mode=True)

        # These should not raise exceptions
        wrapper.size(400, 400)
        wrapper.fill(1, 0, 0)
        wrapper.rect(10, 10, 100, 100)
        wrapper.save_image("test.png")

        # Mock mode should track operations
        assert len(wrapper.operations) > 0
        assert wrapper.operations[0]["method"] == "size"
        assert wrapper.operations[0]["args"] == (400, 400)

    def test_error_recovery(self):
        """Test error recovery and graceful degradation."""
        from src.core.drawbot_wrapper import DrawBotWrapper

        with patch("src.core.drawbot_wrapper.drawbot") as mock_drawbot:
            # Simulate missing DrawBot module
            mock_drawbot.size.side_effect = AttributeError("DrawBot not available")

            wrapper = DrawBotWrapper()

            # Should handle gracefully and switch to mock mode
            wrapper.size(400, 400)

            # Should now be in mock mode
            assert wrapper.mock_mode is True
