"""
DrawBot API wrapper for consistent interface and testing support.
"""
from typing import List, Dict, Any, Tuple, Optional, Union
import sys

# Global drawbot import
try:
    import drawbot
except ImportError:
    drawbot = None


class DrawBotWrapper:
    """Wrapper around DrawBot API with mock support for testing."""
    
    def __init__(self, mock_mode: bool = False):
        """Initialize wrapper.
        
        Args:
            mock_mode: If True, use mock implementation instead of real DrawBot
        """
        self.mock_mode = mock_mode or drawbot is None
        self.operations: List[Dict[str, Any]] = []
        self.canvas_width = 400
        self.canvas_height = 400
    
    def _record_operation(self, method: str, *args, **kwargs):
        """Record operation for mock mode and debugging."""
        operation = {
            'method': method,
            'args': args,
            'kwargs': kwargs
        }
        self.operations.append(operation)
    
    def _execute_or_mock(self, method: str, *args, **kwargs):
        """Execute DrawBot method or record in mock mode."""
        self._record_operation(method, *args, **kwargs)
        
        if self.mock_mode:
            return None
        
        try:
            func = getattr(drawbot, method)
            return func(*args, **kwargs)
        except (AttributeError, Exception) as e:
            # Switch to mock mode on any error
            self.mock_mode = True
            return None
    
    # Canvas operations
    def size(self, width: float, height: float):
        """Set canvas size."""
        self.canvas_width = width
        self.canvas_height = height
        self._execute_or_mock('size', width, height)
    
    def new_page(self):
        """Create a new page."""
        self._execute_or_mock('newPage')
    
    def width(self) -> float:
        """Get canvas width."""
        if self.mock_mode:
            return self.canvas_width
        try:
            return drawbot.width()
        except:
            return self.canvas_width
    
    def height(self) -> float:
        """Get canvas height."""
        if self.mock_mode:
            return self.canvas_height
        try:
            return drawbot.height()
        except:
            return self.canvas_height
    
    # Shape drawing operations
    def rect(self, x: float, y: float, w: float, h: float):
        """Draw a rectangle."""
        self._execute_or_mock('rect', x, y, w, h)
    
    def oval(self, x: float, y: float, w: float, h: float):
        """Draw an oval."""
        self._execute_or_mock('oval', x, y, w, h)
    
    def polygon(self, *points):
        """Draw a polygon."""
        self._execute_or_mock('polygon', *points)
    
    # Color operations
    def fill(self, r: float, g: float = None, b: float = None, a: float = None):
        """Set fill color."""
        if g is None:
            # Grayscale
            self._execute_or_mock('fill', r)
        elif a is None:
            # RGB
            self._execute_or_mock('fill', r, g, b)
        else:
            # RGBA
            self._execute_or_mock('fill', r, g, b, a)
    
    def stroke(self, r: float, g: float = None, b: float = None, a: float = None):
        """Set stroke color."""
        if g is None:
            # Grayscale
            self._execute_or_mock('stroke', r)
        elif a is None:
            # RGB
            self._execute_or_mock('stroke', r, g, b)
        else:
            # RGBA
            self._execute_or_mock('stroke', r, g, b, a)
    
    def stroke_width(self, width: float):
        """Set stroke width."""
        self._execute_or_mock('strokeWidth', width)
    
    # Text operations
    def font(self, font_name: str, size: float = None):
        """Set font."""
        if size is None:
            self._execute_or_mock('font', font_name)
        else:
            self._execute_or_mock('font', font_name, size)
    
    def font_size(self, size: float):
        """Set font size."""
        self._execute_or_mock('fontSize', size)
    
    def text(self, txt: str, position: Tuple[float, float]):
        """Draw text."""
        self._execute_or_mock('text', txt, position)
    
    # Transformation operations
    def save(self):
        """Save drawing state."""
        self._execute_or_mock('save')
    
    def restore(self):
        """Restore drawing state."""
        self._execute_or_mock('restore')
    
    def scale(self, x: float, y: float = None):
        """Scale transformation."""
        if y is None:
            self._execute_or_mock('scale', x)
        else:
            self._execute_or_mock('scale', x, y)
    
    def rotate(self, angle: float):
        """Rotate transformation."""
        self._execute_or_mock('rotate', angle)
    
    def translate(self, x: float, y: float):
        """Translate transformation."""
        self._execute_or_mock('translate', x, y)
    
    # Path operations
    def new_path(self):
        """Start a new path."""
        self._execute_or_mock('newPath')
    
    def move_to(self, point: Tuple[float, float]):
        """Move to point."""
        self._execute_or_mock('moveTo', point)
    
    def line_to(self, point: Tuple[float, float]):
        """Draw line to point."""
        self._execute_or_mock('lineTo', point)
    
    def curve_to(self, cp1: Tuple[float, float], cp2: Tuple[float, float], 
                 end: Tuple[float, float]):
        """Draw curve with control points."""
        self._execute_or_mock('curveTo', cp1, cp2, end)
    
    def close_path(self):
        """Close current path."""
        self._execute_or_mock('closePath')
    
    def draw_path(self):
        """Draw current path."""
        self._execute_or_mock('drawPath')
    
    # Export operations
    def save_image(self, path: str, format: str = None):
        """Save image to file."""
        self._execute_or_mock('saveImage', path)
    
    def get_pdf_data(self) -> bytes:
        """Get PDF data for preview."""
        if self.mock_mode:
            return b'%PDF-1.4 mock pdf data'
        
        try:
            return drawbot.pdfImage()
        except:
            return b'%PDF-1.4 mock pdf data'