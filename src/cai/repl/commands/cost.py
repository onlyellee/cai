"""
Cost command for CAI REPL.
This module provides commands for viewing usage costs and statistics.
"""

from typing import List, Optional
from datetime import datetime, timedelta
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns
from rich.progress import Progress, BarColumn, TextColumn
from rich import box

from cai.repl.commands.base import Command, register_command
from cai.sdk.agents.global_usage_tracker import GLOBAL_USAGE_TRACKER
from cai.util import COST_TRACKER
from cai.i18n import t

console = Console()


class CostCommand(Command):
    """
    Command for viewing usage costs and statistics.

    This command displays:
    - Current session costs
    - Global usage statistics
    - Model-specific costs
    - Daily usage breakdown
    - Recent session history
    """

    def __init__(self):
        """Initialize the cost command."""
        super().__init__(
            name="/cost",
            description="View usage costs and statistics",
            aliases=["/costs", "/usage"],
        )

        # Add subcommands
        self.add_subcommand("summary", "Show cost summary", self.handle_summary)
        self.add_subcommand("models", "Show costs by model", self.handle_models)
        self.add_subcommand("daily", "Show daily usage", self.handle_daily)
        self.add_subcommand("sessions", "Show recent sessions", self.handle_sessions)
        self.add_subcommand("reset", "Reset usage statistics", self.handle_reset)

    def handle(self, args: Optional[List[str]] = None) -> bool:
        """
        Handle the /cost command.

        Args:
            args: Optional list of command arguments

        Returns:
            bool: True if the command was handled successfully
        """
        if not args:
            return self.handle_summary()

        # Check if it's a subcommand
        subcommand = args[0].lower()
        if subcommand in self.subcommands:
            handler = self.subcommands[subcommand]["handler"]
            return handler(args[1:] if len(args) > 1 else [])

        # Default to summary
        return self.handle_summary()

    def handle_summary(self, args: Optional[List[str]] = None) -> bool:
        """Display cost summary including current session and global totals."""
        console.print(f"\n[bold cyan]💰 {t('cost_summary_title')}[/bold cyan]")
        console.print("=" * 40)

        # Current Session Panel
        session_content = self._get_session_summary()
        session_panel = Panel(
            session_content,
            title=f"[cyan]{t('cost_current_session')}[/cyan]",
            border_style="cyan",
            box=box.ROUNDED,
            padding=(1, 2),
        )

        # Global Usage Panel
        global_content = self._get_global_summary()
        global_panel = Panel(
            global_content,
            title=f"[green]{t('cost_global_usage')}[/green]",
            border_style="green",
            box=box.ROUNDED,
            padding=(1, 2),
        )

        # Display panels side by side if terminal is wide enough
        terminal_width = console.width
        if terminal_width > 100:
            console.print(Columns([session_panel, global_panel], equal=True, expand=True))
        else:
            console.print(session_panel)
            console.print(global_panel)

        # Show top models
        self._show_top_models_mini()

        # Show helpful commands
        console.print(f"\n[dim]{t('cost_hint_models')}[/dim]")
        console.print(f"[dim]{t('cost_hint_daily')}[/dim]")
        console.print(f"[dim]{t('cost_hint_sessions')}[/dim]")

        return True

    def _get_session_summary(self) -> str:
        """Get formatted current session summary."""
        lines = []

        # Session cost
        session_cost = COST_TRACKER.session_total_cost
        lines.append(f"[bold]{t('cost_total_cost')}[/bold] [yellow]${session_cost:.6f}[/yellow]")

        # Current agent costs
        if hasattr(COST_TRACKER, "current_agent_total_cost"):
            agent_cost = COST_TRACKER.current_agent_total_cost
            if agent_cost > 0:
                lines.append(f"[bold]{t('cost_current_agent_cost')}[/bold] ${agent_cost:.6f}")

        # Token usage
        if hasattr(COST_TRACKER, "current_agent_input_tokens"):
            input_tokens = COST_TRACKER.current_agent_input_tokens
            output_tokens = COST_TRACKER.current_agent_output_tokens
            total_tokens = input_tokens + output_tokens

            lines.append("")
            lines.append(f"[bold]{t('cost_tokens_used')}[/bold]")
            lines.append(f"  {t('cost_input')}  {input_tokens:,}")
            lines.append(f"  {t('cost_output')} {output_tokens:,}")
            lines.append(f"  {t('cost_total')}  {total_tokens:,}")

        return "\n".join(lines)

    def _get_global_summary(self) -> str:
        """Get formatted global usage summary."""
        lines = []

        if not GLOBAL_USAGE_TRACKER.enabled:
            lines.append(f"[yellow]{t('cost_tracking_disabled')}[/yellow]")
            lines.append(f"[dim]{t('cost_tracking_enable_hint')}[/dim]")
            return "\n".join(lines)

        summary = GLOBAL_USAGE_TRACKER.get_summary()
        totals = summary.get("global_totals", {})

        # Global cost
        total_cost = totals.get("total_cost", 0.0)
        lines.append(f"[bold]{t('cost_total_cost')}[/bold] [green]${total_cost:.6f}[/green]")

        # Sessions
        total_sessions = totals.get("total_sessions", 0)
        lines.append(f"[bold]{t('cost_total_sessions')}[/bold] {total_sessions}")

        # Requests
        total_requests = totals.get("total_requests", 0)
        lines.append(f"[bold]{t('cost_total_requests')}[/bold] {total_requests:,}")

        # Tokens
        input_tokens = totals.get("total_input_tokens", 0)
        output_tokens = totals.get("total_output_tokens", 0)
        total_tokens = input_tokens + output_tokens

        lines.append("")
        lines.append(f"[bold]{t('cost_total_tokens')}[/bold]")
        lines.append(f"  {t('cost_input')}  {input_tokens:,}")
        lines.append(f"  {t('cost_output')} {output_tokens:,}")
        lines.append(f"  {t('cost_total')}  {total_tokens:,}")

        # Average cost per session
        if total_sessions > 0:
            avg_cost = total_cost / total_sessions
            lines.append("")
            lines.append(f"[bold]{t('cost_avg_per_session')}[/bold] ${avg_cost:.6f}")

        return "\n".join(lines)

    def _show_top_models_mini(self):
        """Show a mini view of top models by cost."""
        if not GLOBAL_USAGE_TRACKER.enabled:
            return

        summary = GLOBAL_USAGE_TRACKER.get_summary()
        top_models = summary.get("top_models", [])

        if not top_models:
            return

        console.print(f"\n[bold]{t('cost_top_models')}[/bold]")

        # Create a simple bar chart
        max_cost = top_models[0][1] if top_models else 0

        for model, cost in top_models[:3]:  # Show top 3
            if max_cost > 0:
                bar_length = int((cost / max_cost) * 30)
                bar = "█" * bar_length
            else:
                bar = ""

            console.print(f"  {model:<20} {bar:<30} ${cost:.4f}")

    def handle_models(self, args: Optional[List[str]] = None) -> bool:
        """Show detailed costs by model."""
        if not GLOBAL_USAGE_TRACKER.enabled:
            console.print(f"[yellow]{t('cost_tracking_disabled')}[/yellow]")
            return True

        usage_data = GLOBAL_USAGE_TRACKER.usage_data
        model_usage = usage_data.get("model_usage", {})

        if not model_usage:
            console.print(f"[yellow]{t('cost_no_model_usage')}[/yellow]")
            return True

        # Create detailed model table
        table = Table(
            title=f"[bold cyan]{t('cost_model_usage_title')}[/bold cyan]",
            show_header=True,
            header_style="bold",
            box=box.ROUNDED,
        )

        table.add_column(t('cost_col_model'), style="cyan", no_wrap=True)
        table.add_column(t('cost_col_total_cost'), style="green", justify="right")
        table.add_column(t('cost_col_requests'), style="yellow", justify="right")
        table.add_column(t('cost_col_input_tokens'), style="blue", justify="right")
        table.add_column(t('cost_col_output_tokens'), style="magenta", justify="right")
        table.add_column(t('cost_col_avg_cost'), style="white", justify="right")

        # Sort by cost descending
        sorted_models = sorted(
            model_usage.items(), key=lambda x: x[1].get("total_cost", 0), reverse=True
        )

        total_cost = 0
        total_requests = 0
        total_input = 0
        total_output = 0

        for model, stats in sorted_models:
            cost = stats.get("total_cost", 0)
            requests = stats.get("total_requests", 0)
            input_tokens = stats.get("total_input_tokens", 0)
            output_tokens = stats.get("total_output_tokens", 0)

            avg_cost = cost / requests if requests > 0 else 0

            total_cost += cost
            total_requests += requests
            total_input += input_tokens
            total_output += output_tokens

            table.add_row(
                model,
                f"${cost:.6f}",
                f"{requests:,}",
                f"{input_tokens:,}",
                f"{output_tokens:,}",
                f"${avg_cost:.6f}",
            )

        # Add totals row
        table.add_section()
        table.add_row(
            f"[bold]{t('cost_total_label')}[/bold]",
            f"[bold]${total_cost:.6f}[/bold]",
            f"[bold]{total_requests:,}[/bold]",
            f"[bold]{total_input:,}[/bold]",
            f"[bold]{total_output:,}[/bold]",
            "",
        )

        console.print(table)

        # Show cost breakdown pie chart (text-based)
        if len(sorted_models) > 0:
            console.print(f"\n[bold]{t('cost_distribution')}[/bold]")
            for model, stats in sorted_models[:5]:  # Top 5
                cost = stats.get("total_cost", 0)
                percentage = (cost / total_cost * 100) if total_cost > 0 else 0
                bar_length = int(percentage / 2)  # Scale to 50 chars max
                bar = "█" * bar_length
                console.print(f"  {model:<25} {bar:<25} {percentage:>5.1f}%")

        return True

    def handle_daily(self, args: Optional[List[str]] = None) -> bool:
        """Show daily usage breakdown."""
        if not GLOBAL_USAGE_TRACKER.enabled:
            console.print(f"[yellow]{t('cost_tracking_disabled')}[/yellow]")
            return True

        usage_data = GLOBAL_USAGE_TRACKER.usage_data
        daily_usage = usage_data.get("daily_usage", {})

        if not daily_usage:
            console.print(f"[yellow]{t('cost_no_daily_usage')}[/yellow]")
            return True

        # Create daily usage table
        table = Table(
            title=f"[bold cyan]{t('cost_daily_title')}[/bold cyan]",
            show_header=True,
            header_style="bold",
            box=box.ROUNDED,
        )

        table.add_column(t('cost_col_date'), style="cyan")
        table.add_column(t('cost_col_cost'), style="green", justify="right")
        table.add_column(t('cost_col_requests'), style="yellow", justify="right")
        table.add_column(t('cost_col_tokens'), style="blue", justify="right")
        table.add_column(t('cost_col_trend'), style="white", justify="center")

        # Sort by date descending
        sorted_days = sorted(daily_usage.items(), reverse=True)

        # Calculate trend
        costs = [stats.get("total_cost", 0) for _, stats in sorted_days]

        for i, (date, stats) in enumerate(sorted_days[:30]):  # Last 30 days
            cost = stats.get("total_cost", 0)
            requests = stats.get("total_requests", 0)
            tokens = stats.get("total_input_tokens", 0) + stats.get("total_output_tokens", 0)

            # Calculate trend
            if i < len(costs) - 1:
                prev_cost = costs[i + 1]
                if prev_cost > 0:
                    change = ((cost - prev_cost) / prev_cost) * 100
                    if change > 10:
                        trend = "[red]↑[/red]"
                    elif change < -10:
                        trend = "[green]↓[/green]"
                    else:
                        trend = "[yellow]→[/yellow]"
                else:
                    trend = "[dim]-[/dim]"
            else:
                trend = "[dim]-[/dim]"

            # Format date
            try:
                date_obj = datetime.strptime(date, "%Y-%m-%d")
                date_str = date_obj.strftime("%b %d, %Y")

                # Highlight today
                if date_obj.date() == datetime.now().date():
                    date_str = f"[bold]{date_str} ({t('cost_today')})[/bold]"
            except:
                date_str = date

            table.add_row(date_str, f"${cost:.6f}", f"{requests:,}", f"{tokens:,}", trend)

        console.print(table)

        # Show weekly summary
        self._show_weekly_summary(sorted_days)

        return True

    def _show_weekly_summary(self, sorted_days):
        """Show weekly cost summary."""
        if not sorted_days:
            return

        console.print(f"\n[bold]{t('cost_weekly_summary')}[/bold]")

        # Group by week
        weekly_costs = {}
        for date_str, stats in sorted_days:
            try:
                date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                week_start = date_obj - timedelta(days=date_obj.weekday())
                week_key = week_start.strftime("%Y-%m-%d")

                if week_key not in weekly_costs:
                    weekly_costs[week_key] = 0
                weekly_costs[week_key] += stats.get("total_cost", 0)
            except:
                continue

        # Show last 4 weeks
        sorted_weeks = sorted(weekly_costs.items(), reverse=True)[:4]

        for week_start, cost in sorted_weeks:
            try:
                week_date = datetime.strptime(week_start, "%Y-%m-%d")
                week_label = t('cost_week_of').format(date=week_date.strftime('%b %d'))
                console.print(f"  {week_label:<20} ${cost:.4f}")
            except:
                console.print(f"  {week_start:<20} ${cost:.4f}")

    def handle_sessions(self, args: Optional[List[str]] = None) -> bool:
        """Show recent session details."""
        if not GLOBAL_USAGE_TRACKER.enabled:
            console.print(f"[yellow]{t('cost_tracking_disabled')}[/yellow]")
            return True

        usage_data = GLOBAL_USAGE_TRACKER.usage_data
        sessions = usage_data.get("sessions", [])

        if not sessions:
            console.print(f"[yellow]{t('cost_no_session_data')}[/yellow]")
            return True

        # Show last N sessions (default 10)
        limit = 10
        if args and args[0].isdigit():
            limit = int(args[0])

        recent_sessions = sessions[-limit:]

        # Create sessions table
        table = Table(
            title=f"[bold cyan]{t('cost_recent_sessions').format(count=len(recent_sessions))}[/bold cyan]",
            show_header=True,
            header_style="bold",
            box=box.ROUNDED,
        )

        table.add_column(t('cost_col_session_id'), style="cyan", no_wrap=True)
        table.add_column(t('cost_col_start_time'), style="white")
        table.add_column(t('cost_col_duration'), style="yellow", justify="right")
        table.add_column(t('cost_col_cost'), style="green", justify="right")
        table.add_column(t('cost_col_requests'), style="blue", justify="right")
        table.add_column(t('cost_col_models_used'), style="magenta")

        for session in reversed(recent_sessions):  # Show newest first
            session_id = session.get("session_id", t('cost_unknown'))[:8] + "..."
            start_time = session.get("start_time", "")
            end_time = session.get("end_time")
            cost = session.get("total_cost", 0)
            requests = session.get("total_requests", 0)
            models = session.get("models_used", [])

            # Format start time
            try:
                start_dt = datetime.fromisoformat(start_time)
                start_str = start_dt.strftime("%Y-%m-%d %H:%M")
            except:
                start_str = t('cost_unknown')

            # Calculate duration
            if end_time:
                try:
                    start_dt = datetime.fromisoformat(start_time)
                    end_dt = datetime.fromisoformat(end_time)
                    duration = end_dt - start_dt

                    # Format duration
                    total_seconds = int(duration.total_seconds())
                    hours = total_seconds // 3600
                    minutes = (total_seconds % 3600) // 60
                    seconds = total_seconds % 60

                    if hours > 0:
                        duration_str = f"{hours}h {minutes}m"
                    elif minutes > 0:
                        duration_str = f"{minutes}m {seconds}s"
                    else:
                        duration_str = f"{seconds}s"
                except:
                    duration_str = t('cost_unknown')
            else:
                duration_str = f"[yellow]{t('cost_active')}[/yellow]"

            # Format models
            if models:
                models_str = ", ".join(models[:2])  # Show first 2
                if len(models) > 2:
                    models_str += f" (+{len(models)-2})"
            else:
                models_str = f"[dim]{t('cost_none')}[/dim]"

            table.add_row(
                session_id, start_str, duration_str, f"${cost:.6f}", str(requests), models_str
            )

        console.print(table)

        # Show session statistics
        active_sessions = sum(1 for s in sessions if not s.get("end_time"))
        completed_sessions = len(sessions) - active_sessions
        total_session_cost = sum(s.get("total_cost", 0) for s in sessions)

        console.print(f"\n[bold]{t('cost_session_stats')}[/bold]")
        console.print(f"  {t('cost_total_sessions_count').format(count=len(sessions))}")
        console.print(f"  {t('cost_active_sessions').format(count=active_sessions)}")
        console.print(f"  {t('cost_completed_sessions').format(count=completed_sessions)}")
        console.print(f"  {t('cost_total_all_sessions').format(cost=f'{total_session_cost:.6f}')}")

        if completed_sessions > 0:
            avg_session_cost = total_session_cost / len(sessions)
            console.print(f"  {t('cost_avg_session_cost').format(cost=f'{avg_session_cost:.6f}')}")

        return True

    def handle_reset(self, args: Optional[List[str]] = None) -> bool:
        """Reset usage statistics (with confirmation)."""
        if not GLOBAL_USAGE_TRACKER.enabled:
            console.print(f"[yellow]{t('cost_tracking_disabled')}[/yellow]")
            return True

        from pathlib import Path

        usage_file = Path.home() / ".cai" / "usage.json"

        if not usage_file.exists():
            console.print(f"[yellow]{t('cost_no_usage_data')}[/yellow]")
            return True

        # Show current totals before reset
        summary = GLOBAL_USAGE_TRACKER.get_summary()
        totals = summary.get("global_totals", {})
        total_cost = totals.get("total_cost", 0)
        total_sessions = totals.get("total_sessions", 0)

        console.print(f"\n[bold red]Warning:[/bold red] {t('cost_reset_warning')}")
        console.print(t('cost_reset_current').format(cost=f'{total_cost:.6f}', sessions=total_sessions))

        # Require explicit confirmation
        console.print(f"\n{t('cost_reset_confirm')}")
        confirmation = console.input("> ")

        if confirmation == "RESET":
            # Create backup
            import shutil
            from datetime import datetime

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = usage_file.with_name(f"usage_backup_{timestamp}.json")
            shutil.copy2(usage_file, backup_file)
            console.print(f"[green]{t('cost_backup_created')}[/green] {backup_file}")

            # Reset the file
            usage_file.unlink()
            console.print(f"[green]{t('cost_reset_done')}[/green]")

            # Reinitialize the tracker
            GLOBAL_USAGE_TRACKER._initialized = False
            GLOBAL_USAGE_TRACKER.__init__()
        else:
            console.print(f"[yellow]{t('cost_reset_cancelled')}[/yellow]")

        return True


# Register the command
register_command(CostCommand())
