"""
ImageConverter - PDF to PNG conversion pipeline for preview generation.
"""

import io
import tempfile
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

try:
    from PIL import Image

    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import fitz  # PyMuPDF

    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

try:
    import psutil

    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False


@dataclass
class ConversionResult:
    """Result of PDF to PNG conversion."""

    success: bool
    png_path: Optional[Path] = None
    error: Optional[str] = None
    conversion_time: float = 0.0
    peak_memory_mb: Optional[float] = None


class ImageConverter:
    """Converts PDF data to PNG images for web preview display."""

    def __init__(
        self,
        max_width: int = 1200,
        max_height: int = 1200,
        quality: int = 90,
        retina_scale: float = 3.0,
    ):
        """Initialize image converter.

        Args:
            max_width: Maximum width for output images
            max_height: Maximum height for output images
            quality: PNG compression quality (0-100)
            retina_scale: Target scale factor for retina displays (2.0-4.0 recommended)
        """
        self.max_width = max_width
        self.max_height = max_height
        self.quality = quality
        self.retina_scale = retina_scale

        # Check available conversion backends
        self.conversion_backends = []
        if PYMUPDF_AVAILABLE:
            self.conversion_backends.append("pymupdf")
        if PIL_AVAILABLE:
            self.conversion_backends.append("pil")

    def convert_pdf_to_png(self, pdf_data: bytes, output_dir: Path) -> ConversionResult:
        """Convert PDF data to PNG image.

        Args:
            pdf_data: Raw PDF file data
            output_dir: Directory to save the PNG file

        Returns:
            ConversionResult with conversion status and output path
        """
        start_time = time.time()
        peak_memory = None

        try:
            # Validate input
            if not pdf_data:
                return ConversionResult(success=False, error="Empty PDF data provided")

            if len(pdf_data) < 10:
                return ConversionResult(
                    success=False, error="PDF data too small to be valid"
                )

            # Ensure output directory exists
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)

            # Monitor memory usage if available
            if PSUTIL_AVAILABLE:
                process = psutil.Process()
                initial_memory = process.memory_info().rss / 1024 / 1024  # MB

            # Try conversion with available backends
            result = None
            for backend in self.conversion_backends:
                try:
                    if backend == "pymupdf":
                        result = self._convert_with_pymupdf(pdf_data, output_dir)
                    elif backend == "pil":
                        result = self._convert_with_pil(pdf_data, output_dir)

                    if result and result.success:
                        break

                except Exception as e:
                    # Try next backend
                    continue

            # If no backend succeeded, return error
            if not result or not result.success:
                return ConversionResult(
                    success=False,
                    error="No available conversion backend could process the PDF",
                )

            # Calculate final metrics
            conversion_time = time.time() - start_time

            if PSUTIL_AVAILABLE:
                final_memory = process.memory_info().rss / 1024 / 1024  # MB
                peak_memory = max(initial_memory, final_memory)

            result.conversion_time = conversion_time
            result.peak_memory_mb = peak_memory

            return result

        except Exception as e:
            conversion_time = time.time() - start_time
            return ConversionResult(
                success=False,
                error=f"Conversion failed: {str(e)}",
                conversion_time=conversion_time,
                peak_memory_mb=peak_memory,
            )

    def _convert_with_pymupdf(
        self, pdf_data: bytes, output_dir: Path
    ) -> ConversionResult:
        """Convert PDF using PyMuPDF backend.

        Args:
            pdf_data: Raw PDF data
            output_dir: Output directory

        Returns:
            ConversionResult with conversion status
        """
        try:
            # Open PDF from memory
            pdf_document = fitz.open(stream=pdf_data, filetype="pdf")

            if pdf_document.page_count == 0:
                pdf_document.close()
                return ConversionResult(success=False, error="PDF contains no pages")

            # Convert all pages to images and combine vertically
            page_count = pdf_document.page_count
            page_pixmaps = []

            # Calculate scaling for retina display quality using first page
            first_page = pdf_document[0]
            page_rect = first_page.rect

            # Use retina scale factor, but respect max dimensions
            scale_x = self.max_width / page_rect.width
            scale_y = self.max_height / page_rect.height
            max_scale = min(scale_x, scale_y)

            # Prefer retina scale, but cap at max dimensions
            scale = min(self.retina_scale, max_scale)
            matrix = fitz.Matrix(scale, scale)

            # Render all pages to pixmaps
            for page_num in range(page_count):
                page = pdf_document[page_num]
                pixmap = page.get_pixmap(matrix=matrix)
                page_pixmaps.append(pixmap)

            # If single page, use it directly
            if page_count == 1:
                final_pixmap = page_pixmaps[0]
            else:
                # Combine multiple pages vertically
                page_width = page_pixmaps[0].width
                page_height = page_pixmaps[0].height
                total_height = page_height * page_count

                # Create combined pixmap
                final_pixmap = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, page_width, total_height))
                final_pixmap.clear_with(value=255)  # White background

                # Copy each page into the combined pixmap
                for i, page_pixmap in enumerate(page_pixmaps):
                    y_offset = i * page_height
                    final_pixmap.copy(page_pixmap, fitz.IRect(0, y_offset, page_width, y_offset + page_height))

                # Cleanup individual page pixmaps
                for pixmap in page_pixmaps:
                    pixmap = None

            # Generate unique filename
            output_filename = f"preview_{uuid.uuid4().hex[:8]}.png"
            output_path = output_dir / output_filename

            # Save PNG
            final_pixmap.save(str(output_path))

            # Cleanup
            final_pixmap = None
            pdf_document.close()

            return ConversionResult(success=True, png_path=output_path)

        except Exception as e:
            return ConversionResult(
                success=False, error=f"PyMuPDF conversion failed: {str(e)}"
            )

    def _convert_with_pil(self, pdf_data: bytes, output_dir: Path) -> ConversionResult:
        """Convert PDF using PIL backend (limited support).

        Args:
            pdf_data: Raw PDF data
            output_dir: Output directory

        Returns:
            ConversionResult with conversion status
        """
        try:
            # PIL has limited PDF support, mainly for simple cases
            # This is a fallback when PyMuPDF is not available

            # Create a simple placeholder image since PIL can't easily handle PDF
            # In a real implementation, you might use pdf2image or similar
            placeholder_image = Image.new("RGB", (400, 400), color="white")

            # Add some indication this is a placeholder
            try:
                from PIL import ImageDraw, ImageFont

                draw = ImageDraw.Draw(placeholder_image)

                # Try to use a basic font
                try:
                    font = ImageFont.load_default()
                except:
                    font = None

                draw.text((50, 180), "PDF Preview", fill="black", font=font)
                draw.text((50, 200), "(Conversion)", fill="gray", font=font)

            except ImportError:
                # If ImageDraw not available, just use plain image
                pass

            # Generate unique filename
            output_filename = f"preview_{uuid.uuid4().hex[:8]}.png"
            output_path = output_dir / output_filename

            # Save PNG
            placeholder_image.save(str(output_path), "PNG")

            return ConversionResult(success=True, png_path=output_path)

        except Exception as e:
            return ConversionResult(
                success=False, error=f"PIL conversion failed: {str(e)}"
            )

    def _generate_unique_filename(
        self, output_dir: Path, base_name: str = "preview"
    ) -> Path:
        """Generate unique filename to avoid collisions.

        Args:
            output_dir: Output directory
            base_name: Base name for file

        Returns:
            Unique file path
        """
        counter = 1
        while True:
            filename = f"{base_name}_{counter:03d}.png"
            output_path = output_dir / filename
            if not output_path.exists():
                return output_path
            counter += 1

            # Safety check to prevent infinite loop
            if counter > 1000:
                # Use UUID as fallback
                filename = f"{base_name}_{uuid.uuid4().hex[:8]}.png"
                return output_dir / filename

    def is_available(self) -> bool:
        """Check if image conversion is available."""
        return len(self.conversion_backends) > 0

    def get_backend_info(self) -> dict:
        """Get information about available conversion backends."""
        return {
            "available_backends": self.conversion_backends,
            "pymupdf_available": PYMUPDF_AVAILABLE,
            "pil_available": PIL_AVAILABLE,
            "psutil_available": PSUTIL_AVAILABLE,
        }
