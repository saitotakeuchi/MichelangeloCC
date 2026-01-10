"""
File watcher module for hot-reload functionality.

Uses watchdog library to monitor Python script files for changes
and trigger model reload in the viewer.
"""

from pathlib import Path
from typing import Callable, Awaitable, Optional
import asyncio
import threading
import time

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent, FileMovedEvent, FileCreatedEvent


class ModelFileHandler(FileSystemEventHandler):
    """Handle file system events for model files."""

    def __init__(
        self,
        callback: Callable[[], Awaitable[None]],
        watched_path: Path,
        debounce_seconds: float = 0.5,
    ):
        """
        Initialize the handler.

        Args:
            callback: Async function to call when file changes
            watched_path: Path to the file being watched
            debounce_seconds: Minimum time between callbacks
        """
        self.callback = callback
        self.watched_path = watched_path.resolve()
        self.debounce_seconds = debounce_seconds
        self._last_trigger = 0.0
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def set_loop(self, loop: asyncio.AbstractEventLoop):
        """Set the event loop to use for async callbacks."""
        self._loop = loop

    def on_modified(self, event):
        """Handle file modification events."""
        if event.is_directory:
            return

        # Check if this is our watched file
        modified_path = Path(event.src_path).resolve()
        if modified_path != self.watched_path:
            return

        self._handle_file_change()

    def on_moved(self, event):
        """Handle file move events (for atomic writes via temp file + rename)."""
        if event.is_directory:
            return

        # Check if the destination is our watched file (temp file renamed to target)
        dest_path = Path(event.dest_path).resolve()
        if dest_path != self.watched_path:
            return

        self._handle_file_change()

    def on_created(self, event):
        """Handle file creation events (in case file is recreated)."""
        if event.is_directory:
            return

        created_path = Path(event.src_path).resolve()
        if created_path != self.watched_path:
            return

        self._handle_file_change()

    def _handle_file_change(self):
        """Common handler for file changes (modified, moved, created)."""
        # Debounce rapid changes
        current_time = time.time()
        if current_time - self._last_trigger < self.debounce_seconds:
            return

        self._last_trigger = current_time
        self._trigger_callback()

    def _trigger_callback(self):
        """Trigger the async callback."""
        if self._loop is None:
            # Try to get the running loop
            try:
                self._loop = asyncio.get_running_loop()
            except RuntimeError:
                # No running loop, try to run in new loop
                asyncio.run(self.callback())
                return

        # Schedule callback in the event loop
        asyncio.run_coroutine_threadsafe(self.callback(), self._loop)


class FileWatcher:
    """
    Watch files for changes and trigger callbacks.

    Uses watchdog for cross-platform file system monitoring.
    """

    def __init__(self):
        self.observer = Observer()
        self._handlers: list[ModelFileHandler] = []
        self._started = False

    def watch(
        self,
        path: Path,
        callback: Callable[[], Awaitable[None]],
        debounce_seconds: float = 0.5,
    ):
        """
        Start watching a file for changes.

        Args:
            path: Path to watch
            callback: Async function to call on changes
            debounce_seconds: Minimum time between callbacks
        """
        path = Path(path).resolve()
        handler = ModelFileHandler(callback, path, debounce_seconds)
        self._handlers.append(handler)

        # Watch the parent directory
        self.observer.schedule(handler, str(path.parent), recursive=False)

    def start(self):
        """Start the file watcher."""
        if not self._started:
            self.observer.start()
            self._started = True

    def stop(self):
        """Stop the file watcher."""
        if self._started:
            self.observer.stop()
            self.observer.join()
            self._started = False


# Global watcher instance
_watcher: Optional[FileWatcher] = None
_watcher_thread: Optional[threading.Thread] = None


def start_watcher(
    path: Path,
    callback: Callable[[], Awaitable[None]],
):
    """
    Start a file watcher for the given path.

    This is a convenience function that manages a global watcher instance.

    Args:
        path: Path to watch
        callback: Async function to call on changes
    """
    global _watcher

    _watcher = FileWatcher()
    _watcher.watch(path, callback)
    _watcher.start()

    print(f"Watching for changes: {path}")


def start_watcher_with_loop(
    path: Path,
    callback: Callable[[], Awaitable[None]],
    loop: asyncio.AbstractEventLoop,
):
    """
    Start a file watcher for the given path with a specific event loop.

    This ensures the async callback is scheduled on the correct event loop,
    which is necessary when the watcher runs in a different thread (e.g.,
    watchdog's observer thread) than uvicorn's main event loop.

    Args:
        path: Path to watch
        callback: Async function to call on changes
        loop: The event loop to schedule callbacks on
    """
    global _watcher

    _watcher = FileWatcher()
    _watcher.watch(path, callback)

    # Set the event loop on all handlers before starting
    for handler in _watcher._handlers:
        handler.set_loop(loop)

    _watcher.start()

    print(f"Watching for changes: {path}")


def stop_watcher():
    """Stop the global file watcher."""
    global _watcher

    if _watcher:
        _watcher.stop()
        _watcher = None
