"""
CTR (Cut The Rope) command for security game analysis.
This command provides access to the Cut The Rope game-theoretic security analysis.
"""

import os
import json
import asyncio
import threading
from typing import List, Optional
from pathlib import Path
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax

from cai.repl.commands.base import Command, register_command
from cai.i18n import t as _t

# Heavy imports moved to lazy loading
# These will be imported only when CTR command is actually used
ctr_experiment = None
visualize_baseline_results = None
get_ctr_output_base_dir = None

def _ensure_ctr_imports():
    """Lazily import heavy CTR modules only when needed."""
    global ctr_experiment, visualize_baseline_results, get_ctr_output_base_dir
    if ctr_experiment is None:
        from cai.ctr import experiment as _ctr_experiment
        ctr_experiment = _ctr_experiment
    if visualize_baseline_results is None:
        from cai.ctr.visualization import visualize_baseline_results as _vis
        visualize_baseline_results = _vis
    if get_ctr_output_base_dir is None:
        from cai.ctr.paths import get_ctr_output_base_dir as _get_dir
        get_ctr_output_base_dir = _get_dir

console = Console()


class CTRCommand(Command):
    """CTR command for security game analysis.

    This command serves as the primary interface between CAI's REPL and the CTR
    (Cut The Rope) game-theoretic security analysis system. It handles command
    registration, context gathering, and orchestrates the execution of CTR experiments.
    """

    def __init__(self):
        # Command Registration
        # This initializes the CTR command with the REPL system.
        # The command will be registered globally via register_command() at module load (line 564)
        super().__init__(
            name="/ctr",
            description=_t('ctr_description'),
            aliases=["ctr"]  # Allows both '/ctr' and 'ctr' to invoke the command
        )
        
        # Add subcommands
        self.add_subcommand("show", _t('ctr_sub_show'), self.handle_show)
        self.add_subcommand("graph", _t('ctr_sub_graph'), self.handle_graph)
        self.add_subcommand("list", _t('ctr_sub_list'), self.handle_list)
        self.add_subcommand("use", _t('ctr_sub_use'), self.handle_use)
        self.add_subcommand("open", _t('ctr_sub_open'), self.handle_open)
        
        # Store the last run results
        self.last_results_dir = None

    def handle_no_args(self) -> bool:
        # Ensure CTR modules are loaded
        _ensure_ctr_imports()
        """Run the full CTR analysis on current context.

        Command Dispatch
        This method is called by the base Command.handle() when /ctr is invoked
        without arguments. It serves as the entry point for the default CTR analysis.
        """
        return self.run_full_analysis()

    def run_full_analysis(self, log_path: Optional[str] = None) -> bool:
        """Run the complete CTR analysis.

        Main Orchestrator
        This method coordinates the entire CTR analysis pipeline:
        1. Context gathering (3-tier fallback for conversation data)
        2. Execution mode detection (TUI vs CLI, async vs sync)
        3. Experiment invocation via ctr_experiment.run()
        4. Result handling and UI updates
        """
        console.print(f"[yellow]{_t('ctr_running')}[/yellow]")

        # Context Gathering - Priority 1
        # Try to fetch in-memory history from the active agent
        # This is the preferred source as it contains the most current conversation state
        in_memory_history = None
        try:
            from cai.sdk.agents.simple_agent_manager import AGENT_MANAGER
            active_agent = AGENT_MANAGER.get_active_agent()
            active_name = getattr(active_agent, 'name', None)
            # Prefer the model's live history when available
            if active_agent and hasattr(active_agent, 'model') and hasattr(active_agent.model, 'message_history'):
                if active_agent.model.message_history:
                    in_memory_history = list(active_agent.model.message_history)
            # Fallback to manager's history mapping
            if in_memory_history is None and active_name:
                hist = AGENT_MANAGER.get_message_history(active_name)
                if hist:
                    in_memory_history = list(hist)
        except Exception:
            in_memory_history = None

        # Context Gathering - Priority 2
        # If no in-memory history (or caller forced a file), discover the current session log path
        # This fallback uses the session recorder which writes conversations to JSONL files
        if not in_memory_history and not log_path:
            try:
                from cai.sdk.agents.run_to_jsonl import get_session_recorder
                recorder = get_session_recorder()
                if hasattr(recorder, 'filename'):
                    log_path = recorder.filename
                    console.print(f"[dim]Using current session log: {log_path}[/dim]")
            except Exception:
                pass
        
        # Context Gathering - Priority 3
        # If still no log path, try to find recent logs in the standard CAI logs directory
        # This is the final fallback, using the most recently modified log file
        if not log_path:
            import glob
            log_dir = os.path.expanduser("~/.cai/logs")
            if os.path.exists(log_dir):
                logs = glob.glob(os.path.join(log_dir, "*.jsonl"))
                if logs:
                    logs.sort(key=os.path.getmtime, reverse=True)
                    log_path = logs[0]
                    console.print(f"[dim]Using most recent log: {log_path}[/dim]")
        
        if not in_memory_history and not log_path:
            console.print(f"[red]{_t('ctr_no_history')}[/red]")
            return False
        
        def _execute_experiment_sync():
            """Run experiment in this thread using direct entrypoint.

            CTR Experiment Invocation
            This is where we transition from the REPL command layer to the CTR experiment layer.
            Uses asyncio.run() to execute the async experiment.run() function synchronously.
            The experiment.run() function (in ctr/experiment.py:1272) handles:
            - Log processing
            - LLM-based graph extraction (with ModelSettings max_tokens=8192)
            - Probability computation
            - CTR core solver execution
            - Visualization generation
            """
            if in_memory_history:
                # Extract token counts from active_agent.model if available
                token_counts = None
                try:
                    if active_agent and hasattr(active_agent, 'model'):
                        model = active_agent.model
                        if hasattr(model, 'total_input_tokens') and hasattr(model, 'total_output_tokens'):
                            token_counts = {
                                'input_tokens': getattr(model, 'total_input_tokens', 0),
                                'output_tokens': getattr(model, 'total_output_tokens', 0),
                                'total_tokens': getattr(model, 'total_input_tokens', 0) + getattr(model, 'total_output_tokens', 0)
                            }
                            # Try to get the last response usage for more detail if available
                            if hasattr(model, '_last_response_usage') and model._last_response_usage:
                                last_usage = model._last_response_usage
                                if hasattr(last_usage, 'prompt_tokens'):
                                    token_counts['last_prompt_tokens'] = last_usage.prompt_tokens
                                if hasattr(last_usage, 'completion_tokens'):
                                    token_counts['last_completion_tokens'] = last_usage.completion_tokens
                except Exception:
                    pass  # Silently fail if token extraction doesn't work

                asyncio.run(ctr_experiment.run(messages=in_memory_history, token_counts=token_counts))
            else:
                asyncio.run(ctr_experiment.run(input_log=log_path))

        def _resolve_results_dir() -> Optional[str]:
            output_dir = get_ctr_output_base_dir()
            if os.path.exists(output_dir):
                run_dirs = [d for d in os.listdir(output_dir) if d.startswith('run_')]
                if run_dirs:
                    run_dirs.sort()
                    return os.path.join(output_dir, run_dirs[-1])
            return None

        def _focus_ctr_tab_and_load(run_dir: Optional[str]) -> None:
            """Switch to CTR tab and load the given run in the CTR canvas (TUI only).

            TUI Integration
            This function handles the interaction with CAI's Terminal User Interface.
            It switches to the CTR tab and loads the results for visualization.
            Uses thread-safe UI updates via app.call_from_thread() when available.
            """
            try:
                from cai.tui.cai_terminal import CAITerminal
                from cai.tui.components.graph_canvas import CTRCanvas
                from textual.widgets import Select
            except Exception:
                return

            app = getattr(CAITerminal, "_current_app", None)
            if not app:
                # Try Textual API as fallback
                try:
                    from textual.app import App
                    app = App.get_running_app()
                except Exception:
                    app = None
            if not app:
                return

            def _ui_update():
                try:
                    # Switch to CTR tab
                    try:
                        app.action_show_ctr()
                    except Exception:
                        try:
                            app.switch_to_tab("ctr")
                        except Exception:
                            pass

                    # Find canvas and reload runs
                    canvas = app.query_one("#ctr-canvas", CTRCanvas)
                    # Refresh available runs and select the new one if present
                    try:
                        canvas._load_runs_into_select()  # noqa: SLF001
                    except Exception:
                        pass
                    try:
                        sel = canvas.query_one("#run-select", Select)
                        if run_dir and os.path.isdir(run_dir):
                            # If this run is in options, pick it
                            options = getattr(sel, "options", [])
                            # options are list of (label, value)
                            values = [getattr(o, "value", None) if hasattr(o, "value") else (o[1] if isinstance(o, tuple) else None) for o in options]
                            if run_dir in values:
                                sel.value = run_dir
                            elif options:
                                sel.value = options[-1].value if hasattr(options[-1], "value") else options[-1][1]
                        # Load the selected run into viewport
                        canvas._load_selected_run()  # noqa: SLF001
                    except Exception:
                        pass
                except Exception:
                    pass

            # Ensure execution on UI thread when possible
            try:
                if hasattr(app, "call_from_thread"):
                    app.call_from_thread(_ui_update)
                else:
                    _ui_update()
            except Exception:
                _ui_update()

        # Execution Mode Detection
        # Determines whether to run CTR synchronously or in a background thread.
        # This is critical for proper integration with both CLI and TUI modes.
        # - TUI mode: Runs in background to avoid blocking the UI
        # - Async context: Runs in background to avoid event loop conflicts
        # - CLI mode: Runs synchronously for immediate feedback
        in_tui = os.getenv("CAI_TUI_MODE") == "true"
        loop_running = False
        try:
            loop = asyncio.get_running_loop()
            loop_running = True if loop and loop.is_running() else False
        except RuntimeError:
            loop_running = False

        if in_tui or loop_running:
            # Async/Background Execution
            # In TUI or async contexts, CTR runs in a daemon thread to avoid blocking.
            # This allows the UI to remain responsive while CTR analysis proceeds.
            console.print(f"[dim]{_t('ctr_background')}[/dim]\n")

            def _run_and_report():
                try:
                    _execute_experiment_sync()  # Calls ctr_experiment.run()
                    results_dir = _resolve_results_dir()
                    self.last_results_dir = results_dir

                    def _notify_success():
                        if results_dir:
                            console.print(
                                f"[green]{_t('ctr_complete', dir=results_dir)}[/green]"
                            )
                            console.print(
                                f"[dim]{_t('ctr_show_hint')}[/dim]"
                            )
                            # Auto-focus CTR tab and load latest run
                            _focus_ctr_tab_and_load(results_dir)
                        else:
                            console.print(f"[red]{_t('ctr_no_results')}[/red]")

                    # If in TUI, marshal back to UI thread when possible
                    # Run UI update; rely on CAITerminal app
                    _notify_success()
                except Exception as e:  # noqa: BLE001
                    import traceback

                    def _notify_error():
                        console.print(f"[red]{_t('ctr_error_analysis', error=e)}[/red]")
                        console.print(f"[dim]{traceback.format_exc()}[/dim]")

                    _notify_error()

            t = threading.Thread(target=_run_and_report, daemon=True)
            t.start()
            return True

        # Synchronous Execution
        # In CLI mode without an async context, CTR runs synchronously.
        # This provides immediate feedback in command-line environments.
        try:
            _execute_experiment_sync()  # Blocks until CTR analysis completes
            results_dir = _resolve_results_dir()
            self.last_results_dir = results_dir
            if results_dir:
                console.print(
                    f"[green]{_t('ctr_complete', dir=results_dir)}[/green]"
                )
                console.print(
                    f"[dim]{_t('ctr_show_hint')}[/dim]"
                )
                # If in TUI, auto load CTR tab as well
                if os.getenv("CAI_TUI_MODE") == "true":
                    _focus_ctr_tab_and_load(results_dir)
                return True
            console.print(f"[red]{_t('ctr_no_results')}[/red]")
            return False
        except Exception as e:  # noqa: BLE001
            import traceback
            console.print(f"[red]{_t('ctr_error_analysis', error=e)}[/red]")
            console.print(f"[dim]{traceback.format_exc()}[/dim]")
            return False

    def handle_show(self, args: Optional[List[str]] = None) -> bool:
        # Ensure CTR modules are loaded
        _ensure_ctr_imports()
        """Display the defender/attacker strategies and game equilibrium."""
        # In TUI, just focus CTR tab and load the most recent run
        if os.getenv("CAI_TUI_MODE") == "true":
            # Try to resolve last results directory if not set
            if not self.last_results_dir or not os.path.exists(self.last_results_dir):
                output_dir = get_ctr_output_base_dir()
                if os.path.exists(output_dir):
                    run_dirs = [d for d in os.listdir(output_dir) if d.startswith('run_')]
                    if run_dirs:
                        run_dirs.sort()
                        self.last_results_dir = os.path.join(output_dir, run_dirs[-1])
            # Switch UI to CTR and load
            try:
                # Reuse helper via local implementation
                # Minimal inline to avoid duplication
                from cai.tui.cai_terminal import CAITerminal
                app = getattr(CAITerminal, "_current_app", None)
                if app:
                    if hasattr(app, "call_from_thread"):
                        app.call_from_thread(lambda: app.action_show_ctr())
                    else:
                        app.action_show_ctr()
            except Exception:
                pass
            return True

        # Check if we have results to show
        if not self.last_results_dir:
            # Try to find the most recent results
            output_dir = get_ctr_output_base_dir()
            if os.path.exists(output_dir):
                # First check for 'latest' symlink
                latest_link = os.path.join(output_dir, 'latest')
                if os.path.islink(latest_link) and os.path.exists(latest_link):
                    self.last_results_dir = os.path.realpath(latest_link)
                else:
                    # Fall back to finding most recent run_* directory
                    # But also check subdirectories (session folders)
                    all_run_dirs = []

                    # Check direct run_* directories
                    for item in os.listdir(output_dir):
                        if item.startswith('run_'):
                            all_run_dirs.append(os.path.join(output_dir, item))
                        # Also check one level deeper for session directories
                        elif os.path.isdir(os.path.join(output_dir, item)):
                            subdir = os.path.join(output_dir, item)
                            try:
                                for subitem in os.listdir(subdir):
                                    if subitem.startswith('run_'):
                                        all_run_dirs.append(os.path.join(subdir, subitem))
                            except (PermissionError, OSError):
                                continue

                    if all_run_dirs:
                        # Sort by modification time to get the most recent
                        all_run_dirs.sort(key=lambda x: os.path.getmtime(x), reverse=True)
                        self.last_results_dir = all_run_dirs[0]
        
        if not self.last_results_dir or not os.path.exists(self.last_results_dir):
            console.print(f"[yellow]{_t('ctr_no_results_found')}[/yellow]")
            return False
        
        try:
            # Prefer JSON baseline if present; otherwise parse ctr_baseline.txt
            nash_data = None
            nash_file = os.path.join(self.last_results_dir, 'nash_equilibrium.json')
            if os.path.exists(nash_file):
                with open(nash_file, 'r') as f:
                    nash_data = json.load(f)

            if not nash_data:
                import re
                baseline_file = os.path.join(self.last_results_dir, 'ctr_baseline.txt')
                if os.path.exists(baseline_file):
                    with open(baseline_file, 'r') as f:
                        content = f.read()
                    match = re.search(r'BASELINE RESULT DICTIONARY:\n-+\n(\{[\s\S]*?\})', content)
                    if match:
                        nash_data = json.loads(match.group(1))
                        console.print(f"[dim]Loaded data from ctr_baseline.txt[/dim]")

            if not nash_data:
                console.print(f"[red]{_t('ctr_nash_not_found')}[/red]")
                return False

            if nash_data.get('error') and not nash_data.get('optimal_defense'):
                console.print(f"[red]{_t('ctr_analysis_error', error=nash_data['error'])}[/red]")
                return False

            # Load attack path sequences if available
            paths = None
            paths_json = os.path.join(self.last_results_dir, 'attack_paths.json')
            if os.path.exists(paths_json):
                try:
                    with open(paths_json, 'r') as pf:
                        paths = json.load(pf).get('paths')
                except Exception:
                    paths = None

            # Unified, improved visualization (defense + attacker path sequences + equilibrium)
            visualize_baseline_results(nash_data, paths=paths, print_to_console=True)
            return True

        except Exception as e:
            console.print(f"[red]{_t('ctr_error_display', error=e)}[/red]")
            return False

    def handle_graph(self, args: Optional[List[str]] = None) -> bool:
        # Ensure CTR modules are loaded
        _ensure_ctr_imports()
        """Display the attack graph visualization."""
        # In TUI, never open external viewers; focus the CTR tab and load latest
        if os.getenv("CAI_TUI_MODE") == "true":
            try:
                from cai.tui.cai_terminal import CAITerminal
                app = getattr(CAITerminal, "_current_app", None)
                if app:
                    if hasattr(app, "call_from_thread"):
                        app.call_from_thread(lambda: app.action_show_ctr())
                    else:
                        app.action_show_ctr()
            except Exception:
                pass
            return True

        # Check if we have results to show (CLI mode)
        if not self.last_results_dir:
            # Try to find the most recent results
            output_dir = get_ctr_output_base_dir()
            if os.path.exists(output_dir):
                # First check for 'latest' symlink
                latest_link = os.path.join(output_dir, 'latest')
                if os.path.islink(latest_link) and os.path.exists(latest_link):
                    self.last_results_dir = os.path.realpath(latest_link)
                else:
                    # Fall back to finding most recent run_* directory
                    # But also check subdirectories (session folders)
                    all_run_dirs = []

                    # Check direct run_* directories
                    for item in os.listdir(output_dir):
                        if item.startswith('run_'):
                            all_run_dirs.append(os.path.join(output_dir, item))
                        # Also check one level deeper for session directories
                        elif os.path.isdir(os.path.join(output_dir, item)):
                            subdir = os.path.join(output_dir, item)
                            try:
                                for subitem in os.listdir(subdir):
                                    if subitem.startswith('run_'):
                                        all_run_dirs.append(os.path.join(subdir, subitem))
                            except (PermissionError, OSError):
                                continue

                    if all_run_dirs:
                        # Sort by modification time to get the most recent
                        all_run_dirs.sort(key=lambda x: os.path.getmtime(x), reverse=True)
                        self.last_results_dir = all_run_dirs[0]
        
        if not self.last_results_dir or not os.path.exists(self.last_results_dir):
            console.print(f"[yellow]{_t('ctr_no_results_found')}[/yellow]")
            return False
        
        try:
            # Check for graph files - use the actual filenames being generated
            graph_llm_png = os.path.join(self.last_results_dir, 'attack_graph_llm.png')
            graph_individual_png = os.path.join(self.last_results_dir, 'attack_graph_individual.png')
            graph_cleaned_png = os.path.join(self.last_results_dir, 'attack_graph_individual_cleaned.png')
            graph_json = os.path.join(self.last_results_dir, 'attack_graph.json')
            
            # Check which graph files exist and open the best one
            graph_to_open = None
            if os.path.exists(graph_llm_png):
                graph_to_open = graph_llm_png
                console.print(f"[green]{_t('ctr_graph_llm_found')}[/green] {graph_llm_png}")
            elif os.path.exists(graph_individual_png):
                graph_to_open = graph_individual_png
                console.print(f"[green]{_t('ctr_graph_individual_found')}[/green] {graph_individual_png}")
            elif os.path.exists(graph_cleaned_png):
                graph_to_open = graph_cleaned_png
                console.print(f"[green]{_t('ctr_graph_cleaned_found')}[/green] {graph_cleaned_png}")
            
            if graph_to_open:
                console.print(f"[dim]{_t('ctr_graph_opening')}[/dim]")
                import platform, subprocess
                try:
                    if platform.system() == 'Darwin':  # macOS
                        subprocess.run(["open", graph_to_open], check=False)
                    elif platform.system() == 'Linux':
                        subprocess.run(["xdg-open", graph_to_open], check=False)
                    elif platform.system() == 'Windows':
                        os.startfile(graph_to_open)  # type: ignore[attr-defined]
                except Exception:
                    pass
            
            # Try to display graph structure from graph_information.txt
            graph_info_file = os.path.join(self.last_results_dir, 'graph_information.txt')
            if os.path.exists(graph_info_file):
                import re
                with open(graph_info_file, 'r') as f:
                    content = f.read()
                
                # Extract the JSON graph structure from LLM output
                match = re.search(r'LLM Output:\n-+\n(\{[\s\S]*?\})\n-+', content)
                if match:
                    try:
                        graph_data = json.loads(match.group(1))
                        
                        console.print(f"\n[bold cyan]═══ {_t('ctr_graph_structure_title')} ═══[/bold cyan]")

                        # Show nodes
                        nodes = graph_data.get('nodes', [])
                        console.print(f"\n[bold]{_t('ctr_graph_nodes')}[/bold] {len(nodes)} total")

                        node_table = Table(show_header=True, header_style="bold magenta")
                        node_table.add_column(_t('ctr_graph_col_node_id'), style="cyan")
                        node_table.add_column(_t('ctr_graph_col_name'), style="yellow")
                        node_table.add_column(_t('ctr_graph_col_vulnerable'), justify="center", style="red")
                        
                        for node in nodes[:10]:  # Show first 10 nodes
                            node_id = node.get('id', '')
                            node_name = node.get('name', 'unknown')
                            vulnerable = _t('ctr_graph_yes') if node.get('vulnerability') else _t('ctr_graph_no')
                            node_table.add_row(node_id, node_name, vulnerable)
                        
                        console.print(node_table)
                        
                        if len(nodes) > 10:
                            console.print(f"[dim]{_t('ctr_graph_more_nodes', count=len(nodes) - 10)}[/dim]")

                        # Show edges
                        edges = graph_data.get('edges', [])
                        console.print(f"\n[bold]{_t('ctr_graph_edges')}[/bold] {len(edges)} total")

                        edge_table = Table(show_header=True, header_style="bold magenta")
                        edge_table.add_column(_t('ctr_graph_col_source'), style="cyan")
                        edge_table.add_column(_t('ctr_graph_col_target'), style="cyan")
                        
                        for edge in edges[:10]:  # Show first 10 edges
                            source = edge.get('source', '')
                            target = edge.get('target', '')
                            edge_table.add_row(source, target)
                        
                        console.print(edge_table)
                        
                        if len(edges) > 10:
                            console.print(f"[dim]{_t('ctr_graph_more_edges', count=len(edges) - 10)}[/dim]")
                    except json.JSONDecodeError:
                        console.print(f"[yellow]{_t('ctr_graph_parse_error')}[/yellow]")
            
            return True

        except Exception as e:
            console.print(f"[red]{_t('ctr_error_graph', error=e)}[/red]")
            return False

    def handle_list(self, args: Optional[List[str]] = None) -> bool:
        # Ensure CTR modules are loaded
        _ensure_ctr_imports()
        base = get_ctr_output_base_dir()
        if not os.path.isdir(base):
            console.print(f"[yellow]{_t('ctr_no_output_dir')}[/yellow]")
            return False
        entries = []
        for name in os.listdir(base):
            path = os.path.join(base, name)
            if name.startswith("run_") and os.path.isdir(path):
                try:
                    mtime = os.path.getmtime(path)
                except Exception:
                    mtime = 0
                entries.append((name, path, mtime))
        if not entries:
            console.print(f"[yellow]{_t('ctr_no_runs')}[/yellow]")
            return False
        entries.sort(key=lambda x: x[2], reverse=True)
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column(_t('ctr_col_index'), justify="right")
        table.add_column(_t('ctr_col_run'), justify="left")
        table.add_column(_t('ctr_col_path'), justify="left")
        for idx, (name, path, _) in enumerate(entries, 1):
            marker = _t('ctr_active_marker') if self.last_results_dir and os.path.exists(self.last_results_dir) and os.path.samefile(self.last_results_dir, path) else ""
            table.add_row(str(idx), name + marker, path)
        console.print(table)
        return True

    def handle_use(self, args: Optional[List[str]] = None) -> bool:
        # Ensure CTR modules are loaded
        _ensure_ctr_imports()
        token = (args or [None])[0]
        base = get_ctr_output_base_dir()
        if not token:
            console.print(f"[yellow]{_t('ctr_usage_use')}[/yellow]")
            return False
        # Build candidate list sorted by mtime desc
        entries = []
        if os.path.isdir(base):
            for name in os.listdir(base):
                path = os.path.join(base, name)
                if name.startswith("run_") and os.path.isdir(path):
                    entries.append(path)
            entries.sort(key=lambda p: os.path.getmtime(p), reverse=True)
        selected = None
        # Numeric index
        if token.isdigit():
            idx = int(token)
            if 1 <= idx <= len(entries):
                selected = entries[idx - 1]
        # Exact name match in base
        if not selected:
            cand = os.path.join(base, token)
            if os.path.isdir(cand):
                selected = cand
        # Raw path
        if not selected and os.path.isdir(token):
            selected = token
        if not selected:
            console.print(f"[red]{_t('ctr_run_not_found')}[/red]")
            return False
        self.last_results_dir = selected
        console.print(f"[green]{_t('ctr_run_set')}[/green] {selected}")
        return True

    def handle_open(self, args: Optional[List[str]] = None) -> bool:
        # Ensure CTR modules are loaded
        _ensure_ctr_imports()
        """Open the folder containing the latest CTR run_* directory."""
        base = get_ctr_output_base_dir()
        if not os.path.isdir(base):
            console.print(f"[yellow]{_t('ctr_no_output_dir_open')}[/yellow]")
            return False

        # Prefer parent of the active run; otherwise parent of newest run; fallback to base
        parent = None
        if self.last_results_dir and os.path.isdir(self.last_results_dir):
            parent = os.path.dirname(self.last_results_dir)
        else:
            runs = [
                os.path.join(base, d)
                for d in os.listdir(base)
                if d.startswith("run_") and os.path.isdir(os.path.join(base, d))
            ]
            if runs:
                runs.sort(key=lambda p: os.path.getmtime(p), reverse=True)
                parent = os.path.dirname(runs[0])
        parent = parent or base

        # Open using platform-appropriate mechanism
        try:
            import platform, subprocess
            system = platform.system()
            if system == 'Darwin':
                subprocess.run(["open", parent], check=False)
            elif system == 'Linux':
                subprocess.run(["xdg-open", parent], check=False)
            elif system == 'Windows':
                os.startfile(parent)  # type: ignore[attr-defined]
            console.print(f"[green]{_t('ctr_folder_opened')}[/green] {parent}")
            return True
        except Exception as e:
            console.print(f"[red]{_t('ctr_folder_open_failed', error=e)}[/red]")
            console.print(f"[dim]Path: {parent}[/dim]")
            return False


# Global Command Registration
# This line executes at module import time and registers the CTRCommand instance
# with the global COMMANDS dictionary in base.py.
# After this registration:
# - COMMANDS["/ctr"] = CTRCommand instance
# - COMMAND_ALIASES["ctr"] = "/ctr"
# The REPL's handle_command_with_autocorrect() function (called from cli.py:1544)
# will now recognize and dispatch /ctr commands to this handler.
register_command(CTRCommand())
