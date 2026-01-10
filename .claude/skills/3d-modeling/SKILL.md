---
name: 3d-modeling
description: Generate 3D printable models using MichelangeloCC. Creates STL files from natural language descriptions through build123d CAD operations. Use this skill when the user wants to create 3D models, generate STL files, or design objects for 3D printing.
---

# 3D Model Generation with MichelangeloCC

You are an expert 3D modeler using the MichelangeloCC library built on build123d. Generate precise, printable 3D models from user descriptions.

## Core Workflow

When the user asks you to create a 3D model:

1. **Understand** - Clarify dimensions, tolerances, and intended use if not specified
2. **Design** - Create model using build123d operations
3. **Save** - Write the Python script to a `.py` file
4. **Preview** - Run `mcc preview model <script.py>` to visualize
5. **Validate** - Run `mcc validate mesh <script.py>` to check printability
6. **Export** - Run `mcc export stl <script.py> -o <output.stl>` when ready

## Interactive Session Mode

When running in an interactive session started with `mcc session`, you have a streamlined workflow:

### Session Context
- **Working directory**: The session folder (e.g., `session_20260110_143052/`)
- **Model file**: `model.py` - This is the main file to edit
- **Preview**: Browser is already open at `http://localhost:8080` showing live preview
- **Output folder**: `output/` - Place exported STL files here

### How It Works
The browser shows a **live 3D preview** of `model.py`. When you edit and save `model.py`, the viewer automatically reloads and displays the updated model. This enables rapid iteration without manual refresh.

### Session Workflow
1. **Read** the current `model.py` to understand the starting template
2. **Modify** `model.py` based on the user's request
3. **Wait** - The browser automatically shows the updated model
4. **Ask** the user for feedback and iterate
5. **Export** when satisfied: `mcc export stl model.py -o output/model.stl --quality high`

### Best Practices in Session Mode
- Make **small, incremental changes** - easier to debug if something goes wrong
- Keep **parameters at the top** of the file for easy adjustment
- Use the **existing model.py structure** - don't create new files unless necessary
- Check the browser preview after each change before asking for feedback
- When finished, always export to `output/` folder with high quality

### Session Commands
```bash
# Export final model (run from session folder)
mcc export stl model.py -o output/model.stl --quality high

# Validate before export
mcc validate mesh model.py --verbose

# Get model info
mcc info model.py
```

## Model Script Structure

Always create Python scripts following this pattern:

```python
"""
Model: [Name]
Description: [Brief description]
Author: Claude Code
Units: mm (millimeters)
"""

from build123d import *
from michelangelocc import MichelangeloModel, ModelMetadata

# === Parameters ===
# Define all dimensions as variables at the top for easy modification
length = 50.0  # mm
width = 30.0   # mm
height = 10.0  # mm

# === Model Construction ===
# Use build123d algebra mode (preferred for most operations)
part = Box(length, width, height)
part -= Cylinder(5, height)  # Subtract a hole

# For complex operations, use builder mode:
# with BuildPart() as builder:
#     Box(length, width, height)
#     with Locations((0, 0, height)):
#         Cylinder(5, 10, mode=Mode.SUBTRACT)
# part = builder.part

# === Export ===
model = MichelangeloModel(
    part=part,
    metadata=ModelMetadata(
        name="model_name",
        description="Description of the model",
        units="mm"
    )
)
```

## Build123d Quick Reference

### Primitive Shapes
```python
Box(length, width, height)           # Rectangular prism
Cylinder(radius, height)             # Cylinder
Sphere(radius)                       # Sphere
Cone(bottom_radius, top_radius, height)  # Cone or truncated cone
Torus(major_radius, minor_radius)    # Donut shape
```

### Boolean Operations (Algebra Mode)
```python
part1 + part2      # Union (combine shapes)
part1 - part2      # Subtraction (cut)
part1 & part2      # Intersection
```

### Positioning
```python
Pos(x, y, z) * shape       # Translate
Rot(x, y, z) * shape       # Rotate (degrees around each axis)
Pos(10, 0, 0) * Rot(0, 0, 45) * Box(5, 5, 5)  # Combined
```

### Edge Operations
```python
fillet(part.edges(), radius)         # Round all edges
fillet(part.edges().filter_by(Axis.Z), radius)  # Round vertical edges only
chamfer(part.edges(), distance)      # Bevel edges
```

### 2D to 3D Operations
```python
# Extrude a 2D shape
with BuildPart() as p:
    with BuildSketch():
        Rectangle(width, height)
        Circle(radius)  # Adds to sketch
    extrude(amount=depth)

# Revolve around axis
with BuildPart() as p:
    with BuildSketch(Plane.XZ):
        with BuildLine():
            Polyline([(0, 0), (10, 0), (10, 20), (0, 20)])
    revolve(axis=Axis.Z, revolution_arc=360)

# Loft between profiles
loft([profile1, profile2, profile3])

# Sweep along path
sweep(section=circle_profile, path=spline_path)
```

### Sketching (2D Shapes)
```python
with BuildSketch() as s:
    Rectangle(width, height)
    Circle(radius)
    RegularPolygon(radius, n_sides)
    Text("Label", font_size=10)
```

### Selection and Filtering
```python
part.edges()                         # All edges
part.faces()                         # All faces
part.vertices()                      # All vertices

# Filter by axis
part.edges().filter_by(Axis.Z)       # Edges parallel to Z
part.faces().filter_by(Axis.Z)       # Faces perpendicular to Z

# Sort and select
part.edges().sort_by(Axis.Z)[-1]     # Topmost edge
part.faces().sort_by(Axis.Z)[0]      # Bottom face

# Filter by position
part.edges().filter_by(lambda e: e.center().Z > 5)
```

### Common Patterns

#### Hole Pattern (Grid)
```python
for i in range(rows):
    for j in range(cols):
        part -= Pos(i * spacing, j * spacing, 0) * Cylinder(hole_r, height)
```

#### Hole Pattern (Circular)
```python
import math
for i in range(num_holes):
    angle = i * (360 / num_holes)
    x = radius * math.cos(math.radians(angle))
    y = radius * math.sin(math.radians(angle))
    part -= Pos(x, y, 0) * Cylinder(hole_r, height)
```

#### Shell (Hollow Part)
```python
# Open top face
top_face = part.faces().sort_by(Axis.Z)[-1]
part = shell(part, amount=-wall_thickness, openings=[top_face])
```

#### Fillet Specific Edges
```python
# Fillet only top edges
top_edges = part.edges().filter_by(lambda e: e.center().Z > height/2)
part = fillet(top_edges, radius)
```

#### Counterbore Hole
```python
# Through hole
part -= Cylinder(hole_diameter/2, height)
# Counterbore
part -= Pos(0, 0, height - counterbore_depth) * Cylinder(counterbore_diameter/2, counterbore_depth)
```

#### Text Embossing/Engraving
```python
with BuildSketch(part.faces().sort_by(Axis.Z)[-1]):
    Text("LABEL", font_size=8)
extrude(amount=0.5)   # Emboss (raised)
extrude(amount=-0.5)  # Engrave (recessed)
```

## Design Guidelines

### For Mechanical Parts
- Default to **3mm minimum wall thickness** for strength
- Add **0.2mm tolerance** for mating/sliding parts (holes, slots)
- Add **0.1mm tolerance** for press-fit parts
- Use **fillets (2-3mm)** on stress concentration areas
- Consider print orientation: overhangs should be < 45 degrees
- Add **draft angles (1-2 degrees)** for parts that need to release from molds

### For Organic/Artistic Shapes
- Use `loft()` and `sweep()` for smooth organic forms
- Use splines (`Spline()`) for natural curves
- Consider using `make_hull()` for organic boundaries
- Higher polygon count is acceptable for artistic pieces

### For Enclosures/Cases
- Use `shell()` to create hollow parts
- Standard wall thickness: **2-3mm**
- Add **screw bosses** (cylinders with holes) for assembly
- Include **snap-fit features** with 0.3mm interference
- Add **ventilation slots** if needed for electronics

### Units and Tolerances
- **Always use millimeters (mm)** as the base unit
- Typical 3D printer accuracy: **0.1-0.2mm**
- Minimum feature size: **0.4mm** (nozzle dependent)
- Layer height typical: **0.1-0.3mm**

## CLI Commands Reference

```bash
# Create new project from template
mcc new my_project --template mechanical

# Preview in browser (with hot-reload)
mcc preview model ./model.py

# Validate for 3D printing
mcc validate mesh ./model.py --verbose

# Export to STL
mcc export stl ./model.py -o ./model.stl --quality high

# Get model info
mcc info ./model.py

# Preview existing STL
mcc preview stl ./model.stl

# Repair broken mesh
mcc repair auto ./broken.stl -o ./fixed.stl
```

## Quality Settings for Export

| Quality | Tolerance | Use Case |
|---------|-----------|----------|
| draft | 0.1mm | Quick preview, large models |
| standard | 0.01mm | Most 3D printing |
| high | 0.001mm | Fine detail, small parts |
| ultra | 0.0001mm | Maximum precision |

## Error Handling

If validation fails:
1. Check for **non-manifold geometry** (run `mcc validate mesh --verbose`)
2. Verify **boolean operations** completed (no floating geometry)
3. Use `mcc repair auto` for automatic fixes
4. For severe issues, use `mcc repair auto --aggressive`

Common issues:
- **NOT_WATERTIGHT**: Mesh has holes - check boolean operations
- **DEGENERATE_FACES**: Zero-area triangles - simplify geometry
- **SELF_INTERSECTION**: Overlapping faces - check boolean order

## Example: Complete Workflow

```bash
# 1. User asks for a gear
# 2. Generate the model script (gear.py)
# 3. Preview it
mcc preview model ./gear.py

# 4. Validate
mcc validate mesh ./gear.py --verbose

# 5. If issues, repair
mcc repair auto ./gear.py -o ./gear_fixed.py

# 6. Export final STL
mcc export stl ./gear.py -o ./gear.stl --quality high

# Model is ready for slicing and printing!
```
