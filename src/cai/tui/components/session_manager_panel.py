"""
Panel for displaying and managing sessions.
"""

from textual.app import ComposeResult
from textual.widgets import Static, ListView, ListItem, Label
from textual.containers import Vertical
from cai.i18n import t

class SessionManagerPanel(Static):
    """A panel to display session information."""

    def compose(self) -> ComposeResult:
        """Compose the panel UI."""
        yield Vertical(
            Label(t('tui_sessions'), classes="panel-title"),
            ListView(
                ListItem(Label(t('tui_no_sessions'))),
                id="session-list"
            ),
            id="session-manager-panel-content"
        )