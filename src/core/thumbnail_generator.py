"""
ThumbnailGenerator - Background task queue for progressive thumbnail generation.
"""

import asyncio
import logging
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .preview_engine import PreviewEngine


class TaskPriority(Enum):
    """Task priority levels."""
    HIGH = 1    # User sketches
    MEDIUM = 2  # Examples
    LOW = 3     # Background refresh


@dataclass
class ThumbnailTask:
    """A thumbnail generation task."""
    
    sketch_name: str
    sketch_path: Path
    priority: TaskPriority
    created_at: datetime
    attempts: int = 0
    max_attempts: int = 3
    
    def __post_init__(self):
        if not hasattr(self, 'created_at') or self.created_at is None:
            self.created_at = datetime.now()


@dataclass
class TaskResult:
    """Result of a thumbnail generation task."""
    
    success: bool
    sketch_name: str
    thumbnail_url: Optional[str] = None
    error: Optional[str] = None
    execution_time: float = 0.0
    attempts: int = 0


class ThumbnailGenerator:
    """Background thumbnail generation with priority queue and progressive updates."""
    
    def __init__(
        self, 
        preview_engine: PreviewEngine,
        max_concurrent_tasks: int = 2,
        task_timeout: float = 30.0,
        retry_delay: float = 5.0
    ):
        """Initialize thumbnail generator.
        
        Args:
            preview_engine: PreviewEngine instance for executing sketches
            max_concurrent_tasks: Maximum concurrent thumbnail generations
            task_timeout: Timeout for individual tasks in seconds
            retry_delay: Delay between retry attempts in seconds
        """
        self.preview_engine = preview_engine
        self.max_concurrent_tasks = max_concurrent_tasks
        self.task_timeout = task_timeout
        self.retry_delay = retry_delay
        
        # Task queue (priority queue implemented as sorted list)
        self.task_queue: List[ThumbnailTask] = []
        self.queue_lock = threading.RLock()
        
        # Task management
        self.active_tasks: Dict[str, asyncio.Task] = {}
        self.completed_tasks: Dict[str, TaskResult] = {}
        
        # Worker control
        self.workers: List[asyncio.Task] = []
        self.is_running = False
        self.stop_event = asyncio.Event()
        
        # Callbacks for task completion
        self.completion_callbacks: List[Callable[[TaskResult], None]] = []
        
        # Statistics
        self.stats = {
            "total_tasks": 0,
            "completed_tasks": 0,
            "failed_tasks": 0,
            "skipped_tasks": 0,  # Already have thumbnails
            "total_execution_time": 0.0,
            "started_at": None,
        }
        
        # Logger
        self.logger = logging.getLogger(__name__)
    
    def add_completion_callback(self, callback: Callable[[TaskResult], None]):
        """Add a callback for when tasks complete.
        
        Args:
            callback: Function to call with TaskResult when task completes
        """
        self.completion_callbacks.append(callback)
    
    def queue_sketch(
        self, 
        sketch_name: str, 
        sketch_path: Path, 
        priority: TaskPriority = TaskPriority.MEDIUM,
        force: bool = False
    ) -> bool:
        """Queue a sketch for thumbnail generation.
        
        Args:
            sketch_name: Name of the sketch
            sketch_path: Path to the sketch file
            priority: Task priority level
            force: Force generation even if thumbnail exists
            
        Returns:
            True if task was queued, False if already exists or has thumbnail
        """
        with self.queue_lock:
            # Check if already queued
            if any(task.sketch_name == sketch_name for task in self.task_queue):
                return False
            
            # Check if already being processed
            if sketch_name in self.active_tasks:
                return False
            
            # Check if thumbnail already exists (unless forced)
            if not force:
                current_preview = self.preview_engine.cache.get_current_preview(sketch_name)
                if (current_preview and 
                    current_preview.thumbnail_path and 
                    current_preview.thumbnail_path.exists()):
                    self.stats["skipped_tasks"] += 1
                    return False
            
            # Create and queue task
            task = ThumbnailTask(
                sketch_name=sketch_name,
                sketch_path=sketch_path,
                priority=priority,
                created_at=datetime.now()
            )
            
            self.task_queue.append(task)
            self._sort_task_queue()
            self.stats["total_tasks"] += 1
            
            self.logger.debug(f"Queued thumbnail task for {sketch_name} with priority {priority.name}")
            return True
    
    def queue_multiple_sketches(
        self, 
        sketches: List[Dict[str, Any]], 
        user_sketch_priority: TaskPriority = TaskPriority.HIGH,
        example_priority: TaskPriority = TaskPriority.MEDIUM
    ) -> int:
        """Queue multiple sketches for thumbnail generation.
        
        Args:
            sketches: List of sketch dictionaries with 'name', 'file_path', 'source_type'
            user_sketch_priority: Priority for user sketches
            example_priority: Priority for example sketches
            
        Returns:
            Number of tasks queued
        """
        queued_count = 0
        
        for sketch in sketches:
            sketch_name = sketch["name"]
            sketch_path = Path(sketch["file_path"])
            source_type = sketch.get("source_type", "sketch")
            
            # Determine priority based on source type
            priority = user_sketch_priority if source_type == "sketch" else example_priority
            
            if self.queue_sketch(sketch_name, sketch_path, priority):
                queued_count += 1
        
        self.logger.info(f"Queued {queued_count} thumbnail generation tasks")
        return queued_count
    
    def _sort_task_queue(self):
        """Sort task queue by priority and creation time."""
        self.task_queue.sort(key=lambda task: (task.priority.value, task.created_at))
    
    def get_next_task(self) -> Optional[ThumbnailTask]:
        """Get the next task from the queue.
        
        Returns:
            Next task to process, or None if queue is empty
        """
        with self.queue_lock:
            if self.task_queue:
                return self.task_queue.pop(0)
            return None
    
    def get_queue_status(self) -> Dict[str, Any]:
        """Get current queue status.
        
        Returns:
            Dictionary with queue statistics
        """
        with self.queue_lock:
            queue_by_priority = {}
            for priority in TaskPriority:
                count = len([t for t in self.task_queue if t.priority == priority])
                queue_by_priority[priority.name.lower()] = count
            
            return {
                "total_queued": len(self.task_queue),
                "active_tasks": len(self.active_tasks),
                "by_priority": queue_by_priority,
                "stats": self.stats.copy(),
                "is_running": self.is_running,
            }
    
    async def start(self) -> None:
        """Start the thumbnail generation workers."""
        if self.is_running:
            return
        
        self.is_running = True
        self.stop_event.clear()
        self.stats["started_at"] = datetime.now()
        
        # Start worker tasks
        for i in range(self.max_concurrent_tasks):
            worker = asyncio.create_task(self._worker(f"worker-{i}"))
            self.workers.append(worker)
        
        self.logger.info(f"Started {self.max_concurrent_tasks} thumbnail generation workers")
    
    async def stop(self) -> None:
        """Stop the thumbnail generation workers."""
        if not self.is_running:
            return
        
        self.is_running = False
        self.stop_event.set()
        
        # Cancel all active tasks
        for task in self.active_tasks.values():
            task.cancel()
        
        # Wait for workers to finish
        if self.workers:
            await asyncio.gather(*self.workers, return_exceptions=True)
        
        self.workers.clear()
        self.active_tasks.clear()
        
        self.logger.info("Stopped thumbnail generation workers")
    
    async def _worker(self, worker_name: str) -> None:
        """Worker coroutine for processing thumbnail generation tasks.
        
        Args:
            worker_name: Name of the worker for logging
        """
        self.logger.debug(f"Thumbnail worker {worker_name} started")
        
        while self.is_running and not self.stop_event.is_set():
            try:
                # Get next task
                task = self.get_next_task()
                if not task:
                    # No tasks available, wait a bit
                    await asyncio.sleep(0.5)
                    continue
                
                # Process the task
                await self._process_task(task, worker_name)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Worker {worker_name} error: {e}")
                await asyncio.sleep(1.0)  # Prevent tight error loops
        
        self.logger.debug(f"Thumbnail worker {worker_name} stopped")
    
    async def _process_task(self, task: ThumbnailTask, worker_name: str) -> None:
        """Process a single thumbnail generation task.
        
        Args:
            task: The task to process
            worker_name: Name of the worker processing the task
        """
        start_time = time.time()
        task.attempts += 1
        
        self.logger.debug(f"Worker {worker_name} processing {task.sketch_name} (attempt {task.attempts})")
        
        try:
            # Check if sketch file exists
            if not task.sketch_path.exists():
                raise FileNotFoundError(f"Sketch file not found: {task.sketch_path}")
            
            # Check if we already have a thumbnail (in case it was generated while queued)
            current_preview = self.preview_engine.cache.get_current_preview(task.sketch_name)
            if (current_preview and 
                current_preview.thumbnail_path and 
                current_preview.thumbnail_path.exists()):
                
                # Already have thumbnail, mark as completed
                execution_time = time.time() - start_time
                result = TaskResult(
                    success=True,
                    sketch_name=task.sketch_name,
                    thumbnail_url=f"/thumbnail/{current_preview.thumbnail_path.name}",
                    execution_time=execution_time,
                    attempts=task.attempts
                )
                self._handle_task_completion(result)
                return
            
            # Execute the sketch to generate preview and thumbnail
            preview_result = self.preview_engine.execute_sketch(
                task.sketch_path, 
                task.sketch_name
            )
            
            execution_time = time.time() - start_time
            
            if preview_result.success:
                # Success - preview and thumbnail generated
                result = TaskResult(
                    success=True,
                    sketch_name=task.sketch_name,
                    thumbnail_url=preview_result.thumbnail_url,
                    execution_time=execution_time,
                    attempts=task.attempts
                )
                self._handle_task_completion(result)
            else:
                # Execution failed
                if task.attempts < task.max_attempts:
                    # Retry later
                    await asyncio.sleep(self.retry_delay)
                    with self.queue_lock:
                        self.task_queue.append(task)
                        self._sort_task_queue()
                else:
                    # Max attempts reached, mark as failed
                    result = TaskResult(
                        success=False,
                        sketch_name=task.sketch_name,
                        error=preview_result.error,
                        execution_time=execution_time,
                        attempts=task.attempts
                    )
                    self._handle_task_completion(result)
        
        except Exception as e:
            execution_time = time.time() - start_time
            
            if task.attempts < task.max_attempts:
                # Retry later
                self.logger.warning(f"Task {task.sketch_name} failed (attempt {task.attempts}), will retry: {e}")
                await asyncio.sleep(self.retry_delay)
                with self.queue_lock:
                    self.task_queue.append(task)
                    self._sort_task_queue()
            else:
                # Max attempts reached, mark as failed
                self.logger.error(f"Task {task.sketch_name} failed permanently after {task.attempts} attempts: {e}")
                result = TaskResult(
                    success=False,
                    sketch_name=task.sketch_name,
                    error=str(e),
                    execution_time=execution_time,
                    attempts=task.attempts
                )
                self._handle_task_completion(result)
    
    def _handle_task_completion(self, result: TaskResult) -> None:
        """Handle task completion.
        
        Args:
            result: The task result
        """
        # Update statistics
        if result.success:
            self.stats["completed_tasks"] += 1
        else:
            self.stats["failed_tasks"] += 1
        
        self.stats["total_execution_time"] += result.execution_time
        
        # Store result
        self.completed_tasks[result.sketch_name] = result
        
        # Remove from active tasks if present
        if result.sketch_name in self.active_tasks:
            del self.active_tasks[result.sketch_name]
        
        # Call completion callbacks
        for callback in self.completion_callbacks:
            try:
                callback(result)
            except Exception as e:
                self.logger.error(f"Completion callback error: {e}")
        
        self.logger.debug(f"Task {result.sketch_name} completed: success={result.success}")
    
    def get_task_result(self, sketch_name: str) -> Optional[TaskResult]:
        """Get the result of a completed task.
        
        Args:
            sketch_name: Name of the sketch
            
        Returns:
            TaskResult if task completed, None otherwise
        """
        return self.completed_tasks.get(sketch_name)
    
    def clear_completed_tasks(self) -> None:
        """Clear completed task results."""
        self.completed_tasks.clear()