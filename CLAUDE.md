@AGENTS.md

## Claude Code

The skills named in `AGENTS.md` are installed as user-level plugins. Invoke them
by their plugin names: `andrej-karpathy-skills:karpathy-guidelines`, and
`mattpocock-skills:<name>` for every other skill in the table. The copies in
`.agents/skills/` are for other agents; Claude Code does not read that
directory.

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
