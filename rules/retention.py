"""
30-Day Retention security check.

Validates that aws_s3_bucket_lifecycle_configuration has an enabled rule
that expires (deletes) objects within 30 days.
"""


def check_retention(bucket_name, lifecycle_resource):
    """
    Evaluate lifecycle retention configuration.

    Args:
        bucket_name: Name of the S3 bucket
        lifecycle_resource: The aws_s3_bucket_lifecycle_configuration resource (or None if missing)

    Returns:
        dict with keys:
            - state: "PASS" | "FAIL" | "UNKNOWN"
            - message: explanation
            - severity: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW"
            - threat: description of the risk
            - fix: Terraform code snippet to remediate
    """
    if lifecycle_resource is None:
        return {
            "state": "FAIL",
            "message": "Lifecycle configuration not configured",
            "severity": "HIGH",
            "threat": "Extended data exposure window",
            "fix": f"""resource "aws_s3_bucket_lifecycle_configuration" "{bucket_name}" {{
  bucket = aws_s3_bucket.{bucket_name}.id

  rule {{
    id     = "delete-after-30-days"
    status = "Enabled"

    expiration {{
      days = 30
    }}
  }}
}}"""
        }

    change = lifecycle_resource.get("change", {})
    after = change.get("after", {})

    if not after:
        return {
            "state": "FAIL",
            "message": "Lifecycle configuration is empty",
            "severity": "HIGH",
            "threat": "Extended data exposure window",
            "fix": f"""resource "aws_s3_bucket_lifecycle_configuration" "{bucket_name}" {{
  bucket = aws_s3_bucket.{bucket_name}.id

  rule {{
    id     = "delete-after-30-days"
    status = "Enabled"

    expiration {{
      days = 30
    }}
  }}
}}"""
        }

    rules = after.get("rule", [])
    if not rules or not isinstance(rules, list) or len(rules) == 0:
        return {
            "state": "FAIL",
            "message": "No lifecycle rules configured",
            "severity": "HIGH",
            "threat": "Extended data exposure window",
            "fix": f"""resource "aws_s3_bucket_lifecycle_configuration" "{bucket_name}" {{
  bucket = aws_s3_bucket.{bucket_name}.id

  rule {{
    id     = "delete-after-30-days"
    status = "Enabled"

    expiration {{
      days = 30
    }}
  }}
}}"""
        }

    # Find enabled rules with expiration
    after_unknown = change.get("after_unknown", {})

    for rule_index, rule in enumerate(rules):
        if not isinstance(rule, dict):
            continue

        # Check if rule is enabled
        status = rule.get("status")
        if status and status.upper() != "ENABLED":
            continue

        # Look for Expiration configuration
        expiration = rule.get("expiration")
        if not expiration or not isinstance(expiration, dict):
            continue

        days = expiration.get("days")

        # Check if days is unknown
        if after_unknown:
            rule_unknown = after_unknown.get("rule", [])
            if len(rule_unknown) > rule_index:
                rule_item = rule_unknown[rule_index]
                if isinstance(rule_item, dict):
                    exp_unknown = rule_item.get("expiration", {})
                    if isinstance(exp_unknown, dict) and exp_unknown.get("days") is True:
                        return {
                            "state": "UNKNOWN",
                            "message": "Expiration days value is unknown (computed)",
                            "severity": "MEDIUM",
                            "threat": "Cannot verify retention configuration",
                            "fix": "Re-run check after terraform apply"
                        }

        # Validate days value
        if days is None:
            continue

        try:
            days_int = int(days)
            if days_int <= 30:
                return {
                    "state": "PASS",
                    "message": f"Objects expire within 30 days ({days_int} days)",
                    "severity": "HIGH",
                    "threat": None,
                    "fix": None
                }
            else:
                return {
                    "state": "FAIL",
                    "message": f"Expiration exceeds 30 days ({days_int} days)",
                    "severity": "HIGH",
                    "threat": "Extended data exposure window",
                    "fix": f"""resource "aws_s3_bucket_lifecycle_configuration" "{bucket_name}" {{
  bucket = aws_s3_bucket.{bucket_name}.id

  rule {{
    id     = "delete-after-30-days"
    status = "Enabled"

    expiration {{
      days = 30
    }}
  }}
}}"""
                }
        except (ValueError, TypeError):
            continue

    # No enabled rule with valid expiration found
    return {
        "state": "FAIL",
        "message": "No enabled lifecycle rule with expiration ≤ 30 days found",
        "severity": "HIGH",
        "threat": "Extended data exposure window",
        "fix": f"""resource "aws_s3_bucket_lifecycle_configuration" "{bucket_name}" {{
  bucket = aws_s3_bucket.{bucket_name}.id

  rule {{
    id     = "delete-after-30-days"
    status = "Enabled"

    expiration {{
      days = 30
    }}
  }}
}}"""
    }
