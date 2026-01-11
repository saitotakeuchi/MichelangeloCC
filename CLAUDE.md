# MichelangeloCC Development Guide

> Claude Code-powered 3D model generator for STL files

## Quick Reference

- **Package**: `michelangelocc`
- **Entry Point**: `mcc` CLI command
- **Python**: 3.10+
- **Test Coverage**: 80% minimum (enforced by CI)

## Project Structure

```
src/michelangelocc/
├── cli.py              # Typer CLI - all commands
├── session.py          # Interactive tmux sessions with Claude
├── core/
│   ├── modeler.py      # MichelangeloModel wrapper for build123d
│   ├── exporter.py     # STL export with quality presets
│   ├── validator.py    # 3D printing validation checks
│   └── repairer.py     # Mesh repair (PyMeshFix)
└── server/
    ├── app.py          # FastAPI preview server
    └── watcher.py      # File watching for hot-reload
```

## Key Classes & Patterns

### MichelangeloModel (core/modeler.py)
- Wraps build123d Part/Solid objects
- Use `to_mesh(tolerance)` for trimesh conversion
- Use `to_stl_bytes()` for direct STL export
- `info()` returns dict with dimensions, volume, triangle count

### Export Pipeline (core/exporter.py)
```python
ExportQuality.DRAFT      # 0.1mm tolerance
ExportQuality.STANDARD   # 0.01mm tolerance
ExportQuality.HIGH       # 0.001mm tolerance
ExportQuality.ULTRA      # 0.0001mm tolerance
```

### Validation (core/validator.py)
- Returns `ValidationResult` with `is_valid`, `is_watertight`, `issues[]`
- Issue codes: `NOT_WATERTIGHT`, `DISCONNECTED_PARTS`, `DEGENERATE_FACES`

## Development Commands

```bash
make install-dev     # Setup dev environment
make test            # Run tests
make test-cov        # Tests with coverage report
make test-cov-check  # Fail if coverage < 80%
make lint            # Ruff linting
make check           # All checks
```

## Testing Requirements

**CRITICAL: 80% coverage minimum is enforced by CI**

- All new code must have tests
- Run `make test-cov-check` before pushing
- Tests in `tests/unit/` for isolated logic
- Tests in `tests/integration/` for CLI and server

### Test Fixtures (tests/conftest.py)
- `temp_dir` - temporary directory
- `sample_stl` - valid STL file
- `valid_mesh` - watertight trimesh box
- `disconnected_mesh` - two separate cubes
- `non_watertight_mesh` - box with hole

## CI/CD Pipeline

```
Push/PR to main → ci.yml
├── Tests on Python 3.10, 3.11, 3.12
└── Coverage must be ≥ 80%

Release (GitHub Actions UI) → release.yml
├── Run tests
├── Bump version (patch/minor/major)
├── Tag and push
└── Publish to PyPI
```

## Code Patterns to Follow

### Error Handling
- Return result objects (ExportResult, ValidationResult) instead of exceptions
- Use `typer.Exit(1)` for CLI errors
- Graceful degradation (PyMeshFix is optional)

### Async Code
- Server uses FastAPI async routes
- File watcher uses asyncio callbacks
- Use `pytest.mark.asyncio` for async tests

### File Operations
- Use `Path` objects, not strings
- Watchdog handles atomic writes (temp + rename)
- 0.5s debounce on file changes

## Dependencies

| Package | Purpose |
|---------|---------|
| build123d | CAD kernel |
| trimesh | Mesh processing |
| pymeshfix | Mesh repair |
| typer | CLI framework |
| fastapi | Preview server |
| watchdog | File monitoring |

## Common Tasks

### Adding a New CLI Command
1. Add command in `cli.py` under appropriate app group
2. Add tests in `tests/integration/test_cli.py`
3. Update help text if needed

### Adding a New Validation Check
1. Add check method in `MeshValidator` class
2. Define new issue code constant
3. Add tests in `tests/unit/test_validator.py`

### Modifying Export Pipeline
1. Update `STLExporter` in `exporter.py`
2. Update quality presets if needed
3. Add tests for new functionality

## DO NOT

- Skip tests - 80% coverage is mandatory
- Use `print()` - use Rich console
- Hardcode paths - use Path objects
- Block the main thread in server code
- Commit without running `make test-cov-check`
