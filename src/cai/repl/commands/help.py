"""
Help command for CAI REPL.
This module provides commands for displaying help information.
"""

from typing import List, Optional

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
except ImportError as exc:
    raise ImportError(
        "The 'rich' package is required. Please install it with: pip install rich"
    ) from exc

from cai.repl.commands.base import COMMAND_ALIASES, COMMANDS, Command, register_command

try:
    from caiextensions.platform.base.platform_manager import PlatformManager

    HAS_PLATFORM_EXTENSIONS = True
except ImportError:
    HAS_PLATFORM_EXTENSIONS = False

from cai import is_caiextensions_platform_available
from cai.i18n import t

console = Console()


def create_styled_table(
    title: str, headers: List[tuple[str, str]], header_style: str = "bold white"
) -> Table:
    """Create a styled table with consistent formatting.

    Args:
        title: The table title
        headers: List of (header_name, style) tuples
        header_style: Style for the header row

    Returns:
        A configured Table instance
    """
    table = Table(title=title, show_header=True, header_style=header_style)
    for header, style in headers:
        table.add_column(header, style=style)
    return table


def create_notes_panel(
    notes: List[str], title: Optional[str] = None, border_style: str = "yellow"
) -> Panel:
    """Create a notes panel with consistent formatting.

    Args:
        notes: List of note strings
        title: Panel title
        border_style: Style for the panel border

    Returns:
        A configured Panel instance
    """
    if title is None:
        title = t('help_notes')
    notes_text = Text.from_markup("\n".join(f"• {note}" for note in notes))
    return Panel(notes_text, title=title, border_style=border_style)


class HelpCommand(Command):
    """Command for displaying help information."""

    def __init__(self):
        """Initialize the help command."""
        super().__init__(
            name="/help",
            description=(t('help_description_cmd')),
            aliases=["/h", "/?"],
        )

        # Add subcommands organized by category
        # Agent Management
        self.add_subcommand("agent", "Display help for agent commands", self.handle_agent)
        self.add_subcommand("parallel", "Display help for parallel execution", self.handle_parallel)
        self.add_subcommand("run", "Display help for queued execution", self.handle_run)

        # Memory & History
        self.add_subcommand("memory", "Display help for memory persistence", self.handle_memory)
        self.add_subcommand("history", "Display help for conversation history", self.handle_history)
        self.add_subcommand(
            "compact", "Display help for conversation compaction", self.handle_compact
        )
        self.add_subcommand("flush", "Display help for clearing histories", self.handle_flush)
        self.add_subcommand("load", "Display help for loading JSONL files", self.handle_load)
        self.add_subcommand(
            "merge", "Display help for merging agent histories", self.handle_merge_help
        )

        # Environment & Config
        self.add_subcommand("config", "Display help for configuration", self.handle_config)
        self.add_subcommand("env", "Display help for environment variables", self.handle_env)
        self.add_subcommand(
            "workspace", "Display help for workspace management", self.handle_workspace
        )
        self.add_subcommand(
            "virtualization", "Display help for Docker containers", self.handle_virtualization
        )

        # Tools & Integration
        self.add_subcommand("mcp", "Display help for Model Context Protocol", self.handle_mcp)
        self.add_subcommand("platform", "Display help for platform commands", self.handle_platform)
        self.add_subcommand("shell", "Display help for shell commands", self.handle_shell)

        # Utilities
        self.add_subcommand("model", "Display help for model selection", self.handle_model)
        self.add_subcommand("graph", "Display help for visualization", self.handle_graph)
        self.add_subcommand("aliases", "Display all command aliases", self.handle_aliases)
        self.add_subcommand("kill", "Display help for process management", self.handle_kill)

        # General
        self.add_subcommand("commands", "List all available commands", self.handle_commands)
        self.add_subcommand("quick", "Quick reference guide", self.handle_quick)
        self.add_subcommand(
            "quickstart", "Show quickstart guide for new users", self.handle_quickstart
        )

    def handle_memory(self, _: Optional[List[str]] = None) -> bool:
        """Show help for memory commands."""
        # Get the memory command and show its help
        memory_cmd = next((cmd for cmd in COMMANDS.values() if cmd.name == "/memory"), None)
        if memory_cmd and hasattr(memory_cmd, "show_help"):
            memory_cmd.show_help()
            return True

        # Fallback if memory command not found or doesn't have show_help
        self.handle_help_memory()
        return True

    def handle_agent(self, _: Optional[List[str]] = None) -> bool:
        """Show help for agent management."""
        console.print(
            Panel(
                f"[bold]{t('help_agent_header')}[/bold]\n\n"
                f"{t('help_agent_desc')}\n\n"
                f"[bold yellow]{t('help_agent_avail_cmds')}[/bold yellow]\n"
                f"• [yellow]/agent list[/yellow] - {t('help_agent_list')}\n"
                f"• [yellow]/agent select <name>[/yellow] - {t('help_agent_select')}\n"
                f"• [yellow]/agent info <name>[/yellow] - {t('help_agent_info')}\n"
                f"• [yellow]/agent multi[/yellow] - {t('help_agent_multi')}\n"
                f"• [yellow]/agent current[/yellow] - {t('help_agent_current')}\n\n"
                f"[bold cyan]{t('help_examples')}:[/bold cyan]\n"
                f"• [green]/agent list[/green] - {t('help_agent_ex_list')}\n"
                f"• [green]/agent select red_teamer[/green] - {t('help_agent_ex_select')}\n"
                f"• [green]/agent info bug_bounter[/green] - {t('help_agent_ex_info')}\n"
                f"• [green]/a select 2[/green] - {t('help_agent_ex_num')}\n\n"
                f"[bold]{t('help_agent_avail_agents')}[/bold]\n"
                f"• [cyan]one_tool_agent[/cyan] - {t('help_agent_one_tool')}\n"
                f"• [cyan]red_teamer[/cyan] - {t('help_agent_red')}\n"
                f"• [cyan]blue_teamer[/cyan] - {t('help_agent_blue')}\n"
                f"• [cyan]bug_bounter[/cyan] - {t('help_agent_bug')}\n"
                f"• [cyan]dfir[/cyan] - {t('help_agent_dfir')}\n"
                f"• [cyan]network_traffic_analyzer[/cyan] - {t('help_agent_network')}\n"
                f"• [cyan]flag_discriminator[/cyan] - {t('help_agent_flag')}\n"
                f"• [cyan]codeagent[/cyan] - {t('help_agent_code')}\n"
                f"• [cyan]thought[/cyan] - {t('help_agent_thought')}\n\n"
                "[dim]Alias: /a[/dim]",
                title=t('help_agent_title'),
                border_style="blue",
            )
        )
        return True

    def handle_graph(self, _: Optional[List[str]] = None) -> bool:
        """Show help for graph visualization."""
        console.print(
            Panel(
                f"[bold]{t('help_graph_header')}[/bold]\n\n"
                f"{t('help_graph_desc')}\n\n"
                f"[bold yellow]{t('help_agent_avail_cmds')}[/bold yellow]\n"
                f"• [yellow]/graph[/yellow] - {t('help_graph_show')}\n"
                f"• [yellow]/graph P1[/yellow] - {t('help_graph_by_id')}\n"
                f"• [yellow]/graph <agent_name>[/yellow] - {t('help_graph_by_name')}\n"
                f"• [yellow]/graph all[/yellow] - {t('help_graph_all')}\n"
                f"• [yellow]/graph timeline[/yellow] - {t('help_graph_timeline')}\n"
                f"• [yellow]/graph stats[/yellow] - {t('help_graph_stats')}\n"
                f"• [yellow]/graph export <format>[/yellow] - {t('help_graph_export')}\n\n"
                f"[bold cyan]{t('help_graph_features')}[/bold cyan]\n"
                f"• {t('help_graph_feat_multi')}\n"
                f"• {t('help_graph_feat_user')}\n"
                f"• {t('help_graph_feat_tool')}\n"
                f"• {t('help_graph_feat_timeline')}\n"
                f"• {t('help_graph_feat_stats')}\n"
                f"• {t('help_graph_feat_export')}\n\n"
                f"[bold green]{t('help_examples')}:[/bold green]\n"
                f"• [green]/graph[/green] - {t('help_graph_ex_display')}\n"
                f"• [green]/graph P2[/green] - {t('help_graph_ex_p2')}\n"
                f"• [green]/graph red_teamer[/green] - {t('help_graph_ex_red')}\n"
                f"• [green]/graph timeline[/green] - {t('help_graph_ex_timeline')}\n"
                f"• [green]/graph stats[/green] - {t('help_graph_ex_stats')}\n"
                f"• [green]/graph export mermaid graph.md[/green] - {t('help_graph_ex_mermaid')}\n"
                f"• [green]/g timeline[/green] - {t('help_graph_ex_alias')}\n\n"
                f"[bold]{t('help_graph_export_formats')}[/bold]\n"
                f"• [cyan]json[/cyan] - {t('help_graph_fmt_json')}\n"
                f"• [cyan]dot[/cyan] - {t('help_graph_fmt_dot')}\n"
                f"• [cyan]mermaid[/cyan] - {t('help_graph_fmt_mermaid')}\n\n"
                "[dim]Alias: /g[/dim]",
                title=t('help_graph_title'),
                border_style="blue",
            )
        )
        return True

    def handle_platform(self, _: Optional[List[str]] = None) -> bool:
        """Show help for platform-specific features."""
        platform_cmd = next((cmd for cmd in COMMANDS.values() if cmd.name == "/platform"), None)

        if platform_cmd and hasattr(platform_cmd, "show_help"):
            platform_cmd.show_help()
            return True

        console.print(
            Panel(
                f"{t('help_platform_cmds_desc')}\n\n"
                f"[bold]{t('help_agent_avail_cmds')}[/bold]\n"
                f"• [yellow]/platform list[/yellow] - {t('help_platform_list')}\n"
                f"• [yellow]/platform <platform> <command>[/yellow] - "
                f"{t('help_platform_run')}\n\n"
                f"[bold]{t('help_examples')}:[/bold]\n"
                f"• [green]/platform list[/green] - {t('help_platform_ex_list')}\n"
                f"• [green]/p list[/green] - {t('help_platform_ex_short')}",
                title=t('help_platform_cmds_title'),
                border_style="blue",
            )
        )
        return True

    def handle_shell(self, _: Optional[List[str]] = None) -> bool:
        """Show help for shell command execution."""
        console.print(
            Panel(
                f"{t('help_shell_desc')}\n\n"
                f"[bold]{t('help_agent_avail_cmds')}[/bold]\n"
                f"• [yellow]/shell <command>[/yellow] - {t('help_shell_exec')}\n"
                f"• [yellow]/![/yellow] - {t('help_shell_shorthand')}\n\n"
                f"[bold]{t('help_shell_session')}[/bold]\n"
                f"• [yellow]/shell session list[/yellow] - {t('help_shell_session_list')}\n"
                f"• [yellow]/shell session output <id>[/yellow] - "
                f"{t('help_shell_session_output')}\n"
                f"• [yellow]/shell session kill <id>[/yellow] - "
                f"{t('help_shell_session_kill')}\n\n"
                f"[bold]{t('help_examples')}:[/bold]\n"
                f"• [green]/shell ls -la[/green] - "
                f"{t('help_shell_ex_ls')}\n"
                f"• [green]/! pwd[/green] - {t('help_shell_ex_pwd')}",
                title=t('help_shell_title'),
                border_style="blue",
            )
        )
        return True

    def handle_env(self, _: Optional[List[str]] = None) -> bool:
        """Show help for environment variables."""
        console.print(
            Panel(
                f"{t('help_env_desc')}\n\n"
                f"[bold]{t('help_env_key_vars')}[/bold]\n"
                f"• [yellow]CAI_MODEL[/yellow] - "
                f"{t('help_env_model')}\n"
                f"• [yellow]CAI_<AGENT>_MODEL[/yellow] - "
                f"{t('help_env_agent_model')}\n"
                f"• [yellow]CAI_MEMORY_DIR[/yellow] - "
                f"{t('help_env_memory_dir')}\n\n"
                f"[bold]{t('help_env_api_keys')}[/bold]\n"
                f"{t('help_env_api_desc')}\n"
                f"• [yellow]PROVIDER_API_KEY[/yellow] - {t('help_env_api_pattern')}\n\n"
                f"{t('help_examples')}:\n"
                "• [yellow]export OPENAI_API_KEY='your-key'[/yellow]\n"
                "• [yellow]export ANTHROPIC_API_KEY='your-key'[/yellow]\n"
                "• [yellow]export YOUR_PROVIDER_API_KEY='your-key'[/yellow]\n\n"
                f"[bold]{t('help_agent_avail_cmds')}[/bold]\n"
                f"• [yellow]/env list[/yellow] - {t('help_env_list')}\n"
                f"• [yellow]/env set <n> <value>[/yellow] - "
                f"{t('help_env_set')}\n"
                f"• [yellow]/env get <n>[/yellow] - "
                f"{t('help_env_get')}",
                title=t('help_env_title'),
                border_style="blue",
            )
        )
        return True

    def handle_aliases(self, _: Optional[List[str]] = None) -> bool:
        """Show all command aliases."""
        return self.handle_help_aliases()

    def handle_model(self, _: Optional[List[str]] = None) -> bool:
        """Show help for model selection."""
        return self.handle_help_model()

    def handle_turns(self, _: Optional[List[str]] = None) -> bool:
        """Show help for managing turns."""
        return self.handle_help_turns()

    def handle_config(self, _: Optional[List[str]] = None) -> bool:
        """Display help for config commands.

        Args:
            _: Ignored arguments

        Returns:
            True if successful
        """
        return self.handle_help_config()

    def handle_no_args(self) -> bool:
        """Handle the command when no arguments are provided."""
        return self.handle_help()

    def _print_command_table(
        self,
        title: str,
        commands: List[tuple[str, str, str]],
        header_style: str = "bold yellow",
        command_style: str = "yellow",
    ) -> None:
        """Print a table of commands with consistent formatting."""
        table = create_styled_table(
            title,
            [(t('help_col_command'), command_style), (t('help_col_alias'), "green"), (t('help_col_description'), "white")],
            header_style,
        )

        for cmd, alias, desc in commands:
            table.add_row(cmd, alias, desc)

        console.print(table)

    def handle_help(self) -> bool:
        """Display general help information.

        Returns:
            True if successful
        """
        console.print(
            Panel(
                Text.from_markup(
                    f"[bold]{t('help_welcome')}[/bold]\n\n"
                    f"{t('help_welcome_desc')}\n\n"
                    f"{t('help_wip_notice')}\n"
                    f"[yellow]{t('help_topic_hint')}[/yellow] [bold]/help <topic>[/bold]\n"
                    f"[yellow]{t('help_quick_hint')}[/yellow] [bold]/help quick[/bold]\n"
                    f"[yellow]{t('help_commands_hint')}[/yellow] [bold]/help commands[/bold]"
                ),
                title=f"🔒 {t('help_system_title')}",
                border_style="yellow",
            )
        )

        # Command Categories
        categories = [
            (
                f"[bold yellow]{t('help_cat_agent')}[/bold yellow]",
                [
                    ("[cyan]/agent[/cyan]", t('help_desc_agent')),
                    ("[cyan]/parallel[/cyan]", t('help_desc_parallel')),
                    ("[cyan]/run[/cyan]", t('help_desc_run')),
                ],
            ),
            (
                f"[bold green]{t('help_cat_memory')}[/bold green]",
                [
                    ("[cyan]/memory[/cyan]", t('help_desc_memory')),
                    ("[cyan]/history[/cyan]", t('help_desc_history')),
                    ("[cyan]/compact[/cyan]", t('help_desc_compact')),
                    ("[cyan]/flush[/cyan]", t('help_desc_flush')),
                    ("[cyan]/load[/cyan]", t('help_desc_load')),
                    ("[cyan]/merge[/cyan]", t('help_desc_merge')),
                ],
            ),
            (
                f"[bold blue]{t('help_cat_env')}[/bold blue]",
                [
                    ("[cyan]/config[/cyan]", t('help_desc_config')),
                    ("[cyan]/env[/cyan]", t('help_desc_env')),
                    ("[cyan]/workspace[/cyan]", t('help_desc_workspace')),
                    ("[cyan]/virtualization[/cyan]", t('help_desc_virtualization')),
                ],
            ),
            (
                f"[bold magenta]{t('help_cat_tools')}[/bold magenta]",
                [
                    ("[cyan]/mcp[/cyan]", t('help_desc_mcp')),
                    ("[cyan]/platform[/cyan]", t('help_desc_platform')),
                    ("[cyan]/shell[/cyan]", t('help_desc_shell')),
                ],
            ),
            (
                f"[bold red]{t('help_cat_utils')}[/bold red]",
                [
                    ("[cyan]/model[/cyan]", t('help_desc_model')),
                    ("[cyan]/graph[/cyan]", t('help_desc_graph')),
                    ("[cyan]/kill[/cyan]", t('help_desc_kill')),
                    ("[cyan]/exit[/cyan]", t('help_desc_exit')),
                ],
            ),
        ]

        for category_name, commands in categories:
            console.print(f"\n{category_name}")
            table = Table(show_header=False, box=None, padding=(0, 2))
            table.add_column(style="cyan", width=25)
            table.add_column(style="white")
            for cmd, desc in commands:
                table.add_row(f"  {cmd}", desc)
            console.print(table)

        # Quick Tips
        tips = Panel(
            Text.from_markup(
                f"[bold]{t('help_quick_tips')}[/bold]\n"
                f"• {t('help_tip_tab')}\n"
                f"• {t('help_tip_arrows')}\n"
                f"• {t('help_tip_ctrlc')}\n"
                f"• {t('help_tip_ctrll')}\n"
                f"• {t('help_tip_aliases')}\n"
                f"• {t('help_tip_detail')}"
            ),
            title=f"💡 {t('help_tips')}",
            border_style="cyan",
        )
        console.print("\n")
        console.print(tips)

        return True

    def handle_help_aliases(self) -> bool:
        """Show all command aliases in a well-formatted table."""
        # Create a styled header
        console.print(Panel(t('help_aliases_ref'), border_style="magenta", title=t('help_aliases')))

        # Create a table for aliases
        alias_table = create_styled_table(
            t('help_aliases_title'),
            [(t('help_col_alias'), "green"), (t('help_col_command'), "yellow"), (t('help_col_description'), "white")],
            "bold magenta",
        )

        # Add rows for each alias
        for alias, command in sorted(COMMAND_ALIASES.items()):
            cmd = COMMANDS.get(command)
            description = cmd.description if cmd else ""
            alias_table.add_row(alias, command, description)

        console.print(alias_table)

        # Add tips
        tips = [
            t('help_aliases_tip_use'),
            t('help_aliases_tip_example'),
        ]
        console.print("\n")
        console.print(create_notes_panel(tips, t('help_tips'), "cyan"))

        return True

    def handle_help_memory(self) -> bool:
        """Show help for memory commands with rich formatting."""
        # Create a styled header
        header = Text(t('help_memory_title'), style="bold yellow")
        console.print(Panel(header, border_style="yellow"))

        # Usage table
        usage_table = create_styled_table(
            t('help_usage'), [(t('help_col_command'), "yellow"), (t('help_col_description'), "white")]
        )

        usage_table.add_row("/memory list", t('help_memory_list'))
        usage_table.add_row("/memory load <collection>", t('help_memory_load'))
        usage_table.add_row("/memory delete <collection>", t('help_memory_delete'))
        usage_table.add_row("/memory create <collection>", t('help_memory_create'))
        usage_table.add_row("/m", t('help_memory_alias'))

        console.print(usage_table)

        # Examples table
        examples_table = create_styled_table(
            t('help_examples'), [(t('help_col_example'), "cyan"), (t('help_col_description'), "white")], "bold cyan"
        )

        examples = [
            ("/memory list", t('help_memory_ex_list')),
            ("/memory load _all_", t('help_memory_ex_load_all')),
            ("/memory load my_ctf", t('help_memory_ex_load_ctf')),
            ("/memory create new_collection", t('help_memory_ex_create')),
            ("/memory delete old_collection", t('help_memory_ex_delete')),
        ]

        for example, desc in examples:
            examples_table.add_row(example, desc)

        console.print(examples_table)

        # Collection types table
        types_table = create_styled_table(
            t('help_memory_coll_types'), [(t('help_col_type'), "green"), (t('help_col_description'), "white")], "bold green"
        )

        types = [
            ("_all_", t('help_memory_type_all')),
            ("<CTF_NAME>", t('help_memory_type_ctf')),
            ("<custom_name>", t('help_memory_type_custom')),
        ]

        for type_name, desc in types:
            types_table.add_row(type_name, desc)

        console.print(types_table)

        # Notes panel
        notes = [
            t('help_memory_note_qdrant'),
            t('help_memory_note_env'),
            t('help_memory_note_episodic'),
            t('help_memory_note_semantic'),
            t('help_memory_note_context'),
        ]

        console.print(create_notes_panel(notes, t('help_notes')))

        return True

    def handle_help_model(self) -> bool:
        """Show help for model command with rich formatting."""
        # Create a styled header
        header = Text(t('help_model_title'), style="bold magenta")
        console.print(Panel(header, border_style="magenta"))

        # Usage table
        usage_table = create_styled_table(
            t('help_usage'), [(t('help_col_command'), "magenta"), (t('help_col_description'), "white")]
        )

        usage_commands = [
            ("/model", t('help_model_display')),
            ("/model <model_name>", t('help_model_change_name')),
            ("/model <number>", t('help_model_change_num')),
            ("/mod", t('help_model_alias')),
        ]

        for cmd, desc in usage_commands:
            usage_table.add_row(cmd, desc)

        console.print(usage_table)

        # Examples table
        examples_table = create_styled_table(
            t('help_examples'), [(t('help_col_example'), "cyan"), (t('help_col_description'), "white")], "bold cyan"
        )

        examples = [
            ("/model 1", t('help_model_ex_1')),
            ("/model claude-3-7-sonnet-20250219", t('help_model_ex_claude')),
            ("/model o1", t('help_model_ex_o1')),
            ("/model gpt-4o", t('help_model_ex_gpt4')),
        ]

        for example, desc in examples:
            examples_table.add_row(example, desc)

        console.print(examples_table)

        # Model information
        console.print(f"\n[bold green]{t('help_model_info')}[/bold green]\n")
        console.print(t('help_model_supports'))
        console.print(t('help_model_see_avail'))
        console.print(f"\n{t('help_model_categories')}")
        console.print(f"• {t('help_model_cat_fast')}")
        console.print(f"• {t('help_model_cat_reason')}")
        console.print(f"• {t('help_model_cat_code')}")
        console.print(f"• {t('help_model_cat_local')}")
        console.print(f"• {t('help_model_cat_multi')}")

        # Notes panel
        notes = [
            t('help_model_note_effect'),
            t('help_model_note_env'),
            t('help_model_note_api'),
            t('help_model_note_config'),
            t('help_model_note_quickstart'),
            t('help_model_note_local'),
        ]

        console.print(create_notes_panel(notes, t('help_notes')))

        return True

    def handle_help_turns(self) -> bool:
        """Show help for turns command with rich formatting."""
        # Create a styled header
        header = Text(t('help_turns_title'), style="bold magenta")
        console.print(Panel(header, border_style="magenta"))

        # Usage table
        usage_table = create_styled_table(
            t('help_usage'), [(t('help_col_command'), "magenta"), (t('help_col_description'), "white")]
        )

        usage_commands = [
            ("/turns", t('help_turns_display')),
            ("/turns <number>", t('help_turns_change')),
            ("/turns inf", t('help_turns_inf')),
            ("/t", t('help_turns_alias')),
        ]

        for cmd, desc in usage_commands:
            usage_table.add_row(cmd, desc)

        console.print(usage_table)

        # Examples table
        examples_table = create_styled_table(
            t('help_examples'), [(t('help_col_example'), "cyan"), (t('help_col_description'), "white")], "bold cyan"
        )

        examples = [
            ("/turns", t('help_turns_ex_show')),
            ("/turns 10", t('help_turns_ex_10')),
            ("/turns inf", t('help_turns_ex_inf')),
            ("/t 5", t('help_turns_ex_alias')),
        ]

        for example, desc in examples:
            examples_table.add_row(example, desc)

        console.print(examples_table)

        # Notes panel
        notes = [
            t('help_turns_note_limit'),
            t('help_turns_note_inf'),
            t('help_turns_note_env'),
            t('help_turns_note_count'),
        ]

        console.print(create_notes_panel(notes, t('help_notes')))

        return True

    def handle_help_platform_manager(self) -> bool:
        """Show help for platform manager commands."""
        if HAS_PLATFORM_EXTENSIONS and is_caiextensions_platform_available():
            try:
                from caiextensions.platform.base import platform_manager

                platforms = platform_manager.list_platforms()

                if not platforms:
                    console.print(f"[yellow]{t('help_platform_no_reg')}[/yellow]")
                    return True

                platform_table = create_styled_table(
                    t('help_platform_title'),
                    [(t('help_col_platform'), "magenta"), (t('help_col_description'), "white")],
                    "bold magenta",
                )

                for platform_name in platforms:
                    platform = platform_manager.get_platform(platform_name)
                    description = getattr(platform, "description", platform_name.capitalize())
                    platform_table.add_row(platform_name, description)

                console.print(platform_table)

                # Add platform command examples
                examples = []
                for platform_name in platforms:
                    platform = platform_manager.get_platform(platform_name)
                    commands = platform.get_commands()
                    if commands:
                        command_example = f"[green]/platform {platform_name} {commands[0]}[/green] - {t('help_platform_ex_cmd').format(platform_name=platform_name)}"
                        examples.append(command_example)

                if examples:
                    console.print(
                        Panel(
                            "\n".join(examples),
                            title=t('help_platform_examples'),
                            border_style="blue",
                        )
                    )

                return True
            except (ImportError, Exception) as e:
                console.print(f"[yellow]{t('help_platform_error').format(error=e)}[/yellow]")
                return True

        console.print(f"[yellow]{t('help_platform_no_ext')}[/yellow]")
        return True

    def handle_help_config(self) -> bool:
        """Display help for config commands.

        Returns:
            True if successful
        """
        console.print(
            Panel(
                Text.from_markup(t('help_config_desc')),
                title=t('help_config_title'),
                border_style="yellow",
            )
        )

        # Create table for subcommands
        table = create_styled_table(
            t('help_config_subcmds'), [(t('help_col_command'), "yellow"), (t('help_col_description'), "white")]
        )

        table.add_row("/config", t('help_config_list_desc'))
        table.add_row("/config list", t('help_config_list_desc'))
        table.add_row(
            "/config get <number>", t('help_config_get_desc')
        )
        table.add_row(
            "/config set <number> <value>",
            t('help_config_set_desc'),
        )

        console.print(table)

        # Create notes panel
        notes = [
            t('help_config_note_control'),
            t('help_config_note_session'),
            t('help_config_note_list'),
            t('help_config_note_num'),
        ]
        console.print(create_notes_panel(notes, t('help_notes')))

        return True

    def handle_parallel(self, _: Optional[List[str]] = None) -> bool:
        """Show help for parallel execution."""
        console.print(
            Panel(
                f"[bold]{t('help_parallel_header')}[/bold]\n\n"
                f"{t('help_parallel_desc')}\n\n"
                f"[bold yellow]{t('help_agent_avail_cmds')}[/bold yellow]\n"
                f"• [yellow]/parallel[/yellow] - {t('help_parallel_show')}\n"
                f"• [yellow]/parallel add <agent>[/yellow] - {t('help_parallel_add')}\n"
                f"• [yellow]/parallel list[/yellow] - {t('help_parallel_list')}\n"
                f"• [yellow]/parallel clear[/yellow] - {t('help_parallel_clear')}\n"
                f"• [yellow]/parallel remove <index>[/yellow] - {t('help_parallel_remove')}\n"
                f"• [yellow]/parallel override-models[/yellow] - {t('help_parallel_override')}\n"
                f"• [yellow]/parallel merge <indices>[/yellow] - {t('help_parallel_merge')}\n"
                f"• [yellow]/parallel prompt <index> <text>[/yellow] - {t('help_parallel_prompt')}\n\n"
                f"[bold cyan]{t('help_examples')}:[/bold cyan]\n"
                f"• [green]/parallel add red_teamer[/green] - {t('help_parallel_ex_add')}\n"
                '• [green]/parallel add bug_bounter custom_prompt="Find SQLi"[/green]\n'
                f"• [green]/parallel merge 1,2[/green] - {t('help_parallel_ex_merge')}\n"
                f"• [green]/p list[/green] - {t('help_parallel_ex_list')}\n\n"
                f"[bold]{t('help_notes')}:[/bold]\n"
                f"• {t('help_parallel_note_isolated')}\n"
                f"• {t('help_parallel_note_id')}\n"
                f"• {t('help_parallel_note_display')}\n"
                f"• {t('help_parallel_note_env')}\n\n"
                "[dim]Aliases: /par, /p[/dim]",
                title=t('help_parallel_title'),
                border_style="blue",
            )
        )
        return True

    def handle_run(self, _: Optional[List[str]] = None) -> bool:
        """Show help for queued execution."""
        console.print(
            Panel(
                f"[bold]{t('help_run_header')}[/bold]\n\n"
                f"{t('help_run_desc')}\n\n"
                f"[bold yellow]{t('help_agent_avail_cmds')}[/bold yellow]\n"
                f"• [yellow]/run queue <agent_id> <prompt>[/yellow] - {t('help_run_queue')}\n"
                f"• [yellow]/run list[/yellow] - {t('help_run_list')}\n"
                f"• [yellow]/run clear[/yellow] - {t('help_run_clear')}\n"
                f"• [yellow]/run remove <index>[/yellow] - {t('help_run_remove')}\n\n"
                f"[bold cyan]{t('help_examples')}:[/bold cyan]\n"
                f'• [green]/run queue P1 "Scan port 80"[/green] - {t("help_run_ex_queue")}\n'
                '• [green]/run queue P2 "Check for SQL injection"[/green]\n'
                f"• [green]/run list[/green] - {t('help_run_ex_list')}\n"
                f"• [green]/r clear[/green] - {t('help_run_ex_clear')}\n\n"
                f"[bold]{t('help_notes')}:[/bold]\n"
                f"• {t('help_run_note_parallel')}\n"
                f"• {t('help_run_note_execute')}\n"
                f"• {t('help_run_note_independent')}\n\n"
                "[dim]Alias: /r[/dim]",
                title=t('help_run_title'),
                border_style="green",
            )
        )
        return True

    def handle_history(self, _: Optional[List[str]] = None) -> bool:
        """Show help for conversation history."""
        console.print(
            Panel(
                f"[bold]{t('help_history_header')}[/bold]\n\n"
                f"{t('help_history_desc')}\n\n"
                f"[bold yellow]{t('help_agent_avail_cmds')}[/bold yellow]\n"
                f"• [yellow]/history[/yellow] - {t('help_history_show')}\n"
                f"• [yellow]/history all[/yellow] - {t('help_history_all')}\n"
                f"• [yellow]/history <agent>[/yellow] - {t('help_history_agent')}\n"
                f"• [yellow]/history search <term>[/yellow] - {t('help_history_search')}\n"
                f"• [yellow]/history <agent> <index>[/yellow] - {t('help_history_index')}\n"
                f"• [yellow]/history export <file>[/yellow] - {t('help_history_export')}\n\n"
                f"[bold cyan]{t('help_examples')}:[/bold cyan]\n"
                f"• [green]/history[/green] - {t('help_history_ex_panel')}\n"
                f"• [green]/history P1[/green] - {t('help_history_ex_p1')}\n"
                f'• [green]/history search "password"[/green] - {t("help_history_ex_search")}\n'
                f"• [green]/his red_teamer 5[/green] - {t('help_history_ex_msg')}\n\n"
                f"[bold]{t('help_history_features')}[/bold]\n"
                f"• {t('help_history_feat_token')}\n"
                f"• {t('help_history_feat_role')}\n"
                f"• {t('help_history_feat_tool')}\n"
                f"• {t('help_history_feat_export')}\n\n"
                "[dim]Alias: /his[/dim]",
                title=t('help_history_title'),
                border_style="magenta",
            )
        )
        return True

    def handle_compact(self, _: Optional[List[str]] = None) -> bool:
        """Show help for conversation compaction."""
        console.print(
            Panel(
                f"[bold]{t('help_compact_header')}[/bold]\n\n"
                f"{t('help_compact_desc')}\n\n"
                f"[bold yellow]{t('help_agent_avail_cmds')}[/bold yellow]\n"
                f"• [yellow]/compact[/yellow] - {t('help_compact_run')}\n"
                f"• [yellow]/compact model <name>[/yellow] - {t('help_compact_model')}\n"
                f"• [yellow]/compact prompt <text>[/yellow] - {t('help_compact_prompt')}\n"
                f"• [yellow]/compact status[/yellow] - {t('help_compact_status')}\n\n"
                f"[bold cyan]{t('help_examples')}:[/bold cyan]\n"
                f"• [green]/compact[/green] - {t('help_compact_ex_default')}\n"
                f"• [green]/compact model o3-mini[/green] - {t('help_compact_ex_model')}\n"
                '• [green]/compact prompt "Focus on vulnerabilities"[/green]\n'
                f"• [green]/cmp status[/green] - {t('help_compact_ex_status')}\n\n"
                f"[bold]{t('help_graph_features')}[/bold]\n"
                f"• {t('help_compact_feat_context')}\n"
                f"• {t('help_compact_feat_token')}\n"
                f"• {t('help_compact_feat_memory')}\n"
                f"• {t('help_compact_feat_clear')}\n\n"
                "[dim]Alias: /cmp[/dim]",
                title=t('help_compact_title'),
                border_style="yellow",
            )
        )
        return True

    def handle_flush(self, _: Optional[List[str]] = None) -> bool:
        """Show help for clearing histories."""
        console.print(
            Panel(
                f"[bold]{t('help_flush_header')}[/bold]\n\n"
                f"{t('help_flush_desc')}\n\n"
                f"[bold yellow]{t('help_agent_avail_cmds')}[/bold yellow]\n"
                f"• [yellow]/flush[/yellow] - {t('help_flush_current')}\n"
                f"• [yellow]/flush all[/yellow] - {t('help_flush_all')}\n"
                f"• [yellow]/flush <agent>[/yellow] - {t('help_flush_agent')}\n"
                f"• [yellow]/flush P1[/yellow] - {t('help_flush_parallel')}\n\n"
                f"[bold cyan]{t('help_examples')}:[/bold cyan]\n"
                f"• [green]/flush[/green] - {t('help_flush_ex_active')}\n"
                f"• [green]/flush all[/green] - {t('help_flush_ex_all')}\n"
                f"• [green]/flush red_teamer[/green] - {t('help_flush_ex_red')}\n"
                f"• [green]/clear P2[/green] - {t('help_flush_ex_p2')}\n\n"
                f"[bold]{t('help_flush_effects')}[/bold]\n"
                f"• {t('help_flush_eff_messages')}\n"
                f"• {t('help_flush_eff_tokens')}\n"
                f"• {t('help_flush_eff_config')}\n"
                f"• {t('help_flush_eff_mcp')}\n\n"
                "[dim]Alias: /clear[/dim]",
                title=t('help_flush_title'),
                border_style="red",
            )
        )
        return True

    def handle_load(self, _: Optional[List[str]] = None) -> bool:
        """Show help for loading JSONL files."""
        console.print(
            Panel(
                f"[bold]{t('help_load_header')}[/bold]\n\n"
                f"{t('help_load_desc')}\n\n"
                f"[bold yellow]{t('help_agent_avail_cmds')}[/bold yellow]\n"
                f"• [yellow]/load <file>[/yellow] - {t('help_load_current')}\n"
                f"• [yellow]/load <file> agent <name>[/yellow] - {t('help_load_agent')}\n"
                f"• [yellow]/load <file> all[/yellow] - {t('help_load_all')}\n"
                f"• [yellow]/load <file> parallel[/yellow] - {t('help_load_parallel')}\n\n"
                f"[bold cyan]{t('help_examples')}:[/bold cyan]\n"
                f"• [green]/load session.jsonl[/green] - {t('help_load_ex_current')}\n"
                f"• [green]/load ctf.jsonl agent red_teamer[/green] - {t('help_load_ex_agent')}\n"
                f"• [green]/load scan.jsonl all[/green] - {t('help_load_ex_all')}\n"
                f"• [green]/l pentest.jsonl parallel[/green] - {t('help_load_ex_parallel')}\n\n"
                f"[bold]{t('help_load_dist_modes')}[/bold]\n"
                f"• [cyan]agent[/cyan] - {t('help_load_dist_agent')}\n"
                f"• [cyan]all[/cyan] - {t('help_load_dist_all')}\n"
                f"• [cyan]parallel[/cyan] - {t('help_load_dist_parallel')}\n\n"
                "[dim]Alias: /l[/dim]",
                title=t('help_load_title'),
                border_style="green",
            )
        )
        return True

    def handle_workspace(self, _: Optional[List[str]] = None) -> bool:
        """Show help for workspace management."""
        console.print(
            Panel(
                f"[bold]{t('help_workspace_header')}[/bold]\n\n"
                f"{t('help_workspace_desc')}\n\n"
                f"[bold yellow]{t('help_agent_avail_cmds')}[/bold yellow]\n"
                f"• [yellow]/workspace set <name>[/yellow] - {t('help_workspace_set')}\n"
                f"• [yellow]/workspace get[/yellow] - {t('help_workspace_get')}\n"
                f"• [yellow]/workspace ls[/yellow] - {t('help_workspace_ls')}\n"
                f"• [yellow]/workspace exec <cmd>[/yellow] - {t('help_workspace_exec')}\n"
                f"• [yellow]/workspace copy <src> <dst>[/yellow] - {t('help_workspace_copy')}\n\n"
                f"[bold cyan]{t('help_examples')}:[/bold cyan]\n"
                f"• [green]/workspace set project1[/green] - {t('help_workspace_ex_set')}\n"
                f"• [green]/workspace ls[/green] - {t('help_workspace_ex_ls')}\n"
                f"• [green]/ws exec make build[/green] - {t('help_workspace_ex_exec')}\n"
                f"• [green]/ws copy /tmp/scan.txt .[/green] - {t('help_workspace_ex_copy')}\n\n"
                f"[bold]{t('help_graph_features')}[/bold]\n"
                f"• {t('help_workspace_feat_auto')}\n"
                f"• {t('help_workspace_feat_container')}\n"
                f"• {t('help_workspace_feat_logging')}\n"
                f"• {t('help_workspace_feat_env')}\n\n"
                "[dim]Alias: /ws[/dim]",
                title=t('help_workspace_title'),
                border_style="cyan",
            )
        )
        return True

    def handle_virtualization(self, _: Optional[List[str]] = None) -> bool:
        """Show help for Docker container management."""
        console.print(
            Panel(
                f"[bold]{t('help_virt_header')}[/bold]\n\n"
                f"{t('help_virt_desc')}\n\n"
                f"[bold yellow]{t('help_agent_avail_cmds')}[/bold yellow]\n"
                f"• [yellow]/virtualization pull <image>[/yellow] - {t('help_virt_pull')}\n"
                f"• [yellow]/virtualization run <image>[/yellow] - {t('help_virt_run')}\n"
                f"• [yellow]/virtualization run <container_id>[/yellow] - {t('help_virt_activate')}\n\n"
                f"[bold cyan]{t('help_examples')}:[/bold cyan]\n"
                f"• [green]/virt pull kalilinux/kali-rolling[/green] - {t('help_virt_ex_pull')}\n"
                f"• [green]/virt run parrotsec/security[/green] - {t('help_virt_ex_run')}\n"
                f"• [green]/virt run abc123[/green] - {t('help_virt_ex_activate')}\n\n"
                f"[bold]{t('help_virt_images')}[/bold]\n"
                "• [cyan]kalilinux/kali-rolling[/cyan] - Kali Linux\n"
                "• [cyan]parrotsec/security[/cyan] - Parrot Security\n\n"
                f"[bold]{t('help_graph_features')}[/bold]\n"
                f"• {t('help_virt_feat_network')}\n"
                f"• {t('help_virt_feat_mount')}\n"
                f"• {t('help_virt_feat_tty')}\n"
                f"• {t('help_virt_feat_env')}\n\n"
                "[dim]Alias: /virt[/dim]",
                title=t('help_virt_title'),
                border_style="blue",
            )
        )
        return True

    def handle_mcp(self, _: Optional[List[str]] = None) -> bool:
        """Show help for Model Context Protocol."""
        console.print(
            Panel(
                f"[bold]{t('help_mcp_header')}[/bold]\n\n"
                f"{t('help_mcp_desc')}\n\n"
                f"[bold yellow]{t('help_agent_avail_cmds')}[/bold yellow]\n"
                f"• [yellow]/mcp load <type> <config>[/yellow] - {t('help_mcp_load')}\n"
                f"• [yellow]/mcp list[/yellow] - {t('help_mcp_list')}\n"
                f"• [yellow]/mcp add <server> <agent>[/yellow] - {t('help_mcp_add')}\n"
                f"• [yellow]/mcp remove <server>[/yellow] - {t('help_mcp_remove')}\n"
                f"• [yellow]/mcp tools <server>[/yellow] - {t('help_mcp_tools')}\n"
                f"• [yellow]/mcp status[/yellow] - {t('help_mcp_status')}\n"
                f"• [yellow]/mcp associations[/yellow] - {t('help_mcp_assoc')}\n"
                f"• [yellow]/mcp test <server>[/yellow] - {t('help_mcp_test')}\n\n"
                f"[bold cyan]{t('help_mcp_server_types')}[/bold cyan]\n"
                f"• [green]sse[/green] - {t('help_mcp_type_sse')}\n"
                f"• [green]stdio[/green] - {t('help_mcp_type_stdio')}\n\n"
                f"[bold cyan]{t('help_examples')}:[/bold cyan]\n"
                "• [green]/mcp load sse http://localhost:3000[/green]\n"
                '• [green]/mcp load stdio "npx @modelcontextprotocol/server-sqlite"[/green]\n'
                "• [green]/mcp add filesystem red_teamer[/green]\n"
                "• [green]/mcp tools filesystem[/green]\n\n"
                f"[bold]{t('help_notes')}:[/bold]\n"
                f"• {t('help_mcp_note_fresh')}\n"
                f"• {t('help_mcp_note_discovery')}\n"
                f"• {t('help_mcp_note_headers')}\n\n"
                "[dim]Alias: /m[/dim]",
                title=t('help_mcp_title'),
                border_style="magenta",
            )
        )
        return True

    def handle_kill(self, _: Optional[List[str]] = None) -> bool:
        """Show help for process management."""
        console.print(
            Panel(
                f"[bold]{t('help_kill_header')}[/bold]\n\n"
                f"{t('help_kill_desc')}\n\n"
                f"[bold yellow]{t('help_usage')}:[/bold yellow]\n"
                f"• [yellow]/kill[/yellow] - {t('help_kill_all')}\n\n"
                f"[bold]{t('help_kill_what')}[/bold]\n"
                f"• {t('help_kill_ssh')}\n"
                f"• {t('help_kill_container')}\n"
                f"• {t('help_kill_bg')}\n"
                f"• {t('help_kill_hanging')}\n\n"
                f"[bold cyan]{t('help_examples')}:[/bold cyan]\n"
                f"• [green]/kill[/green] - {t('help_kill_ex_clean')}\n"
                f"• [green]/k[/green] - {t('help_kill_ex_alias')}\n\n"
                f"[bold]{t('help_kill_when')}[/bold]\n"
                f"• {t('help_kill_when_stuck')}\n"
                f"• {t('help_kill_when_reset')}\n"
                f"• {t('help_kill_when_switch')}\n\n"
                "[dim]Alias: /k[/dim]",
                title=t('help_kill_title'),
                border_style="red",
            )
        )
        return True

    def handle_commands(self, _: Optional[List[str]] = None) -> bool:
        """List all available commands."""
        console.print(
            Panel(
                f"[bold]{t('help_all_cmds')}[/bold]",
                title=t('help_cmd_ref'),
                border_style="yellow",
            )
        )

        # Create comprehensive command table
        all_commands = [
            # Agent Management
            (
                t('help_cat_agent'),
                "yellow",
                [
                    ("/agent", "/a", t('help_desc_agent')),
                    ("/parallel", "/par, /p", t('help_desc_parallel_short')),
                    ("/run", "/r", t('help_desc_run_short')),
                ],
            ),
            # Memory & History
            (
                t('help_cat_memory'),
                "green",
                [
                    ("/memory", "/mem", t('help_desc_memory')),
                    ("/history", "/his", t('help_desc_history')),
                    ("/compact", "/cmp", t('help_desc_compact_short')),
                    ("/flush", "/clear", t('help_desc_flush_short')),
                    ("/load", "/l", t('help_desc_load_short')),
                    ("/merge", "/mrg", t('help_desc_merge')),
                ],
            ),
            # Environment & Config
            (
                t('help_cat_env'),
                "blue",
                [
                    ("/config", "/cfg", t('help_desc_config_short')),
                    ("/env", "/e", t('help_desc_env_short')),
                    ("/workspace", "/ws", t('help_desc_workspace_short')),
                    ("/virtualization", "/virt", t('help_desc_virtualization_short')),
                ],
            ),
            # Tools & Integration
            (
                t('help_cat_tools'),
                "magenta",
                [
                    ("/mcp", "/m", t('help_desc_mcp_short')),
                    ("/platform", "/p", t('help_desc_platform_short')),
                    ("/shell", "/s, /$", t('help_desc_shell_short')),
                ],
            ),
            # Utilities
            (
                t('help_cat_utils'),
                "cyan",
                [
                    ("/model", "/mod", t('help_desc_model_short')),
                    ("/graph", "/g", t('help_desc_graph_short')),
                    ("/help", "/h, /?", t('help_desc_help')),
                    ("/kill", "/k", t('help_desc_kill_short')),
                    ("/exit", "/quit, /q", t('help_desc_exit_short')),
                ],
            ),
        ]

        for category, color, commands in all_commands:
            console.print(f"\n[bold {color}]{category}[/bold {color}]")
            table = Table(show_header=True, header_style="bold")
            table.add_column(t('help_col_command'), style="cyan")
            table.add_column(t('help_col_aliases'), style="green")
            table.add_column(t('help_col_description'), style="white")

            for cmd, aliases, desc in commands:
                table.add_row(cmd, aliases, desc)

            console.print(table)

        console.print(
            f"\n[dim]{t('help_detail_hint')}[/dim]"
        )
        return True

    def handle_quick(self, _: Optional[List[str]] = None) -> bool:
        """Show quick reference guide."""
        console.print(
            Panel(
                f"[bold]{t('help_quick_ref')}[/bold]",
                title=f"⚡ {t('help_quick_start')}",
                border_style="yellow",
            )
        )

        # Essential commands
        console.print(f"\n[bold yellow]{t('help_essential_commands')}[/bold yellow]")
        quick_ref = [
            ("[cyan]/agent list[/cyan]", t('help_see_agents')),
            ("[cyan]/agent select red_teamer[/cyan]", t('help_switch_agent')),
            ("[cyan]/model gpt-4o[/cyan]", t('help_change_model')),
            ("[cyan]/shell ls -la[/cyan]", t('help_run_shell')),
            ("[cyan]/config[/cyan]", t('help_view_settings')),
            ("[cyan]/help <topic>[/cyan]", t('help_get_help')),
        ]

        table = Table(show_header=False, box=None)
        table.add_column(width=35)
        table.add_column()
        for cmd, desc in quick_ref:
            table.add_row(f"  {cmd}", desc)
        console.print(table)

        # Common workflows
        console.print(f"\n[bold green]{t('help_common_workflows')}[/bold green]")
        workflows = [
            (
                f"[bold]{t('help_quick_start_ctf')}[/bold]",
                [
                    "/agent select one_tool_agent",
                    "/workspace set ctf_name",
                    t('help_quick_wf_describe'),
                ],
            ),
            (
                f"[bold]{t('help_quick_bug_bounty')}[/bold]",
                [
                    "/agent select bug_bounter",
                    "/model claude-3-7-sonnet-20250219",
                    t('help_quick_wf_test_vuln'),
                ],
            ),
            (
                f"[bold]{t('help_quick_parallel_recon')}[/bold]",
                [
                    "/parallel add red_teamer",
                    "/parallel add network_traffic_analyzer",
                    t('help_quick_wf_scan'),
                ],
            ),
        ]

        for title, steps in workflows:
            console.print(f"\n  {title}")
            for step in steps:
                console.print(f"    [green]→[/green] {step}")

        # Keyboard shortcuts
        console.print(f"\n[bold blue]{t('help_keyboard_shortcuts')}[/bold blue]")
        shortcuts = [
            ("[cyan]Tab[/cyan]", t('help_quick_tab')),
            ("[cyan]↑/↓[/cyan]", t('help_quick_arrows')),
            ("[cyan]Ctrl+C[/cyan]", t('help_quick_ctrlc')),
            ("[cyan]Ctrl+L[/cyan]", t('help_quick_ctrll')),
            ("[cyan]Ctrl+D[/cyan]", t('help_quick_ctrld')),
        ]

        table = Table(show_header=False, box=None)
        table.add_column(width=20)
        table.add_column()
        for key, action in shortcuts:
            table.add_row(f"  {key}", action)
        console.print(table)

        # Pro tips
        tips = [
            t('help_quick_pro_alias'),
            t('help_quick_pro_shell'),
            t('help_quick_pro_parallel'),
            t('help_quick_pro_mcp'),
        ]

        console.print("\n")
        console.print(create_notes_panel(tips, f"💡 {t('help_pro_tips')}", "cyan"))

        return True

    def handle_merge_help(self, _: Optional[List[str]] = None) -> bool:
        """Show help for merge command."""
        console.print(
            Panel(
                f"[bold]{t('help_merge_header')}[/bold]\n\n"
                f"{t('help_merge_desc')}\n\n"
                f"[bold yellow]{t('help_usage')}:[/bold yellow]\n"
                f"• [yellow]/merge <agents...> [options][/yellow] - {t('help_merge_usage_merge')}\n"
                f"• [yellow]/merge all [options][/yellow] - {t('help_merge_usage_all')}\n\n"
                f"[bold cyan]{t('help_merge_default')}[/bold cyan]\n"
                f"{t('help_merge_default_desc')}\n\n"
                f"[bold cyan]{t('help_options')}:[/bold cyan]\n"
                f"• [green]--strategy <type>[/green] - {t('help_merge_strategy')}\n"
                f"  • {t('help_merge_strat_chrono')}\n"
                f"  • {t('help_merge_strat_agent')}\n"
                f"  • {t('help_merge_strat_interleave')}\n"
                f"• [green]--target <name>[/green] - {t('help_merge_target')}\n"
                f"• [green]--remove-sources[/green] - {t('help_merge_remove')}\n\n"
                f"[bold cyan]{t('help_examples')}:[/bold cyan]\n"
                "• [green]/merge P1 P2[/green]\n"
                f"  → {t('help_merge_ex_p1p2')}\n"
                "• [green]/merge P1 P2 --target combined[/green]\n"
                f"  → {t('help_merge_ex_target')}\n"
                "• [green]/merge all[/green]\n"
                f"  → {t('help_merge_ex_all')}\n"
                "• [green]/merge all --target unified --remove-sources[/green]\n"
                f"  → {t('help_merge_ex_unified')}\n\n"
                f"[bold]{t('help_notes')}:[/bold]\n"
                f"• {t('help_merge_note_ids')}\n"
                f"• {t('help_merge_note_spaces')}\n"
                f"• {t('help_merge_note_dups')}\n"
                f"• {t('help_merge_note_alias')}\n\n"
                "[dim]Alias: /mrg[/dim]",
                title=t('help_merge_title'),
                border_style="green",
            )
        )
        return True

    def handle_quickstart(self, _: Optional[List[str]] = None) -> bool:
        """Show quickstart guide by calling the quickstart command."""
        from cai.repl.commands.base import handle_command

        return handle_command("/quickstart")


# Register the command
register_command(HelpCommand())
