"""
MichelangeloCC CLI - Command line interface for 3D model generation.

A Claude Code-powered tool for generating 3D printable STL files from
natural language descriptions using build123d CAD operations.

Usage:
    mcc session "<prompt>"         Start interactive session with Claude Code
    mcc preview model <script>     Preview model in browser
    mcc export stl <script>        Export to STL format
    mcc validate mesh <input>      Validate mesh integrity
    mcc repair auto <stl>          Auto-repair mesh issues
    mcc info <input>               Show model information
    mcc new <name>                 Create new project from template
    mcc help                       Show detailed help

For detailed documentation, see: docs/CLI.md
"""

import typer
from pathlib import Path
from typing import Optional
from enum import Enum
import webbrowser
import sys

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.markdown import Markdown
from rich import print as rprint

console = Console()

# Custom help text
HELP_TEXT = """
# MichelangeloCC CLI

**Claude Code-powered 3D model generator for STL files**

## Quick Start - Interactive Session

The easiest way to create 3D models:

```bash
mcc session "Create a parametric gear with 20 teeth"
```

This starts an interactive session where:
1. A session folder is created with model.py
2. Browser opens with live 3D preview
3. Claude Code launches to help you design
4. Changes update the preview automatically!

## Commands

### Interactive Session (Recommended)
- `mcc session "<prompt>"` - Start interactive modeling session with Claude Code

### Preview
- `mcc preview model <script>` - Preview model in browser with hot-reload
- `mcc preview stl <file>` - Preview existing STL file

### Export
- `mcc export stl <script>` - Export model to STL format

### Validate & Repair
- `mcc validate mesh <input>` - Check mesh for 3D printing compatibility
- `mcc repair auto <stl>` - Automatically fix mesh issues

### Project Management
- `mcc new <name>` - Create new project from template
- `mcc info <input>` - Display model information

### Other
- `mcc version` - Show version
- `mcc help` - Show this help
- `mcc help <command>` - Help for specific command

## Getting Help

Use `--help` with any command for detailed options:
```bash
mcc session --help
mcc export stl --help
```

Full documentation: docs/CLI.md
"""

app = typer.Typer(
    name="mcc",
    help="MichelangeloCC - Claude Code 3D Model Generator. Use 'mcc help' for detailed usage.",
    add_completion=True,
    no_args_is_help=True,
    rich_markup_mode="rich",
)


class QualityOption(str, Enum):
    """Quality presets for STL export."""
    draft = "draft"
    standard = "standard"
    high = "high"
    ultra = "ultra"


class TemplateOption(str, Enum):
    """Available project templates."""
    basic = "basic"
    mechanical = "mechanical"
    organic = "organic"
    parametric = "parametric"


# === PREVIEW COMMANDS ===

preview_app = typer.Typer(help="Preview models in browser")
app.add_typer(preview_app, name="preview")


@preview_app.command("model")
def preview_model(
    script_path: Path = typer.Argument(..., help="Path to Python script generating model"),
    port: int = typer.Option(8080, "--port", "-p", help="Server port"),
    no_browser: bool = typer.Option(False, "--no-browser", help="Don't open browser automatically"),
    watch: bool = typer.Option(True, "--watch/--no-watch", help="Watch for file changes"),
):
    """
    Preview a model from a Python script in the browser.

    The script should define a 'model' variable containing a MichelangeloModel
    or build123d Part object.

    Example:
        mcc preview model ./my_gear.py
        mcc preview model ./bracket.py --port 3000 --no-browser
    """
    if not script_path.exists():
        console.print(f"[red]Error:[/red] Script not found: {script_path}")
        raise typer.Exit(1)

    console.print(f"[cyan]Starting preview server for:[/cyan] {script_path}")
    console.print(f"[cyan]Port:[/cyan] {port}")
    console.print(f"[cyan]Watch mode:[/cyan] {'enabled' if watch else 'disabled'}")

    try:
        from michelangelocc.server.app import run_preview_server
        run_preview_server(
            script_path=script_path,
            port=port,
            open_browser=not no_browser,
            watch=watch,
        )
    except KeyboardInterrupt:
        console.print("\n[yellow]Server stopped.[/yellow]")
    except ImportError as e:
        console.print(f"[red]Error:[/red] Server dependencies not available: {e}")
        raise typer.Exit(1)


@preview_app.command("stl")
def preview_stl(
    stl_path: Path = typer.Argument(..., help="Path to STL file"),
    port: int = typer.Option(8080, "--port", "-p", help="Server port"),
):
    """
    Preview an existing STL file in the browser.

    Example:
        mcc preview stl ./output/model.stl
    """
    if not stl_path.exists():
        console.print(f"[red]Error:[/red] STL file not found: {stl_path}")
        raise typer.Exit(1)

    console.print(f"[cyan]Starting preview server for:[/cyan] {stl_path}")

    try:
        from michelangelocc.server.app import run_stl_preview_server
        run_stl_preview_server(stl_path=stl_path, port=port)
    except KeyboardInterrupt:
        console.print("\n[yellow]Server stopped.[/yellow]")
    except ImportError as e:
        console.print(f"[red]Error:[/red] Server dependencies not available: {e}")
        raise typer.Exit(1)


# === EXPORT COMMANDS ===

export_app = typer.Typer(help="Export models to various formats")
app.add_typer(export_app, name="export")


@export_app.command("stl")
def export_stl(
    script_path: Path = typer.Argument(..., help="Path to Python script generating model"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output file path"),
    quality: QualityOption = typer.Option(QualityOption.standard, "--quality", "-q"),
    binary: bool = typer.Option(True, "--binary/--ascii", help="Binary or ASCII STL"),
    no_validate: bool = typer.Option(False, "--no-validate", help="Skip validation"),
    no_repair: bool = typer.Option(False, "--no-repair", help="Skip auto-repair"),
):
    """
    Export a model to STL format.

    Example:
        mcc export stl ./my_model.py -o ./output/model.stl --quality high
        mcc export stl ./part.py --ascii
    """
    from michelangelocc.core.modeler import load_model_from_script
    from michelangelocc.core.exporter import STLExporter, ExportSettings, ExportQuality, STLFormat

    if not script_path.exists():
        console.print(f"[red]Error:[/red] Script not found: {script_path}")
        raise typer.Exit(1)

    # Default output path
    if output is None:
        output = script_path.with_suffix(".stl")

    console.print(f"[cyan]Loading model from:[/cyan] {script_path}")

    try:
        model = load_model_from_script(script_path)
    except Exception as e:
        console.print(f"[red]Error loading model:[/red] {e}")
        raise typer.Exit(1)

    # Configure export settings
    settings = ExportSettings(
        format=STLFormat.BINARY if binary else STLFormat.ASCII,
        quality=ExportQuality[quality.value.upper()],
        validate_before_export=not no_validate,
        repair_if_invalid=not no_repair,
    )

    console.print(f"[cyan]Exporting to:[/cyan] {output}")
    console.print(f"[cyan]Quality:[/cyan] {quality.value}")
    console.print(f"[cyan]Format:[/cyan] {'binary' if binary else 'ascii'}")

    exporter = STLExporter(settings)
    result = exporter.export(model, output)

    if result.success:
        console.print(f"\n[green]Export successful![/green]")
        console.print(result.summary())
    else:
        console.print(f"\n[red]Export failed:[/red] {result.error_message}")
        raise typer.Exit(1)


# === VALIDATE COMMANDS ===

validate_app = typer.Typer(help="Validate mesh integrity")
app.add_typer(validate_app, name="validate")


@validate_app.command("mesh")
def validate_mesh(
    input_path: Path = typer.Argument(..., help="Path to STL file or Python script"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed output"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """
    Validate mesh for 3D printing compatibility.

    Checks:
    - Watertight (manifold) mesh
    - Consistent normals
    - No degenerate triangles

    Example:
        mcc validate mesh ./model.stl
        mcc validate mesh ./model.py --verbose
    """
    from michelangelocc.core.validator import MeshValidator
    import trimesh
    import json

    if not input_path.exists():
        console.print(f"[red]Error:[/red] File not found: {input_path}")
        raise typer.Exit(1)

    console.print(f"[cyan]Validating:[/cyan] {input_path}")

    # Load mesh
    try:
        if input_path.suffix == ".py":
            from michelangelocc.core.modeler import load_model_from_script
            model = load_model_from_script(input_path)
            mesh = model.to_mesh()
        else:
            mesh = trimesh.load(str(input_path))
    except Exception as e:
        console.print(f"[red]Error loading mesh:[/red] {e}")
        raise typer.Exit(1)

    # Validate
    validator = MeshValidator()
    result = validator.validate(mesh)

    if json_output:
        output = {
            "is_valid": result.is_valid,
            "is_watertight": result.is_watertight,
            "is_printable": result.is_printable,
            "triangle_count": result.triangle_count,
            "vertex_count": result.vertex_count,
            "volume": result.volume,
            "surface_area": result.surface_area,
            "issues": [
                {
                    "severity": i.severity.value,
                    "code": i.code,
                    "message": i.message,
                }
                for i in result.issues
            ],
        }
        print(json.dumps(output, indent=2))
    else:
        if verbose:
            console.print(result.summary())
        else:
            # Brief output
            status = "[green]VALID[/green]" if result.is_valid else "[red]INVALID[/red]"
            watertight = "[green]Yes[/green]" if result.is_watertight else "[red]No[/red]"
            console.print(f"\nStatus: {status}")
            console.print(f"Watertight: {watertight}")
            console.print(f"Triangles: {result.triangle_count:,}")
            if result.issues:
                console.print(f"Issues: {len(result.issues)}")

    if not result.is_valid:
        raise typer.Exit(1)


# === REPAIR COMMANDS ===

repair_app = typer.Typer(help="Repair mesh issues")
app.add_typer(repair_app, name="repair")


@repair_app.command("auto")
def repair_auto(
    input_path: Path = typer.Argument(..., help="Path to STL file"),
    output: Optional[Path] = typer.Option(None, "--output", "-o"),
    aggressive: bool = typer.Option(False, "--aggressive", help="Use PyMeshFix for severe issues"),
):
    """
    Automatically repair mesh issues.

    Example:
        mcc repair auto ./broken.stl -o ./fixed.stl
    """
    from michelangelocc.core.repairer import MeshRepairer
    import trimesh

    if not input_path.exists():
        console.print(f"[red]Error:[/red] File not found: {input_path}")
        raise typer.Exit(1)

    if output is None:
        stem = input_path.stem
        output = input_path.with_name(f"{stem}_repaired.stl")

    console.print(f"[cyan]Repairing:[/cyan] {input_path}")
    console.print(f"[cyan]Mode:[/cyan] {'aggressive (PyMeshFix)' if aggressive else 'standard'}")

    try:
        mesh = trimesh.load(str(input_path))
    except Exception as e:
        console.print(f"[red]Error loading mesh:[/red] {e}")
        raise typer.Exit(1)

    repairer = MeshRepairer()

    if aggressive:
        result = repairer.repair_aggressive(mesh)
    else:
        result = repairer.repair(mesh)

    console.print(result.summary())

    if result.was_modified:
        result.mesh.export(str(output))
        console.print(f"\n[green]Repaired mesh saved to:[/green] {output}")
    else:
        console.print("\n[yellow]No repairs needed.[/yellow]")


# === INFO COMMAND ===

@app.command("info")
def info(
    input_path: Path = typer.Argument(..., help="Path to STL file or Python script"),
):
    """
    Display model information (dimensions, volume, triangle count).

    Example:
        mcc info ./model.stl
    """
    import trimesh

    if not input_path.exists():
        console.print(f"[red]Error:[/red] File not found: {input_path}")
        raise typer.Exit(1)

    console.print(f"[cyan]Model Info:[/cyan] {input_path}\n")

    try:
        if input_path.suffix == ".py":
            from michelangelocc.core.modeler import load_model_from_script
            model = load_model_from_script(input_path)
            info_dict = model.info()
        else:
            mesh = trimesh.load(str(input_path))
            bounds = mesh.bounds
            info_dict = {
                "name": input_path.stem,
                "dimensions": {
                    "x": bounds[1][0] - bounds[0][0],
                    "y": bounds[1][1] - bounds[0][1],
                    "z": bounds[1][2] - bounds[0][2],
                },
                "volume": float(mesh.volume) if mesh.is_watertight else None,
                "surface_area": float(mesh.area),
                "triangles": len(mesh.faces),
                "vertices": len(mesh.vertices),
                "is_watertight": mesh.is_watertight,
            }
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    # Display info
    table = Table(show_header=False, box=None)
    table.add_column(style="cyan")
    table.add_column()

    table.add_row("Name", info_dict.get("name", "Unknown"))

    dims = info_dict.get("dimensions", {})
    table.add_row(
        "Dimensions",
        f"{dims.get('x', 0):.2f} x {dims.get('y', 0):.2f} x {dims.get('z', 0):.2f} mm"
    )

    vol = info_dict.get("volume")
    if vol:
        if vol > 1000:
            table.add_row("Volume", f"{vol/1000:.2f} cm^3")
        else:
            table.add_row("Volume", f"{vol:.2f} mm^3")

    table.add_row("Surface Area", f"{info_dict.get('surface_area', 0):.2f} mm^2")
    table.add_row("Triangles", f"{info_dict.get('triangles', 0):,}")
    table.add_row("Vertices", f"{info_dict.get('vertices', 0):,}")

    watertight = info_dict.get("is_watertight", False)
    table.add_row("Watertight", "[green]Yes[/green]" if watertight else "[red]No[/red]")

    console.print(table)


# === NEW PROJECT COMMAND ===

@app.command("new")
def new_project(
    name: str = typer.Argument(..., help="Project name"),
    template: TemplateOption = typer.Option(
        TemplateOption.basic,
        "--template", "-t",
        help="Template: basic, mechanical, organic, parametric"
    ),
):
    """
    Create a new MichelangeloCC project with boilerplate.

    Example:
        mcc new my_gear --template mechanical
    """
    project_dir = Path.cwd() / name

    if project_dir.exists():
        console.print(f"[red]Error:[/red] Directory already exists: {project_dir}")
        raise typer.Exit(1)

    console.print(f"[cyan]Creating project:[/cyan] {name}")
    console.print(f"[cyan]Template:[/cyan] {template.value}")

    # Create directory
    project_dir.mkdir(parents=True)

    # Create template file
    template_content = _get_template_content(template.value, name)
    model_file = project_dir / f"{name}.py"
    model_file.write_text(template_content)

    console.print(f"\n[green]Project created![/green]")
    console.print(f"\nNext steps:")
    console.print(f"  cd {name}")
    console.print(f"  mcc preview model {name}.py")


def _get_template_content(template: str, name: str) -> str:
    """Get template content for new project."""
    templates = {
        "basic": f'''"""
Model: {name}
Description: Basic 3D model
Author: Generated by MichelangeloCC
Units: mm
"""

from build123d import *
from michelangelocc import MichelangeloModel, ModelMetadata

# === Parameters ===
length = 50.0  # mm
width = 30.0   # mm
height = 20.0  # mm

# === Model Construction ===
part = Box(length, width, height)

# === Export ===
model = MichelangeloModel(
    part=part,
    metadata=ModelMetadata(
        name="{name}",
        description="Basic 3D model",
        units="mm"
    )
)
''',
        "mechanical": f'''"""
Model: {name}
Description: Mechanical part with mounting holes
Author: Generated by MichelangeloCC
Units: mm
"""

from build123d import *
from michelangelocc import MichelangeloModel, ModelMetadata

# === Parameters ===
# Main body
body_length = 80.0  # mm
body_width = 40.0   # mm
body_height = 15.0  # mm

# Mounting holes (M5)
hole_diameter = 5.2   # mm
hole_inset = 10.0     # mm from edge

# Fillets
fillet_radius = 2.0  # mm

# === Model Construction ===
# Main body
part = Box(body_length, body_width, body_height)

# Mounting holes (4 corners)
hole_positions = [
    (body_length/2 - hole_inset, body_width/2 - hole_inset),
    (body_length/2 - hole_inset, -body_width/2 + hole_inset),
    (-body_length/2 + hole_inset, body_width/2 - hole_inset),
    (-body_length/2 + hole_inset, -body_width/2 + hole_inset),
]

for x, y in hole_positions:
    part -= Pos(x, y, 0) * Cylinder(hole_diameter/2, body_height)

# Fillet vertical edges
part = fillet(part.edges().filter_by(Axis.Z), fillet_radius)

# === Export ===
model = MichelangeloModel(
    part=part,
    metadata=ModelMetadata(
        name="{name}",
        description="Mechanical mounting bracket",
        units="mm"
    )
)
''',
        "organic": f'''"""
Model: {name}
Description: Organic/artistic shape with smooth curves
Author: Generated by MichelangeloCC
Units: mm
"""

from build123d import *
from michelangelocc import MichelangeloModel, ModelMetadata
import math

# === Parameters ===
base_radius = 30.0  # mm
top_radius = 15.0   # mm
height = 80.0       # mm
twist_angle = 45.0  # degrees
num_sections = 8    # smoothness

# === Model Construction ===
profiles = []
section_height = height / (num_sections - 1)

for i in range(num_sections):
    z = i * section_height
    t = i / (num_sections - 1)  # 0 to 1

    # Interpolate radius with ease
    ease_t = t * t * (3 - 2 * t)  # Smooth step
    radius = base_radius + (top_radius - base_radius) * ease_t

    # Rotation for twist
    rotation = twist_angle * t

    with BuildSketch(Plane.XY.offset(z)) as profile:
        RegularPolygon(radius, 6, rotation=rotation)

    profiles.append(profile.sketch)

# Loft between profiles
part = loft(profiles)

# === Export ===
model = MichelangeloModel(
    part=part,
    metadata=ModelMetadata(
        name="{name}",
        description="Twisted organic vase shape",
        units="mm"
    )
)
''',
        "parametric": f'''"""
Model: {name}
Description: Parametric design with configurable features
Author: Generated by MichelangeloCC
Units: mm
"""

from build123d import *
from michelangelocc import MichelangeloModel, ModelMetadata

# === Parameters (adjust these to modify the design) ===
# Overall size
outer_diameter = 60.0  # mm
inner_diameter = 50.0  # mm
height = 30.0          # mm

# Features
num_slots = 6           # number of radial slots
slot_width = 4.0        # mm
slot_depth = 10.0       # mm

# Rounding
fillet_radius = 1.5     # mm

# === Derived Parameters ===
outer_radius = outer_diameter / 2
inner_radius = inner_diameter / 2
wall_thickness = outer_radius - inner_radius

# === Model Construction ===
# Base ring
part = Cylinder(outer_radius, height) - Cylinder(inner_radius, height)

# Add radial slots
import math
for i in range(num_slots):
    angle = i * (360 / num_slots)
    angle_rad = math.radians(angle)

    # Slot positioned at outer edge
    slot_x = (outer_radius - slot_depth/2) * math.cos(angle_rad)
    slot_y = (outer_radius - slot_depth/2) * math.sin(angle_rad)

    slot = Pos(slot_x, slot_y, height/2) * Rot(0, 0, angle) * Box(slot_depth, slot_width, height)
    part -= slot

# Fillet top and bottom edges
top_edges = part.edges().filter_by(Axis.Z).filter_by(lambda e: e.center().Z > height/2)
bottom_edges = part.edges().filter_by(Axis.Z).filter_by(lambda e: e.center().Z < height/2)
part = fillet(top_edges, fillet_radius)
part = fillet(bottom_edges, fillet_radius)

# === Export ===
model = MichelangeloModel(
    part=part,
    metadata=ModelMetadata(
        name="{name}",
        description="Parametric ring with radial slots",
        units="mm"
    )
)
''',
    }

    return templates.get(template, templates["basic"])


# === SESSION COMMAND ===

@app.command("session")
def session_command(
    prompt: str = typer.Argument(..., help="Natural language description of the model to create"),
    port: int = typer.Option(8080, "--port", "-p", help="Preview server port"),
    no_browser: bool = typer.Option(False, "--no-browser", help="Don't open browser automatically"),
    template: TemplateOption = typer.Option(
        TemplateOption.basic,
        "--template", "-t",
        help="Initial template: basic, mechanical, organic, parametric"
    ),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="Claude model override (e.g., sonnet, opus)"),
):
    """
    Start an interactive 3D modeling session with Claude Code.

    Creates a session folder, starts the preview server with hot-reload,
    and launches Claude Code with the 3D modeling skill context.

    The browser shows a live preview that updates automatically when
    Claude edits the model file.

    Examples:
        mcc session "Create a parametric gear with 20 teeth"
        mcc session "Design a phone stand" --template mechanical
        mcc session "Build a vase" -t organic --port 9000
    """
    from michelangelocc.session import run_interactive_session

    run_interactive_session(
        prompt=prompt,
        port=port,
        open_browser=not no_browser,
        template=template.value,
        model=model,
    )


# === VERSION COMMAND ===

@app.command("version")
def version():
    """Show MichelangeloCC version."""
    from michelangelocc import __version__
    console.print(f"MichelangeloCC v{__version__}")


# === HELP COMMAND ===

@app.command("help")
def help_command(
    command: Optional[str] = typer.Argument(None, help="Command to get help for"),
):
    """
    Show detailed help information.

    Examples:
        mcc help              Show overview
        mcc help export       Show export commands
        mcc help preview      Show preview commands
    """
    if command is None:
        # Show general help
        console.print(Markdown(HELP_TEXT))
    elif command == "preview":
        console.print(Panel.fit(
            "[bold cyan]Preview Commands[/bold cyan]\n\n"
            "[bold]mcc preview model <script>[/bold]\n"
            "  Preview a Python script model in the browser.\n"
            "  Options:\n"
            "    -p, --port INT      Server port (default: 8080)\n"
            "    --no-browser        Don't open browser automatically\n"
            "    --no-watch          Disable hot-reload\n\n"
            "[bold]mcc preview stl <file>[/bold]\n"
            "  Preview an existing STL file.\n"
            "  Options:\n"
            "    -p, --port INT      Server port (default: 8080)\n",
            title="Preview Help"
        ))
    elif command == "export":
        console.print(Panel.fit(
            "[bold cyan]Export Commands[/bold cyan]\n\n"
            "[bold]mcc export stl <script>[/bold]\n"
            "  Export a model to STL format.\n"
            "  Options:\n"
            "    -o, --output PATH   Output file path\n"
            "    -q, --quality ENUM  Quality: draft, standard, high, ultra\n"
            "    --binary/--ascii    File format (default: binary)\n"
            "    --no-validate       Skip validation\n"
            "    --no-repair         Skip auto-repair\n\n"
            "[bold]Quality Presets:[/bold]\n"
            "    draft    - 0.1mm tolerance (fast)\n"
            "    standard - 0.01mm tolerance (default)\n"
            "    high     - 0.001mm tolerance (detailed)\n"
            "    ultra    - 0.0001mm tolerance (maximum)\n",
            title="Export Help"
        ))
    elif command == "validate":
        console.print(Panel.fit(
            "[bold cyan]Validate Commands[/bold cyan]\n\n"
            "[bold]mcc validate mesh <input>[/bold]\n"
            "  Validate mesh for 3D printing compatibility.\n"
            "  Options:\n"
            "    -v, --verbose       Show detailed output\n"
            "    --json              Output as JSON\n\n"
            "[bold]Checks Performed:[/bold]\n"
            "    - Watertight (manifold) mesh\n"
            "    - Consistent face normals\n"
            "    - No degenerate triangles\n"
            "    - Volume and dimension sanity\n"
            "    - Printability recommendations\n",
            title="Validate Help"
        ))
    elif command == "repair":
        console.print(Panel.fit(
            "[bold cyan]Repair Commands[/bold cyan]\n\n"
            "[bold]mcc repair auto <stl>[/bold]\n"
            "  Automatically repair mesh issues.\n"
            "  Options:\n"
            "    -o, --output PATH   Output file path\n"
            "    --aggressive        Use PyMeshFix (severe issues)\n\n"
            "[bold]Standard Repairs:[/bold]\n"
            "    - Merge duplicate vertices\n"
            "    - Remove degenerate faces\n"
            "    - Fix face normals\n"
            "    - Fill holes\n\n"
            "[bold]Aggressive Mode:[/bold]\n"
            "    Uses PyMeshFix for comprehensive repair.\n"
            "    Best for severely damaged meshes.\n",
            title="Repair Help"
        ))
    elif command == "new":
        console.print(Panel.fit(
            "[bold cyan]New Project Command[/bold cyan]\n\n"
            "[bold]mcc new <name>[/bold]\n"
            "  Create a new project from template.\n"
            "  Options:\n"
            "    -t, --template ENUM  Template type\n\n"
            "[bold]Templates:[/bold]\n"
            "    basic       - Simple box model\n"
            "    mechanical  - Bracket with mounting holes\n"
            "    organic     - Twisted vase shape\n"
            "    parametric  - Ring with configurable slots\n",
            title="New Project Help"
        ))
    elif command == "info":
        console.print(Panel.fit(
            "[bold cyan]Info Command[/bold cyan]\n\n"
            "[bold]mcc info <input>[/bold]\n"
            "  Display model information.\n\n"
            "[bold]Output:[/bold]\n"
            "    - Model name\n"
            "    - Dimensions (X x Y x Z)\n"
            "    - Volume\n"
            "    - Surface area\n"
            "    - Triangle/vertex count\n"
            "    - Watertight status\n",
            title="Info Help"
        ))
    elif command == "session":
        console.print(Panel.fit(
            "[bold cyan]Session Command[/bold cyan]\n\n"
            "[bold]mcc session \"<prompt>\"[/bold]\n"
            "  Start an interactive 3D modeling session.\n"
            "  Options:\n"
            "    -p, --port INT       Server port (default: 8080)\n"
            "    --no-browser         Don't open browser automatically\n"
            "    -t, --template ENUM  Initial template type\n"
            "    -m, --model TEXT     Claude model override\n\n"
            "[bold]What Happens:[/bold]\n"
            "    1. Creates session_<timestamp>/ folder\n"
            "    2. Starts preview server with hot-reload\n"
            "    3. Opens browser with 3D viewer\n"
            "    4. Launches Claude Code with context\n\n"
            "[bold]Templates:[/bold]\n"
            "    basic       - Simple starting point\n"
            "    mechanical  - Bracket with mounting holes\n"
            "    organic     - Twisted vase shape\n"
            "    parametric  - Configurable ring\n\n"
            "[bold]Example:[/bold]\n"
            "    mcc session \"Create a gear with 20 teeth\"\n"
            "    mcc session \"Design phone stand\" -t mechanical\n",
            title="Session Help"
        ))
    else:
        console.print(f"[yellow]Unknown command:[/yellow] {command}")
        console.print("Available: session, preview, export, validate, repair, new, info")
        console.print("\nRun [cyan]mcc help[/cyan] for full help.")


if __name__ == "__main__":
    app()
