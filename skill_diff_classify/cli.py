import argparse
import json
import sys

from skill_diff_classify.classifier import classify


def main():
    parser = argparse.ArgumentParser(
        description="Classify a diff between two versions of an agent skill as cosmetic or risk-relevant."
    )
    parser.add_argument("old_path", help="Path to the old version of the skill directory")
    parser.add_argument("new_path", help="Path to the new version of the skill directory")
    parser.add_argument("--json", action="store_true", help="Output result as JSON")
    args = parser.parse_args()

    result = classify(args.old_path, args.new_path)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        tier = result["tier"] or "UNDETERMINABLE"
        print(f"Classification: {tier}")
        print(f"Rationale: {result['rationale']}")
        if result.get("structural_findings"):
            print("Structural findings:")
            for finding in result["structural_findings"]:
                print(f"  - {finding}")
        if result.get("undeterminable"):
            print("Note: classification is undeterminable — manual review recommended.")

    if result["tier"] == "risk_relevant":
        sys.exit(1)
    elif result["tier"] is None:
        sys.exit(2)
    else:
        sys.exit(0)