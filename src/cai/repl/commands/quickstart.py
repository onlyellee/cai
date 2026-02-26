"""
Quickstart command for CAI REPL.
Provides essential setup information and guidance for new users.
Automatically runs on first launch if ~/.cai doesn't exist.
"""

import os
import subprocess
from pathlib import Path
from typing import List, Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

from cai.repl.commands.base import Command, register_command
from cai.i18n import t

console = Console()


class QuickstartCommand(Command):
    """Command for displaying quickstart guide and setup information."""

    def __init__(self):
        """Initialize the quickstart command."""
        super().__init__(
            name="/quickstart",
            description=t('quickstart_desc'),
            aliases=["/qs", "/quick"],
        )

    def handle_no_args(self) -> bool:
        """Handle the command when no arguments are provided."""
        return self.show_quickstart()

    def check_local_endpoint(self, url: str) -> tuple[bool, str]:
        """Check if a local endpoint is accessible.

        Args:
            url: The endpoint URL to check

        Returns:
            Tuple of (is_accessible, message)
        """
        try:
            # Try using httpx which is already imported by the project
            import httpx

            with httpx.Client(timeout=2.0) as client:
                response = client.get(url)
                if response.status_code == 200:
                    return True, f"✅ {t('quickstart_accessible')}"
                else:
                    return False, f"❌ {t('quickstart_error_http', status=response.status_code)}"
        except httpx.ConnectError:
            return False, f"❌ {t('quickstart_connection_refused')}"
        except httpx.TimeoutException:
            return False, f"❌ {t('quickstart_timeout')}"
        except ImportError:
            # Fallback if httpx not available
            try:
                import urllib.request
                import urllib.error

                with urllib.request.urlopen(url, timeout=2) as response:
                    if response.status == 200:
                        return True, f"✅ {t('quickstart_accessible')}"
                    else:
                        return False, f"❌ {t('quickstart_error_http', status=response.status)}"
            except urllib.error.URLError:
                return False, f"❌ {t('quickstart_connection_refused')}"
            except Exception:
                return False, f"❌ {t('quickstart_error_checking')}"
        except Exception as e:
            return False, f"❌ {t('quickstart_error_generic', error=str(e))}"

    def check_ollama_models(self) -> List[str]:
        """Check available Ollama models."""
        try:
            import httpx

            with httpx.Client(timeout=2.0) as client:
                response = client.get("http://localhost:11434/api/tags")
                if response.status_code == 200:
                    data = response.json()
                    return [model["name"] for model in data.get("models", [])]
        except ImportError:
            # Fallback if httpx not available
            try:
                import urllib.request
                import json

                with urllib.request.urlopen(
                    "http://localhost:11434/api/tags", timeout=2
                ) as response:
                    if response.status == 200:
                        data = json.loads(response.read())
                        return [model["name"] for model in data.get("models", [])]
            except:
                pass
        except:
            pass
        return []

    def get_provider_name(self, api_key: str) -> str:
        """Get a formatted provider name from API key name.

        Args:
            api_key: Environment variable name (e.g., OPENAI_API_KEY)

        Returns:
            Formatted provider name
        """
        # Remove _API_KEY suffix to get provider name
        provider_part = api_key.replace("_API_KEY", "")

        # Convert SOME_PROVIDER to Some Provider
        # Handle special cases for better formatting
        if provider_part == "OPENAI":
            return "OpenAI"
        elif provider_part == "XAI":
            return "xAI"
        elif provider_part == "HUGGINGFACE":
            return "HuggingFace"
        elif provider_part == "OPENROUTER":
            return "OpenRouter"
        elif provider_part == "DEEPSEEK":
            return "DeepSeek"
        else:
            # General case: convert SOME_PROVIDER to Some Provider
            return provider_part.replace("_", " ").title()

    def check_api_keys(self) -> dict[str, bool]:
        """Check which API keys are configured dynamically."""
        keys = {}

        # Scan all environment variables for *_API_KEY pattern
        for env_var in os.environ:
            if env_var.endswith("_API_KEY"):
                # Check if the value is set and not empty
                keys[env_var] = bool(os.getenv(env_var))

        # Also check .env file for any API keys not in current environment
        try:
            from pathlib import Path

            env_file = Path.home() / "cai" / ".env"
            if not env_file.exists():
                # Try current directory
                env_file = Path(".env")

            if env_file.exists():
                with open(env_file, "r") as f:
                    for line in f:
                        line = line.strip()
                        if "=" in line and not line.startswith("#"):
                            key, _ = line.split("=", 1)
                            key = key.strip()
                            if key.endswith("_API_KEY") and key not in keys:
                                # Check if it's in environment (might be loaded)
                                keys[key] = bool(os.getenv(key))
        except:
            pass

        # Sort keys alphabetically for consistent display
        return dict(sorted(keys.items()))

    def show_quickstart(self) -> bool:
        """Display the quickstart guide."""
        # Welcome banner
        console.print(
            Panel(
                Text.from_markup(
                    f"[bold cyan]{t('quickstart_welcome_line1')}[/bold cyan]\n\n"
                    f"[yellow]{t('quickstart_welcome_line2')}[/yellow]\n\n"
                    f"{t('quickstart_welcome_line3')}"
                ),
                title=f"🚀 {t('quickstart_welcome_title')}",
                border_style="cyan",
                box=box.DOUBLE,
            )
        )

        # Step 1: API Requirements
        console.print(f"\n[bold yellow]📋 {t('quickstart_step1_title')}[/bold yellow]\n")
        console.print(t('quickstart_step1_desc'))

        api_keys = self.check_api_keys()

        # Create API status table
        api_table = Table(show_header=True, header_style="bold")
        api_table.add_column(t('quickstart_provider_col'), style="cyan")
        api_table.add_column(t('quickstart_env_var_col'), style="yellow")
        api_table.add_column(t('quickstart_status_col'), style="green")

        # Dynamically build provider list from detected API keys
        for env_var, is_set in api_keys.items():
            provider_name = self.get_provider_name(env_var)
            status = f"✅ {t('quickstart_status_set')}" if is_set else f"❌ {t('quickstart_status_not_set')}"
            api_table.add_row(provider_name, env_var, status)

        console.print(api_table)

        if not any(api_keys.values()):
            console.print(
                Panel(
                    f"[red]⚠️  {t('quickstart_no_api_keys_warning')}[/red]\n\n"
                    f"{t('quickstart_no_api_keys_msg')}\n\n"
                    "[yellow]export PROVIDER_API_KEY='your-key-here'[/yellow]\n\n"
                    f"{t('quickstart_no_api_keys_hint')}\n",
                    border_style="red",
                )
            )

        # Step 2: Local Models (Ollama)
        console.print(f"\n[bold yellow]🖥️  {t('quickstart_step2_title')}[/bold yellow]\n")
        console.print(t('quickstart_step2_desc'))

        # Check Ollama endpoints
        ollama_table = Table(show_header=True, header_style="bold")
        ollama_table.add_column(t('quickstart_endpoint_col'), style="cyan")
        ollama_table.add_column(t('quickstart_status_col'), style="green")
        ollama_table.add_column(t('quickstart_models_col'), style="yellow")

        # Check standard Ollama port
        is_accessible, status = self.check_local_endpoint("http://localhost:11434")
        models = self.check_ollama_models() if is_accessible else []
        model_str = t('quickstart_models_count', count=len(models)) if models else "N/A"
        ollama_table.add_row("http://localhost:11434", status, model_str)

        # Check Docker internal
        is_docker_accessible, docker_status = self.check_local_endpoint(
            "http://host.docker.internal:11434"
        )
        ollama_table.add_row("http://host.docker.internal:11434", docker_status, t('quickstart_docker_access'))

        console.print(ollama_table)

        if is_accessible and models:
            console.print(f"\n[green]{t('quickstart_available_models')}[/green] {', '.join(models[:5])}")
            if len(models) > 5:
                console.print(f"[dim]{t('quickstart_and_more', count=len(models) - 5)}[/dim]")

        console.print(
            Panel(
                f"[cyan]{t('quickstart_ollama_install')}[/cyan]\n"
                "1. Install: [yellow]curl -fsSL https://ollama.com/install.sh | sh[/yellow]\n"
                "2. Pull a model: [yellow]ollama pull llama3.1[/yellow]\n"
                "3. Set in .env: "
                "[yellow]OLLAMA_API_BASE='http://127.0.0.1:11434/v1'[/yellow]\n"
                "4. Use in CAI: [yellow]/model llama3.1[/yellow]",
                border_style="cyan",
            )
        )

        # Step 3: Choose Your Model
        console.print(f"\n[bold yellow]🤖 {t('quickstart_step3_title')}[/bold yellow]\n")

        # Check which API keys are available
        has_api_keys = any(api_keys.values())

        if has_api_keys:
            console.print(t('quickstart_has_keys_msg'))
            console.print(f"\n[cyan]{t('quickstart_see_models')}[/cyan]")
            console.print(
                f"  [yellow]1.[/yellow] {t('quickstart_step3_1')}"
            )
            console.print(
                f"  [yellow]2.[/yellow] {t('quickstart_step3_2')}"
            )
            console.print(
                f"  [yellow]3.[/yellow] {t('quickstart_step3_3')}"
            )
            console.print(
                f"\n[dim]{t('quickstart_default_model_note')}[/dim]"
            )
        else:
            console.print(
                Panel(
                    f"[red]⚠️  {t('quickstart_no_api_keys_warning')}[/red]\n\n"
                    f"{t('quickstart_no_keys_choose_model')}\n\n"
                    f"1. {t('quickstart_no_keys_step1')}\n"
                    f"2. {t('quickstart_no_keys_step2')}",
                    border_style="red",
                )
            )

        # Step 4: Core Commands
        console.print(f"\n[bold yellow]🎯 {t('quickstart_step4_title')}[/bold yellow]\n")

        commands_table = Table(show_header=True, header_style="bold", box=box.SIMPLE)
        commands_table.add_column(t('quickstart_cmd_col'), style="cyan")
        commands_table.add_column(t('quickstart_desc_col'), style="white")
        commands_table.add_column(t('quickstart_example_col'), style="green")

        essential_commands = [
            ("/agent list", t('quickstart_view_agents'), "/agent list"),
            ("/agent select <name>", t('quickstart_switch_agent'), "/agent select red_teamer"),
            ("/model", t('quickstart_view_model'), "/model"),
            ("/model-show", t('quickstart_list_models'), "/model-show"),
            ("/model <name>", t('quickstart_change_model'), "/model gpt-4o"),
            ("/config", t('quickstart_view_settings'), "/config"),
            ("/help", t('quickstart_get_help'), "/help agent"),
            ("/shell <cmd>", t('quickstart_run_shell'), "/shell ls -la"),
            ("$ <cmd>", t('quickstart_quick_shell'), "$ whoami"),
        ]

        for cmd, desc, example in essential_commands:
            commands_table.add_row(cmd, desc, example)

        console.print(commands_table)

        # Step 5: Quick Examples
        console.print(f"\n[bold yellow]💡 {t('quickstart_step5_title')}[/bold yellow]\n")

        examples = [
            (
                f"[bold]{t('quickstart_example_ctf')}[/bold]",
                [
                    "# Select the CTF agent",
                    "/agent select one_tool_agent",
                    "# Describe your challenge",
                    "I have a binary at /tmp/challenge that asks for a password",
                ],
            ),
            (
                f"[bold]{t('quickstart_example_web')}[/bold]",
                [
                    "# Switch to bug bounty agent",
                    "/agent select bug_bounter",
                    "# Test a website",
                    "Test https://example.com for common vulnerabilities",
                ],
            ),
            (
                f"[bold]{t('quickstart_example_recon')}[/bold]",
                [
                    "# Use the red team agent",
                    "/agent select red_teamer",
                    "# Scan network",
                    "Scan the network 192.168.1.0/24 for open ports",
                ],
            ),
        ]

        for title, commands in examples:
            console.print(f"{title}")
            for cmd in commands:
                if cmd.startswith("#"):
                    console.print(f"  [dim]{cmd}[/dim]")
                else:
                    console.print(f"  [green]→[/green] [yellow]{cmd}[/yellow]")
            console.print()

        # Step 6: Features Overview
        console.print(f"\n[bold yellow]🛠️  {t('quickstart_step6_title')}[/bold yellow]\n")

        features_table = Table(show_header=False, box=None)
        features_table.add_column(style="cyan", width=25)
        features_table.add_column(style="white")

        features = [
            (t('quickstart_feat_multi_agents'), t('quickstart_feat_multi_agents_desc')),
            (t('quickstart_feat_tool_integration'), t('quickstart_feat_tool_integration_desc')),
            (t('quickstart_feat_parallel'), t('quickstart_feat_parallel_desc')),
            (t('quickstart_feat_memory'), t('quickstart_feat_memory_desc')),
            (t('quickstart_feat_mcp'), t('quickstart_feat_mcp_desc')),
            (t('quickstart_feat_docker'), t('quickstart_feat_docker_desc')),
        ]

        for feature, desc in features:
            features_table.add_row(f"  • {feature}", desc)

        console.print(features_table)

        # Configuration directory info
        cai_dir = Path.home() / ".cai"
        console.print(f"\n[bold yellow]📁 {t('quickstart_config_dir_title')}[/bold yellow]\n")
        console.print(t('quickstart_config_dir_msg', path=cai_dir))

        if not cai_dir.exists():
            console.print(f"[yellow]→ {t('quickstart_dir_will_create')}[/yellow]")
        else:
            console.print(f"[green]✓ {t('quickstart_dir_exists')}[/green]")

        # Next steps
        console.print(
            Panel(
                f"[bold]🎉 {t('quickstart_ready_line1')}[/bold]\n\n"
                f"[cyan]{t('quickstart_ready_next')}[/cyan]\n"
                f"1. {t('quickstart_ready_step1')}\n"
                f"2. {t('quickstart_ready_step2')}\n"
                f"3. {t('quickstart_ready_step3')}\n"
                f"4. {t('quickstart_ready_step4')}\n\n"
                f"[dim]{t('quickstart_this_guide')}[/dim]",
                title=t('qs_ready_title'),
                border_style="green",
            )
        )

        return True


# Register the command
register_command(QuickstartCommand())
