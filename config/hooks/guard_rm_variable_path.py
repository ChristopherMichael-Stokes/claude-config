#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "pydantic==2.14.4",
#   "tree-sitter==0.26.1",
#   "tree-sitter-bash==0.25.1",
# ]
# ///
"""Claude Code PreToolUse hook: deny 'rm' paths that start with an unguarded variable.

When the variable is empty or unset, '"$DIR"/*' or '$DIR/Users' expands to a path from the
filesystem root. An 'rm' argument (directly or behind 'sudo') is denied when it begins with a
parameter expansion that is not guarded by '${VAR:?}' and is immediately followed by '/', and
the text after the expansion (the tail) either

- contains an unquoted glob character, another parameter expansion or a command substitution, or
- is literal and the path it collapses to when the variable is empty exists.

The hook reads the PreToolUse JSON payload on stdin. A denial is a JSON document on stdout
whose reason explains what each argument would delete; an allowed command prints nothing.
"""

import enum
import json
import os
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import tree_sitter_bash
from pydantic import BaseModel, ConfigDict
from tree_sitter import Language, Node, Parser

BASH_PARSER = Parser(Language(tree_sitter_bash.language()))
BASH_TOOL_NAME = "Bash"
HOOK_EVENT_NAME = "PreToolUse"
RM_EXECUTABLE = "rm"
SUDO_EXECUTABLE = "sudo"
SUDO_SHORT_OPTIONS_WITH_VALUE = frozenset("CDghpRrTtUu")
SUDO_LONG_OPTIONS_WITH_VALUE = frozenset(
    {
        "--chdir",
        "--chroot",
        "--close-from",
        "--command-timeout",
        "--group",
        "--host",
        "--other-user",
        "--prompt",
        "--role",
        "--type",
        "--user",
    }
)
END_OF_OPTIONS = "--"
GLOB_CHARACTERS = frozenset("*?[")
GUARD_OPERATOR_TYPE = ":?"
PARAMETER_EXPANSION_TYPES = frozenset({"simple_expansion", "expansion"})
SUBSTITUTION_TYPES = frozenset(
    {"command_substitution", "arithmetic_expansion", "process_substitution"}
)
VARIABLE_NAME_TYPES = frozenset({"variable_name", "special_variable_name"})
DENY_HEADER = (
    "Blocked: an rm argument starts with a variable that, if empty or unset, "
    "expands to a path from the root."
)
DENY_FOOTER = (
    "Change the command so that no empty or unset variable can make rm reach a path from the "
    "root, then re-run it."
)
DOUBLE_QUOTE_ESCAPABLE = frozenset('$`"\\')
DOUBLE_QUOTE_DELIMITER_TYPE = '"'


class Reason(enum.Enum):
    """Why an argument is denied."""

    PATTERN = "its tail has a glob or another expansion, so it can match far more than one path"
    EXISTING_PATH = "that path exists"


class PieceKind(enum.Enum):
    """Role of one adjacent segment of a shell word."""

    LITERAL = enum.auto()
    PARAMETER = enum.auto()
    SUBSTITUTION = enum.auto()


@dataclass(frozen=True)
class Piece:
    """One adjacent segment of a shell word.

    'text' is the value for a literal and the source text for an expansion. 'quoted' is
    true for text inside quotes; 'has_glob' is true for an unquoted, unescaped glob character.
    """

    kind: PieceKind
    node: Node
    text: str
    quoted: bool
    has_glob: bool


@dataclass(frozen=True)
class DangerousArgument:
    """An 'rm' argument that collapses to a path from the root when its variable is empty."""

    argument: str
    variable: str
    collapsed_path: str
    reason: Reason


class ToolInput(BaseModel):
    """The part of a PreToolUse 'tool_input' this hook reads; other tools have no command."""

    model_config = ConfigDict(frozen=True)

    command: str | None = None


class HookPayload(BaseModel):
    """The part of the PreToolUse stdin payload this hook reads."""

    model_config = ConfigDict(frozen=True)

    tool_name: str
    tool_input: ToolInput


def unescape(text: str, escapable: frozenset[str] | None) -> str:
    """Drop backslashes that escape the next character.

    'escapable' limits which escaped characters lose their backslash; None means all.
    """
    characters = iter(text)
    unescaped: list[str] = []
    for character in characters:
        if character != "\\":
            unescaped.append(character)
            continue
        following = next(characters, "")
        if escapable is not None and following not in escapable:
            unescaped.append(character)
        unescaped.append(following)
    return "".join(unescaped)


def contains_unescaped_glob(text: str) -> bool:
    """Return whether 'text' has a glob character not preceded by a backslash."""
    characters = iter(text)
    for character in characters:
        if character == "\\":
            next(characters, None)
        elif character in GLOB_CHARACTERS:
            return True
    return False


def literal_piece(node: Node, text: str, *, quoted: bool) -> Piece:
    """Build a literal piece from the unescaped 'text' of 'node'."""
    return Piece(
        PieceKind.LITERAL, node, text, quoted, not quoted and contains_unescaped_glob(text_of(node))
    )


def flatten_word(node: Node, *, quoted: bool = False) -> Iterator[Piece]:
    """Yield the adjacent segments of the shell word 'node' in order."""
    source = text_of(node)
    if node.type in PARAMETER_EXPANSION_TYPES:
        yield Piece(PieceKind.PARAMETER, node, source, quoted, has_glob=False)
    elif node.type in SUBSTITUTION_TYPES:
        yield Piece(PieceKind.SUBSTITUTION, node, source, quoted, has_glob=False)
    elif node.type == "concatenation":
        for child in node.children:
            yield from flatten_word(child, quoted=quoted)
    elif node.type == "string":
        for child in node.children:
            if child.type != DOUBLE_QUOTE_DELIMITER_TYPE:
                yield from flatten_word(child, quoted=True)
    elif node.type == "string_content":
        yield literal_piece(node, unescape(source, DOUBLE_QUOTE_ESCAPABLE), quoted=True)
    elif node.type == "raw_string":
        yield literal_piece(node, source[1:-1], quoted=True)
    else:
        yield literal_piece(node, unescape(source, None), quoted=quoted)


def text_of(node: Node) -> str:
    """Return the source text of 'node'; the parser always attaches it to a parsed tree."""
    if node.text is None:
        message = f"syntax node {node.type} carries no text"
        raise ValueError(message)
    return node.text.decode()


def walk(root: Node) -> Iterator[Node]:
    """Yield 'root' and every node under it, depth first in source order."""
    pending = [root]
    while pending:
        node = pending.pop()
        yield node
        pending.extend(reversed(node.children))


def sudo_command_index(words: list[str]) -> int:
    """Return the index in 'words' (the arguments after 'sudo') where the wrapped command starts."""
    index = 0
    while index < len(words):
        word = words[index]
        if word == END_OF_OPTIONS:
            return index + 1
        if word.startswith("--"):
            takes_next_word = word in SUDO_LONG_OPTIONS_WITH_VALUE
        elif word.startswith("-"):
            flags = word[1:]
            value_flag_position = next(
                (
                    position
                    for position, flag in enumerate(flags)
                    if flag in SUDO_SHORT_OPTIONS_WITH_VALUE
                ),
                None,
            )
            takes_next_word = value_flag_position == len(flags) - 1
        elif "=" in word and word.split("=", 1)[0].isidentifier():
            takes_next_word = False
        else:
            return index
        index += 2 if takes_next_word else 1
    return index


def is_executable_named(node: Node, executable: str) -> bool:
    """Return whether the command word 'node' runs 'executable', by name or by path."""
    return Path(text_of(node).removeprefix("\\")).name == executable


def rm_arguments(command: Node) -> list[Node]:
    """Return the arguments of 'command' if it runs 'rm', directly or behind 'sudo'; else []."""
    name = command.child_by_field_name("name")
    arguments = command.children_by_field_name("argument")
    if name is None:
        return []
    if is_executable_named(name, RM_EXECUTABLE):
        return arguments
    if not is_executable_named(name, SUDO_EXECUTABLE):
        return []
    wrapped_index = sudo_command_index([text_of(argument) for argument in arguments])
    if wrapped_index < len(arguments) and is_executable_named(
        arguments[wrapped_index], RM_EXECUTABLE
    ):
        return arguments[wrapped_index + 1 :]
    return []


def variable_name(expansion: Node) -> str:
    """Return the name of the variable 'expansion' refers to."""
    name = next((node for node in walk(expansion) if node.type in VARIABLE_NAME_TYPES), None)
    return text_of(name) if name is not None else text_of(expansion)


def is_guarded(expansion: Node) -> bool:
    """Return whether 'expansion' uses the ':?' operator."""
    return any(child.type == GUARD_OPERATOR_TYPE for child in expansion.children)


def collapsed_tail(tail: list[Piece]) -> str:
    """Return the text of 'tail' with expansions left as source text."""
    return "".join(piece.text for piece in tail)


def pattern_reason_applies(tail: list[Piece]) -> bool:
    """Return whether the tail has an unquoted glob or an expansion of any kind."""
    return any(piece.has_glob or piece.kind is not PieceKind.LITERAL for piece in tail)


def inspect_argument(argument: Node, filesystem_root: Path) -> DangerousArgument | None:
    """Return the finding for 'argument', or None when it is not a dangerous candidate."""
    pieces = list(flatten_word(argument))
    if not pieces:
        return None
    leading, tail = pieces[0], pieces[1:]
    if leading.kind is not PieceKind.PARAMETER or is_guarded(leading.node):
        return None
    if not tail or tail[0].kind is not PieceKind.LITERAL or not tail[0].text.startswith("/"):
        return None
    tail_text = collapsed_tail(tail)
    if pattern_reason_applies(tail):
        reason = Reason.PATTERN
    elif os.path.lexists(filesystem_root / tail_text.lstrip("/")):
        reason = Reason.EXISTING_PATH
    else:
        return None
    return DangerousArgument(
        argument=text_of(argument),
        variable=variable_name(leading.node),
        collapsed_path=tail_text,
        reason=reason,
    )


def find_dangerous_rm_arguments(command: str, filesystem_root: Path) -> list[DangerousArgument]:
    """Return every dangerous argument of every 'rm' invocation in the shell 'command'.

    'filesystem_root' is the directory a collapsed path is looked up under; production
    passes '/'.
    """
    source = command.encode()
    tree = BASH_PARSER.parse(source)
    findings = (
        inspect_argument(argument, filesystem_root)
        for shell_command in walk(tree.root_node)
        if shell_command.type == "command"
        for argument in rm_arguments(shell_command)
    )
    return [finding for finding in findings if finding is not None]


def deny_reason(arguments: list[DangerousArgument]) -> str:
    """Return the message telling the agent what each denied argument could delete."""
    lines = [DENY_HEADER]
    lines.extend(
        f"- {argument.argument}: if ${argument.variable} is empty or unset this is "
        f"{argument.collapsed_path} ({argument.reason.value})."
        for argument in arguments
    )
    lines.append(DENY_FOOTER)
    return "\n".join(lines)


def main() -> None:
    """Read the PreToolUse payload from stdin and print a deny decision when needed."""
    payload = HookPayload.model_validate_json(sys.stdin.read())
    if payload.tool_name != BASH_TOOL_NAME or payload.tool_input.command is None:
        return
    arguments = find_dangerous_rm_arguments(payload.tool_input.command, Path("/"))
    if not arguments:
        return
    decision = {
        "hookSpecificOutput": {
            "hookEventName": HOOK_EVENT_NAME,
            "permissionDecision": "deny",
            "permissionDecisionReason": deny_reason(arguments),
        }
    }
    print(json.dumps(decision))


if __name__ == "__main__":
    main()
