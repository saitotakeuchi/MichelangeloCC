"""
Session management for interactive 3D modeling with Claude Code.

This module handles:
- Session folder creation with model.py template
- Preview server lifecycle management
- Claude CLI invocation with proper context
- Graceful shutdown and cleanup
"""

import os
import sys
import time
import signal
import subprocess
import socket
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional
import atexit

from rich.console import Console

console = Console()

# Global state for server process
_server_process: Optional[subprocess.Popen] = None


def create_session_folder(
    base_dir: Path,
    prompt: str,
    template: str = "basic",
) -> Path:
    """
    Create a timestamped session folder with model.py and structure.

    Args:
        base_dir: Parent directory for the session folder
        prompt: User's description of what they want to create
        template: Template type (basic, mechanical, organic, parametric)

    Returns:
        Path to the created session folder
    """
    # Generate timestamped folder name
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_name = f"session_{timestamp}"
    session_dir = base_dir / session_name

    # Create folder structure
    session_dir.mkdir(parents=True, exist_ok=True)
    (session_dir / "output").mkdir(exist_ok=True)

    # Create model.py from template
    model_content = _get_session_template(prompt, template, timestamp)
    model_path = session_dir / "model.py"
    model_path.write_text(model_content)

    return session_dir


def _get_session_template(prompt: str, template: str, timestamp: str) -> str:
    """Generate the initial model.py content for a session."""

    # Base imports and structure
    header = f'''"""
MichelangeloCC Interactive Session
==================================
Created: {timestamp}
Request: {prompt}

This file is being watched by the preview server.
Any changes will automatically update the 3D viewer in your browser!

To export when ready:
    mcc export stl model.py -o output/model.stl --quality high
"""

from build123d import *
from michelangelocc import MichelangeloModel, ModelMetadata

'''

    # Template-specific content
    templates = {
        "basic": '''# === Parameters ===
length = 50.0  # mm
width = 30.0   # mm
height = 20.0  # mm

# === Model Construction ===
# Starting template - modify based on your needs
part = Box(length, width, height)

''',
        "mechanical": '''# === Parameters ===
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

# Fillet edges
part = fillet(part.edges().filter_by(Axis.Z), fillet_radius)

''',
        "organic": '''# === Parameters ===
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
    t = i / (num_sections - 1)

    # Interpolate radius with smooth easing
    ease_t = t * t * (3 - 2 * t)
    radius = base_radius + (top_radius - base_radius) * ease_t

    # Twist rotation
    rotation = twist_angle * t

    with BuildSketch(Plane.XY.offset(z)) as profile:
        RegularPolygon(radius, 6, rotation=rotation)

    profiles.append(profile.sketch)

# Loft between profiles
part = loft(profiles)

''',
        "parametric": '''# === Parameters (adjust these to modify the design) ===
outer_diameter = 60.0  # mm
inner_diameter = 50.0  # mm
height = 30.0          # mm
num_slots = 6          # number of radial slots
slot_width = 4.0       # mm
slot_depth = 10.0      # mm
fillet_radius = 1.5    # mm

# === Derived Parameters ===
outer_radius = outer_diameter / 2
inner_radius = inner_diameter / 2

# === Model Construction ===
# Base ring
part = Cylinder(outer_radius, height) - Cylinder(inner_radius, height)

# Add radial slots
import math
for i in range(num_slots):
    angle = i * (360 / num_slots)
    angle_rad = math.radians(angle)

    slot_x = (outer_radius - slot_depth/2) * math.cos(angle_rad)
    slot_y = (outer_radius - slot_depth/2) * math.sin(angle_rad)

    slot = Pos(slot_x, slot_y, height/2) * Rot(0, 0, angle) * Box(slot_depth, slot_width, height)
    part -= slot

''',
    }

    body = templates.get(template, templates["basic"])

    # Footer with metadata
    footer = f'''# === Export ===
model = MichelangeloModel(
    part=part,
    metadata=ModelMetadata(
        name="session_model",
        description="""{prompt}""",
        units="mm"
    )
)
'''

    return header + body + footer


def start_preview_server(
    model_path: Path,
    port: int,
    open_browser: bool = True,
) -> subprocess.Popen:
    """
    Start the preview server as a background subprocess.

    Args:
        model_path: Path to model.py to preview
        port: Server port
        open_browser: Whether to open browser automatically

    Returns:
        subprocess.Popen handle for the server process
    """
    cmd = [
        sys.executable, "-m", "michelangelocc.cli",
        "preview", "model",
        str(model_path),
        "--port", str(port),
    ]

    if not open_browser:
        cmd.append("--no-browser")

    # Start as background process with stdout/stderr hidden
    # for clean terminal when running Claude CLI
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,  # Detach from terminal group
    )

    return proc


def wait_for_server_ready(port: int, timeout: float = 10.0) -> bool:
    """
    Poll until the server is accepting connections.

    Args:
        port: Server port to check
        timeout: Maximum time to wait in seconds

    Returns:
        True if server is ready, False if timeout
    """
    start = time.time()
    while time.time() - start < timeout:
        try:
            with socket.create_connection(("localhost", port), timeout=0.5):
                return True
        except (ConnectionRefusedError, socket.timeout, OSError):
            time.sleep(0.2)

    return False


def build_claude_command(
    session_dir: Path,
    prompt: str,
    port: int,
    model: Optional[str] = None,
) -> list[str]:
    """
    Build the Claude CLI command with session context.

    Args:
        session_dir: Path to the session folder
        prompt: User's initial request
        port: Preview server port
        model: Optional Claude model override

    Returns:
        Command as list of strings
    """
    cmd = ["claude"]

    # Add model if specified
    if model:
        cmd.extend(["--model", model])

    # System prompt with session context
    system_prompt = f"""You are in a MichelangeloCC interactive 3D modeling session.

IMPORTANT SESSION CONTEXT:
- Working directory: {session_dir}
- Model file: {session_dir}/model.py
- Preview: http://localhost:{port} (browser shows live preview)
- Output folder: {session_dir}/output/

HOW THIS WORKS:
The browser is showing a live 3D preview of model.py. When you edit model.py,
the viewer automatically reloads and shows the updated model. This lets us
iterate quickly on the design.

WORKFLOW:
1. Read the current model.py to understand the starting point
2. Modify model.py based on the user's request
3. The browser will automatically show the updated model
4. Ask the user for feedback and iterate

WHEN FINISHED:
To export the final STL: mcc export stl model.py -o output/model.stl --quality high

Use the /3d-modeling skill for build123d reference and best practices.

Start by creating the 3D model the user described, then iterate based on their feedback."""

    cmd.extend(["--append-system-prompt", system_prompt])

    # Add initial prompt
    cmd.extend(["-p", prompt])

    return cmd


def cleanup_server():
    """Terminate the server process gracefully."""
    global _server_process

    if _server_process and _server_process.poll() is None:
        # Server still running
        _server_process.terminate()
        try:
            _server_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _server_process.kill()
            _server_process.wait()

    _server_process = None


# === tmux Session Management ===

def check_tmux_installed() -> bool:
    """Check if tmux is available on the system."""
    return shutil.which("tmux") is not None


def create_tmux_session(
    session_name: str,
    command: list[str],
    working_dir: Path,
) -> bool:
    """
    Create a detached tmux session running the given command.

    Args:
        session_name: Name for the tmux session
        command: Command to run inside the session
        working_dir: Working directory for the session

    Returns:
        True if session was created successfully
    """
    # Build the command string for tmux
    # Need to properly quote/escape the command
    cmd_str = " ".join(f'"{arg}"' if " " in arg else arg for arg in command)

    tmux_cmd = [
        "tmux", "new-session",
        "-d",  # Detached
        "-s", session_name,  # Session name
        "-c", str(working_dir),  # Working directory
        cmd_str,  # Command to run
    ]

    try:
        result = subprocess.run(tmux_cmd, capture_output=True, text=True)
        return result.returncode == 0
    except Exception:
        return False


def attach_tmux_session(session_name: str) -> int:
    """
    Attach to an existing tmux session.

    This blocks until the user detaches or the session ends.

    Args:
        session_name: Name of the tmux session to attach to

    Returns:
        Exit code from tmux attach
    """
    tmux_cmd = ["tmux", "attach-session", "-t", session_name]

    # Use os.system for proper terminal passthrough
    # subprocess doesn't handle TTY well for interactive sessions
    return os.system(" ".join(tmux_cmd))


def kill_tmux_session(session_name: str):
    """
    Kill a tmux session if it exists.

    Args:
        session_name: Name of the tmux session to kill
    """
    subprocess.run(
        ["tmux", "kill-session", "-t", session_name],
        capture_output=True,  # Suppress output
    )


def tmux_session_exists(session_name: str) -> bool:
    """Check if a tmux session with the given name exists."""
    result = subprocess.run(
        ["tmux", "has-session", "-t", session_name],
        capture_output=True,
    )
    return result.returncode == 0


def run_interactive_session(
    prompt: str,
    port: int = 8080,
    open_browser: bool = True,
    template: str = "basic",
    model: Optional[str] = None,
):
    """
    Main entry point for an interactive session.

    Creates the session folder, starts the preview server, and launches
    Claude Code CLI with the appropriate context.

    Args:
        prompt: User's description of what they want to create
        port: Preview server port
        open_browser: Whether to open browser automatically
        template: Initial template type
        model: Optional Claude model override
    """
    global _server_process

    base_dir = Path.cwd()

    # Phase 1: Create session folder
    console.print(f"\n[cyan]Creating session folder...[/cyan]")
    session_dir = create_session_folder(base_dir, prompt, template)
    model_path = session_dir / "model.py"
    console.print(f"[green]Created:[/green] {session_dir}")

    # Phase 2: Start preview server
    console.print(f"\n[cyan]Starting preview server on port {port}...[/cyan]")
    _server_process = start_preview_server(model_path, port, open_browser)

    # Register cleanup handlers
    atexit.register(cleanup_server)

    def signal_handler(signum, frame):
        console.print("\n[yellow]Shutting down session...[/yellow]")
        cleanup_server()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Wait for server to be ready
    if not wait_for_server_ready(port):
        console.print("[red]Error:[/red] Server failed to start")
        cleanup_server()
        sys.exit(1)

    console.print(f"[green]Preview server ready![/green]")
    console.print(f"[cyan]Browser:[/cyan] http://localhost:{port}")

    # Phase 3: Check tmux is available
    if not check_tmux_installed():
        console.print("[red]Error:[/red] tmux is required but not installed")
        console.print("Install with: brew install tmux")
        cleanup_server()
        sys.exit(1)

    # Check Claude CLI is available
    if not shutil.which("claude"):
        console.print("[red]Error:[/red] 'claude' command not found. Is Claude Code CLI installed?")
        console.print("Install with: npm install -g @anthropic-ai/claude-code")
        cleanup_server()
        sys.exit(1)

    # Phase 4: Launch Claude CLI in tmux
    timestamp = session_dir.name.replace("session_", "")
    tmux_session_name = f"mcc-{timestamp}"

    console.print(f"\n[cyan]Launching Claude Code in tmux session...[/cyan]")
    console.print(f"[dim]Session folder: {session_dir}[/dim]")
    console.print(f"[dim]tmux session: {tmux_session_name}[/dim]")
    console.print(f"[dim]Detach: Ctrl+B, D | Reattach: tmux attach -t {tmux_session_name}[/dim]\n")

    # Build Claude command
    cmd = build_claude_command(session_dir, prompt, port, model)

    # Create tmux session with Claude CLI
    if not create_tmux_session(tmux_session_name, cmd, session_dir):
        console.print("[red]Error:[/red] Failed to create tmux session")
        cleanup_server()
        sys.exit(1)

    # Attach to tmux session (blocks until detach or exit)
    attach_tmux_session(tmux_session_name)

    # After detach/exit - cleanup
    # Kill tmux session if it's still running
    if tmux_session_exists(tmux_session_name):
        kill_tmux_session(tmux_session_name)

    cleanup_server()

    # Show session summary
    console.print(f"\n[cyan]Session ended.[/cyan]")
    console.print(f"[green]Session folder:[/green] {session_dir}")
    console.print(f"[green]Model file:[/green] {model_path}")
    console.print(f"\n[dim]To continue working on this model:[/dim]")
    console.print(f"  cd {session_dir}")
    console.print(f"  mcc preview model model.py")
    console.print(f"\n[dim]To export:[/dim]")
    console.print(f"  mcc export stl {model_path} -o {session_dir}/output/model.stl --quality high")
