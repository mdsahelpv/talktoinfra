"""Status commands — check agent health and available tools."""

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from talktoinfra_cli.config import CLIConfig
from talktoinfra_cli.client.api import APIClient

console = Console()


@click.command()
@click.option("--url", "-u", default="", help="Orchestrator URL")
def status_cmd(url: str):
    """Show orchestrator and agent status."""
    config = CLIConfig()
    client = APIClient(url or config.orchestrator_url, config.api_key)

    try:
        health = client.health()
        console.print(Panel(f"[bold green]Orchestrator:[/bold green] {health.get('service', 'unknown')}\n"
                           f"[bold]Version:[/bold] {health.get('version', '?')}\n"
                           f"[bold]Healthy:[/bold] {health.get('healthy', False)}",
                           title="System Health"))
    except Exception as e:
        console.print(f"[red]Orchestrator: Unreachable ({e})[/red]")
        return

    try:
        tools = client.list_tools()
        tool_list = tools.get("tools", [])
        table = Table(title=f"Available Tools ({tools.get('total', len(tool_list))})")
        table.add_column("Tool", style="cyan")
        table.add_column("Category")
        table.add_column("Tier")
        table.add_column("Description")
        for t in tool_list:
            tier_color = {"read": "green", "mutate": "yellow", "destructive": "red"}.get(t["tier"], "white")
            table.add_row(t["name"], t["category"], f"[{tier_color}]{t['tier']}[/{tier_color}]", t["description"][:60])
        console.print(table)
    except Exception as e:
        console.print(f"[red]Error fetching tools: {e}[/red]")

    try:
        agents = client.list_agents()
        agent_list = agents.get("agents", [])
        table = Table(title="Agents")
        table.add_column("Agent", style="cyan")
        table.add_column("Description")
        table.add_column("Tools")
        for a in agent_list:
            table.add_row(a["name"], a["description"][:50], ", ".join(a.get("tools", [])[:5]))
        console.print(table)
    except Exception as e:
        pass
