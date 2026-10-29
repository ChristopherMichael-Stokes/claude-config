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
- Machine copies that conflict with the repo are kept under `~/.claude-config-backup/<timestamp>/`.
- Windows needs Developer Mode (or an elevated shell) to create symlinks.
- Claude Code edits `settings.json` through the link, re-serialising it; expect key reordering in diffs.
- Edits made to `config/settings.json` in the repo reached a running session only after a restart,
  and a settings change made inside that older session (e.g. `/effort`) wrote its stale copy back,
  dropping the repo edits. Restart sessions after editing `config/settings.json`.
- Not synced: `~/.claude.json`, credentials, history, projects, plugins and `skills/synced/`
  (account-synced skills Claude Code manages).
