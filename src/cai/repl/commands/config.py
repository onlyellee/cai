"""
Config command for CAI via environmental variables.
"""

# Standard library imports
import os
from typing import List, Optional

# Third party imports
from rich.console import Console  # pylint: disable=import-error
from rich.table import Table  # pylint: disable=import-error

# Local imports
from cai.repl.commands.base import Command, register_command
from cai.i18n import t

console = Console()

# Define environment variables with descriptions and default values
# Organized by category for better maintainability
ENV_VARS = {
    # ===========================================
    # CTF (Capture The Flag) Variables
    # ===========================================
    1: {"name": "CTF_NAME", "description": "Name of the CTF challenge to run", "default": None},
    2: {"name": "CTF_CHALLENGE", "description": "Specific challenge name within the CTF", "default": None},
    3: {"name": "CTF_SUBNET", "description": "Network subnet for CTF container", "default": "192.168.3.0/24"},
    4: {"name": "CTF_IP", "description": "IP address for CTF container", "default": "192.168.3.100"},
    5: {"name": "CTF_INSIDE", "description": "Conquer CTF from within container", "default": "true"},
    6: {"name": "CTF_MODEL", "description": "Model override for CTF challenges", "default": None},
    7: {"name": "CTF_CONTAINER_NAME", "description": "Docker container name for CTF", "default": None},
    8: {"name": "CTF_INSTANCE_ID", "description": "Instance ID for CTF tracking", "default": ""},

    # ===========================================
    # Core Agent & Model Settings
    # ===========================================
    10: {"name": "CAI_MODEL", "description": "Model to use for agents", "default": "alias1"},
    11: {"name": "CAI_AGENT_TYPE", "description": "Agent type (boot2root, one_tool, etc.)", "default": "one_tool"},
    12: {"name": "CAI_TEMPERATURE", "description": "Model temperature (0.0-2.0)", "default": "0.7"},
    13: {"name": "CAI_TOP_P", "description": "Nucleus sampling top_p (0.0-1.0)", "default": "1.0"},
    14: {"name": "CAI_DEBUG", "description": "Debug level (0: tool only, 1: verbose, 2: CLI)", "default": "1"},
    15: {"name": "CAI_BRIEF", "description": "Enable brief output mode", "default": "false"},
    16: {"name": "CAI_STATE", "description": "Enable stateful mode", "default": "false"},
    17: {"name": "CAI_DEFAULT_AGENT", "description": "Default agent type", "default": "redteam_agent"},

    # ===========================================
    # Streaming & Output Control
    # ===========================================
    20: {"name": "CAI_STREAM", "description": "Enable LLM inference streaming", "default": "false"},
    21: {"name": "CAI_TOOL_STREAM", "description": "Enable tool output streaming", "default": "true"},
    22: {"name": "CAI_SHOW_CACHE", "description": "Show cache info and message history", "default": "false"},
    23: {"name": "CAI_DEBUG_TOOLS_VIZ", "description": "Debug tool visualization", "default": "false"},
    24: {"name": "CAI_DEBUG_STREAMING", "description": "Debug streaming output", "default": "false"},
    25: {"name": "CAI_CTX_DEBUG", "description": "Debug context operations", "default": "false"},

    # ===========================================
    # Parallelization & Execution
    # ===========================================
    30: {"name": "CAI_PARALLEL", "description": "Number of parallel agents (1-20)", "default": "1"},
    31: {"name": "CAI_PARALLEL_AGENTS", "description": "Comma-separated agent names for parallel", "default": None},
    32: {"name": "CAI_AUTO_RUN_PARALLEL", "description": "Auto-run parallel agents on startup", "default": "false"},
    33: {"name": "CAI_AUTO_RUN_QUEUE", "description": "Auto-run queued commands", "default": "false"},
    34: {"name": "CAI_QUEUE_FILE", "description": "Path to command queue file", "default": None},

    # ===========================================
    # Execution Limits
    # ===========================================
    40: {"name": "CAI_MAX_TURNS", "description": "Maximum turns for agent interactions", "default": "inf"},
    41: {"name": "CAI_MAX_INTERACTIONS", "description": "Maximum interactions in session", "default": "inf"},
    42: {"name": "CAI_PRICE_LIMIT", "description": "Price limit in dollars", "default": "1"},
    43: {"name": "CAI_TOOL_TIMEOUT", "description": "Tool execution timeout (seconds)", "default": None},
    44: {"name": "CAI_IDLE_TIMEOUT", "description": "Idle timeout before cleanup", "default": "100"},
    45: {"name": "CAI_CODE_TIMEOUT", "description": "Code execution timeout", "default": "30"},

    # ===========================================
    # Memory & Context
    # ===========================================
    50: {"name": "CAI_MEMORY", "description": "Memory mode (false, episodic, semantic, all)", "default": "false"},
    51: {"name": "CAI_MEMORY_ONLINE", "description": "Enable online memory mode", "default": "false"},
    52: {"name": "CAI_MEMORY_OFFLINE", "description": "Enable offline memory", "default": "false"},
    53: {"name": "CAI_MEMORY_ONLINE_INTERVAL", "description": "Turns between memory updates", "default": "5"},
    54: {"name": "CAI_MEMORY_COLLECTION", "description": "Qdrant collection for memory", "default": "default"},
    55: {"name": "CAI_ENV_CONTEXT", "description": "Add environment context to LLM", "default": "true"},
    56: {"name": "CAI_CTX_TRUNC", "description": "Enable context truncation", "default": "false"},

    # ===========================================
    # Workspace
    # ===========================================
    60: {"name": "CAI_WORKSPACE", "description": "Current workspace name", "default": None},
    61: {"name": "CAI_WORKSPACE_DIR", "description": "Workspace directory path", "default": None},
    62: {"name": "CAI_ACTIVE_CONTAINER", "description": "Active Docker container ID", "default": ""},
    63: {"name": "CAI_ACTIVE_CONTAINER_DEFAULT", "description": "Default container", "default": ""},

    # ===========================================
    # Support & Meta Agent
    # ===========================================
    70: {"name": "CAI_SUPPORT_MODEL", "description": "Model for support agent", "default": "o3-mini"},
    71: {"name": "CAI_SUPPORT_INTERVAL", "description": "Turns between support executions", "default": "5"},
    72: {"name": "CAI_META_AGENT", "description": "Enable meta agent", "default": "false"},
    73: {"name": "CAI_META_MODEL", "description": "Model for meta agent", "default": None},
    74: {"name": "CAI_META_AUTOCLOSE_GRACE", "description": "Meta agent auto-close grace (s)", "default": "1.5"},

    # ===========================================
    # Council (Multi-LLM Voting)
    # ===========================================
    80: {"name": "CAI_COUNCIL", "description": "Comma-separated council models", "default": "gpt-4o,gpt-4o-mini"},
    81: {"name": "CAI_COUNCIL_AUTO", "description": "Auto-convene (false/true/N)", "default": "false"},
    82: {"name": "CAI_COUNCIL_PROMPT", "description": "Custom council review prompt", "default": None},
    83: {"name": "CAI_COUNCIL_DEBUG", "description": "Enable council debug output", "default": "false"},

    # ===========================================
    # CTR (Control The Rope)
    # ===========================================
    90: {"name": "CAI_CTR_DIGEST_MODE", "description": "CTR mode: llm or algorithmic", "default": "llm"},
    91: {"name": "CAI_CTR_DIGEST_MODEL", "description": "Model for LLM-based CTR", "default": "alias1"},
    92: {"name": "CAI_CTR_OUTPUT_DIR", "description": "CTR output directory", "default": None},
    93: {"name": "CAI_CTR_DEFAULT_OUTPUT_DIR", "description": "Default CTR output dir", "default": None},
    94: {"name": "CAI_CTR_DEFAULT_RUN", "description": "Default CTR run identifier", "default": None},
    95: {"name": "CAI_CTR_IS_CTF", "description": "CTR in CTF mode", "default": "false"},
    96: {"name": "CAI_CTR_DISTANCE_HEURISTIC", "description": "CTR graph distance heuristic", "default": None},
    97: {"name": "CAI_GCTR_NITERATIONS", "description": "Tool calls before GCTR analysis", "default": "5"},

    # ===========================================
    # Tracing & Telemetry
    # ===========================================
    100: {"name": "CAI_TRACING", "description": "Enable OpenTelemetry tracing", "default": "true"},
    101: {"name": "CAI_TELEMETRY", "description": "Enable telemetry collection", "default": "true"},
    102: {"name": "CAI_DISABLE_SESSION_RECORDING", "description": "Disable JSONL recording", "default": "false"},
    103: {"name": "CAI_DISABLE_USAGE_TRACKING", "description": "Disable usage tracking", "default": "false"},

    # ===========================================
    # Security & Guardrails
    # ===========================================
    110: {"name": "CAI_GUARDRAILS", "description": "Enable security guardrails", "default": "false"},
    111: {"name": "CAI_PLAN", "description": "Enable planning mode", "default": "false"},

    # ===========================================
    # Pricing & Cost Control
    # ===========================================
    120: {"name": "CAI_COST_DISPLAYED", "description": "Show cost display", "default": "false"},
    121: {"name": "CAI_ENABLE_PRICING_FETCH", "description": "Enable async pricing fetch", "default": "false"},
    122: {"name": "CAI_DEBUG_PRICING", "description": "Debug pricing calculations", "default": "false"},
    123: {"name": "CAI_PRICING_FILE", "description": "Custom pricing data file", "default": None},
    124: {"name": "CAI_PRICINGS_DIR", "description": "Pricing data directory", "default": None},

    # ===========================================
    # Reporting
    # ===========================================
    130: {"name": "CAI_REPORT", "description": "Report mode (ctf, nis2, pentesting)", "default": "ctf"},
    131: {"name": "CAI_CONTINUATION_FALLBACK_MODEL", "description": "Fallback model for continuation", "default": None},

    # ===========================================
    # API Server (CLI only)
    # ===========================================
    140: {"name": "CAI_API_HOST", "description": "API server host", "default": "127.0.0.1"},
    141: {"name": "CAI_API_PORT", "description": "API server port", "default": "8000"},
    142: {"name": "CAI_API_CORS", "description": "CORS allowed origins", "default": "*"},
    143: {"name": "CAI_API_KEY_HEADER", "description": "API key header name", "default": "X-CAI-API-Key"},
    144: {"name": "CAI_API_LOG_AUTH", "description": "Log authentication", "default": "false"},
    145: {"name": "CAI_API_LOG_REQUESTS", "description": "Log API requests", "default": "false"},
    146: {"name": "CAI_API_LOG_LEVEL", "description": "API log level", "default": "info"},
    147: {"name": "CAI_API_RELOAD", "description": "API hot-reload mode", "default": "false"},
    148: {"name": "CAI_API_WORKERS", "description": "API worker processes", "default": "1"},

    # ===========================================
    # Authentication
    # ===========================================
    150: {"name": "CAI_AUTH_BASE_URL", "description": "Auth service base URL", "default": None},
    151: {"name": "CAI_AUTH_DEVICE_PORT", "description": "Device auth port", "default": "10101"},
    152: {"name": "CAI_AUTH_PUBLIC_HOST", "description": "Public auth host", "default": None},
    153: {"name": "CAI_AUTH_PUBLIC_PORT", "description": "Public auth port", "default": None},
    154: {"name": "CAI_AUTH_SESSION_TTL_SECONDS", "description": "Session TTL (seconds)", "default": None},

    # ===========================================
    # MCP (Model Context Protocol)
    # ===========================================
    160: {"name": "CAI_MCP_TOKEN", "description": "MCP authentication token", "default": None},
    161: {"name": "CAI_MCP_AUTH_TOKEN", "description": "MCP auth token (alt)", "default": None},
    162: {"name": "CAI_MCP_SSE_TIMEOUT", "description": "MCP SSE timeout (s)", "default": "5"},
    163: {"name": "CAI_MCP_SSE_READ_TIMEOUT", "description": "MCP SSE read timeout (s)", "default": "300"},

    # ===========================================
    # TUI Mode Settings (TUI only)
    # ===========================================
    170: {"name": "CAI_TUI_MODE", "description": "Enable TUI mode", "default": "false"},
    171: {"name": "CAI_TUI_STARTUP_YAML", "description": "TUI startup config YAML", "default": None},
    172: {"name": "CAI_TUI_SHARED_PROMPT", "description": "Shared TUI prompt", "default": None},
    173: {"name": "CAI_TUI_MAX_LINES", "description": "Max TUI output lines", "default": None},
    174: {"name": "CAI_TUI_MAX_RERENDERS_PER_SEC", "description": "Max TUI re-renders/s", "default": None},

    # ===========================================
    # Advanced/Internal
    # ===========================================
    180: {"name": "CAI_VERSION", "description": "CAI version string", "default": "dev"},
    181: {"name": "CAI_THEME", "description": "UI color theme", "default": None},
    182: {"name": "CAI_SKIP_NETWORK_CHECK", "description": "Skip network checks", "default": "false"},
    183: {"name": "CAI_AUTO_COMPACT", "description": "Enable auto-compaction", "default": None},
    184: {"name": "CAI_AUTO_COMPACT_THRESHOLD", "description": "Auto-compact token threshold", "default": None},
    185: {"name": "CAI_WARN_UNATTRIBUTED", "description": "Warn unattributed content", "default": "false"},
    186: {"name": "CAI_UNATTRIBUTED_LOG", "description": "Unattributed content log", "default": "~/.cai_unattributed.log"},
    187: {"name": "CAI_PATTERN_DESCRIPTION", "description": "Agent pattern description", "default": ""},
    188: {"name": "CAI_MODEL_LIST", "description": "Custom model list", "default": None},
    189: {"name": "CAI_CONTEXT_USAGE", "description": "Context usage tracking", "default": None},
    190: {"name": "CAI_SESSION_INPUT_WAIT", "description": "Session input wait (s)", "default": "5.0"},
    191: {"name": "CAI_BROADCAST_MODE", "description": "Broadcast mode for parallel", "default": None},
}


def get_env_var_value(var_name: str) -> str:
    """Get the current value of an environment variable.

    Args:
        var_name: The name of the environment variable

    Returns:
        The current value or the default value if not set
    """
    for var_info in ENV_VARS.values():
        if var_info["name"] == var_name:
            return os.environ.get(var_name, var_info["default"] or t('config_not_set'))
    return t('config_unknown_var')


def set_env_var(var_name: str, value: str) -> bool:
    """Set an environment variable.

    Args:
        var_name: The name of the environment variable
        value: The value to set

    Returns:
        True if successful, False otherwise
    """
    os.environ[var_name] = value
    return True


class ConfigCommand(Command):
    """Command for displaying and configuring environment variables."""

    def __init__(self):
        """Initialize the config command."""
        super().__init__(
            name="/config",
            description=t('config_desc'),
            aliases=["/cfg"],
        )
        # Dynamically add agent-specific model variables
        self._add_agent_model_vars()

        # Add subcommands
        self.add_subcommand(
            "list", t('config_sub_list'), self.handle_list
        )
        self.add_subcommand("set", t('config_sub_set'), self.handle_set)
        self.add_subcommand(
            "get", t('config_sub_get'), self.handle_get
        )

    def handle_no_args(self) -> bool:
        """Handle the command when no arguments are provided.

        Returns:
            True if the command was handled successfully, False otherwise
        """
        return self.handle_list(None)

    def _find_var_by_name(self, var_name: str) -> Optional[int]:
        """Find variable number by name.

        Args:
            var_name: The variable name (e.g. 'CAI_PRICE_LIMIT')

        Returns:
            The variable number if found, None otherwise
        """
        for num, var_info in ENV_VARS.items():
            if var_info["name"] == var_name:
                return num
        return None

    def handle(self, args: Optional[List[str]] = None) -> bool:
        """Handle the command with support for VAR_NAME=value syntax.

        Supports:
        - /config list
        - /config set <number> <value>
        - /config get <number>
        - /config VAR_NAME=value  (direct set by name)
        - /config VAR_NAME value  (direct set by name)

        Args:
            args: Command arguments

        Returns:
            True if handled successfully, False otherwise
        """
        if not args:
            return self.handle_no_args()

        first_arg = args[0]

        # Check for known subcommands first
        if first_arg in self.subcommands:
            handler = self.subcommands[first_arg]["handler"]
            return handler(args[1:] if len(args) > 1 else None)

        # Check for VAR_NAME=value syntax
        if "=" in first_arg:
            parts = first_arg.split("=", 1)
            if len(parts) == 2:
                var_name, value = parts
                return self._set_by_name(var_name, value)

        # Check for VAR_NAME value syntax (two args where first is a known var)
        if len(args) >= 2:
            var_name = args[0]
            var_num = self._find_var_by_name(var_name)
            if var_num is not None:
                value = args[1]
                return self._set_by_name(var_name, value)

        # Unknown subcommand
        return self.handle_unknown_subcommand(first_arg)

    def _set_by_name(self, var_name: str, value: str) -> bool:
        """Set a variable by its name.

        Args:
            var_name: The variable name (e.g. 'CAI_PRICE_LIMIT')
            value: The value to set

        Returns:
            True if successful, False otherwise
        """
        var_num = self._find_var_by_name(var_name)
        if var_num is None:
            console.print(f"[red]{t('config_error_unknown_var', var_name=var_name)}[/red]")
            console.print(f"[yellow]{t('config_use_list')}[/yellow]")
            return False

        old_value = get_env_var_value(var_name)
        set_env_var(var_name, value)
        console.print(f"[green]{t('config_var_changed', var_name=var_name, value=value, old_value=old_value)}[/green]")
        return True

    def _add_agent_model_vars(self):
        """Add CAI_<AGENT>_MODEL variables for each available agent."""
        try:
            from cai.agents import get_available_agents

            available_agents = get_available_agents()
            current_var_num = max(ENV_VARS.keys()) + 1

            # Add general agent model overrides
            for agent_key in sorted(available_agents.keys()):
                var_name = f"CAI_{agent_key.upper()}_MODEL"
                agent_obj = available_agents[agent_key]
                agent_display_name = getattr(agent_obj, "name", agent_key)

                ENV_VARS[current_var_num] = {
                    "name": var_name,
                    "description": f"Model override for {agent_display_name} agent",
                    "default": None,
                }
                current_var_num += 1

            # Add instance-specific model overrides for parallel execution
            parallel_count = int(os.getenv("CAI_PARALLEL", "1"))
            if parallel_count > 1:
                # Add instance-specific variables for each agent type
                for agent_key in sorted(available_agents.keys()):
                    agent_obj = available_agents[agent_key]
                    agent_display_name = getattr(agent_obj, "name", agent_key)

                    for instance_num in range(1, parallel_count + 1):
                        var_name = f"CAI_{agent_key.upper()}_{instance_num}_MODEL"

                        ENV_VARS[current_var_num] = {
                            "name": var_name,
                            "description": f"Model override for {agent_display_name} instance #{instance_num}",
                            "default": None,
                        }
                        current_var_num += 1
        except Exception:
            # If we can't get agents, just skip adding these variables
            pass

    def handle_list(self, _: Optional[List[str]] = None) -> bool:
        """List all environment variables and their values.

        Args:
            _: Ignored arguments

        Returns:
            True if successful
        """
        table = Table(title=t('config_env_vars'), show_header=True, header_style="bold yellow")
        table.add_column("#", style="dim")
        table.add_column(t('config_col_variable'), style="yellow")
        table.add_column(t('config_col_value'), style="green")
        table.add_column(t('config_col_default'), style="blue")
        table.add_column(t('config_col_description'))

        for num, var_info in ENV_VARS.items():
            var_name = var_info["name"]
            current_value = get_env_var_value(var_name)
            default_value = var_info["default"] or t('config_not_set')

            table.add_row(str(num), var_name, current_value, default_value, var_info["description"])

        console.print(table)
        console.print(f"\n{t('config_usage_set')}")
        return True

    def handle_get(self, args: Optional[List[str]] = None) -> bool:
        """Get the value of an environment variable by its number.

        Args:
            args: Command arguments [var_number]

        Returns:
            True if successful, False otherwise
        """
        if not args or len(args) < 1:
            console.print(f"[yellow]{t('config_usage_get')}[/yellow]")
            return False

        try:
            var_num = int(args[0])
            if var_num not in ENV_VARS:
                console.print(f"[red]{t('config_var_not_found', num=var_num)}[/red]")
                return False

            var_info = ENV_VARS[var_num]
            var_name = var_info["name"]
            current_value = get_env_var_value(var_name)

            console.print(
                f"[yellow]{var_name}[/yellow]: "
                f"[green]{current_value}[/green] "
                f"({t('config_col_default')}: [blue]{var_info['default'] or t('config_not_set')}[/blue])"
            )
            return True
        except ValueError:
            console.print(f"[red]{t('config_var_invalid')}[/red]")
            return False

    def handle_set(self, args: Optional[List[str]] = None) -> bool:
        """Set an environment variable by its number.

        Args:
            args: Command arguments [var_number, value]

        Returns:
            True if successful, False otherwise
        """
        if not args or len(args) < 2:
            console.print(f"[yellow]{t('config_usage_set')}[/yellow]")
            return False

        try:
            var_num = int(args[0])
            if var_num not in ENV_VARS:
                console.print(f"[red]{t('config_var_not_found', num=var_num)}[/red]")
                return False

            value = args[1]
            var_info = ENV_VARS[var_num]
            var_name = var_info["name"]

            old_value = get_env_var_value(var_name)
            set_env_var(var_name, value)

            console.print(f"[green]{t('config_var_changed', var_name=var_name, value=value, old_value=old_value)}[/green]")
            return True
        except ValueError:
            console.print(f"[red]{t('config_var_invalid')}[/red]")
            return False


# Register the command
register_command(ConfigCommand())
