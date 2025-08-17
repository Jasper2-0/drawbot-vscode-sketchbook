"""
PreviewCache - Preview image storage and cleanup system for live preview.
"""

import json
import shutil
import threading
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


@dataclass
class CacheEntry:
    """Single preview cache entry."""

    sketch_name: str
    version: int
    file_path: Path
    created_at: datetime
    file_size_bytes: int
    thumbnail_path: Optional[Path] = None
    thumbnail_size_bytes: Optional[int] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "sketch_name": self.sketch_name,
            "version": self.version,
            "file_path": str(self.file_path),
            "created_at": self.created_at.isoformat(),
            "file_size_bytes": self.file_size_bytes,
            "thumbnail_path": str(self.thumbnail_path) if self.thumbnail_path else None,
            "thumbnail_size_bytes": self.thumbnail_size_bytes,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CacheEntry":
        """Create from dictionary."""
        return cls(
            sketch_name=data["sketch_name"],
            version=data["version"],
            file_path=Path(data["file_path"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            file_size_bytes=data["file_size_bytes"],
            thumbnail_path=Path(data["thumbnail_path"]) if data.get("thumbnail_path") else None,
            thumbnail_size_bytes=data.get("thumbnail_size_bytes"),
        )


@dataclass
class CacheResult:
    """Result of cache storage operation."""

    success: bool
    preview_url: Optional[str] = None
    preview_path: Optional[Path] = None
    thumbnail_url: Optional[str] = None
    thumbnail_path: Optional[Path] = None
    version: Optional[int] = None
    error: Optional[str] = None


class PreviewCache:
    """Manages preview image storage with versioning and automatic cleanup."""

    def __init__(
        self,
        cache_dir: Path,
        max_versions_per_sketch: int = 5,
        max_total_size_mb: float = 100,
        max_age_hours: int = 24,
        thumbnail_size: tuple = (300, 200),
    ):
        """Initialize preview cache.

        Args:
            cache_dir: Directory to store cached previews
            max_versions_per_sketch: Maximum versions to keep per sketch
            max_total_size_mb: Maximum total cache size in MB
            max_age_hours: Maximum age for cache entries in hours
            thumbnail_size: Thumbnail dimensions (width, height)
        """
        self.cache_dir = Path(cache_dir)
        self.max_versions_per_sketch = max_versions_per_sketch
        self.max_total_size_mb = max_total_size_mb
        self.max_age_hours = max_age_hours
        self.thumbnail_size = thumbnail_size

        # Thread safety
        self.lock = threading.RLock()

        # Cache metadata
        self.metadata_file = self.cache_dir / ".cache_metadata.json"
        self.entries: Dict[str, List[CacheEntry]] = {}

        # Initialize cache
        self._initialize_cache()

    def _initialize_cache(self):
        """Initialize cache directory and load existing metadata."""
        with self.lock:
            # Create cache directory
            self.cache_dir.mkdir(parents=True, exist_ok=True)

            # Load existing metadata
            self._load_metadata()

            # Clean up orphaned files and validate entries
            self._validate_cache_integrity()

    def _load_metadata(self):
        """Load cache metadata from disk."""
        try:
            if self.metadata_file.exists():
                with open(self.metadata_file, "r") as f:
                    data = json.load(f)

                # Convert to CacheEntry objects
                for sketch_name, entry_list in data.items():
                    self.entries[sketch_name] = [
                        CacheEntry.from_dict(entry_data) for entry_data in entry_list
                    ]
        except Exception:
            # If metadata is corrupted, start fresh
            self.entries = {}

    def _save_metadata(self):
        """Save cache metadata to disk."""
        try:
            # Convert to serializable format
            data = {}
            for sketch_name, entry_list in self.entries.items():
                data[sketch_name] = [entry.to_dict() for entry in entry_list]

            # Write atomically
            temp_file = self.metadata_file.with_suffix(".tmp")
            with open(temp_file, "w") as f:
                json.dump(data, f, indent=2)

            temp_file.replace(self.metadata_file)

        except Exception:
            # Ignore metadata save errors - cache will rebuild from files
            pass

    def _validate_cache_integrity(self):
        """Validate cache integrity and remove orphaned files."""
        # Find all PNG files in cache directory
        existing_files = set(self.cache_dir.glob("*.png"))

        # Find referenced files in metadata
        referenced_files = set()
        valid_entries = {}

        for sketch_name, entry_list in self.entries.items():
            valid_entry_list = []
            for entry in entry_list:
                if entry.file_path.exists():
                    referenced_files.add(entry.file_path)
                    # Also track thumbnail files
                    if entry.thumbnail_path and entry.thumbnail_path.exists():
                        referenced_files.add(entry.thumbnail_path)
                    valid_entry_list.append(entry)

            if valid_entry_list:
                valid_entries[sketch_name] = valid_entry_list

        # Update entries to only valid ones
        self.entries = valid_entries

        # Remove orphaned files
        orphaned_files = existing_files - referenced_files
        for orphaned_file in orphaned_files:
            try:
                orphaned_file.unlink()
            except:
                pass  # Ignore cleanup errors

    def store_preview(self, sketch_name: str, image_data: bytes) -> CacheResult:
        """Store a preview image in the cache.

        Args:
            sketch_name: Name of the sketch
            image_data: PNG image data

        Returns:
            CacheResult with storage status and preview information
        """
        with self.lock:
            try:
                # Validate input
                if not image_data:
                    return CacheResult(success=False, error="Empty image data provided")

                if not sketch_name or not sketch_name.strip():
                    return CacheResult(
                        success=False, error="Invalid sketch name provided"
                    )

                # Generate version number (timestamp-based)
                version = int(time.time() * 1000)  # Millisecond timestamp

                # Generate filename
                filename = f"{sketch_name}_v{version}.png"
                file_path = self.cache_dir / filename

                # Ensure unique filename
                counter = 1
                while file_path.exists():
                    filename = f"{sketch_name}_v{version}_{counter}.png"
                    file_path = self.cache_dir / filename
                    counter += 1

                # Write image data
                with open(file_path, "wb") as f:
                    f.write(image_data)

                # Create cache entry
                entry = CacheEntry(
                    sketch_name=sketch_name,
                    version=version,
                    file_path=file_path,
                    created_at=datetime.now(),
                    file_size_bytes=len(image_data),
                )

                # Add to cache entries
                if sketch_name not in self.entries:
                    self.entries[sketch_name] = []

                self.entries[sketch_name].append(entry)

                # Sort by version (newest first)
                self.entries[sketch_name].sort(key=lambda x: x.version, reverse=True)

                # Cleanup old versions for this sketch
                self._cleanup_sketch_versions(sketch_name)

                # Save metadata
                self._save_metadata()

                # Generate preview URL
                preview_url = f"/preview/{filename}?v={version}"

                # Trigger global cleanup if needed
                self._trigger_global_cleanup()

                return CacheResult(
                    success=True,
                    preview_url=preview_url,
                    preview_path=file_path,
                    version=version,
                )

            except Exception as e:
                return CacheResult(
                    success=False, error=f"Failed to store preview: {str(e)}"
                )

    def _generate_thumbnail(self, full_image_path: Path, thumbnail_path: Path) -> bool:
        """Generate thumbnail from full-size image.
        
        Args:
            full_image_path: Path to the full-size image
            thumbnail_path: Path where thumbnail should be saved
            
        Returns:
            True if thumbnail was generated successfully
        """
        if not PIL_AVAILABLE:
            return False
            
        try:
            with Image.open(full_image_path) as img:
                # Convert to RGB if necessary (for consistent output)
                if img.mode not in ('RGB', 'RGBA'):
                    img = img.convert('RGB')
                
                # Calculate thumbnail size maintaining aspect ratio
                img.thumbnail(self.thumbnail_size, Image.Resampling.LANCZOS)
                
                # Create a canvas with the exact thumbnail size and center the image
                thumb_width, thumb_height = self.thumbnail_size
                canvas = Image.new('RGB', (thumb_width, thumb_height), (240, 240, 240))  # Light gray background
                
                # Calculate position to center the image
                img_width, img_height = img.size
                x = (thumb_width - img_width) // 2
                y = (thumb_height - img_height) // 2
                
                # Paste the image onto the canvas
                if img.mode == 'RGBA':
                    canvas.paste(img, (x, y), img)
                else:
                    canvas.paste(img, (x, y))
                
                # Save thumbnail
                canvas.save(thumbnail_path, 'PNG', optimize=True)
                return True
                
        except Exception:
            return False

    def generate_thumbnail_for_entry(self, sketch_name: str, version: Optional[int] = None) -> Optional[str]:
        """Generate thumbnail for an existing cache entry.
        
        Args:
            sketch_name: Name of the sketch
            version: Specific version, or None for current version
            
        Returns:
            Thumbnail URL if successful, None otherwise
        """
        with self.lock:
            # Get the cache entry
            if version is not None:
                entry = self.get_preview_version(sketch_name, version)
            else:
                entry = self.get_current_preview(sketch_name)
                
            if not entry or not entry.file_path.exists():
                return None
                
            # Check if thumbnail already exists
            if entry.thumbnail_path and entry.thumbnail_path.exists():
                return f"/thumbnail/{entry.thumbnail_path.name}"
            
            # Generate thumbnail filename
            base_filename = entry.file_path.stem  # e.g., "sketch_v123456789"
            thumbnail_filename = f"{base_filename}_thumb.png"
            thumbnail_path = self.cache_dir / thumbnail_filename
            
            # Generate thumbnail
            if self._generate_thumbnail(entry.file_path, thumbnail_path):
                # Update cache entry with thumbnail info
                entry.thumbnail_path = thumbnail_path
                try:
                    entry.thumbnail_size_bytes = thumbnail_path.stat().st_size
                except:
                    entry.thumbnail_size_bytes = 0
                
                # Save updated metadata
                self._save_metadata()
                
                return f"/thumbnail/{thumbnail_filename}"
            
            return None

    def get_current_preview(self, sketch_name: str) -> Optional[CacheEntry]:
        """Get the current (most recent) preview for a sketch.

        Args:
            sketch_name: Name of the sketch

        Returns:
            CacheEntry for the most recent preview, or None if not found
        """
        with self.lock:
            if sketch_name in self.entries and self.entries[sketch_name]:
                # Return the most recent (first in sorted list)
                return self.entries[sketch_name][0]
            return None

    def get_preview_version(
        self, sketch_name: str, version: int
    ) -> Optional[CacheEntry]:
        """Get a specific version of a preview.

        Args:
            sketch_name: Name of the sketch
            version: Version number

        Returns:
            CacheEntry for the specified version, or None if not found
        """
        with self.lock:
            if sketch_name in self.entries:
                for entry in self.entries[sketch_name]:
                    if entry.version == version:
                        return entry
            return None

    def get_available_versions(self, sketch_name: str) -> List[int]:
        """Get all available versions for a sketch.

        Args:
            sketch_name: Name of the sketch

        Returns:
            List of version numbers, sorted newest first
        """
        with self.lock:
            if sketch_name in self.entries:
                return [entry.version for entry in self.entries[sketch_name]]
            return []

    def _cleanup_sketch_versions(self, sketch_name: str):
        """Clean up old versions for a specific sketch."""
        if sketch_name not in self.entries:
            return

        entries = self.entries[sketch_name]

        # Keep only the most recent versions
        if len(entries) > self.max_versions_per_sketch:
            # Remove oldest versions
            to_remove = entries[self.max_versions_per_sketch :]

            for entry in to_remove:
                try:
                    if entry.file_path.exists():
                        entry.file_path.unlink()
                    # Also remove thumbnail if it exists
                    if entry.thumbnail_path and entry.thumbnail_path.exists():
                        entry.thumbnail_path.unlink()
                except:
                    pass  # Ignore cleanup errors

            # Update entries list
            self.entries[sketch_name] = entries[: self.max_versions_per_sketch]

    def _trigger_global_cleanup(self):
        """Trigger global cache cleanup if needed."""
        total_size_mb = self.get_total_cache_size()

        if total_size_mb > self.max_total_size_mb:
            self.cleanup_old_previews()

    def cleanup_old_previews(self):
        """Clean up old previews based on age and size limits."""
        with self.lock:
            current_time = datetime.now()
            cutoff_time = current_time - timedelta(hours=self.max_age_hours)

            # Remove entries older than max_age
            for sketch_name in list(self.entries.keys()):
                entries = self.entries[sketch_name]
                valid_entries = []

                for entry in entries:
                    if entry.created_at > cutoff_time:
                        valid_entries.append(entry)
                    else:
                        # Remove old file and thumbnail
                        try:
                            if entry.file_path.exists():
                                entry.file_path.unlink()
                            if entry.thumbnail_path and entry.thumbnail_path.exists():
                                entry.thumbnail_path.unlink()
                        except:
                            pass

                if valid_entries:
                    self.entries[sketch_name] = valid_entries
                else:
                    del self.entries[sketch_name]

            # If still over size limit, remove oldest entries globally
            total_size_mb = self.get_total_cache_size()
            if total_size_mb > self.max_total_size_mb:
                self._aggressive_cleanup()

            # Save updated metadata
            self._save_metadata()

    def _aggressive_cleanup(self):
        """Aggressively clean up cache to meet size limits."""
        # Collect all entries with timestamps
        all_entries = []
        for sketch_name, entries in self.entries.items():
            for entry in entries:
                all_entries.append((entry.created_at, sketch_name, entry))

        # Sort by age (oldest first)
        all_entries.sort(key=lambda x: x[0])

        # Remove oldest entries until under size limit
        current_size_mb = self.get_total_cache_size()
        target_size_mb = self.max_total_size_mb * 0.8  # Clean to 80% of limit

        for created_at, sketch_name, entry in all_entries:
            if current_size_mb <= target_size_mb:
                break

            # Remove this entry
            try:
                if entry.file_path.exists():
                    file_size_mb = entry.file_size_bytes / (1024 * 1024)
                    entry.file_path.unlink()
                    current_size_mb -= file_size_mb
                
                # Also remove thumbnail
                if entry.thumbnail_path and entry.thumbnail_path.exists():
                    thumb_size_mb = (entry.thumbnail_size_bytes or 0) / (1024 * 1024)
                    entry.thumbnail_path.unlink()
                    current_size_mb -= thumb_size_mb

                # Remove from entries
                if sketch_name in self.entries:
                    self.entries[sketch_name] = [
                        e
                        for e in self.entries[sketch_name]
                        if e.version != entry.version
                    ]

                    # Remove sketch entry if no versions left
                    if not self.entries[sketch_name]:
                        del self.entries[sketch_name]

            except:
                pass  # Ignore cleanup errors

    def get_total_cache_size(self) -> float:
        """Get total cache size in MB.

        Returns:
            Total size of cached files in MB (including thumbnails)
        """
        total_bytes = 0
        for entry_list in self.entries.values():
            for entry in entry_list:
                if entry.file_path.exists():
                    total_bytes += entry.file_size_bytes
                # Include thumbnail size if it exists
                if entry.thumbnail_path and entry.thumbnail_path.exists():
                    total_bytes += entry.thumbnail_size_bytes or 0

        return total_bytes / (1024 * 1024)

    def get_statistics(self) -> Dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        with self.lock:
            total_sketches = len(self.entries)
            total_versions = sum(len(entries) for entries in self.entries.values())
            total_size_mb = self.get_total_cache_size()

            return {
                "total_sketches": total_sketches,
                "total_versions": total_versions,
                "total_size_mb": round(total_size_mb, 2),
                "max_size_mb": self.max_total_size_mb,
                "max_versions_per_sketch": self.max_versions_per_sketch,
                "max_age_hours": self.max_age_hours,
                "cache_dir": str(self.cache_dir),
            }

    def clear_cache(self):
        """Clear all cached previews."""
        with self.lock:
            # Remove all files and thumbnails
            for entry_list in self.entries.values():
                for entry in entry_list:
                    try:
                        if entry.file_path.exists():
                            entry.file_path.unlink()
                        if entry.thumbnail_path and entry.thumbnail_path.exists():
                            entry.thumbnail_path.unlink()
                    except:
                        pass

            # Clear entries
            self.entries = {}

            # Remove metadata file
            try:
                if self.metadata_file.exists():
                    self.metadata_file.unlink()
            except:
                pass
