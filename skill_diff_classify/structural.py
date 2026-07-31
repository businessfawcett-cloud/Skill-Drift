import difflib
import os
import re


FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def find_skill_files(directory):
    results = {"skill_md": None, "scripts": [], "frontmatter": None}

    skill_md_path = os.path.join(directory, "SKILL.md")
    if os.path.isfile(skill_md_path):
        results["skill_md"] = skill_md_path
        with open(skill_md_path, "r") as f:
            content = f.read()
        match = FRONTMATTER_RE.match(content)
        if match:
            results["frontmatter"] = match.group(1)

    script_exts = (".py", ".js", ".ts", ".sh", ".bash")
    for root, _dirs, files in os.walk(directory):
        for fname in files:
            if any(fname.endswith(ext) for ext in script_exts):
                results["scripts"].append(os.path.join(root, fname))

    return results


def diff_frontmatter(old_frontmatter, new_frontmatter):
    if old_frontmatter is None and new_frontmatter is None:
        return []
    if old_frontmatter is None:
        return ["Frontmatter added in new version"]
    if new_frontmatter is None:
        return ["Frontmatter removed in new version"]

    old_lines = old_frontmatter.splitlines()
    new_lines = new_frontmatter.splitlines()
    diff = list(difflib.unified_diff(old_lines, new_lines, lineterm=""))

    findings = []
    for line in diff:
        if line.startswith("+") and not line.startswith("+++"):
            findings.append(f"Added: {line[1:].strip()}")
        elif line.startswith("-") and not line.startswith("---"):
            findings.append(f"Removed: {line[1:].strip()}")

    return findings


def diff_scripts(old_scripts, new_scripts):
    findings = []

    old_by_name = {}
    for path in old_scripts:
        old_by_name[os.path.basename(path)] = path

    new_by_name = {}
    for path in new_scripts:
        new_by_name[os.path.basename(path)] = path

    old_names = set(old_by_name.keys())
    new_names = set(new_by_name.keys())

    for name in sorted(new_names - old_names):
        findings.append(f"Script added: {name}")
    for name in sorted(old_names - new_names):
        findings.append(f"Script removed: {name}")

    for name in sorted(old_names & new_names):
        with open(old_by_name[name], "r") as f:
            old_content = f.read()
        with open(new_by_name[name], "r") as f:
            new_content = f.read()
        if old_content != new_content:
            diff_lines = list(difflib.unified_diff(
                old_content.splitlines(),
                new_content.splitlines(),
                fromfile=f"old/{name}",
                tofile=f"new/{name}",
                lineterm="",
            ))
            changed = [l for l in diff_lines if l.startswith("+") or l.startswith("-")]
            if changed:
                findings.append(f"Script changed: {name} ({len(changed)} lines)")

    return findings


def run_structural_pass(old_dir, new_dir):
    old_files = find_skill_files(old_dir)
    new_files = find_skill_files(new_dir)

    findings = []
    undeterminable = False

    fm_diff = diff_frontmatter(old_files["frontmatter"], new_files["frontmatter"])
    findings.extend(fm_diff)

    if old_files["skill_md"] is None and new_files["skill_md"] is None:
        undeterminable = True
    elif old_files["skill_md"] is None or new_files["skill_md"] is None:
        findings.append("SKILL.md added or removed")
        undeterminable = True

    script_diff = diff_scripts(old_files["scripts"], new_files["scripts"])
    findings.extend(script_diff)

    return {"findings": findings, "undeterminable": undeterminable}