import os
import subprocess
import json


def _detect_provider():
    provider = os.environ.get("SKILLSPECTOR_PROVIDER")
    if provider:
        return provider

    if os.environ.get("ANTHROPIC_API_KEY"):
        return "anthropic"
    if os.environ.get("OPENAI_API_KEY"):
        return "openai"
    if os.environ.get("AWS_REGION"):
        return "bedrock"
    return None


def _call_anthropic(prompt_text):
    result = subprocess.run(
        ["anthropic", "prompt", prompt_text],
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode != 0:
        raise RuntimeError(f"anthropic CLI failed: {result.stderr.strip()}")
    return result.stdout.strip()


def _call_openai(prompt_text):
    result = subprocess.run(
        ["openai", "api", "chat.completions.create", "--model", "gpt-4o-mini", "--messages", json.dumps([{"role": "user", "content": prompt_text}])],
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode != 0:
        raise RuntimeError(f"openai CLI failed: {result.stderr.strip()}")
    return result.stdout.strip()


def _call_bedrock(prompt_text):
    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 1024,
        "messages": [{"role": "user", "content": prompt_text}],
    })
    result = subprocess.run(
        ["aws", "bedrock", "invoke-model", "--model-id", "anthropic.claude-3-sonnet-20240229-v1:0", "--body", body],
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode != 0:
        raise RuntimeError(f"aws bedrock CLI failed: {result.stderr.strip()}")
    return result.stdout.strip()


def _parse_tier(response_text):
    text_upper = response_text.upper()
    if "COSMETIC" in text_upper and "RISK_RELEVANT" not in text_upper:
        return "cosmetic"
    if "RISK_RELEVANT" in text_upper:
        return "risk_relevant"
    return None


def _extract_rationale(response_text):
    lines = response_text.strip().splitlines()
    rationale_lines = []
    in_rationale = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("4.") or stripped.startswith("rationale") or "paragraph" in stripped.lower():
            in_rationale = True
            continue
        if in_rationale and stripped:
            rationale_lines.append(stripped)
    return " ".join(rationale_lines) if rationale_lines else response_text.strip()


def call_llm(prompt_text):
    provider = _detect_provider()
    if provider is None:
        raise RuntimeError(
            "No LLM provider configured. Set SKILLSPECTOR_PROVIDER (anthropic|openai|bedrock), "
            "or set ANTHROPIC_API_KEY, OPENAI_API_KEY, or AWS_REGION."
        )

    callers = {
        "anthropic": _call_anthropic,
        "openai": _call_openai,
        "bedrock": _call_bedrock,
    }

    if provider not in callers:
        raise RuntimeError(
            f"Provider '{provider}' is not supported in v0.1. "
            "Supported: anthropic, openai, bedrock."
        )

    response = callers[provider](prompt_text)
    tier = _parse_tier(response)
    rationale = _extract_rationale(response)

    return {"tier": tier, "rationale": rationale, "raw_response": response}