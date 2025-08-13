"""
FileWatcher for monitoring sketch file changes in live preview system.
"""
import os
import time
import threading
from pathlib import Path
from typing import Dict, List, Callable, Optional
from collections import defaultdict
import logging

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False


class FileWatcher:
    """Monitors file changes with debouncing for live preview system."""
    
    def __init__(self, debounce_delay: float = 0.3):
        """Initialize file watcher.
        
        Args:
            debounce_delay: Delay in seconds to debounce rapid file changes
        """
        self.debounce_delay = debounce_delay
        self.watched_files: Dict[Path, List[Callable]] = defaultdict(list)
        self.pending_callbacks: Dict[Path, threading.Timer] = {}
        self.observer = None
        self.event_handler = None
        self._running = False
        self._lock = threading.Lock()
        self._watched_dirs = set()  # Track watched directories
        
        # Set up logging
        self.logger = logging.getLogger(__name__)
        
        if WATCHDOG_AVAILABLE:
            self._setup_watchdog()
        else:
            self.logger.warning("watchdog library not available, using fallback polling")
            self._setup_polling()
    
    def _setup_watchdog(self):
        """Set up watchdog-based file monitoring."""
        self.event_handler = _FileChangeHandler(self)
        self.observer = Observer()
        self._running = True
    
    def _setup_polling(self):
        """Set up polling-based file monitoring as fallback."""
        self._running = True
        self._file_mtimes: Dict[Path, float] = {}
        self._polling_thread = threading.Thread(target=self._polling_loop, daemon=True)
        self._polling_thread.start()
    
    def _polling_loop(self):
        """Polling loop for file monitoring when watchdog unavailable."""
        while self._running:
            try:
                with self._lock:
                    for file_path in list(self.watched_files.keys()):
                        if file_path.exists():
                            current_mtime = file_path.stat().st_mtime
                            last_mtime = self._file_mtimes.get(file_path, 0)
                            
                            if current_mtime > last_mtime:
                                self._file_mtimes[file_path] = current_mtime
                                if last_mtime > 0:  # Skip first check
                                    self._trigger_callbacks(file_path)
                        else:
                            # File was deleted
                            if file_path in self._file_mtimes:
                                del self._file_mtimes[file_path]
                
                time.sleep(0.1)  # Poll every 100ms
                
            except Exception as e:
                self.logger.error(f"Error in polling loop: {e}")
                time.sleep(0.5)
    
    def watch_file(self, file_path: Path, callback: Callable[[Path], None]):
        """Start watching a file for changes.
        
        Args:
            file_path: Path to the file to watch
            callback: Function to call when file changes, receives file_path
        """
        file_path = Path(file_path).resolve()
        
        with self._lock:
            # Add callback to watched files
            if callback not in self.watched_files[file_path]:
                self.watched_files[file_path].append(callback)
            
            if WATCHDOG_AVAILABLE and self.observer:
                # Start watching the directory containing the file
                watch_dir = file_path.parent
                if watch_dir not in self._watched_dirs:
                    self.observer.schedule(self.event_handler, str(watch_dir), recursive=False)
                    self._watched_dirs.add(watch_dir)
                    if not self.observer.is_alive():
                        self.observer.start()
            elif not WATCHDOG_AVAILABLE:
                # Initialize polling data for fallback mode
                if file_path.exists():
                    self._file_mtimes[file_path] = file_path.stat().st_mtime
    
    def unwatch_file(self, file_path: Path):
        """Stop watching a file.
        
        Args:
            file_path: Path to the file to stop watching
        """
        file_path = Path(file_path).resolve()
        
        with self._lock:
            if file_path in self.watched_files:
                del self.watched_files[file_path]
            
            if file_path in self.pending_callbacks:
                self.pending_callbacks[file_path].cancel()
                del self.pending_callbacks[file_path]
            
            if not WATCHDOG_AVAILABLE:
                if file_path in self._file_mtimes:
                    del self._file_mtimes[file_path]
    
    def _trigger_callbacks(self, file_path: Path):
        """Trigger callbacks for a file change with debouncing.
        
        Args:
            file_path: Path to the file that changed
        """
        with self._lock:
            # Cancel any pending callback for this file
            if file_path in self.pending_callbacks:
                self.pending_callbacks[file_path].cancel()
            
            # Schedule new callback after debounce delay
            timer = threading.Timer(
                self.debounce_delay,
                self._execute_callbacks,
                args=(file_path,)
            )
            self.pending_callbacks[file_path] = timer
            timer.start()
    
    def _execute_callbacks(self, file_path: Path):
        """Execute all callbacks for a file change.
        
        Args:
            file_path: Path to the file that changed
        """
        with self._lock:
            # Remove from pending callbacks
            if file_path in self.pending_callbacks:
                del self.pending_callbacks[file_path]
            
            # Execute all callbacks for this file
            callbacks = self.watched_files.get(file_path, [])
            
        # Execute callbacks outside of lock to prevent deadlocks
        for callback in callbacks:
            try:
                callback(file_path)
            except Exception as e:
                self.logger.error(f"Error executing callback for {file_path}: {e}")
    
    def stop(self):
        """Stop the file watcher and clean up resources."""
        self._running = False
        
        with self._lock:
            # Cancel all pending callbacks
            for timer in self.pending_callbacks.values():
                timer.cancel()
            self.pending_callbacks.clear()
            
            # Stop watchdog observer
            if WATCHDOG_AVAILABLE and self.observer:
                if self.observer.is_alive():
                    self.observer.stop()
                    self.observer.join(timeout=1.0)
            
            # Clear watched files
            self.watched_files.clear()
            self._watched_dirs.clear()
            
            if not WATCHDOG_AVAILABLE:
                self._file_mtimes.clear()


class _FileChangeHandler(FileSystemEventHandler):
    """Handler for watchdog file system events."""
    
    def __init__(self, file_watcher: FileWatcher):
        """Initialize handler.
        
        Args:
            file_watcher: FileWatcher instance to notify of changes
        """
        super().__init__()
        self.file_watcher = file_watcher
    
    def on_modified(self, event):
        """Handle file modification events."""
        if event.is_directory:
            return
        
        file_path = Path(event.src_path)
        
        # Only trigger for watched files
        if file_path in self.file_watcher.watched_files:
            self.file_watcher._trigger_callbacks(file_path)
    
    def on_created(self, event):
        """Handle file creation events."""
        if event.is_directory:
            return
        
        file_path = Path(event.src_path)
        
        # Only trigger for watched files (handles file recreation)
        if file_path in self.file_watcher.watched_files:
            self.file_watcher._trigger_callbacks(file_path)
    
    def on_moved(self, event):
        """Handle file move/rename events."""
        if event.is_directory:
            return
        
        # Handle both source and destination paths
        src_path = Path(event.src_path)
        dest_path = Path(event.dest_path)
        
        if src_path in self.file_watcher.watched_files:
            self.file_watcher._trigger_callbacks(src_path)
        
        if dest_path in self.file_watcher.watched_files:
            self.file_watcher._trigger_callbacks(dest_path)