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
#   "structlog",
# ]
# ///
from dataclasses import dataclass
import os
import subprocess
import sys

import rumps
import structlog


LOGGER = structlog.get_logger()

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
        path = sys.executable.split(".app/")[0] + ".app"
        LOGGER.debug("resolved app bundle path", path=path)
        return path
    path = os.path.abspath(sys.argv[0])
    LOGGER.debug("resolved script path fallback", path=path)
    return path


def run_applescript(script: str) -> subprocess.CompletedProcess[str]:
    LOGGER.debug("running applescript", script=script)
    result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
    if result.returncode != 0:
        LOGGER.warning("applescript failed", returncode=result.returncode, stderr=result.stderr.strip())
    else:
        LOGGER.debug("applescript succeeded")
    return result


def query_pmset() -> str:
    LOGGER.debug("querying pmset")
    return subprocess.getoutput("pmset -g")


# ── App ────────────────────────────────────────────────────────────────────────

class WideAwake(rumps.App):
    REFRESH_INTERVAL: int = 5

    def __init__(self) -> None:
        super().__init__("WideAwake", quit_button=None)
        LOGGER.info("initialising WideAwake app")

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

    # ── Queries ────────────────────────────────────────────────────────────────

    @property
    def sleep_disabled(self) -> bool:
        """True when pmset has disablesleep active."""
        result = "disablesleep 1" in query_pmset()
        LOGGER.debug("checked sleep state", sleep_disabled=result)
        return result

    # ── UI ─────────────────────────────────────────────────────────────────────

    def refresh_ui(self, _: rumps.Timer | None) -> None:
        """Sync menu bar icon and labels with the current system state."""
        # Read once, use everywhere
        is_disabled = self.sleep_disabled
        state = AWAKE if is_disabled else ASLEEP
        LOGGER.debug("current state", state=state.status_label)

        self.title = state.icon
        self.status_item.title = state.status_label
        self.toggle_item.title = state.toggle_label
        LOGGER.debug("ui refreshed", icon=state.icon, status=state.status_label)

    # ── Callbacks ──────────────────────────────────────────────────────────────

    def on_toggle(self, _: rumps.MenuItem) -> None:
        """Toggle sleep prevention via AppleScript (triggers macOS auth prompt)."""
        currently_disabled = self.sleep_disabled
        new_val = "0" if currently_disabled else "1"
        LOGGER.info("toggling sleep prevention", current_sleep_disabled=currently_disabled, new_value=new_val)

        script = f'do shell script "pmset -a disablesleep {new_val}" with administrator privileges'

        if run_applescript(script).returncode == 0:
            LOGGER.info("sleep prevention toggled successfully", sleep_disabled=not currently_disabled)
            self.refresh_ui(None)
        else:
            LOGGER.error("failed to toggle sleep prevention", new_value=new_val)


if __name__ == "__main__":
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(),
        ]
    )

    try:
        LOGGER.info("starting WideAwake")
        WideAwake().run()
    except KeyboardInterrupt:
        LOGGER.warning("User cancelled WideAwake from the terminal.")
    finally:
        LOGGER.info("stopped WideAwake")
