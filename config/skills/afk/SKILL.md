---
name: afk
description: >-
  Carry approved work on unattended for a time window the user gives (/afk 2h, "I'm afk for a
  couple of hours"), using the time efficiently and ending with a report ready for their return.
  Use when the user runs /afk, or says they are going afk or away and the work should carry on
  without them.
---

# Away from keyboard

The user is gone until a stated time. Work done in that window counts; a turn that ends waiting
for an answer idles the session until they return.

## Start

- Take the window from the arguments (`2h`, `90m`, "until 3pm"). With no window given, ask for
  one before the user leaves; that is the only question.
- Run `date`. Set the return time and a hard stop 10 minutes before it, kept for the closing
  report. Both go in the opening report as clock times.
- On macOS, keep the machine awake for the window: `caffeinate -i -t <window in seconds>` as a
  background command. A sleeping Mac kills the response mid-run.
- The work queue is what the user approved, in their order. Work outside it stays out, however
  quick; an empty queue ends the window early.
- Give each item a timebox: the user's if they gave one, otherwise about 30 minutes with 1 hour
  at most.
- Send one opening report, then start without waiting:
  1. the goals, in the user's words where they gave them;
  2. why each matters to the user;
  3. how the time will be used: what runs in the background, what is checked cheaply first,
     where each item stops;
  4. the plan with each item's timebox, the hard stop and the return time;
  5. the questions the user said they will ask on return, if they named any.

## Keep working

- End a turn only while a background job, subagent or Monitor will wake the session. With
  nothing armed, start the next item instead.
- A fork that is the user's call parks only the item it belongs to. Write the question with a
  recommendation into the project's decision log, leave that item's work uncommitted, and move to
  the next item. Never pause unrelated work for it.
- Technical and in-scope calls get made and logged with the alternative not taken, per the
  unattended rules in the global instructions.
- A stop line you set yourself (a threshold, a tolerance, a pass bar) is judged against what the
  user's use can notice, not against a tight number of your own. Take the faster or simpler
  option when its difference sits well below the task's own error scale, and report the
  difference instead of rejecting the option.
- A tool call refused by a permission rule (a new dependency, a blocked command) gets the in-scope
  alternative; the refused option goes in the closing report as the user's call.
- Make no commits until every item is done: `git commit` asks for permission and stalls the
  session. Commit at the end, one commit per item, only when the user asked for commits.
- Keep the machine busy. Long runs go to the background with a log and a Monitor; docs,
  comparison scripts, review of agent diffs and the next item's preparation happen while they
  run. Two jobs whose timings matter never run at once.
- At an item's timebox: stop it, record where it stands and how to resume in the project's status
  or results doc, and move on.
- After each item, update the status doc and run `date`. A usage limit or crash then loses
  nothing, and the clock decides whether the next item fits before the hard stop.
- A subagent that stops early (usage limit, crash) leaves its edits recorded as unchecked, with
  what remains; finish them inside its item's timebox or park them.

## Finish

By the hard stop:

- Nothing running unless the closing report names it with how to stop it; stop `caffeinate`.
- The project's checks pass on the final tree; commits made if the user asked for them.
- The status doc, results docs and decision log hold the window's state.

The closing report is the last message, so it is on screen when the user returns:

1. Answers to the questions the user said they would ask, in their order.
2. A table, one row per item: state (done and committed, done and uncommitted, parked, not
   started), commit hash, and the result with its numbers.
3. Decisions made on the user's behalf, each with the alternative not taken.
4. Parked forks awaiting the user, each with the recommendation.
5. What is still running or kept (runs, stores, scratch) and where.

Finishing early is fine; say when the queue ran out.
