"""Session management commands."""

import click
from rich.console import Console
from rich.table import Table

from talktoinfra_cli.config import CLIConfig
from talktoinfra_cli.client.api import APIClient

console = Console()


@click.group()
def session_cmd():
    """Manage chat sessions."""


@session_cmd.command("list")
@click.option("--url", "-u", default="", help="Orchestrator URL")
def list_sessions(url: str):
    """List all sessions."""
    config = CLIConfig()
    client = APIClient(url or config.orchestrator_url, config.api_key)
    try:
        resp = client.list_sessions()
        sessions = resp.get("sessions", [])
        if not sessions:
            console.print("[yellow]No sessions found[/yellow]")
            return
        table = Table(title="Sessions")
        table.add_column("ID", style="cyan")
        table.add_column("Description")
        table.add_column("Messages", justify="right")
        table.add_column("Status")
        table.add_column("Last Active")
        for s in sessions:
            table.add_row(
                s["id"][:8],
                s.get("description", "")[:40],
                str(s.get("message_count", 0)),
                s.get("status", ""),
                s.get("last_active", "")[:19],
            )
        console.print(table)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


@session_cmd.command("create")
@click.argument("description", default="")
@click.option("--url", "-u", default="", help="Orchestrator URL")
def create_session(description: str, url: str):
    """Create a new session."""
    config = CLIConfig()
    client = APIClient(url or config.orchestrator_url, config.api_key)
    resp = client.create_session(description or f"Session {__import__('datetime').datetime.now()}")
    sid = resp.get("session_id", "")
    config.set("default_session_id", sid)
    click.echo(f"Created session: {sid}")
