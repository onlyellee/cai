"""
CAI Terminal - Clean architecture implementation with modular components
"""

import asyncio
import os
import re
import time
from typing import Optional, Tuple

from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal
from textual.reactive import reactive
from textual.widgets import Footer, Input, ListView, Button, Static, Label, TabbedContent, TabPane
from textual.theme import Theme as TextualTheme
from textual.events import Unmount

# Import theme system
from cai.tui.theme import ThemeManager, THEMES
from cai.tui.config import TUIConfig
from cai.config_loader import (
    AgentsConfigError,
    extract_agent_definitions,
    load_agents_config,
)

# Simple recursion prevention
class RecursionGuard:
    def __init__(self, max_attempts=3):
        self.attempts = {}
        self.max_attempts = max_attempts
    
    def can_proceed(self, key):
        if key not in self.attempts:
            self.attempts[key] = 0
        if self.attempts[key] >= self.max_attempts:
            return False
        self.attempts[key] += 1
        return True

_recursion_guard = RecursionGuard()

# Import UI components
from cai.tui.components.stable_grid import StableTerminalGrid
# from cai.tui.components.enhanced_terminal import ENHANCED_TERMINAL_CSS
from cai.tui.components.universal_terminal import UniversalTerminal
from cai.tui.components.sidebar import Sidebar, AgentDoubleClicked, TeamSelected
from cai.tui.components.autocomplete_input import AutocompleteInput
from cai.tui.components.prompt_input import PromptInput
from cai.tui.components.command_handler import CommandHandler
from cai.tui.components.agent_manager import AgentManager
from pathlib import Path
from cai.tui.components.agent_selector_panel import (
    AgentSelectorPanel, 
    AgentSelectionConfirmed,
    AgentSelectionCancelled
)
from cai.tui.components.agent_creator_panel import (
    AgentCreatorPanel,
    AgentCreationConfirmed,
    AgentCreationCancelled
)
from cai.tui.components.session_manager_panel import SessionManagerPanel
from cai.tui.components.info_status_bar import InfoStatusBar
from cai.repl.commands.parallel import ParallelConfig
from cai.i18n import t
from cai.sdk.agents.models.openai_chatcompletions_integration import (
    integrate_openai_chatcompletions_display,
)
from cai.sdk.agents.simple_agent_manager import AGENT_MANAGER
# Removed: Terminal prompt bar was blocking main input
# from cai.tui.components.terminal_prompt_bar import TerminalPromptBar
from cai.tui.components.graph_canvas import CTRCanvas
from cai.tui.core.terminal_console import get_terminal_console, get_terminal_output
from cai.tui.core.session_manager import SessionManager
from cai.tui.core.prompt_queue import PROMPT_QUEUE
# Removed: TerminalPromptSubmitted from deleted messages.py
from cai.util import get_config_dir

# Enable asyncio context preservation in TUI without patch modules
from cai.tui.display.context_preservation import enable_task_context_propagation
enable_task_context_propagation()

# Performance optimizations are integrated in UniversalTerminal (throttling, summarized mode)

# Apply comprehensive anti-freeze fix to prevent UI blocking
# Disabled for now - causing TUI startup issues
# try:
#     from cai.tui.fixes.comprehensive_anti_freeze import apply_comprehensive_anti_freeze
#     apply_comprehensive_anti_freeze()
# except Exception as e:
#     print(f"[Warning] Could not apply anti-freeze fix: {e}")

# Import CAI core
from cai.repl.commands.parallel import PARALLEL_CONFIGS

# NOTE: Streaming fix has been applied directly to StreamingDisplay class
# No need for patches anymore - progressive streaming is built-in
# try:
#     from cai.tui.fixes.ultimate_streaming_solution import apply_ultimate_streaming_solution
#     apply_ultimate_streaming_solution()
# except Exception as e:
#     print(f"[Warning] Could not apply streaming fix: {e}")

# Compose issue has been fixed in UniversalTerminal directly


# No global patches required; context propagation is enabled above


# Initialize theme system at module level

def is_tui_mode() -> bool:
    """Check if we're running in TUI mode."""
    return os.getenv("CAI_TUI_MODE") == "true"
_tui_config = TUIConfig()
_theme_manager = ThemeManager()

# Get theme from environment or default to a dark theme (force dark by default)
_theme_name = os.getenv("CAI_THEME") or "tokyo-night"
if _theme_name in THEMES:
    _theme_manager.set_theme(_theme_name)

# Generate theme CSS variables
_theme_vars = _theme_manager.get_theme_css()


class CAITerminal(App):
    """Main CAI Terminal application with clean architecture"""

    # Instance attributes
    current_mode = reactive("single")
    current_view = reactive("terminal")  # "terminal" or "ctr"
    sidebar_visible = reactive(True)  # Track sidebar visibility for button positioning
    
    # Generate CSS with theme variables
    CSS = """
    /* MINIMAL CSS FOR DEBUGGING TAB ISSUE */
    
    Screen {
        background: $background;
    }
    
    /* Global Screen Styling */
    Screen {
        background: $background;
        /* Temporarily disabled color to debug tab issue
        color: $text;
        */
        /* Temporarily disabled grid layout
        layout: grid;
        grid-size: 1 3;
        grid-rows: 1fr auto auto;
        */
    }
    
    /* Force all text to be visible */
    /* * {
        text-opacity: 1.0;
    } */
    
    /* Ensure button text is visible */
    Button { text-opacity: 1.0 !important; }
    
    Button Label {
        text-opacity: 1.0 !important;
    }
    
    /* Force button label visibility globally */
    Button .button--label {
        color: $text !important;
        text-opacity: 1.0 !important;
    }
    
    /* Fix button content visibility */
    Sidebar Button.agent-item {
        content-align: left middle !important;
    }
    
    Sidebar Button.agent-item > * {
        visibility: visible !important;
        display: block !important;
    }
    
    /* Force text color for all button states */
    Sidebar Button.agent-item,
    Sidebar Button.agent-item:hover,
    Sidebar Button.agent-item:focus {
        text-opacity: 1.0 !important;
    }
    
    /* Ensure the button renders its label correctly */
    Sidebar Button.agent-item > Label,
    Sidebar Button.agent-item > Static { color: $text !important; text-opacity: 1.0 !important; visibility: visible !important; }
    
    /* Debug: Force specific text rendering for buttons */
    Sidebar Button.agent-item {
        text-style: none !important;
    }
    
    /* Ensure the button content container is visible */
    Sidebar Button.agent-item > * > * {
        color: $text !important;
        text-opacity: 1.0 !important;
    }
    
    /* Modern Scrollbar Design */
    ScrollBar {
        background: $surface;
        color: $primary 30%;
    }
    
    ScrollBar:hover {
        color: $primary;
    }
    
    /* Streaming Message Styles - Refined */
    StreamingMessage,
    IntegratedStreamingMessage {
        background: $surface;
        padding: 1 2;
        margin: 1 2;
        border: none;
        border-left: solid $primary 30%;
    }
    
    InlineStreamingMessage {
        background: transparent;
        padding: 0;
        margin: 0;
    }
    
    /* Terminal Output Area - Enhanced */
    .terminal-richlog {
        background: $surface;
        padding: 1 2;
        color: $text;
    }
    
    .terminal-content {
        background: $background;
        border: none;
    }
    
    /* Layout Containers - Modern Design */
    #app-layout {
        background: $background;
        width: 100%;
        height: 100%;
        layout: horizontal;
        padding: 0;
        margin: 0;
    }
    
    #main-container {
        background: $background;
        padding: 0;
        margin: 0;
        width: 100%;
        height: 100%;
    }
    
    
    /* TabbedContent Styling */
    TabbedContent {
        width: 100%;
        height: 100%;
    }
    
    /* Tab Bar - Fix text visibility issue */
    Tabs {
        height: 3;
        dock: top;
        background: $surface;
    }
    
    /* Default tab style with visible text */
    Tab {
        padding: 0 3;
        text-align: center;
        min-width: 12;
        color: #cccccc !important;
        text-opacity: 1.0 !important;
    }
    
    /* Active tab override */
    Tab.-active {
        color: white !important;
        background: #0178d4 !important;
        text-opacity: 1.0 !important;
    }
    
    /* Tab Bar container styling */
    #main-tabs Tabs {
        background: transparent;
        height: 3;
        width: 100%;
    }
    
    /* Main tabs - exact copy of sidebar approach with different colors */
    #main-tabs Tab {
        height: 3;
        max-height: 3;
        background: transparent;
        padding: 0 2;
        margin: 0 1 0 0;
        border: none;
        color: #ffffff !important;
        text-opacity: 1.0 !important;
        content-align: center middle;
        text-align: center;
    }
    
    /* Active tab for main container */
    #main-tabs Tab.-active {
        color: #ffffff !important;
        background: #0178d4;
        text-style: bold;
        text-opacity: 1.0 !important;
        border: none;
        margin: 0 1 0 0;
        height: 3;
    }
    
    /* Hover state */
    #main-tabs Tab:hover {
        color: #ffffff !important;
        background: rgba(1, 120, 212, 0.3);
        text-opacity: 1.0 !important;
        border: none;
    }
    
    /* Force all tab text to be visible and centered */
    #main-tabs Tab * {
        color: #ffffff !important;
        text-opacity: 1.0 !important;
        background: transparent !important;
        text-align: center !important;
        width: 100%;
        height: 100%;
        content-align: center middle;
    }
    
    #main-tabs Tab.-active * {
        color: #ffffff !important;
        text-opacity: 1.0 !important;
    }
    
    #main-tabs Tab:hover * {
        color: #ffffff !important;
        text-opacity: 1.0 !important;
    }
    
    /* Ensure tab labels are properly displayed */
    #main-tabs Tab Label {
        color: #ffffff !important;
        text-opacity: 1.0 !important;
        background: transparent !important;
        width: 100%;
        height: 100%;
        content-align: center middle;
        text-align: center;
    }
    
    #main-tabs Tab.-active Label {
        color: #ffffff !important;
        text-opacity: 1.0 !important;
    }
    
    #main-tabs Tab:hover Label {
        color: #ffffff !important;
        text-opacity: 1.0 !important;
    }
    
    /* Content Switcher */
    ContentSwitcher {
        width: 100%;
        height: 100%;
        background: $background;
    }
    
    /* Tab Panes */
    TabPane {
        width: 100%;
        height: 100%;
        padding: 0;
        layout: vertical;
    }
    
    /* Terminal Tab Content */
    #terminal {
        width: 100%;
        height: 100%;
    }
    
    #terminal StableTerminalGrid {
        width: 100%;
        height: 1fr;
    }
    
    #terminal InfoStatusBar {
        height: 2;
        dock: bottom;
    }
    
    #terminal #input-area {
        height: 3;
        dock: bottom;
        background: $surface;
        border-top: solid $primary 30%;
        padding: 0 2;
    }
    
    /* CTR Tab Content */
    #ctr {
        width: 100%;
        height: 100%;
    }
    
    #ctr CTRCanvas {
        width: 100%;
        height: 100%;
    }
    
    /* Ensure info status bar is visible */
    #info-status-bar {
        height: 2;
        width: 100%;
        min-height: 2;
        max-height: 2;
        dock: bottom;
    }
    
    /* Remove gaps between terminals for unified action bar */
    StableTerminalGrid.layout-triple {
        grid-gutter: 0 0;
    }
    
    /* Compact layout for 4+ terminals */
    StableTerminalGrid.many-terminals {
        grid-gutter: 0 0;
        padding: 0;
    }
    
    /* Adjust terminal content area for 4+ terminals */
    .many-terminals UniversalTerminal {
        padding: 0;
    }
    
    /* Smaller info bar for 4+ terminals */
    .many-terminals InfoStatusBar {
        height: 1;
        min-height: 1;
    }
    
    /* Hide scrollbars in many-terminals mode but NOT ActualActionBar */
    .many-terminals ScrollBar {
        display: none !important;
    }
    
    /* Don't hide ActualActionBar which extends VerticalScroll */
    .many-terminals ActualActionBar {
        display: block !important;
    }
    
    
    /* Modern Sidebar Design */
    #sidebar {
        width: 32;
        background: $surface;
        border-right: solid $primary 50%;
        dock: left;
        display: none;
        padding: 0;
    }
    
    #sidebar.sidebar-visible {
        display: block;
    }
    
    .sidebar-header {
        height: 3;
        background: $surface;
        color: $primary;
        padding: 0 1;
        text-align: center;
        text-style: bold;
        border-bottom: solid $primary 50%;
        margin: 0;
    }
    
    .sidebar-list {
        height: 1fr;
        background: $surface;
        color: $text;
        padding: 0;
        margin: 0;
    }
    
    /* Modern List Item Styling */
    ListItem {
        padding: 1 2;
        margin: 0;
        background: $surface;
        border: none;
        border-bottom: tall $primary 10%;
        color: $text;
    }
    
    ListItem Label {
        color: $text !important;
        background: transparent !important;
    }
    
    ListItem:hover {
        background: $surface-lighten-2;
        border: none;
        border-bottom: tall $primary 10%;
        color: $secondary;
    }
    
    ListItem:hover Label {
        color: $secondary !important;
    }
    
    ListItem.-selected,
    ListItem.--highlight {
        background: $surface-lighten-2;
        border: none;
        border-left: thick $primary;
        border-bottom: tall $primary 10%;
        color: $primary;
        text-style: bold;
    }
    
    ListItem.-selected Label,
    ListItem.--highlight Label {
        color: $primary !important;
    }
    
    /* Sidebar Content Container */
    #sidebar-content {
        height: 100%;
        background: $surface;
        padding: 0;
        margin: 0;
    }
    
    /* Tabbed Content Styles for Sidebar */
    TabbedContent {
        background: $surface;
        height: 100%;
        border: none;
    }
    
    TabbedContent > ContentTabs {
        background: $surface;
        height: 3;
        padding: 0;
    }
    
    /* Minimal tab styling to avoid conflicts */
    /* Let Textual handle most of the styling */
    
    /* Only set padding and sizing */
    TabbedContent Tab {
        padding: 1 2;
        min-width: 12;
    }
    
    TabbedContent > TabContent {
        background: $surface;
        padding: 0;
        height: 1fr;
    }
    
    /* Sidebar Scroll Containers */
    VerticalScroll.sidebar-list,
    VerticalScroll.queue-list,
    VerticalScroll.state-list {
        background: $surface;
        padding: 0;
        margin: 0;
    }
    
    /* Override sidebar ListItem styles to ensure text visibility */
    Sidebar ListItem {
        background: $surface !important;
    }
    
    Sidebar ListItem Label {
        color: $secondary !important;
        text-opacity: 1.0 !important;
        background: transparent !important;
    }
    
    /* Sidebar separators */
    Sidebar .agent-separator {
        width: 100% !important;
        height: 0 !important;
        margin: 0 !important;
        border: none !important;
        background: transparent !important;
    }
    
    /* Override sidebar list styles */
    Sidebar .sidebar-list {
        background: $surface !important;
        padding: 0 !important;
        margin: 0 !important;
    }
    
    Sidebar .queue-list {
        background: $surface !important;
        padding: 0 !important;
        margin: 0 !important;
    }
    
    Sidebar .state-list {
        background: $surface !important;
        padding: 0 !important;
        margin: 0 !important;
    }
    
    /* Main Content Area - Clean Design */
    #content-area {
        height: 1fr;
        background: $background;
    }
    
    /* Terminal Grid Container - Modern Spacing */
    #terminal-grid-container {
        width: 100%;
        height: 1fr;
        background: $background;
        padding: 0;
        overflow-y: auto;
        scrollbar-size: 1 1;
        scrollbar-color: #529d86;
        scrollbar-background: #2e4f46;
    }
    
    .terminal-grid {
        height: 100%;
        width: 100%;
        layout: grid;
        grid-gutter: 1 2;
    }
    
    /* Universal Terminal - Enhanced Design with Effects */
    .grid-terminal {
        width: 1fr;
        height: 1fr;
        border: none;
        background: $background;
        min-height: 10;
        min-width: 40;
        padding: 0;
    }
    
    .grid-terminal:hover {
        border: none;
        background: $background;
    }
    
    .terminal-container {
        height: 100%;
        width: 100%;
        background: transparent;
    }
    
    /* Terminal Header Bar - Modern Glass Effect */
    .terminal-header-bar {
        height: 2;
        min-height: 2;
        max-height: 2;
        background: $surface;
        border-bottom: solid $primary 50%;
        layout: horizontal;
        padding: 0 1;
    }
    
    .terminal-status {
        width: auto;
        color: $text-muted;
        padding: 0 2 0 0;
        content-align: left middle;
    }
    
    .terminal-header {
        width: 1fr;
        color: $text;
        padding: 0 1;
        content-align: left middle;
        text-style: bold;
    }
    
    /* Role Indicator - Modern Icons */
    .role-indicator {
        width: 3;
        content-align: center middle;
        padding: 0 1;
        text-style: bold;
    }
    
    .role-indicator.inactive { 
        color: $text-muted; 
    }
    .role-indicator.main { 
        color: $primary;
        text-style: bold reverse;
    }
    .role-indicator.agent { 
        color: $secondary;
        text-style: bold;
    }
    .role-indicator.monitor { 
        color: $warning;
        text-style: bold;
    }
    .role-indicator.logger { 
        color: $error;
        text-style: bold;
    }
    
    /* Terminal Output - Enhanced Readability */
    .terminal-output {
        height: 1fr;
        background: $surface;
        color: $text;
        padding: 1;
        scrollbar-size: 1 1;
        scrollbar-color: #529d86;
        scrollbar-background: #2e4f46;
    }
    
    /* Terminal States - Modern Focus Effects */
    .terminal-focused {
        border: none !important;
    }
    
    .terminal-focused .terminal-header-bar {
        background: $surface;
        border-bottom: solid $secondary !important;
    }
    
    .terminal-active .terminal-header-bar {
        background: $surface;
    }
    
    /* Layout Modes - Responsive Design */
    .layout-single .terminal-grid {
        grid-size: 1 1;
    }
    
    .layout-split .terminal-grid {
        grid-size: 2 1;
        grid-gutter: 2 3;
    }
    
    .layout-grid .terminal-grid {
        grid-gutter: 2 3;
    }
    
    .layout-vertical .terminal-grid {
        layout: vertical;
        grid-gutter: 2 0;
    }
    
    .layout-horizontal .terminal-grid {
        layout: horizontal;
        grid-gutter: 0 3;
    }
    
    /* Terminal Role Styles - Modern Design without borders */
    .role-main {
        border: none !important;
    }
    
    .role-main .terminal-header-bar {
        background: $surface;
        border-bottom: solid $primary;
    }
    
    .role-main .terminal-header {
        color: $primary;
    }
    
    .role-agent {
        border: none !important;
    }
    
    .role-agent .terminal-header-bar {
        background: $surface;
        border-bottom: solid $secondary;
    }
    
    .role-agent .terminal-header {
        color: $secondary;
    }
    
    .role-monitor {
        border: none !important;
    }
    
    .role-monitor .terminal-header-bar {
        background: $surface;
        border-bottom: solid $warning;
    }
    
    .role-monitor .terminal-header {
        color: $warning;
    }
    
    .role-logger {
        border: none !important;
    }
    
    .role-logger .terminal-header-bar {
        background: $surface;
        border-bottom: solid $error;
    }
    
    .role-logger .terminal-header {
        color: $error;
    }
    
    .role-empty {
        border: none !important;
    }
    
    /* Parallel Grid - Modern Layout */
    .parallel-grid {
        height: 100%;
        width: 100%;
        background: $background;
    }
    
    .parallel-row {
        height: 1fr;
        width: 100%;
        layout: horizontal;
        padding: 1;
    }
    
    .parallel-column {
        height: 100%;
        width: 100%;
        layout: vertical;
        padding: 1;
    }
    
    /* Agent Terminal - Enhanced Design */
    .agent-terminal {
        width: 1fr;
        height: 100%;
        border: thick $primary 50%;
        margin: 0 1;
        background: $surface;
    }
    
    .agent-terminal:hover {
        border: thick $primary-lighten-1;
    }
    
    .agent-terminal-content {
        height: 100%;
        background: $surface;
    }
    
    .agent-header {
        height: 3;
        background: $surface-lighten-1;
        padding: 0 2;
        text-align: center;
        text-style: bold;
        border-bottom: tall $primary 50%;
        color: $text;
    }
    
    /* Streaming Labels - Clean Design */
    Label#stream-* {
        width: 100%;
        height: 1;
        padding: 0 2;
        background: transparent;
        color: $text;
    }
    
    /* Info Status Bar - Modern Information Display */
    InfoStatusBar {
        height: 2;
        width: 100%;
        margin: 0;
        background: #0a0a0a;
        border-top: solid #03fcb1;
        padding: 0;
        dock: bottom;
    }
    
    InfoStatusBar Static {
        color: #c8ff00 !important;
        background: transparent;
        height: 100%;
    }
    
    InfoStatusBar .info-section {
        color: #c8ff00 !important;
        height: 100%;
    }
    
    InfoStatusBar .separator {
        color: #529d86 !important;
    }
    
    /* Action Bar - Modern Status Display */
    ActualActionBar {
        margin: 0;
        background: $surface;
        border: solid $primary 20%;
        padding: 0;
    }
    
    /* Force action bar height for 4+ terminals */
    .many-terminals ActualActionBar,
    StableTerminalGrid.many-terminals ActualActionBar {
        height: 5 !important;
        min-height: 5 !important;
        max-height: 5 !important;
    }
    
    /* Terminal Output Optimization */
    .terminal-output {
        height: 1fr;
        margin-bottom: 0;
    }
    
    /* Universal Terminal Layout */
    UniversalTerminal {
        height: 100%;
        layout: vertical;
    }
    
    /* Terminal Container Responsiveness */
    .terminal-container {
        height: 1fr;
    }
    
    /* Agent Output - Enhanced Readability */
    .agent-output {
        height: 1fr;
        background: $surface;
        color: $text;
        padding: 1 2;
        scrollbar-size: 1 1;
        scrollbar-color: #529d86;
        scrollbar-background: #2e4f46;
    }
    
    /* Tool Panel - Modern Card Design */
    .tool-panel-container {
        margin: 1 2;
        background: $surface-lighten-1;
        border: tall $primary 20%;
        padding: 1;
    }
    
    .tool-content {
        width: 100%;
        color: $text;
    }
    
    /* Input Area - Modern Command Line */
    #input-area {
        height: 3;
        width: 100%;
        background: $surface;
        border: solid $primary 50%;
        padding: 0 2;
        layout: horizontal;
        align: left middle;
    }
    
    #main-input {
        height: 1;
        width: 100%;
        background: transparent;
        padding: 0;
        layout: horizontal;
    }
    
    #main-input:focus {
        background: transparent;
    }
    
    /* Prompt Input Styles */
    PromptInput {
        height: 1;
        width: 100%;
        background: transparent;
        padding: 0;
        layout: horizontal;
        align: left middle;
    }
    
    PromptInput #prompt-prefix {
        color: $primary;
        text-style: bold;
        background: transparent;
        width: auto;
        padding: 0 0 0 0;
        margin: 0 1 0 0;
        height: 1;
        content-align: left middle;
    }
    
    PromptInput #prompt-input-field {
        background: transparent !important;
        color: $text !important;
        border: none !important;
        width: 1fr;
        padding: 0 !important;
        height: 1;
    }
    
    PromptInput #prompt-input-field:focus {
        background: transparent !important;
        border: none !important;
        color: $text !important;
    }
    
    /* Agent Selector Panel - Modern Modal Design */
    #agent-selector-panel {
        layer: overlay;
        width: 100%;
        height: 100%;
        display: none;
    }
    
    #agent-selector-panel.visible {
        display: block;
    }
    
    #agent-selector-overlay {
        width: 100%;
        height: 100%;
        background: rgba(14, 15, 17, 0.9);
        align: center middle;
    }
    
    #agent-selector-content {
        width: 60;
        max-height: 80%;
        background: $surface-lighten-1;
        border: thick $primary 50%;
        padding: 2;
    }
    
    #selector-header {
        height: 3;
        background: transparent;
        color: $text;
        text-align: center;
        text-style: bold;
        border-bottom: tall $primary 50%;
        margin-bottom: 2;
        padding: 1;
    }
    
    #prompt-preview {
        height: auto;
        padding: 1 2;
        margin-bottom: 2;
        color: $text;
        background: $surface;
        border: tall $primary 20%;
    }
    
    #agent-list-container {
        height: 1fr;
        overflow-y: auto;
        background: $surface;
        border: tall $primary 20%;
        padding: 2;
        margin-bottom: 2;
        scrollbar-size: 1 1;
        scrollbar-color: #529d86;
        scrollbar-background: #2e4f46;
    }
    
    #agent-list-container Checkbox {
        width: 100%;
        margin-bottom: 1;
        color: $text;
        padding: 0 1;
    }
    
    #agent-list-container Checkbox:hover {
        background: $surface;
        color: $text;
    }
    
    #agent-list-container Checkbox:focus {
        background: $surface-lighten-1;
        border: tall $primary 50%;
    }
    
    #selector-buttons {
        height: 3;
        align: center middle;
    }
    
    #selector-buttons Button {
        margin: 0 2;
        background: $surface;
        color: $text;
        border: tall $primary 20%;
        padding: 0 3;
        text-style: bold;
    }
    
    #selector-buttons Button:hover {
        background: $primary;
        color: $background;
        border: tall $primary;
    }
    
    #selector-buttons Button:focus {
        background: $primary-lighten-1;
        color: $background;
    }
    
    /* Footer Enhancement - Modern Status Bar */
    Footer {
        background: $surface-lighten-1;
        color: $text-muted;
        border-top: solid $primary 50%;
        height: 2;
        padding: 0 2;
        layout: horizontal;
    }
    
    Footer > .footer--key {
        background: $surface;
        color: $text;
        text-style: bold;
        margin: 0 1;
        padding: 0 1;
        border: round $primary 20%;
    }
    
    Footer > .footer--key-ready {
        background: $primary-darken-1;
        color: $background;
    }
    
    Footer > .footer--description {
        color: $text-muted;
        margin: 0 1 0 0;
    }
    
    /* Modern Button Styles */
    Button {
        background: $surface;
        color: $text;
        border: solid $primary 20%;
        text-style: none;
        padding: 0 2;
        margin: 0 1;
    }
    
    Button:hover {
        background: $surface-lighten-1;
        color: $primary;
        border: solid $primary;
    }
    
    Button:focus {
        background: $primary 30%;
        color: $primary;
        border: solid $primary;
    }
    
    Button.-primary {
        background: $primary;
        color: $background;
        border: solid $primary;
    }
    
    Button.-primary:hover {
        background: $primary-lighten-1;
        border: solid $primary-lighten-1;
    }
    
    /* Top bar container */
    #top-bar {
        height: 3;
        width: 100%;
        background: $surface;
        dock: top;
    }
    
    /* Sidebar toggle button integrated in top bar */
    .sidebar-toggle {
        width: 8;
        height: 3;
        background: transparent !important;
        border: none !important;
        color: #ffffff !important;
        text-align: center;
        content-align: center middle;
        text-style: bold;
        margin: 0 1 0 0;
        text-opacity: 1.0 !important;
        outline: none !important;
    }
    
    .sidebar-toggle:hover {
        background: rgba(1, 120, 212, 0.3) !important;
        border: none !important;
        color: #ffffff !important;
        text-opacity: 1.0 !important;
        outline: none !important;
    }
    
    /* Tab headers container - takes remaining space in top bar */
    #tab-headers {
        width: 1fr;
        height: 3;
        background: transparent;
        layout: horizontal;
    }
    
    /* Main tabs container - full height below top bar */
    #main-tabs {
        width: 100%;
        height: 1fr;
    }
    
    /* Hide the default tab bar since we're creating custom ones */
    #main-tabs Tabs {
        display: none;
    }
    
    /* Custom tab buttons */
    .custom-tab {
        height: 3;
        background: transparent;
        padding: 0 2;
        margin: 0 1 0 0;
        border: none;
        color: #ffffff !important;
        text-opacity: 1.0 !important;
        content-align: center middle;
        text-align: center;
    }
    
    .custom-tab:hover {
        color: #ffffff !important;
        background: rgba(1, 120, 212, 0.3);
        text-opacity: 1.0 !important;
        border: none;
    }
    
    .custom-tab.active-tab {
        color: #ffffff !important;
        background: #0178d4;
        text-style: bold;
        text-opacity: 1.0 !important;
        border: none;
    }
    
    /* Top bar when sidebar is collapsed - move entire bar left */
    #top-bar.sidebar-collapsed {
        margin-left: -32;  /* Move left by sidebar width */
    }
    
    /* App close button - styled with red/maroon theme for intuitive close action */
    .app-close-button {
        width: 9;
        min-width: 9;
        max-width: 9;
        height: 3;
        background: transparent;
        border: none;
        color: #ffffff;
        text-align: center;
        content-align: center middle;
        text-style: bold;
        margin: 0;
        padding: 0;
        outline: none !important;
    }
    
    .app-close-button:hover {
        background: rgba(200, 60, 60, 0.7);
        border: none;
        color: #ffffff;
    }
    
    /* Add terminal button - styled to match other top bar buttons */
    .add-terminal-button {
        width: 8;
        min-width: 8;
        max-width: 8;
        height: 3;
        background: transparent;
        border: none;
        color: #ffffff;
        text-align: center;
        content-align: center middle;
        text-style: bold;
        margin: 0 1 0 0;
        padding: 0;
        outline: none !important;
        text-opacity: 1.0 !important;
    }
    
    .add-terminal-button:hover {
        background: rgba(1, 120, 212, 0.3);
        border: none;
        color: #ffffff;
        text-opacity: 1.0 !important;
    }
    
    /* Help section styles */
    #help-content {
        width: 100%;
        height: 100%;
        padding: 0;
        background: $surface;
        border-top: solid $border;
        layout: vertical;
    }
    
    .help-title {
        color: $text;
        text-align: center;
        padding: 1 0 1 0;
        margin: 0;
        background: transparent;
        border-bottom: solid $border;
    }
    
    #help-scrollable-content {
        width: 100%;
        height: 1fr;
        padding: 1 2 2 2;
        background: $surface;
        overflow-y: auto;
        scrollbar-size: 1 1;
        scrollbar-color: #529d86;
        scrollbar-background: #2e4f46;
    }
    
    #help-columns {
        width: 100%;
        height: auto;
        layout: horizontal;
    }
    
    .help-column {
        width: 50%;
        height: auto;
        padding: 1;
    }
    
    #help-left-column {
        border-right: solid $border;
        padding-right: 2;
    }
    
    #help-right-column {
        padding-left: 2;
    }
    
    .help-content {
        color: $text;
        text-align: left;
        padding: 0;
        margin: 0;
        background: transparent;
        max-width: 100%;
    }
    
    .help-protips {
        color: $text;
        text-align: left;
        padding: 1 0 1 0;
        margin: 0;
        background: transparent;
        border-top: solid $border;
        margin-top: 2;
        max-width: 100%;
    }
    
    """

    # Enable Command Palette to allow theme search/switch
    ENABLE_COMMAND_PALETTE = True
    # Ensure proper mouse handling
    mouse_over_widget = None
    captured_widget = None
    
    BINDINGS = [
        Binding("ctrl+c", "cancel_selected", t('tui_cancel_selected')),
        Binding("ctrl+q", "quit", t('tui_exit')),
        Binding("ctrl+l", "clear", t('tui_clear')),
        Binding("ctrl+p", "command_palette", t('tui_command_palette')),
        # Reserve ctrl+p for Textual palette; move our parallel prompt
        Binding("ctrl+shift+a", "parallel_prompt", t('tui_prompt_all')),
        Binding("ctrl+s", "toggle_sidebar", t('tui_toggle_sidebar')),
        Binding("ctrl+n", "next_terminal", t('tui_next_terminal')),
        Binding("ctrl+b", "prev_terminal", t('tui_prev_terminal')),
        Binding("escape", "cancel_all", t('tui_cancel_all')),
        Binding("ctrl+shift+q", "show_queue", t('tui_show_queue')),
        Binding("ctrl+e", "close_terminal", t('tui_close_terminal')),
        Binding("ctrl+t", "toggle_terminal_view", t('tui_toggle_view')),
        Binding("ctrl+shift+t", "cycle_theme", t('tui_cycle_theme')),
        Binding("ctrl+u", "clear_input", t('tui_clear_input')),
        # Tab navigation
        Binding("ctrl+1", "show_terminal", t('tui_terminal_tab')),
        Binding("ctrl+2", "show_ctr", t('tui_ctr_tab')),
        Binding("ctrl+tab", "cycle_tabs", t('tui_next_tab')),
    ]

    def __init__(self):
        super().__init__()
        self.terminal_grid = None
        self.sidebar = None
        self.command_handler = None
        self.agent_manager = None
        self.prompt_input = None
        self.session_manager = None
        self._terminal_agent_map = {}
        self._show_all_terminals = True  # Track view state
        # Store current app instance for workers
        CAITerminal._current_app = self
        CAITerminal._instance = self  # Also store as _instance for compatibility
        # Track ESC key presses for double-tap exit
        self._last_esc_time = 0
        self._esc_exit_threshold = 0.5  # 500ms between ESC presses
        # History file path
        self.history_file = None
        # Track cancellation state to prevent concurrent cancellations
        self._cancelling = False
        self._cancel_task = None
        self._startup_config_applied = False
        # Track when the TUI session started for accurate summary reporting
        self._session_start_time = time.time()

    def compose(self) -> ComposeResult:
        """Compose the application UI"""
        # Main layout container
        with Container(id="app-layout"):
            # Sidebar
            yield Sidebar(id="sidebar")

            # Main content container with tabs
            with Container(id="main-container"):
                # Top bar with toggle button, tab headers, and close button
                with Horizontal(id="top-bar"):
                    yield Static("☰", id="sidebar-toggle-btn", classes="sidebar-toggle")
                    with Container(id="tab-headers"):
                        yield Button(t('tui_terminal'), id="tab-terminal-btn", classes="custom-tab active-tab")
                        add_terminal_btn = Static(t('tui_add_terminal'), id="add-terminal-btn", classes="add-terminal-button")
                        add_terminal_btn.tooltip = t('tui_add_terminal_tip')
                        yield add_terminal_btn
                        yield Button(t('tui_graph'), id="tab-graph-btn", classes="custom-tab")
                        yield Button(t('tui_help'), id="tab-help-btn", classes="custom-tab")
                    app_close_btn = Static("×", id="app-close-btn", classes="app-close-button")
                    app_close_btn.tooltip = t('tui_close_cai')
                    yield app_close_btn
                
                # Main tabs content (separate from top bar)
                with TabbedContent(initial="terminal", id="main-tabs"):
                    # Terminal Tab
                    with TabPane(t('tui_terminal'), id="terminal"):
                        # Terminal grid takes all available space
                        yield StableTerminalGrid(id="terminal-grid-container")
                        
                        # Info status bar above input area
                        yield InfoStatusBar(id="info-status-bar", terminal_number=1)
                        
                        # Input area at bottom
                        yield Container(
                            PromptInput(prompt="CAI>", id="main-input"),
                            id="input-area"
                        )
                    
                    # Graph tab (CTR viewer)
                    with TabPane(t('tui_graph'), id="ctr"):
                        yield CTRCanvas(id="ctr-canvas")
                    
                    # Help tab (User guide and tips)
                    with TabPane(t('tui_help'), id="help"):
                        with Container(id="help-content"):
                            # Sticky title section
                            yield Static(f"[bold cyan]🚀 {t('tui_quick_start')}[/bold cyan]",
                                       id="help-title", classes="help-title", markup=True)
                            
                            # Scrollable content container
                            with Container(id="help-scrollable-content"):
                                # Two-column layout for content
                                with Horizontal(id="help-columns"):
                                    # Left column - Basic setup and usage
                                    with Container(id="help-left-column", classes="help-column"):
                                        yield Static(self._get_help_basic_content(), 
                                                   id="help-basic", classes="help-content", markup=True)
                                    
                                    # Right column - Advanced features and commands
                                    with Container(id="help-right-column", classes="help-column"):
                                        yield Static(self._get_help_advanced_content(), 
                                                   id="help-advanced", classes="help-content", markup=True)
                                
                                # Pro Tips footer section
                                yield Static(self._get_help_protips_content(), 
                                           id="help-protips", classes="help-protips", markup=True)

        # Overlay panels
        yield AgentSelectorPanel(id="agent-selector-panel")
        yield AgentCreatorPanel(id="agent-creator-panel")
        
        # Footer at very bottom
        yield Footer()

    def _get_help_basic_content(self) -> str:
        """Generate basic setup and usage content for left column"""
        return """[bold yellow]📋 Initial Setup[/bold yellow]
[cyan]Configure your API Key:[/cyan]
• Go to [bold]Sidebar → Keys[/bold] tab
• Click [bold green]Add New Key[/bold green] 
• Enter: [bold]ALIAS_API_KEY[/bold] = your_alias_api_key_here
• Click [bold green]Save[/bold green] button
• [dim]Alternative: You can add other providers API_KEYS the same way[/dim]

[bold yellow]🤖 Select Your Model[/bold yellow]
[cyan]Choose the right model:[/cyan]
• In terminal header, click [bold]model[/bold] dropdown
• Select: [bold green]alias1[/bold green] (recommended)
• [dim]Alternative: Use command[/dim] [bold]/model alias1[/bold]
• [dim]alias1 provides optimal performance and cost balance[/dim]

[bold yellow]🎯 Choose an Agent[/bold yellow]
[cyan]Pick your AI assistant:[/cyan]
• Click [bold]agent[/bold] dropdown in terminal header and browse available agents
• [dim]Recommendation:[/dim] Use [bold]selection_agent[/bold] (or [bold]/agent 17[/bold]) to get a recommendation based on your task
• [dim]List all agents:[/dim] [bold]/agent list[/bold]
• [dim]Alternative: Use command[/dim] [bold]/agent agent_name[/bold]


[bold yellow]➕ Add New Terminal[/bold yellow]
[cyan]Open another workspace quickly:[/cyan]
• Click [bold]Add +[/bold] on the top bar
• Creates a new terminal with model [bold]alias1[/bold] and agent [bold]redteam_agent[/bold]
• Tooltip shows: [bold]Add new terminal[/bold]


[bold yellow]💬 Start Chatting[/bold yellow]
[cyan]Begin your conversation:[/cyan]
• Type in the input field at bottom: [bold]CAI>[/bold]
• Press [bold]Enter[/bold] to send your prompt
• You can send another prompt while the first one is being processed, and it will be queued automatically.
• Use [bold]/help[/bold] for available commands
"""

    def _get_help_advanced_content(self) -> str:
        """Generate advanced features and tips content for right column"""
        return """[bold yellow]🖥️  Interface Overview[/bold yellow]
[cyan]Main sections explained:[/cyan]
• [bold]Sidebar[/bold]: 
  - [dim]Agents:[/dim] Browse and select AI assistants
  - [dim]Queue:[/dim] Manage prompt batches
  - [dim]Keys:[/dim] Configure API credentials
  - [dim]Stats:[/dim] View conversation stats
• [bold]Terminal[/bold]: Chat interface and command execution
  - [dim]Add +:[/dim] Create a new terminal (defaults: [bold]alias1[/bold] + [bold]redteam_agent[/bold])
• [bold]Graph[/bold]: Visual conversation flow representation
• [bold]Help[/bold]: You are here!

[bold yellow]🔄 Advanced Features[/bold yellow]
[cyan]Power user capabilities:[/cyan]
• [bold]Teams[/bold]: Try collaborative agent groups
  - [dim]Use for complex multi-step tasks[/dim]
  - [dim]Combine different agent specialties[/dim]

• [bold]Stats Monitoring[/bold]: Track conversation metrics
  - [dim]View costs, tokens...[/dim]
  - [dim]Monitor conversation history[/dim]

• [bold]Graph Visualization[/bold]: Understand conversation flow
  - [dim]See agent interactions visually[/dim]
  - [dim]Track conversation branches[/dim]

[bold yellow]⚡ Essential Shortcuts[/bold yellow]
[cyan]Most used hotkeys:[/cyan]
• [bold]Ctrl+S[/bold]: Toggle sidebar
• [bold]Ctrl+Q[/bold]: Exit CAI
• [bold]Ctrl+L[/bold]: Clear terminals
• [bold]Ctrl+N/B[/bold]: Next/Previous terminal
• [bold]Ctrl+E[/bold]: Close current terminal
"""

    def _get_help_protips_content(self) -> str:
        """Generate Pro Tips content for footer section"""
        return """[bold green]💡 Pro Tips[/bold green]
[cyan]Expert recommendations:[/cyan]
- Start with [bold]alias1[/bold] model and explore different agents to find your perfect AI assistant!
- Use [bold]/agent list[/bold] to explore all available capabilities and specialties
- Try different agents in parallel for specialized tasks and comprehensive analysis
- You can add at the end of the prompt or command: "t1", "t2", "t3", etc. or "all" to specify the terminal
- Use Teams feature for complex multi-agent workflows and collaborative problem-solving
- Use the Graph view to understand conversation flow and agent interactions visually

[dim]Need more help? Check the sidebar sections or use /help command in terminal.[/dim]"""

    def on_mount(self) -> None:
        """Initialize when app mounts"""
        # Set TUI mode for display system
        os.environ["CAI_TUI_MODE"] = "true"
        # Register CAI themes and apply preferred one
        try:
            self._register_cai_themes()
        except Exception:
            pass
        # Default to a built-in dark theme unless overridden; avoid any *light* saved theme
        preferred = os.getenv("CAI_THEME") or _tui_config.get_theme() or "tokyo-night"
        if isinstance(preferred, str) and "light" in preferred.lower():
            preferred = "tokyo-night"
        try:
            self.theme = preferred
        except Exception:
            self.theme = "tokyo-night"
        
        # Enable mouse support
        # Note: mouse_over and capture_mouse are methods, not properties
        
        # Removed: Terminal prompt bar was blocking main input
        # self.terminal_prompt_bar = self.query_one("#terminal-prompt-bar", TerminalPromptBar)

        # Set up display manager for TUI mode
        from cai.tui.display import DisplayManager, DisplayMode

        display_manager = DisplayManager()
        display_manager.set_mode(DisplayMode.TUI)

        # OpenAI ChatCompletions integration for TUI display
        integrate_openai_chatcompletions_display()
        
        # Info bar integration (no-op, kept for clarity)
        from cai.sdk.agents.models.openai_chatcompletions_info_bar_integration import (
            integrate_openai_chatcompletions_info_bar,
        )

        integrate_openai_chatcompletions_info_bar()
        
        # Core integrates terminal routing; skip legacy patch hooks
        
        # Streaming is now handled directly in StreamingDisplay
        # No additional patches needed
        
        # Removed: async_integration.py was disabled and not functional

        # Get component references (must happen on mount)
        self.terminal_grid = self.query_one("#terminal-grid-container", StableTerminalGrid)
        self.sidebar = self.query_one("#sidebar", Sidebar)

        # Schedule initialization after the grid has created its terminals
        self.call_after_refresh(self._initialize_after_mount)

        # Initialize command history
        self._initialize_command_history()
        
        # Get prompt input reference and focus it
        self.prompt_input = self.query_one("#main-input", PromptInput)
        self.prompt_input.focus()
        # Ensure Enter works and focus stays on the input field
        try:
            underlying = self.query_one("#prompt-input-field")
            underlying.can_focus = True
        except Exception:
            pass

        # Start periodic updates
        self.set_interval(1.0, self.update_layout_indicator)
        
        # Initialize sidebar visibility state
        try:
            sidebar = self.query_one("#sidebar", Sidebar)
            self.sidebar_visible = sidebar.visible
        except Exception:
            # Sidebar might not be mounted yet, default to True
            self.sidebar_visible = True
        
        # Disable automatic focus management - it interferes with terminal selection
        # self.set_interval(0.5, self._ensure_prompt_focus)

    def _register_cai_themes(self) -> None:
        """Register CAI-specific themes with Textual."""
        # Nature (existing)
        nature = TextualTheme(
            name="nature",
            primary="#00ff9c",
            accent="#00ff9c",
            foreground="#e6ffe6",
            background="#001f1a",
            surface="#01342c",
            panel="#01342c",
            success="#4CAF50",
            warning="#F5A623",
            error="#FF5A5F",
            dark=True,
            variables={
                "graph-node": "#4CAF50",
            },
        )
        self.register_theme(nature)

        # Alias-inspired dark theme (compact high-contrast)
        alias = TextualTheme(
            name="alias-dark",
            primary="#FF4D4D",   # vivid red accent
            accent="#00D1B2",    # teal/mint accent
            foreground="#E8F1F2",# near-white text
            background="#0B1E24",# deep blue-green background
            surface="#102A31",   # slightly lighter surface
            panel="#0F242A",
            success="#21C36B",
            warning="#F4C430",
            error="#FF4D4D",
            dark=True,
            variables={
                "graph-node": "#00D1B2",
                "border": "#184046",
            },
        )
        self.register_theme(alias)

        # Extra curated defaults from Textual
        for builtin in ("textual-dark", "textual-light", "nord", "tokyo-night", "solarized-dark", "solarized-light"):
            try:
                # Setting self.theme to builtin registers it internally; we only want availability.
                pass
            except Exception:
                pass

    def action_cycle_theme(self) -> None:
        """Cycle through a curated list of themes and persist selection."""
        ordered = [
            "textual-dark",
            "textual-light",
            "tokyo-night",
            "nord",
            "solarized-light",
            "solarized-dark",
            "alias-robotics",
            "nature",
        ]
        current = getattr(self, "theme", None)
        idx = ordered.index(current) if current in ordered else -1
        next_theme = ordered[(idx + 1) % len(ordered)]
        try:
            self.theme = next_theme
            _tui_config.set_theme(next_theme)
        except Exception:
            pass

        # (moved initialization to on_mount)

    def _initialize_after_mount(self) -> None:
        """Initialize components after mount and refresh"""
        # Prevent infinite recursion
        if not _recursion_guard.can_proceed("initialize_after_mount"):
            return
            
        # Initialize session manager
        from cai.tui.core import SessionManager

        self.session_manager = SessionManager()
        
        # Set up prompt queue callback
        PROMPT_QUEUE.set_process_callback(self._process_queued_prompt)

        # Get main terminal output for handlers
        main_terminal = self.terminal_grid.get_main_terminal()
        if main_terminal and main_terminal.output:
            # Initialize handlers
            self.command_handler = CommandHandler(main_terminal.output, 1, main_terminal.terminal_id)
            self.agent_manager = AgentManager(main_terminal.output)
            
            # IMPORTANT: Set session manager in command handler
            self.command_handler.session_manager = self.session_manager
            
            # Set default agent name in main terminal
            main_terminal.state.agent_name = self.command_handler.current_agent_name
            main_terminal._update_header()

            # Add main terminal to session manager
            runner = self.session_manager.add_terminal_runner(1, main_terminal)
        
        # Force info bar update (best effort)
        try:
            info_bar = self.query_one("#info-status-bar", InfoStatusBar)
            info_bar._update_info()
        except Exception:
            pass

        # Initialize terminal runner and default agent regardless of info bar
        asyncio.create_task(self._initialize_terminal_runner(1))

        # Initialize default agent (force redteam_agent by default in TUI)
        agent_type = "redteam_agent"
        self.agent_manager.current_agent_name = agent_type
        asyncio.create_task(self.agent_manager.initialize_agent(agent_type))
        
        # Apply startup configuration (if provided) once core components are ready
        asyncio.create_task(self._maybe_apply_startup_config())

        # Load queue file after initialization
        queue_file = os.getenv("CAI_QUEUE_FILE")
        if queue_file:
            main_terminal.write(f"[dim]Queue file detected: {queue_file}[/dim]")
            # Schedule queue loading with a small delay
            asyncio.create_task(self._load_and_process_queue_file(queue_file))
        else:
            # If main terminal not ready, schedule another attempt
            # Try once more with async delay instead of recursive call
            if _recursion_guard.attempts.get("initialize_after_mount", 0) < 2:
                asyncio.create_task(self._delayed_initialize())
            return
    
    async def _delayed_initialize(self) -> None:
        """Delayed initialization attempt"""
        await asyncio.sleep(0.5)
        self._initialize_after_mount()


        # Check initial mode
        self._check_mode()

    async def _maybe_apply_startup_config(self) -> None:
        """Apply startup configuration once per session if provided."""
        if self._startup_config_applied:
            return

        yaml_path = os.getenv("CAI_TUI_STARTUP_YAML")
        if not yaml_path:
            return

        # Give the UI a short moment to finish mounting
        await asyncio.sleep(0.3)

        await self._apply_startup_config(yaml_path)

    async def _apply_startup_config(self, yaml_path: str) -> None:
        """Configure terminals and agents from YAML startup definitions.

        The routine guarantees that each terminal receives a freshly
        initialized ``TerminalRunner`` with its own environment overrides
        before the initial prompt is executed. This keeps red/blue team
        agents fully isolated even when they are auto-launched in parallel.
        """
        if self._startup_config_applied:
            return

        grid = self.terminal_grid
        session_manager = self.session_manager
        if not grid or not session_manager:
            return

        main_terminal = grid.get_main_terminal()

        try:
            data, resolved_path = load_agents_config(yaml_path)
        except AgentsConfigError as exc:
            if main_terminal:
                main_terminal.write(f"[red]Failed to load agents YAML: {exc}[/red]")
            return

        if not resolved_path:
            if main_terminal:
                main_terminal.write(f"[yellow]Startup YAML not found: {yaml_path}[/yellow]")
            return

        agents, metadata, origin = extract_agent_definitions(data)
        if not agents:
            if main_terminal:
                main_terminal.write(
                    f"[yellow]No agent definitions found in {resolved_path}[/yellow]"
                )
            return

        runtime_prompt_override = os.getenv("CAI_TUI_SHARED_PROMPT")
        runtime_prompt = runtime_prompt_override.strip() if isinstance(runtime_prompt_override, str) else None

        shared_prompt = metadata.get("shared_prompt")
        if isinstance(shared_prompt, str):
            shared_prompt = shared_prompt.strip()
        else:
            shared_prompt = None

        auto_run_default = metadata.get("auto_run")
        if auto_run_default is None:
            auto_run_default = True
        auto_run_default = bool(auto_run_default)

        default_team_name = "Parallel Agents"
        team_indices: dict[str, int] = {}
        team_agent_counts: dict[str, int] = {}

        agent_slots = []
        for sequential_index, agent in enumerate(agents, start=1):
            agent_name = agent.get("agent_name")
            if not agent_name:
                continue

            raw_team = agent.get("team")
            team_name = raw_team.strip() if isinstance(raw_team, str) else None
            if not team_name:
                team_name = default_team_name

            team_index = agent.get("team_index")
            if isinstance(team_index, int):
                team_indices.setdefault(team_name, team_index)
            else:
                team_index = team_indices.setdefault(team_name, len(team_indices) + 1)

            team_agent_counts.setdefault(team_name, 0)
            agent_index = agent.get("agent_index")
            if not isinstance(agent_index, int):
                team_agent_counts[team_name] += 1
                agent_index = team_agent_counts[team_name]

            raw_env = agent.get("env") if isinstance(agent.get("env"), dict) else {}
            normalized_env: dict[str, str] = {}
            for key, value in raw_env.items():
                if isinstance(value, bool):
                    normalized_env[str(key)] = "true" if value else "false"
                else:
                    normalized_env[str(key)] = str(value)

            slot_prompt = agent.get("prompt")
            if isinstance(slot_prompt, str):
                slot_prompt = slot_prompt.strip()

            if runtime_prompt:
                prompt_to_use = runtime_prompt
                prompt_source = "runtime"
            elif slot_prompt:
                prompt_to_use = slot_prompt
                prompt_source = "agent"
            else:
                prompt_to_use = shared_prompt
                prompt_source = "shared" if shared_prompt else ""

            agent_auto = agent.get("auto_run")
            if not isinstance(agent_auto, bool):
                agent_auto = auto_run_default

            agent_slots.append(
                {
                    "agent_name": agent_name,
                    "team_name": team_name,
                    "prompt": prompt_to_use,
                    "prompt_source": prompt_source,
                    "env": normalized_env,
                    "model": agent.get("model"),
                    "auto_run": bool(agent_auto),
                    "team_index": team_index,
                    "agent_index": agent_index,
                }
            )

        if not agent_slots:
            if main_terminal:
                main_terminal.write(
                    f"[yellow]No valid agents found in {resolved_path}[/yellow]"
                )
            return

        # Reset to single terminal before configuring and remove stale runners
        grid.remove_agent_terminals()
        await asyncio.sleep(0.05)

        if session_manager:
            stale_numbers = [num for num in session_manager.terminal_runners.keys() if num > 1]
            for num in stale_numbers:
                runner = session_manager.terminal_runners.pop(num)
                try:
                    await runner.cancel_current_task()
                except Exception:
                    pass
                AGENT_MANAGER.decrement_terminal_count()

        required_terminals = len(agent_slots)

        # Ensure all required terminals are mounted before configuration
        for idx in range(2, required_terminals + 1):
            grid.add_agent_terminal(agent_slots[idx - 1]["agent_name"])

        await grid.wait_for_pending_mounts()
        await self._wait_for_terminals_visible(grid, list(range(1, required_terminals + 1)))

        summary_lines = []
        self._terminal_agent_map = {}

        for idx, slot in enumerate(agent_slots, start=1):
            terminal = grid.get_terminal_by_number(idx)
            if not terminal:
                if main_terminal:
                    main_terminal.write(
                        f"[red]Failed to provision terminal {idx} for {slot['agent_name']}[/red]"
                    )
                continue

            if hasattr(terminal, "state"):
                terminal.state.agent_name = slot["agent_name"]
                terminal.state.team_name = slot["team_name"]
                terminal._update_header()

            self._terminal_agent_map[idx] = slot["agent_name"]

            runner = session_manager.terminal_runners.get(idx)
            if not runner:
                runner = session_manager.add_terminal_runner(idx, terminal)
            else:
                runner.terminal = terminal
                runner.config.terminal_id = terminal.terminal_id

            runner.config.is_parallel = required_terminals > 1
            parallel_cfg = ParallelConfig(
                slot["agent_name"],
                slot.get("model"),
                slot.get("prompt"),
                unified_context=False,
            )
            parallel_cfg.id = f"auto-{idx}"
            runner.config.parallel_config = parallel_cfg
            runner.config.agent_name = slot["agent_name"]
            runner.config.env = slot["env"] or None
            if slot["model"]:
                runner.config.model = slot["model"]

            await session_manager.initialize_terminal(idx)
            await session_manager.update_terminal_agent(idx, slot["agent_name"])

            if slot["model"]:
                await runner.update_model(slot["model"])

            env_summary = ", ".join(f"{k}={v}" for k, v in slot["env"].items()) or "default env"
            summary_lines.append(
                f"T{idx}: {slot['agent_name']} [{slot['team_name']}] ({env_summary})"
            )

        session_manager.set_parallel_mode(len(agent_slots) > 1)

        if main_terminal:
            main_terminal.write("")
            origin_label = origin or "parallel_agents"
            header = f"[bold green]Startup agents loaded from {resolved_path}[/bold green]"
            if origin_label != "parallel_agents":
                header = (
                    f"[bold green]Startup agents loaded from {resolved_path} "
                    f"({origin_label})[/bold green]"
                )
            main_terminal.write(header)
            description = metadata.get("description")
            if isinstance(description, str) and description.strip():
                main_terminal.write(f"[dim]{description.strip()}[/dim]")
            for line in summary_lines:
                main_terminal.write(f"[green]- {line}[/green]")
            if runtime_prompt:
                main_terminal.write(
                    f"[cyan]Runtime prompt override applied to all agents:[/cyan] {runtime_prompt}"
                )
            elif shared_prompt:
                main_terminal.write(
                    f"[cyan]Shared prompt applied when agent prompt is absent:[/cyan] {shared_prompt}"
                )
            if shared_prompt and not runtime_prompt:
                main_terminal.write("")
                main_terminal.write(
                    f"[cyan]Shared prompt:[/cyan] {shared_prompt}"
                )
            main_terminal.write("")

        # Ensure all queued terminals have mounted before starting auto-run
        try:
            await grid.wait_for_pending_mounts()
        except Exception:
            # Ignore wait errors; best effort only
            pass

        # Also wait until every terminal is visibly mounted (outputs available)
        await self._wait_for_terminals_visible(
            grid,
            list(range(1, len(agent_slots) + 1)),
        )

        self._startup_config_applied = True

        auto_run_slots: list[tuple[int, dict[str, object]]] = []

        for idx, slot in enumerate(agent_slots, start=1):
            should_auto_run = slot.get("auto_run")
            if should_auto_run is None:
                should_auto_run = auto_run_default
            if not should_auto_run:
                continue
            prompt = slot.get("prompt")
            if not prompt:
                continue
            auto_run_slots.append((idx, slot))

        if auto_run_slots:
            terminal_numbers = [idx for idx, _ in auto_run_slots]

            # Wait until all targeted runners are ready before executing prompts
            await self._wait_for_all_runners(session_manager, terminal_numbers)

            main_terminal = self.terminal_grid.get_main_terminal()
            if main_terminal:
                scheduled = ", ".join(
                    f"T{idx}:{slot.get('agent_name', f'T{idx}') or f'T{idx}'}"
                    f"[{slot.get('prompt_source', 'manual') or 'manual'}]"
                    for idx, slot in auto_run_slots
                )
                main_terminal.write(
                    f"[dim]Auto-run scheduling for {scheduled}[/dim]"
                )

            # Launch prompts concurrently (lightly staggered) so all terminals show activity immediately
            auto_run_tasks = []
            for offset, (idx, slot) in enumerate(auto_run_slots):
                auto_run_tasks.append(
                    asyncio.create_task(
                        self._run_auto_prompt(
                            session_manager,
                            idx,
                            slot.get("prompt"),
                            agent_name=slot.get("agent_name", f"T{idx}"),
                            delay=0.05 * offset,
                        )
                    )
                )

            if auto_run_tasks:
                results = await asyncio.gather(*auto_run_tasks, return_exceptions=True)
                main_terminal = self.terminal_grid.get_main_terminal()
                if main_terminal:
                    for idx, result in enumerate(results, start=1):
                        if isinstance(result, Exception):
                            slot_idx, slot = auto_run_slots[idx - 1]
                            main_terminal.write(
                                f"[red]Auto-run error for T{slot_idx} ({slot.get('agent_name', f'T{slot_idx}') or f'T{slot_idx}'}): {result}[/red]"
                            )
    
    async def _load_and_process_queue_file(self, queue_file: str) -> None:
        """Load queue file and start processing after a short delay"""
        # Wait for everything to be ready
        await asyncio.sleep(1.0)
        
        main_terminal = self.terminal_grid.get_main_terminal()
        if not main_terminal:
            return
            
        try:
            from cai.repl.commands.queue import load_queue_from_file, get_queue
            queue_file = os.path.expanduser(queue_file)
            
            if not os.path.exists(queue_file):
                main_terminal.write(f"[yellow]⚠️ Queue file not found: {queue_file}[/yellow]")
                return
                
            # Load the queue file
            main_terminal.write(f"[dim]Loading queue from {queue_file}...[/dim]")
            loaded = load_queue_from_file(queue_file)
            
            if loaded > 0:
                # Show notification
                main_terminal.write(f"[cyan]📋 Auto-loaded {loaded} prompts from CAI_QUEUE_FILE[/cyan]")
                main_terminal.write(f"[green]▶️ Starting automatic queue processing...[/green]")
                
                # Force refresh the sidebar
                self.sidebar.refresh_queue()
                
                # Give a moment for the UI to update
                await asyncio.sleep(0.5)
                
                # Start processing the first prompt
                if PROMPT_QUEUE.get_queue_size() > 0:
                    # Get the first prompt and process it
                    first_prompt = PROMPT_QUEUE._queue[0]
                    main_terminal.write(f"[cyan]🤖 Processing first prompt: {first_prompt.prompt}[/cyan]")
                    
                    # Trigger processing
                    if not PROMPT_QUEUE.is_processing():
                        asyncio.create_task(PROMPT_QUEUE._process_queue())
            else:
                main_terminal.write(f"[yellow]No prompts loaded from {queue_file}[/yellow]")
                    
        except Exception as e:
            import traceback
            main_terminal.write(f"[red]❌ Failed to load queue file: {e}[/red]")
            main_terminal.write(f"[dim]{traceback.format_exc()}[/dim]")

    async def _wait_for_runner_idle(self, runner, timeout: float = 5.0) -> None:
        """Wait until the given runner is idle and initialized."""
        if not runner:
            return

        start = time.monotonic()
        while runner.is_running or runner.agent is None:
            if time.monotonic() - start >= timeout:
                return
            await asyncio.sleep(0.05)

    async def _wait_for_all_runners(self, session_manager, terminal_numbers: list[int], timeout: float = 5.0) -> None:
        """Wait until all specified terminal runners are ready or timeout."""
        if not terminal_numbers:
            return

        start = time.monotonic()
        pending = set(terminal_numbers)

        while pending:
            done = []
            for term in list(pending):
                runner = session_manager.terminal_runners.get(term)
                if not runner:
                    # No runner registered yet; keep waiting
                    continue
                if runner.agent is not None and not runner.is_running:
                    done.append(term)
            for term in done:
                pending.discard(term)

            if not pending:
                return

            if time.monotonic() - start >= timeout:
                main_terminal = self.terminal_grid.get_main_terminal()
                if main_terminal:
                    main_terminal.write(
                        f"[yellow]Auto-run warning: time-out while waiting for terminals {sorted(pending)} to initialize.[/yellow]"
                    )
                return

            await asyncio.sleep(0.05)

    async def _wait_for_terminals_visible(
        self,
        grid: "StableTerminalGrid",
        terminal_numbers: list[int],
        timeout: float = 3.0,
    ) -> None:
        """Wait until the terminals are mounted in the grid and ready to display output."""
        if not terminal_numbers:
            return

        start = time.monotonic()
        pending = set(terminal_numbers)

        while pending:
            done = []
            for term_num in list(pending):
                terminal = grid.get_terminal_by_number(term_num)
                if terminal and terminal.is_mounted and getattr(terminal, "output", None):
                    done.append(term_num)
            for term_num in done:
                pending.discard(term_num)

            if not pending:
                return

            if time.monotonic() - start >= timeout:
                main_terminal = self.terminal_grid.get_main_terminal()
                if main_terminal:
                    main_terminal.write(
                        f"[yellow]Auto-run warning: terminals {sorted(pending)} not visible after {timeout:.1f}s.[/yellow]"
                    )
                return

            await asyncio.sleep(0.05)

    async def _run_auto_prompt(
        self,
        session_manager,
        terminal_number: int,
        prompt: str,
        *,
        agent_name: str = "",
        delay: float = 0.0,
    ) -> None:
        """Execute an auto-run prompt when the target terminal is ready."""
        try:
            if delay > 0:
                await asyncio.sleep(delay)

            runner = session_manager.terminal_runners.get(terminal_number)
            if not runner:
                main_terminal = self.terminal_grid.get_main_terminal()
                if main_terminal:
                    display_name = agent_name or f"T{terminal_number}"
                    main_terminal.write(
                        f"[red]Auto-run skipped for T{terminal_number} ({display_name}): runner not registered.[/red]"
                    )
                return

            await self._wait_for_runner_idle(runner)

            # Split chained commands when the auto-run prompt mixes CLI commands with chat
            commands_to_run: list[str] = []
            raw_prompt = prompt or ""
            stripped_prompt = raw_prompt.strip()

            if stripped_prompt:
                # Detect chained CLI commands separated by ';' or newlines
                if (";" in raw_prompt or "\n" in raw_prompt):
                    candidate_segments = [
                        segment.strip() for segment in re.split(r"[;\n]", raw_prompt) if segment.strip()
                    ]
                    if len(candidate_segments) > 1 and any(
                        segment.startswith(("$", "/")) for segment in candidate_segments
                    ):
                        commands_to_run = candidate_segments
                if not commands_to_run:
                    commands_to_run = [stripped_prompt]

            target_terminal = runner.terminal

            for idx, command_text in enumerate(commands_to_run):
                if target_terminal:
                    target_terminal.write_command(command_text)

                if command_text.startswith("/") or command_text.startswith("$"):
                    # Route CLI commands through the command handler so $-prefixed auto-run prompts work
                    if target_terminal:
                        self._handle_cli_command_with_terminal(command_text, target_terminal)
                    else:
                        self._handle_cli_command(command_text)
                else:
                    # Execute chat prompts directly on the runner
                    await runner.execute_command(command_text, show_command=False)

                if self.session_manager:
                    await self.session_manager._process_terminal_queue(terminal_number)

                if idx < len(commands_to_run) - 1:
                    await asyncio.sleep(0.01)

            main_terminal = self.terminal_grid.get_main_terminal()
            if main_terminal:
                display_name = agent_name or f"T{terminal_number}"
                main_terminal.write(
                    f"[dim]Auto-run dispatched for T{terminal_number} ({display_name})[/dim]"
                )
        except Exception as exc:  # noqa: BLE001 - keep session alive
            main_terminal = self.terminal_grid.get_main_terminal()
            if main_terminal:
                display_name = agent_name or f"T{terminal_number}"
                main_terminal.write(
                    f"[red]Auto-run failed for T{terminal_number} ({display_name}): {exc}[/red]"
                )

    async def _initialize_terminal_runner(self, terminal_number: int) -> None:
        """Initialize a terminal runner"""
        await self.session_manager.initialize_terminal(terminal_number)

    async def _add_new_terminal_with_defaults(self) -> None:
        """Add a new terminal with default agent (redteam_agent) and model (alias1)"""
        try:
            # Default values
            default_agent = "redteam_agent"
            default_model = "alias1"
            
            # Add the terminal using the grid's method
            new_terminal = self.terminal_grid.add_agent_terminal(default_agent)
            
            if new_terminal and self.session_manager:
                # Add terminal runner to session manager
                runner = self.session_manager.add_terminal_runner(
                    new_terminal.terminal_number, new_terminal
                )
                
                # Set the default model
                runner.config.model = default_model
                
                # Initialize the terminal runner
                await self._initialize_terminal_runner(new_terminal.terminal_number)
                
                # Update the agent (this will also update the header and UI)
                await self.session_manager.update_terminal_agent(
                    new_terminal.terminal_number, default_agent
                )
                
                # Update the model in the terminal widget
                if hasattr(new_terminal, 'update_model_display'):
                    new_terminal.update_model_display(default_model)
                
        except Exception as e:
            # Log error but don't crash the app
            try:
                main_terminal = self.terminal_grid.get_main_terminal()
                if main_terminal:
                    main_terminal.write(f"[red]Error adding new terminal: {str(e)}[/red]")
            except:
                pass

    def _check_mode(self) -> None:
        """Check if we should switch modes based on PARALLEL_CONFIGS"""
        new_mode = "parallel" if len(PARALLEL_CONFIGS) >= 2 else "single"
        if new_mode != self.current_mode:
            self.current_mode = new_mode
            self._update_mode(new_mode)
        elif (
            new_mode == "parallel"
            and self.terminal_grid.terminal_count != len(PARALLEL_CONFIGS) + 1
        ):
            # In parallel mode but terminal count doesn't match - refresh the setup
            self._update_mode(new_mode)

    def _update_mode(self, mode: str) -> None:
        """Update mode and reconfigure terminals"""
        main_terminal = self.terminal_grid.get_main_terminal()

        if mode == "parallel":
            # Write mode change message first
            if main_terminal:
                main_terminal.write("")
                main_terminal.write(f"[bold cyan]{'═'*70}[/bold cyan]")
                main_terminal.write(
                    f"[bold cyan]PARALLEL MODE ACTIVATED - {len(PARALLEL_CONFIGS)} agents[/bold cyan]"
                )
                main_terminal.write(f"[bold cyan]{'═'*70}[/bold cyan]")
                main_terminal.write("")

            # Setup parallel agents - this will create the right number of terminals
            # For N agents in PARALLEL_CONFIGS, we need N terminals total
            # Terminal 1 will run the first agent, Terminal 2 the second, etc.
            # Remove all but the main terminal first
            self.terminal_grid.remove_agent_terminals()

            # Add terminals for all agents except the first (which uses main terminal)
            for i in range(1, len(PARALLEL_CONFIGS)):
                # Get agent name for this terminal
                agent_name = PARALLEL_CONFIGS[i].agent_name if i < len(PARALLEL_CONFIGS) else f"Agent {i+1}"
                self.terminal_grid.add_agent_terminal(agent_name)

            # Add new terminals to session manager
            if self.session_manager:
                # Get all terminals
                all_terminals = self.terminal_grid.active_terminals

                # Each terminal runs an agent from PARALLEL_CONFIGS
                # Terminal 1 runs PARALLEL_CONFIGS[0], Terminal 2 runs PARALLEL_CONFIGS[1], etc.
                for idx, config in enumerate(PARALLEL_CONFIGS):
                    terminal_number = idx + 1  # Terminal numbers: 1, 2, 3...
                    terminal_index = idx  # Array index: 0, 1, 2...

                    if terminal_index < len(all_terminals):
                        terminal = all_terminals[terminal_index]
                        # Update terminal state with agent name
                        terminal.state.agent_name = config.agent_name
                        # Update the header to show the agent name
                        terminal._update_header()
                        
                        if terminal_number in self.session_manager.terminal_runners:
                            # Update existing runner
                            runner = self.session_manager.terminal_runners[terminal_number]
                            runner.config.agent_name = config.agent_name
                            runner.config.is_parallel = True
                            runner.config.parallel_config = config
                        else:
                            # Add new runner
                            runner = self.session_manager.add_terminal_runner(
                                terminal_number, terminal
                            )
                            runner.config.agent_name = config.agent_name
                            runner.config.is_parallel = True
                            runner.config.parallel_config = config
                            asyncio.create_task(self._initialize_terminal_runner(terminal_number))

                # Enable parallel mode
                self.session_manager.set_parallel_mode(True)
        else:
            # Single mode - clear all agents
            self.terminal_grid.clear_agents()

            if main_terminal:
                main_terminal.write("")
                main_terminal.write(f"[bold cyan]{'═'*70}[/bold cyan]")
                main_terminal.write(f"[bold cyan]SINGLE MODE ACTIVATED[/bold cyan]")
                main_terminal.write(f"[bold cyan]{'═'*70}[/bold cyan]")
                main_terminal.write("")

            # Disable parallel mode
            if self.session_manager:
                self.session_manager.set_parallel_mode(False)

        # Update layout indicator
        self.update_layout_indicator()

    @on(Input.Submitted, "#prompt-input-field")
    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle input submission"""
        # Defensive: ensure event.input is the same widget and clear value
        try:
            if getattr(event.input, "id", "") == "prompt-input-field":
                event.input.value = event.value  # normalize
        except Exception:
            pass
        command = event.value.strip()
        if not command:
            return

        # Add to history
        prompt_widget = self.query_one("#main-input", PromptInput)
        prompt_widget.add_to_history(command)
        
        # Save to history file
        self._save_to_history_file(command)

        # Clear input (and UI) explicitly
        try:
            event.input.value = ""
            self.query_one("#prompt-input-field").value = ""
        except Exception:
            pass

        # Process command (it will handle writing to appropriate terminals)
        asyncio.create_task(self._process_command(command))
        
        # Keep focus on the input for continuous typing
        try:
            prompt_widget.focus()
        except Exception:
            pass

    # Note: no generic Submitted handler to avoid double submission

    async def _process_command(self, command: str) -> None:
        """Process user command"""
        # Import terminal parser
        from cai.tui.utils.terminal_parser import parse_terminal_target

        # Check for terminal prefix syntax (e.g., T2:/model gpt-4o)
        import re
        terminal_prefix_match = re.match(r'^T(\d+):(.+)$', command.strip())
        if terminal_prefix_match:
            target_terminal_num = int(terminal_prefix_match.group(1))
            command = terminal_prefix_match.group(2).strip()

            # Find the target terminal
            target_terminal = None
            for terminal in self.terminal_grid.active_terminals:
                if terminal.terminal_number == target_terminal_num:
                    target_terminal = terminal
                    break

            if not target_terminal:
                main_terminal = self.terminal_grid.get_main_terminal()
                if main_terminal:
                    main_terminal.write(f"[red]Terminal T{target_terminal_num} not found[/red]")
                return

            # Process the command with the specific terminal
            if command.startswith("/") or command.startswith("$"):
                self._handle_cli_command_with_terminal(command, target_terminal)
            else:
                # Chat command for specific terminal
                if target_terminal:
                    target_terminal.write_command(command)

                # Execute in the target terminal
                if self.session_manager and target_terminal_num in self.session_manager.terminal_runners:
                    # Execute only in that terminal
                    await self.session_manager.execute_command(command, terminal_number=target_terminal_num)
            return

        # Meta agent integration - intercept ALL user inputs
        if os.environ.get("CAI_META_AGENT", "false").lower() == "true":
            from cai.tui.meta_agent_controller import get_meta_agent_controller

            meta_controller = get_meta_agent_controller()
            if meta_controller:
                # Set TUI app reference if not already set
                if not meta_controller.tui_app_ref:
                    meta_controller.set_tui_app(self)

                if not command.startswith("/") and not command.startswith("$"):
                    # For all non-command inputs (regular prompts), let meta agent decide
                    result = await meta_controller.process_user_request_async(command)
                    # Always return - meta agent will handle execution
                    return
        
        # Debug terminal state if debug command
        if command == "/debug terminals":
            self._debug_terminal_state()
            return
        
        # Quick test command
        if command == "/test selection":
            main_terminal = self.terminal_grid.get_main_terminal()
            if main_terminal:
                main_terminal.write(f"[yellow]TEST: Terminal selection debug removed[/yellow]")
            return
            
        # Import queue functions
        try:
            from cai.repl.commands.queue import add_to_queue, get_queue
        except ImportError:
            add_to_queue = None
            get_queue = None
            
        # Check for TUI-specific help - DISABLED to fix command truncation bug
        # This was causing /help commands to be intercepted and not processed properly
        # if command == "/help" or command == "/h":
        #     self._show_tui_help()
        #     return
            
        if command.startswith("/") or command.startswith("$"):
            # CLI command - check if it's a terminal-specific command
            parts = command.split()
            cmd_name = parts[0][1:] if parts[0].startswith("/") else parts[0]
            
            # Parse terminal target from command
            args = parts[1:] if len(parts) > 1 else []
            cleaned_args, target_terminal_num = parse_terminal_target(args)
            
            # Check if "all" was specified for broadcast
            broadcast_to_all = False
            if cleaned_args and cleaned_args[-1].lower() == "all":
                broadcast_to_all = True
                cleaned_args = cleaned_args[:-1]  # Remove "all" from args
            
            # Check for parallel pattern before normal processing
            if cmd_name == "agent" and len(parts) > 1:
                agent_arg = parts[1]
                # Numeric selection (20+)
                if agent_arg.isdigit():
                    agent_num = int(agent_arg)
                    if agent_num >= 20:
                        main_terminal = self.terminal_grid.get_main_terminal()
                        await self._handle_parallel_pattern_tui(agent_num, main_terminal)
                        return
                else:
                    # Named pattern selection
                    try:
                        from cai.agents.patterns import get_pattern, PatternType
                        pattern = get_pattern(agent_arg)
                        if pattern and str(getattr(pattern.type, 'value', pattern.type)) == 'parallel':
                            # Build agents list from pattern and dispatch through TeamSelected handler
                            agents = []
                            if getattr(pattern, 'configs', None):
                                for cfg in pattern.configs:
                                    name = getattr(cfg, 'agent_name', None)
                                    if name:
                                        agents.append(name)
                            elif getattr(pattern, 'agents', None):
                                for a in pattern.agents:
                                    name = getattr(a, 'name', None) or str(a)
                                    if name:
                                        agents.append(name)
                            if agents:
                                # Simulate team selection path (reuses logic)
                                self.on_team_selected(type('X', (), {'team_name': agent_arg, 'agents': agents})())
                                return
                    except Exception:
                        pass
            
            # Find target terminal
            target_terminal = None
            if target_terminal_num is not None:
                # Find specific terminal
                for terminal in self.terminal_grid.active_terminals:
                    if terminal.terminal_number == target_terminal_num:
                        target_terminal = terminal
                        break
                        
                if not target_terminal:
                    main_terminal = self.terminal_grid.get_main_terminal()
                    if main_terminal:
                        main_terminal.write(f"[red]Terminal T{target_terminal_num} not found[/red]")
                    return
                    
                # Reconstruct command without terminal specifier
                command = f"{parts[0]} {' '.join(cleaned_args)}" if cleaned_args else parts[0]
            else:
                # Use T1 as default
                target_terminal = None
                            
            # If no target terminal, use the focused terminal for commands that should be terminal-specific
            if not target_terminal:
                # For terminal-specific commands, use the focused terminal
                terminal_specific_commands = ["/compact", "/load", "/save", "/memory", "/flush", "/history", "/replay"]
                if any(command.startswith(cmd) for cmd in terminal_specific_commands):
                    target_terminal = self.terminal_grid.get_focused_terminal()
                    if os.getenv("CAI_DEBUG"):
                        if target_terminal:
                            self.terminal_grid.get_main_terminal().write(f"[cyan]DEBUG: Using focused terminal {target_terminal.terminal_number} for command: {command}[/cyan]")
                        else:
                            self.terminal_grid.get_main_terminal().write(f"[cyan]DEBUG: No focused terminal found for command: {command}[/cyan]")
                
                # If still no target terminal (no focused terminal), use main
                if not target_terminal:
                    target_terminal = self.terminal_grid.get_main_terminal()
                
            # Handle broadcast for CLI commands
            if broadcast_to_all:
                # Convert agent number to agent name if needed (for /agent <number> all)
                if cmd_name == "agent" and cleaned_args and cleaned_args[0].isdigit():
                    agent_number = int(cleaned_args[0])
                    # Only convert for regular agents (< 20), not parallel patterns
                    if agent_number < 20:
                        try:
                            from cai.agents import get_available_agents
                            agents = get_available_agents()
                            # Filter out parallel patterns
                            agent_list = []
                            for key, agent in agents.items():
                                if hasattr(agent, "_pattern"):
                                    pattern = agent._pattern
                                    if hasattr(pattern, "type"):
                                        pattern_type_value = getattr(pattern.type, "value", str(pattern.type))
                                        if pattern_type_value == "parallel":
                                            continue
                                agent_list.append(key)
                            
                            # Check if number is valid
                            if 1 <= agent_number <= len(agent_list):
                                agent_name = agent_list[agent_number - 1]
                                # Replace the number with the agent name
                                cleaned_args[0] = agent_name
                        except Exception:
                            pass  # If conversion fails, continue with the number
                
                # Reconstruct command without "all" suffix for broadcast execution
                command = f"{parts[0]} {' '.join(cleaned_args)}" if cleaned_args else parts[0]
                
                # Get all active terminals (use session_manager for more reliable state)
                active_agents = []
                if self.session_manager and hasattr(self.session_manager, 'terminal_runners'):
                    # Use session_manager as source of truth for active terminals
                    for term_num, runner in self.session_manager.terminal_runners.items():
                        if runner and hasattr(runner, 'config') and runner.config.agent_name:
                            agent_name = runner.config.agent_name
                            agent_id = getattr(runner.config, 'agent_id', 'unknown') if hasattr(runner.config, 'agent_id') else 'unknown'
                            active_agents.append((term_num, agent_name, agent_id))
                else:
                    # Fallback to terminal grid if session_manager is not available
                    for t in self.terminal_grid.active_terminals:
                        if hasattr(t, 'state') and t.state.agent_name:
                            active_agents.append((t.terminal_number, t.state.agent_name, getattr(t.state, 'agent_id', 'unknown')))
                
                main_terminal = self.terminal_grid.get_main_terminal()
                
                # Show broadcast info
                # Don't show broadcasting message
                
                # Create command handlers for parallel execution
                from cai.tui.components.command_handler import CommandHandler
                
                # Execute command in all terminals in parallel using threads
                # Since CLI commands are synchronous, we use threads instead of asyncio
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor(max_workers=len(active_agents)) as executor:
                    futures = []
                    terminal_info = []
                    
                    for terminal_num, agent_name, agent_id in active_agents:
                        # Find the terminal
                        target_term = None
                        for terminal in self.terminal_grid.active_terminals:
                            if terminal.terminal_number == terminal_num:
                                target_term = terminal
                                break
                        
                        if target_term:
                            
                            # Create a function to execute in thread
                            # Use default arguments to capture variables correctly (avoid closure issues)
                            def execute_command(term=target_term, term_num=terminal_num, cmd=command):
                                # Set a flag to indicate we're in a broadcast thread
                                import os
                                os.environ['CAI_BROADCAST_MODE'] = 'true'
                                try:
                                    temp_handler = CommandHandler(term.output, term_num, term.terminal_id)
                                    if hasattr(self.command_handler, 'session_manager'):
                                        temp_handler.session_manager = self.command_handler.session_manager
                                    temp_handler.handle_command(cmd)
                                finally:
                                    # Clear the flag
                                    os.environ.pop('CAI_BROADCAST_MODE', None)
                            
                            # Submit to executor
                            future = executor.submit(execute_command)
                            futures.append(future)
                            terminal_info.append((terminal_num, agent_name))
                    
                    # Wait for all to complete and collect errors
                    # TODO: Make this non-blocking in the future
                    errors = []
                    for i, future in enumerate(futures):
                        try:
                            future.result(timeout=60)  # 60 second timeout
                        except Exception as e:
                            terminal_num, agent_name = terminal_info[i]
                            error_msg = f"Terminal {terminal_num} ({agent_name}): {str(e)}"
                            errors.append(error_msg)
                            if main_terminal:
                                main_terminal.write(f"[red]Error in {error_msg}[/red]")
                
                # Show summary
                if main_terminal:
                    if errors:
                        main_terminal.write(f"[yellow]Command broadcast completed with {len(errors)} errors[/yellow]")
                    else:
                        main_terminal.write(f"[green]Command broadcast completed successfully[/green]")
                
                # Return here to prevent further execution after broadcast
                return
                
            else:
                # Check if this was a parallel pattern that was already handled
                # If so, don't pass it to the regular command handler
                is_parallel_pattern = False
                if cmd_name == "agent" and len(parts) > 1:
                    agent_arg = parts[1]
                    if agent_arg.isdigit():
                        agent_num = int(agent_arg)
                        if agent_num >= 20:
                            is_parallel_pattern = True
                
                if not is_parallel_pattern:
                    # All CLI commands should be handled with the terminal-specific handler
                    # This ensures output goes to the correct terminal
                    self._handle_cli_command_with_terminal(command, target_terminal)
        elif command.lower() in ["exit", "quit"]:
            self.exit()
        else:
            # Chat command - check for terminal target syntax
            words = command.split()
            target_terminal = None
            target_terminal_num = None
            broadcast_to_all = False
            
            if len(words) > 0:
                cleaned_words, target_terminal_num = parse_terminal_target(words)
                
                # Check if "all" was specified for broadcast
                if cleaned_words and cleaned_words[-1].lower() == "all":
                    broadcast_to_all = True
                    cleaned_words = cleaned_words[:-1]  # Remove "all" from words
                
                if target_terminal_num is not None or broadcast_to_all:
                    # Update command without terminal target or "all"
                    command = ' '.join(cleaned_words)
                    
                    # Find target terminal if specific one was requested
                    if target_terminal_num is not None:
                        for terminal in self.terminal_grid.active_terminals:
                            if terminal.terminal_number == target_terminal_num:
                                target_terminal = terminal
                                break
                                
                        if not target_terminal:
                            main_terminal = self.terminal_grid.get_main_terminal()
                            if main_terminal:
                                main_terminal.write(f"[red]Terminal T{target_terminal_num} not found[/red]")
                            return
            
            # Chat command - first check for selected terminal
            main_terminal = self.terminal_grid.get_main_terminal()
            
            # Debug logging to understand command routing
            if os.getenv("CAI_DEBUG") == "2" and main_terminal:
                main_terminal.write(f"[bold magenta]===== PROCESSING CHAT COMMAND =====[/bold magenta]")
                main_terminal.write(f"[magenta]Command: {command[:50]}...[/magenta]")
            
            # Get active agents - include agent ID for better tracking
            active_agents = []
            for t in self.terminal_grid.active_terminals:
                if hasattr(t, 'state') and t.state.agent_name:
                    active_agents.append((t.terminal_number, t.state.agent_name, getattr(t.state, 'agent_id', 'unknown')))
                    if os.getenv("CAI_DEBUG") == "2" and main_terminal:
                        main_terminal.write(f"[dim]Terminal {t.terminal_number}: agent={t.state.agent_name}, is_selected={getattr(t, 'is_selected', False)}[/dim]")
            
            if os.getenv("CAI_DEBUG") == "2" and main_terminal:
                main_terminal.write(f"[magenta]Active agents: {len(active_agents)}[/magenta]")
            
            # Remove global busy check - we'll check per terminal instead
            # This was causing prompts to idle terminals to be queued
            
            # Handle broadcast to all terminals
            if broadcast_to_all:
                # Write command to all terminals and execute in parallel
                if self.session_manager:
                    # Don't show broadcast info in main terminal
                    
                    # Create tasks for parallel execution
                    tasks = []
                    terminal_info = []  # Keep track of terminal info for error reporting
                    
                    for terminal_num, agent_name, agent_id in active_agents:
                        if terminal_num in self.session_manager.terminal_runners:
                            runner = self.session_manager.terminal_runners[terminal_num]
                            # Write command to terminal immediately
                            runner.terminal.write_command(command)
                            # Create task for execution
                            task = self.session_manager.execute_command(command, terminal_number=terminal_num)
                            tasks.append(task)
                            terminal_info.append((terminal_num, agent_name))
                    
                    # Execute all tasks in parallel
                    if tasks:
                        results = await asyncio.gather(*tasks, return_exceptions=True)
                        
                        # Check for errors
                        errors = []
                        for i, result in enumerate(results):
                            if isinstance(result, Exception):
                                terminal_num, agent_name = terminal_info[i]
                                error_msg = f"Terminal {terminal_num} ({agent_name}): {str(result)}"
                                errors.append(error_msg)
                                if main_terminal:
                                    main_terminal.write(f"[red]Error in {error_msg}[/red]")
                        
                        # Show summary
                        if main_terminal:
                            # Don't show broadcast completion messages
                            pass
                    return
            
            # Determine which terminal to use
            if not target_terminal and target_terminal_num is None:
                # No specific terminal specified
                # If only one agent is active, use that terminal
                if len(active_agents) == 1:
                    terminal_num = active_agents[0][0]
                    for terminal in self.terminal_grid.active_terminals:
                        if terminal.terminal_number == terminal_num:
                            target_terminal = terminal
                            break
                else:
                    # Multiple agents or no agents - let selector handle it
                    target_terminal = None
                            
            
            
            
            # Note: Terminal registration is handled when executing the command
            
            
            if target_terminal:
                if hasattr(target_terminal, 'state') and target_terminal.state.agent_name:
                    # Ensure terminal is registered before executing
                    if self.session_manager:
                        if target_terminal.terminal_number not in self.session_manager.terminal_runners:
                            # Need to register and initialize first
                            runner = self.session_manager.add_terminal_runner(target_terminal.terminal_number, target_terminal)
                            await self.session_manager.initialize_terminal(target_terminal.terminal_number)
                        
                        # Write command to the target terminal
                        target_terminal.write_command(command)
                        
                        # Now execute the command
                        await self.session_manager.execute_command(
                            command, 
                            terminal_number=target_terminal.terminal_number
                        )
                        # IMPORTANT: Return here to prevent fallthrough
                        return
                else:
                    # Terminal has no agent
                    target_terminal.write(f"[yellow]No agent loaded in this terminal. Use /agent select <agent_name>[/yellow]")
                    return
            
            # If we have multiple terminals with agents AND no specific target, show selector
            if len(active_agents) > 1 and not target_terminal_num and not broadcast_to_all and not target_terminal:
                if os.getenv("CAI_DEBUG") == "2" and main_terminal:
                    main_terminal.write(f"[yellow]Multiple agents found ({len(active_agents)}), showing selector[/yellow]")
                # Show agent selector panel for multiple agents
                self._show_agent_selector_for_prompt(command)
                # IMPORTANT: Don't execute the command here - wait for user selection
                return
            else:
                # Single agent or no focused terminal
                if os.getenv("CAI_DEBUG") == "2" and main_terminal:
                    main_terminal.write(f"[yellow]Single/no agent path: active_agents={len(active_agents)}[/yellow]")
                # If only one terminal has an agent, execute there
                if len(active_agents) == 1 and self.session_manager:
                    terminal_num = active_agents[0][0]
                    if os.getenv("CAI_DEBUG") == "2":
                        main_terminal.write(f"[green]Executing in Terminal {terminal_num} (only agent)[/green]")
                    
                    # Write command to that terminal
                    if terminal_num in self.session_manager.terminal_runners:
                        runner = self.session_manager.terminal_runners[terminal_num]
                        runner.terminal.write_command(command)
                    
                    await self.session_manager.execute_command(command, terminal_number=terminal_num)
                elif self.session_manager:
                    # Execute in main terminal by default
                    if os.getenv("CAI_DEBUG") == "2" and main_terminal:
                        main_terminal.write(f"[red]No focused terminal and no/multiple agents - executing in main terminal[/red]")
                    self.session_manager.set_parallel_mode(False)
                    await self.session_manager.execute_command(command, terminal_number=1)
                else:
                    # Fallback to old behavior
                    if main_terminal:
                        main_terminal.write_command(command)
                        if self.agent_manager:
                            asyncio.create_task(self.agent_manager.chat_with_agent(command))

    async def _run_in_agents(self, command: str) -> None:
        """Run command in all agent terminals"""
        await self.terminal_grid.broadcast_command(command, "agent")

    def _handle_cli_command_with_terminal(self, command: str, target_terminal) -> None:
        """Execute CLI command with specific terminal as output"""
        # Special handling for /agent new in TUI mode
        if command.strip() == "/agent new" or command.strip().startswith("/agent new "):
            # Show the agent creator panel instead of executing the command
            try:
                agent_creator = self.query_one("#agent-creator-panel", AgentCreatorPanel)
                agent_creator.show()
                return
            except Exception as e:
                main_terminal = self.terminal_grid.get_main_terminal()
                if main_terminal:
                    main_terminal.write(f"[red]Error showing agent creator panel: {str(e)}[/red]")
        
        if target_terminal and target_terminal.terminal_number != 1:
            # Create command handler for specific terminal
            from cai.tui.components.command_handler import CommandHandler
            
            temp_handler = CommandHandler(target_terminal.output, target_terminal.terminal_number, target_terminal.terminal_id)
            if hasattr(self.command_handler, 'session_manager'):
                temp_handler.session_manager = self.command_handler.session_manager
                
            temp_handler.handle_command(command)
        else:
            # Use default command handler
            if self.command_handler:
                self.command_handler.handle_command(command)
                
    async def _handle_parallel_pattern_tui(self, pattern_num: int, initial_terminal) -> None:
        """Handle parallel patterns in TUI mode"""
        main_terminal = self.terminal_grid.get_main_terminal()
            
        try:
            from cai.agents.patterns import get_parallel_patterns, get_pattern
            from cai.agents import get_available_agents
            
            # Get all parallel patterns
            parallel_patterns = get_parallel_patterns()
            
            # Find the pattern by number
            # Agent numbering: 1-19 are regular agents, 20+ are parallel patterns
            # So agent 20 = pattern index 1, agent 21 = pattern index 2, etc.
            pattern_list = list(parallel_patterns.values())
            pattern_idx = pattern_num - 19  # Convert agent number to pattern index
            
            if pattern_idx < 1 or pattern_idx > len(pattern_list):
                if main_terminal:
                    main_terminal.write(f"[red]Pattern {pattern_num} not found[/red]")
                return
                
            pattern = pattern_list[pattern_idx - 1]  # Convert to 0-based index
            
            
            # Get agents from the pattern
            agents = []
            if hasattr(pattern, 'configs'):
                # Pattern has configs (like parallel patterns)
                for config in pattern.configs:
                    try:
                        # ParallelConfig objects have agent_name attribute
                        agent_name = config.agent_name
                        agents.append({'agent': agent_name})
                    except AttributeError:
                        # Fallback if config doesn't have agent_name
                        if isinstance(config, str):
                            agents.append({'agent': config})
                        else:
                            agents.append({'agent': str(config)})
            elif hasattr(pattern, 'agents'):
                # Pattern has direct agents list
                for agent in pattern.agents:
                    agent_name = getattr(agent, 'name', str(agent))
                    agents.append({'agent': agent_name})
            
            if not agents:
                return
                
            # Load first agent in initial terminal
            if initial_terminal and agents:
                first_agent = agents[0]
                agent_name = first_agent.get("agent", "redteam_agent")
                
                if initial_terminal.terminal_number not in self.session_manager.terminal_runners:
                    runner = self.session_manager.add_terminal_runner(
                        initial_terminal.terminal_number, initial_terminal
                    )
                    await self._initialize_terminal_runner(initial_terminal.terminal_number)
                
                # Update the agent - this will also update the header
                await self.session_manager.update_terminal_agent(
                    initial_terminal.terminal_number, agent_name
                )
                
            # Determine start index for creating new terminals
            start_idx = 1 if initial_terminal else 0
            
            # Spawn additional terminals
            for i, agent_config in enumerate(agents[start_idx:], start_idx):
                agent_name = agent_config.get("agent", f"Agent {i+1}")
                self.terminal_grid.add_agent_terminal(agent_name)
                
                # Get newly created terminal
                new_terminal = None
                for t in self.terminal_grid.active_terminals:
                    if t.terminal_number == len(self.terminal_grid.terminals):
                        new_terminal = t
                        break
                        
                if new_terminal and self.session_manager:
                    runner = self.session_manager.add_terminal_runner(
                        new_terminal.terminal_number, new_terminal
                    )
                    await self._initialize_terminal_runner(new_terminal.terminal_number)
                    # Use update_terminal_agent to ensure header updates
                    await self.session_manager.update_terminal_agent(
                        new_terminal.terminal_number, agent_name
                    )
                
        except ImportError as e:
            if main_terminal:
                main_terminal.write(f"[red]Could not import parallel patterns: {str(e)}[/red]")
        except Exception as e:
            if main_terminal:
                main_terminal.write(f"[red]Error in _handle_parallel_pattern_tui: {type(e).__name__}: {str(e)}[/red]")
                
    def _handle_cli_command(self, command: str) -> None:
        """Handle CLI commands"""
        # Parse command for special handling
        parts = command.split()
        cmd_name = parts[0][1:] if parts[0].startswith("/") else parts[0]
        
        # Debug output
        if os.getenv("CAI_DEBUG") == "2":
            main_terminal = self.terminal_grid.get_main_terminal()
            if main_terminal:
                main_terminal.write(f"[yellow]_handle_cli_command: command='{command}'[/yellow]")
        
        # Check if this is a parallel pattern BEFORE processing command
        # This prevents the command handler from processing it as a regular agent selection
        if cmd_name == "agent" and len(parts) > 1:
            agent_arg = parts[1]
            if agent_arg.isdigit():
                agent_num = int(agent_arg)
                if agent_num >= 20:
                    # This is a parallel pattern - don't process it here
                    # It will be handled later
                    return
            
        # Use the main command handler
        if self.command_handler:
            self.command_handler.handle_command(command)
        else:
            # Fallback if no command handler
            main_terminal = self.terminal_grid.get_main_terminal()
            if main_terminal:
                main_terminal.write("[red]Command handler not initialized[/red]")

        # For single agent selection, we should NOT create extra terminals
        # The main terminal should run the agent
        # Only parallel patterns create multiple terminals

        # Handle model command specifically for terminal routing
        if cmd_name == "model" and len(parts) > 1 and self.session_manager:
            model_name = parts[1]
            # This is handled by the command handler, so we don't need to do anything here
            # The command handler will determine whether to update all terminals or just one
            pass
                
        # Check if mode should change after command execution
        # Use call_after_refresh to ensure command has completed
        self.call_after_refresh(self._check_mode)

        # Check if this is a parallel pattern selection in TUI mode
        if cmd_name == "agent" and len(parts) > 1:
            agent_arg = parts[1]
            # Check if it's a number (potential parallel pattern)
            if agent_arg.isdigit():
                agent_num = int(agent_arg)
                # Check if this is a parallel pattern (typically >= 20)
                if agent_num >= 20:
                    # In TUI mode, handle parallel patterns differently
                    # Don't load the pattern like CLI does
                    # Instead, spawn terminals like the sidebar does
                    main_terminal = self.terminal_grid.get_main_terminal()
                    if main_terminal:
                        main_terminal.write(f"[yellow]Parallel pattern {agent_num} detected in TUI mode[/yellow]")
                        main_terminal.write(f"[cyan]Loading agents into separate terminals...[/cyan]")
                    
                    # Import pattern info
                    try:
                        from cai.agents.patterns import get_parallel_patterns
                        
                        # Get all parallel patterns and find by index
                        parallel_patterns = get_parallel_patterns()
                        pattern_list = list(parallel_patterns.values())
                        
                        # Convert agent_num to pattern index (agent 20 = pattern 1, etc.)
                        pattern_idx = agent_num - 19  # Assuming patterns start at agent 20
                        
                        if 1 <= pattern_idx <= len(pattern_list):
                            pattern = pattern_list[pattern_idx - 1]
                            
                            # Get agents from the pattern
                            agents = []
                            if hasattr(pattern, 'configs'):
                                # Pattern has configs (like parallel patterns)
                                for config in pattern.configs:
                                    if hasattr(config, 'agent_name'):
                                        agents.append({'agent': config.agent_name})
                            elif hasattr(pattern, 'agents'):
                                # Pattern has direct agents list
                                for agent in pattern.agents:
                                    agent_name = getattr(agent, 'name', str(agent))
                                    agents.append({'agent': agent_name})
                            
                            
                            # Spawn additional terminals for other agents
                            for i, agent_config in enumerate(agents[1:], 1):
                                agent_name = agent_config.get("agent", f"Agent {i+1}")
                                # Add terminal like sidebar double-click
                                self.terminal_grid.add_agent_terminal(agent_name)
                                
                                # Get the newly created terminal
                                new_terminals = [t for t in self.terminal_grid.active_terminals if t.terminal_number == len(self.terminal_grid.terminals)]
                                if new_terminals and self.session_manager:
                                    new_terminal = new_terminals[0]
                                    # Add to session manager
                                    runner = self.session_manager.add_terminal_runner(new_terminal.terminal_number, new_terminal)
                                    # Initialize agent with full UI sync
                                    asyncio.create_task(
                                        self.session_manager.update_terminal_agent(
                                            new_terminal.terminal_number, agent_name
                                        )
                                    )
                            
                            if main_terminal:
                                main_terminal.write(f"[green]✓ Loaded {len(agents)} agents from pattern {agent_num}[/green]")
                                main_terminal.write("")
                        else:
                            if main_terminal:
                                main_terminal.write(f"[red]Pattern {agent_num} not found[/red]")
                    except ImportError as e:
                        if main_terminal:
                            main_terminal.write(f"[red]Could not import parallel patterns: {str(e)}[/red]")
                    except Exception as e:
                        if main_terminal:
                            main_terminal.write(f"[red]Error loading parallel pattern: {type(e).__name__}: {str(e)}[/red]")
                    
                    # Don't continue with normal agent command processing
                    return
        
        # Update agent manager if needed
        if self.command_handler and self.command_handler.current_agent and command.startswith("/agent"):
            self.agent_manager.agent = self.command_handler.current_agent
            self.agent_manager.current_agent_name = self.command_handler.current_agent_name

            # Load agent in main terminal
            main_terminal = self.terminal_grid.get_main_terminal()
            
            if main_terminal and self.session_manager:
                # Update the terminal's agent name in its state
                main_terminal.state.agent_name = self.command_handler.current_agent_name
                main_terminal._update_header()
                
                # Ensure terminal is in session manager
                if main_terminal.terminal_number not in self.session_manager.terminal_runners:
                    runner = self.session_manager.add_terminal_runner(main_terminal.terminal_number, main_terminal)
                    asyncio.create_task(self._initialize_terminal_runner(main_terminal.terminal_number))
                
                # Switch agent in the main terminal with full UI sync
                asyncio.create_task(
                    self.session_manager.update_terminal_agent(
                        main_terminal.terminal_number,
                        self.command_handler.current_agent_name,
                    )
                )


    @on(ListView.Selected, "#agent-list")
    def on_agent_selected(self, event: ListView.Selected) -> None:
        """Handle agent selection from sidebar"""
        agent_name = self.sidebar.get_selected_agent()
        if agent_name:
            self._process_command(f"/agent select {agent_name}")

    @on(AgentDoubleClicked)
    def on_agent_double_clicked(self, event: AgentDoubleClicked) -> None:
        """Handle double-click on agent in sidebar - spawn in new terminal"""
        agent_name = event.agent_name
        if agent_name:
            terminal_count = len(self.terminal_grid.terminals)
            self.terminal_grid.add_agent_terminal(agent_name)
            new_terminals = [t for t in self.terminal_grid.active_terminals if t.terminal_number == terminal_count + 1]
            if new_terminals and self.session_manager:
                new_terminal = new_terminals[0]
                self.session_manager.add_terminal_runner(new_terminal.terminal_number, new_terminal)
                asyncio.create_task(
                    self.session_manager.update_terminal_agent(
                        new_terminal.terminal_number, agent_name
                    )
                )
                # Focus the new terminal
                self.terminal_grid.focus_terminal(new_terminal.terminal_id)
                
                # Show confirmation in the new terminal
                new_terminal.write(f"[bold green]Agent '{agent_name}' spawned in Terminal {new_terminal.terminal_number}[/bold green]")
                new_terminal.write("")

    @on(TeamSelected)
    def on_team_selected(self, event: TeamSelected) -> None:
        """Handle preconfigured team selection to open/reuse up to 4 terminals and assign agents.

        Rules (per user request):
        - Teams are fixed to 4 members max; do not exceed 4 terminals.
        - On click, auto-open terminals until there are 4 (if fewer exist).
        - If there are already 4 terminals, reuse them and just switch agents (no new terminals).
        - Special case: if only one terminal exists and a 4-agent team is chosen and it contains 2 types,
          place the first agent in terminal 1 and the other type in terminals 2-4.
        """
        try:
            team_agents = list(event.agents or [])
            if not team_agents:
                return
            asyncio.create_task(self._apply_team_selection(event.team_name, team_agents))
        except Exception as e:
            mt = self.terminal_grid.get_main_terminal()
            if mt:
                mt.write(f"[red]Error applying team: {type(e).__name__}: {e}[/red]")

    async def _apply_team_selection(self, team_name: str, team_agents: list[str]) -> None:
        desired_n = min(4, len(team_agents))
        grid = self.terminal_grid
        sm = self.session_manager
        try:
            self.switch_to_tab("terminal")
        except Exception:
            pass
        current_n = len(grid.terminals)
        for i in range(current_n, desired_n):
            next_agent = team_agents[min(i, len(team_agents) - 1)]
            grid.add_agent_terminal(next_agent)
            await asyncio.sleep(0)
        all_terms = sorted(grid.active_terminals, key=lambda t: t.terminal_number)
        for idx in range(desired_n):
            term_num = idx + 1
            term = next((t for t in all_terms if t.terminal_number == term_num), None)
            if not term:
                continue
            # Assign agents in exact order as defined in team configuration
            agent_for_term = team_agents[idx if idx < len(team_agents) else -1]
            if term_num not in sm.terminal_runners:
                sm.add_terminal_runner(term_num, term)
            await sm.update_terminal_agent(term_num, agent_for_term)
            
            # Sync the dropdown to reflect the agent change (reuse existing function)
            try:
                from cai.repl.commands.agent import _sync_tui_agent_selection
                # Temporarily set the active terminal for sync
                old_env = os.getenv("CAI_ACTIVE_COMMAND_TERMINAL", "")
                os.environ["CAI_ACTIVE_COMMAND_TERMINAL"] = str(term_num)
                _sync_tui_agent_selection(agent_for_term)
                # Restore previous environment
                if old_env:
                    os.environ["CAI_ACTIVE_COMMAND_TERMINAL"] = old_env
                else:
                    os.environ.pop("CAI_ACTIVE_COMMAND_TERMINAL", None)
            except Exception:
                pass
        main_term = grid.get_main_terminal()
        if main_term:
            grid.focus_terminal(main_term.terminal_id)
            mapping = []
            for i in range(1, desired_n + 1):
                # Assign agents in exact order as defined in team configuration
                eff = team_agents[i - 1] if i - 1 < len(team_agents) else team_agents[-1]
                mapping.append(f"T{i}→{eff}")
            main_term.write(f"[bold green]Team selected: {team_name}[/bold green]")
            main_term.write("Assignment: " + ", ".join(mapping))
            main_term.write("")

    def action_toggle_sidebar(self) -> None:
        """Toggle sidebar action"""
        # Guard against None if sidebar not yet queried
        if not self.sidebar:
            try:
                self.sidebar = self.query_one("#sidebar", Sidebar)
            except Exception:
                self.sidebar = None
        if self.sidebar:
            self.sidebar.toggle()
            # Update our reactive property to match sidebar state
            self.sidebar_visible = self.sidebar.visible
        else:
            # Defer toggle after first refresh if sidebar isn't ready yet
            def deferred_toggle():
                sidebar = self.query_one("#sidebar", Sidebar)
                sidebar.toggle()
                self.sidebar_visible = sidebar.visible
            self.call_after_refresh(deferred_toggle)
    
    def watch_sidebar_visible(self, visible: bool) -> None:
        """Watch sidebar visibility changes and adjust top bar position"""
        try:
            top_bar = self.query_one("#top-bar", Container)
            if visible:
                # Sidebar is visible - top bar at normal position
                top_bar.remove_class("sidebar-collapsed")
            else:
                # Sidebar is collapsed - move entire top bar left
                top_bar.add_class("sidebar-collapsed")
        except Exception:
            # Top bar might not be mounted yet
            pass
    
    def switch_to_tab(self, tab_id: str) -> None:
        """Switch to a specific tab"""
        tabbed_content = self.query_one("#main-tabs", TabbedContent)
        tabbed_content.active = tab_id
        self.current_view = tab_id
        
        # Focus on input when switching to terminal
        if tab_id == "terminal":
            self.set_timer(0.1, lambda: self.query_one("#main-input").focus())
    
    
    def action_show_terminal(self) -> None:
        """Show terminal tab via keyboard shortcut"""
        self.switch_to_tab("terminal")
    
    def action_show_ctr(self) -> None:
        """Show CTR tab via keyboard shortcut"""
        self.switch_to_tab("ctr")
    
    def action_cycle_tabs(self) -> None:
        """Cycle through tabs"""
        if self.current_view == "terminal":
            self.switch_to_tab("ctr")
        else:
            self.switch_to_tab("terminal")
    
    # Removed: Terminal prompt bar handlers
    # @on(TerminalPromptSubmitted)
    # def on_terminal_prompt_submitted(self, message: TerminalPromptSubmitted) -> None:
    #     """Handle prompt submission from terminal prompt bar"""
    #     # Execute the prompt directly in the specified terminal
    #     if self.session_manager:
    #         asyncio.create_task(
    #             self.session_manager.execute_command(
    #                 message.prompt,
    #                 terminal_number=message.terminal_number
    #             )
    #         )
    
    def _show_agent_selector_for_prompt(self, prompt: str) -> None:
        """Show the agent selector panel for a prompt"""
        main_terminal = self.terminal_grid.get_main_terminal()
        
        # Get all available agents in terminals
        available_agents = []
        terminal_agent_map = {}  # Map agent names to terminal numbers
        
        # Only show terminals that have agents loaded
        terminals_with_agents = [t for t in self.terminal_grid.active_terminals if t.state.agent_name]
        
        if terminals_with_agents:
            # Show only loaded agents
            for terminal in terminals_with_agents:
                agent_name = terminal.state.agent_name
                # Make agent names unique by adding terminal number
                display_name = f"{agent_name} (Terminal {terminal.terminal_number})"
                available_agents.append(display_name)
                terminal_agent_map[display_name] = (terminal.terminal_number, agent_name)
                
            if os.getenv("CAI_DEBUG") == "2" and main_terminal:
                main_terminal.write(f"[cyan]Found {len(terminals_with_agents)} terminals with agents[/cyan]")
        else:
            # No terminals have agents loaded yet
            if main_terminal:
                main_terminal.write(f"[yellow]No terminals have agents loaded. Load agents first.[/yellow]")
            return
        
        
        if available_agents:
            # Store the mapping for later use
            self._terminal_agent_map = terminal_agent_map
            try:
                agent_selector = self.query_one("#agent-selector-panel", AgentSelectorPanel)
                # Debug message removed - was causing visual noise
                agent_selector.show_for_prompt(prompt, available_agents)
            except Exception as e:
                # Log the error for debugging
                if main_terminal:
                    main_terminal.write(f"[red]ERROR showing agent selector: {str(e)}[/red]")
                    import traceback
                    main_terminal.write(f"[red]{traceback.format_exc()}[/red]")
            
    @on(AgentSelectionConfirmed)
    def on_agent_selection_confirmed(self, event: AgentSelectionConfirmed) -> None:
        """Handle agent selection confirmation"""
        selected_display_names = event.selected_agents
        prompt = event.prompt
        
        # Get the terminal mapping
        terminal_agent_map = getattr(self, '_terminal_agent_map', {})
        
        if self.session_manager:
            # Execute command only for selected agents
            for display_name in selected_display_names:
                if display_name in terminal_agent_map:
                    terminal_number, agent_name = terminal_agent_map[display_name]
                    # Find the terminal by number
                    for terminal in self.terminal_grid.active_terminals:
                        if terminal.terminal_number == terminal_number:
                            # Execute through session manager for this specific terminal
                            # (session manager will write the command)
                            asyncio.create_task(
                                self.session_manager.execute_command(
                                    prompt, 
                                    terminal_number=terminal.terminal_number
                                )
                            )
                            break
        else:
            # Fallback - write to terminals
            for display_name in selected_display_names:
                if display_name in terminal_agent_map:
                    terminal_number, agent_name = terminal_agent_map[display_name]
                    for terminal in self.terminal_grid.active_terminals:
                        if terminal.terminal_number == terminal_number:
                            # Session manager would write the command,
                            # but in fallback we need to do it
                            terminal.write_command(prompt)
                            break
    
    @on(AgentSelectionCancelled)
    def on_agent_selection_cancelled(self, event: AgentSelectionCancelled) -> None:
        """Handle agent selection cancellation"""
        # Just hide the panel, nothing else to do
        pass
    
    @on(AgentCreationConfirmed)
    def on_agent_creation_confirmed(self, event: AgentCreationConfirmed) -> None:
        """Handle agent creation confirmation"""
        from cai.agents.agent_builder import AgentBuilder
        
        main_terminal = self.terminal_grid.get_main_terminal()
        if main_terminal:
            try:
                # Save the agent file
                filepath = AgentBuilder.save_agent_file(event.agent_config)
                main_terminal.write(f"\n[green]✅ Agent created successfully![/green]")
                main_terminal.write(f"[green]File saved to: {filepath}[/green]")
                main_terminal.write("\n[yellow]To use your new agent:[/yellow]")
                main_terminal.write(f"1. Import it in __init__.py")
                main_terminal.write(f"2. Run: /agent {AgentBuilder.sanitize_name(event.agent_config['name'])}")
            except Exception as e:
                main_terminal.write(f"\n[red]Error creating agent: {str(e)}[/red]")
                import traceback
                main_terminal.write(f"[red]{traceback.format_exc()}[/red]")
    
    @on(AgentCreationCancelled)
    def on_agent_creation_cancelled(self, event: AgentCreationCancelled) -> None:
        """Handle agent creation cancellation"""
        # Just hide the panel, nothing else to do
        pass
    
    def on_click(self, event) -> None:
        """Handle click events on static elements"""
        if hasattr(event, 'widget'):
            if event.widget.id == "sidebar-toggle-btn":
                self.action_toggle_sidebar()
                event.stop()
            elif event.widget.id == "app-close-btn":
                self.action_quit()
                event.stop()
            elif event.widget.id == "add-terminal-btn":
                asyncio.create_task(self._add_new_terminal_with_defaults())
                event.stop()
    
    @on(Button.Pressed, "#tab-terminal-btn")
    def on_terminal_tab_pressed(self, event: Button.Pressed) -> None:
        """Handle Terminal tab button press"""
        self.switch_to_tab("terminal")
        self._update_tab_appearance("terminal")
        event.stop()
    
    @on(Button.Pressed, "#tab-graph-btn")
    def on_graph_tab_pressed(self, event: Button.Pressed) -> None:
        """Handle Graph tab button press"""
        self.switch_to_tab("ctr")
        self._update_tab_appearance("ctr")
        event.stop()
    
    @on(Button.Pressed, "#tab-help-btn")
    def on_help_tab_pressed(self, event: Button.Pressed) -> None:
        """Handle Help tab button press"""
        self.switch_to_tab("help")
        self._update_tab_appearance("help")
        event.stop()
    
    def _update_tab_appearance(self, active_tab: str) -> None:
        """Update the appearance of custom tab buttons"""
        try:
            terminal_btn = self.query_one("#tab-terminal-btn", Button)
            graph_btn = self.query_one("#tab-graph-btn", Button)
            help_btn = self.query_one("#tab-help-btn", Button)
            
            # Remove active class from all tabs
            terminal_btn.remove_class("active-tab")
            graph_btn.remove_class("active-tab")
            help_btn.remove_class("active-tab")
            
            # Add active class to the correct tab
            if active_tab == "terminal":
                terminal_btn.add_class("active-tab")
            elif active_tab == "ctr":
                graph_btn.add_class("active-tab")
            elif active_tab == "help":
                help_btn.add_class("active-tab")
        except Exception:
            # Buttons might not be mounted yet
            pass

    def action_clear(self) -> None:
        """Clear screen"""
        self.terminal_grid.clear_all()

    def action_parallel_prompt(self) -> None:
        """Send prompt to all agents"""
        if self.current_mode != "parallel":
            main_terminal = self.terminal_grid.get_main_terminal()
            if main_terminal:
                main_terminal.write("[yellow]Not in parallel mode[/yellow]")
            return

        prompt = "Tell me about your capabilities"
        asyncio.create_task(self._run_in_agents(prompt))

    def action_next_terminal(self) -> None:
        """Focus next terminal"""
        self.terminal_grid.cycle_focus(forward=True)

    def action_prev_terminal(self) -> None:
        """Focus previous terminal"""
        self.terminal_grid.cycle_focus(forward=False)

    def action_cancel_all(self) -> None:
        """Cancel all running agents. Press ESC twice quickly to exit."""
        import time
        current_time = time.time()
        
        # Check if this is a double ESC press
        if current_time - self._last_esc_time < self._esc_exit_threshold:
            # Double ESC detected - exit the application
            self.exit()
        else:
            # Single ESC - cancel all agents
            self._last_esc_time = current_time
            
            # Prevent concurrent cancellations
            if not self._cancelling:
                self._cancelling = True
                # Cancel any existing cancel task
                if self._cancel_task and not self._cancel_task.done():
                    # Don't try to cancel the cancel task - just return
                    return
                    
                # Create new cancel task
                self._cancel_task = asyncio.create_task(self._do_cancel_all())
    
    async def _do_cancel_all(self) -> None:
        """Wrapper to handle cancellation and reset flag"""
        try:
            await self._cancel_all_agents()
        finally:
            self._cancelling = False
    
    def _debug_terminal_state(self) -> None:
        """Debug current terminal state"""
        main_terminal = self.terminal_grid.get_main_terminal()
        if not main_terminal:
            return
            
        main_terminal.write("[bold cyan]=== TERMINAL STATE DEBUG ===[/bold cyan]")
        main_terminal.write(f"Total terminals: {len(self.terminal_grid.terminals)}")
        
        for tid, terminal in self.terminal_grid.terminals.items():
            main_terminal.write(f"\nTerminal {terminal.terminal_number}:")
            main_terminal.write(f"  - ID: {tid}")
            main_terminal.write(f"  - Agent: {terminal.state.agent_name or 'None'}")
            if self.session_manager:
                main_terminal.write(f"  - In session manager: {terminal.terminal_number in self.session_manager.terminal_runners}")
        main_terminal.write("[bold cyan]==========================[/bold cyan]\n")
    
    def _ensure_prompt_focus(self) -> None:
        """Ensure prompt input always has keyboard focus"""
        try:
            # Get the currently focused widget
            focused = self.focused
            
            # Check if focus is not on the prompt input
            prompt_input_field = self.query_one("#prompt-input-field")
            
            # If focus is not on the prompt input field, restore it
            if focused != prompt_input_field:
                # Check if focused widget is a terminal or its children
                if focused and hasattr(focused, 'id'):
                    # Don't steal focus from modals or special inputs
                    if 'modal' in focused.id or 'selector' in focused.id:
                        return
                    # Don't interfere if a terminal is being clicked
                    if 'terminal' in str(focused.id).lower() or isinstance(focused, UniversalTerminal):
                        # Still restore focus but don't clear selection
                        prompt_input_field.focus()
                        return
                
                # Restore focus to prompt
                prompt_input_field.focus()
        except Exception:
            # Silently ignore any errors in focus management
            pass
    
    async def _cancel_all_agents(self) -> None:
        """Cancel all running agents"""
        try:
            if self.session_manager:
                # Cancel all running tasks
                await self.session_manager.cancel_all_tasks()
                
                # Show notification in main terminal
                if 1 in self.session_manager.terminal_runners:
                    main_terminal = self.session_manager.terminal_runners[1].terminal
                    # Don't show cancellation message
                    pass
        except asyncio.CancelledError:
            # This is expected when cancelling - just ignore
            pass
        except RuntimeError as e:
            # Handle "cannot reuse already awaited coroutine" error
            if "cannot reuse already awaited coroutine" in str(e):
                # Just ignore this error - it means cancellation is already in progress
                pass
            else:
                # Log other runtime errors
                import logging
                logging.getLogger("CAITerminal").error(f"Runtime error cancelling agents: {e}")
        except Exception as e:
            # Log error but continue
            import logging
            logging.getLogger("CAITerminal").error(f"Error cancelling agents: {e}")

    def action_cancel_selected(self) -> None:
        """Cancel execution in selected/focused terminal"""
        asyncio.create_task(self._cancel_selected_agent())
    
    async def _cancel_selected_agent(self) -> None:
        """Cancel execution in the focused terminal"""
        if not self.terminal_grid or not self.session_manager:
            # If no grid or session, just clear input
            if self.prompt_input:
                self.prompt_input.clear()
            return
            
        # Get the focused terminal
        focused_terminal = self.terminal_grid.get_focused_terminal()
        if not focused_terminal:
            # No terminal selected - clear the prompt input
            if self.prompt_input:
                self.prompt_input.clear()
            return
            
        # Find the terminal number from the terminal widget
        terminal_number = focused_terminal.terminal_number
        
        # Check if we have a runner for this terminal
        if terminal_number in self.session_manager.terminal_runners:
            runner = self.session_manager.terminal_runners[terminal_number]
            
            # Cancel the task in this terminal
            if runner.is_running:
                await runner.cancel_current_task()
                focused_terminal.write(f"[yellow]Cancelled execution in Terminal {terminal_number}[/yellow]")
            else:
                focused_terminal.write(f"[dim]No active execution in Terminal {terminal_number}[/dim]")

    def action_close_terminal(self) -> None:
        """Close the currently focused terminal (except main terminal)"""
        if not self.terminal_grid:
            return
            
        focused_terminal = self.terminal_grid.get_focused_terminal()
        if not focused_terminal:
            return
            
        # Don't allow closing the main terminal
        if focused_terminal.terminal_id == self.terminal_grid.main_terminal_id:
            focused_terminal.write("[yellow]Cannot close the main terminal (T1)[/yellow]")
            return
            
        # Don't allow closing if only one terminal
        if self.terminal_grid.terminal_count <= 1:
            focused_terminal.write("[yellow]Cannot close the only terminal[/yellow]")
            return
            
        # Get terminal info before removing
        terminal_number = focused_terminal.terminal_number
        terminal_id = focused_terminal.terminal_id
        
        # Clean up the terminal runner and agent before removing
        if self.session_manager and terminal_number in self.session_manager.terminal_runners:
            # Get the runner
            runner = self.session_manager.terminal_runners[terminal_number]
            
            # Cancel any running tasks
            asyncio.create_task(runner.cleanup())
            
            # Remove from session manager
            del self.session_manager.terminal_runners[terminal_number]
            
            # Decrement terminal count in agent manager
            from cai.sdk.agents.simple_agent_manager import AGENT_MANAGER
            AGENT_MANAGER.decrement_terminal_count()
            
            # Clean up orphaned parallel agents
            AGENT_MANAGER.cleanup_orphaned_parallel_agents()
        
        # Remove the terminal from grid
        if self.terminal_grid.remove_terminal(terminal_id):
            # Show notification in main terminal
            main_terminal = self.terminal_grid.get_main_terminal()
            if main_terminal:
                main_terminal.write(f"[red]Closed Terminal {terminal_number}[/red]")
            
            # Update layout
            self.update_layout_indicator()
            
            # Aggressively clean orphaned TUI agent registry entries
            try:
                from cai.sdk.agents.simple_agent_manager import AGENT_MANAGER
                AGENT_MANAGER.cleanup_tui_orphaned_agents()
            except Exception:
                pass
        else:
            focused_terminal.write("[red]Failed to close terminal[/red]")
    
    def action_clear_input(self) -> None:
        """Clear the prompt input field"""
        if self.prompt_input:
            self.prompt_input.clear()
            self.prompt_input.focus()
    
    def action_toggle_terminal_view(self) -> None:
        """Toggle between showing all terminals and only the focused one"""
        if self.terminal_grid:
            # Toggle the view based on current state
            if self.terminal_grid.is_showing_only_focused():
                self.terminal_grid.show_all_terminals()
                # Show notification
                focused_terminal = self.terminal_grid.get_focused_terminal()
                if focused_terminal:
                    focused_terminal.write("[cyan]📐 Restored grid view - showing all terminals[/cyan]")
            else:
                # Get the focused terminal info before switching
                focused_terminal = self.terminal_grid.get_focused_terminal()
                terminal_num = focused_terminal.terminal_number if focused_terminal else 1
                
                self.terminal_grid.show_only_focused()
                # Show notification in the focused terminal
                focused_terminal = self.terminal_grid.get_focused_terminal()
                if focused_terminal:
                    focused_terminal.write(f"[bold cyan]🖥️  Fullscreen mode - Terminal {terminal_num}[/bold cyan]")
                    focused_terminal.write("[dim]• Ctrl+T: Return to grid view[/dim]")
                    focused_terminal.write("[dim]• Ctrl+N/B: Switch to other terminals (in fullscreen)[/dim]")
    
    def action_show_queue(self) -> None:
        """Show prompt queue status"""
        status = PROMPT_QUEUE.get_queue_status()
        
        # Display in main terminal
        if self.terminal_grid:
            main_terminal = self.terminal_grid.get_main_terminal()
            if main_terminal:
                main_terminal.write("[bold cyan]╭─ Prompt Queue Status ─╮[/bold cyan]")
                main_terminal.write(f"[cyan]Queue Length:[/cyan] {status['queue_length']}")
                main_terminal.write(f"[cyan]Processing:[/cyan] {'Yes' if status['processing'] else 'No'}")
                
                if status['current_prompt']:
                    main_terminal.write(f"[cyan]Current:[/cyan] {status['current_prompt'][:50]}...")
                    
                if status['prompts']:
                    main_terminal.write("[cyan]Queued Prompts:[/cyan]")
                    for i, prompt in enumerate(status['prompts'], 1):
                        main_terminal.write(f"  {i}. {prompt['prompt']} (priority: {prompt['priority']})")
                else:
                    main_terminal.write("[dim]No prompts queued[/dim]")
                    
                main_terminal.write("[bold cyan]╰────────────────────────╯[/bold cyan]")
                main_terminal.write("")
    
    def _show_tui_help(self) -> None:
        """Show TUI-specific help"""
        main_terminal = self.terminal_grid.get_main_terminal()
        if not main_terminal:
            return
            
        main_terminal.write("[bold cyan]╭─ CAI TUI Commands & Shortcuts ─╮[/bold cyan]")
        main_terminal.write("")
        
        main_terminal.write("[bold yellow]Keyboard Shortcuts:[/bold yellow]")
        main_terminal.write("  [cyan]Ctrl+Q[/cyan]     - Exit CAI")
        main_terminal.write("  [cyan]Ctrl+L[/cyan]     - Clear all terminals")
        main_terminal.write("  [cyan]Ctrl+P[/cyan]     - Send prompt to all agents")
        main_terminal.write("  [cyan]Ctrl+S[/cyan]     - Toggle sidebar")
        main_terminal.write("  [cyan]Ctrl+N[/cyan]     - Next terminal")
        main_terminal.write("  [cyan]Ctrl+B[/cyan]     - Previous terminal")
        main_terminal.write("  [cyan]Ctrl+C[/cyan]     - Cancel selected agent")
        main_terminal.write("  [cyan]Ctrl+E[/cyan]     - Close selected terminal")
        main_terminal.write("  [cyan]ESC[/cyan]        - Cancel all agents")
        main_terminal.write("  [cyan]Ctrl+Shift+Q[/cyan] - Show prompt queue")
        main_terminal.write("")
        
        main_terminal.write("[bold yellow]Queue Management:[/bold yellow]")
        main_terminal.write("  [cyan]/queue[/cyan]          - Show current queue")
        main_terminal.write("  [cyan]/queue add <p>[/cyan]  - Add prompt to queue")
        main_terminal.write("  [cyan]/queue remove N[/cyan] - Remove item N from queue")
        main_terminal.write("  [cyan]/queue clear[/cyan]    - Clear all queued prompts")
        main_terminal.write("  [dim]• Prompts auto-queue when agents are busy[/dim]")
        main_terminal.write("")
        
        main_terminal.write("[bold yellow]TUI-Specific Commands:[/bold yellow]")
        main_terminal.write("  [cyan]/help[/cyan]           - Show this TUI help")
        main_terminal.write("")
        
        main_terminal.write("[bold yellow]Terminal Selection:[/bold yellow]")
        main_terminal.write("  [dim]• Click on a terminal to select it (green indicator)[/dim]")
        main_terminal.write("  [dim]• Commands (/) execute in the selected terminal[/dim]")
        main_terminal.write("  [dim]• Prompts always show agent selector (if multiple agents)[/dim]")
        main_terminal.write("")
        
        main_terminal.write("[bold yellow]Standard CAI Commands:[/bold yellow]")
        main_terminal.write("  [dim]All standard CAI commands work as usual[/dim]")
        main_terminal.write("")
        
        main_terminal.write("[bold cyan]╰─────────────────────────────────╯[/bold cyan]")
        main_terminal.write("")
    
    async def _process_queued_prompt(self, prompt: str, terminal_number: Optional[int] = None) -> None:
        """Process a prompt from the queue"""
        try:
            # Check if any runner is still busy
            if self.session_manager:
                for runner in self.session_manager.terminal_runners.values():
                    if runner.is_running:
                        # Still busy, re-queue the prompt
                        await PROMPT_QUEUE.add_prompt(prompt, terminal_number)
                        return
            
            # Show the prompt being processed
            main_terminal = self.terminal_grid.get_main_terminal()
            if main_terminal:
                main_terminal.write(f"[cyan]🤖 Processing from queue:[/cyan] {prompt}")
            
            # Process the command through the normal flow
            await self._process_command(prompt)
            
        except Exception as e:
            import logging
            logging.getLogger("CAITerminal").error(f"Error processing queued prompt: {e}")

    def action_quit(self) -> None:
        """Exit application"""
        # Clean up before exit
        asyncio.create_task(self._cleanup_before_exit())

    async def _cleanup_before_exit(self) -> None:
        """Clean up resources before exit"""
        try:
            if self.session_manager:
                # Cancel all running tasks
                await self.session_manager.cancel_all_tasks()

                # Clean up session
                self.session_manager.cleanup()
        except Exception as e:
            # Log error but continue with exit
            import logging

            logging.getLogger("CAITerminal").error(f"Error during cleanup: {e}")
        finally:
            # Clear TUI mode
            os.environ.pop("CAI_TUI_MODE", None)

            # Exit the app
            self.exit()

    def update_layout_indicator(self) -> None:
        """Update layout indicator in title"""
        terminal_count = self.terminal_grid.terminal_count
        layout_mode = self.terminal_grid.layout_mode.upper()

        title = t('tui_title_format', layout=layout_mode, count=terminal_count)
        self.title = title

    def on_unmount(self, event: Unmount) -> None:
        """Clean up resources when app is being unmounted"""
        if self.session_manager:
            self.session_manager.cleanup()
        # No global patches to remove

    def action_show_agent_selector_for_prompt(self, terminal_id: str) -> None:
        """Shows the agent selector panel."""
        # This is a placeholder for a more complex multi-agent prompt workflow.
        # For now, we'll just show the panel with available agents.
        agent_selector = self.query_one(AgentSelectorPanel)
        available_agents = self.agent_manager.get_available_agent_names()
        
        # In a full implementation, we would get the prompt from the input
        # and pass it here. For now, we pass a placeholder.
        prompt_placeholder = "Select agents to run a command..."
        
        agent_selector.show_for_prompt(prompt_placeholder, available_agents)

    def action_focus_main_input(self) -> None:
        """Focus the main input."""
        self.query_one("#main_input", Input).focus()
    
    def _initialize_command_history(self) -> None:
        """Initialize command history from history file"""
        # Setup history file - use same location as CLI
        history_dir = Path.home() / ".cai"
        history_dir.mkdir(exist_ok=True, parents=True)
        self.history_file = history_dir / "history.txt"
        
        # Load existing history into the prompt widget
        prompt_widget = self.query_one("#main-input", PromptInput)
        if prompt_widget and prompt_widget._input_widget:
            # Load history from file
            if self.history_file.exists():
                try:
                    with open(self.history_file, "r", encoding="utf-8") as f:
                        # Read all lines
                        all_lines = f.readlines()
                        
                        # Parse history file format - skip timestamps and empty lines
                        history_commands = []
                        for line in all_lines:
                            line = line.strip()
                            # Skip empty lines and timestamp lines (starting with #)
                            if not line or line.startswith("#"):
                                continue
                            # Remove leading + if present (prompt toolkit format)
                            if line.startswith("+"):
                                line = line[1:]
                            # Skip commands that are just whitespace after processing
                            if line.strip():
                                history_commands.append(line)
                        
                        # Take last 100 unique commands
                        seen = set()
                        unique_commands = []
                        for cmd in reversed(history_commands):
                            if cmd not in seen:
                                seen.add(cmd)
                                unique_commands.append(cmd)
                                if len(unique_commands) >= 100:
                                    break
                        
                        # Add to widget's history (already in reverse order)
                        prompt_widget._input_widget.command_history = unique_commands
                except Exception as e:
                    # Log error but continue without history
                    main_terminal = self.terminal_grid.get_main_terminal() if self.terminal_grid else None
                    if main_terminal:
                        main_terminal.write(f"[yellow]Warning: Could not load history: {e}[/yellow]")
    
    def _save_to_history_file(self, command: str) -> None:
        """Save command to history file"""
        if self.history_file and command.strip():
            try:
                with open(self.history_file, "a", encoding="utf-8") as f:
                    f.write(f"{command}\n")
            except Exception:
                # Silently ignore history file write errors
                pass
    
    def _compute_session_time_seconds(
        self,
        active_time_seconds: Optional[float] = None,
        idle_time_seconds: Optional[float] = None,
    ) -> float:
        """Return elapsed session seconds with fallbacks."""
        session_start = getattr(self, "_session_start_time", None)
        if session_start:
            elapsed = time.time() - session_start
            if elapsed > 0:
                return elapsed

        # Fall back to timers if available
        active = active_time_seconds or 0.0
        idle = idle_time_seconds or 0.0
        total = active + idle
        return total if total > 0 else 0.0

    @staticmethod
    def _ensure_time_breakdown(
        session_time: float,
        active_time_seconds: Optional[float],
        idle_time_seconds: Optional[float],
    ) -> Tuple[float, float]:
        """Ensure active/idle breakdown sums to session time."""
        session_time = max(session_time, 0.0)

        if active_time_seconds is None and idle_time_seconds is None:
            active_time_seconds = session_time * 0.1
            idle_time_seconds = max(session_time - active_time_seconds, 0.0)
        elif active_time_seconds is None:
            idle = max(idle_time_seconds or 0.0, 0.0)
            active_time_seconds = max(session_time - idle, 0.0)
        elif idle_time_seconds is None:
            active = max(active_time_seconds or 0.0, 0.0)
            idle_time_seconds = max(session_time - active, 0.0)

        return max(active_time_seconds or 0.0, 0.0), max(idle_time_seconds or 0.0, 0.0)
    
    def _display_session_summary(self) -> None:
        """Display session summary when exiting"""
        # Prevent duplicate display
        if hasattr(self, '_summary_displayed'):
            return
        self._summary_displayed = True
        
        try:
            # Format time helper
            def format_time(seconds):
                mins, secs = divmod(int(seconds), 60)
                hours, mins = divmod(mins, 60)
                return f"{hours:02d}:{mins:02d}:{secs:02d}"
            
            # Try to get timing information
            active_time_seconds: Optional[float] = None
            idle_time_seconds: Optional[float] = None
            session_cost = 0.0

            try:
                from cai.util import COST_TRACKER, get_active_time_seconds, get_idle_time_seconds
                
                active_time_seconds = get_active_time_seconds()
                idle_time_seconds = get_idle_time_seconds()
                session_cost = COST_TRACKER.session_total_cost
            except Exception:
                pass

            session_time = self._compute_session_time_seconds(
                active_time_seconds, idle_time_seconds
            )
            active_time_seconds, idle_time_seconds = self._ensure_time_breakdown(
                session_time, active_time_seconds, idle_time_seconds
            )
            
            # Format metrics
            active_percentage = round((active_time_seconds / session_time) * 100, 1) if session_time > 0 else 0.0
            
            # Get session log info
            logging_path = None
            try:
                from cai.sdk.agents.run_to_jsonl import get_session_recorder
                session_logger = get_session_recorder()
                if hasattr(session_logger, 'filename'):
                    logging_path = session_logger.filename
                    
                    # Log session end
                    if hasattr(session_logger, 'log_session_end'):
                        session_logger.log_session_end()
                        
                    # Create symlink to last log
                    try:
                        from pathlib import Path
                        log_path = Path(logging_path)
                        if log_path.exists():
                            symlink_path = Path("logs/last")
                            if symlink_path.exists() or symlink_path.is_symlink():
                                symlink_path.unlink()
                            symlink_path.symlink_to(log_path.name)
                    except:
                        pass
            except:
                pass
            
            # End global usage tracking
            try:
                from cai.sdk.agents.global_usage_tracker import GLOBAL_USAGE_TRACKER
                GLOBAL_USAGE_TRACKER.end_session(final_cost=session_cost)
            except:
                pass
            
            # Create console for output with explicit settings
            import sys
            console = Console(file=sys.stdout, force_terminal=True)
            
            # Build content
            content = []
            content.append(f"{t('tui_session_time')}: {format_time(session_time)}")
            content.append(f"{t('tui_active_time')}: {format_time(active_time_seconds)} ({active_percentage}%)")
            content.append(f"{t('tui_idle_time')}: {format_time(idle_time_seconds)}")
            content.append(f"{t('tui_total_cost')}: ${session_cost:.6f}")
            if logging_path:
                content.append(f"{t('tui_log_available')}: {logging_path}")

            # Create Rich Text objects for each line
            text_content = []
            for line in content:
                if t('tui_total_cost') in line:
                    # Format cost line with special styling
                    cost_text = Text()
                    parts = line.split(":")
                    cost_text.append(parts[0] + ":", style="bold")
                    cost_text.append(parts[1], style="bold green")
                    text_content.append(cost_text)
                else:
                    text_content.append(Text(line))
            
            # Create and print the panel
            summary_panel = Panel(
                Group(*text_content),
                border_style="blue",
                box=ROUNDED,
                padding=(0, 1),
                title=f"[bold]{t('tui_session_summary')}[/bold]",
                title_align="left",
            )

            # Print to console (will appear after TUI exits)
            console.print("\n")
            console.print(summary_panel)
            console.print("")
            
            # Force console to flush output
            console.file.flush()
            
            # Don't prevent the cost display - let it show first
            # os.environ["CAI_COST_DISPLAYED"] = "true"
            
            # Process metrics if telemetry enabled
            try:
                telemetry_enabled = os.getenv("CAI_TELEMETRY", "true").lower() != "false"
                if telemetry_enabled and logging_path:
                    from cai.internal.components.metrics import process_metrics
                    if hasattr(session_logger, 'session_id'):
                        process_metrics(logging_path, sid=session_logger.session_id)
            except:
                pass
                
        except Exception as e:
            # Don't let errors in summary display prevent exit
            import logging
            logging.getLogger("CAITerminal").debug(f"Error displaying session summary: {e}")

def run_cai_tui():
    """Entry point for CAI TUI"""
    # Check system dependencies first (curl is needed for API key validation)
    try:
        from cai.util_ext import check_system_dependencies, display_missing_dependencies_error
        all_ok, missing = check_system_dependencies()
        if not all_ok:
            display_missing_dependencies_error(missing)
            return
    except Exception:
        pass

    # Initial system check (requires curl to be available)
    try:
        from cai.util_ext import _chk
        if not _chk():
            from rich.console import Console
            from rich.panel import Panel
            console_err = Console(stderr=True)
            console_err.print(
                Panel(
                    "[bold red]ALIAS_API_KEY is invalid or not set[/bold red]\n\n"
                    "Please set a valid ALIAS_API_KEY in your .env file or environment.",
                    title=f"[red]{t('tui_auth_error')}[/red]",
                    border_style="red"
                )
            )
            return
    except Exception:
        pass

    # Set TUI mode environment variable
    os.environ["CAI_TUI_MODE"] = "true"
    
    # Allow user to control streaming in TUI mode
    # The TUI now supports streaming visualization
    # os.environ["CAI_STREAM"] = "false"  # REMOVED: Let user control streaming
    
    # Enable mouse tracking
    os.environ["TEXTUAL_MOUSE"] = "1"

    # Apply display patches for TUI integration
    try:
        from cai.sdk.agents.models.openai_chatcompletions_integration import integrate_openai_chatcompletions_display
        
        integrate_openai_chatcompletions_display()
    except ImportError:
        # Patch module not available, continue without patching
        pass

    # Initialize meta agent controller if enabled
    if os.environ.get("CAI_META_AGENT", "false").lower() == "true":
        from cai.tui.meta_agent_controller import get_meta_agent_controller
        meta_controller = get_meta_agent_controller()
        if meta_controller:
            # Meta agent is initialized but remains hidden
            pass

    app = CAITerminal()
    app.run()
    
    # Display session summary after TUI exits
    # This ensures it's displayed after Textual restores the terminal
    
    # Prevent the cost tracker from displaying its message ASAP
    os.environ["CAI_COST_DISPLAYED"] = "true"
    
    try:
        # Add a small delay to let the terminal settle
        import time
        time.sleep(0.1)
        
        # Force stdout to be available
        import sys
        sys.stdout.flush()
        sys.stderr.flush()
        
        # Now display the session summary
        # Use print directly instead of the method to ensure it works outside the app
        
        # Format time helper
        def format_time(seconds):
            mins, secs = divmod(int(seconds), 60)
            hours, mins = divmod(mins, 60)
            return f"{hours:02d}:{mins:02d}:{secs:02d}"
        
        # Try to get timing and cost info
        active_time_seconds: Optional[float] = None
        idle_time_seconds: Optional[float] = None
        session_cost = 0.0

        try:
            from cai.util import COST_TRACKER, get_active_time_seconds, get_idle_time_seconds

            active_time_seconds = get_active_time_seconds()
            idle_time_seconds = get_idle_time_seconds()
            session_cost = COST_TRACKER.session_total_cost
        except Exception:
            pass

        session_time = app._compute_session_time_seconds(
            active_time_seconds, idle_time_seconds
        )
        active_time_seconds, idle_time_seconds = app._ensure_time_breakdown(
            session_time, active_time_seconds, idle_time_seconds
        )
        
        # Get log path
        logging_path = None
        try:
            from cai.sdk.agents.run_to_jsonl import get_session_recorder
            session_logger = get_session_recorder()
            if hasattr(session_logger, 'filename'):
                logging_path = session_logger.filename
        except:
            pass
        
        # Create and print the panel using Rich
        from rich.console import Console
        from rich.panel import Panel
        from rich.box import ROUNDED
        from rich.text import Text
        
        console = Console()
        
        # Build content lines
        lines = []
        lines.append(f"{t('tui_session_time')}: {format_time(session_time)}")
        active_percentage = round((active_time_seconds / session_time) * 100, 1) if session_time > 0 else 0.0
        lines.append(f"{t('tui_active_time')}: {format_time(active_time_seconds)} ({active_percentage}%)")
        lines.append(f"{t('tui_idle_time')}: {format_time(idle_time_seconds)}")
        lines.append(f"{t('tui_total_cost')}: ${session_cost:.6f}")
        if logging_path:
            lines.append(f"{t('tui_log_available')}: {logging_path}")
        
        # Create panel
        panel = Panel(
            "\n".join(lines),
            border_style="blue",
            box=ROUNDED,
            padding=(0, 1),
            title=f"[bold]{t('tui_session_summary')}[/bold]",
            title_align="left",
        )

        console.print(panel)
    except Exception as e:
        # If something fails, at least try to print the error
        print(f"\nError displaying session summary: {e}")
