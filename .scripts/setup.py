# /// script
# requires-python = ">=3.12"
# dependencies = ["cyclopts"]
# ///
import os
import pathlib
import shutil
import subprocess

import cyclopts

LABEL = "com.boonhapus.wide-awake"
PLIST = pathlib.Path.home() / f"Library/LaunchAgents/{LABEL}.plist"
UV = shutil.which("uv")
SCRIPT = pathlib.Path(__file__).parent.parent / "src" / "wide_awake" / "awake.py"

PLIST_XML = f"""
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key><string>{LABEL}</string>
    <key>ProgramArguments</key>
    <array>
        <string>{UV}</string>
        <string>run</string>
        <string>{SCRIPT}</string>
    </array>
    <key>RunAtLoad</key><true/>
</dict>
</plist>
"""

app = cyclopts.App(name="WideAwake Setup", help="Manage the WideAwake launchd service.")


def _gui_domain() -> str:
    """Return the launchd GUI domain for the real user (even under sudo)."""
    uid = os.environ.get("SUDO_UID") or str(os.getuid())
    return f"gui/{uid}"


def _bootout() -> None:
    """Remove any existing launchd registration, ignoring errors."""
    subprocess.run(
        ["launchctl", "bootout", f"{_gui_domain()}/{LABEL}"],
        check=False,
        capture_output=True,
    )


@app.command
def install() -> None:
    """Install and load the WideAwake launchd plist."""
    _bootout()
    PLIST.parent.mkdir(parents=True, exist_ok=True)
    PLIST.write_text(PLIST_XML)
    subprocess.run(
        ["launchctl", "bootstrap", _gui_domain(), str(PLIST)],
        check=True,
    )
    print(f"✓ installed {PLIST}")


@app.command
def uninstall() -> None:
    """Unload and remove the WideAwake launchd plist."""
    _bootout()
    PLIST.unlink(missing_ok=True)
    print(f"✓ removed {PLIST}")


if __name__ == "__main__":
    app()