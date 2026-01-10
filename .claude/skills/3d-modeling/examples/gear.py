"""
Model: Parametric Spur Gear
Description: A parametric spur gear with configurable tooth count and dimensions
Author: Claude Code
Units: mm (millimeters)
"""

from build123d import *
from michelangelocc import MichelangeloModel, ModelMetadata
import math


# === Parameters ===
# Gear specifications
num_teeth = 20              # Number of teeth
module = 2.0                # Module (tooth size) in mm
pressure_angle = 20.0       # Pressure angle in degrees
gear_height = 10.0          # Thickness of gear in mm

# Shaft hole
shaft_diameter = 8.0        # Center hole diameter in mm
keyway_width = 3.0          # Keyway width (set to 0 to disable)
keyway_depth = 1.5          # Keyway depth

# Hub (optional raised center)
hub_diameter = 20.0         # Hub outer diameter (0 to disable)
hub_height = 5.0            # Hub height above gear face

# === Derived Parameters ===
pitch_diameter = module * num_teeth
base_diameter = pitch_diameter * math.cos(math.radians(pressure_angle))
outer_diameter = pitch_diameter + 2 * module
root_diameter = pitch_diameter - 2.5 * module

# Tooth geometry
tooth_thickness = math.pi * module / 2
addendum = module
dedendum = 1.25 * module


# === Helper Functions ===
def involute_point(base_radius: float, angle: float) -> tuple:
    """Calculate point on involute curve."""
    x = base_radius * (math.cos(angle) + angle * math.sin(angle))
    y = base_radius * (math.sin(angle) - angle * math.cos(angle))
    return (x, y)


def create_tooth_profile(base_r: float, outer_r: float, root_r: float) -> list:
    """Create a single tooth profile as a list of points."""
    points = []

    # Root to base (straight radial line if base > root)
    if base_r > root_r:
        points.append((root_r, 0))
        points.append((base_r, 0))

    # Involute curve from base to outer
    max_angle = math.sqrt((outer_r / base_r) ** 2 - 1)
    num_points = 10

    for i in range(num_points + 1):
        angle = i * max_angle / num_points
        x, y = involute_point(base_r, angle)
        if math.sqrt(x**2 + y**2) <= outer_r:
            points.append((x, y))

    return points


# === Model Construction ===
# Create base cylinder at root diameter
part = Cylinder(root_diameter / 2, gear_height)

# Create gear teeth using simplified approach
# For a proper involute gear, we'd use the involute profile
# Here we use a simplified trapezoidal tooth for demonstration

tooth_angle = 360 / num_teeth
half_tooth_angle = tooth_angle / 2 * 0.4  # Tooth takes ~40% of pitch

with BuildPart() as gear_builder:
    # Base cylinder
    Cylinder(root_diameter / 2, gear_height)

    # Add teeth
    for i in range(num_teeth):
        angle = i * tooth_angle
        angle_rad = math.radians(angle)

        # Create tooth as extruded trapezoid
        with BuildSketch(Plane.XY.rotated((0, 0, angle))):
            # Tooth profile (simplified trapezoid)
            with BuildLine():
                # Start at root
                start_x = root_diameter / 2
                mid_x = pitch_diameter / 2
                end_x = outer_diameter / 2

                # Tooth width at different radii
                root_half_width = math.radians(half_tooth_angle * 1.2) * root_diameter / 2
                pitch_half_width = math.radians(half_tooth_angle) * pitch_diameter / 2
                tip_half_width = math.radians(half_tooth_angle * 0.6) * outer_diameter / 2

                Polyline([
                    (start_x, -root_half_width),
                    (end_x, -tip_half_width),
                    (end_x, tip_half_width),
                    (start_x, root_half_width),
                ])
                Line((start_x, root_half_width), (start_x, -root_half_width))

            make_face()

        extrude(amount=gear_height, mode=Mode.ADD)

    part = gear_builder.part

# Alternative simpler approach using RegularPolygon approximation
# Uncomment below for a simpler gear shape:
# part = Cylinder(outer_diameter / 2, gear_height)

# Subtract center hole
part -= Cylinder(shaft_diameter / 2, gear_height * 2)

# Add keyway if specified
if keyway_width > 0:
    keyway = Pos(shaft_diameter / 2 + keyway_depth / 2, 0, 0) * Box(
        keyway_depth, keyway_width, gear_height * 2
    )
    part -= keyway

# Add hub if specified
if hub_diameter > 0 and hub_height > 0:
    hub = Pos(0, 0, gear_height / 2 + hub_height / 2) * Cylinder(
        hub_diameter / 2, hub_height
    )
    hub -= Cylinder(shaft_diameter / 2, hub_height * 2)
    if keyway_width > 0:
        hub -= Pos(shaft_diameter / 2 + keyway_depth / 2, 0, 0) * Box(
            keyway_depth, keyway_width, hub_height * 2
        )
    part += hub

# Chamfer top edges for easier printing
# part = chamfer(part.edges().filter_by(Axis.Z).sort_by(Axis.Z)[-4:], 0.5)


# === Export ===
model = MichelangeloModel(
    part=part,
    metadata=ModelMetadata(
        name="parametric_gear",
        description=f"Spur gear with {num_teeth} teeth, module {module}mm",
        units="mm",
        tags=["gear", "mechanical", "parametric"]
    )
)
