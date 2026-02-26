"""
Temperature and Top-P commands for CAI REPL.
This module provides commands for viewing and changing the agent's temperature and top_p.
"""

import os
from typing import List, Optional

from rich.console import Console
from rich.panel import Panel
from cai.repl.commands.base import Command, register_command
from cai.sdk.agents.model_settings import DEFAULT_TEMPERATURE, DEFAULT_TOP_P
from cai.i18n import t

console = Console()


class TemperatureCommand(Command):
    """Command for viewing and changing the agent's temperature."""

    def __init__(self):
        """Initialize the temperature command."""
        super().__init__(
            name="/temperature",
            description=t('temp_description'),
            aliases=["/temp"],
        )

    def handle(self, args: Optional[List[str]] = None) -> bool:
        """Handle the temperature command.

        Args:
            args: Optional list of command arguments

        Returns:
            True if the command was handled successfully, False otherwise
        """
        # Get current temperature
        current_temp = float(os.getenv("CAI_TEMPERATURE", str(DEFAULT_TEMPERATURE)))
        terminal_info = ""

        # In TUI mode, try to get the specific terminal's temperature
        if os.getenv("CAI_TUI_MODE") == "true":
            try:
                from cai.tui.cai_terminal import CAITerminal
                from cai.tui.core.terminal_tracking import get_current_terminal_id

                app = CAITerminal._instance
                if app and hasattr(app, 'session_manager'):
                    # Try to determine current terminal
                    terminal_number = None

                    # Method 1: Try to get terminal number from command handler context
                    import inspect
                    for frame_info in inspect.stack():
                        frame_locals = frame_info.frame.f_locals
                        if 'self' in frame_locals:
                            obj = frame_locals['self']
                            if hasattr(obj, 'terminal_number') and hasattr(obj, 'handle_command'):
                                terminal_number = obj.terminal_number
                                break

                    # Method 2: Try to get terminal ID and extract number
                    if terminal_number is None:
                        terminal_id = get_current_terminal_id()
                        if terminal_id:
                            import re
                            match = re.search(r'terminal-(\d+)', terminal_id)
                            if match:
                                terminal_number = int(match.group(1))

                    # Method 3: If still none, try to get from focused terminal
                    if terminal_number is None and hasattr(app, 'terminal_grid'):
                        focused_terminal = app.terminal_grid.get_focused_terminal()
                        if focused_terminal and hasattr(focused_terminal, 'state'):
                            terminal_number = focused_terminal.state.terminal_number

                    if terminal_number is not None:
                        runner = app.session_manager.terminal_runners.get(terminal_number)
                        if runner and runner.agent and hasattr(runner.agent, 'model'):
                            current_temp = runner.agent.model.temperature
                            terminal_info = f" (Terminal {terminal_number})"
            except Exception:
                pass

        if not args:
            # Display current temperature
            console.print(
                Panel(
                    f"{t('temp_current', terminal_info=terminal_info, current_temp=f'{current_temp:.1f}')}\n"
                    f"\n[cyan]{t('temp_info_header')}[/cyan]\n"
                    f"  • [bold]{t('temp_info_0')}[/bold]\n"
                    f"  • [bold]{t('temp_info_07')}[/bold]\n"
                    f"  • [bold]{t('temp_info_1')}[/bold]\n"
                    f"  • [bold]{t('temp_info_2')}[/bold]",
                    border_style="green",
                    title=t('temp_panel_title'),
                )
            )
            console.print(f"\n[cyan]{t('temp_usage')}[/cyan]")
            console.print(f"  [bold]{t('temp_usage_set')}[/bold]")
            console.print(f"  [bold]{t('temp_usage_alias')}[/bold]")
            return True

        # Parse temperature value
        try:
            new_temp = float(args[0])

            # Validate temperature range
            if not 0.0 <= new_temp <= 2.0:
                console.print(
                    Panel(
                        f"[red]{t('temp_invalid_value', value=new_temp)}[/red]\n"
                        f"{t('temp_invalid_range')}",
                        border_style="red",
                        title=t('temp_error_title'),
                    )
                )
                return True

        except ValueError:
            console.print(
                Panel(
                    f"[red]{t('temp_invalid_parse', value=args[0])}[/red]\n"
                    f"{t('temp_invalid_parse_hint')}",
                    border_style="red",
                    title=t('temp_error_title'),
                )
            )
            return True

        # Determine temperature description
        if new_temp <= 0.2:
            desc = t('temp_desc_very_focused')
        elif new_temp <= 0.5:
            desc = t('temp_desc_focused')
        elif new_temp <= 0.8:
            desc = t('temp_desc_balanced')
        elif new_temp <= 1.2:
            desc = t('temp_desc_creative')
        elif new_temp <= 1.5:
            desc = t('temp_desc_very_creative')
        else:
            desc = t('temp_desc_max_creative')

        # In TUI mode, only update the current terminal's temperature
        if os.getenv("CAI_TUI_MODE") == "true":
            # Import here to avoid circular imports
            try:
                from cai.tui.cai_terminal import CAITerminal
                from cai.tui.core.terminal_tracking import get_current_terminal_id

                app = CAITerminal._instance
                if app and hasattr(app, 'session_manager'):
                    # Try to determine current terminal from various sources
                    terminal_number = None

                    # Method 1: Try to get terminal number from command handler context
                    import inspect
                    for frame_info in inspect.stack():
                        frame_locals = frame_info.frame.f_locals
                        if 'self' in frame_locals:
                            obj = frame_locals['self']
                            # Check if this is a CommandHandler with terminal_number
                            if hasattr(obj, 'terminal_number') and hasattr(obj, 'handle_command'):
                                terminal_number = obj.terminal_number
                                break

                    # Method 2: Try to get terminal ID and extract number
                    if terminal_number is None:
                        terminal_id = get_current_terminal_id()
                        if terminal_id:
                            # Extract terminal number from ID (e.g., "terminal-1")
                            import re
                            match = re.search(r'terminal-(\d+)', terminal_id)
                            if match:
                                terminal_number = int(match.group(1))

                    # Method 3: If still none, try to get from focused terminal
                    if terminal_number is None and hasattr(app, 'terminal_grid'):
                        focused_terminal = app.terminal_grid.get_focused_terminal()
                        if focused_terminal and hasattr(focused_terminal, 'state'):
                            terminal_number = focused_terminal.state.terminal_number

                    if terminal_number is not None:
                        # Update only the specific terminal's runner
                        runner = app.session_manager.terminal_runners.get(terminal_number)
                        if runner:
                            if runner.agent and hasattr(runner.agent, 'model'):
                                runner.agent.model.temperature = new_temp
                                # Update the terminal's header to refresh tooltip
                                if hasattr(runner.terminal, '_update_header'):
                                    runner.terminal._update_header()
                                # Also refresh the terminal
                                if hasattr(runner.terminal, 'refresh'):
                                    runner.terminal.refresh()

                            # Display terminal-specific message
                            change_message = (
                                f"{t('temp_changed_for_terminal', value=f'{new_temp:.1f}', terminal=terminal_number)}\n"
                                f"[yellow]{desc}[/yellow]\n"
                                f"\n[dim]{t('temp_next_interaction')}[/dim]"
                            )
                        else:
                            change_message = (
                                f"[yellow]{t('temp_warn_runner_not_found', terminal=terminal_number)}[/yellow]\n"
                                f"Temperature value: {new_temp:.1f}"
                            )
                    else:
                        # Fallback if terminal number cannot be determined
                        change_message = (
                            f"[yellow]{t('temp_warn_no_terminal')}[/yellow]\n"
                            f"{t('temp_setting_global', value=f'{new_temp:.1f}')}\n"
                            f"[yellow]{desc}[/yellow]"
                        )
                        # Set global temperature as fallback
                        os.environ["CAI_TEMPERATURE"] = str(new_temp)

                else:
                    # Session manager not available, set global
                    os.environ["CAI_TEMPERATURE"] = str(new_temp)
                    change_message = (
                        f"{t('temp_changed', value=f'{new_temp:.1f}')}\n"
                        f"[yellow]{desc}[/yellow]\n"
                        f"\n[dim]{t('temp_next_interaction')}[/dim]"
                    )

            except Exception as e:
                # Error occurred, set global temperature as fallback
                os.environ["CAI_TEMPERATURE"] = str(new_temp)
                change_message = (
                    f"{t('temp_changed', value=f'{new_temp:.1f}')}\n"
                    f"[yellow]{desc}[/yellow]\n"
                    f"\n[dim]{t('temp_next_interaction')}[/dim]"
                )
        else:
            # Not in TUI mode, set global temperature
            os.environ["CAI_TEMPERATURE"] = str(new_temp)
            change_message = (
                f"{t('temp_changed', value=f'{new_temp:.1f}')}\n"
                f"[yellow]{desc}[/yellow]\n"
                f"\n[dim]{t('temp_next_interaction')}[/dim]"
            )

        # Display temperature change notification
        console.print(
            Panel(change_message, border_style="green", title=t('temp_changed_title'))
        )

        return True


class TopPCommand(Command):
    """Command for viewing and changing the agent's top_p (nucleus sampling)."""

    def __init__(self):
        """Initialize the top_p command."""
        super().__init__(
            name="/topp",
            description=t('temp_topp_description'),
            aliases=["/top_p"],
        )

    def handle(self, args: Optional[List[str]] = None) -> bool:
        """Handle the top_p command.

        Args:
            args: Optional list of command arguments

        Returns:
            True if the command was handled successfully, False otherwise
        """
        # Get current top_p
        current_top_p = float(os.getenv("CAI_TOP_P", str(DEFAULT_TOP_P)))
        terminal_info = ""

        # In TUI mode, try to get the specific terminal's top_p
        if os.getenv("CAI_TUI_MODE") == "true":
            try:
                from cai.tui.cai_terminal import CAITerminal
                from cai.tui.core.terminal_tracking import get_current_terminal_id

                app = CAITerminal._instance
                if app and hasattr(app, 'session_manager'):
                    terminal_number = None

                    import inspect
                    for frame_info in inspect.stack():
                        frame_locals = frame_info.frame.f_locals
                        if 'self' in frame_locals:
                            obj = frame_locals['self']
                            if hasattr(obj, 'terminal_number') and hasattr(obj, 'handle_command'):
                                terminal_number = obj.terminal_number
                                break

                    if terminal_number is None:
                        terminal_id = get_current_terminal_id()
                        if terminal_id:
                            import re
                            match = re.search(r'terminal-(\d+)', terminal_id)
                            if match:
                                terminal_number = int(match.group(1))

                    if terminal_number is None and hasattr(app, 'terminal_grid'):
                        focused_terminal = app.terminal_grid.get_focused_terminal()
                        if focused_terminal and hasattr(focused_terminal, 'state'):
                            terminal_number = focused_terminal.state.terminal_number

                    if terminal_number is not None:
                        runner = app.session_manager.terminal_runners.get(terminal_number)
                        if runner and runner.agent and hasattr(runner.agent, 'model_settings'):
                            if runner.agent.model_settings.top_p is not None:
                                current_top_p = runner.agent.model_settings.top_p
                            terminal_info = f" (Terminal {terminal_number})"
            except Exception:
                pass

        if not args:
            # Display current top_p
            console.print(
                Panel(
                    f"{t('temp_topp_current', terminal_info=terminal_info, current_top_p=f'{current_top_p:.2f}')}\n"
                    f"\n[cyan]{t('temp_topp_info_header')}[/cyan]\n"
                    f"  • [bold]{t('temp_topp_info_05')}[/bold]\n"
                    f"  • [bold]{t('temp_topp_info_09')}[/bold]\n"
                    f"  • [bold]{t('temp_topp_info_1')}[/bold]",
                    border_style="green",
                    title=t('temp_topp_panel_title'),
                )
            )
            console.print(f"\n[cyan]{t('temp_usage')}[/cyan]")
            console.print(f"  [bold]{t('temp_topp_usage_set')}[/bold]")
            console.print(f"  [bold]{t('temp_topp_usage_alias')}[/bold]")
            return True

        # Parse top_p value
        try:
            new_top_p = float(args[0])

            # Validate top_p range
            if not 0.0 <= new_top_p <= 1.0:
                console.print(
                    Panel(
                        f"[red]{t('temp_topp_invalid_value', value=new_top_p)}[/red]\n"
                        f"{t('temp_topp_invalid_range')}",
                        border_style="red",
                        title=t('temp_error_title'),
                    )
                )
                return True

        except ValueError:
            console.print(
                Panel(
                    f"[red]{t('temp_topp_invalid_parse', value=args[0])}[/red]\n"
                    f"{t('temp_topp_invalid_parse_hint')}",
                    border_style="red",
                    title=t('temp_error_title'),
                )
            )
            return True

        # Determine top_p description
        if new_top_p <= 0.5:
            desc = t('temp_topp_desc_focused')
        elif new_top_p <= 0.7:
            desc = t('temp_topp_desc_balanced')
        elif new_top_p <= 0.9:
            desc = t('temp_topp_desc_broad')
        else:
            desc = t('temp_topp_desc_all')

        # Set global top_p
        os.environ["CAI_TOP_P"] = str(new_top_p)
        change_message = (
            f"{t('temp_topp_changed', value=f'{new_top_p:.2f}')}\n"
            f"[yellow]{desc}[/yellow]\n"
            f"\n[dim]{t('temp_next_interaction')}[/dim]"
        )

        # Display top_p change notification
        console.print(
            Panel(change_message, border_style="green", title=t('temp_topp_changed_title'))
        )

        return True


# Register the commands
register_command(TemperatureCommand())
register_command(TopPCommand())
