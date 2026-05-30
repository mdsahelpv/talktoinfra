"""Interactive chat mode — the main user interface."""

import click

from talktoinfra_cli.config import CLIConfig
from talktoinfra_cli.client.api import APIClient
from talktoinfra_cli.ui.chat import ChatUI


@click.command()
@click.option("--session", "-s", default="", help="Session ID to resume")
@click.option("--url", "-u", default="", help="Orchestrator URL")
def chat_cmd(session: str, url: str):
    """Start an interactive chat session."""
    config = CLIConfig()
    base_url = url or config.orchestrator_url
    api_key = config.api_key

    client = APIClient(base_url, api_key)

    try:
        health = client.health()
        click.echo(f"✅ Connected to orchestrator at {base_url}")
    except Exception as e:
        click.echo(f"❌ Cannot connect to orchestrator: {e}")
        return

    if not session:
        resp = client.create_session("Interactive chat")
        session = resp.get("session_id", "")
        config.set("default_session_id", session)

    ui = ChatUI(client, session)
    ui.run()
