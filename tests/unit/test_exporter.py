"""Tests for STL export functionality."""

import pytest
from pathlib import Path
import tempfile
import trimesh

from michelangelocc.core.exporter import (
    STLExporter,
    ExportSettings,
    ExportQuality,
    STLFormat,
)


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def exporter():
    """Create an STLExporter instance."""
    return STLExporter()


@pytest.fixture
def sample_mesh():
    """Create a sample mesh for export testing."""
    return trimesh.creation.box(extents=[10, 10, 10])


class TestExportSettings:
    """Tests for ExportSettings class."""

    def test_default_settings(self):
        """Default settings should be sensible."""
        settings = ExportSettings()

        assert settings.format == STLFormat.BINARY
        assert settings.quality == ExportQuality.STANDARD
        assert settings.validate_before_export is True
        assert settings.repair_if_invalid is True

    def test_tolerance_from_quality(self):
        """Tolerance should be derived from quality preset."""
        draft = ExportSettings(quality=ExportQuality.DRAFT)
        high = ExportSettings(quality=ExportQuality.HIGH)

        assert draft.get_tolerance() > high.get_tolerance()

    def test_custom_tolerance_overrides(self):
        """Custom tolerance should override quality preset."""
        settings = ExportSettings(
            quality=ExportQuality.DRAFT,
            tolerance=0.001
        )

        assert settings.get_tolerance() == 0.001


class TestSTLExporter:
    """Tests for STLExporter class."""

    def test_export_mesh_binary(self, exporter, sample_mesh, temp_dir):
        """Binary STL export should work."""
        output_path = temp_dir / "test.stl"

        result = exporter.export_mesh(
            sample_mesh,
            output_path,
            ExportSettings(format=STLFormat.BINARY)
        )

        assert result.success is True
        assert output_path.exists()
        assert result.file_size_bytes > 0

    def test_export_mesh_ascii(self, exporter, sample_mesh, temp_dir):
        """ASCII STL export should work."""
        output_path = temp_dir / "test_ascii.stl"

        result = exporter.export_mesh(
            sample_mesh,
            output_path,
            ExportSettings(format=STLFormat.ASCII)
        )

        assert result.success is True
        assert output_path.exists()

        # ASCII file should contain "solid" keyword
        content = output_path.read_text()
        assert "solid" in content.lower()

    def test_export_creates_parent_dirs(self, exporter, sample_mesh, temp_dir):
        """Export should create parent directories if needed."""
        output_path = temp_dir / "nested" / "dirs" / "test.stl"

        result = exporter.export_mesh(sample_mesh, output_path)

        assert result.success is True
        assert output_path.exists()

    def test_export_with_validation(self, exporter, sample_mesh, temp_dir):
        """Export should include validation results."""
        output_path = temp_dir / "test.stl"

        result = exporter.export_mesh(
            sample_mesh,
            output_path,
            ExportSettings(validate_before_export=True)
        )

        assert result.success is True
        assert result.validation_result is not None
        assert result.validation_result.is_watertight is True

    def test_export_summary(self, exporter, sample_mesh, temp_dir):
        """Export result should generate summary."""
        output_path = temp_dir / "test.stl"
        result = exporter.export_mesh(sample_mesh, output_path)

        summary = result.summary()
        assert "Export Summary" in summary
        assert "SUCCESS" in summary

    def test_binary_smaller_than_ascii(self, exporter, sample_mesh, temp_dir):
        """Binary STL should be smaller than ASCII."""
        binary_path = temp_dir / "binary.stl"
        ascii_path = temp_dir / "ascii.stl"

        exporter.export_mesh(
            sample_mesh, binary_path,
            ExportSettings(format=STLFormat.BINARY)
        )
        exporter.export_mesh(
            sample_mesh, ascii_path,
            ExportSettings(format=STLFormat.ASCII)
        )

        assert binary_path.stat().st_size < ascii_path.stat().st_size

    def test_export_without_validation(self, exporter, sample_mesh, temp_dir):
        """Export without validation should skip validation."""
        output_path = temp_dir / "test.stl"

        result = exporter.export_mesh(
            sample_mesh,
            output_path,
            ExportSettings(validate_before_export=False)
        )

        assert result.success is True
        assert result.validation_result is None

    def test_export_to_bytes(self, exporter):
        """Export to bytes should return STL data."""
        from build123d import Box
        from michelangelocc import MichelangeloModel, ModelMetadata

        part = Box(10, 10, 10)
        model = MichelangeloModel(
            part=part,
            metadata=ModelMetadata(name="test", description="test")
        )

        stl_bytes = exporter.export_to_bytes(
            model,
            ExportSettings(format=STLFormat.BINARY)
        )

        assert stl_bytes is not None
        assert len(stl_bytes) > 0

    def test_export_to_bytes_ascii(self, exporter):
        """Export to bytes in ASCII format."""
        from build123d import Box
        from michelangelocc import MichelangeloModel, ModelMetadata

        part = Box(10, 10, 10)
        model = MichelangeloModel(
            part=part,
            metadata=ModelMetadata(name="test", description="test")
        )

        stl_bytes = exporter.export_to_bytes(
            model,
            ExportSettings(format=STLFormat.ASCII)
        )

        assert stl_bytes is not None
        assert b"solid" in stl_bytes.lower()

    def test_estimate_file_size(self, exporter):
        """Estimate file size should give reasonable estimate."""
        from build123d import Box
        from michelangelocc import MichelangeloModel, ModelMetadata

        part = Box(10, 10, 10)
        model = MichelangeloModel(
            part=part,
            metadata=ModelMetadata(name="test", description="test")
        )

        estimate = exporter.estimate_file_size(model)

        assert estimate > 0

    def test_export_with_quality_presets(self, exporter, sample_mesh, temp_dir):
        """Export with different quality presets should work."""
        for quality in ExportQuality:
            output_path = temp_dir / f"test_{quality.value}.stl"

            result = exporter.export_mesh(
                sample_mesh,
                output_path,
                ExportSettings(quality=quality)
            )

            assert result.success is True
            assert output_path.exists()


class TestExportQuality:
    """Tests for ExportQuality enum."""

    def test_quality_values(self):
        """Quality enum should have expected values."""
        assert ExportQuality.DRAFT.value == "draft"
        assert ExportQuality.STANDARD.value == "standard"
        assert ExportQuality.HIGH.value == "high"
        assert ExportQuality.ULTRA.value == "ultra"


class TestSTLFormat:
    """Tests for STLFormat enum."""

    def test_format_values(self):
        """Format enum should have expected values."""
        assert STLFormat.BINARY.value == "binary"
        assert STLFormat.ASCII.value == "ascii"


class TestExportResult:
    """Tests for ExportResult class."""

    def test_summary_with_validation(self, temp_dir):
        """Summary should include validation when present."""
        from michelangelocc.core.exporter import ExportResult
        from michelangelocc.core.validator import ValidationResult

        result = ExportResult(
            success=True,
            file_path=temp_dir / "test.stl",
            file_size_bytes=1000,
            triangle_count=12,
            validation_result=ValidationResult(
                is_valid=True,
                is_watertight=True,
                is_printable=True,
                triangle_count=12,
                vertex_count=8,
                volume=1000.0,
                surface_area=600.0,
                bounding_box=((0, 0, 0), (10, 10, 10)),
            ),
            repair_result=None,
        )

        summary = result.summary()
        assert "Validation" in summary or "Valid" in summary

    def test_summary_failure(self, temp_dir):
        """Summary should indicate failure."""
        from michelangelocc.core.exporter import ExportResult

        result = ExportResult(
            success=False,
            file_path=None,
            file_size_bytes=0,
            triangle_count=0,
            validation_result=None,
            repair_result=None,
            error_message="Test error",
        )

        summary = result.summary()
        assert "FAILED" in summary
        assert "Test error" in summary
