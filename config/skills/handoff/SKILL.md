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

## Persist before handing off

The new session finds results in the repo only if they are there. Before writing the prompt, move
everything that exists only in this conversation into the project's knowledge store (the docs
folder its instruction files name: status log, plans, results docs), then check the store.

- Sweep the conversation for content that a reset would wipe: subagent and research reports,
  measurements and tables, run recipes (commands, environments, weight sources, input scaling),
  traps and failure modes, decisions with their reasons, the user's verdicts on renders and
  results, specs briefed to agents, review-page links. Add each to the matching doc, or a new
  results or recipes doc, with numbers kept; do not summarise away the figures.
- Update the status or decision log and the tracker so a fresh session reads the true state: what
  is done, what is paused and why, what is approved, what awaits the user.
- Record scratch and running state: which scratch directories exist, what each holds, which the
  next stage reads (inputs, caches, stores, features, weights), how to rerun, and any process
  still running with its log path and how to stop it. Move model weights or data that live only
  in an ephemeral location (a session scratchpad, a temp dir) somewhere durable, or record how to
  recreate them.
- Never delete scratch as part of a handoff. List what could be removed and what it would cost
  to regenerate; deletion is the user's decision.
- Follow the project's own rules for commits: commit docs only if the user has allowed it;
  otherwise leave them uncommitted and say so in the reply.
- Reread the knowledge store against the conversation once: anything the next stage needs that
  is still only in the conversation goes in before the prompt is written.

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
must do first (commit pending work, stop a process) and one line saying what was persisted to the
knowledge store and where. Do not write the prompt to a file unless asked.
