# Chart Pre-Flight

Use this checklist before finishing any frontend work involving Kronos paths, market data, ranking charts, or risk visuals.

## Forecast Path Chart

- Actual historical path is visually distinct from forecast paths.
- Prediction start is marked.
- Sample paths are thin and semi-transparent.
- Mean or median path is emphasized.
- Confidence band is present when uncertainty is available.
- Axis labels and units are readable.
- Tooltip shows date, actual value when available, forecast summary, and uncertainty.
- Colors remain legible in both light and dark contexts if both exist.
- The chart does not imply deterministic price prediction.

## Ranking Table

- Symbol, latest price or return basis, rank signal, confidence, and risk are visible.
- Sort state is clear.
- Missing data is explicit.
- Top ranks do not use investment-advice copy.
- Color is paired with text or icons.

## Risk Visuals

- Downside or drawdown risk uses caution language.
- Red is reserved for negative direction or risk, not generic decoration.
- Low liquidity or stale data warnings are visible before rank interpretation.

## Interaction

- Hover and selected states are clear.
- Keyboard focus is visible for controls.
- Loading, empty, error, and stale states are implemented.
- Long labels do not overflow fixed-width controls.
- Mobile layout preserves chart readability before secondary panels.
