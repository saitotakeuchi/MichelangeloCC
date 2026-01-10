"""Integration tests for CLI commands."""

import pytest
from typer.testing import CliRunner
from pathlib import Path

from michelangelocc.cli import app

runner = CliRunner()


class TestVersionCommand:
    """Tests for version command."""

    def test_version_output(self):
        """Version command should output version string."""
        result = runner.invoke(app, ["version"])

        assert result.exit_code == 0
        assert "MichelangeloCC" in result.stdout
        assert "v" in result.stdout


class TestInfoCommand:
    """Tests for info command."""

    def test_info_stl_file(self, sample_stl):
        """Info command should display STL file information."""
        result = runner.invoke(app, ["info", str(sample_stl)])

        assert result.exit_code == 0
        assert "Dimensions" in result.stdout
        assert "Triangles" in result.stdout

    def test_info_missing_file(self, temp_dir):
        """Info command should error on missing file."""
        result = runner.invoke(app, ["info", str(temp_dir / "missing.stl")])

        assert result.exit_code == 1
        assert "not found" in result.stdout.lower() or "error" in result.stdout.lower()


class TestValidateCommand:
    """Tests for validate command."""

    def test_validate_valid_stl(self, sample_stl):
        """Validate should pass for valid STL."""
        result = runner.invoke(app, ["validate", "mesh", str(sample_stl)])

        assert result.exit_code == 0
        assert "VALID" in result.stdout or "Watertight" in result.stdout

    def test_validate_verbose(self, sample_stl):
        """Verbose validation should show detailed output."""
        result = runner.invoke(app, ["validate", "mesh", str(sample_stl), "-v"])

        assert result.exit_code == 0
        assert "Validation Summary" in result.stdout

    def test_validate_json_output(self, sample_stl):
        """JSON output should be valid."""
        import json

        result = runner.invoke(app, ["validate", "mesh", str(sample_stl), "--json"])

        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert "is_valid" in data
        assert "is_watertight" in data


class TestNewCommand:
    """Tests for new project command."""

    def test_new_basic_project(self, temp_dir):
        """New command should create project directory."""
        import os
        os.chdir(temp_dir)

        result = runner.invoke(app, ["new", "test_project"])

        assert result.exit_code == 0
        assert (temp_dir / "test_project").exists()
        assert (temp_dir / "test_project" / "test_project.py").exists()

    def test_new_mechanical_template(self, temp_dir):
        """Mechanical template should include mounting holes."""
        import os
        os.chdir(temp_dir)

        result = runner.invoke(app, ["new", "bracket", "-t", "mechanical"])

        assert result.exit_code == 0
        script = (temp_dir / "bracket" / "bracket.py").read_text()
        assert "hole" in script.lower()

    def test_new_existing_directory(self, temp_dir):
        """New command should error if directory exists."""
        import os
        os.chdir(temp_dir)

        # Create directory first
        (temp_dir / "existing").mkdir()

        result = runner.invoke(app, ["new", "existing"])

        assert result.exit_code == 1
        assert "exists" in result.stdout.lower()
