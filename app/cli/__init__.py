"""CLI module for application management."""

import typer

from app.cli.keys import app as keys_app

app = typer.Typer(
    name="my-project",
    help="My Project API - CLI management tool",
    no_args_is_help=True,
)

# Add subcommands
app.add_typer(keys_app, name="keys", help="Manage API keys")


@app.command()
def serve(
    host: str = typer.Option("0.0.0.0", "--host", "-h", help="Host to bind to"),
    port: int = typer.Option(8000, "--port", "-p", help="Port to bind to"),
    reload: bool = typer.Option(False, "--reload", "-r", help="Enable auto-reload"),
) -> None:
    """Start the API server."""
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=reload,
    )


@app.command()
def version() -> None:
    """Show the application version."""
    from importlib.metadata import PackageNotFoundError, version as get_version

    try:
        ver = get_version("my-project")
    except PackageNotFoundError:
        ver = "0.1.0 (development)"
    typer.echo(f"my-project version {ver}")


if __name__ == "__main__":
    app()
