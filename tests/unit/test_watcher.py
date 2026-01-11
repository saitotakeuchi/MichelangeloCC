"""Tests for file watcher module."""

import pytest
from pathlib import Path
import tempfile
import time
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch

from watchdog.events import FileModifiedEvent, FileMovedEvent, FileCreatedEvent

from michelangelocc.server.watcher import (
    ModelFileHandler,
    FileWatcher,
    start_watcher,
    start_watcher_with_loop,
    stop_watcher,
)


class TestModelFileHandler:
    """Tests for ModelFileHandler class."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def watched_file(self, temp_dir):
        """Create a file to watch."""
        path = temp_dir / "model.py"
        path.write_text("# initial")
        return path

    @pytest.fixture
    def mock_callback(self):
        """Create a mock async callback."""
        return AsyncMock()

    @pytest.fixture
    def handler(self, mock_callback, watched_file):
        """Create a ModelFileHandler instance."""
        return ModelFileHandler(
            callback=mock_callback,
            watched_path=watched_file,
            debounce_seconds=0.1,
        )

    def test_init(self, handler, watched_file, mock_callback):
        """Handler should initialize correctly."""
        assert handler.callback is mock_callback
        assert handler.watched_path == watched_file.resolve()
        assert handler.debounce_seconds == 0.1

    def test_on_modified_triggers_callback(self, handler, watched_file):
        """on_modified should trigger callback for watched file."""
        # Set up event loop for async callback
        loop = asyncio.new_event_loop()
        handler.set_loop(loop)

        event = FileModifiedEvent(str(watched_file))

        handler.on_modified(event)

        # Callback should be scheduled
        # (actual execution happens in event loop)
        assert handler._last_trigger > 0

    def test_on_modified_ignores_other_files(self, handler, temp_dir):
        """on_modified should ignore events for other files."""
        other_file = temp_dir / "other.py"
        other_file.write_text("# other")

        event = FileModifiedEvent(str(other_file))

        initial_trigger = handler._last_trigger
        handler.on_modified(event)

        # Should not update last_trigger
        assert handler._last_trigger == initial_trigger

    def test_on_modified_ignores_directories(self, handler, temp_dir):
        """on_modified should ignore directory events."""
        event = FileModifiedEvent(str(temp_dir))
        event.is_directory = True

        initial_trigger = handler._last_trigger
        handler.on_modified(event)

        assert handler._last_trigger == initial_trigger

    def test_on_moved_triggers_callback(self, handler, watched_file, temp_dir):
        """on_moved should trigger callback when file is renamed to watched path."""
        temp_file = temp_dir / "temp.py"
        temp_file.write_text("# temp")

        loop = asyncio.new_event_loop()
        handler.set_loop(loop)

        event = FileMovedEvent(str(temp_file), str(watched_file))

        handler.on_moved(event)

        assert handler._last_trigger > 0

    def test_on_moved_ignores_other_destinations(self, handler, temp_dir):
        """on_moved should ignore moves to other files."""
        temp_file = temp_dir / "temp.py"
        other_file = temp_dir / "other.py"

        event = FileMovedEvent(str(temp_file), str(other_file))

        initial_trigger = handler._last_trigger
        handler.on_moved(event)

        assert handler._last_trigger == initial_trigger

    def test_on_created_triggers_callback(self, handler, watched_file):
        """on_created should trigger callback for watched file."""
        loop = asyncio.new_event_loop()
        handler.set_loop(loop)

        event = FileCreatedEvent(str(watched_file))

        handler.on_created(event)

        assert handler._last_trigger > 0

    def test_on_created_ignores_other_files(self, handler, temp_dir):
        """on_created should ignore events for other files."""
        other_file = temp_dir / "other.py"

        event = FileCreatedEvent(str(other_file))

        initial_trigger = handler._last_trigger
        handler.on_created(event)

        assert handler._last_trigger == initial_trigger

    def test_debounce_prevents_rapid_calls(self, handler, watched_file):
        """Debounce should prevent rapid callback triggers."""
        loop = asyncio.new_event_loop()
        handler.set_loop(loop)

        event = FileModifiedEvent(str(watched_file))

        # First call should trigger
        handler.on_modified(event)
        first_trigger = handler._last_trigger

        # Immediate second call should be debounced
        handler.on_modified(event)
        second_trigger = handler._last_trigger

        # Should be same (debounced)
        assert first_trigger == second_trigger

    def test_debounce_allows_after_delay(self, handler, watched_file):
        """Debounce should allow callback after delay."""
        handler.debounce_seconds = 0.05  # Short debounce for test

        loop = asyncio.new_event_loop()
        handler.set_loop(loop)

        event = FileModifiedEvent(str(watched_file))

        # First call
        handler.on_modified(event)
        first_trigger = handler._last_trigger

        # Wait for debounce
        time.sleep(0.1)

        # Second call should trigger
        handler.on_modified(event)
        second_trigger = handler._last_trigger

        # Should be different (not debounced)
        assert second_trigger > first_trigger

    def test_set_loop(self, handler):
        """set_loop should set the event loop."""
        loop = asyncio.new_event_loop()
        handler.set_loop(loop)

        assert handler._loop is loop


class TestFileWatcher:
    """Tests for FileWatcher class."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def watcher(self):
        """Create a FileWatcher instance."""
        w = FileWatcher()
        yield w
        # Cleanup
        if w._started:
            w.stop()

    def test_init(self, watcher):
        """Watcher should initialize correctly."""
        assert watcher.observer is not None
        assert watcher._handlers == []
        assert watcher._started is False

    def test_watch_adds_handler(self, watcher, temp_dir):
        """watch() should add a handler."""
        path = temp_dir / "model.py"
        path.write_text("# test")
        callback = AsyncMock()

        watcher.watch(path, callback)

        assert len(watcher._handlers) == 1
        assert watcher._handlers[0].watched_path == path.resolve()

    def test_start_and_stop(self, watcher, temp_dir):
        """start() and stop() should manage observer lifecycle."""
        path = temp_dir / "model.py"
        path.write_text("# test")
        callback = AsyncMock()

        watcher.watch(path, callback)

        # Start
        watcher.start()
        assert watcher._started is True

        # Stop
        watcher.stop()
        assert watcher._started is False

    def test_start_idempotent(self, watcher, temp_dir):
        """Multiple start() calls should be safe."""
        path = temp_dir / "model.py"
        path.write_text("# test")
        callback = AsyncMock()

        watcher.watch(path, callback)
        watcher.start()
        watcher.start()  # Should not raise

        assert watcher._started is True

    def test_stop_idempotent(self, watcher, temp_dir):
        """Multiple stop() calls should be safe."""
        path = temp_dir / "model.py"
        path.write_text("# test")
        callback = AsyncMock()

        watcher.watch(path, callback)
        watcher.start()
        watcher.stop()
        watcher.stop()  # Should not raise

        assert watcher._started is False


class TestGlobalWatcherFunctions:
    """Tests for global watcher convenience functions."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_start_watcher_creates_global(self, temp_dir):
        """start_watcher should create global watcher."""
        import michelangelocc.server.watcher as watcher_module

        path = temp_dir / "model.py"
        path.write_text("# test")
        callback = AsyncMock()

        try:
            start_watcher(path, callback)

            assert watcher_module._watcher is not None
            assert watcher_module._watcher._started is True
        finally:
            stop_watcher()

    def test_start_watcher_with_loop(self, temp_dir):
        """start_watcher_with_loop should set event loop on handlers."""
        import michelangelocc.server.watcher as watcher_module

        path = temp_dir / "model.py"
        path.write_text("# test")
        callback = AsyncMock()
        loop = asyncio.new_event_loop()

        try:
            start_watcher_with_loop(path, callback, loop)

            assert watcher_module._watcher is not None
            # Handler should have loop set
            handler = watcher_module._watcher._handlers[0]
            assert handler._loop is loop
        finally:
            stop_watcher()

    def test_stop_watcher_cleans_up(self, temp_dir):
        """stop_watcher should clean up global watcher."""
        import michelangelocc.server.watcher as watcher_module

        path = temp_dir / "model.py"
        path.write_text("# test")
        callback = AsyncMock()

        start_watcher(path, callback)
        assert watcher_module._watcher is not None

        stop_watcher()
        assert watcher_module._watcher is None

    def test_stop_watcher_safe_when_none(self):
        """stop_watcher should be safe when no watcher exists."""
        import michelangelocc.server.watcher as watcher_module

        watcher_module._watcher = None

        # Should not raise
        stop_watcher()
