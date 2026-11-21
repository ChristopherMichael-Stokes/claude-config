#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "pydantic==2.14.4",
#   "shellcheck-py==0.11.0.1",
# ]
# ///
"""Claude Code PreToolUse hook: deny Bash commands that trip a guarded ShellCheck rule.

ShellCheck runs on the command as a bash script. The command is denied when it reports any of
SC2094 (read and write of the same file in one pipeline), SC2088 (tilde in quotes), SC2146
(find '-o' without grouping) or SC2216 (pipe into 'rm'). Every other ShellCheck code is ignored,
whatever its severity.

The hook reads the PreToolUse JSON payload on stdin. A denial is a JSON document on stdout
whose reason names each finding and why it is wrong; an allowed command prints nothing. A ShellCheck
failure or unparsable ShellCheck output raises.
"""

import json
import subprocess
import sys
from dataclasses import dataclass
from importlib import metadata
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

BASH_TOOL_NAME = "Bash"
HOOK_EVENT_NAME = "PreToolUse"
SHELLCHECK_DISTRIBUTION = "shellcheck-py"
SHELLCHECK_EXECUTABLE = "shellcheck"
SHELLCHECK_EXIT_WITH_FINDINGS = 1
WIKI_URL_PREFIX = "https://www.shellcheck.net/wiki/SC"
CODE_PREFIX = "SC"

HAZARD_BY_CODE = {
    2094: (
        "The same file is read and written in one pipeline. The shell truncates it for the "
        "write before the reader gets to it, so its contents are lost."
    ),
    2088: (
        "A tilde inside quotes is not expanded, so the path is a literal directory named '~' in "
        "the current directory, not the home directory."
    ),
    2146: (
        "'-o' has lower precedence than the implicit '-a', so the action applies only to the "
        "last alternative; the earlier alternatives match and do nothing."
    ),
    2216: (
        "'rm' does not read stdin, so the names piped into it are ignored and nothing is "
        "deleted, while the command can still look as if it succeeded."
    ),
}
SHELLCHECK_ARGUMENTS = (
    "--norc",
    "--shell=bash",
    "--format=json1",
    "--include=" + ",".join(f"{CODE_PREFIX}{code}" for code in HAZARD_BY_CODE),
    "-",
)
DENY_HEADER = "Blocked: ShellCheck found a bug in this command."
DENY_FOOTER = "Work out a correct form of the command, then re-run it."


@dataclass(frozen=True)
class Finding:
    """One ShellCheck finding for a guarded code.

    'snippet' is the command text of the reported range.
    """

    code: int
    snippet: str


class ShellCheckComment(BaseModel):
    """One entry of the ShellCheck 'json1' output; lines and columns are 1-based.

    'end_column' is exclusive.
    """

    model_config = ConfigDict(frozen=True)

    code: int
    line: int
    column: int
    end_line: int = Field(alias="endLine")
    end_column: int = Field(alias="endColumn")


class ShellCheckReport(BaseModel):
    """The ShellCheck 'json1' document."""

    model_config = ConfigDict(frozen=True)

    comments: list[ShellCheckComment]


class ToolInput(BaseModel):
    """The part of a PreToolUse 'tool_input' this hook reads; other tools have no command."""

    model_config = ConfigDict(frozen=True)

    command: str | None = None


class HookPayload(BaseModel):
    """The part of the PreToolUse stdin payload this hook reads."""

    model_config = ConfigDict(frozen=True)

    tool_name: str
    tool_input: ToolInput


def shellcheck_binary() -> Path:
    """Return the native binary the shellcheck-py wheel installed.

    The wheel's file record locates it in the environment that holds the package; PATH and the
    interpreter's own scripts directory can point elsewhere (for example under 'uv run --with').
    """
    distribution = metadata.distribution(SHELLCHECK_DISTRIBUTION)
    record = next(file for file in distribution.files or [] if file.name == SHELLCHECK_EXECUTABLE)
    return Path(str(distribution.locate_file(record))).resolve()


def run_shellcheck(command: str) -> ShellCheckReport:
    """Run ShellCheck on 'command' (as stdin, no shell) and parse its report.

    Raises on any exit status other than "clean" or "findings reported", and on unparsable output.
    """
    completed = subprocess.run(  # noqa: S603  # fixed argv; the command travels on stdin
        [str(shellcheck_binary()), *SHELLCHECK_ARGUMENTS],
        input=command,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode not in {0, SHELLCHECK_EXIT_WITH_FINDINGS}:
        message = f"shellcheck exited {completed.returncode}: {completed.stderr.strip()}"
        raise RuntimeError(message)
    return ShellCheckReport.model_validate_json(completed.stdout)


def offset_of(lines: list[str], line: int, column: int) -> int:
    """Return the offset in the newline-joined 'lines' of the 1-based 'line' and 'column'."""
    return sum(len(text) + 1 for text in lines[: line - 1]) + column - 1


def snippet_of(command: str, comment: ShellCheckComment) -> str:
    """Return the text of 'command' covered by the range of 'comment'."""
    lines = command.split("\n")
    start = offset_of(lines, comment.line, comment.column)
    end = offset_of(lines, comment.end_line, comment.end_column)
    return command[start:end]


def find_findings(command: str) -> list[Finding]:
    """Return the findings of the guarded ShellCheck codes for the shell 'command'."""
    return [
        Finding(comment.code, snippet_of(command, comment))
        for comment in run_shellcheck(command).comments
        if comment.code in HAZARD_BY_CODE
    ]


def deny_reason(findings: list[Finding]) -> str:
    """Return the message naming each finding, its command text, its hazard and its wiki page."""
    lines = [DENY_HEADER]
    lines.extend(
        f"- {CODE_PREFIX}{finding.code} at: {finding.snippet}\n"
        f"  {HAZARD_BY_CODE[finding.code]}\n"
        f"  {WIKI_URL_PREFIX}{finding.code}"
        for finding in findings
    )
    lines.append(DENY_FOOTER)
    return "\n".join(lines)


def main() -> None:
    """Read the PreToolUse payload from stdin and print a deny decision when needed."""
    payload = HookPayload.model_validate_json(sys.stdin.read())
    if payload.tool_name != BASH_TOOL_NAME or payload.tool_input.command is None:
        return
    findings = find_findings(payload.tool_input.command)
    if not findings:
        return
    decision = {
        "hookSpecificOutput": {
            "hookEventName": HOOK_EVENT_NAME,
            "permissionDecision": "deny",
            "permissionDecisionReason": deny_reason(findings),
        }
    }
    print(json.dumps(decision))


if __name__ == "__main__":
    main()
