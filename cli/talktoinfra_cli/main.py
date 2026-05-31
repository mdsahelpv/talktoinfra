"""CLI entry point."""

import click

from talktoinfra_cli.commands.chat import chat_cmd
from talktoinfra_cli.commands.ask import ask_cmd
from talktoinfra_cli.commands.session import session_cmd
from talktoinfra_cli.commands.status import status_cmd
from talktoinfra_cli.commands.history import history_cmd
from talktoinfra_cli.commands.config import config_cmd
from talktoinfra_cli.commands.netscan import netscan_cmd


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """TalkToInfra — AI-native infrastructure copilot.

    Talk to your infrastructure in natural language.
    """


cli.add_command(chat_cmd)
cli.add_command(ask_cmd)
cli.add_command(session_cmd)
cli.add_command(status_cmd)
cli.add_command(history_cmd)
cli.add_command(config_cmd)
cli.add_command(netscan_cmd)

if __name__ == "__main__":
    cli()
