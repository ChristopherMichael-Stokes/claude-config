"""Tests for the ShellCheck rules guard hook.

The commands are only text fed to ShellCheck; none is executed.
"""

import importlib.util
import json
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path
from types import ModuleType

import pytest

HOOK_PATH = (
    Path(__file__).resolve().parent.parent / "config" / "hooks" / "guard_shellcheck_rules.py"
)


def load_hook() -> ModuleType:
    """Import the hook script, which lives outside any package."""
    spec = importlib.util.spec_from_file_location("guard_shellcheck_rules", HOOK_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


hook = load_hook()


def codes(command: str) -> list[int]:
    """Return the guarded ShellCheck codes reported for 'command'."""
    return [finding.code for finding in hook.find_findings(command)]


@pytest.mark.parametrize(
    ("command", "code"),
    [
        ("sort f > f", 2094),
        ("grep x f > f", 2094),
        ("cat f | sort > f", 2094),
        ("sed s/a/b/ f > f", 2094),
        ("cat f >> f", 2094),
        ('echo "~/foo"', 2088),
        ('mkdir "~/foo"', 2088),
        ('rm -rf "~/foo"', 2088),
        ("find / -name x -o -name y -delete", 2146),
        (r"find . -name a -o -name b -exec rm {} \;", 2146),
        ("find . -name x | rm", 2216),
        ("ls | rm", 2216),
    ],
)
def test_denied_commands_report_their_code(command: str, code: int) -> None:
    assert code in codes(command)


@pytest.mark.parametrize(
    "command",
    [
        "sort f > g",
        "sed -i s/a/b/ f",
        'ls ~/"foo"',
        'ls "$HOME/foo"',
        r"find . \( -name a -o -name b \) -delete",
        "find . -name x -delete",
        "find . -name x -print0 | xargs -0 rm",
        "ls $DIR",
        "rm *",
        "cd dir; ls",
        "echo $(date)",
    ],
)
def test_allowed_commands_report_nothing(command: str) -> None:
    assert codes(command) == []


def test_snippet_is_the_reported_range() -> None:
    findings = hook.find_findings('echo ok\nmkdir "~/foo"')
    assert [finding.snippet for finding in findings] == ["~/foo"]


def test_deny_reason_has_code_snippet_hazard_and_wiki_url() -> None:
    reason = hook.deny_reason(hook.find_findings("ls | rm"))
    assert "SC2216" in reason
    assert "rm" in reason
    assert hook.HAZARD_BY_CODE[2216] in reason
    assert "https://www.shellcheck.net/wiki/SC2216" in reason


def test_every_guarded_code_has_a_hazard() -> None:
    assert set(hook.HAZARD_BY_CODE) == {2094, 2088, 2146, 2216}


def run_hook(payload: Mapping[str, object]) -> subprocess.CompletedProcess[str]:
    """Run the hook script with 'payload' as JSON on stdin."""
    return subprocess.run(  # noqa: S603
        [str(HOOK_PATH)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        check=False,
    )


def test_end_to_end_denies_blocked_command() -> None:
    result = run_hook({"tool_name": "Bash", "tool_input": {"command": "sort f > f"}})
    assert result.returncode == 0, result.stderr
    output = json.loads(result.stdout)["hookSpecificOutput"]
    assert output["hookEventName"] == "PreToolUse"
    assert output["permissionDecision"] == "deny"
    assert "https://www.shellcheck.net/wiki/SC2094" in output["permissionDecisionReason"]


def test_end_to_end_allows_clean_command() -> None:
    result = run_hook({"tool_name": "Bash", "tool_input": {"command": "sort f > g"}})
    assert result.returncode == 0, result.stderr
    assert result.stdout == ""


def test_end_to_end_ignores_other_tools() -> None:
    result = run_hook({"tool_name": "Read", "tool_input": {"file_path": "/etc/hosts"}})
    assert result.returncode == 0, result.stderr
    assert result.stdout == ""
