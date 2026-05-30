"""Interactive chat UI using Rich."""

import sys
from datetime import datetime

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.markdown import Markdown
from rich.live import Live
from rich.spinner import Spinner
from rich.table import Table
from rich import box

from talktoinfra_cli.client.api import APIClient

console = Console()


class ChatUI:
    def __init__(self, client: APIClient, session_id: str):
        self.client = client
        self.session_id = session_id

    def run(self):
        console.clear()
        self._print_header()

        while True:
            try:
                prompt_text = "[bold cyan]You[/bold cyan]"
                user_input = Prompt.ask(prompt_text)

                if user_input.lower() in ("/quit", "/exit", "exit", "quit"):
                    break
                if user_input.lower() == "/help":
                    self._show_help()
                    continue
                if user_input.lower() == "/status":
                    self._show_status()
                    continue

                self._show_thinking()
                resp = self.client.chat(user_input, self.session_id)

                if resp.get("session_id"):
                    self.session_id = resp["session_id"]

                console.print()
                self._print_assistant(resp)

                if resp.get("requires_approval"):
                    self._handle_approval(resp)

                console.print()

            except KeyboardInterrupt:
                break
            except Exception as e:
                console.print(f"\n[red]Error: {e}[/red]")

    def _print_header(self):
        header = Panel(
            "[bold cyan]TalkToInfra[/bold cyan] — AI Infrastructure Copilot\n"
            f"Session: {self.session_id[:8]}...  "
            "Type [bold]/help[/bold] for commands, [bold]/quit[/bold] to exit",
            box=box.ROUNDED,
        )
        console.print(header)

    def _show_thinking(self):
        with Live(Spinner("dots", text="Thinking..."), refresh_per_second=10):
            pass

    def _print_assistant(self, resp: dict):
        message = resp.get("message", "")
        tool_calls = resp.get("tool_calls", [])

        if message:
            console.print(Panel(Markdown(message), title="🤖 Assistant", border_style="green"))

        if tool_calls:
            table = Table(title="Tool Calls", box=box.SIMPLE)
            table.add_column("Action", style="cyan")
            table.add_column("Parameters")
            for tc in tool_calls:
                params_str = ", ".join(f"{k}={v}" for k, v in tc.get("parameters", {}).items())
                table.add_row(tc["action"], params_str[:80])
            console.print(table)

    def _handle_approval(self, resp: dict):
        approval_id = resp.get("approval_id")
        if not approval_id:
            return

        console.print("\n[yellow]⚠️  This action requires your approval[/yellow]")
        if Confirm.ask("Approve this action?"):
            result = self.client.approve(approval_id, True, "Approved via CLI")
            console.print(f"[green]✅ Approved: {result.get('tool_call_id', 'done')}[/green]")
        else:
            self.client.approve(approval_id, False, "Denied via CLI")
            console.print("[red]❌ Action denied[/red]")

    def _show_help(self):
        help_text = """
## Commands
| Command | Description |
|---------|-------------|
| `/help` | Show this help |
| `/status` | Show system status |
| `/quit` | Exit the chat |

## Example Questions
- "Are there any failing pods in production?"
- "What's the IP of the DNS server?"
- "Where is the AD server located?"
- "Show me all EC2 instances in us-east-1"
- "Check disk usage on web-server-01"
- "Restart the payment-service deployment"
        """
        console.print(Panel(Markdown(help_text), title="Help", border_style="blue"))

    def _show_status(self):
        try:
            health = self.client.health()
            tools = self.client.list_tools()
            console.print(Panel(
                f"[bold]Orchestrator:[/bold] {health.get('service', '?')} "
                f"[green]v{health.get('version', '?')}[/green]\n"
                f"[bold]Tools:[/bold] {tools.get('total', 0)} available\n"
                f"[bold]Session:[/bold] {self.session_id[:8]}...",
                title="Status",
                border_style="blue",
            ))
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
