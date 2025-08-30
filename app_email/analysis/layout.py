from rich import box
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.layout import Layout
from rich.spinner import Spinner
from rich.markdown import Markdown

from .constants import (
    DEFAULT_MAX_TOOL_ARGS_LENGTH,
    DEFAULT_MAX_CONTENT_LENGTH,
    DEFAULT_MAX_DISPLAY_MESSAGES,
)


def create_layout():
    layout = Layout()
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="main"),
        Layout(name="footer", size=3),
    )
    layout["main"].split_column(Layout(name="upper", ratio=3), Layout(name="analysis", ratio=5))
    layout["upper"].split_row(Layout(name="progress", ratio=2), Layout(name="messages", ratio=3))
    return layout


def update_display(layout, message_buffer, spinner_text=None):
    layout["header"].update(
        Panel(
            "[bold green]Welcome to TradingAgents CLI[/bold green]\n[dim]© [Tauric Research](https://github.com/TauricResearch)[/dim]",
            title="Welcome to TradingAgents",
            border_style="green",
            padding=(1, 2),
            expand=True,
        )
    )

    progress_table = Table(
        show_header=True,
        header_style="bold magenta",
        show_footer=False,
        box=box.SIMPLE_HEAD,
        title=None,
        padding=(0, 2),
        expand=True,
    )
    progress_table.add_column("Team", style="cyan", justify="center", width=20)
    progress_table.add_column("Agent", style="green", justify="center", width=20)
    progress_table.add_column("Status", style="yellow", justify="center", width=20)

    teams = {
        "Analyst Team": [
            "Market Analyst",
            "Social Analyst",
            "News Analyst",
            "Fundamentals Analyst",
        ],
        "Research Team": ["Bull Researcher", "Bear Researcher", "Research Manager"],
        "Trading Team": ["Trader"],
        "Risk Management": ["Risky Analyst", "Neutral Analyst", "Safe Analyst"],
        "Portfolio Management": ["Portfolio Manager"],
    }

    for team, agents in teams.items():
        first_agent = agents[0]
        status = message_buffer.agent_status[first_agent]
        if status == "in_progress":
            status_cell = Spinner("dots", text="[blue]in_progress[/blue]", style="bold cyan")
        else:
            status_color = {"pending": "yellow", "completed": "green", "error": "red"}.get(status, "white")
            status_cell = f"[{status_color}]{status}[/{status_color}]"
        progress_table.add_row(team, first_agent, status_cell)

        for agent in agents[1:]:
            status = message_buffer.agent_status[agent]
            if status == "in_progress":
                status_cell = Spinner("dots", text="[blue]in_progress[/blue]", style="bold cyan")
            else:
                status_color = {"pending": "yellow", "completed": "green", "error": "red"}.get(status, "white")
                status_cell = f"[{status_color}]{status}[/{status_color}]"
            progress_table.add_row("", agent, status_cell)

        progress_table.add_row("─" * 20, "─" * 20, "─" * 20, style="dim")

    layout["progress"].update(Panel(progress_table, title="Progress", border_style="cyan", padding=(1, 2)))

    messages_table = Table(
        show_header=True,
        header_style="bold magenta",
        show_footer=False,
        expand=True,
        box=box.MINIMAL,
        show_lines=True,
        padding=(0, 1),
    )
    messages_table.add_column("Time", style="cyan", width=8, justify="center")
    messages_table.add_column("Type", style="green", width=10, justify="center")
    messages_table.add_column("Content", style="white", no_wrap=False, ratio=1)

    all_messages = []
    for timestamp, tool_name, args in message_buffer.tool_calls:
        if isinstance(args, str) and len(args) > DEFAULT_MAX_TOOL_ARGS_LENGTH:
            args = args[:97] + "..."
        all_messages.append((timestamp, "Tool", f"{tool_name}: {args}"))
    for timestamp, msg_type, content in message_buffer.messages:
        content_str = content if isinstance(content, str) else str(content)
        if len(content_str) > DEFAULT_MAX_CONTENT_LENGTH:
            content_str = content_str[:197] + "..."
        all_messages.append((timestamp, msg_type, content_str))
    all_messages.sort(key=lambda x: x[0])
    max_messages = DEFAULT_MAX_DISPLAY_MESSAGES
    recent_messages = all_messages[-max_messages:]
    for timestamp, msg_type, content in recent_messages:
        messages_table.add_row(timestamp, msg_type, Text(content, overflow="fold"))
    if spinner_text:
        messages_table.add_row("", "Spinner", spinner_text)
    if len(all_messages) > max_messages:
        messages_table.footer = f"[dim]Showing last {max_messages} of {len(all_messages)} messages[/dim]"

    layout["messages"].update(Panel(messages_table, title="Messages & Tools", border_style="blue", padding=(1, 2)))

    if message_buffer.current_report:
        layout["analysis"].update(
            Panel(Markdown(message_buffer.current_report), title="Current Report", border_style="green", padding=(1, 2))
        )
    else:
        layout["analysis"].update(
            Panel("[italic]Waiting for analysis report...[/italic]", title="Current Report", border_style="green", padding=(1, 2))
        )


