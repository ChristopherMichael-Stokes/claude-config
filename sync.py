#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Symlink the Claude Code config tracked in this repo into the Claude config directory.

The Claude config directory is '$CLAUDE_CONFIG_DIR' if set, else '~/.claude'.
Each name in 'MANAGED_ENTRIES' lives in 'config/' and is linked into place:

- 'install' links every entry. An entry that exists only on this machine is moved
  into the repo first; a machine copy that conflicts with the repo copy is preserved
  under '~/.claude-config-backup/<timestamp>/' before the link replaces it.
- 'status' reports each entry's state, diffs files whose link was replaced by a
  regular file, and exits non-zero when anything needs 'install'.

Usage: ./sync.py {install,status}  (Windows: uv run sync.py {install,status})
"""

import argparse
import difflib
import enum
import os
import shutil
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

REPO_CONFIG_DIR = Path(__file__).resolve().parent / "config"
BACKUP_ROOT = Path.home() / ".claude-config-backup"
MANAGED_ENTRIES = (
    "CLAUDE.md",
    "settings.json",
    "keybindings.json",
    "agents",
    "commands",
    "hooks",
    "rules",
    "skills",
)
TEMPORARY_LINK_SUFFIX = ".claude-config-tmp"
WINDOWS_PRIVILEGE_NOT_HELD = 1314
WINDOWS_SYMLINK_HINT = (
    "Creating symlinks on Windows needs Developer Mode "
    "(Settings > System > For developers) or an elevated shell."
)
REPLACED_HINT = (
    "\nRun install to link. Copy any machine-side changes shown above into config/ "
    "first to keep them."
)


class State(enum.Enum):
    """Relationship between a managed entry's repo copy and its machine path."""

    LINKED = "linked"
    ABSENT = "absent from repo and machine"
    NOT_INSTALLED = "in repo, not linked on this machine"
    MACHINE_ONLY = "on this machine only; install moves it into the repo"
    REPLACED = "regular file or directory where the link should be"
    OTHER_LINK = "symlink that does not point at the repo copy"


NEEDS_INSTALL = {State.NOT_INSTALLED, State.MACHINE_ONLY, State.REPLACED, State.OTHER_LINK}


@dataclass(frozen=True)
class Entry:
    """One managed name, located in the repo and in the Claude config directory."""

    name: str
    repo_path: Path
    machine_path: Path


def claude_config_dir() -> Path:
    """Return the directory Claude Code reads user config from."""
    override = os.environ.get("CLAUDE_CONFIG_DIR")
    return Path(override).expanduser() if override else Path.home() / ".claude"


def managed_entries() -> list[Entry]:
    """Return every entry in 'MANAGED_ENTRIES', located for this machine."""
    machine_dir = claude_config_dir()
    return [Entry(name, REPO_CONFIG_DIR / name, machine_dir / name) for name in MANAGED_ENTRIES]


def classify(entry: Entry) -> State:
    """Return the current state of 'entry' on this machine."""
    if entry.machine_path.is_symlink():
        points_at_repo = (
            entry.repo_path.exists() and entry.machine_path.resolve() == entry.repo_path.resolve()
        )
        return State.LINKED if points_at_repo else State.OTHER_LINK
    if not entry.machine_path.exists():
        return State.NOT_INSTALLED if entry.repo_path.exists() else State.ABSENT
    return State.REPLACED if entry.repo_path.exists() else State.MACHINE_ONLY


def preserve(source: Path, destination: Path) -> None:
    """Keep 'source''s content at 'destination', leaving files in place.

    A file stays put so the link can later replace it atomically; a directory can't
    be replaced atomically, so it is moved.
    """
    destination.parent.mkdir(parents=True, exist_ok=True)
    if source.is_dir() and not source.is_symlink():
        shutil.move(str(source), str(destination))
    else:
        shutil.copy2(source, destination, follow_symlinks=False)


def link_into_place(entry: Entry) -> None:
    """Replace 'entry''s machine path with a symlink to its repo copy."""
    # link-then-rename so running sessions never observe a missing settings file
    temporary_link = entry.machine_path.with_name(entry.machine_path.name + TEMPORARY_LINK_SUFFIX)
    try:
        temporary_link.symlink_to(entry.repo_path, target_is_directory=entry.repo_path.is_dir())
    except OSError as error:
        if getattr(error, "winerror", None) == WINDOWS_PRIVILEGE_NOT_HELD:
            raise SystemExit(WINDOWS_SYMLINK_HINT) from error
        raise
    temporary_link.replace(entry.machine_path)


def install(entries: list[Entry]) -> None:
    """Link every entry that needs it, adopting or backing up what is in the way."""
    backup_dir = BACKUP_ROOT / datetime.now(UTC).astimezone().strftime("%Y%m%d-%H%M%S")
    claude_config_dir().mkdir(parents=True, exist_ok=True)
    for entry in entries:
        state = classify(entry)
        if state not in NEEDS_INSTALL:
            continue
        if state is State.MACHINE_ONLY:
            preserve(entry.machine_path, entry.repo_path)
            print(f"adopted  {entry.name} into {entry.repo_path}")
        elif state in (State.REPLACED, State.OTHER_LINK):
            preserve(entry.machine_path, backup_dir / entry.name)
            print(f"backed up {entry.name} to {backup_dir / entry.name}")
        link_into_place(entry)
        print(f"linked   {entry.machine_path} -> {entry.repo_path}")


def file_diff(repo_path: Path, machine_path: Path) -> str:
    """Return a unified diff from the repo copy to the machine copy."""
    repo_lines = repo_path.read_text(encoding="utf-8").splitlines(keepends=True)
    machine_lines = machine_path.read_text(encoding="utf-8").splitlines(keepends=True)
    diff = difflib.unified_diff(repo_lines, machine_lines, str(repo_path), str(machine_path))
    return "".join(diff)


def status(entries: list[Entry]) -> int:
    """Print each entry's state; return 1 if any entry needs 'install', else 0."""
    needs_install = False
    for entry in entries:
        state = classify(entry)
        needs_install |= state in NEEDS_INSTALL
        print(f"{entry.name:<18} {state.value}")
        if state is State.REPLACED and entry.machine_path.is_file() and entry.repo_path.is_file():
            print(file_diff(entry.repo_path, entry.machine_path) or "  (contents identical)")
    if needs_install:
        print(REPLACED_HINT)
    return 1 if needs_install else 0


def main() -> int:
    """Parse the command line and run the chosen command."""
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("command", choices=("install", "status"))
    arguments = parser.parse_args()
    entries = managed_entries()
    if arguments.command == "install":
        install(entries)
        return 0
    return status(entries)


if __name__ == "__main__":
    sys.exit(main())
