"""Tests for the rm variable-path guard hook."""

import importlib.util
import json
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path
from types import ModuleType

import pytest

HOOK_PATH = (
    Path(__file__).resolve().parent.parent / "config" / "hooks" / "guard_rm_variable_path.py"
)


def load_hook() -> ModuleType:
    """Import the hook script, which lives outside any package."""
    spec = importlib.util.spec_from_file_location("guard_rm_variable_path", HOOK_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


hook = load_hook()


@pytest.fixture
def root(tmp_path: Path) -> Path:
    """A stand-in filesystem root containing '/Users' and '/etc'."""
    (tmp_path / "Users").mkdir()
    (tmp_path / "etc").mkdir()
    return tmp_path


def blocked_arguments(command: str, root: Path) -> list[str]:
    """Return the source text of every argument the hook denies in 'command'."""
    return [finding.argument for finding in hook.find_dangerous_rm_arguments(command, root)]


@pytest.mark.parametrize(
    "command",
    [
        'rm -rf "$DIR"/*',
        "rm -rf $DIR/*",
        'rm -rf "$DIR/"*',
        'rm -rf "${DIR}"/*',
        "rm -rf $DIR/Users",
        'rm -rf "$DIR/Users"',
        'rm -rf "${DIR}/etc"',
        "rm -rf $DIR/",
        'rm -rf "$DIR/"',
        'rm -r -- "$A/$B"',
        "rm -rf $DIR/$(whoami)",
        "rm -rf $DIR/`whoami`",
        "rm -rf $DIR/?tc",
        "rm -rf $DIR/[e]tc",
        'sudo rm -rf "$D/etc"',
        "sudo -u root rm -rf $D/Users",
        "sudo -E -- rm -rf $D/Users",
        "sudo FOO=1 rm -rf $D/Users",
        "/bin/rm -rf $D/Users",
        "echo hi; rm -rf $D/Users",
        "true && rm -rf $D/Users",
        "false || rm -rf $D/Users",
        "cat file | rm -rf $D/Users",
        "(rm -rf $D/Users)",
        "{ rm -rf $D/Users; }",
        "for d in a; do rm -rf $D/Users; done",
        "if true; then rm -rf $D/Users; fi",
        "echo $(rm -rf $D/Users)",
        "rm -rf ${arr[0]}/Users",
        "rm -rf $1/Users",
        "rm -rf ${D:-x}/Users",
        "rm -rf ${D?}/Users",
        "rm -rf $D/Users$E",
    ],
)
def test_blocks_dangerous_argument(command: str, root: Path) -> None:
    assert len(blocked_arguments(command, root)) == 1


@pytest.mark.parametrize(
    "command",
    [
        'rm -rf "${DIR:?}/Users"',
        'rm -rf "${DIR:?}"/*',
        "rm -rf ${DIR:?}/*",
        'rm -rf "${DIR:?message}"/*',
        "rm -rf $DIR/build",
        'echo hi; rm -fr "$D"/x',
        'rm -rf "$D"',
        "rm -rf $D",
        "rm -rf ${D}x/Users",
        "rm -rf $D$E/Users",
        "rm -rf $D/'*'",
        'rm -rf $D/"*"',
        "rm -rf $D/\\*",
        "rm -rf ./$D/*",
        "rm -rf build/*",
        "rm -rf /tmp/$D/*",
        "rm -rf $(pwd)/*",
        "ls $D/",
        "ls $D/*",
        "echo rm -rf $D/Users",
        "rm -rf",
        'rm ""',
        'rm -- "" x',
        "",
    ],
)
def test_allows_safe_command(command: str, root: Path) -> None:
    assert blocked_arguments(command, root) == []


def test_reports_each_dangerous_argument_of_each_rm(root: Path) -> None:
    command = 'rm -rf "$A"/* safe; sudo rm "$B/etc" $C/build'
    assert blocked_arguments(command, root) == ['"$A"/*', '"$B/etc"']


def test_dangling_symlink_counts_as_existing(root: Path) -> None:
    (root / "gone").symlink_to(root / "missing")
    assert blocked_arguments("rm $D/gone", root) == ["$D/gone"]


def test_existing_path_depends_on_root(tmp_path: Path) -> None:
    assert blocked_arguments("rm $D/Users", tmp_path) == []
    (tmp_path / "Users").mkdir()
    assert blocked_arguments("rm $D/Users", tmp_path) == ["$D/Users"]


def test_unparsable_command_does_not_crash(root: Path) -> None:
    assert blocked_arguments('rm -rf "$D"/* "unterminated', root) == ['"$D"/*']
    assert blocked_arguments("rm -rf $D/* ))) ;;", root) == ["$D/*"]


def test_finding_fields(root: Path) -> None:
    (pattern,) = hook.find_dangerous_rm_arguments('rm "$DIR"/*', root)
    assert (pattern.variable, pattern.collapsed_path, pattern.reason) == (
        "DIR",
        "/*",
        hook.Reason.PATTERN,
    )
    (existing,) = hook.find_dangerous_rm_arguments("rm $DIR/Users", root)
    assert (existing.variable, existing.collapsed_path, existing.reason) == (
        "DIR",
        "/Users",
        hook.Reason.EXISTING_PATH,
    )


def test_deny_reason_names_argument_and_collapse_without_a_rewrite(root: Path) -> None:
    findings = hook.find_dangerous_rm_arguments('rm -rf "$DIR"/* $D2/Users', root)
    reason = hook.deny_reason(findings)
    for expected in ('"$DIR"/*', "$D2/Users", "/Users", "/*"):
        assert expected in reason
    assert ":?" not in reason


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
    payload = {"tool_name": "Bash", "tool_input": {"command": 'rm -rf "$D"/*'}, "session_id": "x"}
    result = run_hook(payload)
    assert result.returncode == 0, result.stderr
    output = json.loads(result.stdout)["hookSpecificOutput"]
    assert output["hookEventName"] == "PreToolUse"
    assert output["permissionDecision"] == "deny"
    assert '"$D"/*' in output["permissionDecisionReason"]


def test_end_to_end_allows_guarded_command() -> None:
    result = run_hook({"tool_name": "Bash", "tool_input": {"command": 'rm -rf "${D:?}"/*'}})
    assert result.returncode == 0, result.stderr
    assert result.stdout == ""


def test_end_to_end_ignores_other_tools() -> None:
    result = run_hook({"tool_name": "Read", "tool_input": {"file_path": "/etc/hosts"}})
    assert result.returncode == 0, result.stderr
    assert result.stdout == ""
