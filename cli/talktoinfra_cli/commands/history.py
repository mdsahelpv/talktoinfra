"""View audit log and history."""

import click
from rich.console import Console
from rich.table import Table

from talktoinfra_cli.config import CLIConfig
from talktoinfra_cli.client.api import APIClient

console = Console()


@click.command()
@click.option("--session", "-s", default="", help="Filter by session ID")
@click.option("--limit", "-l", default=20, help="Number of entries")
@click.option("--url", "-u", default="", help="Orchestrator URL")
def history_cmd(session: str, limit: int, url: str):
    """View audit log of past actions."""
    config = CLIConfig()
    client = APIClient(url or config.orchestrator_url, config.api_key)

    try:
        resp = client.get_audit_log(session, limit)
        entries = resp.get("entries", [])
        if not entries:
            console.print("[yellow]No audit entries found[/yellow]")
            return
        table = Table(title="Audit Log")
        table.add_column("Timestamp", style="cyan")
        table.add_column("Action")
        table.add_column("Tier")
        table.add_column("Approved")
        table.add_column("Status")
        for e in entries:
            table.add_row(
                str(e.get("timestamp", ""))[:19],
                e.get("action", ""),
                e.get("tier", ""),
                "✅" if e.get("approved") else "❌",
                e.get("status", ""),
            )
        console.print(table)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
