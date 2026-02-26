"""
Resume and sessions commands for CAI REPL.

This module provides commands for managing and resuming sessions:
- /resume: Resume a previous session
- /sessions: List recent sessions
"""

from datetime import datetime
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.table import Table

from cai.repl.commands.base import Command, register_command
from cai.repl.session_resume import (
    get_session_metadata,
    list_recent_sessions,
    load_session_into_agent,
    resume_session,
)
from cai.sdk.agents.simple_agent_manager import AGENT_MANAGER

console = Console()


class ResumeCommand(Command):
    """Command for resuming a previous session."""

    def __init__(self):
        """Initialize the resume command."""
        super().__init__(
            name="/resume",
            description="Resume a previous session and load its conversation history",
            aliases=["/r"],
        )

    def handle(self, args: Optional[list[str]] = None) -> bool:
        """Handle the resume command.

        Args:
            args: Optional list of command arguments.
                  - No args: resume last session
                  - session ID or file path: resume specific session

        Returns:
            True if the command was handled successfully, False otherwise
        """
        # Determine the log path
        log_path = None
        show_full = False

        if args:
            for arg in args:
                if arg == "--full" or arg == "-f":
                    show_full = True
                elif arg.startswith("-"):
                    console.print(f"[yellow]Unknown option: {arg}[/yellow]")
                else:
                    # It's either a file path or session ID
                    if arg.endswith(".jsonl") or "/" in arg or "\\" in arg:
                        log_path = arg
                    else:
                        # Try to find matching session by ID
                        logs_dir = Path("logs")
                        if logs_dir.exists():
                            matching_files = list(logs_dir.glob(f"cai_{arg}*.jsonl"))
                            if matching_files:
                                matching_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
                                log_path = str(matching_files[0])
                            else:
                                console.print(f"[red]No session found matching ID: {arg}[/red]")
                                console.print("[dim]Use /sessions to list available sessions[/dim]")
                                return False

        # Resume the session
        messages, used_path, parallel_agents = resume_session(log_path, show_full_output=show_full)

        if not messages:
            console.print("[yellow]No messages to load from session[/yellow]")
            return True

        # Get the current active agent
        current_agent = AGENT_MANAGER.get_active_agent()
        if not current_agent:
            console.print("[red]No active agent to load history into[/red]")
            return False

        # Load messages into the agent
        success = load_session_into_agent(current_agent, messages)

        if success:
            console.print(
                "[green]Session resumed successfully. You can continue the conversation.[/green]"
            )

        return success


class SessionsCommand(Command):
    """Command for listing recent sessions."""

    def __init__(self):
        """Initialize the sessions command."""
        super().__init__(
            name="/sessions",
            description="List recent sessions available for resuming",
            aliases=["/sess"],
        )

    def handle(self, args: Optional[list[str]] = None) -> bool:
        """Handle the sessions command.

        Args:
            args: Optional list of command arguments.
                  - No args: list recent 10 sessions
                  - number: list that many sessions
                  - session ID: show details for specific session

        Returns:
            True if the command was handled successfully, False otherwise
        """
        limit = 10

        if args:
            if args[0].isdigit():
                limit = int(args[0])
            else:
                # Show details for specific session
                return self._show_session_details(args[0])

        sessions = list_recent_sessions(limit)

        if not sessions:
            console.print("[yellow]No sessions found in logs/ directory[/yellow]")
            return True

        # Create table
        table = Table(
            title=f"Recent Sessions (last {len(sessions)})",
            show_header=True,
            header_style="bold cyan",
        )
        table.add_column("ID", style="magenta", width=12)
        table.add_column("Date/Time", style="green")
        table.add_column("Agent", style="yellow")
        table.add_column("Messages", justify="right")
        table.add_column("Cost", justify="right", style="cyan")
        table.add_column("Duration", justify="right")

        for session in sessions:
            # Extract short ID from session_id
            session_id = session.get("session_id", "")
            short_id = session_id[:8] if session_id else "-"

            # Format start time
            start_time = session.get("start_time", "")
            if start_time:
                try:
                    # Parse ISO format
                    dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
                    formatted_time = dt.strftime("%Y-%m-%d %H:%M")
                except (ValueError, AttributeError):
                    formatted_time = start_time[:16] if len(start_time) > 16 else start_time
            else:
                # Use file modification time as fallback
                file_path = session.get("file_path", "")
                if file_path and Path(file_path).exists():
                    mtime = Path(file_path).stat().st_mtime
                    formatted_time = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")
                else:
                    formatted_time = "-"

            # Agent name
            agent_name = session.get("agent_name", "-")
            if agent_name and len(agent_name) > 20:
                agent_name = agent_name[:17] + "..."

            # Message count
            msg_count = str(session.get("message_count", 0))

            # Cost
            cost = session.get("total_cost", 0.0)
            cost_str = f"${cost:.4f}" if cost > 0 else "-"

            # Duration
            active = session.get("active_time", 0)
            idle = session.get("idle_time", 0)
            total_secs = active + idle
            if total_secs > 0:
                mins, secs = divmod(int(total_secs), 60)
                hours, mins = divmod(mins, 60)
                if hours > 0:
                    duration = f"{hours}h {mins}m"
                elif mins > 0:
                    duration = f"{mins}m {secs}s"
                else:
                    duration = f"{secs}s"
            else:
                duration = "-"

            table.add_row(short_id, formatted_time, agent_name, msg_count, cost_str, duration)

        console.print(table)
        console.print()
        console.print("[dim]Usage:[/dim]")
        console.print("  [cyan]/resume[/cyan]            - Resume the last session")
        console.print("  [cyan]/resume <id>[/cyan]       - Resume a specific session by ID")
        console.print("  [cyan]/resume <path>[/cyan]     - Resume from a specific log file")
        console.print("  [cyan]/sessions <n>[/cyan]      - Show last n sessions")

        return True

    def _show_session_details(self, session_arg: str) -> bool:
        """Show details for a specific session."""
        # Find the session file
        log_path = None

        if session_arg.endswith(".jsonl") or "/" in session_arg:
            log_path = session_arg
        else:
            logs_dir = Path("logs")
            if logs_dir.exists():
                matching_files = list(logs_dir.glob(f"cai_{session_arg}*.jsonl"))
                if matching_files:
                    matching_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
                    log_path = str(matching_files[0])

        if not log_path or not Path(log_path).exists():
            console.print(f"[red]Session not found: {session_arg}[/red]")
            return False

        metadata = get_session_metadata(log_path)

        console.print("\n[bold cyan]Session Details[/bold cyan]")
        console.print(f"[dim]{'=' * 50}[/dim]")
        console.print(f"File: {log_path}")
        console.print(f"Session ID: {metadata.get('session_id', 'N/A')}")
        console.print(f"Start: {metadata.get('start_time', 'N/A')}")
        console.print(f"End: {metadata.get('end_time', 'N/A')}")
        console.print(f"Model: {metadata.get('model', 'N/A')}")
        console.print(f"Agent: {metadata.get('agent_name', 'N/A')}")
        console.print(f"Messages: {metadata.get('message_count', 0)}")
        console.print(f"Total Cost: ${metadata.get('total_cost', 0.0):.4f}")

        active = metadata.get("active_time", 0)
        idle = metadata.get("idle_time", 0)
        console.print(f"Active Time: {active:.1f}s")
        console.print(f"Idle Time: {idle:.1f}s")

        console.print()
        console.print(f"[dim]Use '/resume {session_arg}' to resume this session[/dim]")

        return True


# Register the commands
register_command(ResumeCommand())
register_command(SessionsCommand())
