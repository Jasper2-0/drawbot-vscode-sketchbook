"""
Sketch execution engine for DrawBot VSCode Sketchbook.
"""

import contextlib
import io
import os
import subprocess
import sys
import tempfile
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class ExecutionResult:
    """Result of sketch execution."""

    success: bool
    error: Optional[str] = None
    execution_time: float = 0.0
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    output_path: Optional[Path] = None
    output_files: Optional[List[Path]] = None  # For multi-page outputs
    sketch_path: Optional[Path] = None
    timestamp: Optional[datetime] = None


class SketchRunner:
    """Manages sketch execution with safety and monitoring."""

    def __init__(self, project_path: Path, timeout: float = 30.0):
        """Initialize sketch runner.

        Args:
            project_path: Path to the project directory
            timeout: Maximum execution time in seconds
        """
        self.project_path = project_path
        self.timeout = timeout

    def run_sketch(
        self, sketch_path: Path, output_dir: Optional[Path] = None
    ) -> ExecutionResult:
        """Run a sketch and return execution results.

        Args:
            sketch_path: Path to the sketch file to execute
            output_dir: Optional custom output directory

        Returns:
            ExecutionResult containing execution status and outputs
        """
        start_time = time.time()
        timestamp = datetime.now()

        # Validate sketch file exists
        if not sketch_path.exists():
            return ExecutionResult(
                success=False,
                error=f"Sketch file not found: {sketch_path}",
                timestamp=timestamp,
                sketch_path=sketch_path,
            )

        # Set up output directory
        if output_dir is None:
            output_dir = self.project_path

        # Create a safe execution environment
        try:
            result = self._execute_sketch_safely(sketch_path, output_dir)
            execution_time = time.time() - start_time

            result.execution_time = execution_time
            result.sketch_path = sketch_path
            result.timestamp = timestamp

            return result

        except Exception as e:
            execution_time = time.time() - start_time
            return ExecutionResult(
                success=False,
                error=f"Execution failed: {str(e)}",
                execution_time=execution_time,
                sketch_path=sketch_path,
                timestamp=timestamp,
            )

    def _execute_sketch_safely(
        self, sketch_path: Path, output_dir: Path
    ) -> ExecutionResult:
        """Execute sketch in isolated environment with timeout protection."""

        # Use subprocess for isolation and timeout control
        return self._execute_with_subprocess(sketch_path, output_dir)

    def _execute_with_subprocess(
        self, sketch_path: Path, output_dir: Path
    ) -> ExecutionResult:
        """Execute sketch using subprocess for better isolation."""

        # Determine the Python executable to use
        python_executable = self._get_python_executable()

        # Prepare environment
        env = os.environ.copy()

        # Create execution script that changes directory and runs the sketch
        # Ensure absolute paths
        sketch_path = sketch_path.resolve()
        sketch_dir = sketch_path.parent
        execution_script = f"""
import os
import sys
import traceback

# Change to sketch directory so relative paths work correctly
os.chdir(r'{sketch_dir}')

# Add project path to Python path for imports
sys.path.insert(0, r'{self.project_path}')

# Patch DrawBot for retina scaling and multi-page extraction
def setup_drawbot_patches():
    try:
        import drawBot
        from pathlib import Path
        
        # Store original functions
        _original_saveImage = drawBot.saveImage
        _original_newPage = drawBot.newPage
        
        # Track pages for multi-page documents
        _page_count = 0
        _current_sketch_name = Path(r'{sketch_path}').stem
        _page_images = []  # Store individual pages as they're created
        
        def patched_newPage(*args, **kwargs):
            nonlocal _page_count, _page_images
            
            # Before creating new page, save current page if we have content
            if _page_count >= 0:  # Always save, including page 0 (first page)
                try:
                    page_filename = f"{{_current_sketch_name}}_page_{{_page_count + 1}}.png"
                    page_path = Path(r'{sketch_path}').parent / page_filename
                    _original_saveImage(str(page_path), imageResolution=216)
                    _page_images.append(page_path)
                    print(f"Saved page {{_page_count + 1}} to {{page_filename}}", file=sys.stderr)
                except Exception as e:
                    print(f"Warning: Could not save page {{_page_count + 1}}: {{e}}", file=sys.stderr)
            
            _page_count += 1
            return _original_newPage(*args, **kwargs)
        
        def patched_saveImage(path, *args, **kwargs):
            nonlocal _page_count, _page_images
            
            # For PNG output, use high imageResolution for retina displays
            if str(path).lower().endswith('.png'):
                kwargs['imageResolution'] = 216
            
            # If this is a PDF and we have multiple pages, save the final page first
            if str(path).lower().endswith('.pdf') and _page_count >= 0:
                try:
                    # Save the final page
                    page_filename = f"{{_current_sketch_name}}_page_{{_page_count + 1}}.png"
                    page_path = Path(path).parent / page_filename
                    _original_saveImage(str(page_path), imageResolution=216)
                    _page_images.append(page_path)
                    print(f"Saved final page {{_page_count + 1}} to {{page_filename}}", file=sys.stderr)
                except Exception as e:
                    print(f"Warning: Could not save final page: {{e}}", file=sys.stderr)
            
            # Call original saveImage for the main output
            result = _original_saveImage(path, *args, **kwargs)
            return result

        # Apply patches
        drawBot.newPage = patched_newPage
        drawBot.saveImage = patched_saveImage

    except ImportError:
        pass  # DrawBot not available, skip patching

setup_drawbot_patches()

# Create output directory if it doesn't exist
output_dir = r'{output_dir}'
os.makedirs(output_dir, exist_ok=True)

try:
    with open(r'{sketch_path}', 'r', encoding='utf-8') as f:
        sketch_code = f.read()

    # Create a clean namespace for execution
    namespace = {{
        '__name__': '__main__',
        '__file__': r'{sketch_path}',
    }}

    # Execute the sketch
    exec(sketch_code, namespace)

except Exception as e:
    print(f"ERROR: {{type(e).__name__}}: {{str(e)}}", file=sys.stderr)
    traceback.print_exc(file=sys.stderr)
    sys.exit(1)
"""

        try:
            # Run the execution script
            process = subprocess.Popen(
                [python_executable, "-c", execution_script],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=str(sketch_dir),
                env=env,
            )

            # Wait for completion with timeout
            try:
                stdout, stderr = process.communicate(timeout=self.timeout)
                return_code = process.returncode

                # Determine output path (look for generated files)
                output_path, output_files = self._find_output_files(output_dir)

                # If no files found in output dir, also check sketch directory
                if not output_path:
                    sketch_dir = sketch_path.parent
                    output_path, output_files = self._find_output_files(sketch_dir)

                # If still no files found, check sketch's output subdirectory
                if not output_path:
                    sketch_output_dir = sketch_path.parent / "output"
                    output_path, output_files = self._find_output_files(sketch_output_dir)

                if return_code == 0:
                    return ExecutionResult(
                        success=True,
                        stdout=stdout if stdout else None,
                        stderr=stderr if stderr else None,
                        output_path=output_path,
                        output_files=output_files,
                    )
                else:
                    # Extract error from stderr
                    error_msg = stderr if stderr else "Unknown execution error"
                    return ExecutionResult(
                        success=False,
                        error=error_msg,
                        stdout=stdout if stdout else None,
                        stderr=stderr if stderr else None,
                    )

            except subprocess.TimeoutExpired:
                process.kill()
                try:
                    stdout, stderr = process.communicate(timeout=1.0)
                except subprocess.TimeoutExpired:
                    stdout, stderr = "", ""

                return ExecutionResult(
                    success=False,
                    error="Sketch execution timed out",
                    stdout=stdout if stdout else None,
                    stderr=stderr if stderr else None,
                )

        except Exception as e:
            return ExecutionResult(
                success=False, error=f"Failed to execute sketch: {str(e)}"
            )

    def _find_output_files(self, output_dir: Path) -> tuple[Optional[Path], Optional[List[Path]]]:
        """Find generated output files in the output directory.
        
        Returns:
            tuple: (primary_output_path, all_output_files)
                   primary_output_path: Main output file (for backward compatibility)
                   all_output_files: List of all output files (for multi-page support)
        """

        # Common output extensions
        output_extensions = [".png", ".jpg", ".jpeg", ".pdf", ".svg", ".gif", ".mp4"]

        # Look for recently created files
        if not output_dir.exists():
            return None, None

        output_files = []
        for ext in output_extensions:
            pattern = f"*{ext}"
            matches = list(output_dir.glob(pattern))
            output_files.extend(matches)

        if not output_files:
            return None, None

        # Check for multi-page pattern (page_1.png, page_2.png, etc.)
        page_files = [f for f in output_files if f.stem.startswith('page_') and f.stem[5:].isdigit()]
        
        if page_files:
            # Sort page files by page number
            page_files.sort(key=lambda f: int(f.stem[5:]))
            # Return first page as primary, all pages as list
            return page_files[0], page_files
        else:
            # Single file output - return most recent as primary
            primary_file = max(output_files, key=lambda f: f.stat().st_mtime)
            return primary_file, [primary_file]

    def validate_sketch_before_run(self, sketch_path: Path) -> ExecutionResult:
        """Validate sketch syntax before execution.

        Args:
            sketch_path: Path to sketch file

        Returns:
            ExecutionResult indicating validation success/failure
        """
        if not sketch_path.exists():
            return ExecutionResult(
                success=False,
                error=f"Sketch file not found: {sketch_path}",
                sketch_path=sketch_path,
            )

        try:
            with open(sketch_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Try to compile the code
            compile(content, str(sketch_path), "exec")

            return ExecutionResult(success=True, sketch_path=sketch_path)

        except SyntaxError as e:
            return ExecutionResult(
                success=False,
                error=f"SyntaxError: {e.msg} at line {e.lineno}",
                sketch_path=sketch_path,
            )
        except Exception as e:
            return ExecutionResult(
                success=False,
                error=f"Validation error: {str(e)}",
                sketch_path=sketch_path,
            )

    def _get_python_executable(self) -> str:
        """Get the appropriate Python executable, preferring virtual environment if available."""

        # Check if we're in a virtual environment
        if hasattr(sys, "real_prefix") or (
            hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix
        ):
            # We're in a virtual environment, use current interpreter
            return sys.executable

        # Check for local venv directory
        venv_python = self.project_path / "venv" / "bin" / "python3"
        if venv_python.exists():
            return str(venv_python)

        # Check for virtualenv directory
        venv_python = self.project_path / "venv" / "bin" / "python"
        if venv_python.exists():
            return str(venv_python)

        # Fall back to system Python
        return sys.executable
