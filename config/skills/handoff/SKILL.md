---
name: handoff
description: Generate a minimal prompt that starts a fresh session on the next stage of the current scope of work. Use when the user runs /handoff or asks for a continuation, handoff or "new session" prompt at the end of a stage.
---

# Handoff prompt

Output one paste-ready prompt for a fresh session. The new session has no access to this
conversation, finds past results itself, and is told where to look, not what was found.

## Infer the scope

Work out all of this from the session and the repo; ask the user only if two readings are both
plausible.

- What stage just finished and what comes next: the conversation first, then whatever the project
  uses to track stages (plan, roadmap, TODO, checklist, issue, brief), then `git log` and
  `git status`.
- Where the project keeps its own context: CLAUDE.md / AGENTS.md, plan and results documents,
  prior reports. List them by path; confirm each exists with `ls`.
- Whether the next stage is approved. Only state approval the user gave in this session or the
  plan records; otherwise say the plan awaits approval.
- Unfinished state worth knowing before starting: uncommitted files, running processes, scratch
  work the next stage depends on, decisions the user left open.

## Write the prompt

- One imperative sentence naming the next stage as the project names it.
- Reading list: the project instruction file, the plan or tracker and the stage's row or section,
  then the latest results documents. Paths only.
- One sentence on approval status and who decides open forks.
- Anything the new session cannot find on its own, one line each: unfinished state, a scratch
  location it must reuse, a decision the user already made that is not written down.
- Nothing the repo already says: no results, numbers, conclusions, design choices or rules that
  the instruction files already carry.
- No preamble or sign-off inside the prompt. Shorter is better; a stage that needs more than
  about ten lines has been over-specified.

## Reply

The prompt in a single fenced block, then at most two lines outside it for anything the user
must do first (commit pending work, stop a process). Do not write the prompt to a file unless
asked.
