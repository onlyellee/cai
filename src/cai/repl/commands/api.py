"""
API command for CAI REPL.
This module provides commands for managing the ALIAS_API_KEY in the .env file.
"""

import os
import re
from typing import List, Optional
from rich.console import Console  # pylint: disable=import-error
from rich.panel import Panel  # pylint: disable=import-error

from cai.repl.commands.base import Command, register_command

console = Console()


class ApiCommand(Command):
    """Command for managing the ALIAS_API_KEY in the .env file."""

    def __init__(self):
        """Initialize the api command."""
        super().__init__(
            name="/api",
            description="Set or display the ALIAS_API_KEY in the .env file",
            aliases=["/apikey"],
        )

        # Add subcommands
        self.add_subcommand("show", "Display the current ALIAS_API_KEY", self.handle_show)
        self.add_subcommand("set", "Set a new ALIAS_API_KEY", self.handle_set)

    def handle(self, args: Optional[List[str]] = None) -> bool:
        """Handle the api command.

        Args:
            args: Optional list of command arguments

        Returns:
            True if the command was handled successfully, False otherwise
        """
        if not args:
            return self.handle_show(args)

        # Check if first argument is a subcommand
        if args[0] in self.get_subcommands():
            subcommand = args[0]
            remaining_args = args[1:] if len(args) > 1 else None
            handler = self.subcommands[subcommand]["handler"]
            return handler(remaining_args)
        else:
            # Treat the argument as the API key to set
            return self.handle_set(args)

    def handle_show(self, args: Optional[List[str]] = None) -> bool:
        """Display the current ALIAS_API_KEY.

        Args:
            args: Optional list of command arguments (not used)

        Returns:
            True if the command was handled successfully
        """
        try:
            env_file_path = self._get_env_file_path()
            current_key = self._get_current_api_key(env_file_path)
            
            if current_key:
                # Mask the key for security, showing only first 6 and last 4 characters
                if len(current_key) > 10:
                    masked_key = current_key[:6] + "*" * (len(current_key) - 10) + current_key[-4:]
                else:
                    masked_key = current_key[:3] + "*" * (len(current_key) - 3)
                
                console.print(
                    Panel(
                        f"Current ALIAS_API_KEY: [bold green]{masked_key}[/bold green]",
                        border_style="green",
                        title="API Key Status",
                    )
                )
            else:
                console.print(
                    Panel(
                        "[yellow]ALIAS_API_KEY is not set or empty[/yellow]",
                        border_style="yellow",
                        title="API Key Status",
                    )
                )
            return True
            
        except Exception as e:
            console.print(f"[red]Error reading API key: {e}[/red]")
            return False

    def handle_set(self, args: Optional[List[str]] = None) -> bool:
        """Set a new ALIAS_API_KEY.

        Args:
            args: List containing the new API key

        Returns:
            True if the command was handled successfully
        """
        if not args or not args[0]:
            console.print("[red]Error: API key is required[/red]")
            console.print("Usage: /api <api_key>")
            console.print("       /api set <api_key>")
            return False

        new_api_key = args[0].strip()
        
        # Basic validation
        if len(new_api_key) < 10:
            console.print("[red]Error: API key seems too short (minimum 10 characters)[/red]")
            return False

        try:
            env_file_path = self._get_env_file_path()
            success = self._update_env_file(env_file_path, new_api_key)
            
            if success:
                # Mask the key for display
                if len(new_api_key) > 10:
                    masked_key = new_api_key[:6] + "*" * (len(new_api_key) - 10) + new_api_key[-4:]
                else:
                    masked_key = new_api_key[:3] + "*" * (len(new_api_key) - 3)
                
                console.print(
                    Panel(
                        f"ALIAS_API_KEY successfully updated to: [bold green]{masked_key}[/bold green]\n"
                        "[yellow]Note: Changes will take effect on the next agent interaction[/yellow]",
                        border_style="green",
                        title="API Key Updated",
                    )
                )
                
                # Also update the environment variable for immediate effect
                os.environ["ALIAS_API_KEY"] = new_api_key
                
                # Update sidebar immediately after success message
                self._update_sidebar_keys()
                
                return True
            else:
                console.print("[red]Error: Failed to update .env file[/red]")
                return False
                
        except Exception as e:
            console.print(f"[red]Error updating API key: {e}[/red]")
            return False

    def _get_env_file_path(self) -> str:
        """Get the path to the .env file.

        Returns:
            Path to the .env file
        """
        # Look for .env file in current working directory or project root
        current_dir = os.getcwd()
        
        # Try current directory first
        env_path = os.path.join(current_dir, ".env")
        if os.path.exists(env_path):
            return env_path
        
        # Try to find project root by looking for specific files
        search_dir = current_dir
        for _ in range(5):  # Limit search depth
            if any(os.path.exists(os.path.join(search_dir, marker)) 
                   for marker in ["pyproject.toml", "setup.py", ".git"]):
                env_path = os.path.join(search_dir, ".env")
                if os.path.exists(env_path):
                    return env_path
            parent = os.path.dirname(search_dir)
            if parent == search_dir:  # Reached root
                break
            search_dir = parent
        
        # Default to current directory if not found
        return os.path.join(current_dir, ".env")

    def _get_current_api_key(self, env_file_path: str) -> Optional[str]:
        """Get the current ALIAS_API_KEY from the .env file.

        Args:
            env_file_path: Path to the .env file

        Returns:
            Current API key or None if not found
        """
        if not os.path.exists(env_file_path):
            return None

        try:
            with open(env_file_path, "r", encoding="utf-8") as file:
                content = file.read()
            
            # Look for ALIAS_API_KEY line
            match = re.search(r'^ALIAS_API_KEY\s*=\s*["\']?([^"\']*)["\']?', content, re.MULTILINE)
            if match:
                return match.group(1).strip()
            
            return None
        except Exception:
            return None

    def _create_env_backup(self, env_file_path: str) -> bool:
        """Create a backup of the .env file before modifications"""
        try:
            import shutil
            import datetime
            
            if not os.path.exists(env_file_path):
                return True  # No file to backup
            
            # Create backup with timestamp
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"{env_file_path}.backup.{timestamp}"
            
            # Copy the current .env to backup
            shutil.copy2(env_file_path, backup_path)
            
            # Also create/update a simple .env.backup (latest backup)
            latest_backup_path = f"{env_file_path}.backup"
            shutil.copy2(env_file_path, latest_backup_path)
            
            console.print(f"[dim]Created .env backup: {backup_path}[/dim]")
            console.print(f"[dim]Updated latest backup: {latest_backup_path}[/dim]")
            
            return True
            
        except Exception as e:
            console.print(f"[red]Error creating .env backup: {e}[/red]")
            return False

    def _update_env_file(self, env_file_path: str, new_api_key: str) -> bool:
        """Update the ALIAS_API_KEY in the .env file.

        Args:
            env_file_path: Path to the .env file
            new_api_key: New API key to set

        Returns:
            True if successful, False otherwise
        """
        try:
            # Create backup before modification
            self._create_env_backup(env_file_path)
            # Read current content
            if os.path.exists(env_file_path):
                with open(env_file_path, "r", encoding="utf-8") as file:
                    content = file.read()
            else:
                content = ""

            # Update or add ALIAS_API_KEY
            alias_key_pattern = r'^(ALIAS_API_KEY\s*=\s*)["\']?[^"\']*["\']?'
            new_line = f'ALIAS_API_KEY="{new_api_key}"'
            
            if re.search(alias_key_pattern, content, re.MULTILINE):
                # Replace existing line
                content = re.sub(alias_key_pattern, new_line, content, flags=re.MULTILINE)
            else:
                # Add new line
                if content and not content.endswith('\n'):
                    content += '\n'
                content += new_line + '\n'

            # Write updated content
            with open(env_file_path, "w", encoding="utf-8") as file:
                file.write(content)
            
            return True
            
        except Exception as e:
            console.print(f"[red]Error writing to .env file: {e}[/red]")
            return False

    def _update_sidebar_keys(self) -> None:
        """Update the sidebar keys display using multiple strategies"""
        import os
        if os.getenv("CAI_DEBUG"):
            print(f"Debug: _update_sidebar_keys called")
        
        # Strategy 1: Try using CAITerminal._instance directly
        try:
            from cai.tui.cai_terminal import CAITerminal
            app = CAITerminal._instance
            if os.getenv("CAI_DEBUG"):
                print(f"Debug: CAITerminal._instance = {app}")
            
            if app and hasattr(app, 'sidebar'):
                if os.getenv("CAI_DEBUG"):
                    print(f"Debug: Found sidebar via CAITerminal._instance")
                
                # Send refresh message
                from cai.tui.components.sidebar import RefreshKeysMessage
                app.post_message(RefreshKeysMessage())
                
                # Also direct call
                app.sidebar.force_refresh_keys()
                
                if os.getenv("CAI_DEBUG"):
                    print(f"Debug: Refresh sent via CAITerminal._instance")
                return
                
        except Exception as e:
            if os.getenv("CAI_DEBUG"):
                print(f"Debug: Strategy 1 failed: {e}")
        
        # Strategy 2: Try App.get_running_app()
        try:
            from textual.app import App
            current_app = App.get_running_app()
            if os.getenv("CAI_DEBUG"):
                print(f"Debug: App.get_running_app() = {current_app}")
            
            if current_app and hasattr(current_app, 'sidebar'):
                if os.getenv("CAI_DEBUG"):
                    print(f"Debug: Found sidebar via get_running_app")
                
                from cai.tui.components.sidebar import RefreshKeysMessage
                current_app.post_message(RefreshKeysMessage())
                current_app.sidebar.force_refresh_keys()
                
                if os.getenv("CAI_DEBUG"):
                    print(f"Debug: Refresh sent via get_running_app")
                return
                    
        except Exception as e:
            if os.getenv("CAI_DEBUG"):
                print(f"Debug: Strategy 2 failed: {e}")
                import traceback
                traceback.print_exc()


# Register the command
register_command(ApiCommand())
