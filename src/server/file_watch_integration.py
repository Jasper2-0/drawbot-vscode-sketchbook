"""
FileWatchIntegration - Bridge between FileWatcher and preview system.
"""
import asyncio
from pathlib import Path
from typing import Dict, Optional, List, Set
import logging

from ..core.file_watcher import FileWatcher
from ..core.preview_engine import PreviewEngine
from ..core.preview_cache import PreviewCache


class FileWatchIntegration:
    """Bridges file watching with the live preview system."""
    
    def __init__(self, project_path: Path, cache_dir: Path, preview_manager, 
                 debounce_delay: float = 0.3):
        """Initialize file watch integration.
        
        Args:
            project_path: Path to project directory
            cache_dir: Path to preview cache directory  
            preview_manager: LivePreviewManager instance for broadcasting
            debounce_delay: Delay for file change debouncing
        """
        self.project_path = Path(project_path)
        self.cache_dir = Path(cache_dir)
        self.preview_manager = preview_manager
        self.debounce_delay = debounce_delay
        
        # Initialize components
        self.file_watcher = FileWatcher(debounce_delay=debounce_delay)
        self.cache = PreviewCache(cache_dir)
        self.preview_engine = PreviewEngine(project_path, self.cache)
        
        # Track watched sketches
        self.watched_sketches: Set[str] = set()
        self.execution_locks: Dict[str, asyncio.Lock] = {}
        
        # Logging
        self.logger = logging.getLogger(__name__)
    
    def _find_sketch_file(self, sketch_name: str) -> Optional[Path]:
        """Find sketch file supporting both flat and folder-based structures.
        
        Args:
            sketch_name: Name of the sketch
            
        Returns:
            Path to sketch file if found, None otherwise
        """
        # Try flat structure
        sketch_file = self.project_path / f"{sketch_name}.py"
        if sketch_file.exists() and sketch_file.is_file():
            return sketch_file
        
        # Try folder-based structure
        folder_sketch_file = self.project_path / sketch_name / f"{sketch_name}.py"
        if folder_sketch_file.exists() and folder_sketch_file.is_file():
            return folder_sketch_file
        
        return None
    
    async def start_watching_sketch(self, sketch_name: str):
        """Start watching a sketch file for changes.
        
        Args:
            sketch_name: Name of sketch to watch
        """
        if sketch_name in self.watched_sketches:
            return  # Already watching
        
        # Find sketch file (supports both flat and folder-based structures)
        sketch_file = self._find_sketch_file(sketch_name)
        if not sketch_file:
            self.logger.warning(f"Sketch file not found: {sketch_name}")
            return
        
        # Create execution lock for this sketch
        self.execution_locks[sketch_name] = asyncio.Lock()
        
        # Set up file watcher callback
        def on_file_changed(file_path: Path):
            # Schedule async execution safely
            try:
                loop = asyncio.get_event_loop()
                loop.create_task(self._handle_file_change(sketch_name, file_path))
            except RuntimeError:
                # No event loop running, create new one or use thread-safe call
                import threading
                def run_async():
                    asyncio.run(self._handle_file_change(sketch_name, file_path))
                thread = threading.Thread(target=run_async)
                thread.start()
        
        # Start watching the file
        self.file_watcher.watch_file(sketch_file, on_file_changed)
        self.watched_sketches.add(sketch_name)
        
        self.logger.info(f"Started watching sketch: {sketch_name}")
    
    async def stop_watching_sketch(self, sketch_name: str):
        """Stop watching a sketch file.
        
        Args:
            sketch_name: Name of sketch to stop watching
        """
        if sketch_name not in self.watched_sketches:
            return
        
        # Find sketch file
        sketch_file = self._find_sketch_file(sketch_name)
        if sketch_file:
            # Stop watching
            self.file_watcher.unwatch_file(sketch_file)
        self.watched_sketches.discard(sketch_name)
        
        # Clean up execution lock
        if sketch_name in self.execution_locks:
            del self.execution_locks[sketch_name]
        
        self.logger.info(f"Stopped watching sketch: {sketch_name}")
    
    async def _handle_file_change(self, sketch_name: str, file_path: Path):
        """Handle file change event.
        
        Args:
            sketch_name: Name of changed sketch
            file_path: Path to changed file
        """
        # Use lock to prevent concurrent executions of same sketch
        if sketch_name not in self.execution_locks:
            return
        
        async with self.execution_locks[sketch_name]:
            try:
                self.logger.info(f"File changed: {sketch_name}")
                
                # Broadcast execution started
                await self.preview_manager.broadcast_to_sketch(sketch_name, {
                    "type": "execution_started",
                    "sketch": sketch_name
                })
                
                # Execute sketch with timing
                import time
                start_time = time.time()
                result = self.preview_engine.execute_sketch(file_path)
                total_time = time.time() - start_time
                self.logger.info(f"Total execution time for {sketch_name}: {total_time:.3f}s")
                
                if result.success:
                    # Broadcast success with preview URL
                    message = {
                        "type": "preview_updated",
                        "sketch": sketch_name,
                        "status": "success",
                        "execution_time": result.execution_time
                    }
                    
                    if result.preview_url:
                        message["image_url"] = result.preview_url
                    
                    if result.version:
                        message["version"] = result.version
                    
                    await self.preview_manager.broadcast_to_sketch(sketch_name, message)
                    
                    self.logger.info(f"Sketch executed successfully: {sketch_name} "
                                   f"({result.execution_time:.3f}s)")
                
                else:
                    # Broadcast error
                    await self.preview_manager.broadcast_to_sketch(sketch_name, {
                        "type": "execution_error",
                        "sketch": sketch_name,
                        "error": result.error,
                        "execution_time": result.execution_time if result.execution_time else 0
                    })
                    
                    self.logger.warning(f"Sketch execution failed: {sketch_name} - {result.error}")
                
            except Exception as e:
                # Broadcast unexpected error
                await self.preview_manager.broadcast_to_sketch(sketch_name, {
                    "type": "execution_error",
                    "sketch": sketch_name,
                    "error": f"Unexpected error: {str(e)}"
                })
                
                self.logger.error(f"Unexpected error handling file change for {sketch_name}: {e}")
    
    def is_watching_sketch(self, sketch_name: str) -> bool:
        """Check if a sketch is being watched.
        
        Args:
            sketch_name: Name of sketch to check
            
        Returns:
            True if sketch is being watched
        """
        return sketch_name in self.watched_sketches
    
    def get_watched_sketches(self) -> List[str]:
        """Get list of watched sketches.
        
        Returns:
            List of sketch names being watched
        """
        return list(self.watched_sketches)
    
    async def force_execute_sketch(self, sketch_name: str):
        """Force execution of a sketch without file change.
        
        Args:
            sketch_name: Name of sketch to execute
        """
        sketch_file = self._find_sketch_file(sketch_name)
        if not sketch_file:
            await self.preview_manager.broadcast_to_sketch(sketch_name, {
                "type": "execution_error",
                "sketch": sketch_name,
                "error": f"Sketch file not found: {sketch_name}"
            })
            return
        
        await self._handle_file_change(sketch_name, sketch_file)
    
    async def shutdown(self):
        """Shutdown the file watch integration."""
        self.logger.info("Shutting down FileWatchIntegration...")
        
        # Stop watching all sketches
        watched_sketches = list(self.watched_sketches)
        for sketch_name in watched_sketches:
            await self.stop_watching_sketch(sketch_name)
        
        # Stop file watcher
        self.file_watcher.stop()
        
        # Clear locks
        self.execution_locks.clear()
        
        self.logger.info("FileWatchIntegration shutdown complete")