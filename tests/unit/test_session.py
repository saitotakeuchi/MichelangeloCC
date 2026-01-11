"""Tests for session management module."""

import pytest
from pathlib import Path
import tempfile
from unittest.mock import patch, MagicMock
import socket

from michelangelocc.session import (
    create_session_folder,
    _get_session_template,
    start_preview_server,
    wait_for_server_ready,
    build_claude_command,
    check_tmux_installed,
    create_tmux_session,
    kill_tmux_session,
    tmux_session_exists,
    attach_tmux_session,
    cleanup_server,
    find_available_port,
)


class TestCreateSessionFolder:
    """Tests for create_session_folder function."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_creates_timestamped_folder(self, temp_dir):
        """Session folder should have timestamp in name."""
        session_dir = create_session_folder(temp_dir, "test prompt", "basic")

        assert session_dir.exists()
        assert session_dir.name.startswith("session_")
        assert len(session_dir.name) == len("session_20260110_120000")

    def test_creates_model_py(self, temp_dir):
        """model.py should be created in session folder."""
        session_dir = create_session_folder(temp_dir, "test prompt", "basic")

        model_path = session_dir / "model.py"
        assert model_path.exists()
        assert model_path.is_file()

    def test_creates_output_folder(self, temp_dir):
        """output/ folder should be created."""
        session_dir = create_session_folder(temp_dir, "test prompt", "basic")

        output_dir = session_dir / "output"
        assert output_dir.exists()
        assert output_dir.is_dir()

    def test_model_contains_prompt(self, temp_dir):
        """model.py should contain the user's prompt."""
        prompt = "Create a custom bracket"
        session_dir = create_session_folder(temp_dir, prompt, "basic")

        model_content = (session_dir / "model.py").read_text()
        assert prompt in model_content

    def test_template_basic(self, temp_dir):
        """Basic template should have simple Box."""
        session_dir = create_session_folder(temp_dir, "test", "basic")

        model_content = (session_dir / "model.py").read_text()
        assert "Box(length, width, height)" in model_content

    def test_template_mechanical(self, temp_dir):
        """Mechanical template should have mounting holes."""
        session_dir = create_session_folder(temp_dir, "test", "mechanical")

        model_content = (session_dir / "model.py").read_text()
        assert "hole_diameter" in model_content
        assert "Cylinder" in model_content
        assert "fillet" in model_content

    def test_template_organic(self, temp_dir):
        """Organic template should have loft operation."""
        session_dir = create_session_folder(temp_dir, "test", "organic")

        model_content = (session_dir / "model.py").read_text()
        assert "loft" in model_content
        assert "profiles" in model_content

    def test_template_parametric(self, temp_dir):
        """Parametric template should have configurable slots."""
        session_dir = create_session_folder(temp_dir, "test", "parametric")

        model_content = (session_dir / "model.py").read_text()
        assert "num_slots" in model_content
        assert "slot_width" in model_content


class TestGetSessionTemplate:
    """Tests for _get_session_template function."""

    def test_basic_template_structure(self):
        """Template should have proper structure."""
        content = _get_session_template("test prompt", "basic", "20260110_120000")

        # Should have docstring header
        assert '"""' in content
        assert "MichelangeloCC Interactive Session" in content

        # Should have imports
        assert "from build123d import *" in content
        assert "from michelangelocc import" in content

        # Should have export section
        assert "MichelangeloModel" in content
        assert "ModelMetadata" in content

    def test_template_includes_timestamp(self):
        """Template should include the timestamp."""
        timestamp = "20260110_143052"
        content = _get_session_template("test", "basic", timestamp)

        assert timestamp in content

    def test_template_includes_prompt(self):
        """Template should include the user's prompt."""
        prompt = "Create a gear with 20 teeth"
        content = _get_session_template(prompt, "basic", "20260110_120000")

        assert prompt in content

    def test_unknown_template_falls_back_to_basic(self):
        """Unknown template name should fall back to basic."""
        content = _get_session_template("test", "unknown_template", "20260110_120000")

        # Should use basic template content
        assert "Box(length, width, height)" in content


class TestStartPreviewServer:
    """Tests for start_preview_server function."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @patch("michelangelocc.session.subprocess.Popen")
    def test_starts_subprocess(self, mock_popen, temp_dir):
        """Should start subprocess with correct command."""
        mock_proc = MagicMock()
        mock_popen.return_value = mock_proc

        model_path = temp_dir / "model.py"
        model_path.write_text("# test")

        proc = start_preview_server(model_path, 8080)

        assert mock_popen.called
        call_args = mock_popen.call_args
        cmd = call_args[0][0]

        assert "preview" in cmd
        assert "model" in cmd
        assert str(model_path) in cmd
        assert "--port" in cmd
        assert "8080" in cmd

    @patch("michelangelocc.session.subprocess.Popen")
    def test_no_browser_flag(self, mock_popen, temp_dir):
        """--no-browser flag should be added when open_browser=False."""
        mock_popen.return_value = MagicMock()

        model_path = temp_dir / "model.py"
        model_path.write_text("# test")

        start_preview_server(model_path, 8080, open_browser=False)

        cmd = mock_popen.call_args[0][0]
        assert "--no-browser" in cmd


class TestWaitForServerReady:
    """Tests for wait_for_server_ready function."""

    @patch("michelangelocc.session.socket.create_connection")
    def test_returns_true_when_ready(self, mock_connect):
        """Should return True when connection succeeds."""
        # Mock successful connection
        mock_socket = MagicMock()
        mock_connect.return_value.__enter__ = MagicMock(return_value=mock_socket)
        mock_connect.return_value.__exit__ = MagicMock(return_value=False)

        result = wait_for_server_ready(8080, timeout=1.0)

        assert result is True

    @patch("michelangelocc.session.socket.create_connection")
    def test_returns_false_on_timeout(self, mock_connect):
        """Should return False when connection times out."""
        # Mock connection failure
        mock_connect.side_effect = ConnectionRefusedError()

        result = wait_for_server_ready(8080, timeout=0.5)

        assert result is False


class TestBuildClaudeCommand:
    """Tests for build_claude_command function."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_basic_command_structure(self, temp_dir):
        """Command should have basic structure."""
        cmd = build_claude_command(temp_dir, "test prompt", 8080)

        assert cmd[0] == "claude"
        assert "--append-system-prompt" in cmd
        assert "test prompt" in cmd

    def test_includes_system_prompt(self, temp_dir):
        """Command should include system prompt with context."""
        cmd = build_claude_command(temp_dir, "test prompt", 8080)

        # Find the system prompt in the command
        idx = cmd.index("--append-system-prompt")
        system_prompt = cmd[idx + 1]

        assert str(temp_dir) in system_prompt
        assert "model.py" in system_prompt
        assert "8080" in system_prompt
        assert "mcc export stl" in system_prompt

    def test_includes_model_flag(self, temp_dir):
        """Command should include --model when specified."""
        cmd = build_claude_command(temp_dir, "test prompt", 8080, model="opus")

        assert "--model" in cmd
        idx = cmd.index("--model")
        assert cmd[idx + 1] == "opus"

    def test_no_model_flag_when_none(self, temp_dir):
        """Command should not include --model when not specified."""
        cmd = build_claude_command(temp_dir, "test prompt", 8080, model=None)

        assert "--model" not in cmd

    def test_prompt_is_positional(self, temp_dir):
        """Prompt should be positional argument (not -p)."""
        prompt = "Create a gear"
        cmd = build_claude_command(temp_dir, prompt, 8080)

        # -p is NOT used (that's print-and-exit mode)
        assert "-p" not in cmd

        # Prompt should be last argument
        assert cmd[-1] == prompt


class TestTmuxFunctions:
    """Tests for tmux-related functions."""

    @patch("michelangelocc.session.shutil.which")
    def test_check_tmux_installed_true(self, mock_which):
        """Should return True when tmux is found."""
        mock_which.return_value = "/usr/bin/tmux"

        assert check_tmux_installed() is True

    @patch("michelangelocc.session.shutil.which")
    def test_check_tmux_installed_false(self, mock_which):
        """Should return False when tmux is not found."""
        mock_which.return_value = None

        assert check_tmux_installed() is False

    @patch("michelangelocc.session.subprocess.run")
    def test_create_tmux_session_success(self, mock_run, tmp_path):
        """Should return True on successful session creation."""
        mock_run.return_value = MagicMock(returncode=0, stderr="")

        result = create_tmux_session(
            "test-session",
            ["claude", "test"],
            tmp_path,
        )

        assert result is True
        assert mock_run.called

    @patch("michelangelocc.session.subprocess.run")
    def test_create_tmux_session_failure(self, mock_run, tmp_path):
        """Should return False on failed session creation."""
        mock_run.return_value = MagicMock(returncode=1, stderr="error")

        result = create_tmux_session(
            "test-session",
            ["claude", "test"],
            tmp_path,
        )

        assert result is False

    @patch("michelangelocc.session.subprocess.run")
    def test_tmux_session_exists_true(self, mock_run):
        """Should return True when session exists."""
        mock_run.return_value = MagicMock(returncode=0)

        assert tmux_session_exists("test-session") is True

    @patch("michelangelocc.session.subprocess.run")
    def test_tmux_session_exists_false(self, mock_run):
        """Should return False when session doesn't exist."""
        mock_run.return_value = MagicMock(returncode=1)

        assert tmux_session_exists("test-session") is False

    @patch("michelangelocc.session.subprocess.run")
    def test_kill_tmux_session(self, mock_run):
        """Should call tmux kill-session with correct args."""
        kill_tmux_session("test-session")

        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert "tmux" in call_args
        assert "kill-session" in call_args
        assert "test-session" in call_args


class TestCleanupServer:
    """Tests for cleanup_server function."""

    @patch("michelangelocc.session._server_process", None)
    def test_cleanup_when_no_server(self):
        """Should do nothing when no server is running."""
        from michelangelocc.session import cleanup_server
        # Should not raise
        cleanup_server()

    @patch("michelangelocc.session._server_process")
    def test_cleanup_terminates_server(self, mock_proc):
        """Should terminate running server."""
        import michelangelocc.session as session_module
        from michelangelocc.session import cleanup_server

        mock_proc.poll.return_value = None  # Still running
        mock_proc.wait.return_value = None
        session_module._server_process = mock_proc

        cleanup_server()

        mock_proc.terminate.assert_called_once()

    @patch("michelangelocc.session._server_process")
    def test_cleanup_kills_stubborn_server(self, mock_proc):
        """Should kill server if terminate times out."""
        import subprocess
        import michelangelocc.session as session_module
        from michelangelocc.session import cleanup_server

        mock_proc.poll.return_value = None  # Still running
        mock_proc.wait.side_effect = [subprocess.TimeoutExpired("cmd", 5), None]
        session_module._server_process = mock_proc

        cleanup_server()

        mock_proc.kill.assert_called_once()


class TestAttachTmuxSession:
    """Tests for attach_tmux_session function."""

    @patch("michelangelocc.session.subprocess.run")
    def test_attach_calls_tmux(self, mock_run):
        """Should call tmux attach with correct args."""
        from michelangelocc.session import attach_tmux_session

        attach_tmux_session("test-session")

        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert "tmux" in call_args
        assert "attach-session" in call_args or "attach" in call_args
        assert "test-session" in call_args


class TestFindAvailablePort:
    """Tests for find_available_port function."""

    def test_finds_port(self):
        """Should find an available port."""
        from michelangelocc.session import find_available_port

        port = find_available_port()

        assert port is not None
        assert 8080 <= port <= 65535

    def test_finds_different_port_when_occupied(self):
        """Should find different port when preferred is occupied."""
        from michelangelocc.session import find_available_port
        import socket

        # Occupy a port
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('localhost', 8080))
        sock.listen(1)

        try:
            port = find_available_port(start_port=8080)
            # Should find a different port
            assert port != 8080 or port is None
        finally:
            sock.close()
