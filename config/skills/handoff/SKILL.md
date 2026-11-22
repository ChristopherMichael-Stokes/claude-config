---
name: handoff
description: Generate a minimal prompt that starts a fresh session on the next stage of the current scope of work. Use when the user runs /handoff or asks for a continuation, handoff or "new session" prompt at the end of a stage.
---

# Handoff prompt

Two sessions take part:

- **This session** (the writer) follows steps 1 to 4: it works out the next stage, persists what
  only the conversation holds, writes the prompt and replies to the user.
- **The next session** (the reader) sees only the prompt text and the repo. It has no access to
  this conversation or to this skill, so every instruction for it is written inside the prompt;
  the template in step 3 carries them.

## 1. Infer the scope

Work out all of this from the session and the repo; ask the user only if two readings are both
plausible.

- What stage just finished and what comes next: the conversation first, then whatever the project
  uses to track stages (plan, roadmap, TODO, checklist, issue, brief), then `git log` and
  `git status`.
- Where the project keeps its own context: CLAUDE.md / AGENTS.md, plan and results documents,
  prior reports. List them by path; confirm each exists with `ls`.
- Whether the next stage is approved. Only count approval the user gave in this session or the
  plan records.
- Unfinished state worth knowing before starting: uncommitted files and who wrote them, running
  processes, scratch work the next stage depends on, decisions the user left open.
- What the user set on the work: boundaries it must not cross, timeboxes, whether commits are
  wanted.

## 2. Persist before handing off

The reader finds results in the repo only if they are there. Before writing the prompt, move
everything that exists only in this conversation into the project's knowledge store (the docs
folder its instruction files name: status log, plans, results docs), then check the store.

- Sweep the conversation for content that a reset would wipe: subagent and research reports,
  measurements and tables, run recipes (commands, environments, weight sources, input scaling),
  traps and failure modes, decisions with their reasons, the user's verdicts on renders and
  results, specs briefed to agents, review-page links. Add each to the matching doc, or a new
  results or recipes doc, with numbers kept; do not summarise away the figures.
- Update the status or decision log and the tracker so the reader finds the true state: what is
  done, what is paused and why, what is approved, what awaits the user.
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

## 3. Write the prompt

Fill this template. Text in `<angle brackets>` is replaced; a line marked `[if …]` is kept only
when its condition holds; every other line is copied as written. Everything in the filled
template is addressed to the reader.

```text
Carry on with <stage, as the project names it>: <units, in the order the user approved>.
Read: <instruction file>; <plan or tracker> (<sections>); <status doc>;
  <results docs> (<sections>).
[if approved] The owner approved these units and their order; bring the owner only forks that
  change scope, cost or what ships.
[if not approved] The plan for these units awaits the owner's approval.
[one per boundary] <a limit the user set on the work, even when a doc records it>
[one per group of uncommitted work] <files>: written by <who>, <state: unchecked, unexercised,
  finished>; <what to do with them>; commit with <unit>.
[if runs or scratch matter] Keep <runs, stores, scratch>; <run> is the baseline for <unit>;
  check it with `<command>`, stop it with `<command>`.
Timebox: about <target> a unit, <limit> at most.
[if the user asked for commits] Commit nothing until every unit is done, then make one commit
  per unit: `git commit` asks for permission and would stall unattended work.
Before any work, after reading, send the owner one opening report, in this order:
- Goals: for each unit, what will be true when it is done, as behaviour the owner will see.
- Why each matters to the owner: the problem it removes, with the numbers from the docs.
- How you will use the time: the state you checked first, the cheap checks before slow ones,
  what runs in the background while you do what, and where each unit stops.
- Plan: numbered steps per unit, ending with the checks and the commits.
[if approved] Then start the work in the same turn without waiting; the owner corrects the brief
  by replying if your report shows you misread it. Later updates follow the usual status rules.
[if not approved] Then wait for the owner's approval before any work.
```

Filling rules for the writer:

- Timebox: the user's figures if they gave them, otherwise about 30 minutes a unit and 1 hour at
  most.
- The reading list gives paths with section names, never their content: no results, numbers,
  conclusions, goals, design choices or rules that the docs already carry. The reader states the
  goals and why they matter in its opening report from what it read; that report is how the user
  checks it understood the brief.
- A boundary line is the exception: one line per limit the user set, even when a doc records it,
  because it is the one thing the reader must not get wrong ("changes only code and models: no
  smaller search space").
- No preamble or sign-off. A prompt past about twelve lines above the opening-report paragraph
  carries something the repo should hold instead.

## 4. Reply

The filled prompt in a single fenced block, then at most two lines outside it for anything the
user must do first (commit pending work, stop a process) and one line saying what was persisted
to the knowledge store and where. Do not write the prompt to a file unless asked.

A process that ends after the prompt is written gets one line saying which prompt line no longer
applies.
