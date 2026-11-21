# claude-config

Claude Code user config, symlinked into `~/.claude` (or `$CLAUDE_CONFIG_DIR`) on Linux, macOS and Windows.

```sh
make setup     # install the prek git hook
make install   # link config/ entries into place; Windows without make: uv run sync.py install
make status    # show link state, diff any link replaced by a regular file
make check     # all pre-commit checks via uvx prek
make update-hooks  # bump hook revs older than 7 days
```

- Managed entries: `CLAUDE.md`, `settings.json`, `keybindings.json`, `agents/`, `commands/`,
  `hooks/`, `rules/`, `skills/`.
- `hooks/guard_rm_variable_path.py` (PreToolUse on Bash) denies `rm` arguments such as `"$DIR"/*` or
  `$DIR/Users` that reach a path from `/` when the variable is empty, and tells the agent which path
  each would delete. It runs through `uv run --script`; its first run downloads tree-sitter and pydantic.
- `hooks/guard_shellcheck_rules.py` (PreToolUse on Bash) denies commands on which ShellCheck reports
  SC2094 (same file read and written in one pipeline), SC2088 (quoted tilde), SC2146 (`find -o`
  without grouping) or SC2216 (pipe into `rm`), with why the command is wrong and the wiki link.
- Hook tests: `uv run --with pytest --with pydantic==2.14.4 --with tree-sitter==0.26.1
  --with tree-sitter-bash==0.25.1 --with shellcheck-py==0.11.0.1 pytest tests -q`.
- Machine copies that conflict with the repo are kept under `~/.claude-config-backup/<timestamp>/`.
- Windows needs Developer Mode (or an elevated shell) to create symlinks.
- Claude Code edits `settings.json` through the link, re-serialising it; expect key reordering in diffs.
- Edits made to `config/settings.json` in the repo reached a running session only after a restart,
  and a settings change made inside that older session (e.g. `/effort`) wrote its stale copy back,
  dropping the repo edits. Restart sessions after editing `config/settings.json`.
- Not synced: `~/.claude.json`, credentials, history, projects, plugins and `skills/synced/`
  (account-synced skills Claude Code manages).
