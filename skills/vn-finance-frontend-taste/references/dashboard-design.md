# Dashboard Design Reference

## Visual Direction

This app should feel like a serious research cockpit for Vietnam equities, not a consumer trading game and not a generic AI landing page.

Use:

- Dense but breathable layouts.
- Clear chart hierarchy.
- Compact filters and selectors.
- Tables optimized for scan, sort, and compare.
- Calm neutral backgrounds with semantic accents.

Avoid:

- Full-page hero sections inside the app.
- Purple/blue AI glow as default branding.
- Single-color palettes.
- Decorative blobs, orbs, and background mesh.
- Over-styled cards for every metric.
- Fake precision and hype copy.

## Palette Guidance

Use a neutral base and semantic accents:

- Background: near-white or dark neutral, depending on existing app.
- Text: high-contrast neutral.
- Positive direction: green.
- Negative direction: red.
- Caution/risk: amber.
- Model/forecast state: blue or cyan.
- Disabled/low-confidence state: muted neutral.

Green/red must be paired with signs, labels, arrows, or icons so the UI remains understandable for color-blind users.

## Layout Guidance

Prefer:

- A persistent header or toolbar for symbol/date/model controls.
- A main chart region for forecast path visualization.
- Adjacent compact panels for metric summary and signal explanation.
- A ranking table with sticky headers if the list is long.
- Tabs for Forecast, Ranking, Risk, and Diagnostics once the app grows.

Avoid nested cards. Use borders, spacing, section headers, and table structure for hierarchy.

## Copy Tone

Use research wording:

- "Forecast path"
- "Expected return"
- "Uncertainty"
- "Signal"
- "Risk"
- "Watchlist"
- "Model run"
- "Data updated"

Avoid advice wording:

- "Buy now"
- "Guaranteed"
- "Tomorrow's winner"
- "Safe stock"
- "Must hold"

## State Design

Every data surface needs:

- Loading state shaped like the final layout.
- Empty state with a clear reason.
- Error state with recovery path.
- Stale-data state when data timestamp is old.
- Low-confidence state when model output is not reliable enough to rank.

## Responsive Behavior

Desktop:

- Chart and table can sit side by side only if both remain readable.
- Keep controls on one or two predictable rows.

Mobile:

- Chart first.
- Controls collapse into compact selectors.
- Ranking table can become a horizontally scrollable table or stacked rows, but values must stay aligned.
- Legends and tooltips must not cover chart lines.
