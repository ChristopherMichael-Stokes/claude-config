---
name: tidy
description: >-
  Inventory what a line of work has left behind (scratch, build outputs, data stores, caches,
  stale docs, stray processes) and report a keep-or-delete recommendation for each item. Use
  when the user runs /tidy or asks to tidy, clean up, do housekeeping, or says the repo, docs or
  scratch are a mess. Deletes nothing until the user picks.
---

# Tidy

Produce one table of leftovers with a recommendation per row. Deleting, moving and rewriting
happen only for the rows the user approves afterwards.

## Find the leftovers

- Uncommitted and untracked files: `git status --short`, plus the ignored directories the
  project uses for scratch, outputs and data (its instruction files name them).
- Session scratch directories that still hold something a later stage reads.
- Data stores, model weights, downloaded footage and caches, inside the repo and in the
  user-level cache directories the project writes to.
- Docs for agents: files no index links to, files describing work that is finished or
  rejected, and several files covering the same thing.
- Processes this work started that are still running, and the ports they hold.
- Sizes come from `du`; never open large data files to judge them.

## Classify each item

Work out the status from the project's tracker, decision log and `git log`, not from memory:

- shipped: the result is in the production code;
- rejected: the method was dropped and the decision is recorded;
- in progress or paused: a later stage still reads it;
- unknown: say so.

## Recommend

- Delete: leftovers of shipped or rejected work, once every result, measurement and decision
  they hold is in the docs. If one is not, the recommendation is "lift out, then delete", and
  the row names what to lift and where it goes.
- Keep: anything a queued or paused stage reads, and caches or downloads that are slow to
  regenerate, unless disk is tight.
- Merge or retire: docs that overlap or describe finished work. Name the surviving file.
- Stop: stray processes, with the command that stops each.
- Leave session transcripts alone.

## Reply

One table: path, what it is, size, status, recommendation, cost to regenerate. Largest first.
Below it, the total size the delete rows would free. Nothing else.

## After the user picks

- Lift results out before deleting anything that holds them, then delete only the approved
  rows.
- Tracked files with no uncommitted changes can be removed with `git rm`. Untracked files and
  tracked files with uncommitted changes are removed only when their row was approved.
- Regenerate any docs index the project keeps, run the project's checks, and report what was
  removed and how much space it freed.
- Follow the project's commit rules: commit only if the user has said to.
