"""Set the KiCad stack up on this machine, in one go.

    python bootstrap.py                 the library, its environment, the MCP registration, a health check
    python bootstrap.py --tools         also FreeRouting and, on Windows, a Java runtime into tools/
    python bootstrap.py --ipc --browser the optional install groups (KiCad's live API; headless Chromium)
    python bootstrap.py --dry-run       say what would happen and change nothing

Needs Python 3.12 or newer and git on the PATH. KiCad 10 itself comes from kicad.org; the health check at
the end says whether it was found. Every step is safe to repeat: what exists is kept.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LIBRARY = ROOT / "kicad-mcp-layer"
OLD_LIBRARY = ROOT / "kicad-layer"  # the folder's name before 2026-09-12; migrated on sight
TOOLS = ROOT / "tools"

KICAD_LAYER_REPO = "https://github.com/ShamanAndrey/kicad-mcp-layer.git"  # the library's own repository
KICAD_LAYER_REF = "main"
# Exact releases with their SHA-256, so a download is refused unless it is the file these were tested with.
FREEROUTING_URL = "https://github.com/freerouting/freerouting/releases/download/v2.4.1/freerouting-2.4.1.jar"
FREEROUTING_SHA256 = "251101c3eeac22d7e7dfcf6796603279e5d1000283eb82d8f093780f7afc6aa9"
TEMURIN_JRE_URL = "https://github.com/adoptium/temurin25-binaries/releases/download/jdk-25.0.4.1%2B1/OpenJDK25U-jre_x64_windows_hotspot_25.0.4.1_1.zip"
TEMURIN_JRE_SHA256 = "4c95451cea98556def2c54f7782933f52a26d4a36bd85e1d59f0364464828b07"

WINDOWS = platform.system() == "Windows"
DRY = False


def say(msg: str) -> None:
    print(f"  {msg}", flush=True)  # flushed, so the log stays in order with the subprocesses' output


def step(title: str) -> None:
    print(f"\n{title}", flush=True)


def run(cmd: list[str], **kw) -> None:
    say("$ " + " ".join(str(c) for c in cmd))
    if not DRY:
        subprocess.run([str(c) for c in cmd], check=True, **kw)


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1 << 20):
            h.update(chunk)
    return h.hexdigest()


def download(url: str, dest: Path, sha256: str) -> None:
    """Fetch ``url`` to ``dest`` and refuse it unless its SHA-256 is ``sha256``."""
    say(f"download {url}\n      -> {dest}")
    if DRY:
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    with urllib.request.urlopen(url) as r, open(tmp, "wb") as f:
        total = int(r.headers.get("Content-Length") or 0)
        done = 0
        while chunk := r.read(1 << 20):
            f.write(chunk)
            done += len(chunk)
            if total:
                print(f"\r      {done // (1 << 20)} / {total // (1 << 20)} MB", end="", flush=True)
    print()
    got = sha256_of(tmp)
    if got != sha256:
        tmp.unlink()
        sys.exit(f"{dest.name}: SHA-256 {got} is not the expected {sha256}; the download is refused. Fetch it by hand from {url} and compare, or update the hash in bootstrap.py if the release changed on purpose")
    say(f"SHA-256 verified")
    tmp.replace(dest)


def venv_python() -> Path:
    return LIBRARY / ".venv" / ("Scripts/python.exe" if WINDOWS else "bin/python")


def check_prerequisites() -> None:
    step("Prerequisites")
    if sys.version_info < (3, 12):
        sys.exit(f"Python 3.12 or newer is needed; this is {platform.python_version()}")
    say(f"Python {platform.python_version()} at {sys.executable}")
    if not shutil.which("git"):
        sys.exit("git is not on the PATH; install it from git-scm.com and run again")
    say(f"git at {shutil.which('git')}")


def migrate_old_layout() -> None:
    """The library folder was called kicad-layer until 2026-09-12: rename it, drop its virtual environment (it holds
    absolute paths and would not survive the move) and point .mcp.json at the new place."""
    if not OLD_LIBRARY.is_dir() or LIBRARY.exists():
        return
    step("Old layout found: kicad-layer -> kicad-mcp-layer")
    say(f"rename {OLD_LIBRARY.name} -> {LIBRARY.name} (close KiCad and Claude Code first if this fails)")
    if not DRY:
        OLD_LIBRARY.rename(LIBRARY)
    mcp = ROOT / ".mcp.json"
    if mcp.is_file() and "kicad-layer" in mcp.read_text(encoding="utf-8"):
        say("point .mcp.json at the new folder and server name")
        if not DRY:
            text = mcp.read_text(encoding="utf-8").replace("kicad-mcp-layer", "kicad-layer").replace("kicad-layer", "kicad-mcp-layer")
            mcp.write_text(text, encoding="utf-8")
    remove_venv(LIBRARY / ".venv", "the old virtual environment holds absolute paths; it is rebuilt below")


def remove_venv(venv: Path, why: str) -> bool:
    """Delete a virtual environment; False, with a clear message, when a running process holds its files."""
    if not venv.is_dir():
        return True
    say(f"remove {venv}: {why}")
    if DRY:
        return True
    try:
        shutil.rmtree(venv)
        return True
    except PermissionError as ex:
        say(f"could not remove it completely ({ex.filename}): a process still uses it, usually Claude Code's MCP server. "
            "Close Claude Code and KiCad, run bootstrap.py again, and the environment is rebuilt")
        return False


def venv_works(py: Path) -> bool:
    """A virtual environment in which the library and its dependencies import; a half-deleted or moved one fails
    this, and so does one whose install never finished, and both are cheaper to rebuild than to repair."""
    if not py.is_file():
        return False
    r = subprocess.run([str(py), "-c", "import pip, pydantic, mcp, kicad_layer"], capture_output=True, text=True)
    return r.returncode == 0


def ensure_library() -> None:
    step("The library (kicad-mcp-layer)")
    if (LIBRARY / "pyproject.toml").is_file():
        say(f"present at {LIBRARY}" + (" (its own git repository; pull it yourself when you want a newer one)" if (LIBRARY / ".git").exists() else ""))
        return
    run(["git", "clone", "--branch", KICAD_LAYER_REF, KICAD_LAYER_REPO, str(LIBRARY)])


def ensure_environment(extras: list[str]) -> None:
    step("The library's environment")
    py = venv_python()
    if venv_works(py):
        say(f"virtual environment present: {py}")
    else:
        if py.is_file():
            say("the virtual environment is broken (half removed or moved)")
            if not remove_venv(LIBRARY / ".venv", "a broken environment is rebuilt from scratch"):
                sys.exit(1)
        run([sys.executable, "-m", "venv", str(LIBRARY / ".venv")])
    groups = ",".join(["dev", "parts", "preview", *extras])
    run([py, "-m", "pip", "install", "--upgrade", "pip", "--quiet"])
    run([py, "-m", "pip", "install", "-e", f"{LIBRARY}[{groups}]", "--quiet"])
    if "browser" in extras:
        run([py, "-m", "playwright", "install", "chromium"])


def ensure_tools() -> None:
    step("Tools: FreeRouting and a Java runtime")
    jar = TOOLS / Path(FREEROUTING_URL).name
    if jar.is_file():
        say(f"present: {jar.name}")
    else:
        download(FREEROUTING_URL, jar, FREEROUTING_SHA256)
    java = TOOLS / "jre" / ("bin/java.exe" if WINDOWS else "bin/java")
    if java.is_file():
        say(f"present: {java}")
    elif not WINDOWS:
        say("no Java runtime fetched on this platform: install a Java 21 or newer runtime with your package manager, FreeRouting will use it from the PATH")
    else:
        zip_path = TOOLS / "temurin-jre.zip"
        download(TEMURIN_JRE_URL, zip_path, TEMURIN_JRE_SHA256)
        say(f"unzip {zip_path.name} -> tools/jre")
        if not DRY:
            with tempfile.TemporaryDirectory(dir=TOOLS) as tmp:
                with zipfile.ZipFile(zip_path) as z:
                    z.extractall(tmp)
                inner = next(p for p in Path(tmp).iterdir() if p.is_dir())
                shutil.move(str(inner), str(TOOLS / "jre"))
            zip_path.unlink()


def ensure_mcp_json() -> None:
    step("Claude Code registration (.mcp.json)")
    target = ROOT / ".mcp.json"
    if target.is_file():
        say("present; left as it is")
        return
    config = {
        "mcpServers": {
            "kicad-mcp-layer": {
                "command": str(venv_python()),
                "args": ["-m", "kicad_layer"],
                "env": {"KICAD_LAYER_WORKSPACE": str(ROOT), "KICAD_LAYER_MODE": "readonly", "KICAD_LAYER_TOOLS": "core"},
            }
        }
    }
    say(f"write {target} (read-only mode, core tools; set KICAD_LAYER_MODE=write and KICAD_LAYER_TOOLS=full for edits and routers)")
    if not DRY:
        target.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")


HEALTH_SUMMARY = r'''
from kicad_layer import doctor
r = doctor.diagnose().model_dump()
cli = r.get("kicad_cli") or {}
print("  server        ", r.get("server_version"), "| mode", r.get("mode"), "| workspace", r.get("workspace_root"))
print("  kicad-cli     ", (f'{cli.get("version")} at {cli.get("path")}' if cli.get("found") else "NOT FOUND: install KiCad 10 from kicad.org") )
ipc = r.get("ipc") or {}
state = ipc.get("state") or ipc.get("status") or ("reachable" if ipc.get("reachable") else "not reachable")
print("  live API      ", state, "(needs KiCad open with its API on; every kicad-cli and file tool works without it)")
procs = r.get("kicad_processes") or []
print("  KiCad running ", "yes" if procs else "no")
for line in (r.get("advice") or [])[:4]:
    print("  advice        ", line)
'''


def health_check() -> None:
    step("Health check (kicad_doctor)")
    if DRY:
        say("$ <the doctor's summary from the library's environment>")
        return
    subprocess.run([str(venv_python()), "-c", HEALTH_SUMMARY], check=True)


def main() -> int:
    global DRY
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tools", action="store_true", help="fetch FreeRouting and, on Windows, a Java runtime into tools/")
    ap.add_argument("--ipc", action="store_true", help="install the ipc extra (KiCad's live API through kicad-python)")
    ap.add_argument("--browser", action="store_true", help="install the browser extra and its Chromium (datasheet portals)")
    ap.add_argument("--dry-run", action="store_true", help="print the steps, change nothing")
    args = ap.parse_args()
    DRY = args.dry_run
    if DRY:
        print("dry run: nothing is changed")
    check_prerequisites()
    migrate_old_layout()
    ensure_library()
    ensure_environment([x for x, on in (("ipc", args.ipc), ("browser", args.browser)) if on])
    if args.tools:
        ensure_tools()
    ensure_mcp_json()
    try:
        health_check()
    except subprocess.CalledProcessError as ex:
        say(f"the health check failed ({ex}); open Claude Code here and call kicad_doctor")
    step("Next")
    say("open (or restart) Claude Code in this folder: the kicad-mcp-layer server registers from .mcp.json")
    say("datasheets are not in the repository: doc_fetch brings the ones you need into research/references/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
