@AGENTS.md

## Project guardrails

`AGENTS.md` sets how to work; these are the project's hard rules. Each points at
where it is defined. Read `SPEC.md` and `docs/experiments.md` before any
project-level decision.

- `AGENTS.md`, `model/kronos.py` and `model/module.py` change only on the user's
  explicit request.
- A run that produces evidence starts only after its registration is committed
  under `docs/registrations/`: data, dates or folds, candidates, budget, reading
  rule, acceptance criteria. Training runs included.
- A registered threshold may be raised after a result is read and is never
  lowered. A changed threshold means a new registration and a new run.
- `reports/**` and `docs/registrations/**` are frozen once committed. Correct
  `docs/evidence/` by adding a later section, never by editing in place.
- The 2026 lockbox stays closed until the final M3 reading. Check with
  `python evaluation/freeze_milestone_2.py`, which refuses to write if any date
  reaches it.
- Results from two hosts never enter one paired comparison. The host is the
  interpreter path in a manifest's `command` (`docs/evidence/3.12-*`).
- Splits are temporal, windows stay inside one security, missing history is never
  imputed, and every output traces to data, universe, model, config, revision,
  origin and seed (SPEC section 2).
- Outputs are research results, never investment advice.
- Commit, push or tag only when the user asks. Commit messages carry no
  attribution lines.

## Skills

Installed as user-level plugins; copies for other agents live in
`.agents/skills/`, unmodified from their sources. Reach for the skill that
matches the task before working freehand.

| task | skill |
|---|---|
| writing, reviewing or refactoring code | `andrej-karpathy-skills:karpathy-guidelines` |
| a behaviour change or a new function | `mattpocock-skills:tdd` |
| a failing test, a crash, a wrong number | `mattpocock-skills:diagnosing-bugs` |
| reviewing a branch or a diff since a commit | `mattpocock-skills:code-review` |
| stress-testing a registration or a plan before a run | `mattpocock-skills:grilling` |
| a question answered from papers or primary docs | `mattpocock-skills:research` |
| module boundaries, testability, a refactor's shape | `mattpocock-skills:codebase-design` |
| project vocabulary, `CONTEXT.md`, an ADR | `mattpocock-skills:domain-modeling` |
| editing `CLAUDE.md`, `AGENTS.md` or a skill | `mattpocock-skills:writing-for-agents` |
| a throwaway check of an idea | `mattpocock-skills:prototype` |
| steps only the user can perform, such as a GPU host | `mattpocock-skills:wizard` |
| a merge or rebase conflict | `mattpocock-skills:resolving-merge-conflicts` |
| ending a session with work in flight | `mattpocock-skills:handoff` |

## Agent skills

### Issue tracker

Issues live in GitHub Issues for `vminh16/stock-VietNam-forecasting`, via the
`gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

The five default labels: `needs-triage`, `needs-info`, `ready-for-agent`,
`ready-for-human`, `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: one `CONTEXT.md` and `docs/adr/` at the repo root, created when
first needed. See `docs/agents/domain.md`.
