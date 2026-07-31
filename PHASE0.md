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

## Stress tests for the decision procedure

The following cases from real diffs are designed to stress-test whether the 5-question decision procedure actually discriminates or whether cases quietly pile up in the "ambiguous, default risk-relevant" bucket. If they all land in ambiguous, the procedure needs sharper questions before the classifier is built.

1. **User-Agent string change** (`AgriciDaniel/claude-seo`): changing default UA from bot-style `ClaudeSEO/1.0` to Chrome-like string. Does the procedure resolve this via "does it change what the skill can access" (a UA change affects how servers respond, arguably a capability change) or does it only resolve via the ambiguous-default fallback? The answer is data.
2. **Tool removal under vague purpose** (`AgriciDaniel/claude-seo`, VULN-A01 entry): removing `bash` from allowed-tools when the purpose statement is vague enough that you can't confirm consistency. Should resolve via Q1 (permission change → risk-relevant) or Q5 (ambiguous)?
3. **Metadata drift without behavior change** (`AgriciDaniel/claude-seo`, issue #92): touches multiple files (frontmatter, README, version numbers) but no actual behavior change. Should resolve via Q4 (cosmetic). If it doesn't, the procedure is over-triggering on file count.

Only if hand-labeling turns out to be genuinely hard to agree on (i.e., the cosmetic/risk-relevant line is fuzzy even for a human) does the entire premise need rethinking before Phase 1.

## Candidate skills

1. `blader/humanizer` — 43 commits, real version history, maintainer-written version notes in README, Python-based, ~32k stars. Strong candidate; version notes provide free cross-check signal.
2. `AgriciDaniel/claude-seo` — CHANGELOG with explicit cosmetic/risk-relevant self-labeling, including a tagged VULN severity entry. Rich ground-truth signal across the full classification range.