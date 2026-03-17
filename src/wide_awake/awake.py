"""
WideAwake - a macOS menu bar app that toggles system sleep prevention.

Uses `pmset` to query and control sleep state, and AppleScript to request
administrator privileges when making changes.

Manage with..
  uv run .scripts/setup.py --help
"""
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "rumps",
# ]
# ///
from dataclasses import dataclass
import os
import subprocess
import sys

import rumps


# ── State configuration ────────────────────────────────────────────────────────

@dataclass(frozen=True)
class SleepState:
    icon: str
    status_label: str
    toggle_label: str


AWAKE = SleepState(
    icon = "😃",
    status_label = "🌞 System is Wide Awake",
    toggle_label = "Allow Sleep",
)

ASLEEP = SleepState(
    icon = "😴",
    status_label = "🌚 System is Resting",
    toggle_label = "Stay Wide Awake",
)


# ── Helpers ────────────────────────────────────────────────────────────────────

def get_app_path() -> str:
    """Return the .app bundle path, or the running script path as a fallback."""
    if ".app/Contents/MacOS" in sys.executable:
        return sys.executable.split(".app/")[0] + ".app"
    return os.path.abspath(sys.argv[0])


def run_applescript(script: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["osascript", "-e", script], capture_output=True, text=True)


def query_pmset() -> str:
    return subprocess.getoutput("pmset -g")


# ── App ────────────────────────────────────────────────────────────────────────

class WideAwake(rumps.App):
    REFRESH_INTERVAL: int = 5

    def __init__(self) -> None:
        super().__init__("WideAwake", quit_button=None)

        self.status_item = rumps.MenuItem("", callback=None)
        self.toggle_item = rumps.MenuItem("", callback=self.on_toggle)

        self.menu = [
            self.status_item,
            None,
            self.toggle_item,
            None,
            rumps.MenuItem("Quit", callback=rumps.quit_application),
        ]

        self.timer = rumps.Timer(self.refresh_ui, self.REFRESH_INTERVAL)
        self.timer.start()
        self.refresh_ui(None)

    # ── Queries ────────────────────────────────────────────────────────────────

    @property
    def sleep_disabled(self) -> bool:
        """True when pmset has disablesleep active."""
        return "disablesleep 1" in query_pmset()

    @property
    def current_state(self) -> SleepState:
        return AWAKE if self.sleep_disabled else ASLEEP

    # ── UI ─────────────────────────────────────────────────────────────────────

    def refresh_ui(self, _: rumps.Timer | None) -> None:
        """Sync menu bar icon and labels with the current system state."""
        state = self.current_state
        self.title = state.icon
        self.status_item.title = state.status_label
        self.toggle_item.title = state.toggle_label

    # ── Callbacks ──────────────────────────────────────────────────────────────

    def on_toggle(self, _: rumps.MenuItem) -> None:
        """Toggle sleep prevention via AppleScript (triggers macOS auth prompt)."""
        new_val = "0" if self.sleep_disabled else "1"
        script  = f'do shell script "pmset -a disablesleep {new_val}" with administrator privileges'

        if run_applescript(script).returncode == 0:
            self.refresh_ui(None)


if __name__ == "__main__":
    WideAwake().run()
