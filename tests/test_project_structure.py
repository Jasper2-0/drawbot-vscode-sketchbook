"""
Tests for project structure validation and management.
"""
import os
import shutil
import tempfile
from pathlib import Path

import pytest


class TestProjectStructure:
    """Test suite for project structure operations."""

    def test_creates_required_directories(self):
        """Test that project initialization creates all required directories."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)

            # Import will happen after implementation
            # For now, test the expected directory structure
            expected_dirs = [
                "sketches",
                "templates",
                "examples",
                "tools",
                "docs",
                "extensions",
                "src",
                "tests",
            ]

            # This test will fail initially - that's the point of TDD
            from src.core.project_structure import ProjectStructure

            ps = ProjectStructure(project_path)
            ps.create_directories()

            for dir_name in expected_dirs:
                assert (
                    project_path / dir_name
                ).exists(), f"Directory {dir_name} should exist"
                assert (
                    project_path / dir_name
                ).is_dir(), f"{dir_name} should be a directory"

    def test_validates_project_structure(self):
        """Test that project structure validator works correctly."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)

            from src.core.project_structure import ProjectStructure

            ps = ProjectStructure(project_path)

            # Should fail validation on empty directory
            assert not ps.validate_structure()

            # Create directories
            ps.create_directories()

            # Should pass validation after creating directories
            assert ps.validate_structure()

    def test_detects_missing_directories(self):
        """Test detection of missing required directories."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)

            from src.core.project_structure import ProjectStructure

            ps = ProjectStructure(project_path)

            # Create only some directories
            (project_path / "sketches").mkdir()
            (project_path / "templates").mkdir()

            missing = ps.get_missing_directories()

            # Should detect missing directories
            assert "examples" in missing
            assert "tools" in missing
            assert "docs" in missing
            assert "extensions" in missing
            assert "src" in missing
            assert "tests" in missing

            # Should not include existing directories
            assert "sketches" not in missing
            assert "templates" not in missing

    def test_handles_invalid_project_path(self):
        """Test handling of invalid project paths."""
        from src.core.project_structure import ProjectStructure

        # Test with non-existent path
        invalid_path = Path("/non/existent/path")

        with pytest.raises(ValueError, match="Project path does not exist"):
            ProjectStructure(invalid_path)

    def test_preserves_existing_directories(self):
        """Test that existing directories are preserved during creation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)

            # Create a directory with some content
            sketches_dir = project_path / "sketches"
            sketches_dir.mkdir()
            test_file = sketches_dir / "test.py"
            test_file.write_text("# Test sketch")

            from src.core.project_structure import ProjectStructure

            ps = ProjectStructure(project_path)
            ps.create_directories()

            # Test file should still exist
            assert test_file.exists()
            assert test_file.read_text() == "# Test sketch"
