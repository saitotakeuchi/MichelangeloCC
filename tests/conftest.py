"""Shared test fixtures."""

import pytest
from pathlib import Path
import tempfile


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_script(temp_dir):
    """Create a sample model script."""
    script = temp_dir / "sample.py"
    script.write_text('''
from build123d import *
from michelangelocc import MichelangeloModel, ModelMetadata

part = Box(20, 20, 20)

model = MichelangeloModel(
    part=part,
    metadata=ModelMetadata(name="test_box", description="Test box")
)
''')
    return script


@pytest.fixture
def sample_stl(temp_dir):
    """Create a sample STL file."""
    import trimesh

    # Create a simple cube mesh
    mesh = trimesh.creation.box(extents=[10, 10, 10])
    stl_path = temp_dir / "sample.stl"
    mesh.export(str(stl_path))
    return stl_path


@pytest.fixture
def valid_mesh():
    """Create a valid watertight mesh."""
    import trimesh
    return trimesh.creation.box(extents=[10, 10, 10])


@pytest.fixture
def disconnected_mesh():
    """Create a mesh with two separate cubes (disconnected parts)."""
    import trimesh

    box1 = trimesh.creation.box(extents=[10, 10, 10])
    box2 = trimesh.creation.box(extents=[10, 10, 10])
    box2.apply_translation([50, 0, 0])  # Move far away
    return trimesh.util.concatenate([box1, box2])


@pytest.fixture
def non_watertight_mesh():
    """Create a mesh with holes (not watertight)."""
    import trimesh

    # Create a box and remove one face
    mesh = trimesh.creation.box(extents=[10, 10, 10])
    # Remove the top face by filtering triangles
    mask = mesh.face_normals[:, 2] < 0.9  # Keep faces not pointing up
    mesh.update_faces(mask)
    return mesh
