"""Single question mode — ask one question, get an answer."""

import json
import click

from talktoinfra_cli.config import CLIConfig
from talktoinfra_cli.client.api import APIClient


@click.command()
@click.argument("question")
@click.option("--session", "-s", default="", help="Session ID")
@click.option("--url", "-u", default="", help="Orchestrator URL")
@click.option("--json-output", "-j", is_flag=True, help="Output as JSON")
def ask_cmd(question: str, session: str, url: str, json_output: bool):
    """Ask a single question about your infrastructure."""
    config = CLIConfig()
    base_url = url or config.orchestrator_url
    api_key = config.api_key

    client = APIClient(base_url, api_key)
    client._http = type(client._http)(timeout=120)

    try:
        resp = client.chat(question, session or config.default_session_id)
        if json_output:
            click.echo(json.dumps(resp, indent=2))
        else:
            click.echo()
            click.echo(resp.get("message", ""))

            if resp.get("requires_approval"):
                click.echo()
                click.echo("⚠️  This action requires approval.")
        if resp.get("session_id"):
            config.set("default_session_id", resp["session_id"])
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
