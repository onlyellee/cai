#!/usr/bin/env python3
"""
Patch v0.7.4 installed CAI files with i18n support.
Adds 'from cai.i18n import t' imports and replaces English strings with t() calls.
"""
import re
import sys
import os

SITE_CAI = "/Users/inteligence-q/.local/python312/python/lib/python3.12/site-packages/cai"

def add_import(content, after_pattern="import"):
    """Add i18n import after the last standard import line."""
    if "from cai.i18n import t" in content:
        return content

    lines = content.split('\n')
    insert_idx = 0

    # Find last import line
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith('import ') or stripped.startswith('from '):
            insert_idx = i + 1

    lines.insert(insert_idx, 'from cai.i18n import t')
    return '\n'.join(lines)


def patch_file(filepath, replacements):
    """Apply string replacements to a file."""
    rel = os.path.relpath(filepath, SITE_CAI)
    full = os.path.join(SITE_CAI, filepath) if not filepath.startswith('/') else filepath

    if not os.path.exists(full):
        print(f"  SKIP {rel}: not found")
        return 0

    with open(full, 'r') as f:
        content = f.read()

    original = content

    # Add import
    content = add_import(content)

    # Apply replacements
    count = 0
    for old, new in replacements:
        if old in content:
            content = content.replace(old, new, 1)
            count += 1

    if content != original:
        with open(full, 'w') as f:
            f.write(content)
        print(f"  OK   {rel}: {count} replacements")
    else:
        print(f"  SKIP {rel}: no changes needed")

    return count


# ============================================================
# BANNER.PY patches
# ============================================================
banner_patches = [
    ('Bug bounty-ready AI', "{t_banner_subtitle}"),  # placeholder, handled specially
]

def patch_banner():
    fp = os.path.join(SITE_CAI, "repl/ui/banner.py")
    with open(fp, 'r') as f:
        content = f.read()

    original = content
    content = add_import(content)
    count = 0

    # Simple text replacements in banner.py
    subs = {
        'Bug bounty-ready AI': "' + t('banner_subtitle') + '",
        'title="Quick Tips"': "title=t('welcome_tips_title')",
        'title="[bold blue]CAI Features[/bold blue]"': """title=f"[bold blue]{t('capabilities_title')}[/bold blue]" """.strip(),
        '"AI Models"': "t('capabilities_ai_models')",
        '"Supported AI models including GPT-4, Claude, Llama"': "t('capabilities_ai_models_desc')",
        '"Agents"': "t('capabilities_agents')",
        '"Specialized AI agents for different cybersecurity tasks"': "t('capabilities_agents_desc')",

        'title="[bold yellow]🤖 Available Security Agents[/bold yellow]"': """title=f"[bold yellow]🤖 {t('agent_overview_title')}[/bold yellow]" """.strip(),

        # Quick guide strings
        '("CAI Command Reference", "bold cyan underline")': f"""(t('guide_command_ref'), "bold cyan underline")""",
        '("AGENT MANAGEMENT", "bold yellow")': f"""(t('guide_agent_mgmt'), "bold yellow")""",
        '("MEMORY & HISTORY", "bold yellow")': f"""(t('guide_memory_history'), "bold yellow")""",
        '("ENVIRONMENT", "bold yellow")': f"""(t('guide_environment'), "bold yellow")""",
        '("TOOLS & INTEGRATION", "bold yellow")': f"""(t('guide_tools_integration'), "bold yellow")""",
        '("Quick Start Workflows", "bold cyan underline")': f"""(t('guide_quick_start_workflows'), "bold cyan underline")""",

        # Shortcuts
        '("QUICK SHORTCUTS", "bold yellow")': f"""(t('guide_shortcuts'), "bold yellow")""",

        # Workflow titles
        '"🎯 CTF Challenge"': f"""f"🎯 {{t('guide_ctf_challenge')}}" """.strip(),
        '"🐛 Bug Bounty"': f"""f"🐛 {{t('guide_bug_bounty')}}" """.strip(),
        '"🔍 Parallel Recon"': f"""f"🔍 {{t('guide_parallel_recon')}}" """.strip(),
        '"🛠️ MCP Tools Integration"': f"""f"🛠️ {{t('guide_mcp_tools')}}" """.strip(),

        # Pro tips
        '("💡 Pro Tips:", "bold yellow")': f"""(f"💡 {{t('guide_pro_tips')}}", "bold yellow")""",

        # Ollama
        'title="[bold yellow]Ollama Configuration[/bold yellow]"': """title=f"[bold yellow]{t('guide_ollama_title')}[/bold yellow]" """.strip(),

        # Alias1
        'title="[bold yellow]🛡️ Alias1 - best model for cybersecurity [/bold yellow]"': """title=f"[bold yellow]🛡️ {t('guide_alias1_title')} [/bold yellow]" """.strip(),

        # Environment Variables:
        '("Environment Variables:", "bold yellow")': f"""(f"{{t('guide_env_vars')}}", "bold yellow")""",
    }

    for old, new in subs.items():
        if old in content:
            content = content.replace(old, new, 1)
            count += 1

    if content != original:
        with open(fp, 'w') as f:
            f.write(content)
        print(f"  OK   repl/ui/banner.py: {count} replacements")
    else:
        print(f"  SKIP repl/ui/banner.py: no changes")
    return count


# ============================================================
# TOOLBAR.PY patches
# ============================================================
def patch_toolbar():
    fp = os.path.join(SITE_CAI, "repl/ui/toolbar.py")
    with open(fp, 'r') as f:
        content = f.read()
    original = content
    content = add_import(content)
    count = 0

    subs = {
        """active_env_name, active_env_icon, active_env_color = "Host System\"""": """active_env_name, active_env_icon, active_env_color = t('toolbar_host_system')""",
        """'Loading system information...'""": """t('toolbar_loading')""",
        '''"(stopped)"''': """t('toolbar_stopped')""",
    }

    for old, new in subs.items():
        if old in content:
            content = content.replace(old, new, 1)
            count += 1

    # Also try alternate patterns
    alt_subs = {
        'active_env_name, active_env_icon, active_env_color = "Host System"': "active_env_name, active_env_icon, active_env_color = t('toolbar_host_system')",
    }
    for old, new in alt_subs.items():
        if old in content:
            content = content.replace(old, new, 1)
            count += 1

    if content != original:
        with open(fp, 'w') as f:
            f.write(content)
        print(f"  OK   repl/ui/toolbar.py: {count} replacements")
    else:
        print(f"  SKIP repl/ui/toolbar.py: no changes")
    return count


# ============================================================
# CLI.PY patches
# ============================================================
def patch_cli():
    fp = os.path.join(SITE_CAI, "cli.py")
    with open(fp, 'r') as f:
        content = f.read()
    original = content
    content = add_import(content)
    count = 0

    subs = {
        '"Turn limit increased. You can now continue using CAI."': "t('turn_limit_increased')",
        '"SECURITY GUARDRAIL TRIGGERED"': "t('guardrail_triggered')",
        '"INPUT SECURITY GUARDRAIL TRIGGERED"': "t('guardrail_input_triggered')",
        '"The agent\'s output was blocked for security reasons."': "t('guardrail_output_blocked')",
        '"Your input was blocked for security reasons."': "t('guardrail_input_blocked')",
        '"You can continue the conversation with a different request."': "t('guardrail_continue')",
        '"Please rephrase your request or try a different approach."': "t('guardrail_rephrase')",
        '"Session Summary"': "t('session_summary_title')",
        '"Operation interrupted by user (Keyboard Interrupt during shutdown)"': "t('operation_interrupted')",
    }

    for old, new in subs.items():
        while old in content:
            content = content.replace(old, new, 1)
            count += 1

    # f-string replacements
    fsubs = {
        'f"Error: Maximum turn limit ({max_turns}) reached."': "t('error_max_turns', max_turns=max_turns)",
        'f"Log file: {filename}"': "t('log_file', filename=filename)",
    }
    for old, new in fsubs.items():
        if old in content:
            content = content.replace(old, new, 1)
            count += 1

    if content != original:
        with open(fp, 'w') as f:
            f.write(content)
        print(f"  OK   cli.py: {count} replacements")
    else:
        print(f"  SKIP cli.py: no changes")
    return count


# ============================================================
# UTIL.PY patches
# ============================================================
def patch_util():
    fp = os.path.join(SITE_CAI, "util.py")
    with open(fp, 'r') as f:
        content = f.read()
    original = content
    content = add_import(content)
    count = 0

    subs = {
        '"Tool Call:"': "t('tool_call')",
        '"Name:"': "t('tool_name')",
        '"Args:"': "t('tool_args')",
        '"Output:"': "t('tool_output')",
        '"No agent provided to visualize."': "t('no_agent_visualize')",
        '"Current Agent"': "t('current_agent')",
        '"Tools"': "t('tools_header')",
    }

    for old, new in subs.items():
        if old in content:
            content = content.replace(old, new, 1)
            count += 1

    if content != original:
        with open(fp, 'w') as f:
            f.write(content)
        print(f"  OK   util.py: {count} replacements")
    else:
        print(f"  SKIP util.py: no changes")
    return count


# ============================================================
# REPL COMMANDS patches
# ============================================================
def patch_repl_commands():
    total = 0

    # config.py
    total += patch_file(os.path.join(SITE_CAI, "repl/commands/config.py"), [
        ('"Environment Variables"', "t('config_env_vars')"),
        ('"Usage: /config set <number> <value> to configure a variable"', "t('config_usage_set')"),
        ('"Usage: /config get <number>"', "t('config_usage_get')"),
        ('"No CAI_ or CTF_ environment variables found"', "t('config_no_env_vars')"),
    ])

    # help.py
    total += patch_file(os.path.join(SITE_CAI, "repl/commands/help.py"), [
        ('"Available Commands"', "t('help_available_commands')"),
        ('"Usage"', "t('help_usage')"),
        ('"Examples"', "t('help_examples')"),
        ('"Options"', "t('help_options')"),
        ('"CAI Quick Reference"', "t('help_quick_ref')"),
    ])

    # cost.py
    total += patch_file(os.path.join(SITE_CAI, "repl/commands/cost.py"), [
        ('"CAI Usage Cost Summary"', "t('cost_summary_title')"),
        ('"Current Session"', "t('cost_current_session')"),
        ('"Global Usage (All Time)"', "t('cost_global_usage')"),
        ('"Model Usage Statistics"', "t('cost_model_usage_title')"),
        ('"Daily Usage Statistics"', "t('cost_daily_title')"),
    ])

    # model.py
    total += patch_file(os.path.join(SITE_CAI, "repl/commands/model.py"), [
        ('"Active Model"', "t('model_active_title')"),
        ('"Available Models"', "t('model_available')"),
        ('"Model Changed"', "t('model_changed_title')"),
        ('"All Available Models"', "t('model_show_all_title')"),
    ])

    # agent.py
    total += patch_file(os.path.join(SITE_CAI, "repl/commands/agent.py"), [
        ('"Available Agents"', "t('agent_table_available')"),
        ('"Available Parallel Patterns"', "t('agent_table_parallel')"),
        ('"Current Configuration"', "t('agent_current_config')"),
    ])

    # memory.py
    total += patch_file(os.path.join(SITE_CAI, "repl/commands/memory.py"), [
        ('"Memory Management Control Panel"', "t('memory_control_panel')"),
        ('"Stored Memories"', "t('memory_stored')"),
        ('"Applied Memories"', "t('memory_applied')"),
        ('"Memory Status"', "t('memory_status_title')"),
    ])

    # history.py
    total += patch_file(os.path.join(SITE_CAI, "repl/commands/history.py"), [
        ('"Agent History Control Panel"', "t('history_control_panel')"),
        ('"All Agent Conversations"', "t('history_all_title')"),
    ])

    # quickstart.py
    total += patch_file(os.path.join(SITE_CAI, "repl/commands/quickstart.py"), [
        ('"CAI Quickstart"', "t('qs_title')"),
        ('"Welcome to CAI (Cybersecurity AI)!"', "t('qs_welcome')"),
        ('"Ready to Go!"', "t('qs_ready_title')"),
    ])

    # env.py
    total += patch_file(os.path.join(SITE_CAI, "repl/commands/env.py"), [
        ('"Environment Variables"', "t('env_title')"),
        ('"No CAI_ or CTF_ environment variables found"', "t('env_no_vars')"),
    ])

    # merge.py
    total += patch_file(os.path.join(SITE_CAI, "repl/commands/merge.py"), [
        ('"Merge Command Help"', "t('merge_help_title')"),
    ])

    return total


# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":
    print("Patching CAI v0.7.4 with Korean i18n...\n")
    total = 0

    print("[Banner & Toolbar]")
    total += patch_banner()
    total += patch_toolbar()

    print("\n[CLI & Util]")
    total += patch_cli()
    total += patch_util()

    print("\n[REPL Commands]")
    total += patch_repl_commands()

    print(f"\nDone! {total} total replacements applied.")
    print("Set CAI_LANGUAGE=ko to activate Korean mode.")
