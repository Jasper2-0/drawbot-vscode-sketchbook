"""
Simplified tests for DrawBot API wrapper focusing on core functionality.
"""
import tempfile
from pathlib import Path

import pytest


class TestDrawBotWrapperSimple:
    """Test suite for DrawBot wrapper core functionality."""

    def test_mock_mode_initialization(self):
        """Test wrapper initializes correctly in mock mode."""
        from src.core.drawbot_wrapper import DrawBotWrapper

        wrapper = DrawBotWrapper(mock_mode=True)
        assert wrapper.mock_mode is True
        assert wrapper.operations == []
        assert wrapper.canvas_width == 400
        assert wrapper.canvas_height == 400

    def test_canvas_operations_recorded(self):
        """Test that canvas operations are recorded."""
        from src.core.drawbot_wrapper import DrawBotWrapper

        wrapper = DrawBotWrapper(mock_mode=True)
        wrapper.size(800, 600)

        assert len(wrapper.operations) == 1
        assert wrapper.operations[0]["method"] == "size"
        assert wrapper.operations[0]["args"] == (800, 600)
        assert wrapper.canvas_width == 800
        assert wrapper.canvas_height == 600

    def test_drawing_operations_recorded(self):
        """Test that drawing operations are recorded."""
        from src.core.drawbot_wrapper import DrawBotWrapper

        wrapper = DrawBotWrapper(mock_mode=True)

        # Test various drawing operations
        wrapper.rect(10, 20, 100, 50)
        wrapper.oval(30, 40, 80, 60)
        wrapper.fill(1, 0, 0)
        wrapper.text("Hello", (100, 200))

        assert len(wrapper.operations) == 4

        # Check rect operation
        rect_op = wrapper.operations[0]
        assert rect_op["method"] == "rect"
        assert rect_op["args"] == (10, 20, 100, 50)

        # Check oval operation
        oval_op = wrapper.operations[1]
        assert oval_op["method"] == "oval"
        assert oval_op["args"] == (30, 40, 80, 60)

        # Check fill operation
        fill_op = wrapper.operations[2]
        assert fill_op["method"] == "fill"
        assert fill_op["args"] == (1, 0, 0)

        # Check text operation
        text_op = wrapper.operations[3]
        assert text_op["method"] == "text"
        assert text_op["args"] == ("Hello", (100, 200))

    def test_color_operations_variations(self):
        """Test different color operation signatures."""
        from src.core.drawbot_wrapper import DrawBotWrapper

        wrapper = DrawBotWrapper(mock_mode=True)

        # Grayscale fill
        wrapper.fill(0.5)
        assert wrapper.operations[-1]["args"] == (0.5,)

        # RGB fill
        wrapper.fill(1, 0, 0)
        assert wrapper.operations[-1]["args"] == (1, 0, 0)

        # RGBA fill
        wrapper.fill(0, 1, 0, 0.5)
        assert wrapper.operations[-1]["args"] == (0, 1, 0, 0.5)

    def test_transformation_operations(self):
        """Test transformation operations."""
        from src.core.drawbot_wrapper import DrawBotWrapper

        wrapper = DrawBotWrapper(mock_mode=True)

        wrapper.save()
        wrapper.scale(1.5, 2.0)
        wrapper.rotate(45)
        wrapper.translate(100, 50)
        wrapper.restore()

        operations = wrapper.operations
        assert len(operations) == 5
        assert operations[0]["method"] == "save"
        assert operations[1]["method"] == "scale"
        assert operations[1]["args"] == (1.5, 2.0)
        assert operations[2]["method"] == "rotate"
        assert operations[2]["args"] == (45,)
        assert operations[3]["method"] == "translate"
        assert operations[3]["args"] == (100, 50)
        assert operations[4]["method"] == "restore"

    def test_path_operations_sequence(self):
        """Test path creation and drawing sequence."""
        from src.core.drawbot_wrapper import DrawBotWrapper

        wrapper = DrawBotWrapper(mock_mode=True)

        wrapper.new_path()
        wrapper.move_to((50, 50))
        wrapper.line_to((150, 100))
        wrapper.curve_to((200, 150), (250, 200), (300, 150))
        wrapper.close_path()
        wrapper.draw_path()

        operations = wrapper.operations
        assert len(operations) == 6
        assert operations[0]["method"] == "newPath"
        assert operations[1]["method"] == "moveTo"
        assert operations[1]["args"] == ((50, 50),)
        assert operations[2]["method"] == "lineTo"
        assert operations[2]["args"] == ((150, 100),)
        assert operations[3]["method"] == "curveTo"
        assert operations[3]["args"] == ((200, 150), (250, 200), (300, 150))
        assert operations[4]["method"] == "closePath"
        assert operations[5]["method"] == "drawPath"

    def test_text_operations(self):
        """Test text and font operations."""
        from src.core.drawbot_wrapper import DrawBotWrapper

        wrapper = DrawBotWrapper(mock_mode=True)

        wrapper.font_size(24)
        wrapper.font("Helvetica", 18)
        wrapper.text("Hello World", (100, 200))

        operations = wrapper.operations
        assert len(operations) == 3
        assert operations[0]["method"] == "fontSize"
        assert operations[0]["args"] == (24,)
        assert operations[1]["method"] == "font"
        assert operations[1]["args"] == ("Helvetica", 18)
        assert operations[2]["method"] == "text"
        assert operations[2]["args"] == ("Hello World", (100, 200))

    def test_canvas_properties(self):
        """Test canvas dimension properties."""
        from src.core.drawbot_wrapper import DrawBotWrapper

        wrapper = DrawBotWrapper(mock_mode=True)
        wrapper.size(800, 600)

        assert wrapper.width() == 800
        assert wrapper.height() == 600

    def test_export_operations(self):
        """Test export functionality."""
        from src.core.drawbot_wrapper import DrawBotWrapper

        wrapper = DrawBotWrapper(mock_mode=True)

        # Test image saving
        wrapper.save_image("test.png", format="png")
        assert wrapper.operations[-1]["method"] == "saveImage"
        assert wrapper.operations[-1]["args"] == ("test.png",)

        # Test PDF data retrieval
        pdf_data = wrapper.get_pdf_data()
        assert isinstance(pdf_data, bytes)
        assert pdf_data.startswith(b"%PDF")

    def test_multi_page_operations(self):
        """Test multi-page document functionality."""
        from src.core.drawbot_wrapper import DrawBotWrapper

        wrapper = DrawBotWrapper(mock_mode=True)

        wrapper.size(400, 400)
        wrapper.rect(0, 0, 100, 100)
        wrapper.new_page()
        wrapper.oval(0, 0, 100, 100)

        operations = wrapper.operations
        size_ops = [op for op in operations if op["method"] == "size"]
        shape_ops = [op for op in operations if op["method"] in ["rect", "oval"]]
        page_ops = [op for op in operations if op["method"] == "newPage"]

        assert len(size_ops) == 1
        assert len(shape_ops) == 2
        assert len(page_ops) == 1

    def test_complex_drawing_workflow(self):
        """Test a complete drawing workflow."""
        from src.core.drawbot_wrapper import DrawBotWrapper

        wrapper = DrawBotWrapper(mock_mode=True)

        # Setup canvas
        wrapper.size(600, 400)

        # Draw background
        wrapper.fill(1)
        wrapper.rect(0, 0, wrapper.width(), wrapper.height())

        # Draw shapes with transformations
        wrapper.save()
        wrapper.fill(1, 0, 0)
        wrapper.translate(300, 200)
        wrapper.rotate(45)
        wrapper.rect(-50, -50, 100, 100)
        wrapper.restore()

        # Add text
        wrapper.fill(0)
        wrapper.font_size(24)
        wrapper.text("Test", (50, 50))

        # Verify operations were recorded
        assert len(wrapper.operations) > 8
        assert any(op["method"] == "size" for op in wrapper.operations)
        assert any(op["method"] == "rect" for op in wrapper.operations)
        assert any(op["method"] == "text" for op in wrapper.operations)
        assert any(op["method"] == "save" for op in wrapper.operations)
        assert any(op["method"] == "restore" for op in wrapper.operations)
