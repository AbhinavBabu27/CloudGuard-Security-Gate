"""
Encryption security check.

Validates that aws_s3_bucket_server_side_encryption_configuration is configured
with a valid encryption algorithm (AES256 or aws:kms).
"""


def check_encryption(bucket_name, encryption_resource):
    """
    Evaluate encryption configuration.

    Args:
        bucket_name: Name of the S3 bucket
        encryption_resource: The aws_s3_bucket_server_side_encryption_configuration resource (or None if missing)

    Returns:
        dict with keys:
            - state: "PASS" | "FAIL" | "UNKNOWN" | "ERROR"
            - message: explanation
            - severity: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW"
            - threat: description of the risk
            - fix: Terraform code snippet to remediate
    """
    if encryption_resource is None:
        return {
            "state": "FAIL",
            "message": "Encryption not configured",
            "severity": "HIGH",
            "threat": "Data exposure at rest",
            "fix": f"""resource "aws_s3_bucket_server_side_encryption_configuration" "{bucket_name}" {{
  bucket = aws_s3_bucket.{bucket_name}.id

  rule {{
    apply_server_side_encryption_by_default {{
      sse_algorithm = "AES256"
    }}
  }}
}}"""
        }

    change = encryption_resource.get("change", {})
    after = change.get("after", {})

    if not after:
        return {
            "state": "FAIL",
            "message": "Encryption configuration is empty",
            "severity": "HIGH",
            "threat": "Data exposure at rest",
            "fix": f"""resource "aws_s3_bucket_server_side_encryption_configuration" "{bucket_name}" {{
  bucket = aws_s3_bucket.{bucket_name}.id

  rule {{
    apply_server_side_encryption_by_default {{
      sse_algorithm = "AES256"
    }}
  }}
}}"""
        }

    # Extract rule array
    rules = after.get("rule", [])
    if not rules or not isinstance(rules, list) or len(rules) == 0:
        return {
            "state": "FAIL",
            "message": "No encryption rules configured",
            "severity": "HIGH",
            "threat": "Data exposure at rest",
            "fix": f"""resource "aws_s3_bucket_server_side_encryption_configuration" "{bucket_name}" {{
  bucket = aws_s3_bucket.{bucket_name}.id

  rule {{
    apply_server_side_encryption_by_default {{
      sse_algorithm = "AES256"
    }}
  }}
}}"""
        }

    # Check first rule (or any rule) for encryption algorithm
    for rule in rules:
        apply_default = rule.get("apply_server_side_encryption_by_default", {})

        # Check if algorithm is unknown
        after_unknown = change.get("after_unknown", {})
        if after_unknown:
            # Traverse nested structure to check if sse_algorithm is unknown
            if _is_algorithm_unknown(after_unknown, rules.index(rule)):
                return {
                    "state": "UNKNOWN",
                    "message": "Encryption algorithm is unknown (computed)",
                    "severity": "MEDIUM",
                    "threat": "Cannot verify encryption configuration",
                    "fix": "Re-run check after terraform apply"
                }

        sse_algorithm = apply_default.get("sse_algorithm")

        # Accept AES256 or aws:kms
        if sse_algorithm in ["AES256", "aws:kms"]:
            return {
                "state": "PASS",
                "message": f"Encryption configured with {sse_algorithm}",
                "severity": "HIGH",
                "threat": None,
                "fix": None
            }
        elif sse_algorithm is None:
            continue  # Check next rule
        else:
            return {
                "state": "FAIL",
                "message": f"Unknown encryption algorithm: {sse_algorithm}",
                "severity": "HIGH",
                "threat": "Data exposure at rest",
                "fix": f"""resource "aws_s3_bucket_server_side_encryption_configuration" "{bucket_name}" {{
  bucket = aws_s3_bucket.{bucket_name}.id

  rule {{
    apply_server_side_encryption_by_default {{
      sse_algorithm = "AES256"
    }}
  }}
}}"""
            }

    return {
        "state": "FAIL",
        "message": "No valid encryption algorithm specified",
        "severity": "HIGH",
        "threat": "Data exposure at rest",
        "fix": f"""resource "aws_s3_bucket_server_side_encryption_configuration" "{bucket_name}" {{
  bucket = aws_s3_bucket.{bucket_name}.id

  rule {{
    apply_server_side_encryption_by_default {{
      sse_algorithm = "AES256"
    }}
  }}
}}"""
    }


def _is_algorithm_unknown(after_unknown, rule_index):
    """Helper to check if sse_algorithm is marked unknown in the plan."""
    if not isinstance(after_unknown, dict):
        return False

    rule_unknown = after_unknown.get("rule")
    if rule_unknown and isinstance(rule_unknown, list) and len(rule_unknown) > rule_index:
        rule_item = rule_unknown[rule_index]
        if isinstance(rule_item, dict):
            apply_default = rule_item.get("apply_server_side_encryption_by_default", {})
            if isinstance(apply_default, dict):
                return apply_default.get("sse_algorithm") is True

    return False
