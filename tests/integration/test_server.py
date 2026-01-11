"""Integration tests for the FastAPI preview server."""

import pytest
from pathlib import Path
import tempfile
import io

import trimesh
from httpx import AsyncClient, ASGITransport

from michelangelocc.server.app import app, _current_script_path, _current_stl_path


# Set up test transport
transport = ASGITransport(app=app)


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def valid_model_script(temp_dir):
    """Create a valid model script."""
    script = temp_dir / "model.py"
    script.write_text('''
from build123d import Box
from michelangelocc import MichelangeloModel, ModelMetadata

part = Box(20, 20, 20)
model = MichelangeloModel(
    part=part,
    metadata=ModelMetadata(name="test_cube", description="A test cube")
)
''')
    return script


@pytest.fixture
def valid_stl_file(temp_dir):
    """Create a valid STL file."""
    stl_path = temp_dir / "test.stl"
    mesh = trimesh.creation.box(extents=[10, 10, 10])
    mesh.export(str(stl_path))
    return stl_path


@pytest.fixture
def disconnected_stl_file(temp_dir):
    """Create an STL file with disconnected parts."""
    stl_path = temp_dir / "disconnected.stl"
    box1 = trimesh.creation.box(extents=[10, 10, 10])
    box2 = trimesh.creation.box(extents=[10, 10, 10])
    box2.apply_translation([50, 0, 0])  # Move far away
    combined = trimesh.util.concatenate([box1, box2])
    combined.export(str(stl_path))
    return stl_path


class TestViewerEndpoint:
    """Tests for the viewer HTML endpoint."""

    @pytest.mark.asyncio
    async def test_get_viewer_html(self):
        """GET / should return HTML page."""
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    @pytest.mark.asyncio
    async def test_viewer_contains_threejs(self):
        """Viewer HTML should contain Three.js setup."""
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/")

        html = response.text
        assert "three" in html.lower()
        assert "STLLoader" in html
        assert "MichelangeloViewer" in html

    @pytest.mark.asyncio
    async def test_viewer_contains_warning_banner(self):
        """Viewer HTML should contain warning banner element."""
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/")

        html = response.text
        assert "warning-banner" in html
        assert "showWarning" in html


class TestModelStlEndpoint:
    """Tests for the model STL endpoint."""

    @pytest.mark.asyncio
    async def test_get_stl_not_found(self):
        """GET /model.stl should return 404 when no model loaded."""
        # Reset global state
        import michelangelocc.server.app as app_module
        app_module._current_script_path = None
        app_module._current_stl_path = None

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/model.stl")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_stl_from_static_file(self, valid_stl_file):
        """GET /model.stl should serve static STL file."""
        import michelangelocc.server.app as app_module
        app_module._current_stl_path = valid_stl_file
        app_module._current_script_path = None

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/model.stl")

        assert response.status_code == 200
        assert "application/octet-stream" in response.headers["content-type"]
        assert len(response.content) > 0

        # Clean up
        app_module._current_stl_path = None

    @pytest.mark.asyncio
    async def test_get_stl_validation_warning_header(self, disconnected_stl_file):
        """GET /model.stl should include validation warning header for invalid mesh."""
        import michelangelocc.server.app as app_module
        app_module._current_stl_path = disconnected_stl_file
        app_module._current_script_path = None

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/model.stl")

        assert response.status_code == 200
        # Should have validation warning for disconnected parts
        warning = response.headers.get("x-validation-warning")
        assert warning is not None
        assert "disconnected" in warning.lower()

        # Clean up
        app_module._current_stl_path = None


class TestModelInfoEndpoint:
    """Tests for the model info endpoint."""

    @pytest.mark.asyncio
    async def test_get_info_not_found(self):
        """GET /model/info should return 404 when no model loaded."""
        import michelangelocc.server.app as app_module
        app_module._current_script_path = None
        app_module._current_stl_path = None
        app_module._model_info_cache = None

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/model/info")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_info_from_stl(self, valid_stl_file):
        """GET /model/info should return info for STL file."""
        import michelangelocc.server.app as app_module
        app_module._current_stl_path = valid_stl_file
        app_module._current_script_path = None
        app_module._model_info_cache = None

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/model/info")

        assert response.status_code == 200
        info = response.json()

        assert "name" in info
        assert "dimensions" in info
        assert "triangles" in info
        assert "vertices" in info
        assert "is_watertight" in info

        # Clean up
        app_module._current_stl_path = None

    @pytest.mark.asyncio
    async def test_get_info_returns_json(self, valid_stl_file):
        """GET /model/info should return valid JSON."""
        import michelangelocc.server.app as app_module
        app_module._current_stl_path = valid_stl_file
        app_module._current_script_path = None
        app_module._model_info_cache = None

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/model/info")

        assert response.status_code == 200
        assert "application/json" in response.headers["content-type"]

        # Should be valid JSON
        info = response.json()
        assert isinstance(info, dict)

        # Clean up
        app_module._current_stl_path = None


class TestValidateStlBytes:
    """Tests for _validate_stl_bytes function."""

    def test_returns_none_for_valid_mesh(self):
        """Should return None for valid watertight mesh."""
        from michelangelocc.server.app import _validate_stl_bytes

        mesh = trimesh.creation.box(extents=[10, 10, 10])
        buffer = io.BytesIO()
        mesh.export(buffer, file_type="stl")
        stl_bytes = buffer.getvalue()

        warning = _validate_stl_bytes(stl_bytes)

        assert warning is None

    def test_returns_warning_for_disconnected_mesh(self):
        """Should return warning for mesh with disconnected parts."""
        from michelangelocc.server.app import _validate_stl_bytes

        # Create disconnected mesh
        box1 = trimesh.creation.box(extents=[10, 10, 10])
        box2 = trimesh.creation.box(extents=[10, 10, 10])
        box2.apply_translation([50, 0, 0])
        combined = trimesh.util.concatenate([box1, box2])

        buffer = io.BytesIO()
        combined.export(buffer, file_type="stl")
        stl_bytes = buffer.getvalue()

        warning = _validate_stl_bytes(stl_bytes)

        assert warning is not None
        assert "disconnected" in warning.lower()

    def test_returns_none_on_exception(self):
        """Should return None if validation fails."""
        from michelangelocc.server.app import _validate_stl_bytes

        # Invalid STL bytes
        invalid_bytes = b"not a valid stl file"

        warning = _validate_stl_bytes(invalid_bytes)

        # Should not raise, just return None
        assert warning is None


class TestWebSocket:
    """Tests for WebSocket functionality."""

    @pytest.mark.asyncio
    async def test_websocket_connect(self):
        """Should accept WebSocket connection."""
        from httpx._transports.asgi import ASGITransport
        from starlette.testclient import TestClient

        # Use Starlette TestClient for WebSocket testing
        client = TestClient(app)

        with client.websocket_connect("/ws") as websocket:
            # Connection should succeed
            assert websocket is not None

    @pytest.mark.asyncio
    async def test_websocket_ping_pong(self):
        """Should echo back messages."""
        from starlette.testclient import TestClient

        client = TestClient(app)

        with client.websocket_connect("/ws") as websocket:
            websocket.send_text("ping")
            response = websocket.receive_text()
            assert response == "ping"


class TestModelInfoCache:
    """Tests for model info caching."""

    @pytest.mark.asyncio
    async def test_get_info_uses_cache(self, valid_stl_file):
        """GET /model/info should use cache when available."""
        import michelangelocc.server.app as app_module

        # Set up cache
        cached_info = {
            "name": "cached_model",
            "dimensions": {"x": 10, "y": 10, "z": 10},
            "triangles": 12,
            "vertices": 8,
            "is_watertight": True,
        }
        app_module._model_info_cache = cached_info
        app_module._current_stl_path = None
        app_module._current_script_path = None

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/model/info")

        assert response.status_code == 200
        info = response.json()
        assert info["name"] == "cached_model"

        # Clean up
        app_module._model_info_cache = None


class TestNotifyModelChange:
    """Tests for notify_model_change function."""

    @pytest.mark.asyncio
    async def test_notify_clears_cache(self):
        """notify_model_change should clear caches."""
        import michelangelocc.server.app as app_module
        from michelangelocc.server.app import notify_model_change

        # Set up caches
        app_module._model_cache = b"some stl data"
        app_module._model_info_cache = {"name": "test"}

        # Call notify
        await notify_model_change()

        # Caches should be cleared
        assert app_module._model_cache is None
        assert app_module._model_info_cache is None


class TestGetStlFromScript:
    """Tests for loading STL from Python script."""

    @pytest.fixture
    def valid_model_script(self, temp_dir):
        """Create a valid model script."""
        script = temp_dir / "model.py"
        script.write_text('''
from build123d import Box
from michelangelocc import MichelangeloModel, ModelMetadata

part = Box(20, 20, 20)
model = MichelangeloModel(
    part=part,
    metadata=ModelMetadata(name="test_cube", description="A test cube")
)
''')
        return script

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.mark.asyncio
    async def test_get_stl_from_script(self, valid_model_script):
        """GET /model.stl should generate STL from script."""
        import michelangelocc.server.app as app_module
        app_module._current_script_path = valid_model_script
        app_module._current_stl_path = None
        app_module._model_cache = None

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/model.stl")

        assert response.status_code == 200
        assert len(response.content) > 0

        # Clean up
        app_module._current_script_path = None
        app_module._model_cache = None

    @pytest.mark.asyncio
    async def test_get_info_from_script(self, valid_model_script):
        """GET /model/info should return info from script."""
        import michelangelocc.server.app as app_module
        app_module._current_script_path = valid_model_script
        app_module._current_stl_path = None
        app_module._model_info_cache = None

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/model/info")

        assert response.status_code == 200
        info = response.json()
        assert "name" in info
        assert info["name"] == "test_cube"

        # Clean up
        app_module._current_script_path = None
        app_module._model_info_cache = None
