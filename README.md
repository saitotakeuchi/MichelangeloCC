# MichelangeloCC

**Claude Code-powered 3D model generator for STL files**

MichelangeloCC is a tool that enables Claude Code to generate 3D printable models from natural language descriptions. It combines the power of [build123d](https://github.com/gumyr/build123d) for CAD modeling with a browser-based visualization and seamless STL export.

## Features

- **Natural Language to 3D**: Describe what you want, Claude generates the model
- **Browser-based Preview**: Interactive 3D viewer with hot-reload
- **Validation Pipeline**: Checks models for 3D printability before export
- **Auto-repair**: Automatically fixes common mesh issues
- **Quality Control**: Configurable export quality settings
- **SKILL Integration**: Claude Code skill for guided model generation

## Installation

### Quick Install (Recommended)

Run the install script - it handles Python version detection and isolated installation automatically:

```bash
curl -sSL https://raw.githubusercontent.com/saitotakeuchi/MichelangeloCC/main/install.sh | bash
```

### Alternative: Using pipx

If you already have [pipx](https://pipx.pypa.io/) installed:

```bash
pipx install git+https://github.com/saitotakeuchi/MichelangeloCC.git
```

### Alternative: Using uv

If you prefer [uv](https://github.com/astral-sh/uv):

```bash
uv tool install git+https://github.com/saitotakeuchi/MichelangeloCC.git
```

### For Development

```bash
git clone https://github.com/saitotakeuchi/MichelangeloCC.git
cd MichelangeloCC
make install-dev
source .venv/bin/activate
```

### Requirements

- Python 3.10+
- macOS or Linux (Windows via WSL)
- A modern browser for visualization

### Troubleshooting

<details>
<summary>macOS: "externally-managed-environment" error</summary>

Modern Homebrew Python is PEP 668 compliant and blocks direct pip installs.
Use the install script, pipx, or uv instead - they create isolated environments automatically.

</details>

<details>
<summary>"command not found: mcc" after installation</summary>

Your PATH may need updating. Restart your terminal or run:

```bash
source ~/.zshrc  # or ~/.bashrc
```

</details>

<details>
<summary>Uninstalling</summary>

```bash
# If installed via pipx
pipx uninstall michelangelocc

# If installed via uv
uv tool uninstall michelangelocc

# Or use the uninstall script
curl -sSL https://raw.githubusercontent.com/saitotakeuchi/MichelangeloCC/main/uninstall.sh | bash
```

</details>

## Quick Start

### 1. Create a New Project

```bash
mcc new my_gear --template mechanical
cd my_gear
```

### 2. Preview Your Model

```bash
mcc preview model my_gear.py
```

This opens a browser window with an interactive 3D viewer. Changes to the script automatically reload.

### 3. Export to STL

```bash
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
│   ├── cli.py              # Typer CLI
│   ├── core/
│   │   ├── modeler.py      # build123d wrapper
│   │   ├── validator.py    # Mesh validation
│   │   ├── repairer.py     # Mesh repair
│   │   └── exporter.py     # STL export
│   └── server/
│       ├── app.py          # FastAPI server
│       └── watcher.py      # Hot-reload
├── .claude/skills/
│   └── 3d-modeling/
│       ├── SKILL.md        # Claude Code skill
│       └── examples/       # Example models
└── tests/
```

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
