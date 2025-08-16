"""
Project structure management for DrawBot VSCode Sketchbook.
"""

from pathlib import Path
from typing import List, Set


class ProjectStructure:
    """Manages the project directory structure and validation."""

    REQUIRED_DIRECTORIES = {
        "sketches",
        "templates",
        "examples",
        "tools",
        "docs",
        "extensions",
        "src",
        "tests",
    }

    def __init__(self, project_path: Path):
        """Initialize with project path.

        Args:
            project_path: Path to the project directory

        Raises:
            ValueError: If project path does not exist
        """
        if not project_path.exists():
            raise ValueError("Project path does not exist")

        self.project_path = project_path

    def create_directories(self) -> None:
        """Create all required directories if they don't exist."""
        for dir_name in self.REQUIRED_DIRECTORIES:
            dir_path = self.project_path / dir_name
            dir_path.mkdir(exist_ok=True)

    def validate_structure(self) -> bool:
        """Validate that all required directories exist.

        Returns:
            True if all directories exist, False otherwise
        """
        for dir_name in self.REQUIRED_DIRECTORIES:
            dir_path = self.project_path / dir_name
            if not dir_path.exists() or not dir_path.is_dir():
                return False
        return True

    def get_missing_directories(self) -> List[str]:
        """Get list of missing required directories.

        Returns:
            List of missing directory names
        """
        missing = []
        for dir_name in self.REQUIRED_DIRECTORIES:
            dir_path = self.project_path / dir_name
            if not dir_path.exists() or not dir_path.is_dir():
                missing.append(dir_name)
        return missing
