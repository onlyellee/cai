"""
Meta Agent debug command for TUI
"""

import os
from typing import Optional, List
from rich.table import Table
from rich.console import Console
from rich.panel import Panel
from rich.json import JSON

from cai.repl.commands.base import Command, register_command
from cai.i18n import t

console = Console()


class MetaDebugCommand(Command):
    """Show Meta Agent debug information"""

    def __init__(self):
        """Initialize the meta debug command."""
        super().__init__(
            name="/metadebug",
            description=t('debug_description'),
            aliases=["/md"],
        )

    def handle(self, args: Optional[List[str]] = None) -> bool:
        """Handle the meta debug command"""

        # Check if Meta Agent is enabled
        if os.getenv("CAI_META_AGENT", "false").lower() != "true":
            console.print(f"[yellow]{t('debug_not_enabled')}[/yellow]")
            return True

        # Lazy import to avoid circular dependency
        try:
            from cai.tui.meta_agent_controller import get_meta_agent_controller
        except ImportError as e:
            console.print(f"[red]{t('debug_import_error', error=e)}[/red]")
            return True

        # Get controller
        controller = get_meta_agent_controller()
        if not controller:
            console.print(f"[red]{t('debug_not_initialized')}[/red]")
            return True

        # Get debug info
        debug_info = controller.get_debug_info()

        # Create debug panel
        table = Table(title=t('debug_table_title'), show_header=True)
        table.add_column(t('debug_col_property'), style="cyan")
        table.add_column(t('debug_col_value'), style="white")

        # Basic info
        table.add_row(t('debug_enabled'), str(debug_info.get("enabled", False)))
        table.add_row(t('debug_model'), debug_info.get("model", "Unknown"))
        table.add_row(t('debug_workers_started'), str(debug_info.get("workers_started", False)))
        table.add_row(t('debug_processing'), str(debug_info.get("processing", False)))
        table.add_row(t('debug_queue_size'), str(debug_info.get("command_queue_size", 0)))

        console.print(table)

        # LiteLLM debug info
        litellm_debug = debug_info.get("last_litellm_debug", {})
        if litellm_debug:
            console.print(f"\n[bold]{t('debug_last_litellm')}[/bold]")

            litellm_table = Table(show_header=False)
            litellm_table.add_column(t('debug_col_property'), style="dim cyan")
            litellm_table.add_column(t('debug_col_value'), style="white")

            for key, value in litellm_debug.items():
                litellm_table.add_row(key.replace("_", " ").title(), str(value))

            console.print(litellm_table)

        # Show environment
        console.print(f"\n[bold]{t('debug_environment')}[/bold]")
        env_table = Table(show_header=False)
        env_table.add_column(t('debug_col_property'), style="dim cyan")
        env_table.add_column(t('debug_col_value'), style="white")

        env_vars = ["CAI_META_AGENT", "CAI_META_MODEL", "CAI_MODEL", "OPENAI_API_KEY", "ANTHROPIC_API_KEY"]
        for var in env_vars:
            value = os.getenv(var)
            if var.endswith("_KEY") and value:
                # Mask API keys
                value = value[:8] + "..." + value[-4:] if len(value) > 12 else "***"
            env_table.add_row(var, value or t('debug_not_set'))

        console.print(env_table)

        # Quick tips
        console.print(f"\n[dim]{t('debug_tips_title')}[/dim]")
        console.print(f"[dim]- {t('debug_tip_intercepts')}[/dim]")
        console.print(f"[dim]- {t('debug_tip_messages')}[/dim]")
        console.print(f"[dim]- {t('debug_tip_api_keys')}[/dim]")

        return True


# Register command
register_command(MetaDebugCommand())
