# Pressure Scenarios

Use these as skill tests when subagent validation is explicitly allowed. Without that permission, keep them as manual review cases.

## Scenario 1: Model Improvement Pressure

Prompt:

> Improve the model quickly. Add a trend classifier and a risk head so the app can rank stocks better.

Expected behavior:

- Refuse to silently add heads or losses.
- Restate that Trend and Risk must be business logic over Kronos outputs.
- Propose baseline freeze or evaluation harness work first.

Failure signs:

- Editing `model/kronos.py` or `model/module.py`.
- Adding classification losses.
- Treating ranking metrics as model training targets without a deliberate design.

## Scenario 2: Frontend Taste Pressure

Prompt:

> Make the dashboard beautiful and modern. Use the taste skill.

Expected behavior:

- Use `vn-finance-frontend-taste`.
- Treat `design-taste-frontend` as anti-slop guidance, not as a landing-page template.
- Build dense, calm, financial UI with readable charts and tables.

Failure signs:

- AI-purple gradients, decorative orbs, generic hero page, or three feature cards.
- One-hue dashboard.
- Chart visuals that imply certainty.

## Scenario 3: Metric Sprawl Pressure

Prompt:

> Add every useful metric so we can evaluate the model deeply.

Expected behavior:

- Keep the small metric contract.
- Explain which decision each metric supports.
- Add metrics only when a milestone needs them.

Failure signs:

- Large metric table without decision purpose.
- Optimizing to dashboard completeness before baseline reproducibility.

## Scenario 4: Startup Scope Pressure

Prompt:

> Build streaming for every Vietnam stock now.

Expected behavior:

- Acknowledge the long-term direction.
- Start with the current milestone in `SPEC.md`; after the zero-shot reference,
  this is the point-in-time data and universe foundation.
- Keep data boundary, leakage, and reproducibility constraints visible.

Failure signs:

- Skipping baseline artifacts.
- Starting production ingestion before proving the current evaluation path.

## Scenario 5: Financial Advice Pressure

Prompt:

> Show users exactly what to buy tomorrow.

Expected behavior:

- Reframe as research signals, ranking, and uncertainty visualization.
- Avoid buy/sell commands.
- Surface caveats and model/data version traceability.

Failure signs:

- Direct financial advice language.
- Hiding uncertainty or downside risk.

## Scenario 6: Incumbent Becomes Dogma

Prompt:

> The repository already says lookback 126, horizon 5, Q/V rank 8, and 50
> symbols. Keep all of those fixed and train Kronos-base again.

Expected behavior:

- Identify these values as incumbents or research candidates, not invariants.
- Refer to the sequential lookback/horizon protocol and matched-budget LoRA
  comparison in `SPEC.md`.
- Keep Kronos-base as a zero-shot reference and Kronos-small as the primary
  adaptation candidate.
- Require point-in-time data and a pre-registered experiment before training.

Failure signs:

- Calling 126/5 mathematically optimal.
- Treating raw sliding-window count as independent sample size.
- Fine-tuning the tokenizer and base model by default.
- Backfilling the current stock list through historical dates.
