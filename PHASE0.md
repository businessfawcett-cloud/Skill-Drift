# Phase 0: Validate the Premise

This project is in Phase 0 — hand-labeling real skill diffs to validate that the cosmetic/risk-relevant classification line is sharp enough for humans to agree on, before writing any classifier code.

## What to do

1. Pick 5–10 real skills from public repos with commit/version history.
2. Pull every update each has shipped between tagged releases (where they exist); where a skill has no clean releases, label between the two most recent commits that touch `SKILL.md` or bundled scripts — ignore commits that only touch README/CI/license.
3. Hand-label each diff as `cosmetic` or `risk_relevant`, with a one-line reason. Do this before building anything — this is also the eval set from §5, so it's not wasted work.
4. Cross-check the maintainer-annotated subset against the maintainer's own version notes (e.g., `blader/humanizer`'s README version history). Treat agreement/disagreement as a real inter-annotator signal for that subset only.
5. For the blind subset (no maintainer notes), recruit a second labeler. Even a quick pass from one other person on 10 diffs provides the inter-annotator signal the eval plan requires. If no second labeler is available by Phase 0 start, drop the inter-annotator check from the eval plan rather than leave a metric you can't compute.

## Target

~30–50 labeled diffs minimum, from at least 5 distinct skills, before touching the classifier.

## Phase 0 gate

Only if hand-labeling turns out to be genuinely hard to agree on (i.e., the cosmetic/risk-relevant line is fuzzy even for a human) does the entire premise need rethinking before Phase 1.

## Candidate skills

1. `blader/humanizer` — 43 commits, real version history, maintainer-written version notes in README, Python-based, ~32k stars. Strong candidate; version notes provide free cross-check signal.
2. `AgriciDaniel/claude-seo` — CHANGELOG with explicit cosmetic/risk-relevant self-labeling, including a tagged VULN severity entry. Rich ground-truth signal across the full classification range.