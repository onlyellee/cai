"""
Virtualization command for CAI REPL.
This module provides commands for setting up and managing Docker virtualization
environments.
"""

# Standard library imports
import os
import json
import subprocess
import datetime
import time
from typing import List, Optional, Dict, Any, Tuple

# Third-party imports
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.markdown import Markdown
import rich.box

# Local imports
from cai.i18n import t
from cai.repl.commands.base import Command, register_command

console = Console()


class WorkspaceCommand(Command):
    """Command for workspace management within Docker containers or locally."""

    def __init__(self):
        """Initialize the workspace command."""
        super().__init__(
            name="/workspace",
            description=t('workspace_description'),
            aliases=["/ws"],
        )

        # Add subcommands
        self.add_subcommand("set", t('workspace_sub_set'), self.handle_set)
        self.add_subcommand("get", t('workspace_sub_get'), self.handle_get)
        self.add_subcommand("ls", t('workspace_sub_ls'), self.handle_ls_subcommand)
        self.add_subcommand(
            "exec", t('workspace_sub_exec'), self.handle_exec_subcommand
        )
        self.add_subcommand(
            "copy", t('workspace_sub_copy'), self.handle_copy_subcommand
        )

    def handle(self, args: Optional[List[str]] = None) -> bool:
        """Handle the workspace command.

        Args:
            args: Optional list of command arguments

        Returns:
            True if the command was handled successfully, False otherwise
        """
        # If there are subcommands, process them
        if args and args[0] in self.subcommands:
            return super().handle(args)

        # No arguments means show workspace info (same as get)
        return self.handle_get()

    def handle_no_args(self) -> bool:
        """Handle the command when no arguments are provided."""
        return self.handle_get()

    def handle_get(self, _: Optional[List[str]] = None) -> bool:
        """Display the current workspace name and directory information."""
        # Get workspace info
        workspace_name = os.getenv("CAI_WORKSPACE", None)

        # Check if a container is active
        active_container = os.getenv("CAI_ACTIVE_CONTAINER", "")

        # Determine environment (container or host)
        if active_container:
            try:
                # Get container details
                result = subprocess.run(
                    ["docker", "inspect", active_container],
                    capture_output=True,
                    text=True,
                    check=False,
                )

                if result.returncode == 0:
                    container_info = json.loads(result.stdout)
                    if container_info:
                        image = container_info[0].get("Config", {}).get("Image", "unknown")
                        env_type = "container"
                        env_name = f"Container ({image})"

                        # For containers, if workspace is set, use container workspace path
                        # otherwise use root directory
                        if workspace_name:
                            # This will create the workspace in the container if it doesn't exist
                            workspace_dir = f"/workspace/workspaces/{workspace_name}"
                            # Ensure the directory exists in the container
                            subprocess.run(
                                ["docker", "exec", active_container, "mkdir", "-p", workspace_dir],
                                capture_output=True,
                                check=False,
                            )
                        else:
                            workspace_dir = "/"
                else:
                    env_type = "host"
                    env_name = "Host System (container not running)"
                    # Use common._get_workspace_dir() for consistency
                    try:
                        from cai.tools.common import _get_workspace_dir as get_common_workspace_dir

                        workspace_dir = get_common_workspace_dir()
                    except ImportError:
                        workspace_dir = os.getcwd()  # Basic fallback
            except Exception:
                env_type = "host"
                env_name = "Host System (error inspecting container)"
                # Use common._get_workspace_dir() for consistency
                try:
                    from cai.tools.common import _get_workspace_dir as get_common_workspace_dir

                    workspace_dir = get_common_workspace_dir()
                except ImportError:
                    workspace_dir = os.getcwd()  # Basic fallback
        else:
            env_type = "host"
            env_name = "Host System"
            # Use common._get_workspace_dir() for consistency
            try:
                from cai.tools.common import _get_workspace_dir as get_common_workspace_dir

                workspace_dir = get_common_workspace_dir()
            except ImportError:
                workspace_dir = os.getcwd()  # Basic fallback

        # Show workspace information
        console.print(
            Panel(
                f"{t('workspace_current')} [bold green]{workspace_name or 'None'}[/bold green]\n"
                f"{t('workspace_working_env')} [bold]{env_name}[/bold]\n"
                f"{t('workspace_directory')} [bold]{workspace_dir}[/bold]",
                title=t('workspace_info_title'),
                border_style="green",
            )
        )

        # Show available workspace commands
        console.print(f"\n[cyan]{t('workspace_commands')}[/cyan]")
        console.print(
            f"  [bold]/workspace set <name>[/bold]      - {t('workspace_cmd_set')}"
        )
        console.print(f"  [bold]/workspace ls[/bold]              - {t('workspace_cmd_ls')}")
        console.print(
            f"  [bold]/workspace exec <cmd>[/bold]      - {t('workspace_cmd_exec')}"
        )

        if active_container:
            console.print(
                f"  [bold]/workspace copy <src> <dst>[/bold] - "
                f"{t('workspace_cmd_copy')}"
            )

        # List contents of the workspace
        self._list_workspace_contents(env_type, workspace_dir)

        return True

    def handle_set(self, args: Optional[List[str]] = None) -> bool:
        """Set the current workspace name"""
        if not args or len(args) != 1:
            console.print(f"[yellow]{t('workspace_usage_set')}[/yellow]")
            return False

        workspace_name = args[0]
        # Allow alphanumeric, underscores, hyphens
        if not all(c.isalnum() or c in ["_", "-"] for c in workspace_name):
            console.print(
                f"[red]{t('workspace_invalid_name')}[/red]"
            )
            return False

        # Import the necessary modules for setting environment variables
        # And for getting workspace dir consistently
        try:
            from cai.repl.commands.config import set_env_var
            from cai.tools.common import _get_workspace_dir as get_common_workspace_dir
            from cai.tools.common import _get_container_workspace_path as get_common_container_path

            # Set the environment variable
            if not set_env_var("CAI_WORKSPACE", workspace_name):
                console.print(f"[red]{t('workspace_set_failed')}[/red]")
                return False
        except ImportError:
            # Fallback if import fails
            os.environ["CAI_WORKSPACE"] = workspace_name

            # Define basic fallbacks for path functions if import failed
            def get_common_workspace_dir():
                base = os.getenv("CAI_WORKSPACE_DIR", ".")  # Default to current dir base
                name = os.getenv("CAI_WORKSPACE")
                if name:
                    return os.path.abspath(os.path.join(base, name))
                return os.path.abspath(base)  # Use base dir if no name

            def get_common_container_path():
                name = os.getenv("CAI_WORKSPACE")
                if name:
                    return f"/workspace/workspaces/{name}"
                return "/"  # Default container path

        # Get the new workspace directory using the common function
        new_workspace_dir = get_common_workspace_dir()

        # Create the directory if it doesn't exist on host
        try:  # Add try-except for robustness
            os.makedirs(new_workspace_dir, exist_ok=True)
        except OSError as e:
            console.print(f"[red]Error creating host directory {new_workspace_dir}: {e}[/red]")
            # Decide if this is fatal or just a warning

        # If container is active, also create the directory in the container
        active_container = os.getenv("CAI_ACTIVE_CONTAINER", "")
        if active_container:
            # Check if container is running
            check_process = subprocess.run(
                ["docker", "inspect", "--format", "{{.State.Running}}", active_container],
                capture_output=True,
                text=True,
                check=False,
            )

            if check_process.returncode == 0 and "true" in check_process.stdout.lower():
                # Get container workspace path using the common function
                container_workspace_path = get_common_container_path()
                try:
                    mkdir_cmd = [
                        "docker",
                        "exec",
                        active_container,
                        "mkdir",
                        "-p",
                        container_workspace_path,
                    ]
                    mkdir_result = subprocess.run(
                        mkdir_cmd, capture_output=True, text=True, check=False
                    )

                    if mkdir_result.returncode == 0:
                        console.print(
                            f"[dim]Created workspace directory in container: {container_workspace_path}[/dim]"
                        )
                    else:
                        console.print(
                            f"[yellow]Warning: Could not create workspace directory in container: {mkdir_result.stderr}[/yellow]"
                        )
                except Exception as e:
                    console.print(
                        f"[yellow]Warning: Failed to setup workspace in container: {str(e)}[/yellow]"
                    )

        # Use a different panel style to indicate success
        console.print(
            Panel(
                f"{t('workspace_changed_to')} [bold green]{workspace_name}[/bold green]\n"
                f"{t('workspace_new_dir')} [bold]{new_workspace_dir}[/bold]",
                title=t('workspace_updated_title'),
                border_style="green",
            )
        )

        return True

    def _get_workspace_dir(self) -> str:
        """Get the host workspace directory using the common utility.

        Returns:
            The host workspace directory path.
        """
        try:
            # Use the centralized function from common.py
            from cai.tools.common import _get_workspace_dir as get_common_workspace_dir

            return get_common_workspace_dir()
        except ImportError:
            # Provide a basic fallback if import fails, mirroring common.py logic
            # without 'cai_default'
            base_dir = os.getenv("CAI_WORKSPACE_DIR")
            workspace_name = os.getenv("CAI_WORKSPACE")

            if base_dir and workspace_name:
                # Basic validation
                if not all(c.isalnum() or c in ["_", "-"] for c in workspace_name):
                    print(
                        f"[yellow]Warning: Invalid CAI_WORKSPACE name '{workspace_name}' in fallback.[/yellow]"
                    )
                    # Fallback to base directory if name is invalid
                    return os.path.abspath(base_dir)
                target_dir = os.path.join(base_dir, workspace_name)
                return os.path.abspath(target_dir)
            elif base_dir:
                # If only base dir is set, use that
                return os.path.abspath(base_dir)
            else:
                # Default to current working directory if nothing else is set
                return os.getcwd()

    def _list_workspace_contents(self, env_type: str, workspace_dir: str) -> None:
        """List the contents of the workspace.

        Args:
            env_type: The environment type (container or host)
            workspace_dir: The workspace directory
        """
        console.print(f"\n[bold]{t('workspace_contents')}[/bold]")

        if env_type == "container":
            active_container = os.getenv("CAI_ACTIVE_CONTAINER", "")

            # For containers, use the workspace path provided
            # This should already be the correct path from handle_get

            # First ensure the workspace directory exists in the container
            try:
                mkdir_cmd = ["docker", "exec", active_container, "mkdir", "-p", workspace_dir]
                subprocess.run(mkdir_cmd, capture_output=True, text=True, check=False)

                # Now list the contents
                result = subprocess.run(
                    ["docker", "exec", active_container, "ls", "-la", workspace_dir],
                    capture_output=True,
                    text=True,
                    check=False,
                )

                if result.returncode == 0:
                    console.print(result.stdout)
                else:
                    console.print(
                        f"[yellow]{t('workspace_error_listing_container').format(error=result.stderr)}[/yellow]"
                    )
                    # Fallback to host
                    self._list_host_files(workspace_dir)
            except Exception as e:
                console.print(f"[yellow]{t('workspace_error_accessing_container').format(error=str(e))}[/yellow]")
                # Fallback to host
                self._list_host_files(workspace_dir)
        else:
            # List files in host
            self._list_host_files(workspace_dir)

    def _list_host_files(self, workspace_dir: str) -> None:
        """List files in the host workspace.

        Args:
            workspace_dir: The workspace directory
        """
        # Ensure the directory exists
        os.makedirs(workspace_dir, exist_ok=True)

        try:
            result = subprocess.run(
                ["ls", "-la", workspace_dir], capture_output=True, text=True, check=False
            )

            if result.returncode == 0:
                console.print(result.stdout)
            else:
                console.print(f"[yellow]{t('workspace_error_listing').format(error=result.stderr)}[/yellow]")
        except Exception as e:
            console.print(f"[yellow]Error: {str(e)}[/yellow]")

    def handle_ls_subcommand(self, args: Optional[List[str]] = None) -> bool:
        """Handle the ls subcommand.

        Args:
            args: Optional list of subcommand arguments

        Returns:
            True if the subcommand was handled successfully, False otherwise
        """
        # Get workspace info using common functions
        try:
            from cai.tools.common import _get_workspace_dir as get_common_workspace_dir
            from cai.tools.common import _get_container_workspace_path as get_common_container_path
        except ImportError:
            # Define basic fallbacks if import fails
            def get_common_workspace_dir():
                base = os.getenv("CAI_WORKSPACE_DIR", ".")
                name = os.getenv("CAI_WORKSPACE")
                if name:
                    return os.path.abspath(os.path.join(base, name))
                return os.path.abspath(base)

            def get_common_container_path():
                name = os.getenv("CAI_WORKSPACE")
                if name:
                    return f"/workspace/workspaces/{name}"
                return "/"

        host_workspace_dir = get_common_workspace_dir()
        active_container = os.getenv("CAI_ACTIVE_CONTAINER", "")

        # Execute command in the appropriate environment
        if active_container:
            # Use the container workspace path from common function
            container_workspace_path = get_common_container_path()

            # Determine the target path within the container
            target_path_in_container = container_workspace_path
            if args:
                # Ensure args[0] is treated as relative to the workspace
                target_path_in_container = os.path.join(container_workspace_path, args[0])

            # Ensure the base workspace directory exists in the container
            mkdir_cmd = [
                "docker",
                "exec",
                active_container,
                "mkdir",
                "-p",
                container_workspace_path,
            ]
            subprocess.run(mkdir_cmd, capture_output=True, text=True, check=False)

            # Try in container
            result = subprocess.run(
                [
                    "docker",
                    "exec",
                    active_container,
                    "ls",
                    "-la",
                    target_path_in_container,
                ],  # Use target path
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode == 0:
                console.print(result.stdout)
                return True

            # If failed, try on host
            console.print(f"[yellow]{t('workspace_failed_container_ls').format(error=result.stderr)}[/yellow]")
            console.print(f"[yellow]{t('workspace_fallback_host')}[/yellow]")

        # List on host
        # Determine target path on host relative to host workspace dir
        target_path_on_host = host_workspace_dir
        if args:
            # Ensure args[0] is treated as relative to the workspace
            target_path_on_host = os.path.join(host_workspace_dir, args[0])

        # Ensure the target directory exists on host before listing
        # Use os.path.dirname if target is potentially a file path
        dir_to_ensure = (
            os.path.dirname(target_path_on_host)
            if "." in os.path.basename(target_path_on_host)
            else target_path_on_host
        )
        try:
            os.makedirs(dir_to_ensure, exist_ok=True)
        except OSError as e:
            console.print(f"[red]Error creating directory {dir_to_ensure} on host: {e}[/red]")
            # Potentially return False or handle error appropriately

        try:
            result = subprocess.run(
                ["ls", "-la", target_path_on_host],  # Use target path
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode == 0:
                console.print(result.stdout)
                return True
            else:
                console.print(f"[red]Error listing files: {result.stderr}[/red]")
                return False
        except Exception as e:
            console.print(f"[red]Error: {str(e)}[/red]")
            return False

        return True

    def handle_exec_subcommand(self, args: Optional[List[str]] = None) -> bool:
        """Handle the exec subcommand.

        Args:
            args: Optional list of subcommand arguments

        Returns:
            True if the subcommand was handled successfully, False otherwise
        """
        if not args:
            console.print(f"[yellow]{t('workspace_please_specify_cmd')}[/yellow]")
            return False

        command = " ".join(args)
        # Get workspace info using common functions
        try:
            from cai.tools.common import _get_workspace_dir as get_common_workspace_dir
            from cai.tools.common import _get_container_workspace_path as get_common_container_path
        except ImportError:
            # Define basic fallbacks if import fails
            def get_common_workspace_dir():
                base = os.getenv("CAI_WORKSPACE_DIR", ".")
                name = os.getenv("CAI_WORKSPACE")
                if name:
                    return os.path.abspath(os.path.join(base, name))
                return os.path.abspath(base)

            def get_common_container_path():
                name = os.getenv("CAI_WORKSPACE")
                if name:
                    return f"/workspace/workspaces/{name}"
                return "/"

        host_workspace_dir = get_common_workspace_dir()
        active_container = os.getenv("CAI_ACTIVE_CONTAINER", "")

        # Execute in container if active
        if active_container:
            try:
                # Use the container workspace path from common function
                container_workspace_path = get_common_container_path()

                # First ensure the workspace directory exists in the container
                mkdir_cmd = [
                    "docker",
                    "exec",
                    active_container,
                    "mkdir",
                    "-p",
                    container_workspace_path,
                ]
                subprocess.run(mkdir_cmd, capture_output=True, text=True, check=False)

                # Execute the command in the container's workspace directory
                result = subprocess.run(
                    [
                        "docker",
                        "exec",
                        "-w",
                        container_workspace_path,
                        active_container,
                        "sh",
                        "-c",
                        command,
                    ],
                    capture_output=True,
                    text=True,
                    check=False,
                )

                console.print(f"[dim]$ {command}[/dim]")
                if result.stdout:
                    console.print(result.stdout)

                if result.stderr:
                    console.print(f"[yellow]{result.stderr}[/yellow]")

                if result.returncode != 0:
                    console.print(f"[yellow]{t('workspace_cmd_failed_container')}[/yellow]")
                    return self._exec_on_host(
                        command, host_workspace_dir
                    )  # Pass host_workspace_dir

                return True
            except Exception as e:
                console.print(f"[yellow]{t('workspace_error_exec_container').format(error=str(e))}[/yellow]")
                console.print(f"[yellow]{t('workspace_fallback_host_exec')}[/yellow]")

        # Execute on host
        return self._exec_on_host(command, host_workspace_dir)  # Pass host_workspace_dir

    def _exec_on_host(self, command: str, workspace_dir: str) -> bool:
        """Execute a command on the host.

        Args:
            command: The command to execute
            workspace_dir: The workspace directory

        Returns:
            True if the command was executed successfully, False otherwise
        """
        # Ensure the directory exists
        os.makedirs(workspace_dir, exist_ok=True)

        try:
            result = subprocess.run(
                command,
                shell=True,  # nosec B602
                capture_output=True,
                text=True,
                check=False,
                cwd=workspace_dir,
            )

            console.print(f"[dim]$ {command}[/dim]")
            if result.stdout:
                console.print(result.stdout)

            if result.stderr:
                console.print(f"[yellow]{result.stderr}[/yellow]")

            return result.returncode == 0
        except Exception as e:
            console.print(f"[red]{t('workspace_error_exec').format(error=str(e))}[/red]")
            return False

    def handle_copy_subcommand(self, args: Optional[List[str]] = None) -> bool:
        """Handle the copy subcommand.

        Args:
            args: Optional list of subcommand arguments

        Returns:
            True if the subcommand was handled successfully, False otherwise
        """
        if not args or len(args) < 2:
            console.print(f"[yellow]{t('workspace_please_specify_copy')}[/yellow]")
            console.print(t('workspace_usage_copy'))
            return False

        active_container = os.getenv("CAI_ACTIVE_CONTAINER", "")
        if not active_container:
            console.print(f"[yellow]{t('workspace_no_active_container')}[/yellow]")
            return False

        source = args[0]
        destination = args[1]

        # Check if copying from container to host or vice versa
        if source.startswith("container:"):
            # Copy from container to host
            container_path = source[10:]  # Remove "container:" prefix
            host_path = destination

            if not container_path.startswith("/"):
                container_path = f"/workspace/{container_path}"

            try:
                result = subprocess.run(
                    ["docker", "cp", f"{active_container}:{container_path}", host_path],
                    capture_output=True,
                    text=True,
                    check=False,
                )

                if result.returncode == 0:
                    console.print(
                        f"[green]{t('workspace_copied_from_container').format(src=container_path, dst=host_path)}[/green]"
                    )
                    return True
                else:
                    console.print(f"[red]{t('workspace_error_copy_from').format(error=result.stderr)}[/red]")
                    return False
            except Exception as e:
                console.print(f"[red]Error: {str(e)}[/red]")
                return False
        elif destination.startswith("container:"):
            # Copy from host to container
            host_path = source
            container_path = destination[10:]  # Remove "container:" prefix

            if not container_path.startswith("/"):
                container_path = f"/workspace/{container_path}"

            try:
                result = subprocess.run(
                    ["docker", "cp", host_path, f"{active_container}:{container_path}"],
                    capture_output=True,
                    text=True,
                    check=False,
                )

                if result.returncode == 0:
                    console.print(
                        f"[green]{t('workspace_copied_to_container').format(src=host_path, dst=container_path)}[/green]"
                    )
                    return True
                else:
                    console.print(f"[red]{t('workspace_error_copy_to').format(error=result.stderr)}[/red]")
                    return False
            except Exception as e:
                console.print(f"[red]Error: {str(e)}[/red]")
                return False
        else:
            # Ambiguous copy - show help
            console.print(
                f"[yellow]{t('workspace_ambiguous_copy')}[/yellow]"
            )
            console.print(f"{t('workspace_copy_examples')}")
            console.print(f"  {t('workspace_copy_example_host_to')}")
            console.print(f"  {t('workspace_copy_example_container_to')}")
            return False


# Register the commands
register_command(WorkspaceCommand())
