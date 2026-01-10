"""Tests for mesh repair functionality."""

import pytest
import trimesh
import numpy as np

from michelangelocc.core.repairer import MeshRepairer, RepairAction


@pytest.fixture
def repairer():
    """Create a MeshRepairer instance."""
    return MeshRepairer()


@pytest.fixture
def valid_mesh():
    """Create a valid mesh that doesn't need repair."""
    return trimesh.creation.box(extents=[10, 10, 10])


@pytest.fixture
def mesh_with_duplicates():
    """Create a mesh with duplicate vertices."""
    mesh = trimesh.creation.box(extents=[10, 10, 10])
    # Duplicate vertices by adding very close points
    extra_vertices = mesh.vertices + np.random.uniform(-1e-9, 1e-9, mesh.vertices.shape)
    mesh.vertices = np.vstack([mesh.vertices, extra_vertices])
    return mesh


class TestMeshRepairer:
    """Tests for MeshRepairer class."""

    def test_repair_valid_mesh(self, repairer, valid_mesh):
        """Valid mesh should not need significant repairs."""
        result = repairer.repair(valid_mesh)

        # Should still return a valid mesh
        assert result.mesh is not None
        assert result.mesh.is_watertight

    def test_repair_returns_result(self, repairer, valid_mesh):
        """Repair should return a RepairResult."""
        result = repairer.repair(valid_mesh)

        assert hasattr(result, 'mesh')
        assert hasattr(result, 'was_modified')
        assert hasattr(result, 'log')

    def test_repair_log_entries(self, repairer, valid_mesh):
        """Repair should log all actions taken."""
        result = repairer.repair(valid_mesh)

        assert len(result.log) > 0
        for entry in result.log:
            assert hasattr(entry, 'action')
            assert hasattr(entry, 'description')
            assert hasattr(entry, 'success')

    def test_specific_actions(self, repairer, valid_mesh):
        """Specific repair actions should work."""
        actions = [RepairAction.FIX_NORMALS]
        result = repairer.repair(valid_mesh, actions=actions)

        assert len(result.log) == 1
        assert result.log[0].action == RepairAction.FIX_NORMALS

    def test_summary_generation(self, repairer, valid_mesh):
        """Summary should be generated correctly."""
        result = repairer.repair(valid_mesh)
        summary = result.summary()

        assert "Repair Summary" in summary
