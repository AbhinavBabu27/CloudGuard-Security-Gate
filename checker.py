#!/usr/bin/env python3
"""
CloudGuard - S3 Security Configuration Checker

Validates S3 bucket security configurations in Terraform plans.
"""

import sys
import json
from pathlib import Path
from datetime import datetime, timezone

from rules.public_access_block import check_public_access_block
from rules.encryption import check_encryption
from rules.https_policy import check_https_policy
from rules.retention import check_retention


def load_plan(plan_file):
    """
    Load and parse Terraform plan JSON.

    Args:
        plan_file: Path to plan JSON file

    Returns:
        Parsed plan dict or None if error
    """
    try:
        with open(plan_file, 'r') as f:
            plan = json.load(f)
        return plan
    except FileNotFoundError:
        print(f"Error: Plan file not found: {plan_file}")
        sys.exit(3)
    except json.JSONDecodeError as e:
        print(f"Error: Plan file is not valid JSON: {e}")
        sys.exit(3)
    except Exception as e:
        print(f"Error reading plan file: {e}")
        sys.exit(3)


def extract_resources(plan):
    """
    Extract and organize resources from plan.

    Args:
        plan: Parsed Terraform plan

    Returns:
        dict mapping bucket names to their related resources
    """
    resources_by_bucket = {}
    resource_changes = plan.get("resource_changes", [])

    for change in resource_changes:
        resource_type = change.get("type")
        address = change.get("address", "")

        # Skip non-S3 resources
        if not resource_type or not resource_type.startswith("aws_s3_bucket"):
            continue

        # Extract bucket name from resource
        bucket_name = _extract_bucket_name(change)
        if not bucket_name:
            continue

        # Initialize bucket entry if needed
        if bucket_name not in resources_by_bucket:
            resources_by_bucket[bucket_name] = {
                "address": address,
                "aws_s3_bucket": None,
                "aws_s3_bucket_public_access_block": None,
                "aws_s3_bucket_server_side_encryption_configuration": None,
                "aws_s3_bucket_policy": None,
                "aws_s3_bucket_lifecycle_configuration": None,
            }

        # Store resource
        if resource_type == "aws_s3_bucket":
            resources_by_bucket[bucket_name]["aws_s3_bucket"] = change
        elif resource_type == "aws_s3_bucket_public_access_block":
            resources_by_bucket[bucket_name]["aws_s3_bucket_public_access_block"] = change
        elif resource_type == "aws_s3_bucket_server_side_encryption_configuration":
            resources_by_bucket[bucket_name]["aws_s3_bucket_server_side_encryption_configuration"] = change
        elif resource_type == "aws_s3_bucket_policy":
            resources_by_bucket[bucket_name]["aws_s3_bucket_policy"] = change
        elif resource_type == "aws_s3_bucket_lifecycle_configuration":
            resources_by_bucket[bucket_name]["aws_s3_bucket_lifecycle_configuration"] = change

    return resources_by_bucket


def _extract_bucket_name(resource_change):
    """
    Extract bucket name from a resource.

    For bucket resources, gets the name directly.
    For related resources, gets it from the 'bucket' attribute.
    """
    change = resource_change.get("change", {})
    after = change.get("after", {})

    # For aws_s3_bucket itself, the bucket name is the 'bucket' attribute
    if resource_change.get("type") == "aws_s3_bucket":
        return after.get("bucket")

    # For related resources, also look for 'bucket' attribute
    return after.get("bucket")


def evaluate_bucket(bucket_name, resources):
    """
    Evaluate all security checks for a bucket.

    Args:
        bucket_name: Name of the bucket
        resources: dict with bucket's S3 resources

    Returns:
        dict with check results, overall state, risk score, and deployment decision
    """
    results = {
        "bucket": bucket_name,
        "checks": {
            "public_access_block": None,
            "encryption": None,
            "https_policy": None,
            "retention": None,
        },
        "overall": None,
        "risk_score": None,
        "decision": None,
        "json_report": None,
    }

    # Run each check
    results["checks"]["public_access_block"] = check_public_access_block(
        bucket_name,
        resources["aws_s3_bucket_public_access_block"]
    )

    results["checks"]["encryption"] = check_encryption(
        bucket_name,
        resources["aws_s3_bucket_server_side_encryption_configuration"]
    )

    results["checks"]["https_policy"] = check_https_policy(
        bucket_name,
        resources["aws_s3_bucket_policy"]
    )

    results["checks"]["retention"] = check_retention(
        bucket_name,
        resources["aws_s3_bucket_lifecycle_configuration"]
    )

    # Aggregate overall result
    results["overall"] = aggregate_results(results["checks"])

    # Calculate risk score and deployment decision
    results["risk_score"] = calculate_risk_score(results["checks"])
    results["decision"] = determine_deployment_decision(results["checks"], results["risk_score"])
    results["json_report"] = generate_json_report(bucket_name, results["checks"], results["risk_score"], results["decision"])

    return results


def aggregate_results(checks):
    """
    Aggregate individual check results into overall state.

    Logic:
    - ERROR found → FAIL
    - FAIL found → FAIL
    - UNKNOWN found (no FAIL/ERROR) → UNKNOWN
    - All PASS → PASS
    """
    states = [check["state"] for check in checks.values()]

    if "ERROR" in states:
        return "FAIL"
    if "FAIL" in states:
        return "FAIL"
    if "UNKNOWN" in states:
        return "UNKNOWN"

    return "PASS"


def calculate_risk_score(checks):
    """
    Calculate risk score from check results.

    Scoring:
    - CRITICAL failure: 25 points
    - HIGH failure: 10 points
    - UNKNOWN: 5 points
    - Range: 0-100 (capped at 100)
    """
    score = 0
    for check in checks.values():
        if check["state"] == "FAIL":
            severity = check.get("severity", "MEDIUM")
            if severity == "CRITICAL":
                score += 25
            elif severity == "HIGH":
                score += 10
        elif check["state"] == "UNKNOWN":
            score += 5

    return min(score, 100)


def determine_deployment_decision(checks, risk_score):
    """
    Determine deployment decision based on failures and risk score.

    Returns:
    - "ALLOW" (exit 0): No CRITICAL failures, all checks PASS or HIGH warnings
    - "BLOCKED" (exit 1): CRITICAL failures present
    - "REVIEW" (exit 2): Only UNKNOWN values, no CRITICAL failures
    """
    has_critical_fail = any(
        c["state"] == "FAIL" and c.get("severity") == "CRITICAL"
        for c in checks.values()
    )
    has_high_fail = any(
        c["state"] == "FAIL" and c.get("severity") in ["HIGH", "MEDIUM", "LOW"]
        for c in checks.values()
    )
    has_unknown = any(c["state"] == "UNKNOWN" for c in checks.values())

    if has_critical_fail:
        return "BLOCKED"
    elif has_high_fail:
        return "REVIEW"
    elif has_unknown:
        return "REVIEW"
    else:
        return "ALLOW"


def generate_json_report(bucket_name, checks, risk_score, decision):
    """
    Generate structured JSON report for pipeline consumption.
    """
    issues = []
    for check_name, check_result in checks.items():
        if check_result["state"] != "PASS":
            issues.append({
                "check": check_name,
                "state": check_result["state"],
                "severity": check_result.get("severity"),
                "message": check_result.get("message"),
                "threat": check_result.get("threat"),
                "fix": check_result.get("fix")
            })

    exit_code = 0 if decision == "ALLOW" else (1 if decision == "BLOCKED" else 2)

    return {
        "bucket": bucket_name,
        "deployment_decision": decision,
        "risk_score": risk_score,
        "exit_code": exit_code,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "issues": issues
    }


def format_output(results_list):
    """
    Format results for human-readable display with Phase 1 enhancements.

    Args:
        results_list: List of bucket evaluation results

    Returns:
        Formatted string
    """
    output = []

    for result in results_list:
        bucket_name = result["bucket"]
        checks = result["checks"]
        overall = result["overall"]
        risk_score = result["risk_score"]
        decision = result["decision"]

        # Deployment decision header
        decision_symbol = "[ALLOW]" if decision == "ALLOW" else ("[REVIEW]" if decision == "REVIEW" else "[BLOCKED]")
        output.append("=" * 70)
        output.append(f"DEPLOYMENT DECISION: {decision_symbol} {decision}")
        output.append("=" * 70)
        output.append(f"Risk Score: {risk_score}/100")
        output.append("")

        # Group checks by severity
        critical_issues = []
        high_issues = []

        for check_name, check_result in checks.items():
            if check_result["state"] != "PASS":
                severity = check_result.get("severity", "LOW")
                if severity == "CRITICAL":
                    critical_issues.append((check_name, check_result))
                elif severity == "HIGH":
                    high_issues.append((check_name, check_result))

        # Display CRITICAL issues
        if critical_issues:
            output.append("CRITICAL Issues (Must fix before deploy):")
            for check_name, check in critical_issues:
                symbol = "[FAIL]" if check["state"] == "FAIL" else "[UNKNOWN]"
                display_name = check_name.replace("_", " ").title()
                output.append(f"  {symbol} {display_name}: {check['state']}")
                output.append(f"    Message: {check.get('message', 'No details')}")
                if check.get("threat"):
                    output.append(f"    Threat: {check['threat']}")
                if check.get("fix"):
                    output.append(f"    Fix:")
                    for line in check["fix"].split("\n"):
                        output.append(f"      {line}")
            output.append("")

        # Display HIGH issues
        if high_issues:
            output.append("HIGH Issues (Requires review):")
            for check_name, check in high_issues:
                symbol = "[FAIL]" if check["state"] == "FAIL" else "[UNKNOWN]"
                display_name = check_name.replace("_", " ").title()
                output.append(f"  {symbol} {display_name}: {check['state']}")
                output.append(f"    Message: {check.get('message', 'No details')}")
                if check.get("threat"):
                    output.append(f"    Threat: {check['threat']}")
                if check.get("fix"):
                    output.append(f"    Fix:")
                    for line in check["fix"].split("\n"):
                        output.append(f"      {line}")
            output.append("")

        # If no issues, show all pass
        if not critical_issues and not high_issues:
            output.append("[OK] All security checks passed - Ready to deploy!")
            output.append("")

    # Summary
    if results_list:
        output.append("=" * 70)
        output.append("SUMMARY")
        output.append("=" * 70)
        for result in results_list:
            output.append(f"  {result['bucket']}: {result['decision']}")

    return "\n".join(output)


def determine_exit_code(results_list):
    """
    Determine exit code based on deployment decisions.

    0: All resources decision=ALLOW
    1: At least one resource decision=BLOCKED
    2: At least one resource decision=REVIEW (no BLOCKED)
    3: Error (already handled, shouldn't reach here)
    """
    decisions = [r.get("decision", "ALLOW") for r in results_list]

    if "BLOCKED" in decisions:
        return 1
    if "REVIEW" in decisions:
        return 2

    return 0


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python checker.py <plan.json> [--json]")
        print("Example: python checker.py fixtures/plan_compliant.json")
        print("Example: python checker.py fixtures/plan_compliant.json --json")
        sys.exit(3)

    plan_file = sys.argv[1]
    json_output = "--json" in sys.argv

    # Load plan
    plan = load_plan(plan_file)

    # Extract resources
    resources_by_bucket = extract_resources(plan)

    if not resources_by_bucket:
        print("No S3 buckets found in plan")
        sys.exit(0)

    # Evaluate each bucket
    results = []
    for bucket_name, resources in resources_by_bucket.items():
        bucket_result = evaluate_bucket(bucket_name, resources)
        results.append(bucket_result)

    # Output
    if json_output:
        # JSON output for pipeline consumption
        json_reports = [r["json_report"] for r in results]
        print(json.dumps(json_reports, indent=2))
    else:
        # Human-readable output
        output = format_output(results)
        print(output)

    # Exit with appropriate code
    exit_code = determine_exit_code(results)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
