# MichelangeloCC Documentation

## Contents

- [CLI Reference](CLI.md) - Complete command-line interface documentation
- [Decision Log](DECISIONS.md) - Technical decisions and rationale
- [SKILL Guide](../README.md#using-with-claude-code) - Using MichelangeloCC with Claude Code

## Installation

```bash
pipx install michelangelocc
```

Or with uv: `uv tool install michelangelocc`

## Quick Links

### Commands

| Command | Documentation |
|---------|---------------|
| `mcc session` | [Session Command](CLI.md#session-command) |
| `mcc preview` | [Preview Commands](CLI.md#preview-commands) |
| `mcc export` | [Export Commands](CLI.md#export-commands) |
| `mcc validate` | [Validate Commands](CLI.md#validate-commands) |
| `mcc repair` | [Repair Commands](CLI.md#repair-commands) |
| `mcc info` | [Info Command](CLI.md#info-command) |
| `mcc new` | [New Command](CLI.md#new-command) |
| `mcc help` | [Help Command](CLI.md#help-command) |

## Getting Started

### Recommended: Interactive Session

```bash
# Start an interactive session with Claude Code
mcc session "Create a phone stand with adjustable angle"

# Claude Code + live preview + automatic hot-reload
# Browser opens automatically with 3D viewer
# Edit model.py and preview updates instantly
```

### Manual Workflow

```bash
# 1. Create project
mcc new my_model --template mechanical

# 2. Preview (with hot-reload)
mcc preview model my_model/my_model.py

# 3. Export
mcc export stl my_model/my_model.py -o output.stl
```

## Getting Help

```bash
# General help
mcc --help
mcc help

# Command-specific help
mcc export --help
mcc export stl --help
mcc help export
mcc session --help
```

## Architecture Overview

```
User Request → mcc session → tmux + Claude Code + Preview Server
                                    ↓
                              model.py (edit)
                                    ↓
                              File Watcher (watchdog)
                                    ↓
                              WebSocket notification
                                    ↓
                              Browser reloads model
```

### Key Components

| Component | File | Purpose |
|-----------|------|---------|
| CLI | `cli.py` | Typer-based command interface |
| Session Manager | `session.py` | tmux session lifecycle, Claude CLI integration |
| Preview Server | `server/app.py` | FastAPI + Three.js viewer |
| File Watcher | `server/watcher.py` | Detects file changes, triggers reload |
| Modeler | `core/modeler.py` | build123d wrapper for model loading |
| Validator | `core/validator.py` | Mesh validation for printability |
| Exporter | `core/exporter.py` | STL export with quality settings |

## Requirements

- Python 3.10+
- tmux (for `mcc session`)
- Claude Code CLI (for `mcc session`)
- Modern browser (for preview)
