"""
Queue command for managing prompt queue
"""

from typing import List, Optional
from rich.table import Table
from rich.panel import Panel
from datetime import datetime
import os

from .base import Command, register_command, console
from cai.i18n import t

# Try to import the TUI prompt queue if available
try:
    if os.getenv("CAI_TUI_MODE") == "true":
        from cai.tui.core.prompt_queue import PROMPT_QUEUE as TUI_PROMPT_QUEUE
        from cai.tui.core.terminal_queue import TERMINAL_QUEUE_MANAGER
    else:
        TUI_PROMPT_QUEUE = None
        TERMINAL_QUEUE_MANAGER = None
except ImportError:
    TUI_PROMPT_QUEUE = None
    TERMINAL_QUEUE_MANAGER = None

# Fallback queue for non-TUI mode
FALLBACK_QUEUE = []


class QueueCommand(Command):
    """Manage the prompt queue"""

    def __init__(self):
        super().__init__(
            name="queue",
            aliases=["q"],
            description=t('queue_desc')
        )

    def handle(self, args: Optional[List[str]] = None) -> bool:
        """Handle queue command"""
        # Check if we're in TUI mode with terminal queues
        if TERMINAL_QUEUE_MANAGER and os.getenv("CAI_TUI_MODE") == "true":
            return self._handle_terminal_queues(args)
        
        if not args:
            return self._show_queue()
        
        action = args[0].lower()
        
        if action in ["show", "list", "ls"]:
            return self._show_queue()
        elif action == "add":
            if len(args) < 2:
                error_panel = Panel(
                    f"[bold red]❌ {t('queue_error_no_prompt')}[/bold red]\n\n"
                    f"[dim]{t('queue_add_usage')}[/dim]",
                    border_style="red"
                )
                console.print(error_panel)
                return False
            prompt = " ".join(args[1:])
            return self._add_to_queue(prompt)
        elif action == "remove" or action == "rm":
            if len(args) < 2:
                error_panel = Panel(
                    f"[bold red]❌ {t('queue_error_no_index')}[/bold red]\n\n"
                    f"[dim]{t('queue_remove_usage')}[/dim]",
                    border_style="red"
                )
                console.print(error_panel)
                return False
            try:
                index = int(args[1]) - 1  # Convert to 0-based index
                return self._remove_from_queue(index)
            except ValueError:
                error_panel = Panel(
                    f"[bold red]❌ {t('queue_error_invalid_index')}[/bold red]\n\n"
                    f"[dim]{t('queue_provide_valid_number')}[/dim]",
                    border_style="red"
                )
                console.print(error_panel)
                return False
        elif action == "clear":
            return self._clear_queue()
        elif action == "next":
            return self._get_next()
        elif action == "load":
            if len(args) < 2:
                # Try to load from environment variable
                queue_file = os.getenv("CAI_QUEUE_FILE")
                if queue_file:
                    load_queue_from_file(os.path.expanduser(queue_file))
                    return True
                else:
                    error_panel = Panel(
                        f"[bold red]❌ {t('queue_error_no_file')}[/bold red]\n\n"
                        f"[dim]{t('queue_load_usage')}[/dim]\n"
                        f"[dim]{t('queue_load_env_hint')}[/dim]",
                        border_style="red"
                    )
                    console.print(error_panel)
                    return False
            file_path = " ".join(args[1:])
            load_queue_from_file(os.path.expanduser(file_path))
            return True
        else:
            error_panel = Panel(
                f"[bold red]❌ {t('queue_unknown_action', action=action)}[/bold red]\n\n"
                f"[dim]{t('queue_use_help')}[/dim]",
                border_style="red",
                padding=(1, 2)
            )
            console.print(error_panel)
            self._show_help()
            return False

    def _show_queue(self) -> bool:
        """Show the current queue"""
        queue_items = self._get_queue_items()
        
        if not queue_items:
            # Empty queue with styled panel
            empty_panel = Panel(
                f"[dim italic]{t('queue_no_prompts')}[/dim italic]",
                title=f"[bold cyan]📋 {t('queue_title')}[/bold cyan]",
                border_style="cyan",
                padding=(1, 2)
            )
            console.print(empty_panel)
            return True
        
        # Create a fancy table with modern styling
        table = Table(
            title=f"[bold cyan]📋 {t('queue_title')}[/bold cyan]",
            show_header=True,
            header_style="bold bright_cyan on gray23",
            border_style="bright_blue",
            title_style="bold bright_cyan",
            caption=f"[dim]{t('queue_total_items', count=len(queue_items))}[/dim]",
            caption_style="dim cyan",
            row_styles=["none", "gray23"],
            pad_edge=True,
            box=None
        )
        
        table.add_column("🔢", style="bold bright_green", width=4, justify="center")
        table.add_column(f"💬 {t('queue_col_prompt')}", style="white", overflow="ellipsis")
        table.add_column(f"⏰ {t('queue_col_time')}", style="bright_yellow", width=12)
        table.add_column(f"⚡ {t('queue_col_priority')}", style="bright_magenta", width=10, justify="center")
        
        for i, item in enumerate(queue_items, 1):
            prompt_text = item.get("prompt", "")
            
            # Add syntax highlighting for commands
            if prompt_text.startswith("/"):
                prompt_display = f"[bold green]{prompt_text}[/bold green]"
            elif prompt_text.startswith("$"):
                prompt_display = f"[bold yellow]{prompt_text}[/bold yellow]"
            else:
                prompt_display = f"[white]{prompt_text}[/white]"
            
            # Format timestamp
            timestamp = item.get("timestamp", datetime.now())
            time_str = timestamp.strftime("%H:%M:%S")
            
            # Format priority with icons
            priority = item.get("priority", 0)
            if priority > 5:
                priority_display = f"[bold red]🔥 {priority}[/bold red]"
            elif priority > 0:
                priority_display = f"[yellow]⚡ {priority}[/yellow]"
            else:
                priority_display = f"[dim]▪ {priority}[/dim]"
            
            table.add_row(
                f"[bold bright_green]{i}[/bold bright_green]",
                prompt_display,
                f"[bright_yellow]{time_str}[/bright_yellow]",
                priority_display
            )
        
        # Wrap table in a panel for better visual
        queue_panel = Panel(
            table,
            border_style="bright_cyan",
            padding=(0, 1)
        )
        
        console.print(queue_panel)
        
        # Add helpful tip
        console.print(
            f"\n[dim cyan]💡 {t('queue_tip')}[/dim cyan]"
        )
        
        return True
    
    def _get_queue_items(self) -> List[dict]:
        """Get queue items from the appropriate queue"""
        # Try to get the TUI queue dynamically
        if os.getenv("CAI_TUI_MODE") == "true":
            try:
                from cai.tui.core.prompt_queue import PROMPT_QUEUE as TUI_QUEUE
                # Get from TUI queue
                items = []
                for queued_prompt in TUI_QUEUE._queue:
                    items.append({
                        "prompt": queued_prompt.prompt,
                        "timestamp": queued_prompt.timestamp,
                        "priority": queued_prompt.priority
                    })
                return items
            except ImportError:
                pass
        
        # Fallback to module-level queue
        if TUI_PROMPT_QUEUE:
            # Get from TUI queue
            items = []
            for queued_prompt in TUI_PROMPT_QUEUE._queue:
                items.append({
                    "prompt": queued_prompt.prompt,
                    "timestamp": queued_prompt.timestamp,
                    "priority": queued_prompt.priority
            })
            return items
        else:
            # Use fallback queue
            return FALLBACK_QUEUE

    def _add_to_queue(self, prompt: str) -> bool:
        """Add a prompt to the queue"""
        queue_len = 0
        
        # Try to get the TUI queue dynamically
        if os.getenv("CAI_TUI_MODE") == "true":
            try:
                from cai.tui.core.prompt_queue import PROMPT_QUEUE as TUI_QUEUE
                # Add to TUI queue asynchronously
                import asyncio
                asyncio.create_task(TUI_QUEUE.add_prompt(prompt))
                queue_len = len(TUI_QUEUE._queue) + 1
            except ImportError:
                pass
        
        # Fallback to module-level queue if needed
        if queue_len == 0:
            if TUI_PROMPT_QUEUE:
                # Add to TUI queue asynchronously
                import asyncio
                asyncio.create_task(TUI_PROMPT_QUEUE.add_prompt(prompt))
                queue_len = len(TUI_PROMPT_QUEUE._queue) + 1
            else:
                # Add to fallback queue
                item = {
                    "prompt": prompt,
                    "timestamp": datetime.now(),
                    "priority": 0
                }
                FALLBACK_QUEUE.append(item)
                queue_len = len(FALLBACK_QUEUE)
        
        # Success message with icon
        success_panel = Panel(
            f"[bold green]✅ {t('queue_added_success')}[/bold green]\n\n"
            f"[white]{t('queue_position', pos=queue_len)}[/white]\n"
            f"[dim]{t('queue_col_prompt')}: {prompt[:50]}{'...' if len(prompt) > 50 else ''}[/dim]",
            title=f"[bold green]{t('queue_updated_title')}[/bold green]",
            border_style="green",
            padding=(1, 2)
        )
        console.print(success_panel)
        return True

    def _remove_from_queue(self, index: int) -> bool:
        """Remove a prompt from the queue"""
        queue_items = self._get_queue_items()
        
        if index < 0 or index >= len(queue_items):
            error_panel = Panel(
                f"[bold red]❌ {t('queue_error_out_of_range')}[/bold red]\n\n"
                f"[dim]{t('queue_valid_range', max=len(queue_items))}[/dim]",
                border_style="red"
            )
            console.print(error_panel)
            return False
        
        prompt_text = ""
        
        # Try to get the TUI queue dynamically
        if os.getenv("CAI_TUI_MODE") == "true":
            try:
                from cai.tui.core.prompt_queue import PROMPT_QUEUE as TUI_QUEUE
                # Remove from TUI queue
                if index < len(TUI_QUEUE._queue):
                    removed = TUI_QUEUE._queue.pop(index)
                    prompt_text = removed.prompt[:50]
                else:
                    prompt_text = "Unknown"
            except ImportError:
                pass
        
        # Fallback to module-level queue if needed
        if not prompt_text:
            if TUI_PROMPT_QUEUE:
                # Remove from TUI queue
                if index < len(TUI_PROMPT_QUEUE._queue):
                    removed = TUI_PROMPT_QUEUE._queue.pop(index)
                    prompt_text = removed.prompt[:50]
                else:
                    prompt_text = "Unknown"
            else:
                # Remove from fallback queue
                removed = FALLBACK_QUEUE.pop(index)
                prompt_text = removed["prompt"][:50]
        
        # Removal success message
        remove_panel = Panel(
            f"[bold yellow]🗑️  {t('queue_item_removed')}[/bold yellow]\n\n"
            f"[dim]{t('queue_removed_label', prompt=prompt_text)}{'...' if len(prompt_text) == 50 else ''}[/dim]",
            border_style="yellow",
            padding=(1, 2)
        )
        console.print(remove_panel)
        return True

    def _clear_queue(self) -> bool:
        """Clear the entire queue"""
        count = 0
        
        # Try to get the TUI queue dynamically
        if os.getenv("CAI_TUI_MODE") == "true":
            try:
                from cai.tui.core.prompt_queue import PROMPT_QUEUE as TUI_QUEUE
                count = len(TUI_QUEUE._queue)
                TUI_QUEUE._queue.clear()
            except ImportError:
                pass
        
        # Fallback to module-level queue if needed
        if count == 0:
            if TUI_PROMPT_QUEUE:
                count = len(TUI_PROMPT_QUEUE._queue)
                TUI_PROMPT_QUEUE._queue.clear()
            else:
                count = len(FALLBACK_QUEUE)
                FALLBACK_QUEUE.clear()
        
        # Clear success message
        clear_panel = Panel(
            f"[bold red]🧹 {t('queue_cleared')}[/bold red]\n\n"
            f"[white]{t('queue_cleared_count', count=count)}[/white]",
            border_style="red",
            padding=(1, 2)
        )
        console.print(clear_panel)
        return True

    def _get_next(self) -> bool:
        """Get the next prompt from the queue"""
        queue_items = self._get_queue_items()
        
        if not queue_items:
            # Empty queue message
            empty_panel = Panel(
                f"[dim italic]{t('queue_no_prompts')}[/dim italic]",
                title=f"[bold cyan]📝 {t('queue_status_title')}[/bold cyan]",
                border_style="cyan",
                padding=(1, 2)
            )
            console.print(empty_panel)
            return True
        
        next_item = queue_items[0]
        
        # Format the next item display
        timestamp = next_item.get("timestamp", datetime.now())
        time_str = timestamp.strftime("%H:%M:%S")
        priority = next_item.get("priority", 0)
        
        # Create styled panel for next item
        content = f"[bold cyan]👉 {t('queue_next_in_queue')}[/bold cyan]\n\n"
        content += f"[bold white]{next_item['prompt']}[/bold white]\n\n"
        content += f"[dim]{t('queue_added_at', time=time_str, priority=priority)}[/dim]"

        next_panel = Panel(
            content,
            title=f"[bold green]⏭️ {t('queue_next_prompt_title')}[/bold green]",
            border_style="green",
            padding=(1, 2)
        )
        console.print(next_panel)
        return True

    def _show_help(self) -> None:
        """Show help for the queue command"""
        # Create a rich help panel
        help_table = Table(
            show_header=True,
            header_style="bold bright_cyan",
            border_style="cyan",
            box=None,
            padding=(0, 1)
        )
        
        help_table.add_column(f"🎯 {t('queue_col_command')}", style="bold green")
        help_table.add_column(f"📖 {t('queue_col_description')}", style="white")
        help_table.add_column(f"💡 {t('queue_col_example')}", style="dim")

        commands = [
            ("/queue", t('queue_help_show'), "/queue"),
            ("/queue show", t('queue_help_show'), "/queue show"),
            ("/queue add <prompt>", t('queue_help_add'), "/queue add tell me a joke"),
            ("/queue remove <index>", t('queue_help_remove'), "/queue remove 2"),
            ("/queue clear", t('queue_help_clear'), "/queue clear"),
            ("/queue next", t('queue_help_next'), "/queue next"),
            ("/queue load <file>", t('queue_help_load'), "/queue load prompts.txt")
        ]
        
        for cmd, desc, example in commands:
            help_table.add_row(
                f"[bold green]{cmd}[/bold green]",
                desc,
                f"[dim]{example}[/dim]"
            )
        
        help_panel = Panel(
            help_table,
            title=f"[bold cyan]📚 {t('queue_help_title')}[/bold cyan]",
            subtitle=f"[dim]{t('queue_help_alias')}[/dim]",
            border_style="cyan",
            padding=(1, 1)
        )
        
        console.print(help_panel)
    
    def _handle_terminal_queues(self, args: Optional[List[str]] = None) -> bool:
        """Handle per-terminal queue commands"""
        if not args or args[0].lower() in ["show", "list", "ls", "status"]:
            return self._show_terminal_queues()
        
        action = args[0].lower()
        
        if action == "clear":
            if len(args) > 1:
                try:
                    terminal_num = int(args[1])
                    return self._clear_terminal_queue(terminal_num)
                except ValueError:
                    error_panel = Panel(
                        f"[bold red]❌ {t('queue_terminal_invalid_num')}[/bold red]",
                        border_style="red"
                    )
                    console.print(error_panel)
                    return False
            else:
                return self._clear_all_terminal_queues()
        elif action == "help":
            self._show_terminal_queue_help()
            return True
        else:
            # For other actions, fall back to regular queue handling
            return self._show_queue()
    
    def _show_terminal_queues(self) -> bool:
        """Show status of all terminal queues"""
        all_status = TERMINAL_QUEUE_MANAGER.get_all_queues_status()
        
        if not all_status:
            success_panel = Panel(
                f"[green]{t('queue_terminal_no_queues')}[/green]",
                title=f"[bold cyan]{t('queue_terminal_status_title')}[/bold cyan]",
                border_style="cyan"
            )
            console.print(success_panel)
            return True
        
        # Create main table
        table = Table(
            title=f"[bold cyan]📋 {t('queue_terminal_status_title')}[/bold cyan]",
            show_header=True,
            header_style="bold bright_cyan on gray23",
            border_style="bright_blue",
            row_styles=["none", "gray23"],
            box=None
        )
        
        table.add_column(t('queue_terminal_col_terminal'), style="bold green", width=10)
        table.add_column(t('queue_terminal_col_status'), style="yellow", width=12)
        table.add_column(t('queue_terminal_col_current'), style="white", overflow="ellipsis")
        table.add_column(t('queue_terminal_col_queued'), style="cyan", width=8, justify="center")
        
        for terminal_num in sorted(all_status.keys()):
            status = all_status[terminal_num]
            
            # Status icon and text
            if status["processing"]:
                status_text = f"[yellow]⚡ {t('queue_terminal_processing')}[/yellow]"
                current_text = status["current_prompt"][:40] + "..." if status["current_prompt"] and len(status["current_prompt"]) > 40 else status["current_prompt"] or ""
            else:
                status_text = f"[green]✓ {t('queue_terminal_idle')}[/green]"
                current_text = "[dim]-[/dim]"
            
            queue_len = status["queue_length"]
            queue_text = f"[cyan]{queue_len}[/cyan]" if queue_len > 0 else "[dim]0[/dim]"
            
            table.add_row(
                f"[bold green]T{terminal_num}[/bold green]",
                status_text,
                current_text,
                queue_text
            )
        
        console.print(table)
        console.print()
        
        # Show detailed queue items if any
        has_queued_items = False
        for terminal_num in sorted(all_status.keys()):
            status = all_status[terminal_num]
            if status["prompts"]:
                has_queued_items = True
                console.print(f"[bold]{t('queue_terminal_queue_label', num=terminal_num)}[/bold]")
                for i, prompt_info in enumerate(status["prompts"], 1):
                    console.print(f"  {i}. {prompt_info['prompt']} [dim](priority: {prompt_info['priority']})[/dim]")
                console.print()
        
        if not has_queued_items:
            console.print(f"[dim]{t('queue_terminal_no_prompts')}[/dim]")

        console.print(f"[dim cyan]💡 {t('queue_terminal_tip')}[/dim cyan]")
        return True
    
    def _clear_terminal_queue(self, terminal_num: int) -> bool:
        """Clear queue for specific terminal"""
        count = TERMINAL_QUEUE_MANAGER.clear_terminal_queue(terminal_num)
        if count > 0:
            success_panel = Panel(
                f"[green]✅ {t('queue_terminal_cleared', count=count, num=terminal_num)}[/green]",
                border_style="green"
            )
        else:
            success_panel = Panel(
                f"[yellow]{t('queue_terminal_already_empty', num=terminal_num)}[/yellow]",
                border_style="yellow"
            )
        console.print(success_panel)
        return True

    def _clear_all_terminal_queues(self) -> bool:
        """Clear all terminal queues"""
        count = TERMINAL_QUEUE_MANAGER.clear_all_queues()
        if count > 0:
            success_panel = Panel(
                f"[green]✅ {t('queue_terminal_all_cleared', count=count)}[/green]",
                border_style="green"
            )
        else:
            success_panel = Panel(
                f"[yellow]{t('queue_terminal_all_already_empty')}[/yellow]",
                border_style="yellow"
            )
        console.print(success_panel)
        return True
    
    def _show_terminal_queue_help(self) -> None:
        """Show help for terminal queue commands"""
        help_table = Table(
            show_header=True,
            header_style="bold bright_cyan",
            border_style="cyan",
            box=None
        )
        
        help_table.add_column(f"🎯 {t('queue_col_command')}", style="bold green")
        help_table.add_column(f"📖 {t('queue_col_description')}", style="white")

        commands = [
            ("/queue", t('queue_terminal_help_show')),
            ("/queue status", t('queue_terminal_help_show')),
            ("/queue clear", t('queue_terminal_help_clear_all')),
            ("/queue clear <num>", t('queue_terminal_help_clear_num')),
            ("/queue help", t('queue_terminal_help_help'))
        ]

        for cmd, desc in commands:
            help_table.add_row(cmd, desc)

        help_panel = Panel(
            help_table,
            title=f"[bold cyan]📚 {t('queue_terminal_help_title')}[/bold cyan]",
            subtitle=f"[dim]{t('queue_terminal_help_subtitle')}[/dim]",
            border_style="cyan"
        )
        
        console.print(help_panel)
        console.print(f"\n[dim]{t('queue_terminal_independent')}[/dim]")


# Register the command
register_command(QueueCommand())


def get_queue():
    """Get the current queue"""
    # Try to get the TUI queue dynamically
    if os.getenv("CAI_TUI_MODE") == "true":
        try:
            from cai.tui.core.prompt_queue import PROMPT_QUEUE as TUI_QUEUE
            # Return TUI queue items as dict format
            items = []
            for queued_prompt in TUI_QUEUE._queue:
                items.append({
                    "prompt": queued_prompt.prompt,
                    "timestamp": queued_prompt.timestamp,
                    "priority": queued_prompt.priority
                })
            return items
        except ImportError:
            pass
    
    # Fallback to module-level queue
    if TUI_PROMPT_QUEUE:
        # Return TUI queue items as dict format
        items = []
        for queued_prompt in TUI_PROMPT_QUEUE._queue:
            items.append({
                "prompt": queued_prompt.prompt,
                "timestamp": queued_prompt.timestamp,
                "priority": queued_prompt.priority
            })
        return items
    else:
        return FALLBACK_QUEUE


def add_to_queue(prompt: str):
    """Add a prompt to the queue"""
    # Try to get the TUI queue dynamically
    if os.getenv("CAI_TUI_MODE") == "true":
        try:
            from cai.tui.core.prompt_queue import PROMPT_QUEUE as TUI_QUEUE
            # Add to TUI queue (synchronously for compatibility)
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(TUI_QUEUE.add_prompt(prompt))
                else:
                    loop.run_until_complete(TUI_QUEUE.add_prompt(prompt))
            except RuntimeError:
                # Fallback if no event loop
                pass
            return len(TUI_QUEUE._queue)
        except ImportError:
            pass
    
    # Fallback to module-level queue
    if TUI_PROMPT_QUEUE:
        # Add to TUI queue (synchronously for compatibility)
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(TUI_PROMPT_QUEUE.add_prompt(prompt))
            else:
                loop.run_until_complete(TUI_PROMPT_QUEUE.add_prompt(prompt))
        except RuntimeError:
            # Fallback if no event loop
            pass
        return len(TUI_PROMPT_QUEUE._queue)
    else:
        item = {
            "prompt": prompt,
            "timestamp": datetime.now(),
            "priority": 0
        }
        FALLBACK_QUEUE.append(item)
        return len(FALLBACK_QUEUE)


def get_next_prompt():
    """Get and remove the next prompt from the queue"""
    # Check TUI mode queue
    if os.getenv("CAI_TUI_MODE") == "true":
        try:
            from cai.tui.core.prompt_queue import PROMPT_QUEUE as TUI_QUEUE
            if TUI_QUEUE._queue:
                queued_item = TUI_QUEUE._queue.pop(0)
                return queued_item.prompt  # Return just the prompt string
        except ImportError:
            pass
    
    # Check module-level TUI queue
    if TUI_PROMPT_QUEUE and TUI_PROMPT_QUEUE._queue:
        queued_item = TUI_PROMPT_QUEUE._queue.pop(0)
        return queued_item.prompt if hasattr(queued_item, 'prompt') else queued_item
    elif FALLBACK_QUEUE:
        item = FALLBACK_QUEUE.pop(0)
        return item.get("prompt", "") if isinstance(item, dict) else item
    return None


def is_queue_empty():
    """Check if the queue is empty"""
    if TUI_PROMPT_QUEUE:
        return len(TUI_PROMPT_QUEUE._queue) == 0
    else:
        return len(FALLBACK_QUEUE) == 0


def load_queue_from_file(file_path: str) -> int:
    """Load prompts from a text file into the queue
    
    Args:
        file_path: Path to the text file containing prompts (one per line)
        
    Returns:
        Number of prompts loaded
    """
    loaded_count = 0
    
    try:
        prompts_to_load = []
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                # Strip whitespace and skip empty lines
                prompt = line.strip()
                if prompt and not prompt.startswith('#'):  # Skip comments
                    prompts_to_load.append(prompt)
                    
        # Add all prompts to the appropriate queue
        if os.getenv("CAI_TUI_MODE") == "true":
            try:
                from cai.tui.core.prompt_queue import PROMPT_QUEUE as TUI_QUEUE, QueuedPrompt
                # Add directly to the TUI queue without async
                for prompt in prompts_to_load:
                    queued_prompt = QueuedPrompt(
                        prompt=prompt,
                        terminal_number=None,
                        priority=0
                    )
                    TUI_QUEUE._queue.append(queued_prompt)
                    loaded_count += 1
                
                # Trigger processing if not already running
                if loaded_count > 0 and not TUI_QUEUE._processing:
                    import asyncio
                    try:
                        # If there's a running event loop, create a task
                        loop = asyncio.get_running_loop()
                        loop.create_task(TUI_QUEUE._process_queue())
                    except RuntimeError:
                        # No running event loop yet, processing will start when TUI is ready
                        pass
            except ImportError:
                # Fallback to regular add
                for prompt in prompts_to_load:
                    add_to_queue(prompt)
                    loaded_count += 1
        else:
            # Non-TUI mode
            for prompt in prompts_to_load:
                add_to_queue(prompt)
                loaded_count += 1
                    
        console.print(f"[green]✅ {t('queue_loaded_prompts', count=loaded_count, path=file_path)}[/green]")
    except FileNotFoundError:
        console.print(f"[red]❌ {t('queue_file_not_found', path=file_path)}[/red]")
    except Exception as e:
        console.print(f"[red]❌ {t('queue_load_error', error=e)}[/red]")
        
    return loaded_count


def load_queue_from_env():
    """Load queue from file specified in CAI_QUEUE_FILE environment variable"""
    queue_file = os.getenv("CAI_QUEUE_FILE")
    
    if queue_file:
        # Expand user home directory if needed
        queue_file = os.path.expanduser(queue_file)
        
        if os.path.exists(queue_file):
            loaded = load_queue_from_file(queue_file)
            if loaded > 0:
                console.print(f"[cyan]📋 {t('queue_auto_loaded', count=loaded)}[/cyan]")
        else:
            console.print(f"[yellow]⚠️ {t('queue_env_file_not_found', path=queue_file)}[/yellow]")


# Note: Auto-loading is handled by the main CLI and TUI on startup
# to avoid circular imports and ensure proper initialization