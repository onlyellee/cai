"""
Platform command for CAI REPL.
This module provides commands for interacting with platform-specific features.
"""

from typing import List, Optional
from rich.console import Console  # pylint: disable=import-error
from rich.panel import Panel  # pylint: disable=import-error

from cai import is_caiextensions_platform_available
from cai.i18n import t
from cai.repl.commands.base import Command, register_command

console = Console()


class PlatformCommand(Command):
    """Command for interacting with platform-specific features."""

    def __init__(self):
        """Initialize the platform command."""
        super().__init__(
            name="/platform", description=t('platform_description'), aliases=["/p"]
        )

        # Add subcommands dynamically based on available platforms
        if is_caiextensions_platform_available():
            from caiextensions.platform.base import platform_manager  # pylint: disable=import-error,import-outside-toplevel,unused-import,line-too-long,no-name-in-module # noqa: E501

            # Add list subcommand
            self.add_subcommand("list", t('platform_sub_list'), self.handle_list)

            # Add VPN status command
            self.add_subcommand(
                "vpn-status", t('platform_sub_vpn_status'), self.handle_vpn_status
            )

            # Add keep-vpn command
            self.add_subcommand(
                "keep-vpn", t('platform_sub_keep_vpn'), self.handle_keep_vpn
            )

            # Add platform-specific subcommands
            platforms = platform_manager.list_platforms()
            for platform in platforms:
                platform_cmds = platform_manager.get_platform(platform).get_commands()
                for cmd in platform_cmds:
                    # Add platform-specific commands as subcommands
                    self.add_subcommand(
                        f"{platform}:{cmd}",
                        t('platform_sub_platform_cmd').format(cmd=cmd, platform=platform),
                        lambda args, p=platform, c=cmd: self.handle_platform_command(
                            [p, c] + (args or [])
                        ),
                    )

    def handle(self, args: Optional[List[str]] = None) -> bool:
        """Handle the platform command.

        Args:
            args: Optional list of command arguments

        Returns:
            True if the command was handled successfully, False otherwise
        """
        if not is_caiextensions_platform_available():
            console.print(f"[red]{t('platform_not_available')}[/red]")
            return False

        return self.handle_platform_command(args)

    def handle_list(self, args: Optional[List[str]] = None) -> bool:  # pylint: disable=unused-argument # noqa: E501
        """Handle /platform list command."""
        if not is_caiextensions_platform_available():
            console.print(f"[red]{t('platform_not_available')}[/red]")
            return False

        from caiextensions.platform.base import platform_manager  # pylint: disable=import-error,import-outside-toplevel,unused-import,line-too-long,no-name-in-module # noqa: E501

        platforms = platform_manager.list_platforms()

        console.print(
            Panel(
                "\n".join(f"[green]{p}[/green]" for p in platforms),
                title=t('platform_available_title'),
                border_style="blue",
            )
        )
        return True

    def handle_platform_command(self, args: Optional[List[str]] = None) -> bool:
        """Handle platform specific commands."""
        if not is_caiextensions_platform_available():
            console.print(f"[red]{t('platform_not_available')}[/red]")
            return False

        from caiextensions.platform.base import platform_manager  # pylint: disable=import-error,import-outside-toplevel,unused-import,line-too-long,no-name-in-module # noqa: E501

        if not args:
            # Show available platforms
            platforms = platform_manager.list_platforms()
            console.print(
                Panel(
                    "\n".join(f"[green]{p}[/green]" for p in platforms),
                    title=t('platform_available_title'),
                    border_style="blue",
                )
            )
            return True

        platform_name = args[0].lower()
        platform = platform_manager.get_platform(platform_name)

        if not platform:
            console.print(f"[red]{t('platform_unknown').format(name=platform_name)}[/red]")
            return False

        if len(args) == 1:
            # Show platform help
            console.print(
                Panel(
                    platform.get_help(), title=t('platform_help_title').format(name=platform_name.upper()), border_style="blue"
                )
            )
            return True

        # Pass the command to the platform (without the platform name)
        platform.handle_command(args[1:])
        return True

    def handle_vpn_status(self, args: Optional[List[str]] = None) -> bool:  # pylint: disable=unused-argument # noqa: E501
        """
        Check the status of the VPN connection.

        Args:
            args: Optional list of command arguments (not used)

        Returns:
            True if the command was handled successfully, False otherwise
        """
        if not is_caiextensions_platform_available():
            console.print(f"[red]{t('platform_not_available')}[/red]")
            return False

        try:
            from caiextensions.platform.htb.cli import (  # pylint: disable=import-error,import-outside-toplevel,line-too-long # noqa: E501
                is_vpn_connected,
                get_vpn_ip,
                vpn_active,
            )

            # Check VPN connection status
            if is_vpn_connected():
                status = f"[green]{t('platform_vpn_connected')}[/green]"
            else:
                status = f"[red]{t('platform_vpn_disconnected')}[/red]"

            # Check if VPN is set to persistent mode
            if vpn_active:
                persistent = f"[green]{t('platform_vpn_yes')}[/green]"
            else:
                persistent = f"[red]{t('platform_vpn_no')}[/red]"
            ip = get_vpn_ip()

            console.print(
                Panel(
                    f"{t('platform_vpn_status_label')} {status}\n"
                    f"{t('platform_vpn_persistent_label')} {persistent}\n"
                    f"{t('platform_vpn_ip_label')} {ip}",
                    title=t('platform_vpn_status_title'),
                    border_style="blue",
                )
            )
            return True
        except ImportError:
            console.print(f"[red]{t('platform_htb_not_available')}[/red]")
            return False

    def handle_keep_vpn(self, args: Optional[List[str]] = None) -> bool:  # pylint: disable=unused-argument # noqa: E501
        """
        Set the VPN to remain active even when the program is interrupted.

        Args:
            args: Optional list of command arguments (not used)

        Returns:
            True if the command was handled successfully, False otherwise
        """
        if not is_caiextensions_platform_available():
            console.print(f"[red]{t('platform_not_available')}[/red]")
            return False

        try:
            from caiextensions.platform.htb.cli import (  # pylint: disable=import-error,import-outside-toplevel,line-too-long # noqa: E501
                is_vpn_connected,
            )

            if not is_vpn_connected():
                console.print(f"[red]{t('platform_no_vpn')}[/red]")
                console.print(
                    f"[yellow]{t('platform_connect_first')}[/yellow]"
                )
                return False

            # Set the VPN to persistent mode
            import caiextensions.platform.htb.cli as htb_cli  # pylint: disable=import-error,import-outside-toplevel,line-too-long # noqa: E501

            htb_cli.vpn_active = True

            console.print(f"[green]{t('platform_vpn_persistent_set')}[/green]")
            console.print(f"[yellow]{t('platform_vpn_persistent_note')}[/yellow]")
            return True
        except ImportError:
            console.print(f"[red]{t('platform_htb_not_available')}[/red]")
            return False


# Register the command
if is_caiextensions_platform_available():
    register_command(PlatformCommand())
