"""
Model generation module wrapping build123d for CAD operations.

This module provides a simplified API for generating 3D models using build123d,
optimized for AI-generated code from natural language descriptions.
"""

from dataclasses import dataclass, field
from typing import Optional, Union, List, Tuple, Any
from pathlib import Path
import tempfile
import io

from build123d import Part, Solid, Compound, export_stl, export_step
import trimesh
import numpy as np


@dataclass
class ModelMetadata:
    """Metadata attached to generated models."""

    name: str
    description: str = ""
    units: str = "mm"
    author: Optional[str] = None
    version: str = "1.0.0"
    tags: List[str] = field(default_factory=list)


class MichelangeloModel:
    """
    Wrapper around build123d Part with additional metadata and utilities.

    This class provides a unified interface for working with 3D models,
    including conversion to mesh format for validation and export.

    Attributes:
        part: The underlying build123d Part, Solid, or Compound object
        metadata: Model metadata including name, description, and units
    """

    def __init__(
        self,
        part: Union[Part, Solid, Compound],
        metadata: Optional[ModelMetadata] = None,
    ):
        """
        Initialize a MichelangeloModel.

        Args:
            part: A build123d Part, Solid, or Compound object
            metadata: Optional metadata for the model
        """
        self._part = part
        self.metadata = metadata or ModelMetadata(name="unnamed")
        self._mesh_cache: Optional[trimesh.Trimesh] = None
        self._mesh_tolerance: Optional[float] = None

    @property
    def part(self) -> Union[Part, Solid, Compound]:
        """Access the underlying build123d Part."""
        return self._part

    def bounding_box(self) -> Tuple[Tuple[float, float, float], Tuple[float, float, float]]:
        """
        Get model bounding box.

        Returns:
            Tuple of ((min_x, min_y, min_z), (max_x, max_y, max_z))
        """
        bbox = self._part.bounding_box()
        return (
            (bbox.min.X, bbox.min.Y, bbox.min.Z),
            (bbox.max.X, bbox.max.Y, bbox.max.Z),
        )

    def dimensions(self) -> Tuple[float, float, float]:
        """
        Get model dimensions (length, width, height).

        Returns:
            Tuple of (x_size, y_size, z_size) in model units
        """
        bbox_min, bbox_max = self.bounding_box()
        return (
            bbox_max[0] - bbox_min[0],
            bbox_max[1] - bbox_min[1],
            bbox_max[2] - bbox_min[2],
        )

    def volume(self) -> float:
        """
        Calculate model volume in cubic units.

        Returns:
            Volume in cubic units (e.g., mm^3 if units are mm)
        """
        if hasattr(self._part, "volume"):
            return self._part.volume
        # Fallback to mesh-based calculation
        mesh = self.to_mesh()
        return float(mesh.volume) if mesh.is_watertight else 0.0

    def surface_area(self) -> float:
        """
        Calculate total surface area.

        Returns:
            Surface area in square units
        """
        mesh = self.to_mesh()
        return float(mesh.area)

    def center_of_mass(self) -> Tuple[float, float, float]:
        """
        Calculate the center of mass.

        Returns:
            Tuple of (x, y, z) coordinates
        """
        if hasattr(self._part, "center"):
            c = self._part.center()
            return (c.X, c.Y, c.Z)
        mesh = self.to_mesh()
        com = mesh.center_mass
        return (float(com[0]), float(com[1]), float(com[2]))

    def to_mesh(self, tolerance: float = 0.001, angular_tolerance: float = 0.1) -> trimesh.Trimesh:
        """
        Convert to trimesh for validation/export.

        Args:
            tolerance: Linear tolerance for tessellation (chord height)
            angular_tolerance: Angular tolerance in degrees

        Returns:
            trimesh.Trimesh object
        """
        # Use cached mesh if tolerance matches
        if self._mesh_cache is not None and self._mesh_tolerance == tolerance:
            return self._mesh_cache

        # Export to STL in memory
        with tempfile.NamedTemporaryFile(suffix=".stl", delete=False) as f:
            temp_path = Path(f.name)

        try:
            export_stl(
                self._part,
                str(temp_path),
                tolerance=tolerance,
                angular_tolerance=angular_tolerance,
            )
            mesh = trimesh.load(str(temp_path))

            # Cache the mesh
            self._mesh_cache = mesh
            self._mesh_tolerance = tolerance

            return mesh
        finally:
            temp_path.unlink(missing_ok=True)

    def to_stl_bytes(self, tolerance: float = 0.001, binary: bool = True) -> bytes:
        """
        Export model to STL bytes.

        Args:
            tolerance: Tessellation tolerance
            binary: If True, export binary STL; otherwise ASCII

        Returns:
            STL file content as bytes
        """
        mesh = self.to_mesh(tolerance=tolerance)
        buffer = io.BytesIO()
        mesh.export(buffer, file_type="stl")
        return buffer.getvalue()

    def info(self) -> dict:
        """
        Get comprehensive model information.

        Returns:
            Dictionary with model statistics
        """
        dims = self.dimensions()
        mesh = self.to_mesh()

        return {
            "name": self.metadata.name,
            "description": self.metadata.description,
            "units": self.metadata.units,
            "dimensions": {"x": dims[0], "y": dims[1], "z": dims[2]},
            "volume": self.volume(),
            "surface_area": self.surface_area(),
            "triangles": len(mesh.faces),
            "vertices": len(mesh.vertices),
            "is_watertight": mesh.is_watertight,
            "bounding_box": {
                "min": self.bounding_box()[0],
                "max": self.bounding_box()[1],
            },
        }


def load_model_from_script(script_path: Path) -> MichelangeloModel:
    """
    Load a model from a Python script.

    The script should define a `model` variable containing either:
    - A MichelangeloModel instance
    - A build123d Part/Solid/Compound object

    Args:
        script_path: Path to the Python script

    Returns:
        MichelangeloModel instance

    Raises:
        ValueError: If no model found in script
        Exception: If script execution fails
    """
    script_path = Path(script_path)

    # Read and execute the script
    script_content = script_path.read_text()
    script_globals: dict[str, Any] = {}

    exec(script_content, script_globals)

    # Look for 'model' variable
    if "model" in script_globals:
        model = script_globals["model"]
        if isinstance(model, MichelangeloModel):
            return model
        elif isinstance(model, (Part, Solid, Compound)):
            return MichelangeloModel(
                part=model,
                metadata=ModelMetadata(name=script_path.stem),
            )

    # Look for 'part' variable as fallback
    if "part" in script_globals:
        part = script_globals["part"]
        if isinstance(part, (Part, Solid, Compound)):
            return MichelangeloModel(
                part=part,
                metadata=ModelMetadata(name=script_path.stem),
            )

    raise ValueError(
        f"No 'model' or 'part' variable found in {script_path}. "
        "The script should define a 'model' (MichelangeloModel) or 'part' (build123d Part) variable."
    )


def load_stl(stl_path: Path) -> trimesh.Trimesh:
    """
    Load an STL file as a trimesh.

    Args:
        stl_path: Path to STL file

    Returns:
        trimesh.Trimesh object
    """
    return trimesh.load(str(stl_path))
