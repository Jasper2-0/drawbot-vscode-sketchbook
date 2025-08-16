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
from typing import Any, Dict, Optional


@dataclass
class ExecutionResult:
    """Result of sketch execution."""

    success: bool
    error: Optional[str] = None
    execution_time: float = 0.0
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    output_path: Optional[Path] = None
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

# Patch DrawBot for retina scaling using imageResolution
def setup_retina_scaling():
    try:
        import drawBot
        # Store original saveImage function
        _original_saveImage = drawBot.saveImage

        def retina_saveImage(path, *args, **kwargs):
            # For PNG output, use high imageResolution for retina displays
            if str(path).lower().endswith('.png'):
                # Set imageResolution to 216 DPI (3x the standard 72 DPI) for retina
                kwargs['imageResolution'] = 216
            # For other formats (GIF, JPEG, etc.), don't modify - let DrawBot handle them normally
            return _original_saveImage(path, *args, **kwargs)

        # Only patch saveImage function
        drawBot.saveImage = retina_saveImage

    except ImportError:
        pass  # DrawBot not available, skip patching

setup_retina_scaling()

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
                output_path = self._find_output_files(output_dir)

                # If no files found in output dir, also check sketch directory
                if not output_path:
                    sketch_dir = sketch_path.parent
                    output_path = self._find_output_files(sketch_dir)

                # If still no files found, check sketch's output subdirectory
                if not output_path:
                    sketch_output_dir = sketch_path.parent / "output"
                    output_path = self._find_output_files(sketch_output_dir)

                if return_code == 0:
                    return ExecutionResult(
                        success=True,
                        stdout=stdout if stdout else None,
                        stderr=stderr if stderr else None,
                        output_path=output_path,
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

    def _find_output_files(self, output_dir: Path) -> Optional[Path]:
        """Find generated output files in the output directory."""

        # Common output extensions
        output_extensions = [".png", ".jpg", ".jpeg", ".pdf", ".svg", ".gif", ".mp4"]

        # Look for recently created files
        if not output_dir.exists():
            return None

        output_files = []
        for ext in output_extensions:
            pattern = f"*{ext}"
            matches = list(output_dir.glob(pattern))
            output_files.extend(matches)

        if output_files:
            # Return the most recently modified file
            return max(output_files, key=lambda f: f.stat().st_mtime)

        return None

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
