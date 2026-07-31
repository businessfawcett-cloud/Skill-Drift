# Skill-Drift

Classify diffs between versions of AI agent skills as **cosmetic** or **risk-relevant**.

## What it does

Agent skills change over time — new capabilities get added, permissions shift, instructions are rewritten. `skill-diff-classify` reads two versions of a skill and tells you whether the change is safe (cosmetic) or needs a human look (risk-relevant).

This fills a gap in the ecosystem: existing tools flag *that* something changed, but not *whether the change matters*.

## Install

```bash
pip install skill-drift
```

## Usage

```bash
skill-diff-classify <old-skill-dir> <new-skill-dir>
```

Example:

```bash
skill-diff-classify ./skills/v1 ./skills/v2
```

For machine-readable output:

```bash
skill-diff-classify --json ./skills/v1 ./skills/v2
```

## How it works

1. **Structural pass** — diffs frontmatter (`allowed-tools`, permissions) and bundled scripts (Python, JS/TS, shell). Flags when declarations change.
2. **Semantic pass** — sends the diff to an LLM (provider selected via env var, matching SkillSpector's pattern) and asks whether the prose instructions changed behavior.
3. **Output** — `COSMETIC`, `RISK_RELEVANT`, or `UNDETERMINABLE` (when neither pass can decide).

## LLM provider setup

Set `SKILLSPECTOR_PROVIDER` to select a provider, or set the provider's
credential env var directly:

| Provider | Env var / credential |
|---|---|
| Anthropic | `SKILLSPECTOR_PROVIDER=anthropic` + `ANTHROPIC_API_KEY` |
| OpenAI | `SKILLSPECTOR_PROVIDER=openai` + `OPENAI_API_KEY` |
| AWS Bedrock | `SKILLSPECTOR_PROVIDER=bedrock` + `AWS_REGION` |

The tool uses the provider's CLI or API — no additional SDK installs required.
If `SKILLSPECTOR_PROVIDER` is unset, the tool infers the provider from the
credential env vars present.

## Limitations (v0.1)

- No local/rule-based fallback — requires an LLM provider to be configured.
- No fetching; both skill directories must be available locally.
- Bundled script diff is text-level, not AST-level for v0.1.
- Binary files, Dockerfiles, and Makefiles are detected and flagged as
  undeterminable rather than silently ignored.
- Runtime-templated skills (detected via build scripts or template engine
  config files) are flagged as undeterminable.
- Only `SKILL.md` and bundled scripts are analyzed; supporting files are
  ignored for classification purposes.

## Phase 0

This project is in Phase 0: validating that the cosmetic/risk-relevant classification line is sharp enough for humans to agree on. If you're interested in helping hand-label diffs, see `PHASE0.md`.

## License

MIT
