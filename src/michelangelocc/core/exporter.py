"""
STL export module with quality control and validation.

Handles exporting models to STL format with configurable quality settings,
pre-export validation, and optional auto-repair.
"""

from dataclasses import dataclass
from typing import Optional
from pathlib import Path
from enum import Enum
import io

import trimesh

from michelangelocc.core.modeler import MichelangeloModel
from michelangelocc.core.validator import MeshValidator, ValidationResult
from michelangelocc.core.repairer import MeshRepairer, RepairResult


class STLFormat(Enum):
    """STL file format options."""

    BINARY = "binary"
    ASCII = "ascii"


class ExportQuality(Enum):
    """Preset quality levels for STL export."""

    DRAFT = "draft"  # Fast, large tolerance (0.1mm)
    STANDARD = "standard"  # Balanced (0.01mm)
    HIGH = "high"  # Fine detail (0.001mm)
    ULTRA = "ultra"  # Maximum detail (0.0001mm)


# Quality preset tolerances
QUALITY_TOLERANCES = {
    ExportQuality.DRAFT: 0.1,
    ExportQuality.STANDARD: 0.01,
    ExportQuality.HIGH: 0.001,
    ExportQuality.ULTRA: 0.0001,
}


@dataclass
class ExportSettings:
    """Configuration for STL export."""

    format: STLFormat = STLFormat.BINARY
    quality: ExportQuality = ExportQuality.STANDARD
    tolerance: Optional[float] = None  # Override quality preset
    angular_tolerance: Optional[float] = None
    validate_before_export: bool = True
    repair_if_invalid: bool = True

    def get_tolerance(self) -> float:
        """Get effective tolerance value."""
        if self.tolerance is not None:
            return self.tolerance
        return QUALITY_TOLERANCES[self.quality]

    def get_angular_tolerance(self) -> float:
        """Get effective angular tolerance in degrees."""
        if self.angular_tolerance is not None:
            return self.angular_tolerance
        # Default angular tolerances based on quality
        angular_presets = {
            ExportQuality.DRAFT: 15.0,
            ExportQuality.STANDARD: 5.0,
            ExportQuality.HIGH: 1.0,
            ExportQuality.ULTRA: 0.5,
        }
        return angular_presets[self.quality]


@dataclass
class ExportResult:
    """Result of export operation."""

    success: bool
    file_path: Optional[Path]
    file_size_bytes: int
    triangle_count: int
    validation_result: Optional[ValidationResult]
    repair_result: Optional[RepairResult]
    error_message: Optional[str] = None

    def summary(self) -> str:
        """Generate human-readable export summary."""
        lines = ["=== Export Summary ==="]

        if self.success:
            lines.append(f"Status: SUCCESS")
            lines.append(f"Output: {self.file_path}")
            lines.append(f"File Size: {self._format_size(self.file_size_bytes)}")
            lines.append(f"Triangles: {self.triangle_count:,}")
        else:
            lines.append(f"Status: FAILED")
            if self.error_message:
                lines.append(f"Error: {self.error_message}")

        if self.validation_result:
            lines.append("")
            lines.append(f"Validation: {'PASSED' if self.validation_result.is_valid else 'FAILED'}")
            lines.append(f"Watertight: {'Yes' if self.validation_result.is_watertight else 'No'}")

        if self.repair_result and self.repair_result.was_modified:
            lines.append("")
            lines.append("Repairs Applied: Yes")

        return "\n".join(lines)

    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """Format file size for display."""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        else:
            return f"{size_bytes / (1024 * 1024):.2f} MB"


class STLExporter:
    """
    Export models to STL format with quality control.

    Features:
    - Binary or ASCII STL output
    - Configurable tessellation quality
    - Pre-export validation
    - Automatic repair option
    - File integrity verification
    """

    def __init__(self, settings: Optional[ExportSettings] = None):
        """
        Initialize the exporter.

        Args:
            settings: Export settings (uses defaults if not provided)
        """
        self.settings = settings or ExportSettings()
        self.validator = MeshValidator()
        self.repairer = MeshRepairer()

    def export(
        self,
        model: MichelangeloModel,
        output_path: Path,
        settings: Optional[ExportSettings] = None,
    ) -> ExportResult:
        """
        Export model to STL file.

        Performs validation and optional repair before export.

        Args:
            model: MichelangeloModel to export
            output_path: Path to output STL file
            settings: Optional settings override

        Returns:
            ExportResult with export status and details
        """
        settings = settings or self.settings
        output_path = Path(output_path)

        # Convert to mesh
        tolerance = settings.get_tolerance()
        angular_tolerance = settings.get_angular_tolerance()

        try:
            mesh = model.to_mesh(
                tolerance=tolerance,
                angular_tolerance=angular_tolerance,
            )
        except Exception as e:
            return ExportResult(
                success=False,
                file_path=None,
                file_size_bytes=0,
                triangle_count=0,
                validation_result=None,
                repair_result=None,
                error_message=f"Failed to convert model to mesh: {str(e)}",
            )

        # Validate if requested
        validation_result: Optional[ValidationResult] = None
        repair_result: Optional[RepairResult] = None

        if settings.validate_before_export:
            validation_result = self.validator.validate(mesh)

            # Repair if invalid and repair is enabled
            if not validation_result.is_valid and settings.repair_if_invalid:
                repair_result = self.repairer.repair(mesh)
                mesh = repair_result.mesh

                # Re-validate after repair
                validation_result = self.validator.validate(mesh)

        # Export
        try:
            # Ensure parent directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Export based on format
            if settings.format == STLFormat.BINARY:
                mesh.export(str(output_path), file_type="stl")
            else:
                # ASCII export
                mesh.export(str(output_path), file_type="stl_ascii")

            file_size = output_path.stat().st_size

            return ExportResult(
                success=True,
                file_path=output_path,
                file_size_bytes=file_size,
                triangle_count=len(mesh.faces),
                validation_result=validation_result,
                repair_result=repair_result,
            )

        except Exception as e:
            return ExportResult(
                success=False,
                file_path=None,
                file_size_bytes=0,
                triangle_count=len(mesh.faces),
                validation_result=validation_result,
                repair_result=repair_result,
                error_message=f"Failed to write STL file: {str(e)}",
            )

    def export_mesh(
        self,
        mesh: trimesh.Trimesh,
        output_path: Path,
        settings: Optional[ExportSettings] = None,
    ) -> ExportResult:
        """
        Export a trimesh directly to STL.

        Args:
            mesh: trimesh.Trimesh to export
            output_path: Path to output file
            settings: Optional settings override

        Returns:
            ExportResult
        """
        settings = settings or self.settings
        output_path = Path(output_path)

        validation_result: Optional[ValidationResult] = None
        repair_result: Optional[RepairResult] = None

        if settings.validate_before_export:
            validation_result = self.validator.validate(mesh)

            if not validation_result.is_valid and settings.repair_if_invalid:
                repair_result = self.repairer.repair(mesh)
                mesh = repair_result.mesh
                validation_result = self.validator.validate(mesh)

        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)

            if settings.format == STLFormat.BINARY:
                mesh.export(str(output_path), file_type="stl")
            else:
                mesh.export(str(output_path), file_type="stl_ascii")

            file_size = output_path.stat().st_size

            return ExportResult(
                success=True,
                file_path=output_path,
                file_size_bytes=file_size,
                triangle_count=len(mesh.faces),
                validation_result=validation_result,
                repair_result=repair_result,
            )

        except Exception as e:
            return ExportResult(
                success=False,
                file_path=None,
                file_size_bytes=0,
                triangle_count=len(mesh.faces),
                validation_result=validation_result,
                repair_result=repair_result,
                error_message=str(e),
            )

    def export_to_bytes(
        self,
        model: MichelangeloModel,
        settings: Optional[ExportSettings] = None,
    ) -> bytes:
        """
        Export model to STL bytes (for in-memory use).

        Args:
            model: MichelangeloModel to export
            settings: Optional settings override

        Returns:
            STL file content as bytes
        """
        settings = settings or self.settings
        tolerance = settings.get_tolerance()

        mesh = model.to_mesh(tolerance=tolerance)

        buffer = io.BytesIO()
        if settings.format == STLFormat.BINARY:
            mesh.export(buffer, file_type="stl")
        else:
            mesh.export(buffer, file_type="stl_ascii")

        return buffer.getvalue()

    def estimate_file_size(
        self,
        model: MichelangeloModel,
        settings: Optional[ExportSettings] = None,
    ) -> int:
        """
        Estimate output file size in bytes.

        Args:
            model: MichelangeloModel
            settings: Optional settings override

        Returns:
            Estimated file size in bytes
        """
        settings = settings or self.settings
        mesh = model.to_mesh(tolerance=settings.get_tolerance())

        # Binary STL: 84 byte header + 50 bytes per triangle
        # ASCII STL: ~200 bytes per triangle (rough estimate)
        triangle_count = len(mesh.faces)

        if settings.format == STLFormat.BINARY:
            return 84 + (50 * triangle_count)
        else:
            return 200 * triangle_count
