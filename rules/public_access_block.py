"""
Public Access Block security check.

Validates that aws_s3_bucket_public_access_block is configured with all
four blocking settings enabled.
"""


def check_public_access_block(bucket_name, pab_resource):
    """
    Evaluate Public Access Block configuration.

    Args:
        bucket_name: Name of the S3 bucket
        pab_resource: The aws_s3_bucket_public_access_block resource (or None if missing)

    Returns:
        dict with keys:
            - state: "PASS" | "FAIL" | "UNKNOWN" | "ERROR"
            - message: explanation
            - severity: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW"
            - threat: description of the risk
            - fix: Terraform code snippet to remediate
    """
    if pab_resource is None:
        return {
            "state": "FAIL",
            "message": "Public access block not configured",
            "severity": "CRITICAL",
            "threat": "Data exfiltration via public access",
            "fix": f"""resource "aws_s3_bucket_public_access_block" "{bucket_name}" {{
  bucket = aws_s3_bucket.{bucket_name}.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}}"""
        }

    change = pab_resource.get("change", {})
    after = change.get("after", {})

    if not after:
        return {
            "state": "FAIL",
            "message": "Public access block configuration is empty",
            "severity": "CRITICAL",
            "threat": "Data exfiltration via public access",
            "fix": f"""resource "aws_s3_bucket_public_access_block" "{bucket_name}" {{
  bucket = aws_s3_bucket.{bucket_name}.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}}"""
        }

    # Check if value is unknown
    after_unknown = change.get("after_unknown", {})
    if after_unknown:
        for key in ["block_public_acls", "block_public_policy", "ignore_public_acls", "restrict_public_buckets"]:
            if after_unknown.get(key) is True:
                return {
                    "state": "UNKNOWN",
                    "message": f"Public access block setting '{key}' is unknown (computed)",
                    "severity": "MEDIUM",
                    "threat": "Cannot verify public access block configuration",
                    "fix": "Re-run check after terraform apply"
                }

    # Validate all four blocks are enabled
    required_blocks = [
        "block_public_acls",
        "block_public_policy",
        "ignore_public_acls",
        "restrict_public_buckets"
    ]

    disabled_blocks = []
    for block in required_blocks:
        value = after.get(block)
        if value is None or value is False:
            disabled_blocks.append(block)

    if disabled_blocks:
        return {
            "state": "FAIL",
            "message": f"Public access block incomplete: {', '.join(disabled_blocks)} not enabled",
            "severity": "CRITICAL",
            "threat": "Data exfiltration via public access",
            "fix": f"""resource "aws_s3_bucket_public_access_block" "{bucket_name}" {{
  bucket = aws_s3_bucket.{bucket_name}.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}}"""
        }

    return {
        "state": "PASS",
        "message": "All public access blocks enabled",
        "severity": "CRITICAL",
        "threat": None,
        "fix": None
    }
