---
name: vn-finance-frontend-taste
description: Use when designing or editing Stock-VN-Forecasting frontend screens, Kronos Path Viewer, financial charts, dashboards, ranking tables, risk panels, or user-facing market analytics where the installed design-taste-frontend skill must be adapted to dense finance/product UI.
---

# VN Finance Frontend Taste

## Overview

This is a finance-dashboard adapter for the installed `design-taste-frontend` skill. Use its anti-slop taste rules, but do not copy its landing-page bias into this product UI.

## Design Read

Default read:

> Reading this as: a trust-first Vietnam equity research dashboard for model inspection and ranking, with a dense but calm product language, leaning toward restrained analytics UI rather than a marketing page.

Default dials:

- `DESIGN_VARIANCE: 4`
- `MOTION_INTENSITY: 2`
- `VISUAL_DENSITY: 7`

For the Kronos Path Viewer, density may drop to 6 so the chart can breathe.

## Required Sub-Skill

Read `design-taste-frontend` when available, but apply it selectively:

- Keep anti-default discipline, color checks, typography discipline, responsive checks, and pre-flight rigor.
- Ignore its landing-page assumptions for dashboard surfaces.
- Do not create a hero-first marketing page unless the task explicitly asks for a landing page.

## Finance UI Rules

- Prioritize trust, scan speed, and uncertainty over decoration.
- Use neutral structure plus multiple semantic accents, not a one-hue AI palette.
- Green/red may encode market direction, but never rely on color alone.
- Use amber for caution/risk and blue or cyan for model/forecast state only when consistent.
- Avoid buy/sell advice language. Prefer "signal", "forecast", "rank", "risk", "watchlist".
- Use compact panels, tables, tabs, filters, legends, and tooltips. Avoid nested cards and generic feature-card layouts.
- Use charts as the primary visual asset. Do not fake screenshots or use decorative finance imagery as the main proof.

## Kronos Path Viewer Rules

- Actual path: solid, readable, neutral or white depending on theme.
- Sample forecast paths: thin, low opacity, visible enough to show dispersion.
- Mean or median path: stronger line, clearly labeled.
- Confidence band: translucent, not visually dominant.
- Forecast boundary: visible vertical marker at prediction start.
- Derived trend/risk badges: explain from forecast path features, not from hidden model heads.
- Never imply deterministic price prediction.

## Pre-Flight

Before finishing frontend work, check:

- No AI-purple default, decorative orbs, glass-heavy gimmicks, or generic hero.
- No one-color dashboard. Semantic accents have clear meaning.
- Tables and charts remain readable on mobile and desktop.
- Text does not overlap or wrap awkwardly inside fixed controls.
- Loading, empty, and error states exist for data surfaces.
- The UI shows model/data timestamp or version when available.
- Financial outputs read as research signals, not advice.

## References

- Read `references/dashboard-design.md` before designing a new screen or changing layout.
- Read `references/chart-preflight.md` before implementing or reviewing charts.

If a requested surface is a public landing page rather than the app itself, use `design-taste-frontend` directly and keep this skill as finance-domain context.
