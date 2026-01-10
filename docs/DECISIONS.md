# Technical Decision Log

This document records key technical decisions made during development of MichelangeloCC.

## Table of Contents

- [Session Management](#session-management)
- [File Watching](#file-watching)
- [Installation](#installation)
- [Preview Server](#preview-server)

---

## Session Management

### Decision: Use tmux for Claude Code Sessions

**Date:** 2026-01-10

**Context:**
The `mcc session` command needs to run Claude Code CLI interactively while keeping a preview server running in the background. The session should persist if the terminal disconnects.

**Options Considered:**
1. **pty.spawn()** - Direct PTY for Claude CLI
2. **subprocess** - Run Claude as subprocess
3. **tmux** - Terminal multiplexer

**Decision:** Use tmux

**Rationale:**
- **Session persistence**: tmux sessions survive terminal disconnection
- **Detach/reattach**: Users can detach (`Ctrl+B, D`) and reattach later
- **Clean process management**: tmux handles process lifecycle cleanly
- **Widely available**: Standard tool on macOS/Linux

**Alternatives Rejected:**
- `pty.spawn()`: Doesn't persist if terminal closes; blocking
- `subprocess`: No interactive terminal support

**Implementation:**
```python
# Create detached tmux session
tmux new-session -d -s "mcc-{timestamp}" -c "{session_dir}" "{claude_cmd}"

# Attach to session (blocks until detach/exit)
tmux attach-session -t "mcc-{timestamp}"
```

---

### Decision: Pass Prompt as Positional Argument to Claude CLI

**Date:** 2026-01-10

**Context:**
Claude Code CLI has different modes. Using `-p` flag prints output and exits (non-interactive).

**Decision:** Use positional argument for prompt, not `-p` flag

**Rationale:**
- `-p/--print` is non-interactive (print and exit)
- Positional argument starts interactive session with initial prompt
- User needs to iterate on the model interactively

**Implementation:**
```python
cmd = ["claude", "--append-system-prompt", system_prompt, prompt]
# NOT: cmd = ["claude", "-p", prompt]  # This would be non-interactive
```

---

## File Watching

### Decision: Handle Atomic Writes (on_moved events)

**Date:** 2026-01-10

**Context:**
The Claude Code Edit tool (and many editors) use atomic writes: create temp file, write content, rename to target. The original watcher only handled `on_modified` events.

**Problem:**
Atomic writes don't trigger `on_modified` for the target file. Instead:
1. `on_created` fires for temp file
2. `on_modified` fires for temp file
3. `on_moved` fires when temp → target

**Decision:** Handle `on_modified`, `on_moved`, and `on_created` events

**Implementation:**
```python
def on_moved(self, event):
    """Handle file move events (for atomic writes via temp file + rename)."""
    if event.is_directory:
        return
    dest_path = Path(event.dest_path).resolve()
    if dest_path != self.watched_path:
        return
    self._handle_file_change()
```

---

### Decision: Use asyncio.run_coroutine_threadsafe for Event Loop Communication

**Date:** 2026-01-10

**Context:**
The watchdog observer runs in its own thread. The async callback (`notify_model_change`) needs to run in uvicorn's event loop.

**Problem:**
- watchdog callback runs in observer thread
- WebSocket notifications need to run in main event loop
- `asyncio.get_running_loop()` fails from wrong thread

**Decision:** Pass event loop to watcher at startup, use `run_coroutine_threadsafe`

**Implementation:**
```python
# At startup (in uvicorn's event loop)
loop = asyncio.get_running_loop()
start_watcher_with_loop(path, callback, loop)

# In watcher callback (different thread)
asyncio.run_coroutine_threadsafe(self.callback(), self._loop)
```

---

## Installation

### Decision: Provide Multiple Installation Methods

**Date:** 2026-01-10

**Context:**
Modern macOS uses PEP 668 ("externally managed environment") which blocks direct `pip install` to system Python. Users have varying familiarity with Python tooling.

**Decision:** Support three installation methods:

1. **install.sh** (recommended) - One-liner for beginners
2. **pipx** - For users who already have pipx
3. **uv** - For users who prefer uv

**Rationale:**
- install.sh handles edge cases (finds Python 3.10+, installs pipx, etc.)
- pipx/uv are standard tools for isolated CLI installations
- Avoids "externally managed environment" errors

**Implementation:**
```bash
# Recommended
curl -sSL https://raw.githubusercontent.com/.../install.sh | bash

# Alternative
pipx install git+https://github.com/.../MichelangeloCC.git
uv tool install git+https://github.com/.../MichelangeloCC.git
```

---

## Preview Server

### Decision: Use FastAPI Startup Event for Watcher Initialization

**Date:** 2026-01-10

**Context:**
The file watcher needs access to uvicorn's event loop to schedule async callbacks.

**Problem:**
- Event loop doesn't exist until uvicorn starts
- Watcher must be initialized after server startup
- Global state needs to be set before `uvicorn.run()`

**Decision:** Use FastAPI's `@app.on_event("startup")` lifecycle hook

**Implementation:**
```python
_watch_enabled: bool = False

@app.on_event("startup")
async def startup_event():
    if _watch_enabled and _current_script_path:
        loop = asyncio.get_running_loop()
        start_watcher_with_loop(_current_script_path, notify_model_change, loop)
```

---

### Decision: Embedded Three.js Viewer (No External Dependencies)

**Date:** 2026-01-10

**Context:**
The preview server needs to serve a 3D viewer. Options include external files or embedded HTML/JS.

**Decision:** Embed viewer HTML/JS directly in `app.py`

**Rationale:**
- No external file dependencies to manage
- Viewer served from any working directory
- Single source of truth for viewer code
- Uses Three.js from CDN (import maps)

**Trade-offs:**
- Larger Python file (~600 lines)
- Editing HTML requires Python file changes

---

## Future Considerations

### Potential: WebSocket Heartbeat

Currently WebSocket connections reconnect on close. A heartbeat mechanism could detect stale connections faster.

### Potential: Multi-file Watching

Currently watches single `model.py`. Could extend to watch imported modules for complex projects.

### Potential: Session Resume

Allow resuming a previous session with `mcc session --resume session_20260110_*`.
