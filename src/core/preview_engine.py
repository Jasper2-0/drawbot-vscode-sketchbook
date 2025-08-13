"""
PreviewEngine for generating live previews of DrawBot sketches.
"""
import os
import sys
import subprocess
import time
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime
import contextlib
import io

from .drawbot_wrapper import DrawBotWrapper
from .sketch_runner import SketchRunner, ExecutionResult


@dataclass
class PreviewResult:
    """Result of preview generation."""
    success: bool
    pdf_data: Optional[bytes] = None
    error: Optional[str] = None
    generation_time: float = 0.0
    sketch_path: Optional[Path] = None
    timestamp: Optional[datetime] = None


class PreviewEngine:
    """Manages in-memory preview generation for live preview system."""
    
    def __init__(self, project_path: Path, timeout: float = 5.0):
        """Initialize preview engine.
        
        Args:
            project_path: Path to the project directory
            timeout: Maximum execution time in seconds
        """
        self.project_path = project_path
        self.timeout = timeout
        self.sketch_runner = SketchRunner(project_path, timeout=timeout)
    
    def generate_preview(self, sketch_path: Path) -> bytes:
        """Generate PDF preview from sketch file.
        
        Args:
            sketch_path: Path to the sketch file
            
        Returns:
            PDF data as bytes
        """
        start_time = time.time()
        
        try:
            # Validate sketch file exists
            if not sketch_path.exists():
                return self._generate_error_pdf("Sketch file not found", sketch_path)
            
            # Check file permissions
            if not os.access(sketch_path, os.R_OK):
                return self._generate_error_pdf("Permission denied", sketch_path)
            
            # Generate preview using in-memory execution
            pdf_data = self._execute_sketch_for_preview(sketch_path)
            
            generation_time = time.time() - start_time
            
            # Validate PDF data
            if pdf_data and len(pdf_data) > 0:
                return pdf_data
            else:
                return self._generate_error_pdf("Preview generation failed", sketch_path)
                
        except Exception as e:
            generation_time = time.time() - start_time
            return self._generate_error_pdf(f"Error: {str(e)}", sketch_path)
    
    def _execute_sketch_for_preview(self, sketch_path: Path) -> bytes:
        """Execute sketch and return PDF data."""
        
        # Create a modified execution environment for preview
        execution_script = f"""
import os
import sys
import traceback

# Change to project directory
os.chdir(r'{self.project_path}')

# Add project path to Python path
sys.path.insert(0, r'{self.project_path}')

# Import DrawBot wrapper for in-memory PDF generation
try:
    from src.core.drawbot_wrapper import DrawBotWrapper
    
    # Create wrapper instance
    wrapper = DrawBotWrapper(mock_mode=False)  # Try real mode first
    
    # Read sketch file
    with open(r'{sketch_path}', 'r', encoding='utf-8') as f:
        sketch_code = f.read()
    
    # Replace direct DrawBot imports with wrapper
    # This ensures we can capture PDF data
    sketch_code = sketch_code.replace('import drawbot', 'wrapper = globals()["__preview_wrapper__"]\\ndrawbot = wrapper')
    sketch_code = sketch_code.replace('import drawBot as drawbot', 'wrapper = globals()["__preview_wrapper__"]\\ndrawbot = wrapper')
    sketch_code = sketch_code.replace('from drawBot import', 'wrapper = globals()["__preview_wrapper__"]\\n# Original import disabled for preview')
    
    # Create execution namespace
    namespace = {{
        '__name__': '__main__',
        '__file__': r'{sketch_path}',
        '__preview_wrapper__': wrapper,
        'drawbot': wrapper,  # Make drawbot available directly
    }}
    
    # Execute the sketch
    exec(sketch_code, namespace)
    
    # Get PDF data from wrapper
    pdf_data = wrapper.get_pdf_data()
    
    # Write PDF data to stdout as base64 for safe transport
    import base64
    print("PDF_DATA_START")
    print(base64.b64encode(pdf_data).decode('ascii'))
    print("PDF_DATA_END")
    
except Exception as e:
    print(f"ERROR: {{type(e).__name__}}: {{str(e)}}", file=sys.stderr)
    traceback.print_exc(file=sys.stderr)
    sys.exit(1)
"""
        
        try:
            # Get Python executable
            python_executable = self._get_python_executable()
            
            # Run the execution script
            process = subprocess.Popen(
                [python_executable, '-c', execution_script],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=str(self.project_path),
                env=os.environ.copy()
            )
            
            # Wait for completion with timeout
            try:
                stdout, stderr = process.communicate(timeout=self.timeout)
                return_code = process.returncode
                
                if return_code == 0:
                    # Extract PDF data from stdout
                    pdf_data = self._extract_pdf_data(stdout)
                    if pdf_data:
                        return pdf_data
                    else:
                        # No PDF data but successful exit - might be empty sketch
                        return self._generate_mock_pdf()
                else:
                    # Error occurred, generate error PDF
                    error_msg = stderr if stderr else "Unknown execution error"
                    return self._generate_error_pdf(error_msg, sketch_path)
                    
            except subprocess.TimeoutExpired:
                process.kill()
                try:
                    stdout, stderr = process.communicate(timeout=1.0)
                except subprocess.TimeoutExpired:
                    pass
                
                return self._generate_error_pdf("Sketch execution timed out", sketch_path)
                
        except Exception as e:
            return self._generate_error_pdf(f"Execution failed: {str(e)}", sketch_path)
    
    def _extract_pdf_data(self, stdout: str) -> Optional[bytes]:
        """Extract PDF data from subprocess stdout."""
        lines = stdout.strip().split('\n')
        
        # Find PDF data markers
        start_idx = None
        end_idx = None
        
        for i, line in enumerate(lines):
            if line.strip() == "PDF_DATA_START":
                start_idx = i + 1
            elif line.strip() == "PDF_DATA_END":
                end_idx = i
                break
        
        if start_idx is not None and end_idx is not None:
            # Extract base64 data
            b64_data = ''.join(lines[start_idx:end_idx])
            try:
                import base64
                pdf_data = base64.b64decode(b64_data)
                return pdf_data
            except Exception:
                return None
        
        return None
    
    def _generate_error_pdf(self, error_message: str, sketch_path: Optional[Path] = None) -> bytes:
        """Generate an error PDF with error information."""
        # Create a simple error PDF with error text embedded in the PDF structure
        error_text = f"Preview Error: {error_message}"
        if sketch_path:
            error_text += f" (File: {sketch_path.name})"
            
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Create a PDF with error information embedded in the content stream
        error_pdf = f'''%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj

2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj

3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 600 400]
/Contents 4 0 R
>>
endobj

4 0 obj
<<
/Length 200
>>
stream
BT
/F1 16 Tf
1 0 0 rg
50 350 Td
(Error: Preview Generation Failed) Tj
0 -20 Td
/F1 12 Tf
0 0 0 rg
({error_message[:100]}) Tj
0 -40 Td
/F1 10 Tf
0.5 0.5 0.5 rg
(Generated: {timestamp}) Tj
ET
endstream
endobj

xref
0 5
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000200 00000 n 
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
450
%%EOF'''.encode('utf-8')
        
        return error_pdf
    
    def _generate_mock_pdf(self) -> bytes:
        """Generate basic mock PDF for fallback."""
        wrapper = DrawBotWrapper(mock_mode=True)
        wrapper.size(400, 300)
        wrapper.fill(0.8, 0.8, 0.9)
        wrapper.rect(0, 0, 400, 300)
        return wrapper.get_pdf_data()
    
    def _get_python_executable(self) -> str:
        """Get the appropriate Python executable, preferring virtual environment if available."""
        
        # Check if we're in a virtual environment
        if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
            # We're in a virtual environment, use current interpreter
            return sys.executable
        
        # Check for local venv directory
        venv_python = self.project_path / 'venv' / 'bin' / 'python3'
        if venv_python.exists():
            return str(venv_python)
        
        # Check for virtualenv directory  
        venv_python = self.project_path / 'venv' / 'bin' / 'python'
        if venv_python.exists():
            return str(venv_python)
        
        # Fall back to system Python
        return sys.executable