"""Tests for mesh validation."""

import pytest
import trimesh
import numpy as np

from michelangelocc.core.validator import MeshValidator, ValidationSeverity


@pytest.fixture
def validator():
    """Create a MeshValidator instance."""
    return MeshValidator()


@pytest.fixture
def valid_cube():
    """Create a valid watertight cube mesh."""
    return trimesh.creation.box(extents=[10, 10, 10])


@pytest.fixture
def non_watertight_mesh():
    """Create a mesh with holes (not watertight)."""
    # Create a box and remove one face
    mesh = trimesh.creation.box(extents=[10, 10, 10])
    # Remove the top face by removing triangles
    mask = mesh.face_normals[:, 2] < 0.9  # Keep faces not pointing up
    mesh.update_faces(mask)
    return mesh


class TestMeshValidator:
    """Tests for MeshValidator class."""

    def test_validate_valid_mesh(self, validator, valid_cube):
        """Valid mesh should pass validation."""
        result = validator.validate(valid_cube)

        assert result.is_valid is True
        assert result.is_watertight is True
        assert result.is_printable is True
        assert result.triangle_count > 0
        assert result.vertex_count > 0
        assert result.volume is not None
        assert result.volume > 0

    def test_validate_non_watertight(self, validator, non_watertight_mesh):
        """Non-watertight mesh should fail validation."""
        result = validator.validate(non_watertight_mesh)

        assert result.is_watertight is False
        assert any(i.code == "NOT_WATERTIGHT" for i in result.issues)

    def test_bounding_box_calculation(self, validator, valid_cube):
        """Bounding box should be correctly calculated."""
        result = validator.validate(valid_cube)

        bbox_min, bbox_max = result.bounding_box
        # Box is 10x10x10 centered at origin
        assert pytest.approx(bbox_max[0] - bbox_min[0], abs=0.1) == 10.0
        assert pytest.approx(bbox_max[1] - bbox_min[1], abs=0.1) == 10.0
        assert pytest.approx(bbox_max[2] - bbox_min[2], abs=0.1) == 10.0

    def test_volume_calculation(self, validator, valid_cube):
        """Volume should be correctly calculated."""
        result = validator.validate(valid_cube)

        # 10x10x10 = 1000 cubic units
        assert result.volume is not None
        assert pytest.approx(result.volume, rel=0.01) == 1000.0

    def test_summary_generation(self, validator, valid_cube):
        """Summary should be generated correctly."""
        result = validator.validate(valid_cube)
        summary = result.summary()

        assert "Validation Summary" in summary
        assert "Valid:" in summary
        assert "Watertight:" in summary

    def test_issue_counts(self, validator, non_watertight_mesh):
        """Issue counts should be correct."""
        result = validator.validate(non_watertight_mesh)

        assert result.error_count >= 0
        assert result.warning_count >= 0
        assert len(result.issues) == result.error_count + result.warning_count + \
               sum(1 for i in result.issues if i.severity == ValidationSeverity.INFO)
