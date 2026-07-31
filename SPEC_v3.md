# Spec v3: Semantic Diff Classifier for Agent Skills

**Working name:** TBD
**Status:** Draft v3 — consolidated from decision log
**Author:** Parker

---

## 0. What changed from v2 (decision log)

| Decision | Rationale |
|---|---|
| Binary output only (`cosmetic` / `risk-relevant`), no third tier | "Superseded" (full rewrite) routes to `risk-relevant` by default — a total behavior change is trivially not cosmetic. A third tier can be promoted in v0.2 if Phase 0 labelers consistently flag binary forcing as wrong. |
| Maintainer-annotated and blind diff subsets reported separately | `blader/humanizer` has version notes that serve as free ground truth for annotated diffs, but those notes are self-selected for interesting changes, creating sample bias. Pooling them into one precision number would measure "classifier agrees with a maintainer who already flagged this as interesting" — a different and easier question than the real one. |
| Prompt lives in repo as `prompt.txt`, not embedded in spec | The prompt and the labeler guidelines should be built together; the spec references them, does not contain them. |
| `undeterminable` handled via existing `undeterminable: bool` field in JSON schema | When structural pass can't determine and semantic pass also can't decide, `tier` is `null` and the CLI outputs "could not classify — manual review needed." This is not a third tier — it's the tool admitting it doesn't know. |
| Recall on risk-relevant is the primary metric | Missing a risk-relevant diff is the costly error; over-flagging cosmetic is merely annoying. Secondary metric: precision on cosmetic (if terrible, the tool is useless as a filter regardless of recall). |
| Python implementation | Matches SkillSpector's ecosystem, matches the skill repos being studied, and AST/static-analysis tooling for Python/JS/shell is more mature there. |
| No fetching in v0.1 — two local directory paths only | `skill-diff-classify <old-path> <new-path>`. The user (or Phase 0 labeler) checks out both versions. Fetching is a provenance-layer concern, stays out. |
| Superseded/rewrite cases default to `risk-relevant` | A full-purpose rewrite is not cosmetic. It may or may not be risk-relevant in the same way an expansion is, but it's not a "no behavior change" case, so it's not cosmetic either. |

---

## 1. The one claim this project stakes itself on

Given two versions of a skill (old, new), correctly classify the diff into:

- **COSMETIC** — wording, formatting, typo fixes, no behavior change
- **RISK_RELEVANT** — any change that alters what the skill asks the agent to do, what it can access, or what it claims to do vs. what it now does

A full-purpose rewrite (same name/repo, different skill) routes to `risk-relevant` by default. Whether "supersession" deserves its own category is a question Phase 0 data can answer — not before.

---

## 2. Phase 0: validate the premise (before writing any classifier code)

### 2a. Hand-labeling

1. Pick 5–10 real skills from public repos with commit/version history.
2. Pull every update each has shipped between tagged releases (where they exist); where a skill has no clean releases, label between the two most recent commits that touch `SKILL.md` or bundled scripts — ignore commits that only touch README/CI/license.
3. Hand-label each diff as `cosmetic` or `risk_relevant`, with a one-line reason. Do this before building anything — this is also the eval set from §5.
4. Cross-check the maintainer-annotated subset against the maintainer's own version notes (e.g., `blader/humanizer`'s README version history). Treat agreement/disagreement as a real inter-annotator signal for that subset only.
5. For the blind subset (no maintainer notes), recruit a second labeler. Even a quick pass from one other person on 10 diffs provides the inter-annotator signal the eval plan requires. If no second labeler is available by Phase 0 start, drop the inter-annotator check from the eval plan rather than leave a metric you can't compute.

**Target:** ~30–50 labeled diffs minimum, from at least 5 distinct skills, before touching the classifier.

### 2b. Baseline measurement

Run `skilldrift` (as-is) against the same diffs if it can be installed standalone. Note what it flags. The baseline is not "skilldrift's classification accuracy" — skilldrift likely just flags "content changed." The baseline is: **of the changes skilldrift flags, what fraction are actually cosmetic?** This is the "always escalate" rate to beat.

### 2c. Candidate skills (initial)

- `blader/humanizer` — 43 commits, real version history, maintainer-written version notes in README, Python-based, ~32k stars. Strong candidate; version notes provide free cross-check signal.
- `AgriciDaniel/claude-seo` — commit history not yet pulled.
- `VibeWithClaude/Claude-Code-SEO-skills` — commit history not yet pulled.

### 2d. Phase 0 gate

Only if hand-labeling turns out to be genuinely hard to agree on (i.e., the cosmetic/risk-relevant line is fuzzy even for a human) does the entire premise need rethinking before Phase 1.

---

## 3. Classifier design

### 3a. Structural pass

- **Frontmatter diff:** did `allowed-tools` / declared permissions change? For skills without structured frontmatter, flag as "undeterminable structurally" and force the semantic pass to carry the full decision.
- **Bundled script diff:** for skills with scripts, diff at the language level (Python, JS/TS, shell). No exotic language support in v0.1.
- **Undeterminable signals:** binaries, Dockerfiles, Makefiles, and runtime-templated output are detected and flagged as `undeterminable: true` rather than silently ignored. A runtime-templated skill (detected via build scripts or template engine config files) is flagged as undeterminable because the installed output can't be reliably diffed from source.

### 3b. Semantic pass

- LLM-graded comparison of old vs. new prose instructions: does the new version ask the agent to do something materially different, access something new, or contradict its own declared purpose?
- Single call per diff for v0.1. If a diff is large enough to need chunking, surface that as a signal ("large instruction rewrite — manual review recommended") rather than solving it automatically.
- Provider: env-var selected matching SkillSpector's own pattern (Bedrock / Claude CLI / OpenAI). No local/rule-based fallback in v0.1 — stated limitation, not hidden.
- **Do not infer intent beyond what the diff shows.** If the skill's purpose statement is vague enough that you cannot tell whether a new capability is "consistent" with it, say that explicitly rather than guessing. This is a genuine hard case, not a gap to paper over.

### 3c. Prompt (v0 draft, lives in repo as `prompt.txt`)

```
You are comparing two versions of an AI agent skill (SKILL.md and any
bundled scripts). Given OLD and NEW content:

1. List concrete differences (added/removed/changed instructions,
   permissions, tool calls, external references).
2. For each difference, state whether it changes what the skill asks
   the agent to do, what the skill can access, or what the skill
   claims to do vs. what it now does.
3. Classify the overall diff as exactly one of:
   - COSMETIC: wording/formatting only, no behavior change
   - RISK_RELEVANT: any difference from step 2 is present
4. Give a one-paragraph rationale citing the specific difference(s)
   that drove the classification. If no differences from step 2
   exist, say so explicitly and classify COSMETIC.

Do not infer intent beyond what the diff shows. If the skill's
purpose statement is vague enough that you cannot tell whether a
new capability is "consistent" with it, say that explicitly rather
than guessing — this is a genuine hard case, not a gap to paper over.
```

### 3d. Output schema

```json
{
  "tier": "cosmetic" | "risk_relevant" | null,
  "rationale": "one-paragraph explanation",
  "structural_findings": ["list of structural pass results"],
  "undeterminable": false
}
```

When `undeterminable` is `true`, `tier` is `null` and the CLI outputs "could not classify — manual review needed."

No numeric confidence score in v0.1 — a plain-language rationale is more actionable than a number nobody's calibrated yet.

---

## 4. CLI interface

```
skill-diff-classify <old-path> <new-path>
```

- Two local directory paths (the skill's files, old and new). Not commits, not lock entries, not remote URLs.
- Output to terminal (human-readable by default, `--json` for machine-readable output matching the schema above).
- Exit code 0 for cosmetic, 1 for risk-relevant, 2 for undeterminable.

---

## 5. What ships in v0.1

- `skill-diff-classify` CLI (Python)
- Structural pass (frontmatter diff + bundled script diff for Python/JS/TS/shell)
- Semantic pass (LLM-graded, provider-agnostic via env vars)
- JSON output (`--json` flag)
- README with usage, setup (LLM provider env vars), and known limitations
- No provenance lock file, no scheduling, no GitHub Action, no Issue-filing, no SkillSpector integration, no consensus logic

---

## 6. Evaluation

- **Primary metric:** recall on the risk-relevant class — of everything actually risk-relevant in the Phase 0 hand-labeled set, what fraction does the classifier catch?
- **Secondary metric:** precision on the cosmetic class — of everything the classifier calls cosmetic, what fraction is actually cosmetic?
- **Baseline:** "always escalate" rate from Phase 0's skilldrift run — what fraction of skilldrift-flagged changes are actually cosmetic?
- **Inter-annotator check:** agreement between hand-labelers on the blind subset; agreement between hand-labels and maintainer notes on the annotated subset.
- **Caveat:** Phase 0's labeled set serves as both design-input and initial eval set. With 30–50 examples, early precision/recall numbers are optimistic. A genuine held-out test set is a v0.2 problem once N grows.

---

## 7. Explicitly out of scope for this project

- Multi-scanner consensus/arbitration
- Mutation-tested behavioral verification
- Provenance lock file / non-git install sources (npm/curl/zip)
- Scheduling, GitHub Action, Issue filing
- Scanner weighting by historical precision
- Git-aware fetching or commit-level invocation
- SARIF output
- Local/rule-based LLM fallback

---

## 8. Open questions / blockers before Phase 0 starts

| Item | Status |
|---|---|
| Second human labeler recruited | **Not done.** Required for inter-annotator check on blind subset. |
| Prompt finalization (this v0 draft is a starting point for discussion) | **Draft exists, not finalized.** |
| Labeler guidelines written | **Not done.** Should be built alongside the prompt (same edge cases go into both). |
| `AgriciDaniel/claude-seo` commit history pulled | **Not done.** |
| `VibeWithClaude/Claude-Code-SEO-skills` commit history pulled | **Not done.** |
| `skilldrift` source code reviewed (§7 from v2) | **Not done.** Blocks v0.2 design decision. |
| SkillSpector env var names verified (not assumed) | **Not done.** Need to check actual var names from `NVIDIA/SkillSpector`. |
| Repo name, license, org placement | **Deferred** — not blocking Phase 0, needed before release. |
| `blader/humanizer` commit logs pulled and confirmed as Phase 0 candidate | **Not done.** Humanizer alone is a strong signal but needs confirmation of enough substantive updates. |

---

## 9. Relationship to existing work

- `blader/humanizer`'s `AGENTS.md`/`WARP.md` already encodes the labeling discipline this classifier automates: maintainer-written version notes describe what changed and why. Phase 0 can leverage this as a cross-check signal, not as a replacement for human labeling.
- The structural pass reuses AST diffing patterns from standard supply-chain tooling (Python/JS/TS/shell).
- This project is a standalone OSS repo, not a component of rebuild-dossier or skilldrift — though the eventual v0.2 GitHub Action wrapper could reasonably reuse skilldrift's existing Action shape once the classifier is proven.
