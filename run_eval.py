"""
Phase 0 eval harness.

Reads manifest.csv (the candidate diff pool) joined against phase0_labels.csv
(real human labels — must be filled in separately, never fabricated here),
checks out each old/new ref pair from a local clone of the source repo,
runs the classifier, and reports:

  - Primary metric: recall on risk_relevant (of everything humans labeled
    risk_relevant, what fraction did the classifier catch)
  - Secondary metric: precision on cosmetic (of everything the classifier
    called cosmetic, what fraction did humans agree was cosmetic)
  - Human-vs-human inter-annotator agreement, where two human labels exist
  - Confusion matrix and per-diff mismatch detail, so failures are inspectable
    rather than hidden behind an aggregate number

This harness does NOT fabricate labels. If phase0_labels.csv has no rows
(or a row has no human_label_1), that diff is skipped and reported as
"unlabeled" rather than silently excluded — the report should make it
obvious how much of the manifest actually has real ground truth.

Requires: repos cloned locally (see clone_repos.sh), and an LLM provider
configured per README.md (SKILLSPECTOR_PROVIDER or a credential env var) —
without one, semantic.call_llm will raise, and this script will report the
diff as an error rather than guessing.
"""

import argparse
import csv
import os
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from skill_diff_classify.classifier import classify  # noqa: E402

REPO_CLONE_ROOT = os.environ.get("SKILLDRIFT_REPO_ROOT", os.path.expanduser("~/skilldrift_repos"))


def load_csv(path):
    if not os.path.isfile(path):
        return []
    with open(path, newline="") as f:
        rows = [r for r in csv.DictReader(f) if r.get("id") and not r["id"].startswith("#")]
    return rows


def checkout_ref(repo_dir, ref, dest_dir):
    subprocess.run(["git", "-C", repo_dir, "worktree", "add", "--detach", dest_dir, ref],
                    check=True, capture_output=True, text=True)


def cleanup_worktree(repo_dir, dest_dir):
    subprocess.run(["git", "-C", repo_dir, "worktree", "remove", "--force", dest_dir],
                    capture_output=True, text=True)
    shutil.rmtree(dest_dir, ignore_errors=True)


def run_one(row, dry_run=False):
    repo_dir = os.path.join(REPO_CLONE_ROOT, row["repo"])
    if not os.path.isdir(repo_dir):
        return {"id": row["id"], "error": f"repo not cloned at {repo_dir}"}

    with tempfile.TemporaryDirectory() as tmp:
        old_dir = os.path.join(tmp, "old")
        new_dir = os.path.join(tmp, "new")
        try:
            checkout_ref(repo_dir, row["old_ref"], old_dir)
            checkout_ref(repo_dir, row["new_ref"], new_dir)
        except subprocess.CalledProcessError as e:
            return {"id": row["id"], "error": f"checkout failed: {e.stderr.strip()}"}

        try:
            if dry_run:
                result = {"tier": None, "rationale": "(dry run — classifier not invoked)",
                          "undeterminable": None, "structural_findings": []}
            else:
                result = classify(old_dir, new_dir)
        except Exception as e:  # noqa: BLE001 — surface any provider/parse error per-diff, don't crash the run
            result = {"error": str(e)}
        finally:
            cleanup_worktree(repo_dir, old_dir)
            cleanup_worktree(repo_dir, new_dir)

    result["id"] = row["id"]
    return result


def agreement(a, b):
    if not a or not b:
        return None
    return a == b


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default=os.path.join(os.path.dirname(__file__), "manifest.csv"))
    ap.add_argument("--labels", default=os.path.join(os.path.dirname(__file__), "phase0_labels.csv"))
    ap.add_argument("--dry-run", action="store_true",
                     help="Skip actual LLM calls; validates checkout/plumbing only.")
    args = ap.parse_args()

    manifest = {r["id"]: r for r in load_csv(args.manifest)}
    labels = {r["id"]: r for r in load_csv(args.labels)}

    if not labels:
        print("No labeled data found in phase0_labels.csv — nothing to evaluate.")
        print(f"Manifest has {len(manifest)} candidate diffs waiting on real human labels.")
        return

    rows = []
    for diff_id, m in manifest.items():
        lab = labels.get(diff_id, {})
        h1 = lab.get("human_label_1", "").strip() or None
        h2 = lab.get("human_label_2", "").strip() or None
        rows.append({"id": diff_id, "manifest": m, "human_1": h1, "human_2": h2})

    unlabeled = [r for r in rows if not r["human_1"]]
    labeled = [r for r in rows if r["human_1"]]

    print(f"Manifest: {len(rows)} diffs | Labeled (human_1 present): {len(labeled)} | Unlabeled: {len(unlabeled)}")
    if unlabeled:
        print(f"  Unlabeled ids: {', '.join(r['id'] for r in unlabeled)}")

    both_labeled = [r for r in labeled if r["human_2"]]
    if both_labeled:
        agree_count = sum(1 for r in both_labeled if agreement(r["human_1"], r["human_2"]))
        print(f"\nHuman-vs-human agreement: {agree_count}/{len(both_labeled)} "
              f"({100 * agree_count / len(both_labeled):.0f}%)")
        disagreements = [r["id"] for r in both_labeled if agreement(r["human_1"], r["human_2"]) is False]
        if disagreements:
            print(f"  Disagreements: {', '.join(disagreements)}")
    else:
        print("\nNo diffs have both human_label_1 and human_label_2 — "
              "inter-annotator agreement cannot be computed yet.")

    if not labeled:
        return

    print(f"\nRunning classifier on {len(labeled)} labeled diffs"
          f"{' (DRY RUN — no LLM calls)' if args.dry_run else ''}...")

    results = []
    for r in labeled:
        out = run_one(r["manifest"], dry_run=args.dry_run)
        out["human_1"] = r["human_1"]
        results.append(out)
        status = out.get("error", out.get("tier"))
        print(f"  {r['id']}: human={r['human_1']} classifier={status}")

    if args.dry_run:
        print("\nDry run complete — plumbing validated. Re-run without --dry-run "
              "once an LLM provider is configured to get real metrics.")
        return

    errored = [r for r in results if "error" in r]
    scored = [r for r in results if "error" not in r and r["tier"] is not None]

    tp = sum(1 for r in scored if r["human_1"] == "risk_relevant" and r["tier"] == "risk_relevant")
    fn = sum(1 for r in scored if r["human_1"] == "risk_relevant" and r["tier"] != "risk_relevant")
    tn = sum(1 for r in scored if r["human_1"] == "cosmetic" and r["tier"] == "cosmetic")
    fp = sum(1 for r in scored if r["human_1"] == "cosmetic" and r["tier"] != "cosmetic")

    recall_risk = tp / (tp + fn) if (tp + fn) else None
    precision_cosmetic = tn / (tn + fp) if (tn + fp) else None
    undeterminable_count = sum(1 for r in results if r.get("undeterminable"))

    print("\n--- Results ---")
    print(f"Scored: {len(scored)} | Errored: {len(errored)} | Undeterminable: {undeterminable_count}")
    print(f"Recall on risk_relevant (PRIMARY metric):  "
          f"{f'{recall_risk:.0%}' if recall_risk is not None else 'n/a'}  (tp={tp}, fn={fn})")
    print(f"Precision on cosmetic (secondary metric):  "
          f"{f'{precision_cosmetic:.0%}' if precision_cosmetic is not None else 'n/a'}  (tn={tn}, fp={fp})")

    missed_risk = [r["id"] for r in scored if r["human_1"] == "risk_relevant" and r["tier"] != "risk_relevant"]
    if missed_risk:
        print(f"\nMissed risk-relevant diffs (the costly failure mode): {', '.join(missed_risk)}")
    if errored:
        print(f"\nErrored diffs (see stderr detail per-run): {', '.join(r['id'] for r in errored)}")

    print("\nCaveat per SPEC_v3 §6: this labeled set doubles as design-input and eval set. "
          "Treat these numbers as optimistic, not final.")


if __name__ == "__main__":
    main()