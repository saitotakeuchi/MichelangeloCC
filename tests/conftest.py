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
    import numpy as np

    # Create a simple cube mesh
    mesh = trimesh.creation.box(extents=[10, 10, 10])
    stl_path = temp_dir / "sample.stl"
    mesh.export(str(stl_path))
    return stl_path
