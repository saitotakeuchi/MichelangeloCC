"""
Mesh validation module for 3D printing compatibility checks.

Uses trimesh to analyze mesh geometry and identify potential issues
that could cause problems during 3D printing.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from enum import Enum
from pathlib import Path

import trimesh
import numpy as np


class ValidationSeverity(Enum):
    """Severity level of validation issues."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class ValidationIssue:
    """A single validation issue found in the mesh."""

    severity: ValidationSeverity
    code: str
    message: str
    details: Optional[dict] = None

    def __str__(self) -> str:
        return f"[{self.severity.value.upper()}] {self.code}: {self.message}"


@dataclass
class ValidationResult:
    """Complete validation result for a mesh."""

    is_valid: bool
    is_watertight: bool
    is_printable: bool
    volume: Optional[float]
    surface_area: Optional[float]
    triangle_count: int
    vertex_count: int
    bounding_box: Tuple[Tuple[float, float, float], Tuple[float, float, float]]
    issues: List[ValidationIssue] = field(default_factory=list)

    def summary(self) -> str:
        """Generate human-readable validation summary."""
        lines = [
            "=== Mesh Validation Summary ===",
            f"Valid: {'Yes' if self.is_valid else 'No'}",
            f"Watertight: {'Yes' if self.is_watertight else 'No'}",
            f"Printable: {'Yes' if self.is_printable else 'No'}",
            f"Triangles: {self.triangle_count:,}",
            f"Vertices: {self.vertex_count:,}",
        ]

        if self.volume is not None:
            lines.append(f"Volume: {self.volume:.2f} mm^3")

        if self.surface_area is not None:
            lines.append(f"Surface Area: {self.surface_area:.2f} mm^2")

        bbox_min, bbox_max = self.bounding_box
        dims = (
            bbox_max[0] - bbox_min[0],
            bbox_max[1] - bbox_min[1],
            bbox_max[2] - bbox_min[2],
        )
        lines.append(f"Dimensions: {dims[0]:.2f} x {dims[1]:.2f} x {dims[2]:.2f} mm")

        if self.issues:
            lines.append("")
            lines.append(f"Issues Found: {len(self.issues)}")
            for issue in self.issues:
                icon = {"error": "X", "warning": "!", "info": "i"}[issue.severity.value]
                lines.append(f"  [{icon}] {issue.message}")

        return "\n".join(lines)

    @property
    def error_count(self) -> int:
        """Count of error-level issues."""
        return sum(1 for i in self.issues if i.severity == ValidationSeverity.ERROR)

    @property
    def warning_count(self) -> int:
        """Count of warning-level issues."""
        return sum(1 for i in self.issues if i.severity == ValidationSeverity.WARNING)


class MeshValidator:
    """
    Validates meshes for 3D printing compatibility.

    Checks performed:
    - Watertight (manifold) mesh
    - Consistent face winding
    - No degenerate triangles
    - Volume and dimensions sanity checks
    - Printability recommendations
    """

    def __init__(
        self,
        min_wall_thickness: float = 0.8,
        min_volume: float = 0.001,
        max_dimensions: Tuple[float, float, float] = (300, 300, 300),
    ):
        """
        Initialize the validator.

        Args:
            min_wall_thickness: Minimum wall thickness in mm
            min_volume: Minimum volume in cubic mm
            max_dimensions: Maximum printable dimensions (x, y, z) in mm
        """
        self.min_wall_thickness = min_wall_thickness
        self.min_volume = min_volume
        self.max_dimensions = max_dimensions

    def validate(self, mesh: trimesh.Trimesh) -> ValidationResult:
        """
        Perform full validation of the mesh.

        Args:
            mesh: trimesh.Trimesh object to validate

        Returns:
            ValidationResult with all findings
        """
        issues: List[ValidationIssue] = []

        # Basic mesh properties
        is_watertight = bool(mesh.is_watertight)
        triangle_count = len(mesh.faces)
        vertex_count = len(mesh.vertices)

        # Bounding box
        bounds = mesh.bounds
        bounding_box = (
            (float(bounds[0][0]), float(bounds[0][1]), float(bounds[0][2])),
            (float(bounds[1][0]), float(bounds[1][1]), float(bounds[1][2])),
        )

        # Volume (only valid if watertight)
        volume: Optional[float] = None
        if is_watertight:
            volume = float(mesh.volume)
        else:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="NOT_WATERTIGHT",
                    message="Mesh is not watertight (has holes or non-manifold edges)",
                    details={"is_watertight": False},
                )
            )

        # Surface area
        surface_area = float(mesh.area)

        # Check for watertight issues
        watertight_issues = self._check_watertight(mesh)
        issues.extend(watertight_issues)

        # Check for degenerate faces
        degenerate_issues = self._check_degenerate_faces(mesh)
        issues.extend(degenerate_issues)

        # Check face winding consistency
        winding_issues = self._check_winding(mesh)
        issues.extend(winding_issues)

        # Check printability
        printability_issues = self._check_printability(mesh, volume)
        issues.extend(printability_issues)

        # Determine overall validity
        has_errors = any(i.severity == ValidationSeverity.ERROR for i in issues)
        is_valid = not has_errors
        is_printable = is_watertight and not has_errors

        return ValidationResult(
            is_valid=is_valid,
            is_watertight=is_watertight,
            is_printable=is_printable,
            volume=volume,
            surface_area=surface_area,
            triangle_count=triangle_count,
            vertex_count=vertex_count,
            bounding_box=bounding_box,
            issues=issues,
        )

    def _check_watertight(self, mesh: trimesh.Trimesh) -> List[ValidationIssue]:
        """Check for watertight-related issues."""
        issues = []

        # Check for holes (boundary edges)
        if hasattr(mesh, "edges_unique") and hasattr(mesh, "faces"):
            # Count edges that appear in only one face (boundary edges)
            edges = mesh.edges_sorted
            unique_edges, counts = np.unique(edges, axis=0, return_counts=True)
            boundary_count = np.sum(counts == 1)

            if boundary_count > 0:
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        code="BOUNDARY_EDGES",
                        message=f"Found {boundary_count} boundary edges (indicates holes)",
                        details={"boundary_edge_count": int(boundary_count)},
                    )
                )

        return issues

    def _check_degenerate_faces(self, mesh: trimesh.Trimesh) -> List[ValidationIssue]:
        """Check for degenerate (zero-area) triangles."""
        issues = []

        # Check for zero-area faces
        face_areas = mesh.area_faces
        degenerate_count = np.sum(face_areas < 1e-10)

        if degenerate_count > 0:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    code="DEGENERATE_FACES",
                    message=f"Found {degenerate_count} degenerate (zero-area) triangles",
                    details={"degenerate_count": int(degenerate_count)},
                )
            )

        return issues

    def _check_winding(self, mesh: trimesh.Trimesh) -> List[ValidationIssue]:
        """Check face winding consistency."""
        issues = []

        # trimesh provides face normal consistency check
        if hasattr(mesh, "is_winding_consistent"):
            if not mesh.is_winding_consistent:
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        code="INCONSISTENT_WINDING",
                        message="Face winding is not consistent (normals may be inverted)",
                    )
                )

        return issues

    def _check_printability(
        self, mesh: trimesh.Trimesh, volume: Optional[float]
    ) -> List[ValidationIssue]:
        """Check 3D printing specific requirements."""
        issues = []

        # Check minimum volume
        if volume is not None and volume < self.min_volume:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    code="SMALL_VOLUME",
                    message=f"Volume ({volume:.6f} mm^3) is below minimum ({self.min_volume} mm^3)",
                    details={"volume": volume, "min_volume": self.min_volume},
                )
            )

        # Check dimensions against max build volume
        bounds = mesh.bounds
        dims = bounds[1] - bounds[0]

        for i, (dim, max_dim, axis) in enumerate(
            zip(dims, self.max_dimensions, ["X", "Y", "Z"])
        ):
            if dim > max_dim:
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        code="EXCEEDS_BUILD_VOLUME",
                        message=f"{axis} dimension ({dim:.1f}mm) exceeds max build size ({max_dim}mm)",
                        details={"axis": axis, "size": float(dim), "max_size": max_dim},
                    )
                )

        # Check for very thin parts (rough estimation)
        if volume is not None and mesh.area > 0:
            avg_thickness = volume / mesh.area
            if avg_thickness < self.min_wall_thickness / 10:
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.INFO,
                        code="POSSIBLY_THIN",
                        message=f"Model may have thin walls (avg thickness estimate: {avg_thickness:.3f}mm)",
                        details={"avg_thickness": float(avg_thickness)},
                    )
                )

        return issues

    def validate_file(self, file_path: Path) -> ValidationResult:
        """
        Validate a mesh from a file.

        Args:
            file_path: Path to STL or other mesh file

        Returns:
            ValidationResult
        """
        mesh = trimesh.load(str(file_path))
        return self.validate(mesh)
