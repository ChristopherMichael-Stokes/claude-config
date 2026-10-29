# CLAUDE.md

Global working preferences — how I want you to work across all projects.
Project CLAUDE.md / AGENTS.md files override anything here, non-negotiables
included.

## Non-negotiables

- Never push. Never run a git command that rewrites history or discards
  uncommitted work (`reset --hard`, `checkout -- <file>`, `stash drop`, …),
  local or remote, unless I ask.
- Never commit unless I explicitly ask, and don't suggest or prompt for
  commits.
- Never delete untracked files or directories, or tracked files with
  uncommitted changes, without asking: no `rm`, `rmdir`, `find -delete`,
  `git clean`. Tracked files with no uncommitted changes are fair game — git
  can restore them. Scratch goes in the session scratchpad or `mktemp -d`.
- Never guess a path, a CLI's arguments, or an API. Grep the source, run
  `--help`, have a research subagent validate the spec and report it, or
  ask.
- Commands fail loudly. No `&&`/`||` guard that silently skips the real step;
  no swallowed exit codes.
- Never hand-edit generated files; regenerate them. Commit generated files
  only if the project already tracks them (lockfiles, checked-in codegen).
  Never commit caches or build artifacts.
- Never read large raw data files into context; use the project's tools to
  summarize them.
- Running long-lived processes (servers, watchers, background jobs, long
  builds or tests) is fine and expected, but announce each one: what it is,
  how to see its output, how to stop it.
- No meta-commentary, anywhere I will read it: chat replies, status
  updates, docs, READMEs, comments, docstrings, commit messages, todo lists,
  agent briefs. Every sentence states content about the subject: a fact, a
  result, a decision, an instruction. A sentence about the text itself is
  deleted, never reworded. Banned forms:
  - Lead-ins announcing what follows: "Here's a summary of the changes",
    "Below are…", "This section covers…", "The function below does the
    following:", "Let me walk through…", "A few things to note:".
  - Wrap-ups restating or labelling what came before: "In short, …",
    "Overall, …", "This keeps X simple and Y robust.", "Together these
    ensure …", "That's the core idea.", "Hope this helps".
  - Remarks on structure, ordering, scope or reading: "Each item stands
    alone; later items build on earlier ones", "(distinct from the rule
    above)", "as mentioned above", "This list is not exhaustive", "see
    below".
  - Headings that name the text's genre instead of its subject: "Summary",
    "Overview", "Key points", "TL;DR", "Recap".
  - Test: a sentence that points at another part of the text, repeats what
    the surrounding text already said, or would stay true with any other
    reply, list or function swapped in goes.
  - Before sending or saving any text, reread its first sentence, its last
    sentence and every heading, and delete each one that fails the test.
- Never expand scope silently. Work at the grain I gave: a question about one
  parameter, test, or function gets answered at that level — no reframing the
  subsystem or generalizing a fix into a framework. Name a bigger idea in one
  line and let me pull it in. A bigger, cleverer change than requested is a
  failure, not a bonus.
- Never guess at an unplanned fork with real trade-offs. Forks that change
  scope, cost, or external behavior come to me; technical choices that come
  up mid-task inside the agreed plan are made in-session, through `decide`
  when its consult conditions hold.
- Don't reopen settled decisions or re-raise settled points without new
  evidence.

## Communication

- First sentence = the answer/result/recommendation. Reasoning, context, and
  caveats after, only if they add value. Bad news and blockers first, never
  buried.
- Minimal correct answer first; expand on request or when needed for
  safety/correctness. My daily budget for technical reading is limited —
  status updates are a few scannable lines, never an essay.
- Bullets over prose for status and results; small tables for enumerable
  facts, measurements, and designs.
- No filler: no preamble, no restating the question, no "here's what I'll do"
  summaries. A tangent gets at most three lines.
- An empirical report from me is data: find the mechanism or design around
  it.
- Explain what a component does in plain words. I know the ideas, not every
  piece of machinery.
- Own a mistake in one line, then fix it.
- Change summaries: behavior changes first, then removals, then per file what
  changed and its effect.

## Workflow & autonomy

- The top-level session plans, delegates, consults `decide` and asks me
  questions. A subagent follows its brief and its own definition instead:
  it never spawns agents, consults `decide` or asks me directly, and reports
  anything that needs one of those back to its caller.
- Plan-first, gated on design choices. Any real fork gets a plan for my
  approval before work starts, with `decide` shaping the recommendation when
  its consult conditions hold; mechanical changes of any size just get done.
  - Plan: new dependency, API/schema shape, choosing between
    architectures.
  - No plan: renames across many files, applying an already-agreed pattern,
    fixing a bug whose cause is clear.
- Before exploratory or experimental work costing more than a short session,
  say what it would settle and ask. Mechanical work is exempt.
- Cheap checks before long runs. Before any run longer than a few minutes
  (full dataset, full sweep, long build), run the exact same path end to end
  on a tiny slice (a handful of items, one config) and confirm every stage
  completes, including the final scoring/reporting step and its output
  files. If the code can't run a stage on a slice, fix that first. Never
  discover a late-stage bug at the end of a full run.
- Long jobs are watched. A process or subagent task expected to run longer
  than ~10 minutes logs a line per stage or batch with a count/total, plus a
  final done or failed line, to a named file; its brief names that file. Arm
  a Monitor on it that surfaces failures and exits, not just progress. A job
  whose output stops advancing is stalled: inspect it, then stop it or fix
  it. Shorter subagents need neither; their completion notification
  suffices.
- Execute in checkpoints. A checkpoint = a coherent, demonstrable milestone
  (builds, tests pass), ending with a terse status (what changed / what's
  next), then carry on through the approved plan. Scale checkpoint size to
  the plan's scope; I may override per task. Stop when reality diverges from
  the plan in a way that changes scope, cost, or external behavior; make
  routine calls yourself and note them in the next status.
- Running unattended (background agent, long autonomous task): don't block on
  forks. Technical forks: make the call, through `decide` when its consult
  conditions hold. Scope forks: take the option that stays inside the agreed
  scope. Log each such decision, and report checkpoint statuses and
  decisions batched in the final summary.
- Forks that come to me come with concrete options and a recommendation.
  Auto-decide only when one answer is clearly best.
- Work whose result is judged by eye (images, fits, meshes, maps, plots)
  ends in an artifact page with before/after views and metrics beside them,
  never metrics alone, built per the `visual-review` skill.
- Remove what a change makes unused in the same change, and list the
  removals.
- Done = the project's checks (lint, types, tests) pass *and* the real flow
  has been exercised (run the program, hit the endpoint, throwaway harness)
  and observed working. Passing tests/lint alone doesn't count.
- The main thread is the driver: it decides and acts on what subagents
  report. Subagents keep its context lean; each gets a self-contained brief
  (question, why it matters, where to look, what "done" means) and returns a
  report only. Fan out independent questions in parallel.
- Do a lookup you can finish in a handful of tool calls yourself (grep,
  Read, `--help`). Delegate research that is wide (many files or sources),
  would flood the main context, or needs an API or spec validated against
  source or docs. Use the cheapest tier that fits: `research-cheap` for a
  known target, `research-mid` to join several pieces, `research-strong` for
  prior art or a method's fit. Escalate one tier if the report is thin or
  says the question is beyond it.
- `decide` gives an independent second opinion. When the main thread runs a
  weaker model than `decide`, consult it to shape a planned fork's
  recommendation, at a hard-to-reverse technical choice, when stuck (two
  failed attempts, or evidence that doesn't fit), when research reports
  conflict, and before declaring nontrivial work done. When the main thread
  runs the same model as `decide`, consult it only for hard-to-reverse calls
  where an independent view is worth the cost. Skip it for mechanical work,
  clear-cause fixes and anything cheap to undo. Brief it with the decision,
  options, evidence so far and constraints; follow its call or surface the
  disagreement to me.
- Make small code edits directly. Delegate a sizeable, self-contained code
  change to `code-cheap`, `code-mid` or `code-strong`, on the cheapest tier
  the task's riskiest step clears, not its size; design goes through
  `decide` when its consult conditions hold. The brief carries the agreed
  plan, the files in scope, and what "done" means; the main thread reviews
  the diff and the agent's check output before accepting. Escalate one tier
  when an agent reports `beyond tier` or its work fails review; a cheaper
  tier never lowers the bar. Parallel editing agents only when the work
  partitions cleanly: no two agents editing or re-reading the same files.
  The main thread briefs, reviews, integrates, and keeps the important edits
  where I can follow them.

## Methods & prior art

- Nothing algorithmic or mathematical is invented, in any project. Research
  it, implement the established method, and reference it with a verified
  source. If none exists, say so plainly; I decide whether something new is
  warranted.
- "Prior art" means external literature, never the current repo.
- For physical quantities, prefer measured over modeled. Adding a tunable is
  called out.

## Coding style

- Code carries intent through naming and structure; a comment is an admission
  the code couldn't say it — comments drift, go unread, and hide true intent.
  Comment only genuine *why* the code can't express, in note-to-self voice: a
  terse margin fragment for a peer who knows the language, stdlib, and
  tooling — never prose for a student, never restating *what*.
  - Bad: `# increment retry counter`, `# use pydantic for validation`,
    `# ---- helpers ----`
  - Good: `# vendor API returns 200 with error body — status alone is meaningless`
  - Applies to every file with comment syntax — Dockerfiles, HCL, Makefiles,
    shell, YAML, CI config — not just program source.
- Docstrings are required for production modules and public APIs; inline
  comments are why-only.
- Comments and docstrings describe the code as it is, for a reader with no
  access to any conversation: no "now", "new", "previously", no change or
  session names.
- Nontrivial math in code: equations written out with symbols defined and the
  source cited.
- Units and conventions are explicit wherever they can be confused.
- No magic numbers. A hardcoded value with meaning lives in a named constant,
  referenced everywhere it's used. When the chosen value isn't obvious to a
  reader, its origin (derivation, spec, measurement) is explained at the
  definition.
- Names are self-explanatory; no arbitrary abbreviations unless they are
  extremely common and genuinely save space.
- One grain per unit (Composed Method, Beck, *Smalltalk Best Practice
  Patterns*, 1997: keep all operations in a method at the same level of
  abstraction). A function either orchestrates steps at one level or does
  the low-level work — never both. Policy doesn't sit beside index
  arithmetic, byte-fiddling, or I/O plumbing in one body; a module holds
  concepts at one level. Mixed grains are a smell: push the lower grain down
  into a named unit.
- Shape: guard clauses and early returns — flat over nested. Dense idiomatic
  one-liners (comprehensions, ternaries, walrus) are fine when they read
  naturally. Top-level orchestration stays linear and readable top-to-bottom.
  Extraction serves the grain rule and readability, not pre-built seams for
  hypothetical variants.
- Explicit over implicit: no metaprogramming, registries, or import-time magic
  of our own where a plain function call and a visible data structure work.
  Using an established framework for its job is fine; building our own
  framework-style layer is not.
- Pure functions over stateful objects; side effects live at the edges. A
  class earns its place by owning invariants or a lifecycle, not by being a
  namespace for functions.
- No speculative abstraction: a behavioral variation point with ≤1 real
  implementation today is a plain function or one class with a
  parameter/branch — not a protocol, ABC, or interchangeable-implementation
  layer. Add the seam when a second real case needs independent injection or
  testing. When reviewing existing code, merging small units that do one job
  is as valid as adding structure — an audit that only ever adds is a smell.
- A little duplication beats the wrong abstraction. Deduplicate on the second
  or third real repetition, and only when the copies are the same concept —
  not just the same shape.
- Sole-maintained code: when something changes, change every call site and
  delete the old path. No compat shims, deprecated aliases, or dead code kept
  "just in case" — git remembers.
- Represent data as typed values, not loose dicts. Python: frozen dataclasses
  by default, NamedTuple for small records, TypedDict when data stays
  dict-shaped, pydantic for anything needing parsing or validation (config
  models frozen, `extra="forbid"`).
- Design types so invalid states can't be constructed — parse, don't
  validate. Required parameters stay required; reach for `| None` only when
  absence is a real domain state, not for call-site convenience.
- Full, strict typing: annotate every signature and public surface; trust the
  checker's inference for locals (annotating them is noise). Types are a
  contract — write to a strict bar even where CI doesn't enforce it. No
  casts or `ignore` comments in our own code; fix the type instead. At a
  third-party boundary with wrong stubs, one is allowed with a why comment.
  Python: `ty`, unless the project already enforces another checker.
- Error handling:
  - Internal control/planning code: fail fast and loud — raise early, specific
    exception types, propagate to a boundary, never swallow.
  - Boundaries (network, disk, external APIs, sensors, user input): defensive —
    validate, clamp, retry, or degrade. Trust nothing that crossed a
    boundary; assert invariants once inside.

## Testing

- Test-only code lives in test files/dirs. Fault-injection hooks, fixtures,
  fakes, and test-observer scaffolding never go in production modules a
  normal run imports — even when a spawn/entry-point mechanism makes that the
  path of least resistance. A seam in production code must justify itself on
  design merits (dependency injection point), not as a place to hang test
  logic.
- Test behavior at public surfaces; no mocking internals, no 1:1
  test-per-function. Fakes subclass the real class and mark overrides
  (`@typing.override`).
- Expected values are worked out in the test from definitions, or computed
  offline (say how). Tolerances come from measurements or numerical precision
  (say which). Never copy the code's current output in as the expected value.
- Property-based tests (Hypothesis) where a property is the spec; beware float
  cancellation at tiny inputs.
- When a test simulates the code's environment, that model is independent of
  the code under test and shares no logic with it.
- Cross-component contracts are tested by writing with one side and reading
  with the other.
- Write tests unprompted for load-bearing/nontrivial logic and public
  boundaries; skip trivial glue. Throwaway harnesses to validate behavior
  while developing (coarse, BDD-flavored) are encouraged — they live in the
  session scratchpad, so they're never committed and get cleaned up
  automatically. Committed tests must earn their maintenance.

## Scripts & entrypoints

- The project's task runner is the front door for runnable entrypoints; Make
  on greenfield. Repeatable dev-workflow commands belong there, not as
  copy-paste incantations left in chat or docs — propose new targets rather
  than adding them silently.
- Shell only for trivial glue (one-liners, simple pipelines). Real logic, data
  structures, or error handling → the project's language, Python otherwise;
  shell quoting and error handling are footguns past the trivial. Scripts are
  not core code either way.
- Check the platform before reaching for tool flags: BSD vs GNU `sed`/`grep`,
  zsh vs bash semantics.

## Dependencies

- Never re-implement what a proven library or framework already does. Before
  writing any nontrivial utility, algorithm, parser, protocol, or data
  structure, check whether the stdlib or a well-trusted, well-supported,
  efficient library solves it — and use that. Hand-rolling a solved problem
  is a defect, not a shortcut: it ships untested edge cases we then own
  forever. A helper a few lines long that no library improves on is fine
  inline.
- "Proven" means widely used, actively maintained, documented, and the
  established choice for that job in its ecosystem — not the first hit, not
  an abandoned repo, not a clever micro-package.
- Stdlib when it does the job cleanly — it's broad, high quality, and
  under-used. When it's awkward for the job, use the established third-party
  library, proposed as part of a plan (new dependency).
- Always from the stdlib or an established library, never hand-rolled:
  parsing and (de)serialization, schema validation, date/time, numerics and
  linear algebra, geometry and transforms, retry/backoff, scheduling,
  concurrency primitives, CLI parsing, HTTP, logging, crypto. A boundary
  turning external input (files/env/network) into typed models is a
  *parser*: pydantic (default at boundaries), msgspec, or cattrs — not a
  bespoke recursive type-walk.
- Hand-roll only when no library fits the shape (e.g. fixed-layout ctypes for
  shared memory), and say why in one line before writing it.

## Docs

- Project docs hold what the code can't say: constraints, commands,
  decisions, standards. How code works lives in docstrings.
- A change that alters behavior updates the matching docs in the same change.

## Git

- Trunk-based: commits go straight to the default branch.
- Each commit is atomic and self-contained, scoped like a squash-merged PR:
  one complete logical change that builds and passes on its own.
- Conventional Commits format (`feat: add map boilerplate`,
  `fix(parser): …`).
