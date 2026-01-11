"""Tests for model generation module."""

import pytest
from pathlib import Path
import tempfile

from build123d import Box, Cylinder, Part, Solid
import trimesh

from michelangelocc.core.modeler import (
    ModelMetadata,
    MichelangeloModel,
    load_model_from_script,
    load_stl,
)


class TestModelMetadata:
    """Tests for ModelMetadata dataclass."""

    def test_default_values(self):
        """Test default values are set correctly."""
        metadata = ModelMetadata(name="test")

        assert metadata.name == "test"
        assert metadata.description == ""
        assert metadata.units == "mm"
        assert metadata.author is None
        assert metadata.version == "1.0.0"
        assert metadata.tags == []

    def test_custom_values(self):
        """Test custom values are preserved."""
        metadata = ModelMetadata(
            name="custom_model",
            description="A custom model",
            units="inches",
            author="Test Author",
            version="2.0.0",
            tags=["mechanical", "bracket"],
        )

        assert metadata.name == "custom_model"
        assert metadata.description == "A custom model"
        assert metadata.units == "inches"
        assert metadata.author == "Test Author"
        assert metadata.version == "2.0.0"
        assert metadata.tags == ["mechanical", "bracket"]

    def test_optional_fields(self):
        """Test that optional fields can be None."""
        metadata = ModelMetadata(name="minimal", author=None)

        assert metadata.author is None


class TestMichelangeloModel:
    """Tests for MichelangeloModel class."""

    @pytest.fixture
    def simple_box(self):
        """Create a simple 20x20x20 box."""
        return Box(20, 20, 20)

    @pytest.fixture
    def model_with_metadata(self, simple_box):
        """Create a model with full metadata."""
        return MichelangeloModel(
            part=simple_box,
            metadata=ModelMetadata(
                name="test_box",
                description="A test box",
                units="mm",
            ),
        )

    @pytest.fixture
    def model_without_metadata(self, simple_box):
        """Create a model without explicit metadata."""
        return MichelangeloModel(part=simple_box)

    def test_init_with_valid_part(self, simple_box):
        """Model should initialize with valid part."""
        model = MichelangeloModel(part=simple_box)

        assert model.part is not None
        assert model.metadata.name == "unnamed"

    def test_init_with_metadata(self, model_with_metadata):
        """Model should preserve metadata."""
        assert model_with_metadata.metadata.name == "test_box"
        assert model_with_metadata.metadata.description == "A test box"

    def test_part_property(self, model_with_metadata, simple_box):
        """Part property should return the underlying part."""
        assert model_with_metadata.part is simple_box

    def test_bounding_box(self, model_with_metadata):
        """Bounding box should be correctly calculated."""
        bbox_min, bbox_max = model_with_metadata.bounding_box()

        # 20x20x20 box centered at origin: -10 to 10 on each axis
        assert pytest.approx(bbox_min[0], abs=0.1) == -10.0
        assert pytest.approx(bbox_min[1], abs=0.1) == -10.0
        assert pytest.approx(bbox_min[2], abs=0.1) == -10.0
        assert pytest.approx(bbox_max[0], abs=0.1) == 10.0
        assert pytest.approx(bbox_max[1], abs=0.1) == 10.0
        assert pytest.approx(bbox_max[2], abs=0.1) == 10.0

    def test_dimensions(self, model_with_metadata):
        """Dimensions should be correctly calculated."""
        dims = model_with_metadata.dimensions()

        # 20x20x20 box
        assert pytest.approx(dims[0], abs=0.1) == 20.0
        assert pytest.approx(dims[1], abs=0.1) == 20.0
        assert pytest.approx(dims[2], abs=0.1) == 20.0

    def test_volume(self, model_with_metadata):
        """Volume should be correctly calculated."""
        volume = model_with_metadata.volume()

        # 20x20x20 = 8000 cubic mm
        assert pytest.approx(volume, rel=0.01) == 8000.0

    def test_surface_area(self, model_with_metadata):
        """Surface area should be correctly calculated."""
        area = model_with_metadata.surface_area()

        # 6 faces * 20*20 = 2400 square mm
        assert pytest.approx(area, rel=0.05) == 2400.0

    def test_center_of_mass(self, model_with_metadata):
        """Center of mass should be at origin for symmetric box."""
        com = model_with_metadata.center_of_mass()

        assert pytest.approx(com[0], abs=0.1) == 0.0
        assert pytest.approx(com[1], abs=0.1) == 0.0
        assert pytest.approx(com[2], abs=0.1) == 0.0

    def test_to_mesh(self, model_with_metadata):
        """to_mesh should return valid trimesh object."""
        mesh = model_with_metadata.to_mesh()

        assert isinstance(mesh, trimesh.Trimesh)
        assert len(mesh.vertices) > 0
        assert len(mesh.faces) > 0
        assert mesh.is_watertight

    def test_to_mesh_caching(self, model_with_metadata):
        """Mesh should be cached for same tolerance."""
        mesh1 = model_with_metadata.to_mesh(tolerance=0.01)
        mesh2 = model_with_metadata.to_mesh(tolerance=0.01)

        # Same object should be returned (cached)
        assert mesh1 is mesh2

    def test_to_mesh_tolerance_invalidates_cache(self, model_with_metadata):
        """Different tolerance should invalidate cache."""
        mesh1 = model_with_metadata.to_mesh(tolerance=0.01)
        mesh2 = model_with_metadata.to_mesh(tolerance=0.001)

        # Different tolerance means different mesh (not cached)
        assert mesh1 is not mesh2

    def test_to_stl_bytes(self, model_with_metadata):
        """to_stl_bytes should return valid STL bytes."""
        stl_bytes = model_with_metadata.to_stl_bytes()

        assert isinstance(stl_bytes, bytes)
        assert len(stl_bytes) > 0
        # Binary STL starts with 80-byte header
        assert len(stl_bytes) >= 84

    def test_to_stl_bytes_binary(self, model_with_metadata):
        """Binary STL should be returned by default."""
        stl_bytes = model_with_metadata.to_stl_bytes(binary=True)

        # Binary STL has specific structure
        assert len(stl_bytes) >= 84

    def test_info_returns_dict(self, model_with_metadata):
        """info() should return complete dictionary."""
        info = model_with_metadata.info()

        assert isinstance(info, dict)
        assert "name" in info
        assert "description" in info
        assert "units" in info
        assert "dimensions" in info
        assert "volume" in info
        assert "surface_area" in info
        assert "triangles" in info
        assert "vertices" in info
        assert "is_watertight" in info
        assert "bounding_box" in info

    def test_info_values(self, model_with_metadata):
        """info() should return correct values."""
        info = model_with_metadata.info()

        assert info["name"] == "test_box"
        assert info["description"] == "A test box"
        assert info["units"] == "mm"
        assert pytest.approx(info["dimensions"]["x"], abs=0.1) == 20.0
        assert pytest.approx(info["volume"], rel=0.01) == 8000.0
        assert info["triangles"] > 0
        assert info["is_watertight"] is True


class TestLoadModelFromScript:
    """Tests for load_model_from_script function."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_load_valid_script_with_model(self, temp_dir):
        """Load script with MichelangeloModel variable."""
        script = temp_dir / "model.py"
        script.write_text('''
from build123d import Box
from michelangelocc import MichelangeloModel, ModelMetadata

part = Box(10, 10, 10)
model = MichelangeloModel(
    part=part,
    metadata=ModelMetadata(name="loaded_model")
)
''')
        loaded = load_model_from_script(script)

        assert isinstance(loaded, MichelangeloModel)
        assert loaded.metadata.name == "loaded_model"

    def test_load_valid_script_with_part(self, temp_dir):
        """Load script with 'part' variable (fallback)."""
        script = temp_dir / "part_only.py"
        script.write_text('''
from build123d import Box

part = Box(15, 15, 15)
''')
        loaded = load_model_from_script(script)

        assert isinstance(loaded, MichelangeloModel)
        assert loaded.metadata.name == "part_only"
        dims = loaded.dimensions()
        assert pytest.approx(dims[0], abs=0.1) == 15.0

    def test_load_script_not_found(self, temp_dir):
        """Should raise error for non-existent script."""
        fake_path = temp_dir / "nonexistent.py"

        with pytest.raises(FileNotFoundError):
            load_model_from_script(fake_path)

    def test_load_script_syntax_error(self, temp_dir):
        """Should raise error for script with syntax error."""
        script = temp_dir / "bad_syntax.py"
        script.write_text('''
def incomplete(
''')
        with pytest.raises(SyntaxError):
            load_model_from_script(script)

    def test_load_script_no_model_variable(self, temp_dir):
        """Should raise ValueError if no model/part found."""
        script = temp_dir / "no_model.py"
        script.write_text('''
x = 42
y = "hello"
''')
        with pytest.raises(ValueError) as exc_info:
            load_model_from_script(script)

        assert "No 'model' or 'part' variable found" in str(exc_info.value)

    def test_load_script_with_imports(self, temp_dir):
        """Script with imports should work."""
        script = temp_dir / "with_imports.py"
        script.write_text('''
import math
from build123d import Box, Cylinder, Pos

base = Box(30, 30, 10)
hole = Cylinder(5, 10)
part = base - hole
''')
        loaded = load_model_from_script(script)

        assert isinstance(loaded, MichelangeloModel)


class TestLoadStl:
    """Tests for load_stl function."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def valid_stl(self, temp_dir):
        """Create a valid STL file."""
        stl_path = temp_dir / "valid.stl"
        mesh = trimesh.creation.box(extents=[10, 10, 10])
        mesh.export(str(stl_path))
        return stl_path

    def test_load_valid_stl(self, valid_stl):
        """Load valid STL file."""
        mesh = load_stl(valid_stl)

        assert isinstance(mesh, trimesh.Trimesh)
        assert len(mesh.vertices) > 0
        assert len(mesh.faces) > 0

    def test_load_invalid_path(self, temp_dir):
        """Should raise error for non-existent file."""
        fake_path = temp_dir / "nonexistent.stl"

        with pytest.raises(Exception):  # trimesh raises various exceptions
            load_stl(fake_path)
