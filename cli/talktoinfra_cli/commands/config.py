"""CLI configuration commands."""

import click

from talktoinfra_cli.config import CLIConfig


@click.group()
def config_cmd():
    """Manage CLI configuration."""


@config_cmd.command("set")
@click.argument("key")
@click.argument("value")
def set_config(key: str, value: str):
    """Set a config value (e.g. orchestrator_url, api_key)."""
    config = CLIConfig()
    config.set(key, value)
    click.echo(f"Set {key} = {value}")


@config_cmd.command("show")
def show_config():
    """Show current configuration."""
    config = CLIConfig()
    click.echo(f"orchestrator_url: {config.orchestrator_url}")
    click.echo(f"api_key: {'****' if config.api_key else '(not set)'}")
    click.echo(f"default_session_id: {config.default_session_id or '(none)'}")


@config_cmd.command("reset")
def reset_config():
    """Reset all configuration."""
    config = CLIConfig()
    import json
    from pathlib import Path
    config_file = Path.home() / ".talktoinfra" / "config.json"
    config_file.write_text(json.dumps({}))
    click.echo("Configuration reset")
