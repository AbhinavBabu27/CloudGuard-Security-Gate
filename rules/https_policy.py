"""
HTTPS-Only Policy security check.

Validates that aws_s3_bucket_policy enforces HTTPS-only access via a Deny
statement with aws:SecureTransport condition set to false.
"""

import json


def check_https_policy(bucket_name, policy_resource):
    """
    Evaluate HTTPS-only enforcement in bucket policy.

    Args:
        bucket_name: Name of the S3 bucket
        policy_resource: The aws_s3_bucket_policy resource (or None if missing)

    Returns:
        dict with keys:
            - state: "PASS" | "FAIL" | "UNKNOWN" | "ERROR"
            - message: explanation
            - severity: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW"
            - threat: description of the risk
            - fix: Terraform code snippet to remediate
    """
    if policy_resource is None:
        return {
            "state": "FAIL",
            "message": "No bucket policy configured",
            "severity": "CRITICAL",
            "threat": "Data interception in transit",
            "fix": _get_policy_fix(bucket_name)
        }

    change = policy_resource.get("change", {})
    after = change.get("after", {})

    if not after:
        return {
            "state": "FAIL",
            "message": "Policy configuration is empty",
            "severity": "CRITICAL",
            "threat": "Data interception in transit",
            "fix": _get_policy_fix(bucket_name)
        }

    policy_str = after.get("policy")

    # Check if policy is unknown (computed)
    after_unknown = change.get("after_unknown", {})
    if after_unknown and after_unknown.get("policy") is True:
        return {
            "state": "UNKNOWN",
            "message": "Policy is unknown (computed at apply time)",
            "severity": "MEDIUM",
            "threat": "Cannot verify HTTPS-only policy",
            "fix": "Re-run check after terraform apply"
        }

    if not policy_str:
        return {
            "state": "FAIL",
            "message": "Policy is empty or not defined",
            "severity": "CRITICAL",
            "threat": "Data interception in transit",
            "fix": _get_policy_fix(bucket_name)
        }

    # Parse policy JSON
    try:
        policy_obj = json.loads(policy_str)
    except json.JSONDecodeError as e:
        return {
            "state": "ERROR",
            "message": f"Policy is not valid JSON: {str(e)}",
            "severity": "CRITICAL",
            "threat": "Data interception in transit",
            "fix": _get_policy_fix(bucket_name)
        }

    # Validate policy structure
    if not isinstance(policy_obj, dict):
        return {
            "state": "ERROR",
            "message": "Policy is not a valid JSON object",
            "severity": "CRITICAL",
            "threat": "Data interception in transit",
            "fix": _get_policy_fix(bucket_name)
        }

    if "Statement" not in policy_obj:
        return {
            "state": "ERROR",
            "message": "Policy missing 'Statement' key",
            "severity": "CRITICAL",
            "threat": "Data interception in transit",
            "fix": _get_policy_fix(bucket_name)
        }

    statements = policy_obj["Statement"]
    if not isinstance(statements, list):
        return {
            "state": "ERROR",
            "message": "Policy 'Statement' must be an array",
            "severity": "CRITICAL",
            "threat": "Data interception in transit",
            "fix": _get_policy_fix(bucket_name)
        }

    if len(statements) == 0:
        return {
            "state": "FAIL",
            "message": "Policy has no statements",
            "severity": "CRITICAL",
            "threat": "Data interception in transit",
            "fix": _get_policy_fix(bucket_name)
        }

    # Look for Deny statement with SecureTransport condition
    result = _find_https_deny_statement(statements, bucket_name)
    return result


def _get_policy_fix(bucket_name):
    """Return the policy fix snippet."""
    return f"""resource "aws_s3_bucket_policy" "{bucket_name}" {{
  bucket = aws_s3_bucket.{bucket_name}.id

  policy = jsonencode({{
    Statement = [{{
      Effect = "Deny"
      Principal = "*"
      Action = "s3:*"
      Resource = [
        "arn:aws:s3:::{bucket_name}",
        "arn:aws:s3:::{bucket_name}/*"
      ]
      Condition = {{
        Bool = {{
          "aws:SecureTransport" = "false"
        }}
      }}
    }}]
  }})
}}"""


def _find_https_deny_statement(statements, bucket_name):
    """
    Search statements for a Deny with aws:SecureTransport: false condition.

    Returns:
        dict with state and message
    """
    for stmt in statements:
        if not isinstance(stmt, dict):
            continue

        # Check if this is a Deny statement
        if stmt.get("Effect") != "Deny":
            continue

        # Check for the SecureTransport condition
        conditions = stmt.get("Condition", {})
        if not isinstance(conditions, dict):
            continue

        bool_conditions = conditions.get("Bool", {})
        if not isinstance(bool_conditions, dict):
            continue

        secure_transport = bool_conditions.get("aws:SecureTransport")

        # We need it to be "false" (blocks unencrypted access)
        if secure_transport == "false":
            # Verify resource coverage
            resources = stmt.get("Resource", [])
            if isinstance(resources, str):
                resources = [resources]

            if not isinstance(resources, list):
                continue

            # Check if resources cover the bucket and its objects
            bucket_arn = f"arn:aws:s3:::{bucket_name}"
            objects_arn = f"arn:aws:s3:::{bucket_name}/*"

            resource_strs = [str(r) for r in resources]
            has_bucket = any(bucket_arn in r for r in resource_strs)
            has_objects = any(f"{bucket_name}/*" in r for r in resource_strs)

            if has_bucket and has_objects:
                return {
                    "state": "PASS",
                    "message": "HTTPS-only policy enforced (Deny non-HTTPS requests)",
                    "severity": "CRITICAL",
                    "threat": None,
                    "fix": None
                }
            else:
                return {
                    "state": "FAIL",
                    "message": "Deny statement found but resource coverage incomplete",
                    "severity": "CRITICAL",
                    "threat": "Data interception in transit",
                    "fix": _get_policy_fix(bucket_name)
                }

        elif secure_transport is not None and secure_transport != "false":
            return {
                "state": "FAIL",
                "message": f"SecureTransport condition set to '{secure_transport}', not 'false'",
                "severity": "CRITICAL",
                "threat": "Data interception in transit",
                "fix": _get_policy_fix(bucket_name)
            }

    # No matching Deny + SecureTransport statement found
    return {
        "state": "FAIL",
        "message": "No HTTPS-only policy found (Deny with aws:SecureTransport: false required)",
        "severity": "CRITICAL",
        "threat": "Data interception in transit",
        "fix": _get_policy_fix(bucket_name)
    }
