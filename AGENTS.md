# AGENTS.md

First-read rules for every coding agent in this repository. This file changes
only on the user's explicit request.

## Read order

1. This file.
2. `SPEC.md`: the contract. Data, metrics, gates, milestones.
3. `docs/experiments.md`: where each experiment's config, registration,
   evidence and report live.

When two instructions conflict, follow the more cautious and more specific one.

## Project guardrails

- `model/kronos.py` and `model/module.py` change only on the user's explicit
  request. The loss family stays token cross-entropy and no prediction head is
  added (SPEC section 2).
- A run that produces evidence starts only after its registration is committed
  under `docs/registrations/`: data, dates or folds, candidates, budget, reading
  rule, acceptance criteria. Training runs included.
- A registered threshold may be raised after a result is read and is never
  lowered. A changed threshold means a new registration and a new run.
- `reports/**` and `docs/registrations/**` are frozen once committed. Correct
  `docs/evidence/` by adding a later section, never by editing in place.
- The 2026 lockbox stays closed until the final M3 reading.
  `python evaluation/freeze_milestone_2.py` refuses to write if any date reaches
  it.
- Results from two hosts never enter one paired comparison. The host is the
  interpreter path in a manifest's `command` (`docs/evidence/3.12-*`).
- Splits are temporal, windows stay inside one security, missing history is never
  imputed, and every output traces to data, universe, model, config, revision,
  origin and seed (SPEC section 2).
- Outputs are research results, never investment advice.
- Commit, push or tag only when the user asks. Commit messages carry no
  attribution lines.

## How to work

The full guidelines are `.agents/skills/karpathy-guidelines/SKILL.md`. In short:

1. **Think first.** State assumptions; when a request has two readings, name
   both and ask; say so when a simpler route exists.
2. **Simplest code that works.** Only what was asked: no speculative features,
   single-use abstractions or handling for impossible cases.
3. **Surgical changes.** Every changed line traces to the request. Match the
   surrounding style; mention unrelated dead code rather than removing it; clean
   up only what your own change orphaned.
4. **Verifiable goals.** Turn each task into a check: a failing test made to
   pass, a suite green before and after a refactor. For multi-step work, state
   the plan with a check per step.

## Skills

`.agents/skills/` holds the skills this repository uses, copied unmodified from
their sources. Reach for the one that matches the task before working freehand.

| task | skill |
|---|---|
| writing, reviewing or refactoring code | `karpathy-guidelines` |
| a behaviour change or a new function | `tdd` |
| a failing test, a crash, a wrong number | `diagnosing-bugs` |
| reviewing a branch or a diff since a commit | `code-review` |
| stress-testing a registration or a plan before a run | `grilling` |
| a question answered from papers or primary docs | `research` |
| module boundaries, testability, a refactor's shape | `codebase-design` |
| project vocabulary, `CONTEXT.md`, an ADR | `domain-modeling` |
| editing this file, `CLAUDE.md` or a skill | `writing-for-agents` |
| a throwaway check of an idea | `prototype` |
| steps only the user can perform, such as a GPU host | `wizard` |
| a merge or rebase conflict | `resolving-merge-conflicts` |
| ending a session with work in flight | `handoff` |

Issue tracker, triage labels and domain-doc layout for those skills are in
`docs/agents/`.
