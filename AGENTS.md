# AGENTS.md - Immutable First-Read Rules

> This file is the repository's first-read operating rule for coding agents.
> Treat it as immutable. Do not edit, weaken, bypass, or reinterpret these rules
> unless the user explicitly asks to change this file.

After reading this file, also read `GEMINI.md` and `SPEC.md` before making
project-level decisions. Merge these rules with project-specific instructions.
When instructions conflict, prefer the more cautious and more specific rule.

## Purpose

These guidelines reduce common LLM coding mistakes. They intentionally bias
toward caution over speed. For trivial tasks, use judgment, but do not skip the
core discipline: understand first, change only what is needed, and verify.

## 1. Think Before Coding

Do not assume. Do not hide confusion. Surface tradeoffs.

Before implementing:

- State assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them instead of silently choosing.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop, name what is confusing, and ask.

## 2. Simplicity First

Write the minimum code that solves the problem. Add nothing speculative.

- No features beyond what was asked.
- No abstractions for single-use code.
- No flexibility or configurability that was not requested.
- No error handling for impossible scenarios.
- If 200 lines could safely be 50, rewrite it.
- Ask: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

Touch only what you must. Clean up only your own mess.

When editing existing code:

- Do not improve adjacent code, comments, or formatting.
- Do not refactor things that are not broken.
- Match existing style, even if you would do it differently.
- If you notice unrelated dead code, mention it. Do not delete it.

When your changes create orphans:

- Remove imports, variables, functions, and files that your change made unused.
- Do not remove pre-existing dead code unless asked.

The test: every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

Define success criteria. Loop until verified.

Transform tasks into verifiable goals:

- "Add validation" means write tests for invalid inputs, then make them pass.
- "Fix the bug" means write a test that reproduces it, then make it pass.
- "Refactor X" means ensure tests pass before and after.

For multi-step tasks, state a brief plan:

1. Step -> verify: check.
2. Step -> verify: check.
3. Step -> verify: check.

Strong success criteria let you loop independently. Weak criteria like "make it
work" require clarification before implementation.

These guidelines are working when diffs are smaller, unnecessary changes are
rarer, rewrites from overcomplication decrease, and clarifying questions happen
before implementation mistakes.
