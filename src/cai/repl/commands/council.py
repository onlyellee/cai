"""
Council command for CAI CLI - Execute prompts using LLM Council.

This command allows users to get responses from multiple LLMs that
evaluate each other's work before producing a final synthesized answer.
"""

import asyncio
import os
from typing import List, Optional

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from cai.repl.commands.base import Command, register_command

console = Console()


class CouncilCommand(Command):
    """Command for executing prompts using LLM Council."""

    def __init__(self):
        """Initialize the council command."""
        super().__init__(
            name="/council",
            description="Execute a prompt using LLM Council (multi-model consensus)",
            aliases=["/c"],
        )

    def show_usage(self) -> None:
        """Show detailed usage information for the council command."""
        # Get current council configuration
        council_models = os.getenv("CAI_COUNCIL", "gpt-4o,gpt-4o-mini")
        models_list = [m.strip() for m in council_models.split(",") if m.strip()]

        # Get chairman model info from active agent
        chairman_info = "Active agent's model"
        try:
            from cai.sdk.agents.simple_agent_manager import AGENT_MANAGER
            current_agent = AGENT_MANAGER.get_active_agent()
            if current_agent:
                model_name = current_agent.model
                if not isinstance(model_name, str):
                    model_name = getattr(model_name, 'model', None) or getattr(model_name, 'name', None) or str(model_name)
                chairman_info = f"{current_agent.name} ({model_name})"
        except Exception:
            pass

        help_text = f"""## /council - LLM Council Multi-Model Consensus

**Usage:** `/council <prompt>`

**Description:**
Execute a prompt using multiple LLMs that evaluate each other's responses
before the chairman (active agent) synthesizes a final answer.

**How it works:**
1. **Stage 1**: Council members independently respond to your prompt
2. **Stage 2**: Each member ranks and evaluates all responses
3. **Stage 3**: The chairman (your active agent) synthesizes the best answer

**Current Configuration:**

| Setting | Value |
|---------|-------|
| **Chairman** | {chairman_info} |
| **Council Models** | {', '.join(models_list)} |

**Environment Variables:**
- `CAI_COUNCIL` - Comma-separated list of models for council members
- `CAI_COUNCIL_DEBUG` - Set to "1" for verbose debug output

**Examples:**
```
/council What are the best practices for securing a REST API?
/council Explain quantum computing in simple terms
/c How should I structure a microservices architecture?
```

**Alias:** `/c`
"""
        console.print(Markdown(help_text))

    def handle(self, args: Optional[List[str]] = None) -> bool:
        """Handle the council command - execute prompt using council.

        Args:
            args: The prompt as a list of words

        Returns:
            True if the command was handled successfully
        """
        if not args:
            self.show_usage()
            return True

        # Join args to form the full prompt
        prompt = " ".join(args)

        try:
            # Import council module - use agent-based version
            from cai.council import run_full_council_agents, CouncilAgentConfig

            # Get current active agent to use as base
            current_agent = None
            try:
                from cai.sdk.agents.simple_agent_manager import AGENT_MANAGER

                current_agent = AGENT_MANAGER.get_active_agent()
                if not current_agent:
                    console.print(
                        "[yellow]No active agent found. Please load an agent first with /agent[/yellow]"
                    )
                    return False
            except Exception as e:
                console.print(
                    f"[red]Could not get active agent: {e}[/red]"
                )
                return False

            # Get conversation history for context
            # Use the agent's model history directly for the most up-to-date context
            conversation_history = None
            debug = os.getenv("CAI_COUNCIL_DEBUG", "").lower() in ("1", "true", "yes")
            try:
                if hasattr(current_agent, 'model') and hasattr(current_agent.model, 'message_history'):
                    # Use the live history reference from the agent's model
                    conversation_history = current_agent.model.message_history
                    if debug:
                        console.print(f"[dim]  Context: {len(conversation_history)} messages from agent model[/dim]")
                else:
                    # Fallback to AGENT_MANAGER
                    history = AGENT_MANAGER.get_message_history(current_agent.name)
                    if history:
                        conversation_history = history
                        if debug:
                            console.print(f"[dim]  Context: {len(conversation_history)} messages from AGENT_MANAGER[/dim]")
            except Exception:
                pass  # History not available, proceed without it

            # Execute the agent-based council
            stage1_results, stage2_results, stage3_result, metadata = asyncio.run(
                run_full_council_agents(
                    base_agent=current_agent,
                    user_query=prompt,
                    config=None,  # Will load from environment
                    conversation_history=conversation_history,
                )
            )

            # Note: Council costs are already added to session total in council_agents.py
            # before Runner.run() is called, so the chairman's response panel shows correct totals

            # Display results
            self._display_results(
                prompt, stage1_results, stage2_results, stage3_result, metadata, current_agent
            )

            return True

        except ImportError as e:
            console.print(
                f"[red]Error: Council module not available: {e}[/red]\n"
                "[yellow]Make sure the council module is properly installed.[/yellow]"
            )
            return False
        except Exception as e:
            console.print(f"[red]Error running council: {e}[/red]")
            import traceback
            console.print(f"[dim]{traceback.format_exc()}[/dim]")
            return False

    def _display_results(
        self,
        prompt: str,
        stage1_results: List,
        stage2_results: List,
        stage3_result: dict,
        metadata: dict,
        base_agent,
    ):
        """Display council results in a formatted way.

        Note: The agent's response is already shown by Runner.run(),
        and rankings/costs are shown in the council panel during deliberation.
        This method is kept for compatibility but no longer displays anything
        to avoid redundant output.

        Args:
            prompt: The original prompt
            stage1_results: Stage 1 results (individual responses)
            stage2_results: Stage 2 results (rankings)
            stage3_result: Stage 3 result (final synthesis)
            metadata: Additional metadata (aggregate rankings, etc.)
            base_agent: The base agent used for the council
        """
        # All display is now handled by the council panel and Runner.run()
        # No additional output needed here
        pass


# Register the command when this module is imported
council_cmd = CouncilCommand()
register_command(council_cmd)
