# Architecture

## Distribution by symlink

`sync.py` links each name in its `MANAGED_ENTRIES` from `config/` into the Claude config directory
(`$CLAUDE_CONFIG_DIR`, else `~/.claude`). Claude Code then reads the repo files directly; there is
no build or copy step, and a commit on one machine reaches another by pull plus `make install`.

```text
repo config/CLAUDE.md      <-  ~/.claude/CLAUDE.md       global instructions, every session
repo config/settings.json  <-  ~/.claude/settings.json   permissions, hooks, model settings
repo config/agents/        <-  ~/.claude/agents/         subagent definitions
repo config/skills/        <-  ~/.claude/skills/         skills (skills/synced/ is Claude Code's own)
repo config/rules/         <-  ~/.claude/rules/          path-scoped rules
repo config/hooks/         <-  ~/.claude/hooks/          hook scripts named in settings.json
```

`install` adopts an entry that exists only on the machine into the repo, and backs up a conflicting
machine copy under `~/.claude-config-backup/<timestamp>/` before linking. `status` reports each
entry's state and diffs a link that something replaced with a regular file.

## Instruction layers

- `config/CLAUDE.md` holds the user's working preferences for all projects. Its "Who follows what"
  section splits them between the top-level session and subagents.
- `config/agents/` defines the subagent tiers it names: `code-*` edit, `research-*` read,
  `decide` reviews. Each definition sets model and tools in frontmatter; where a definition and
  `config/CLAUDE.md` disagree, the definition wins.
- `config/skills/` packages procedures loaded on demand; `config/rules/` holds instructions scoped
  by file glob (`paths:` frontmatter).
- Repo-level `CLAUDE.md`, `AGENTS.md` and this file apply only to sessions working in this repo.

## Bash guard hooks

`config/settings.json` registers PreToolUse hooks on the Bash tool. Claude Code runs each with the
tool call as JSON on stdin; a hook prints a `deny` decision with a reason, or nothing to allow.

| Hook | Detects | Mechanism |
|---|---|---|
| `guard_rm_variable_path.py` | `rm` arguments starting with an unguarded `$VAR/` whose tail is a glob or expansion, or collapses to an existing path from `/` | tree-sitter-bash parse of the command |
| `guard_shellcheck_rules.py` | ShellCheck SC2094, SC2088, SC2146, SC2216 | ShellCheck binary from `shellcheck-py`, JSON output |

Each script runs as `uv run --script` with pinned dependencies, so the first call on a machine
downloads them. A hook that fails (no network, crash) is reported by Claude Code and the command
runs unchecked. Tests in `tests/` import each hook by path and also run it as a subprocess.

## Checks

`prek.toml` defines the pre-commit checks run by `make check`: ruff, ty, typos, rumdl for
Markdown, mbake and checkmake for the Makefile, JSON validity and the Claude Code settings schema
for `config/settings.json`.
