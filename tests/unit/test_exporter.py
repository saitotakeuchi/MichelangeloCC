"""Tests for STL export functionality."""

import pytest
from pathlib import Path
import trimesh

from michelangelocc.core.exporter import (
    STLExporter,
    ExportSettings,
    ExportQuality,
    STLFormat,
)


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
