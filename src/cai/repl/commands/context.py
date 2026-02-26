"""
Context command for CAI REPL.
This module provides commands for viewing context usage and token statistics.
"""

import json
import os
import pathlib
import sys
from typing import Dict, List, Optional
from rich.console import Console

from cai.repl.commands.base import Command, register_command
from cai.sdk.agents.simple_agent_manager import AGENT_MANAGER
from cai.sdk.agents.models.openai_chatcompletions import count_tokens_with_tiktoken
from cai.sdk.agents.run_context import RunContextWrapper


class DummyLock:
    """No-op lock for when _registry_lock is unavailable."""

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def _get_console() -> Console:
    """Return a Console bound to the current stdout.

    In TUI mode stdout is dynamically routed per terminal. Creating the
    Console lazily ensures it writes to the correct output widget.
    """
    return Console(file=sys.stdout)


class ContextCommand(Command):
    """
    Command for viewing context usage and token statistics.

    This command displays:
    - Total context usage (used/max tokens)
    - Visual grid representation of context usage with colors
    - Breakdown by category (system prompt, tool definitions, memory, messages, etc.)
    """

    def __init__(self):
        """Initialize the context command."""
        super().__init__(
            name="/context",
            description="View context usage and token statistics",
            aliases=["/ctx"],
        )

    def handle(self, args: Optional[List[str]] = None) -> bool:
        """
        Handle the /context command.

        Args:
            args: Optional list of command arguments

        Returns:
            bool: True if the command was handled successfully
        """
        # Resolve the active agent for the current execution context
        active_agent = self._get_active_agent_for_context()

        if not active_agent:
            # In TUI, we may still have history via terminal P-ID; continue gracefully
            if os.getenv("CAI_TUI_MODE") != "true":
                _get_console().print("[yellow]No active agent found[/yellow]")
                return False

        # Get model name and capacity
        model_name = self._get_model_name(active_agent)
        max_tokens = self._get_model_max_tokens(model_name)

        # Prefer the last interaction snapshot if available to match IN:
        last_used = 0
        last_breakdown = None
        last_msgs = None
        selected_agent_id: Optional[str] = None
        debug_src = []  # collect debug breadcrumbs when CAI_CTX_DEBUG=1
        if active_agent and hasattr(active_agent, "model") and active_agent.model:
            model = active_agent.model
            last_used = int(getattr(model, "_last_request_actual_input_tokens", 0) or 0)
            # Use stored breakdown if available
            if hasattr(model, "_last_request_breakdown"):
                last_breakdown = getattr(model, "_last_request_breakdown") or None
                if last_breakdown:
                    debug_src.append("last_breakdown=snapshot")
            # Also capture the exact message list used in the last request (best-effort)
            try:
                lm = getattr(model, "_last_request_messages", None)
                if isinstance(lm, list) and lm:
                    last_msgs = lm
                    debug_src.append("last_msgs=snapshot")
            except Exception:
                last_msgs = None

        # Fallback: prefer ACTIVE AGENT (agent_id) first, then terminal-scoped, then name
        if last_used <= 0:
            try:
                from cai.util import COST_TRACKER
                tid = self._get_current_terminal_id()
                agent_id = getattr(active_agent.model, "agent_id", None) if active_agent and hasattr(active_agent, "model") else None
                agent_name = getattr(active_agent, "name", None)

                best_state = None
                best_updated = -1
                # 1) Exact agent_id match (most precise)
                if agent_id:
                    for state in getattr(COST_TRACKER, "agent_cost_states", {}).values():
                        if not isinstance(state, dict):
                            continue
                        if state.get("agent_id") != agent_id:
                            continue
                        upd = int(state.get("updated_at", 0) or 0)
                        if upd >= best_updated:
                            best_updated = upd
                            best_state = state
                # 2) Then match by current terminal id (freshest in that terminal)
                if best_state is None and tid:
                    for state in getattr(COST_TRACKER, "agent_cost_states", {}).values():
                        if not isinstance(state, dict):
                            continue
                        if state.get("terminal_id") != tid:
                            continue
                        upd = int(state.get("updated_at", 0) or 0)
                        if upd >= best_updated:
                            best_updated = upd
                            best_state = state
                # 3) Finally by agent_name (least precise)
                if best_state is None and agent_name:
                    for state in getattr(COST_TRACKER, "agent_cost_states", {}).values():
                        if not isinstance(state, dict):
                            continue
                        if state.get("agent_name") != agent_name:
                            continue
                        upd = int(state.get("updated_at", 0) or 0)
                        if upd >= best_updated:
                            best_updated = upd
                            best_state = state
                if best_state:
                    last_used = int(best_state.get("last_interaction_input_tokens", 0) or 0)
                    selected_agent_id = best_state.get("agent_id")
                    debug_src.append(f"state.agent_id={selected_agent_id or '-'} tid={tid or '-'}")
            except Exception:
                pass

        # Final fallback: avoid globals in TUI; only use global in headless CLI
        if last_used <= 0:
            try:
                if os.getenv("CAI_TUI_MODE") != "true":
                    from cai.util import COST_TRACKER
                    last_used = int(getattr(COST_TRACKER, "interaction_input_tokens", 0) or 0)
                else:
                    last_used = 0
            except Exception:
                last_used = 0

        # Build breakdown and total_used
        if last_used > 0 and last_breakdown:
            system_tokens = int(last_breakdown.get("system_tokens", 0) or 0)
            tool_definitions_tokens = int(last_breakdown.get("tool_definitions_tokens", 0) or 0)
            messages_breakdown = {
                "user": int(last_breakdown.get("messages_breakdown", {}).get("user", 0) or 0),
                "assistant": int(last_breakdown.get("messages_breakdown", {}).get("assistant", 0) or 0),
                "tool_calls": int(last_breakdown.get("messages_breakdown", {}).get("tool_calls", 0) or 0),
                "tool_results": int(last_breakdown.get("messages_breakdown", {}).get("tool_results", 0) or 0),
            }
            memory_tokens = 0  # Memory is accounted inside messages/system when applicable
            total_messages = sum(messages_breakdown.values())
            # Force total_used to equal last_used (panel IN:)
            known_sum = system_tokens + tool_definitions_tokens + memory_tokens + total_messages
            overhead = last_used - known_sum
            total_used = last_used
            free_space = max(0, max_tokens - total_used)
            usage_percent = (total_used / max_tokens * 100) if max_tokens > 0 else 0
        else:
            # Recount from history; if we do have last_used>0 but no last_breakdown,
            # use the selected agent's history in TUI (agent_id), otherwise fall back to active agent.
            if selected_agent_id and os.getenv("CAI_TUI_MODE") == "true":
                message_history = AGENT_MANAGER.get_message_history(selected_agent_id) or []
                system_tokens = 0
                tool_definitions_tokens = 0
                memory_tokens = 0
                messages_breakdown = self._calculate_messages_tokens(None, message_history)
            else:
                message_history = last_msgs or self._get_message_history_for_context(active_agent)
                system_tokens = self._calculate_system_tokens(active_agent, message_history)
                tool_definitions_tokens = self._calculate_tool_definitions_tokens(active_agent)
                memory_tokens = self._calculate_memory_tokens(active_agent)
                messages_breakdown = self._calculate_messages_tokens(active_agent, message_history)
                if last_msgs is None:
                    messages_breakdown["tool_results"] = 0
            total_messages = sum(messages_breakdown.values())
            known_sum = system_tokens + tool_definitions_tokens + memory_tokens + total_messages
            if last_used > 0:
                total_used = last_used
                overhead = last_used - known_sum
            else:
                total_used = known_sum
                overhead = 0
            free_space = max(0, max_tokens - total_used)
            usage_percent = (total_used / max_tokens * 100) if max_tokens > 0 else 0
            debug_src.append("last_breakdown=history_recount")

        # --- Normalization step: ensure breakdown sum never exceeds total_used (IN:) ---
        # Build category map for normalization
        categories_map = {
            "system": int(system_tokens or 0),
            "tools": int(tool_definitions_tokens or 0),
            "memory": int(memory_tokens or 0),
            "user": int(messages_breakdown.get("user", 0) or 0),
            "assistant": int(messages_breakdown.get("assistant", 0) or 0),
            "tool_calls": int(messages_breakdown.get("tool_calls", 0) or 0),
            "tool_results": int(messages_breakdown.get("tool_results", 0) or 0),
        }
        est_sum = sum(categories_map.values())
        normalization_delta = 0
        if est_sum > total_used and est_sum > 0:
            # Scale down proportionally and distribute rounding to match exactly total_used
            factor = float(total_used) / float(est_sum)
            scaled = {}
            remainders = []
            running_sum = 0
            for k, v in categories_map.items():
                raw = v * factor
                val = int(raw)
                scaled[k] = val
                running_sum += val
                remainders.append((raw - val, k))
            # Distribute remaining tokens by largest fractional parts
            leftover = total_used - running_sum
            if leftover > 0:
                remainders.sort(reverse=True)
                for i in range(leftover):
                    scaled[remainders[i % len(remainders)][1]] += 1
            categories_map = scaled
            normalization_delta = est_sum - total_used
            # No overhead in this case (we normalized to measured usage)
            overhead = 0

        # Reassign normalized values back to variables
        system_tokens = categories_map["system"]
        tool_definitions_tokens = categories_map["tools"]
        memory_tokens = categories_map["memory"]
        messages_breakdown["user"] = categories_map["user"]
        messages_breakdown["assistant"] = categories_map["assistant"]
        messages_breakdown["tool_calls"] = categories_map["tool_calls"]
        messages_breakdown["tool_results"] = categories_map["tool_results"]

        # Label explícito para la iteración anterior (lo que leyó el modelo)
        try:
            _get_console().print("\n[bold green]Last Iteration (model read)[/bold green]")
        except Exception:
            pass

        # Display context usage
        self._display_context_usage(
            total_used=total_used,
            max_tokens=max_tokens,
            usage_percent=usage_percent,
            system_tokens=system_tokens,
            tool_definitions_tokens=tool_definitions_tokens,
            memory_tokens=memory_tokens,
            messages_breakdown=messages_breakdown,
            free_space=free_space,
        )

        # If we had adjustments, print lines so totals are transparent
        if overhead and overhead > 0:
            try:
                from rich.console import Console
                c = _get_console()
                c.print(f"  [dim]◼[/dim] Overhead/serialization: {self._format_number(overhead)} tokens ({(overhead/max_tokens*100) if max_tokens else 0:.1f}%)")
            except Exception:
                pass
        elif normalization_delta and normalization_delta > 0:
            try:
                from rich.console import Console
                c = _get_console()
                c.print(f"  [dim]◼[/dim] Normalization (provider formatting): -{self._format_number(normalization_delta)} tokens")
            except Exception:
                pass

        # Optional source debug
        try:
            if str(os.getenv("CAI_CTX_DEBUG", "")).lower() in ("1", "true", "yes"):
                _get_console().print(f"  [dim]DEBUG[/dim] last_used={last_used} source={'|'.join(debug_src) if debug_src else 'unknown'} agent_id={selected_agent_id or '-'}")
        except Exception:
            pass

        # Resumen claro: solo IN de la última iteración
        try:
            c = _get_console()
            c.print()
            c.print(f"[bold]Summary[/bold]: IN (last) = {self._format_number(total_used)}")
            c.print("[dim]Note: IN is the sum of 'Last Iteration' categories after normalization.[/dim]")
        except Exception:
            pass

        return True

    def _get_active_agent_for_context(self):
        """Return the most relevant agent for the current CLI/TUI context.

        In TUI mode, attempt to fetch the agent bound to the current terminal
        runner; otherwise fall back to the globally active agent.
        """
        try:
            if os.getenv("CAI_TUI_MODE") == "true":
                # Discover current terminal number (ContextVar-backed)
                try:
                    from cai.tui.core.terminal_tracking import (
                        get_current_terminal_number,
                    )

                    term_num = get_current_terminal_number()
                except Exception:
                    term_num = None

                if term_num:
                    # Try to access the SessionManager and its runner
                    try:
                        from cai.tui.core.session_manager import SessionManager

                        sm = SessionManager.get_instance()
                        if sm and term_num in getattr(sm, "terminal_runners", {}):
                            runner = sm.terminal_runners.get(term_num)
                            if runner and getattr(runner, "agent", None):
                                return runner.agent
                    except Exception:
                        pass

            # Fallback to global active agent
            return AGENT_MANAGER.get_active_agent()
        except Exception:
            return None

    def _get_p_id_for_current_terminal(self) -> Optional[str]:
        """Resolve the P-ID for the current TUI terminal if available."""
        if os.getenv("CAI_TUI_MODE") != "true":
            return None
        try:
            from cai.tui.core.terminal_tracking import get_current_terminal_number

            term_num = get_current_terminal_number()
        except Exception:
            term_num = None

        if not term_num:
            return None

        # Best-effort: find mapping from T{n}_* -> P-ID in the registry
        try:
            prefix = f"T{term_num}_"
            with getattr(AGENT_MANAGER, "_registry_lock", None) or DummyLock():
                for key, val in getattr(AGENT_MANAGER, "_agent_registry", {}).items():
                    if isinstance(key, str) and key.startswith(prefix):
                        return val
        except Exception:
            pass

        # Fallback to predictable mapping used in several parts of TUI
        return f"P{term_num}"

    def _get_current_terminal_id(self) -> Optional[str]:
        """Resolve the current terminal_id using TUI context vars or thread-local."""
        if os.getenv("CAI_TUI_MODE") != "true":
            return None
        try:
            from cai.tui.core.execution_context import get_terminal_id_context
            tid = get_terminal_id_context()
            if tid:
                return tid
        except Exception:
            pass
        try:
            from cai.tui.core.terminal_tracking import get_current_terminal_id
            return get_current_terminal_id()
        except Exception:
            return None

    def _get_message_history_for_context(self, agent) -> list:
        """Get the appropriate message history for the current context.

        - In TUI mode, prefer the history keyed by the terminal's P-ID.
        - Otherwise, use the agent's model history or manager's history by name.
        """
        # TUI-aware resolution
        if os.getenv("CAI_TUI_MODE") == "true":
            # 1) If agent has a model with history, prefer that
            if agent and hasattr(agent, "model") and hasattr(agent.model, "message_history"):
                hist = agent.model.message_history
                if isinstance(hist, list) and hist:
                    return hist

            # 2) Try by P-ID from current terminal
            p_id = self._get_p_id_for_current_terminal()
            if p_id:
                hist = AGENT_MANAGER.get_message_history(p_id)
                if isinstance(hist, list):
                    return hist

            # 3) Last resort: manager by active name
            if agent and hasattr(agent, "name"):
                hist = AGENT_MANAGER.get_message_history(agent.name)
                if isinstance(hist, list):
                    return hist

            return []

        # Non-TUI resolution
        if agent and hasattr(agent, "model") and hasattr(agent.model, "message_history"):
            return agent.model.message_history
        if agent and hasattr(agent, "name"):
            return AGENT_MANAGER.get_message_history(agent.name)
        return []

    def _get_model_name(self, agent) -> str:
        """Get the model name from the agent."""
        if hasattr(agent, "model") and agent.model:
            if isinstance(agent.model, str):
                return agent.model
            elif hasattr(agent.model, "model"):
                return str(agent.model.model)

        # Fallback to environment variable
        return os.getenv("CAI_MODEL", "gpt-4")

    def _get_model_max_tokens(self, model_name: str) -> int:
        """Get the maximum input tokens for a model from shared util."""
        try:
            from cai.util import get_model_input_tokens
            return int(get_model_input_tokens(model_name))
        except Exception:
            return 200000

    def _calculate_system_tokens(self, agent, message_history: Optional[list] = None) -> int:
        """Calculate tokens used by system prompt/instructions.

        Priority:
        1) Use the exact snapshot from the active model (preferred and exact).
        2) If missing, count system messages from history.
        3) If missing, use agent.instructions string if available.
        4) Avoid static estimates unless nothing else is available.
        """
        # 1) Exact snapshot on the model instance
        model = getattr(agent, "model", None)
        if model is not None:
            # If the model already computed token count for system, trust it
            try:
                last_sys_toks = int(getattr(model, "_last_system_tokens", 0) or 0)
                if last_sys_toks > 0:
                    return last_sys_toks
            except Exception:
                pass

            # If we have the literal instructions string, compute dynamically now
            try:
                last_sys_str = getattr(model, "_last_system_instructions", None)
                if isinstance(last_sys_str, str) and last_sys_str.strip():
                    tokens, _ = count_tokens_with_tiktoken(last_sys_str)
                    return int(tokens or 0)
            except Exception:
                pass

            # If we have the exact list of messages used last time, count system-role tokens
            try:
                last_msgs = getattr(model, "_last_request_messages", None)
                if isinstance(last_msgs, list) and last_msgs:
                    total = 0
                    for msg in last_msgs:
                        if isinstance(msg, dict) and msg.get("role") == "system":
                            content = msg.get("content", "")
                            if isinstance(content, str) and content:
                                t, _ = count_tokens_with_tiktoken(content)
                                total += int(t or 0)
                            elif isinstance(content, list):
                                for part in content:
                                    if isinstance(part, dict) and part.get("type") == "text" and part.get("text"):
                                        t, _ = count_tokens_with_tiktoken(part.get("text") or "")
                                        total += int(t or 0)
                    if total > 0:
                        return total
            except Exception:
                pass

        # 2) Fallback: scan message history for system role
        if message_history is None:
            message_history = self._get_message_history_for_context(agent)
        for msg in message_history:
            if isinstance(msg, dict) and msg.get("role") == "system":
                content = msg.get("content", "")
                if content:
                    tokens, _ = count_tokens_with_tiktoken(str(content))
                    return int(tokens or 0)
                break

        # 3) Fallback: agent.instructions string or renderer
        try:
            instructions = getattr(agent, "instructions", None)
            # If renderer callable is present, call with no args to get base instructions
            if callable(instructions) and hasattr(instructions, "_is_system_prompt_renderer"):
                try:
                    rendered = instructions()  # returns base instructions when no args
                    if isinstance(rendered, str) and rendered.strip():
                        tokens, _ = count_tokens_with_tiktoken(rendered)
                        return int(tokens or 0)
                except Exception:
                    pass
            if isinstance(instructions, str) and instructions.strip():
                tokens, _ = count_tokens_with_tiktoken(instructions)
                return int(tokens or 0)
        except Exception:
            pass

        # 4) Nothing else we can measure precisely
        return 0

    def _calculate_tool_definitions_tokens(self, agent) -> int:
        """Calculate tokens used by tool definitions (params_json_schema)."""
        if not hasattr(agent, "tools") or not agent.tools:
            return 0

        total_tokens = 0
        for tool in agent.tools:
            # Use params_json_schema which is what gets sent to the API
            if hasattr(tool, "params_json_schema"):
                schema_json = json.dumps(tool.params_json_schema)
                tokens, _ = count_tokens_with_tiktoken(schema_json)
                total_tokens += tokens
            else:
                # Fallback estimate if schema not available
                total_tokens += 100

        return total_tokens

    def _calculate_memory_tokens(self, agent) -> int:
        """Calculate tokens used by RAG memory (episodic/semantic)."""
        # Check if memory is enabled
        rag_enabled = os.getenv("CAI_MEMORY", "").lower() in ["episodic", "semantic", "all"]
        if not rag_enabled:
            return 0

        # Try to get memory content
        try:
            from cai.rag.vector_db import get_previous_memory

            # Get memory query based on type
            if os.getenv("CAI_MEMORY", "").lower() in ["semantic", "all"]:
                # For semantic, use first line of instructions
                if hasattr(agent, "instructions") and agent.instructions:
                    instructions = agent.instructions
                    if callable(instructions):
                        query = ""
                    else:
                        query = instructions.split("\n")[0].replace("Instructions: ", "")
                else:
                    query = ""
            else:
                # For episodic, use empty query
                query = ""

            memory = get_previous_memory(query)
            if memory:
                tokens, _ = count_tokens_with_tiktoken(memory)
                return tokens
        except Exception:
            pass

        return 0

    def _calculate_messages_tokens(self, agent, message_history: Optional[list] = None) -> Dict[str, int]:
        """Calculate tokens used by message history, separated by type."""
        result = {
            "user": 0,
            "assistant": 0,
            "tool_calls": 0,
            "tool_results": 0,
        }

        # Get message history
        if message_history is None:
            message_history = self._get_message_history_for_context(agent)

        if not message_history:
            return result

        # Analyze each message
        for msg in message_history:
            role = msg.get("role", "")
            content = msg.get("content", "")

            if role == "user":
                # User messages
                tokens, _ = count_tokens_with_tiktoken(str(content))
                result["user"] += tokens

            elif role == "assistant":
                # Assistant messages (can have text + tool_calls)
                if content:
                    tokens, _ = count_tokens_with_tiktoken(str(content))
                    result["assistant"] += tokens

                # Tool calls in assistant messages
                if "tool_calls" in msg and msg["tool_calls"]:
                    tool_calls_json = json.dumps(msg["tool_calls"])
                    tokens, _ = count_tokens_with_tiktoken(tool_calls_json)
                    result["tool_calls"] += tokens

            elif role == "tool":
                # Tool result messages
                tokens, _ = count_tokens_with_tiktoken(str(content))
                result["tool_results"] += tokens

        return result

    def _display_context_usage(
        self,
        total_used: int,
        max_tokens: int,
        usage_percent: float,
        system_tokens: int,
        tool_definitions_tokens: int,
        memory_tokens: int,
        messages_breakdown: Dict[str, int],
        free_space: int,
    ):
        """Display context usage with visual grid and breakdown."""
        # Format numbers
        total_used_str = self._format_number(total_used)
        max_tokens_str = self._format_number(max_tokens)

        # Create title
        title = f"[bold cyan]/context[/bold cyan]"
        _get_console().print(f"\n{title}")

        # Create usage summary
        usage_summary = (
            f"[bold]Context Usage {total_used_str}/{max_tokens_str} tokens "
            f"({usage_percent:.1f}%)[/bold]"
        )
        _get_console().print(usage_summary)

        # Calculate category percentages for coloring
        categories = []
        if system_tokens > 0:
            categories.append(("system", system_tokens, "dim"))
        if tool_definitions_tokens > 0:
            categories.append(("tools", tool_definitions_tokens, "dim"))
        if memory_tokens > 0:
            categories.append(("memory", memory_tokens, "red"))
        if messages_breakdown.get("user", 0) > 0:
            categories.append(("user", messages_breakdown["user"], "blue"))
        if messages_breakdown.get("assistant", 0) > 0:
            categories.append(("assistant", messages_breakdown["assistant"], "green"))
        if messages_breakdown.get("tool_calls", 0) > 0:
            categories.append(("tool_calls", messages_breakdown["tool_calls"], "yellow"))
        if messages_breakdown.get("tool_results", 0) > 0:
            categories.append(("tool_results", messages_breakdown["tool_results"], "magenta"))

        # Create visual grid with colors
        grid = self._create_context_grid(total_used, max_tokens, categories)
        _get_console().print(grid)

        # Create breakdown
        breakdown_lines = []

        # System prompt
        sys_percent = (system_tokens / max_tokens * 100) if max_tokens > 0 else 0
        breakdown_lines.append(
            f"  [dim]◼[/dim] System prompt: {self._format_number(system_tokens)} tokens ({sys_percent:.1f}%)"
        )

        # Tool definitions (not "system tools")
        tools_percent = (tool_definitions_tokens / max_tokens * 100) if max_tokens > 0 else 0
        breakdown_lines.append(
            f"  [dim]◼[/dim] Tool definitions: {self._format_number(tool_definitions_tokens)} tokens ({tools_percent:.1f}%)"
        )

        # Memory files (RAG)
        if memory_tokens > 0:
            mem_percent = (memory_tokens / max_tokens * 100) if max_tokens > 0 else 0
            breakdown_lines.append(
                f"  [red]◼[/red] Memory files: {self._format_number(memory_tokens)} tokens ({mem_percent:.1f}%)"
            )

        # Messages breakdown
        user_tokens = messages_breakdown.get("user", 0)
        assistant_tokens = messages_breakdown.get("assistant", 0)
        tool_calls_tokens = messages_breakdown.get("tool_calls", 0)
        tool_results_tokens = messages_breakdown.get("tool_results", 0)

        # User prompts
        if user_tokens > 0:
            user_percent = (user_tokens / max_tokens * 100) if max_tokens > 0 else 0
            breakdown_lines.append(
                f"  [blue]◼[/blue] User prompts: {self._format_number(user_tokens)} tokens ({user_percent:.1f}%)"
            )

        # Assistant responses
        if assistant_tokens > 0:
            asst_percent = (assistant_tokens / max_tokens * 100) if max_tokens > 0 else 0
            breakdown_lines.append(
                f"  [green]◼[/green] Assistant responses: {self._format_number(assistant_tokens)} tokens ({asst_percent:.1f}%)"
            )

        # Tool calls
        if tool_calls_tokens > 0:
            tc_percent = (tool_calls_tokens / max_tokens * 100) if max_tokens > 0 else 0
            breakdown_lines.append(
                f"  [yellow]◼[/yellow] Tool calls: {self._format_number(tool_calls_tokens)} tokens ({tc_percent:.1f}%)"
            )

        # Tool results
        if tool_results_tokens > 0:
            tr_percent = (tool_results_tokens / max_tokens * 100) if max_tokens > 0 else 0
            breakdown_lines.append(
                f"  [magenta]◼[/magenta] Tool results: {self._format_number(tool_results_tokens)} tokens ({tr_percent:.1f}%)"
            )

        # Free space
        free_percent = (free_space / max_tokens * 100) if max_tokens > 0 else 0
        breakdown_lines.append(
            f"  [dim]◻[/dim] Free space: {self._format_number(free_space)} ({free_percent:.1f}%)"
        )

        # Print breakdown
        _get_console().print("\n".join(breakdown_lines))
        _get_console().print()

    def _create_context_grid(self, used_tokens: int, max_tokens: int, categories: List[tuple]) -> str:
        """Create a visual grid representation of context usage with colors and CAI logo."""
        # Grid dimensions
        grid_width = 40
        grid_height = 10
        total_blocks = grid_width * grid_height

        # CAI logo pattern (1 = filled, 0 = empty)
        # C       A        I
        cai_logo = [
            [0, 1, 1, 1, 1, 0, 0, 0, 1, 1, 1, 1, 0, 0, 0, 1, 1, 1, 0],
            [1, 1, 0, 0, 1, 1, 0, 1, 1, 0, 0, 1, 1, 0, 0, 0, 1, 0, 0],
            [1, 1, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 0, 0, 0, 1, 0, 0],
            [1, 1, 0, 0, 1, 1, 0, 1, 1, 0, 0, 1, 1, 0, 0, 0, 1, 0, 0],
            [0, 1, 1, 1, 1, 0, 0, 1, 1, 0, 0, 1, 1, 0, 0, 1, 1, 1, 0],
        ]

        # Calculate starting position to center CAI
        cai_height = len(cai_logo)
        cai_width = len(cai_logo[0])
        start_row = (grid_height - cai_height) // 2
        start_col = (grid_width - cai_width) // 2

        # Calculate how many blocks each category gets
        usage_ratio = used_tokens / max_tokens if max_tokens > 0 else 0
        filled_blocks = int(total_blocks * usage_ratio)

        # Distribute blocks to categories proportionally
        category_blocks = []
        remaining_blocks = filled_blocks
        total_category_tokens = sum(cat[1] for cat in categories)

        for i, (name, tokens, color) in enumerate(categories):
            if i == len(categories) - 1:
                # Last category gets remaining blocks
                blocks = remaining_blocks
            else:
                ratio = tokens / total_category_tokens if total_category_tokens > 0 else 0
                blocks = int(filled_blocks * ratio)
                remaining_blocks -= blocks
            category_blocks.append((name, blocks, color))

        # Build grid
        grid_lines = []
        block_index = 0
        current_category_idx = 0
        current_category_blocks = 0

        for row in range(grid_height):
            line = ""
            for col in range(grid_width):
                # Check if this position is part of CAI logo
                in_logo = False
                logo_filled = False

                if start_row <= row < start_row + cai_height:
                    logo_row = row - start_row
                    if start_col <= col < start_col + cai_width:
                        logo_col = col - start_col
                        if logo_col < cai_width and logo_row < cai_height:
                            in_logo = True
                            logo_filled = cai_logo[logo_row][logo_col] == 1

                # Render the block
                if in_logo and logo_filled:
                    # This is part of the CAI logo
                    if block_index < filled_blocks and current_category_idx < len(category_blocks):
                        # Logo is filled with category color
                        cat_name, cat_blocks, cat_color = category_blocks[current_category_idx]
                        line += f"[{cat_color}]█[/{cat_color}]"

                        current_category_blocks += 1
                        if current_category_blocks >= cat_blocks:
                            current_category_idx += 1
                            current_category_blocks = 0
                        block_index += 1
                    else:
                        # Logo outline in cyan when no usage
                        line += "[cyan]█[/cyan]"

                elif not in_logo:
                    # Outside logo
                    if block_index < filled_blocks and current_category_idx < len(category_blocks):
                        # Get current category
                        cat_name, cat_blocks, cat_color = category_blocks[current_category_idx]
                        line += f"[{cat_color}]◼[/{cat_color}]"

                        current_category_blocks += 1
                        if current_category_blocks >= cat_blocks:
                            current_category_idx += 1
                            current_category_blocks = 0
                        block_index += 1
                    else:
                        line += "[dim]◻[/dim]"
                else:
                    # Inside logo area but not filled (space)
                    line += " "

            grid_lines.append(line)

        return "\n".join(grid_lines)

    def _format_number(self, num: int) -> str:
        """Format a number with k suffix for thousands."""
        if num >= 1000:
            return f"{num / 1000:.1f}k"
        return str(num)


# Register the command
register_command(ContextCommand())
