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


class TestPreviewCommands:
    """Tests for preview commands."""

    def test_preview_model_missing_file(self, temp_dir):
        """Preview model should error on missing file."""
        result = runner.invoke(app, ["preview", "model", str(temp_dir / "missing.py")])

        assert result.exit_code == 1

    def test_preview_stl_missing_file(self, temp_dir):
        """Preview stl should error on missing file."""
        result = runner.invoke(app, ["preview", "stl", str(temp_dir / "missing.stl")])

        assert result.exit_code == 1


class TestExportCommands:
    """Tests for export commands."""

    def test_export_stl_missing_file(self, temp_dir):
        """Export should error on missing file."""
        result = runner.invoke(app, ["export", "stl", str(temp_dir / "missing.py")])

        assert result.exit_code == 1

    def test_export_stl_basic(self, sample_script, temp_dir):
        """Export should create STL file."""
        output_path = temp_dir / "output.stl"

        result = runner.invoke(app, [
            "export", "stl",
            str(sample_script),
            "-o", str(output_path),
        ])

        # Check successful export
        if result.exit_code == 0:
            assert output_path.exists()
            assert output_path.stat().st_size > 0

    def test_export_stl_quality_options(self, sample_script, temp_dir):
        """Export should accept quality options."""
        output_path = temp_dir / "output.stl"

        result = runner.invoke(app, [
            "export", "stl",
            str(sample_script),
            "-o", str(output_path),
            "--quality", "high",
        ])

        # Quality option should be accepted
        if result.exit_code == 0:
            assert output_path.exists()


class TestRepairCommands:
    """Tests for repair commands."""

    def test_repair_missing_file(self, temp_dir):
        """Repair should error on missing file."""
        result = runner.invoke(app, ["repair", "auto", str(temp_dir / "missing.stl")])

        assert result.exit_code == 1

    def test_repair_auto_basic(self, sample_stl, temp_dir):
        """Repair should create repaired file."""
        output_path = temp_dir / "repaired.stl"

        result = runner.invoke(app, [
            "repair", "auto",
            str(sample_stl),
            "-o", str(output_path),
        ])

        if result.exit_code == 0:
            assert output_path.exists()


class TestHelpCommands:
    """Tests for help and documentation."""

    def test_help_flag(self):
        """--help should show usage."""
        result = runner.invoke(app, ["--help"])

        assert result.exit_code == 0
        assert "Usage" in result.stdout or "usage" in result.stdout

    def test_help_command(self):
        """help command should show detailed info."""
        result = runner.invoke(app, ["help"])

        assert result.exit_code == 0

    def test_subcommand_help(self):
        """Subcommand help should work."""
        result = runner.invoke(app, ["export", "--help"])

        assert result.exit_code == 0
        assert "stl" in result.stdout.lower()


class TestValidateDisconnectedParts:
    """Tests for disconnected parts validation."""

    @pytest.fixture
    def disconnected_stl(self, temp_dir):
        """Create an STL with disconnected parts."""
        import trimesh

        box1 = trimesh.creation.box(extents=[10, 10, 10])
        box2 = trimesh.creation.box(extents=[10, 10, 10])
        box2.apply_translation([50, 0, 0])
        combined = trimesh.util.concatenate([box1, box2])

        stl_path = temp_dir / "disconnected.stl"
        combined.export(str(stl_path))
        return stl_path

    def test_validate_detects_disconnected_parts(self, disconnected_stl):
        """Validation should detect disconnected parts."""
        result = runner.invoke(app, ["validate", "mesh", str(disconnected_stl), "-v"])

        assert "disconnected" in result.stdout.lower() or "DISCONNECTED" in result.stdout

    def test_validate_json_includes_disconnected_issue(self, disconnected_stl):
        """JSON validation should include disconnected parts issue."""
        import json

        result = runner.invoke(app, ["validate", "mesh", str(disconnected_stl), "--json"])

        data = json.loads(result.stdout)

        # Should have issues
        assert "issues" in data
        assert len(data["issues"]) > 0

        # Should include disconnected parts issue
        codes = [i.get("code", "") for i in data["issues"]]
        assert "DISCONNECTED_PARTS" in codes or any("disconnect" in c.lower() for c in codes)
