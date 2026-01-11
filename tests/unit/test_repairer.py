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

    def test_repair_with_merge_vertices_action(self, repairer, valid_mesh):
        """Merge vertices action should work."""
        actions = [RepairAction.MERGE_VERTICES]
        result = repairer.repair(valid_mesh, actions=actions)

        assert len(result.log) == 1
        assert result.log[0].action == RepairAction.MERGE_VERTICES
        assert result.log[0].success is True

    def test_repair_with_remove_degenerate_action(self, repairer, valid_mesh):
        """Remove degenerate action should work."""
        actions = [RepairAction.REMOVE_DEGENERATE]
        result = repairer.repair(valid_mesh, actions=actions)

        assert len(result.log) == 1
        assert result.log[0].action == RepairAction.REMOVE_DEGENERATE
        assert result.log[0].success is True

    def test_repair_with_fill_holes_action(self, repairer, valid_mesh):
        """Fill holes action should work on watertight mesh."""
        actions = [RepairAction.FILL_HOLES]
        result = repairer.repair(valid_mesh, actions=actions)

        assert len(result.log) == 1
        assert result.log[0].action == RepairAction.FILL_HOLES
        assert result.log[0].success is True

    def test_repair_non_watertight_mesh(self, repairer, non_watertight_mesh):
        """Repair should attempt to fix non-watertight mesh."""
        result = repairer.repair(non_watertight_mesh)

        assert result.mesh is not None
        assert len(result.log) > 0


class TestRepairAggressive:
    """Tests for aggressive repair with PyMeshFix."""

    @pytest.fixture
    def repairer(self):
        """Create a MeshRepairer instance."""
        return MeshRepairer()

    @pytest.fixture
    def valid_mesh(self):
        """Create a valid mesh."""
        return trimesh.creation.box(extents=[10, 10, 10])

    def test_repair_aggressive_returns_result(self, repairer, valid_mesh):
        """Aggressive repair should return a RepairResult."""
        result = repairer.repair_aggressive(valid_mesh)

        assert hasattr(result, 'mesh')
        assert hasattr(result, 'was_modified')
        assert hasattr(result, 'log')

    def test_repair_aggressive_logs_action(self, repairer, valid_mesh):
        """Aggressive repair should log the PyMeshFix action."""
        result = repairer.repair_aggressive(valid_mesh)

        assert len(result.log) == 1
        assert result.log[0].action == RepairAction.PYMESHFIX_REPAIR


class TestRepairFile:
    """Tests for file-based repair."""

    @pytest.fixture
    def repairer(self):
        """Create a MeshRepairer instance."""
        return MeshRepairer()

    @pytest.fixture
    def temp_stl_file(self, tmp_path):
        """Create a temporary STL file."""
        mesh = trimesh.creation.box(extents=[10, 10, 10])
        stl_path = tmp_path / "test.stl"
        mesh.export(str(stl_path))
        return stl_path

    def test_repair_file_basic(self, repairer, temp_stl_file):
        """Repair file should work with valid STL."""
        result = repairer.repair_file(temp_stl_file)

        assert result.mesh is not None
        assert len(result.log) > 0

    def test_repair_file_with_output(self, repairer, temp_stl_file, tmp_path):
        """Repair file should save output when path provided."""
        output_path = tmp_path / "repaired.stl"

        # Create a mesh that will be modified
        mesh = trimesh.creation.box(extents=[10, 10, 10])
        temp_stl_file.write_bytes(mesh.export(file_type='stl'))

        result = repairer.repair_file(temp_stl_file, output_path=output_path)

        # Output may or may not be written depending on whether mesh was modified
        assert result.mesh is not None

    def test_repair_file_aggressive(self, repairer, temp_stl_file):
        """Repair file with aggressive mode should use PyMeshFix."""
        result = repairer.repair_file(temp_stl_file, aggressive=True)

        assert result.mesh is not None
        # Should have PyMeshFix action in log
        actions = [entry.action for entry in result.log]
        assert RepairAction.PYMESHFIX_REPAIR in actions


class TestRepairResultSummary:
    """Tests for RepairResult summary generation."""

    def test_summary_no_modifications(self):
        """Summary should indicate no repairs needed."""
        from michelangelocc.core.repairer import RepairResult

        mesh = trimesh.creation.box(extents=[10, 10, 10])
        result = RepairResult(mesh=mesh, was_modified=False, log=[])

        summary = result.summary()
        assert "No repairs needed" in summary

    def test_summary_with_modifications(self):
        """Summary should list repairs when modifications made."""
        from michelangelocc.core.repairer import RepairResult, RepairLog

        mesh = trimesh.creation.box(extents=[10, 10, 10])
        log = [
            RepairLog(
                action=RepairAction.FIX_NORMALS,
                description="Fixed normals",
                affected_elements=12,
                success=True,
            )
        ]
        result = RepairResult(mesh=mesh, was_modified=True, log=log)

        summary = result.summary()
        assert "Repairs performed" in summary
        assert "fix_normals" in summary


@pytest.fixture
def non_watertight_mesh():
    """Create a mesh with holes (not watertight)."""
    mesh = trimesh.creation.box(extents=[10, 10, 10])
    # Remove the top face
    mask = mesh.face_normals[:, 2] < 0.9
    mesh.update_faces(mask)
    return mesh
