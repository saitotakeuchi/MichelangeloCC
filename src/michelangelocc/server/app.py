"""
FastAPI server for previewing 3D models in the browser.

Provides a lightweight HTTP server with WebSocket support for hot-reload
when model files change.
"""

from pathlib import Path
from typing import Optional, List
import asyncio
import webbrowser
import os

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, Response, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

# Global state for the server
_current_script_path: Optional[Path] = None
_current_stl_path: Optional[Path] = None
_websocket_clients: List[WebSocket] = []
_model_cache: Optional[bytes] = None
_model_info_cache: Optional[dict] = None

app = FastAPI(title="MichelangeloCC Viewer")


@app.get("/")
async def viewer_page():
    """Serve the Three.js viewer HTML."""
    return HTMLResponse(content=VIEWER_HTML)


@app.get("/model.stl")
async def get_model_stl():
    """Generate and serve current model as STL."""
    global _model_cache

    if _current_stl_path and _current_stl_path.exists():
        # Serve static STL file
        content = _current_stl_path.read_bytes()
        return Response(content=content, media_type="application/octet-stream")

    if _current_script_path and _current_script_path.exists():
        try:
            # Regenerate model from script
            from michelangelocc.core.modeler import load_model_from_script

            model = load_model_from_script(_current_script_path)
            stl_bytes = model.to_stl_bytes(tolerance=0.01)
            _model_cache = stl_bytes

            # Update info cache
            global _model_info_cache
            _model_info_cache = model.info()

            return Response(content=stl_bytes, media_type="application/octet-stream")
        except Exception as e:
            return JSONResponse(
                status_code=500,
                content={"error": str(e)},
            )

    return JSONResponse(status_code=404, content={"error": "No model loaded"})


@app.get("/model/info")
async def get_model_info():
    """Return model metadata and statistics."""
    global _model_info_cache

    if _model_info_cache:
        return JSONResponse(content=_model_info_cache)

    if _current_script_path and _current_script_path.exists():
        try:
            from michelangelocc.core.modeler import load_model_from_script

            model = load_model_from_script(_current_script_path)
            _model_info_cache = model.info()
            return JSONResponse(content=_model_info_cache)
        except Exception as e:
            return JSONResponse(
                status_code=500,
                content={"error": str(e)},
            )

    if _current_stl_path and _current_stl_path.exists():
        try:
            import trimesh

            mesh = trimesh.load(str(_current_stl_path))
            bounds = mesh.bounds
            info = {
                "name": _current_stl_path.stem,
                "dimensions": {
                    "x": float(bounds[1][0] - bounds[0][0]),
                    "y": float(bounds[1][1] - bounds[0][1]),
                    "z": float(bounds[1][2] - bounds[0][2]),
                },
                "volume": float(mesh.volume) if mesh.is_watertight else None,
                "surface_area": float(mesh.area),
                "triangles": len(mesh.faces),
                "vertices": len(mesh.vertices),
                "is_watertight": bool(mesh.is_watertight),
            }
            return JSONResponse(content=info)
        except Exception as e:
            return JSONResponse(
                status_code=500,
                content={"error": str(e)},
            )

    return JSONResponse(status_code=404, content={"error": "No model loaded"})


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket for hot-reload notifications."""
    await websocket.accept()
    _websocket_clients.append(websocket)

    try:
        while True:
            # Keep connection alive, wait for messages
            data = await websocket.receive_text()
            # Echo back for ping/pong
            await websocket.send_text(data)
    except WebSocketDisconnect:
        _websocket_clients.remove(websocket)


async def notify_model_change():
    """Notify all connected clients of model update."""
    global _model_cache, _model_info_cache

    # Clear caches
    _model_cache = None
    _model_info_cache = None

    # Notify clients
    for client in _websocket_clients:
        try:
            await client.send_json({"type": "reload"})
        except Exception:
            pass


def run_preview_server(
    script_path: Path,
    port: int = 8080,
    open_browser: bool = True,
    watch: bool = True,
):
    """
    Run the preview server for a Python script.

    Args:
        script_path: Path to Python script generating model
        port: Server port
        open_browser: Open browser automatically
        watch: Enable file watching for hot-reload
    """
    global _current_script_path
    _current_script_path = Path(script_path).resolve()

    if watch:
        from michelangelocc.server.watcher import start_watcher

        start_watcher(_current_script_path, notify_model_change)

    if open_browser:
        import threading

        def open_browser_delayed():
            import time
            time.sleep(0.5)
            webbrowser.open(f"http://localhost:{port}")

        threading.Thread(target=open_browser_delayed, daemon=True).start()

    uvicorn.run(app, host="0.0.0.0", port=port, log_level="warning")


def run_stl_preview_server(stl_path: Path, port: int = 8080):
    """
    Run the preview server for a static STL file.

    Args:
        stl_path: Path to STL file
        port: Server port
    """
    global _current_stl_path
    _current_stl_path = Path(stl_path).resolve()

    webbrowser.open(f"http://localhost:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="warning")


# Embedded HTML/JS/CSS for the viewer (to avoid external file dependencies)
VIEWER_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MichelangeloCC Viewer</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #1a1a2e;
            color: #eee;
            overflow: hidden;
        }
        #viewer-container {
            width: 100vw;
            height: 100vh;
        }
        #info-panel {
            position: fixed;
            top: 20px;
            left: 20px;
            background: rgba(0,0,0,0.7);
            padding: 15px 20px;
            border-radius: 8px;
            min-width: 200px;
            backdrop-filter: blur(10px);
        }
        #info-panel h2 {
            font-size: 16px;
            margin-bottom: 10px;
            color: #3498db;
        }
        .info-row {
            display: flex;
            justify-content: space-between;
            margin: 5px 0;
            font-size: 13px;
        }
        .info-row .label { color: #888; }
        .info-row .value { color: #fff; }
        #controls-panel {
            position: fixed;
            bottom: 20px;
            right: 20px;
            display: flex;
            gap: 10px;
        }
        #controls-panel button {
            background: rgba(0,0,0,0.7);
            border: none;
            color: #fff;
            padding: 10px 15px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 16px;
            backdrop-filter: blur(10px);
        }
        #controls-panel button:hover { background: rgba(52,152,219,0.7); }
        #loading {
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            font-size: 18px;
            color: #3498db;
        }
        #error {
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            color: #e74c3c;
            text-align: center;
            display: none;
        }
        .watertight-yes { color: #2ecc71 !important; }
        .watertight-no { color: #e74c3c !important; }
    </style>
</head>
<body>
    <div id="viewer-container"></div>

    <div id="loading">Loading model...</div>
    <div id="error">
        <h2>Error Loading Model</h2>
        <p id="error-message"></p>
    </div>

    <div id="info-panel" style="display: none;">
        <h2 id="model-name">Model</h2>
        <div class="info-row">
            <span class="label">Dimensions:</span>
            <span class="value" id="model-dimensions">-</span>
        </div>
        <div class="info-row">
            <span class="label">Volume:</span>
            <span class="value" id="model-volume">-</span>
        </div>
        <div class="info-row">
            <span class="label">Triangles:</span>
            <span class="value" id="model-triangles">-</span>
        </div>
        <div class="info-row">
            <span class="label">Watertight:</span>
            <span class="value" id="model-watertight">-</span>
        </div>
    </div>

    <div id="controls-panel">
        <button id="btn-reset-view" title="Reset View">Reset</button>
        <button id="btn-wireframe" title="Toggle Wireframe">Wireframe</button>
    </div>

    <script type="importmap">
    {
        "imports": {
            "three": "https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js",
            "three/addons/": "https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/"
        }
    }
    </script>

    <script type="module">
        import * as THREE from 'three';
        import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
        import { STLLoader } from 'three/addons/loaders/STLLoader.js';

        class MichelangeloViewer {
            constructor(container) {
                this.container = container;
                this.scene = null;
                this.camera = null;
                this.renderer = null;
                this.controls = null;
                this.currentMesh = null;
                this.websocket = null;
                this.wireframeMode = false;

                this.init();
                this.connectWebSocket();
                this.loadModel();
                this.setupControls();
            }

            init() {
                // Scene
                this.scene = new THREE.Scene();
                this.scene.background = new THREE.Color(0x1a1a2e);

                // Camera
                this.camera = new THREE.PerspectiveCamera(
                    45, window.innerWidth / window.innerHeight, 0.1, 10000
                );
                this.camera.position.set(100, 100, 100);

                // Renderer
                this.renderer = new THREE.WebGLRenderer({ antialias: true });
                this.renderer.setSize(window.innerWidth, window.innerHeight);
                this.renderer.setPixelRatio(window.devicePixelRatio);
                this.renderer.shadowMap.enabled = true;
                this.container.appendChild(this.renderer.domElement);

                // Controls
                this.controls = new OrbitControls(this.camera, this.renderer.domElement);
                this.controls.enableDamping = true;
                this.controls.dampingFactor = 0.05;

                // Lighting
                this.setupLighting();

                // Grid
                const grid = new THREE.GridHelper(200, 20, 0x444444, 0x222222);
                this.scene.add(grid);

                // Axes
                const axes = new THREE.AxesHelper(50);
                this.scene.add(axes);

                // Resize handler
                window.addEventListener('resize', () => this.onResize());

                // Start render loop
                this.animate();
            }

            setupLighting() {
                const ambient = new THREE.AmbientLight(0xffffff, 0.4);
                this.scene.add(ambient);

                const keyLight = new THREE.DirectionalLight(0xffffff, 0.8);
                keyLight.position.set(50, 100, 50);
                keyLight.castShadow = true;
                this.scene.add(keyLight);

                const fillLight = new THREE.DirectionalLight(0xffffff, 0.3);
                fillLight.position.set(-50, 50, -50);
                this.scene.add(fillLight);

                const backLight = new THREE.DirectionalLight(0xffffff, 0.2);
                backLight.position.set(0, -50, -50);
                this.scene.add(backLight);
            }

            setupControls() {
                document.getElementById('btn-reset-view').onclick = () => this.resetView();
                document.getElementById('btn-wireframe').onclick = () => this.toggleWireframe();
            }

            async loadModel() {
                const loader = new STLLoader();
                const loadingEl = document.getElementById('loading');
                const errorEl = document.getElementById('error');
                const infoPanel = document.getElementById('info-panel');

                loadingEl.style.display = 'block';
                errorEl.style.display = 'none';

                try {
                    const response = await fetch('/model.stl');
                    if (!response.ok) {
                        throw new Error('Failed to load model');
                    }

                    const arrayBuffer = await response.arrayBuffer();
                    const geometry = loader.parse(arrayBuffer);

                    // Remove old mesh
                    if (this.currentMesh) {
                        this.scene.remove(this.currentMesh);
                    }

                    // Create material
                    const material = new THREE.MeshPhongMaterial({
                        color: 0x3498db,
                        specular: 0x111111,
                        shininess: 100,
                        flatShading: false,
                        side: THREE.DoubleSide,
                    });

                    // Create mesh
                    this.currentMesh = new THREE.Mesh(geometry, material);
                    this.currentMesh.castShadow = true;
                    this.currentMesh.receiveShadow = true;

                    // Center the model
                    geometry.computeBoundingBox();
                    const center = new THREE.Vector3();
                    geometry.boundingBox.getCenter(center);
                    this.currentMesh.position.sub(center);

                    this.scene.add(this.currentMesh);

                    // Fit camera
                    this.fitCameraToModel();

                    // Update info
                    this.updateModelInfo();

                    loadingEl.style.display = 'none';
                    infoPanel.style.display = 'block';

                } catch (error) {
                    console.error('Failed to load model:', error);
                    loadingEl.style.display = 'none';
                    errorEl.style.display = 'block';
                    document.getElementById('error-message').textContent = error.message;
                }
            }

            connectWebSocket() {
                const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
                this.websocket = new WebSocket(`${protocol}//${location.host}/ws`);

                this.websocket.onmessage = (event) => {
                    const data = JSON.parse(event.data);
                    if (data.type === 'reload') {
                        console.log('Model changed, reloading...');
                        this.loadModel();
                    }
                };

                this.websocket.onclose = () => {
                    // Reconnect after delay
                    setTimeout(() => this.connectWebSocket(), 2000);
                };
            }

            fitCameraToModel() {
                if (!this.currentMesh) return;

                const box = new THREE.Box3().setFromObject(this.currentMesh);
                const size = box.getSize(new THREE.Vector3());
                const maxDim = Math.max(size.x, size.y, size.z);

                this.camera.position.set(maxDim * 1.5, maxDim * 1.2, maxDim * 1.5);
                this.controls.target.set(0, 0, 0);
                this.controls.update();
            }

            resetView() {
                this.fitCameraToModel();
            }

            toggleWireframe() {
                this.wireframeMode = !this.wireframeMode;
                if (this.currentMesh) {
                    this.currentMesh.material.wireframe = this.wireframeMode;
                }
            }

            async updateModelInfo() {
                try {
                    const response = await fetch('/model/info');
                    const info = await response.json();

                    document.getElementById('model-name').textContent = info.name || 'Model';

                    const dims = info.dimensions || {};
                    document.getElementById('model-dimensions').textContent =
                        `${(dims.x || 0).toFixed(1)} x ${(dims.y || 0).toFixed(1)} x ${(dims.z || 0).toFixed(1)} mm`;

                    if (info.volume) {
                        const vol = info.volume;
                        document.getElementById('model-volume').textContent =
                            vol > 1000 ? `${(vol/1000).toFixed(2)} cm³` : `${vol.toFixed(2)} mm³`;
                    } else {
                        document.getElementById('model-volume').textContent = 'N/A';
                    }

                    document.getElementById('model-triangles').textContent =
                        (info.triangles || 0).toLocaleString();

                    const watertightEl = document.getElementById('model-watertight');
                    if (info.is_watertight) {
                        watertightEl.textContent = 'Yes';
                        watertightEl.className = 'value watertight-yes';
                    } else {
                        watertightEl.textContent = 'No';
                        watertightEl.className = 'value watertight-no';
                    }

                } catch (error) {
                    console.error('Failed to fetch model info:', error);
                }
            }

            animate() {
                requestAnimationFrame(() => this.animate());
                this.controls.update();
                this.renderer.render(this.scene, this.camera);
            }

            onResize() {
                this.camera.aspect = window.innerWidth / window.innerHeight;
                this.camera.updateProjectionMatrix();
                this.renderer.setSize(window.innerWidth, window.innerHeight);
            }
        }

        // Initialize viewer
        const viewer = new MichelangeloViewer(document.getElementById('viewer-container'));
    </script>
</body>
</html>
"""
