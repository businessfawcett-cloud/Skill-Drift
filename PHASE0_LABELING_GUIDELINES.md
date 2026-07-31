# Phase 0 Labeling Guidelines

## What you're labeling

For each diff between two versions of a skill, assign exactly one label:

- **COSMETIC** — wording, formatting, typo fixes, documentation-only changes. No behavior change.
- **RISK_RELEVANT** — any change that alters what the skill asks the agent to do, what it can access, or what it claims to do vs. what it now does.

## Decision procedure

Work through these questions in order. Stop at the first one that resolves the case.

### 1. Did the diff change a permission, tool grant, or access scope?

If yes → **RISK_RELEVANT**.

Examples:
- Added `allowed-tools: [read, write, bash]` when it was previously `[read, write]` → risk-relevant (new tool permission).
- Removed `allowed-tools: [bash]` → risk-relevant (permission scope reduction — this is a security fix, but it changes what the skill can do).
- Added a new `allowed-tools` entry that didn't exist before → risk-relevant.

### 2. Did the diff change what the skill tells the agent to do?

If yes → **RISK_RELEVANT**.

Examples:
- Added a new detection pattern or workflow step → risk-relevant (new capability).
- Changed an instruction from "check for X" to "check for X and Y" → risk-relevant (expanded scope).
- Changed a prompt to handle a new failure mode → risk-relevant (new behavior).
- Added a new mode (e.g., "pasted-text mode", "file mode", "embedded invocation mode") → risk-relevant (new behavior mode).

### 3. Did the diff change the skill's declared purpose or identity?

If yes → **RISK_RELEVANT**.

Examples:
- Changed the skill's name or description in frontmatter → risk-relevant (identity change).
- A full-purpose rewrite where the skill now does something entirely different → risk-relevant.

### 4. Is the change purely cosmetic?

If yes → **COSMETIC**.

Examples:
- Typo fixes in prose.
- Formatting changes (restructured headings, reorganized sections).
- Em-dash normalization in documentation (not in instructions).
- Version number updates in metadata.
- README rewrites that don't change agent behavior.
- "No skill behavior changes, no breaking changes, no script changes" — maintainer self-labeling as cosmetic-equivalent.

### 5. Is the change genuinely ambiguous?

If you can't tell after working through 1–4, it's a hard case. Label it as **RISK_RELEVANT** (the safe default when uncertain) and note what made it ambiguous in the rationale.

Examples of ambiguous cases (use as reference, not rules):
- **User-Agent string change** — changing the default User-Agent from bot-style to Chrome-like changes how the tool presents itself to servers. This could be a compatibility fix (cosmetic) or an evasion-adjacent behavior change (risk-relevant). Label risk-relevant and explain why.
- **Tool removal under vague purpose** — removing a tool when the purpose statement is vague enough that you can't tell if the removal is consistent with it. Label risk-relevant and note the ambiguity.
- **Metadata drift without behavior change** — a commit that touches multiple files (frontmatter, README, version numbers) but doesn't change any agent instruction. Label cosmetic if you can confirm no behavior changed; risk-relevant if you can't confirm.

## What to ignore

- Commits that only touch README, CI config, or license files.
- Version-bump commits that have no other changes.
- Packaging changes (e.g., "improved distribution and portability").

## What NOT to do

- Do not infer intent beyond what the diff shows.
- Do not label based on what you think the skill "should" do — only what the diff actually changes.
- Do not worry about whether the change is "good" or "bad" — only whether it changes behavior.

## Worked examples from real diffs

### Example 1: Cosmetic (maintainer-labeled)

**Repo:** `blader/humanizer` v2.9.1
**Maintainer note:** "Improved distribution and portability: removed nonportable frontmatter and tool preapprovals, made global installation the documented default, added package validation, removed the duplicated long-form example."
**Label:** COSMETIC
**Reasoning:** No behavior change — packaging, documentation, and installation defaults changed. Tool preapproval removal is a packaging cleanup, not a permission-scope change in the skill's instructions.

### Example 2: Risk-relevant (maintainer-labeled)

**Repo:** `blader/humanizer` v2.9.0
**Maintainer note:** "Adds a hard no-fabrication rule... introduces pasted-text, file, and embedded invocation modes."
**Label:** RISK_RELEVANT
**Reasoning:** New behavior modes added (pasted-text, file, embedded invocation). New rule added (no-fabrication). These change what the skill asks the agent to do.

### Example 3: Risk-relevant (maintainer-labeled, security)

**Repo:** `AgriciDaniel/claude-seo` — "SSRF prevention: added private IP blocking"
**Label:** RISK_RELEVANT
**Reasoning:** New security behavior added (private IP blocking). Changes what the skill does at runtime.

### Example 4: Risk-relevant (permission scope change)

**Repo:** `AgriciDaniel/claude-seo` — "Removed Bash from seo-flow agent tool grant"
**Label:** RISK_RELEVANT
**Reasoning:** Tool grant scope changed (Bash removed). Even though this is a security fix, it changes what the skill can do.

### Example 5: Ambiguous — hard case

**Repo:** `AgriciDaniel/claude-seo` — "User-Agent header: changed default from bot-style ClaudeSEO/1.0 to Chrome-like string"
**Label:** RISK_RELEVANT (with note)
**Reasoning:** Changes how the tool presents itself to servers. Could be a compatibility fix (cosmetic) or an evasion-adjacent behavior change (risk-relevant). When in doubt, label risk-relevant and note the ambiguity.

### Example 6: Ambiguous — metadata drift

**Repo:** `AgriciDaniel/claude-seo` — issue #92, stale version metadata, drifted sub-skill counts, missing agent from list, over-claimed "author added" that verification showed was not.
**Label:** COSMETIC (with note)
**Reasoning:** Touches multiple files (frontmatter, README, version numbers) but no actual behavior change. Maintenance/bookkeeping fix.

### Example 7: Ambiguous — vague purpose, new tool added

**Scenario:** A skill's purpose statement says "I help with file operations." The new version adds a shell script that runs `rm -rf`.
**Label:** RISK_RELEVANT
**Reasoning:** The purpose statement is vague enough that you can't confirm the new behavior is "consistent" with it. When in doubt, label risk-relevant.

### Example 8: Ambiguous — tool removal under vague purpose

**Scenario:** A skill removes a tool (e.g., removes `write` from allowed-tools) but the purpose statement is vague.
**Label:** RISK_RELEVANT
**Reasoning:** Tool removal changes what the skill can do. Even if it's a security fix, it's a behavior change. Label risk-relevant.

## Inter-annotator agreement

If you and a second labeler disagree on a diff, discuss it and try to reach consensus. If you can't agree, note the disagreement and both labels — the disagreement itself is data about where the classification line is fuzzy.