# MichelangeloCC CLI Reference

Complete command reference for the `mcc` command-line interface.

## Quick Reference

```bash
mcc --help                      # Show all commands
mcc <command> --help            # Show help for a command
mcc <command> <subcommand> --help  # Show help for a subcommand
```

## Installation

```bash
pipx install michelangelocc
mcc --help
```

For development:
```bash
git clone https://github.com/saitotakeuchi/MichelangeloCC.git
cd MichelangeloCC && make install-dev
```

---

## Commands Overview

| Command | Description |
|---------|-------------|
| `mcc session` | **Start interactive session with Claude Code** |
| `mcc preview` | Preview models in browser |
| `mcc export` | Export models to various formats |
| `mcc validate` | Validate mesh integrity |
| `mcc repair` | Repair mesh issues |
| `mcc info` | Display model information |
| `mcc new` | Create new project from template |
| `mcc version` | Show version |
| `mcc help` | Show help information |

---

## Session Command

### `mcc session`

Start an interactive 3D modeling session with Claude Code. This is the **recommended way** to use MichelangeloCC for iterative design.

```bash
mcc session "<prompt>" [OPTIONS]
```

**Arguments:**
| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `prompt` | TEXT | Yes | Natural language description of the model to create |

**Options:**
| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--port` | `-p` | INT | 8080 | Preview server port |
| `--no-browser` | | FLAG | False | Don't open browser automatically |
| `--template` | `-t` | ENUM | `basic` | Initial template: `basic`, `mechanical`, `organic`, `parametric` |
| `--model` | `-m` | TEXT | None | Claude model override (e.g., `sonnet`, `opus`) |
| `--help` | | FLAG | | Show help message |

**What Happens:**
1. Creates a timestamped session folder (e.g., `session_20260110_143052/`)
2. Generates `model.py` from the selected template with your prompt
3. Starts the preview server with hot-reload
4. Opens browser to show live 3D preview
5. Creates a tmux session (named `mcc-<timestamp>`)
6. Launches Claude Code CLI inside tmux with full session context

**Requirements:**
- tmux must be installed (`brew install tmux` on macOS)
- Claude Code CLI must be installed (`npm install -g @anthropic-ai/claude-code`)

**Session Folder Structure:**
```
session_20260110_143052/
├── model.py              # Main model script (edit this)
└── output/               # Folder for exported STL files
```

**Examples:**
```bash
# Basic session
mcc session "Create a simple phone stand"

# Mechanical part with template
mcc session "Design a mounting bracket with 4 M5 holes" --template mechanical

# Organic shape on custom port
mcc session "Create a decorative vase" -t organic -p 3000

# Use specific Claude model
mcc session "Design a gear with 24 teeth" --model opus
```

**During the Session:**
- Edit `model.py` and the browser preview updates automatically
- Ask Claude to modify the model iteratively
- When finished, export: `mcc export stl model.py -o output/model.stl --quality high`
- Press `Ctrl+C` or type `/exit` to end the session

**tmux Session Management:**
```bash
# Detach from session (keeps it running)
Ctrl+B, then D

# List running sessions
tmux list-sessions

# Reattach to a session
tmux attach -t mcc-20260110_143052

# Kill a session manually
tmux kill-session -t mcc-20260110_143052
```

**Note:** When you exit Claude (via `/exit` or `Ctrl+C`), both the tmux session and preview server are automatically cleaned up.

**After the Session:**
```bash
# Continue working on the model later
cd session_20260110_143052
mcc preview model model.py

# Export the final STL
mcc export stl model.py -o output/model.stl --quality high
```

---

## Preview Commands

### `mcc preview model`

Preview a 3D model from a Python script in the browser with hot-reload.

```bash
mcc preview model <script_path> [OPTIONS]
```

**Arguments:**
| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `script_path` | PATH | Yes | Path to Python script generating model |

**Options:**
| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--port` | `-p` | INT | 8080 | Server port |
| `--no-browser` | | FLAG | False | Don't open browser automatically |
| `--watch/--no-watch` | | FLAG | True | Watch for file changes (hot-reload) |
| `--help` | | FLAG | | Show help message |

**Examples:**
```bash
# Basic preview
mcc preview model ./my_gear.py

# Custom port, don't open browser
mcc preview model ./bracket.py --port 3000 --no-browser

# Disable hot-reload
mcc preview model ./part.py --no-watch
```

---

### `mcc preview stl`

Preview an existing STL file in the browser.

```bash
mcc preview stl <stl_path> [OPTIONS]
```

**Arguments:**
| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `stl_path` | PATH | Yes | Path to STL file |

**Options:**
| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--port` | `-p` | INT | 8080 | Server port |
| `--help` | | FLAG | | Show help message |

**Examples:**
```bash
mcc preview stl ./output/model.stl
mcc preview stl ./gear.stl --port 9000
```

---

## Export Commands

### `mcc export stl`

Export a model to STL format.

```bash
mcc export stl <script_path> [OPTIONS]
```

**Arguments:**
| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `script_path` | PATH | Yes | Path to Python script generating model |

**Options:**
| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--output` | `-o` | PATH | `<script>.stl` | Output file path |
| `--quality` | `-q` | ENUM | `standard` | Quality preset: `draft`, `standard`, `high`, `ultra` |
| `--binary/--ascii` | | FLAG | `--binary` | Binary or ASCII STL format |
| `--no-validate` | | FLAG | False | Skip validation before export |
| `--no-repair` | | FLAG | False | Skip auto-repair if invalid |
| `--help` | | FLAG | | Show help message |

**Quality Presets:**
| Quality | Tolerance | Use Case |
|---------|-----------|----------|
| `draft` | 0.1mm | Quick preview, large models |
| `standard` | 0.01mm | Most 3D printing (default) |
| `high` | 0.001mm | Fine detail, small parts |
| `ultra` | 0.0001mm | Maximum precision |

**Examples:**
```bash
# Basic export (uses script name for output)
mcc export stl ./my_model.py

# Specify output path and quality
mcc export stl ./gear.py -o ./output/gear.stl --quality high

# ASCII format (larger but human-readable)
mcc export stl ./part.py --ascii

# Skip validation and repair (faster but risky)
mcc export stl ./model.py --no-validate --no-repair
```

---

## Validate Commands

### `mcc validate mesh`

Validate mesh for 3D printing compatibility.

```bash
mcc validate mesh <input_path> [OPTIONS]
```

**Arguments:**
| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `input_path` | PATH | Yes | Path to STL file or Python script |

**Options:**
| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--verbose` | `-v` | FLAG | False | Show detailed validation output |
| `--json` | | FLAG | False | Output results as JSON |
| `--help` | | FLAG | | Show help message |

**Validation Checks:**
- Watertight (manifold) mesh
- Consistent face normals
- No degenerate triangles
- Volume and dimension sanity
- Printability recommendations

**Examples:**
```bash
# Basic validation
mcc validate mesh ./model.stl

# Verbose output with all details
mcc validate mesh ./model.py --verbose

# JSON output (for scripting)
mcc validate mesh ./part.stl --json
```

**JSON Output Format:**
```json
{
  "is_valid": true,
  "is_watertight": true,
  "is_printable": true,
  "triangle_count": 5000,
  "vertex_count": 2500,
  "volume": 15000.5,
  "surface_area": 3200.0,
  "issues": []
}
```

---

## Repair Commands

### `mcc repair auto`

Automatically repair mesh issues.

```bash
mcc repair auto <input_path> [OPTIONS]
```

**Arguments:**
| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `input_path` | PATH | Yes | Path to STL file |

**Options:**
| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--output` | `-o` | PATH | `<input>_repaired.stl` | Output file path |
| `--aggressive` | | FLAG | False | Use PyMeshFix for severe issues |
| `--help` | | FLAG | | Show help message |

**Repair Operations (Standard Mode):**
1. Merge duplicate vertices
2. Remove degenerate faces
3. Fix face normals
4. Fill holes

**Repair Operations (Aggressive Mode):**
- Uses PyMeshFix for comprehensive repair
- Handles severely damaged meshes
- May significantly modify geometry

**Examples:**
```bash
# Basic repair
mcc repair auto ./broken.stl

# Specify output path
mcc repair auto ./broken.stl -o ./fixed.stl

# Aggressive repair for severe issues
mcc repair auto ./badly_broken.stl --aggressive
```

---

## Info Command

### `mcc info`

Display model information (dimensions, volume, triangle count).

```bash
mcc info <input_path>
```

**Arguments:**
| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `input_path` | PATH | Yes | Path to STL file or Python script |

**Options:**
| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--help` | | FLAG | | Show help message |

**Output Information:**
- Model name
- Dimensions (X × Y × Z) in mm
- Volume (mm³ or cm³)
- Surface area (mm²)
- Triangle count
- Vertex count
- Watertight status

**Examples:**
```bash
mcc info ./model.stl
mcc info ./gear.py
```

**Sample Output:**
```
Model Info: gear.py

Name         parametric_gear
Dimensions   42.00 x 42.00 x 10.00 mm
Volume       8.50 cm³
Surface Area 3200.00 mm²
Triangles    12,500
Vertices     6,250
Watertight   Yes
```

---

## New Command

### `mcc new`

Create a new MichelangeloCC project with boilerplate.

```bash
mcc new <name> [OPTIONS]
```

**Arguments:**
| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `name` | TEXT | Yes | Project name |

**Options:**
| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--template` | `-t` | ENUM | `basic` | Template: `basic`, `mechanical`, `organic`, `parametric` |
| `--help` | | FLAG | | Show help message |

**Templates:**
| Template | Description |
|----------|-------------|
| `basic` | Simple box model |
| `mechanical` | Bracket with mounting holes, fillets |
| `organic` | Twisted vase with smooth curves |
| `parametric` | Ring with radial slots, configurable features |

**Examples:**
```bash
# Basic project
mcc new my_project

# Mechanical part template
mcc new bracket --template mechanical

# Organic/artistic shape
mcc new vase -t organic

# Parametric design
mcc new widget -t parametric
```

**Created Files:**
```
<name>/
└── <name>.py    # Model script from template
```

---

## Version Command

### `mcc version`

Show MichelangeloCC version.

```bash
mcc version
```

**Example Output:**
```
MichelangeloCC v0.1.0
```

---

## Help Command

### `mcc help`

Show help information for any command.

```bash
mcc --help                          # All commands
mcc help                            # Same as above
mcc <command> --help                # Command help
mcc <command> <subcommand> --help   # Subcommand help
```

**Examples:**
```bash
mcc --help
mcc export --help
mcc export stl --help
mcc validate mesh --help
```

---

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Error (file not found, validation failed, etc.) |

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `MCC_DEFAULT_QUALITY` | Default export quality | `standard` |
| `MCC_DEFAULT_PORT` | Default preview server port | `8080` |

---

## Common Workflows

### Interactive Session (Recommended)

```bash
# 1. Start a session with Claude Code
mcc session "Create a parametric gear with 20 teeth and 8mm shaft hole" --template mechanical

# 2. Claude and browser work together:
#    - Claude edits model.py based on your feedback
#    - Browser shows live preview updates automatically
#    - Iterate until you're happy with the design

# 3. Export when finished (from within the session)
mcc export stl model.py -o output/gear.stl --quality high

# 4. Session ends with Ctrl+C or /exit
#    Your work is saved in the session folder!
```

### Generate and Export (Manual)

```bash
# 1. Create a new project
mcc new my_gear --template mechanical

# 2. Edit the script (or ask Claude to modify it)
cd my_gear

# 3. Preview while editing
mcc preview model my_gear.py

# 4. Validate before export
mcc validate mesh my_gear.py --verbose

# 5. Export final STL
mcc export stl my_gear.py -o my_gear.stl --quality high
```

### Fix a Broken STL

```bash
# 1. Check what's wrong
mcc validate mesh broken.stl --verbose

# 2. Try standard repair
mcc repair auto broken.stl -o fixed.stl

# 3. If still broken, use aggressive mode
mcc repair auto broken.stl -o fixed.stl --aggressive

# 4. Verify the fix
mcc validate mesh fixed.stl
```

### Batch Processing (Shell Script)

```bash
#!/bin/bash
for script in models/*.py; do
    name=$(basename "$script" .py)
    echo "Processing $name..."
    mcc export stl "$script" -o "output/${name}.stl" --quality high
done
```

---

## Troubleshooting

### "Command not found: mcc"

Make sure MichelangeloCC is installed:
```bash
pip install -e /path/to/MichelangeloCC
```

### "Module not found" errors

Install all dependencies:
```bash
pip install -e ".[dev]"
```

### Preview server won't start

Check if the port is already in use:
```bash
mcc preview model script.py --port 9000
```

### Validation fails but model looks fine

Try auto-repair:
```bash
mcc repair auto model.stl -o model_fixed.stl
```

### Export produces empty or corrupted file

1. Check script for errors: `python your_script.py`
2. Validate first: `mcc validate mesh your_script.py`
3. Lower quality setting: `--quality draft`
