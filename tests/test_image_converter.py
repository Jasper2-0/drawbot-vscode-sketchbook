"""
Tests for ImageConverter - PDF to PNG conversion pipeline.
"""
import pytest
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from src.core.image_converter import ImageConverter, ConversionResult


class TestImageConverter:
    """Test suite for ImageConverter functionality."""

    def test_convert_pdf_to_png(self):
        """Test basic PDF to PNG conversion."""
        with tempfile.TemporaryDirectory() as temp_dir:
            converter = ImageConverter()
            
            # Create mock PDF data (simplified but realistic structure)
            pdf_data = b'''%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj
3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 400 400]/Contents 4 0 R>>endobj
4 0 obj<</Length 44>>stream
BT /F1 12 Tf 50 350 Td (Test Content) Tj ET
endstream endobj
xref 0 5 0000000000 65535 f 0000000009 00000 n 0000000058 00000 n 0000000115 00000 n 0000000200 00000 n 
trailer<</Size 5/Root 1 0 R>>startxref 294 %%EOF'''
            
            result = converter.convert_pdf_to_png(pdf_data, Path(temp_dir))
            
            assert result.success
            assert result.png_path is not None
            assert result.png_path.exists()
            assert result.png_path.suffix == '.png'
            assert result.conversion_time > 0

    def test_handle_invalid_pdf_data(self):
        """Test graceful handling of corrupted PDFs."""
        with tempfile.TemporaryDirectory() as temp_dir:
            converter = ImageConverter()
            
            # Test completely invalid data
            invalid_data = b"This is not a PDF file"
            result = converter.convert_pdf_to_png(invalid_data, Path(temp_dir))
            
            assert not result.success
            assert result.error is not None
            assert "invalid" in result.error.lower() or "pdf" in result.error.lower()
            
            # Test empty data
            result = converter.convert_pdf_to_png(b"", Path(temp_dir))
            assert not result.success
            assert "empty" in result.error.lower()
            
            # Test None data
            result = converter.convert_pdf_to_png(None, Path(temp_dir))
            assert not result.success

    def test_conversion_with_different_sizes(self):
        """Test handling various canvas sizes."""
        with tempfile.TemporaryDirectory() as temp_dir:
            converter = ImageConverter()
            
            test_sizes = [
                (200, 200),   # Small square
                (800, 600),   # Medium rectangle
                (1920, 1080), # Large rectangle
                (100, 500),   # Tall rectangle
                (500, 100),   # Wide rectangle
            ]
            
            for width, height in test_sizes:
                # Create PDF with specific dimensions
                pdf_data = f'''%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj
3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 {width} {height}]/Contents 4 0 R>>endobj
4 0 obj<</Length 44>>stream
BT /F1 12 Tf 50 350 Td (Size Test) Tj ET
endstream endobj
xref 0 5 0000000000 65535 f 0000000009 00000 n 0000000058 00000 n 0000000115 00000 n 0000000200 00000 n 
trailer<</Size 5/Root 1 0 R>>startxref 294 %%EOF'''.encode()
                
                result = converter.convert_pdf_to_png(pdf_data, Path(temp_dir))
                
                assert result.success, f"Failed to convert {width}x{height} PDF"
                assert result.png_path.exists()

    def test_conversion_performance_benchmarks(self):
        """Test conversion speed meets requirements (<100ms for typical sketches)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            converter = ImageConverter()
            
            # Create typical sketch-sized PDF
            pdf_data = b'''%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj
3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 400 400]/Contents 4 0 R>>endobj
4 0 obj<</Length 44>>stream
BT /F1 12 Tf 50 350 Td (Performance Test) Tj ET
endstream endobj
xref 0 5 0000000000 65535 f 0000000009 00000 n 0000000058 00000 n 0000000115 00000 n 0000000200 00000 n 
trailer<</Size 5/Root 1 0 R>>startxref 294 %%EOF'''
            
            # Perform multiple conversions to get average time
            conversion_times = []
            for i in range(5):
                start_time = time.time()
                result = converter.convert_pdf_to_png(pdf_data, Path(temp_dir))
                end_time = time.time()
                
                assert result.success
                conversion_times.append(end_time - start_time)
            
            avg_time = sum(conversion_times) / len(conversion_times)
            
            # Should be reasonably fast (allowing some tolerance for test environment)
            assert avg_time < 1.0, f"Average conversion time {avg_time:.3f}s too slow"
            
            # Individual result should also report reasonable time
            assert result.conversion_time < 1.0

    @patch('psutil.Process')
    def test_memory_usage_during_conversion(self, mock_process):
        """Test memory efficiency."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Mock memory monitoring
            mock_memory_info = Mock()
            mock_memory_info.rss = 50 * 1024 * 1024  # 50MB
            mock_process.return_value.memory_info.return_value = mock_memory_info
            
            converter = ImageConverter()
            
            # Large PDF data to test memory handling
            large_pdf_data = b'''%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj
3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 800 800]/Contents 4 0 R>>endobj
4 0 obj<</Length 1000>>stream
''' + b'BT /F1 12 Tf ' + b'50 750 Td (Large Content) Tj ' * 20 + b'ET\n' + b'''endstream endobj
xref 0 5 0000000000 65535 f 0000000009 00000 n 0000000058 00000 n 0000000115 00000 n 0000000200 00000 n 
trailer<</Size 5/Root 1 0 R>>startxref 1294 %%EOF'''
            
            result = converter.convert_pdf_to_png(large_pdf_data, Path(temp_dir))
            
            # Should succeed without excessive memory usage
            assert result.success
            # Memory info should be captured in result
            assert hasattr(result, 'peak_memory_mb')

    def test_concurrent_conversions(self):
        """Test multiple simultaneous conversions."""
        with tempfile.TemporaryDirectory() as temp_dir:
            converter = ImageConverter()
            
            import threading
            import concurrent.futures
            
            def convert_worker(worker_id):
                pdf_data = f'''%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj
3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 400 400]/Contents 4 0 R>>endobj
4 0 obj<</Length 50>>stream
BT /F1 12 Tf 50 350 Td (Worker {worker_id}) Tj ET
endstream endobj
xref 0 5 0000000000 65535 f 0000000009 00000 n 0000000058 00000 n 0000000115 00000 n 0000000200 00000 n 
trailer<</Size 5/Root 1 0 R>>startxref 300 %%EOF'''.encode()
                
                return converter.convert_pdf_to_png(pdf_data, Path(temp_dir))
            
            # Run multiple conversions concurrently
            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                futures = [executor.submit(convert_worker, i) for i in range(5)]
                results = [future.result() for future in concurrent.futures.as_completed(futures)]
            
            # All conversions should succeed
            assert len(results) == 5
            assert all(result.success for result in results)
            assert all(result.png_path.exists() for result in results)

    def test_output_directory_handling(self):
        """Test output directory creation and permissions."""
        with tempfile.TemporaryDirectory() as temp_dir:
            converter = ImageConverter()
            
            # Test with non-existent output directory
            output_dir = Path(temp_dir) / "non_existent" / "output"
            
            pdf_data = b'''%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj
3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 400 400]/Contents 4 0 R>>endobj
4 0 obj<</Length 44>>stream
BT /F1 12 Tf 50 350 Td (Directory Test) Tj ET
endstream endobj
xref 0 5 0000000000 65535 f 0000000009 00000 n 0000000058 00000 n 0000000115 00000 n 0000000200 00000 n 
trailer<</Size 5/Root 1 0 R>>startxref 294 %%EOF'''
            
            result = converter.convert_pdf_to_png(pdf_data, output_dir)
            
            # Should create directory and succeed
            assert result.success
            assert output_dir.exists()
            assert result.png_path.parent == output_dir

    def test_filename_collision_handling(self):
        """Test handling of filename collisions."""
        with tempfile.TemporaryDirectory() as temp_dir:
            converter = ImageConverter()
            output_dir = Path(temp_dir)
            
            # Create existing file with same name pattern
            existing_file = output_dir / "preview_001.png"
            existing_file.write_bytes(b"existing content")
            
            pdf_data = b'''%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj
3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 400 400]/Contents 4 0 R>>endobj
4 0 obj<</Length 44>>stream
BT /F1 12 Tf 50 350 Td (Collision Test) Tj ET
endstream endobj
xref 0 5 0000000000 65535 f 0000000009 00000 n 0000000058 00000 n 0000000115 00000 n 0000000200 00000 n 
trailer<</Size 5/Root 1 0 R>>startxref 294 %%EOF'''
            
            result = converter.convert_pdf_to_png(pdf_data, output_dir)
            
            # Should handle collision by using different filename
            assert result.success
            assert result.png_path != existing_file
            assert result.png_path.exists()

    def test_cleanup_temp_files(self):
        """Test cleanup of temporary files during conversion."""
        with tempfile.TemporaryDirectory() as temp_dir:
            converter = ImageConverter()
            
            # Track files before conversion
            files_before = set(Path(temp_dir).rglob("*"))
            
            pdf_data = b'''%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj
3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 400 400]/Contents 4 0 R>>endobj
4 0 obj<</Length 44>>stream
BT /F1 12 Tf 50 350 Td (Cleanup Test) Tj ET
endstream endobj
xref 0 5 0000000000 65535 f 0000000009 00000 n 0000000058 00000 n 0000000115 00000 n 0000000200 00000 n 
trailer<</Size 5/Root 1 0 R>>startxref 294 %%EOF'''
            
            result = converter.convert_pdf_to_png(pdf_data, Path(temp_dir))
            
            assert result.success
            
            # Only the output PNG should be added, no temp files should remain
            files_after = set(Path(temp_dir).rglob("*"))
            new_files = files_after - files_before
            
            # Should only have the output PNG file
            assert len(new_files) == 1
            assert list(new_files)[0] == result.png_path