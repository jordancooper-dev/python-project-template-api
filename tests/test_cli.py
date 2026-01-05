"""Tests for CLI commands."""

from typer.testing import CliRunner

from app.cli import app

runner = CliRunner()


def test_version_command() -> None:
    """Test version command outputs version info."""
    result = runner.invoke(app, ["version"])

    assert result.exit_code == 0
    assert "my-project version" in result.stdout


def test_serve_help() -> None:
    """Test serve command help."""
    result = runner.invoke(app, ["serve", "--help"])

    assert result.exit_code == 0
    assert "--host" in result.stdout
    assert "--port" in result.stdout
    assert "--reload" in result.stdout


def test_keys_help() -> None:
    """Test keys subcommand help."""
    result = runner.invoke(app, ["keys", "--help"])

    assert result.exit_code == 0
    assert "create" in result.stdout
    assert "list" in result.stdout
    assert "revoke" in result.stdout
    assert "info" in result.stdout


def test_keys_create_help() -> None:
    """Test keys create command help."""
    result = runner.invoke(app, ["keys", "create", "--help"])

    assert result.exit_code == 0
    assert "--name" in result.stdout
    assert "--client-id" in result.stdout
