# MichelangeloCC

**Claude Code-powered 3D model generator for STL files**

MichelangeloCC is a tool that enables Claude Code to generate 3D printable models from natural language descriptions. It combines the power of [build123d](https://github.com/gumyr/build123d) for CAD modeling with a browser-based visualization and seamless STL export.

## Features

- **Interactive Sessions**: Start a session with `mcc session` - Claude Code + live preview + hot-reload
- **Natural Language to 3D**: Describe what you want, Claude generates the model
- **Browser-based Preview**: Interactive 3D viewer with automatic hot-reload
- **Validation Pipeline**: Checks models for 3D printability before export
- **Auto-repair**: Automatically fixes common mesh issues
- **Quality Control**: Configurable export quality settings
- **SKILL Integration**: Claude Code skill for guided model generation

## Installation

### Quick Install (Recommended)

```bash
pipx install michelangelocc
```

Or with [uv](https://github.com/astral-sh/uv):

```bash
uv tool install michelangelocc
```

> **Note:** If you don't have pipx, install it first: `brew install pipx && pipx ensurepath` (macOS) or `pip install --user pipx && pipx ensurepath` (Linux)

### For Development

```bash
git clone https://github.com/saitotakeuchi/MichelangeloCC.git
cd MichelangeloCC
make install-dev
source .venv/bin/activate
```

### Upgrade

```bash
pipx upgrade michelangelocc
# or
uv tool upgrade michelangelocc
```

### Requirements

- Python 3.10+
- macOS or Linux (Windows via WSL)
- tmux (for interactive sessions)
- Claude Code CLI (for interactive sessions)
- A modern browser for visualization

```bash
# Install tmux (if not already installed)
brew install tmux        # macOS
sudo apt install tmux    # Ubuntu/Debian

# Claude Code CLI
npm install -g @anthropic-ai/claude-code
```

### Verify Installation

```bash
# Check mcc is installed
mcc version

# Check all requirements
mcc --help
tmux -V
claude --version
```

### Troubleshooting

<details>
<summary>macOS: "externally-managed-environment" error</summary>

Modern Homebrew Python is PEP 668 compliant and blocks direct pip installs.
Use pipx or uv instead - they create isolated environments automatically.

</details>

<details>
<summary>"command not found: mcc" after installation</summary>

Your PATH may need updating. Restart your terminal or run:

```bash
source ~/.zshrc  # or ~/.bashrc
```

</details>

<details>
<summary>"tmux is required but not installed" error</summary>

Install tmux for your platform:
```bash
brew install tmux        # macOS
sudo apt install tmux    # Ubuntu/Debian
sudo dnf install tmux    # Fedora
```

</details>

<details>
<summary>"'claude' command not found" error</summary>

Install Claude Code CLI:
```bash
npm install -g @anthropic-ai/claude-code
```

If npm is not installed, install Node.js first from https://nodejs.org/

</details>

<details>
<summary>Uninstalling</summary>

```bash
pipx uninstall michelangelocc
# or
uv tool uninstall michelangelocc
```

</details>

## Quick Start

### Interactive Session (Recommended)

The fastest way to create 3D models with Claude Code:

```bash
mcc session "Create a phone stand with cable routing"
```

This will:
1. Create a session folder with a template `model.py`
2. Start a preview server with hot-reload
3. Open your browser with a live 3D preview
4. Launch Claude Code in a tmux session with full context

Claude will iterate on the design based on your feedback. The browser preview updates automatically when the model changes. When you're done:

```bash
mcc export stl model.py -o output/model.stl --quality high
```

**tmux Tips:**
- Detach: `Ctrl+B`, then `D`
- Reattach: `tmux attach -t mcc-*`
- Exit: Type `/exit` in Claude or `Ctrl+C`

### Manual Workflow

For more control, create and preview models manually:

```bash
# 1. Create a new project
mcc new my_gear --template mechanical
cd my_gear

# 2. Preview your model (hot-reload enabled)
mcc preview model my_gear.py

# 3. Export to STL
mcc export stl my_gear.py -o my_gear.stl --quality high
```

## Using with Claude Code

MichelangeloCC includes a SKILL that teaches Claude Code how to generate 3D models. Simply ask Claude to create a model:

```
"Create a parametric gear with 20 teeth and an 8mm shaft hole"
```

Claude will:
1. Generate a Python script using build123d
2. Preview it with `mcc preview model`
3. Validate with `mcc validate mesh`
4. Export to STL when you're ready

## CLI Reference

| Command | Description |
|---------|-------------|
| `mcc session "<prompt>"` | **Start interactive session with Claude Code** |
| `mcc preview model <script>` | Preview model in browser with hot-reload |
| `mcc preview stl <file>` | Preview existing STL file |
| `mcc export stl <script>` | Export to STL format |
| `mcc validate mesh <input>` | Validate mesh for 3D printing |
| `mcc repair auto <stl>` | Auto-repair mesh issues |
| `mcc info <input>` | Show model information |
| `mcc new <name>` | Create new project from template |
| `mcc help` | Show detailed help |
| `mcc help <command>` | Show help for specific command |

### Getting Help

```bash
# Show all commands
mcc --help

# Detailed help with examples
mcc help

# Help for specific commands
mcc help export
mcc help preview
mcc export stl --help
```

See [docs/CLI.md](docs/CLI.md) for complete documentation.

### Export Quality Options

```bash
# Draft (fast, lower detail)
mcc export stl model.py --quality draft

# Standard (default, balanced)
mcc export stl model.py --quality standard

# High (fine detail)
mcc export stl model.py --quality high

# Ultra (maximum precision)
mcc export stl model.py --quality ultra
```

## Writing Model Scripts

Model scripts follow a simple pattern:

```python
"""
Model: My Part
Description: A simple box with a hole
Units: mm
"""

from build123d import *
from michelangelocc import MichelangeloModel, ModelMetadata

# Parameters at the top
length = 50.0  # mm
width = 30.0   # mm
height = 20.0  # mm
hole_diameter = 10.0  # mm

# Build the model
part = Box(length, width, height)
part -= Cylinder(hole_diameter / 2, height)

# Export
model = MichelangeloModel(
    part=part,
    metadata=ModelMetadata(
        name="my_part",
        description="A simple box with a hole",
        units="mm"
    )
)
```

## Project Templates

```bash
# Basic template
mcc new my_project

# Mechanical part with mounting holes
mcc new bracket --template mechanical

# Organic/artistic shape
mcc new vase --template organic

# Parametric design
mcc new widget --template parametric
```

## Architecture

```
MichelangeloCC/
├── src/michelangelocc/
│   ├── cli.py              # Typer CLI entry point
│   ├── session.py          # Interactive session management (tmux)
│   ├── core/
│   │   ├── modeler.py      # build123d wrapper
│   │   ├── validator.py    # Mesh validation
│   │   ├── repairer.py     # Mesh repair
│   │   └── exporter.py     # STL export
│   └── server/
│       ├── app.py          # FastAPI preview server
│       └── watcher.py      # File watcher for hot-reload
├── .claude/skills/
│   └── 3d-modeling/
│       ├── SKILL.md        # Claude Code skill
│       └── examples/       # Example models
├── docs/
│   ├── CLI.md              # CLI reference
│   └── DECISIONS.md        # Technical decision log
└── tests/
```

### How It Works

1. **`mcc session`** creates a session folder, starts the preview server, and launches Claude Code in tmux
2. **Preview Server** (FastAPI + WebSocket) serves the Three.js viewer and pushes reload notifications
3. **File Watcher** (watchdog) monitors `model.py` for changes (handles atomic writes via move events)
4. **Claude Code** edits `model.py` based on user feedback; changes trigger automatic preview reload
5. **Export** converts build123d geometry to STL with configurable quality

## Development

```bash
# Setup development environment
make install-dev
source .venv/bin/activate

# Run tests
make test

# Run all checks (lint + typecheck + test)
make check

# See all available commands
make help
```

## License

MIT License - see [LICENSE](LICENSE) for details.

## Acknowledgments

- [build123d](https://github.com/gumyr/build123d) - Modern Python CAD
- [trimesh](https://trimesh.org/) - Mesh processing
- [Three.js](https://threejs.org/) - 3D visualization
- [Typer](https://typer.tiangolo.com/) - CLI framework
