# TASK: Refactor the `processing/` package of RuneMaster to be atomic, simple, and readable

You are refactoring existing, working code. The goal is NOT new features and NOT
a rewrite. The goal is the same behavior, in smaller, clearer pieces.

## 0. Ground rules (read twice)

1. BEHAVIOR MUST NOT CHANGE. Same inputs → same outputs. Same public API.
2. Public API to preserve exactly:
   - `from processing import ProcessingConfig, RuneMaster`
   - `RuneMaster(equipments, config=...)`, `.run_deterministic()`, `.run_all()`
     (alias of deterministic), `.get_summary()`
   - Canonical group fields consumed by `main.py` and `visualization/`
   - Metric definitions (sharing efficiency, quality score, Jaccard, etc.) as
     specified in `processing/PROCESSING.md`
   - `ProcessingConfig` field names and defaults
3. Do NOT touch: `data/`, `models/`, `visualization/`, `main.py`, `serve.py`,
   `capture/`, `resource_cache.db*`, `visualizations/`. If a change there seems
   required, STOP and report it instead.
4. No new dependencies. Python 3.12. Use `uv run ...` for everything.
5. Never run live-API commands. Never run `evolutionary_committee` end-to-end
   unless I explicitly ask (it is slow).
6. Do not "improve" algorithms, rename metrics, or fix bugs you notice. Write
   suspected bugs into `plans/refactor/FINDINGS.md` and move on.

## 1. ANTI-LOOP PROTOCOL (mandatory)

I have seen you get stuck repeating yourself. To prevent that:

- STATE FILE: Maintain `plans/refactor/STATE.md`. Update it after EVERY step
  (format in section 6). At the start of every session and after any
  confusion, re-read ONLY this file, not the whole codebase.
- ONE STEP AT A TIME. Each step touches at most ONE module/concern and at most
  ~150 changed lines. Finish it, verify, commit, update STATE.md, then pick
  the next.
- READ EACH FILE AT MOST ONCE per step. Take notes in STATE.md instead of
  re-reading. Do not re-run `ls`/`grep` for information you already recorded.
- TWO-STRIKE RULE: if the same test fails or the same error appears twice
  after you tried a fix, STOP. Do not try a third variant. Revert the step
  (`git checkout -- <files>`), write what you tried and what failed into
  STATE.md under "BLOCKED", and ask me.
- NO PLAN-ABOUT-PLANS. If you catch yourself restating the plan, summarizing
  what you are about to do for the second time, or "reconsidering", stop and
  execute the next concrete action (a command or a file edit).
- MAX 15 tool calls per step. If you exceed that, stop, record state, ask me.
- If you are unsure between two options, pick the more conservative one
  (smaller change, fewer files moved), note the choice in STATE.md, continue.
- When a step is done, say "STEP N DONE" and the one-line result. Do not
  re-explain it.

## 2. PHASE A: Inventory (no code changes)

Goal: understand what exists. Output goes ONLY to `plans/refactor/INVENTORY.md`.

For every `.py` file in `processing/` (including `processing/experts/`):
- path, line count
- one-sentence responsibility
- public functions/classes (name + one-line purpose)
- who imports it (inside `processing/`, and from outside: `main.py`, `test/`)
- smells: functions >50 lines, files >300 lines, duplicated logic, dead code
  (defined but never referenced), circular imports, config values read in
  multiple places, mixed concerns (e.g., I/O or printing inside algorithms)

Then produce:
- an import graph (text, A → B)
- a list of DEAD CODE candidates (verified by grep across the whole repo)
- a list of DUPLICATED logic groups (which files, which functions)
- the list of symbols re-exported by `processing/__init__.py`

Do not edit any source file in this phase. When done, stop and wait for my OK.

## 3. PHASE B: Safety net (tests first)

Before moving any code:
1. Run `uv run pytest -q` and record the result in STATE.md (baseline).
2. Add characterization tests in `test/` (new file `test/test_refactor_snapshot.py`)
   that lock current behavior on a small, hand-built set of `Equipment` objects
   (6–12 items with overlapping recipes, built in the test, no network):
   - deterministic grouping output (group membership + canonical metrics)
   - random grouping with a fixed `random_seed`
   - hybrid supplementation
   - density filtering (including the fallback-disabled case)
   - `get_summary()` keys and value types
   Store expected values as literals in the test (not recomputed).
3. Run the new tests against the UNMODIFIED code. They must pass. Commit:
   `test: add characterization tests before refactor`.

If you cannot make a snapshot deterministic after two attempts, apply the
two-strike rule.

## 4. PHASE C: Refactor plan

Write `plans/refactor/PLAN.md` as an ordered checklist of atomic steps. Each step:
- ID (S01, S02, ...)
- what moves/changes, in one sentence
- files touched
- how to verify (always: `uv run pytest -q`)
- risk: low / medium

Ordering rules:
1. Delete dead code first (only if verified unreferenced repo-wide).
2. Extract pure helpers (no I/O, no globals) from long functions.
3. Remove duplication by introducing ONE shared helper, then switch call
   sites one at a time.
4. Split oversized files by concern (e.g., graph building / metrics / filtering
   / expert logic), keeping old import paths working via re-exports until
   the end.
5. Consolidate config access: algorithms receive a `ProcessingConfig` (or
   specific values) as parameters; no hidden module-level state.
6. Last: tidy names, docstrings, type hints, and `__init__.py` exports.

Target structure principles (adapt to what the inventory shows; do not invent
more layers than needed):
- One concern per module; one reason to change per module.
- Pure functions for scoring/metrics/similarity (input data → output data).
- Experts share a single small interface (e.g., `propose(equipments, config) -> list[Group]`)
  and contain only strategy-specific logic.
- No function longer than ~40 lines; no file longer than ~250 lines unless
  justified in STATE.md.
- No printing/logging inside pure algorithms; reporting happens at the edges.
- Names say what things are (`compute_pairwise_jaccard`, not `process2`).
- Comments explain WHY, not WHAT. Remove commented-out code.

Stop after writing PLAN.md and wait for my approval.

## 5. PHASE D: Execute the plan, step by step

For each step S_n:
1. State the step ID and goal in ONE line.
2. Make the change (smallest possible diff).
3. Run `uv run pytest -q` and `python3 -m compileall -q processing`.
4. If green: `git add -A && git commit -m "refactor(processing): S_n <summary>"`,
   update STATE.md, then continue to the next step.
5. If red: apply the two-strike rule.

Every 5 steps, stop and give me a short checkpoint report (what changed,
line counts before/after, anything BLOCKED) and wait for "continue".

Moving code rule: when moving a function between files, move it verbatim first
(commit), THEN clean it up in a separate step. Never move and rewrite at once.

## 6. STATE.md format (keep it short, overwrite sections, don't append forever)

```
# STATE
Phase: <A|B|C|D>   Current step: <ID>   Last green commit: <hash>
## Done
- S01 ... 
## Next
- S05 ...
## Notes (facts learned, so I do not re-read files)
- ...
## BLOCKED
- <step>: tried X, got Y, need decision on Z
```

## 7. Definition of done

- `uv run pytest -q` green, including the new characterization tests
- `python3 -m compileall -q data processing main.py config.py test visualization` clean
- `uv run main.py --grouping-method deterministic --no-serve` runs and
  produces the same group count as before the refactor (record both numbers)
- `from processing import ProcessingConfig, RuneMaster` still works
- No file in `processing/` > ~250 lines, no function > ~40 lines (or justified)
- `processing/PROCESSING.md` still accurate; update only file paths/names if
  they changed, never the algorithm descriptions
- `plans/refactor/FINDINGS.md` lists every bug/oddity noticed but NOT changed

## 8. First action

Start Phase A now. Create `plans/refactor/` and `STATE.md`, then do the
inventory. Do not write any code outside `plans/refactor/` until I approve
Phase C.