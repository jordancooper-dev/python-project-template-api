"""CLI commands for API key management."""

import asyncio
import selectors
import sys
from collections.abc import Coroutine
from typing import Any

import typer
from rich.console import Console
from rich.table import Table
from sqlalchemy.exc import SQLAlchemyError

from app.auth.schemas import APIKeyCreate
from app.auth.service import APIKeyService
from app.db.session import get_session_factory

console = Console()
error_console = Console(stderr=True)


def run_async(coro: Coroutine[Any, Any, Any]) -> Any:
    """Run an async coroutine synchronously.

    On Windows, psycopg3 requires SelectorEventLoop instead of ProactorEventLoop.
    """
    if sys.platform == "win32":
        # psycopg3 on Windows requires SelectorEventLoop
        selector = selectors.SelectSelector()
        loop = asyncio.SelectorEventLoop(selector)
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()
    else:
        return asyncio.run(coro)


def handle_db_error(e: SQLAlchemyError) -> None:
    """Handle database errors with user-friendly message."""
    error_console.print("[red]Error: Unable to connect to database.[/red]")
    error_console.print(f"[dim]Details: {e!s}[/dim]")
    raise typer.Exit(1) from None


app = typer.Typer(help="Manage API keys")


@app.command("create")
def create_key(
    name: str = typer.Option(..., "--name", "-n", help="Name for the API key"),
    client_id: str = typer.Option(..., "--client-id", "-c", help="Client identifier"),
) -> None:
    """Create a new API key."""

    async def _create() -> None:
        try:
            async with get_session_factory()() as db:
                data = APIKeyCreate(name=name, client_id=client_id)
                result = await APIKeyService.create_key(db, data)
                await db.commit()

                console.print()
                console.print("[bold green]API Key created successfully![/bold green]")
                console.print()
                console.print(f"[bold]Name:[/bold] {result.name}")
                console.print(f"[bold]Client ID:[/bold] {result.client_id}")
                console.print(f"[bold]Prefix:[/bold] {result.key_prefix}")
                console.print()
                console.print(
                    "[bold yellow]IMPORTANT: Save this key now - "
                    "it will only be shown once![/bold yellow]"
                )
                console.print()
                console.print(f"[bold cyan]{result.key}[/bold cyan]")
                console.print()
        except SQLAlchemyError as e:
            handle_db_error(e)

    run_async(_create())


@app.command("list")
def list_keys(
    limit: int = typer.Option(50, "--limit", "-l", help="Maximum keys to show"),
) -> None:
    """List all API keys."""

    async def _list() -> None:
        try:
            async with get_session_factory()() as db:
                keys, total = await APIKeyService.list_keys(db, skip=0, limit=limit)

                if not keys:
                    console.print("[yellow]No API keys found.[/yellow]")
                    return

                table = Table(title=f"API Keys ({total} total)")
                table.add_column("Prefix", style="cyan")
                table.add_column("Name")
                table.add_column("Client ID")
                table.add_column("Status")
                table.add_column("Last Used")
                table.add_column("Created")

                for key in keys:
                    status = (
                        "[green]active[/green]"
                        if key.is_active
                        else "[red]revoked[/red]"
                    )
                    last_used = (
                        key.last_used_at.strftime("%Y-%m-%d %H:%M")
                        if key.last_used_at
                        else "[dim]never[/dim]"
                    )
                    created = key.created_at.strftime("%Y-%m-%d %H:%M")

                    table.add_row(
                        key.key_prefix,
                        key.name,
                        key.client_id,
                        status,
                        last_used,
                        created,
                    )

                console.print(table)
        except SQLAlchemyError as e:
            handle_db_error(e)

    run_async(_list())


@app.command("revoke")
def revoke_key(
    prefix: str = typer.Argument(..., help="Key prefix or ID to revoke"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation prompt"),
) -> None:
    """Revoke an API key."""

    async def _revoke() -> None:
        try:
            async with get_session_factory()() as db:
                # Try to find by prefix first
                key = await APIKeyService.get_key_by_prefix(db, prefix)

                if not key:
                    # Try by ID
                    key = await APIKeyService.get_key_by_id(db, prefix)

                if not key:
                    console.print(
                        f"[red]No API key found with prefix/ID: {prefix}[/red]"
                    )
                    raise typer.Exit(1)

                if not key.is_active:
                    console.print(
                        f"[yellow]Key '{key.name}' is already revoked.[/yellow]"
                    )
                    return

                if not force:
                    console.print(
                        f"[bold]Key to revoke:[/bold] {key.name} ({key.key_prefix})"
                    )
                    confirm = typer.confirm("Are you sure you want to revoke this key?")
                    if not confirm:
                        console.print("[dim]Cancelled.[/dim]")
                        raise typer.Exit(0)

                success = await APIKeyService.revoke_key(db, key.id)
                await db.commit()

                if success:
                    console.print(
                        f"[green]Successfully revoked key '{key.name}' "
                        f"({key.key_prefix})[/green]"
                    )
                else:
                    console.print("[red]Failed to revoke key.[/red]")
                    raise typer.Exit(1)
        except SQLAlchemyError as e:
            handle_db_error(e)

    run_async(_revoke())


@app.command("info")
def key_info(
    prefix: str = typer.Argument(..., help="Key prefix or ID to show"),
) -> None:
    """Show detailed information about an API key."""

    async def _info() -> None:
        try:
            async with get_session_factory()() as db:
                # Try to find by prefix first
                key = await APIKeyService.get_key_by_prefix(db, prefix)

                if not key:
                    # Try by ID
                    key = await APIKeyService.get_key_by_id(db, prefix)

                if not key:
                    console.print(
                        f"[red]No API key found with prefix/ID: {prefix}[/red]"
                    )
                    raise typer.Exit(1)

                console.print()
                console.print("[bold]API Key Details[/bold]")
                console.print("─" * 40)
                console.print(f"[bold]ID:[/bold] {key.id}")
                console.print(f"[bold]Name:[/bold] {key.name}")
                console.print(f"[bold]Client ID:[/bold] {key.client_id}")
                console.print(f"[bold]Prefix:[/bold] {key.key_prefix}")

                status = (
                    "[green]Active[/green]" if key.is_active else "[red]Revoked[/red]"
                )
                console.print(f"[bold]Status:[/bold] {status}")

                console.print(
                    f"[bold]Created:[/bold] {key.created_at.strftime('%Y-%m-%d %H:%M:%S %Z')}"
                )

                if key.last_used_at:
                    console.print(
                        f"[bold]Last Used:[/bold] "
                        f"{key.last_used_at.strftime('%Y-%m-%d %H:%M:%S %Z')}"
                    )
                else:
                    console.print("[bold]Last Used:[/bold] [dim]Never[/dim]")

                if key.revoked_at:
                    console.print(
                        f"[bold]Revoked At:[/bold] "
                        f"{key.revoked_at.strftime('%Y-%m-%d %H:%M:%S %Z')}"
                    )

                console.print()
        except SQLAlchemyError as e:
            handle_db_error(e)

    run_async(_info())
