import difflib
import os

from skill_diff_classify.structural import run_structural_pass
from skill_diff_classify.semantic import call_llm
from skill_diff_classify.prompt import get_prompt


def _read_dir_contents(directory):
    skill_md_path = os.path.join(directory, "SKILL.md")
    content = ""
    if os.path.isfile(skill_md_path):
        with open(skill_md_path, "r") as f:
            content = f.read()

    script_exts = (".py", ".js", ".ts", ".sh", ".bash")
    for root, _dirs, files in os.walk(directory):
        for fname in sorted(files):
            if any(fname.endswith(ext) for ext in script_exts):
                fpath = os.path.join(root, fname)
                with open(fpath, "r") as f:
                    content += f"\n--- {os.path.relpath(fpath, directory)} ---\n"
                    content += f.read()

    return content


def classify(old_dir, new_dir):
    old_content = _read_dir_contents(old_dir)
    new_content = _read_dir_contents(new_dir)

    structural = run_structural_pass(old_dir, new_dir)
    prompt_text = get_prompt(old_content, new_content)

    llm_result = call_llm(prompt_text)

    tier = llm_result["tier"]
    rationale = llm_result["rationale"]

    if structural["undeterminable"] and tier is None:
        tier = None
        rationale = "Could not classify — neither structural nor semantic pass produced a definitive result. Manual review recommended."

    if tier == "cosmetic" and structural["findings"]:
        has_permission_change = any(
            "tool" in f.lower() or "permission" in f.lower() or "allowed" in f.lower()
            for f in structural["findings"]
        )
        if has_permission_change:
            tier = "risk_relevant"
            rationale = (
                f"Structural pass detected permission/tool change: {'; '.join(structural['findings'])}. "
                f"Semantic pass classified as cosmetic but structural signals override."
            )

    return {
        "tier": tier,
        "rationale": rationale,
        "structural_findings": structural["findings"],
        "undeterminable": structural["undeterminable"] or (tier is None),
    }