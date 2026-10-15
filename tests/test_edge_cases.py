"""
Tests for edge cases and overall checker behavior.
"""

import json
import pytest
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from checker import extract_resources, evaluate_bucket, aggregate_results


def test_multiple_buckets_in_plan():
    """Plan with multiple buckets should evaluate each independently."""
    plan = {
        "resource_changes": [
            {
                "address": "aws_s3_bucket.bucket1",
                "type": "aws_s3_bucket",
                "change": {
                    "actions": ["create"],
                    "after": {"bucket": "bucket1"}
                }
            },
            {
                "address": "aws_s3_bucket.bucket2",
                "type": "aws_s3_bucket",
                "change": {
                    "actions": ["create"],
                    "after": {"bucket": "bucket2"}
                }
            }
        ]
    }

    resources = extract_resources(plan)

    assert len(resources) == 2
    assert "bucket1" in resources
    assert "bucket2" in resources


def test_non_s3_resources_ignored():
    """Non-S3 resources should be ignored."""
    plan = {
        "resource_changes": [
            {
                "address": "aws_dynamodb_table.example",
                "type": "aws_dynamodb_table",
                "change": {
                    "actions": ["create"],
                    "after": {"name": "example"}
                }
            },
            {
                "address": "aws_s3_bucket.bucket",
                "type": "aws_s3_bucket",
                "change": {
                    "actions": ["create"],
                    "after": {"bucket": "bucket"}
                }
            }
        ]
    }

    resources = extract_resources(plan)

    assert len(resources) == 1
    assert "bucket" in resources


def test_empty_plan():
    """Empty plan should return empty resources."""
    plan = {"resource_changes": []}

    resources = extract_resources(plan)

    assert len(resources) == 0


def test_result_aggregation_error():
    """ERROR in any check should result in overall FAIL."""
    checks = {
        "public_access_block": {"state": "PASS", "message": ""},
        "encryption": {"state": "ERROR", "message": ""},
        "https_policy": {"state": "PASS", "message": ""},
        "retention": {"state": "PASS", "message": ""}
    }

    overall = aggregate_results(checks)

    assert overall == "FAIL"


def test_result_aggregation_fail():
    """FAIL in any check should result in overall FAIL."""
    checks = {
        "public_access_block": {"state": "FAIL", "message": ""},
        "encryption": {"state": "PASS", "message": ""},
        "https_policy": {"state": "PASS", "message": ""},
        "retention": {"state": "PASS", "message": ""}
    }

    overall = aggregate_results(checks)

    assert overall == "FAIL"


def test_result_aggregation_unknown():
    """UNKNOWN (with no FAIL/ERROR) should result in overall UNKNOWN."""
    checks = {
        "public_access_block": {"state": "PASS", "message": ""},
        "encryption": {"state": "UNKNOWN", "message": ""},
        "https_policy": {"state": "PASS", "message": ""},
        "retention": {"state": "PASS", "message": ""}
    }

    overall = aggregate_results(checks)

    assert overall == "UNKNOWN"


def test_result_aggregation_all_pass():
    """All PASS should result in overall PASS."""
    checks = {
        "public_access_block": {"state": "PASS", "message": ""},
        "encryption": {"state": "PASS", "message": ""},
        "https_policy": {"state": "PASS", "message": ""},
        "retention": {"state": "PASS", "message": ""}
    }

    overall = aggregate_results(checks)

    assert overall == "PASS"


def test_result_aggregation_fail_beats_unknown():
    """FAIL should take precedence over UNKNOWN."""
    checks = {
        "public_access_block": {"state": "FAIL", "message": ""},
        "encryption": {"state": "UNKNOWN", "message": ""},
        "https_policy": {"state": "PASS", "message": ""},
        "retention": {"state": "PASS", "message": ""}
    }

    overall = aggregate_results(checks)

    assert overall == "FAIL"


def test_result_aggregation_error_beats_unknown():
    """ERROR should result in FAIL, taking precedence over UNKNOWN."""
    checks = {
        "public_access_block": {"state": "ERROR", "message": ""},
        "encryption": {"state": "UNKNOWN", "message": ""},
        "https_policy": {"state": "PASS", "message": ""},
        "retention": {"state": "PASS", "message": ""}
    }

    overall = aggregate_results(checks)

    assert overall == "FAIL"


def test_resource_linking_by_bucket_name():
    """Resources should be linked by bucket name."""
    plan = {
        "resource_changes": [
            {
                "address": "aws_s3_bucket.test",
                "type": "aws_s3_bucket",
                "change": {
                    "actions": ["create"],
                    "after": {"bucket": "my-bucket"}
                }
            },
            {
                "address": "aws_s3_bucket_public_access_block.test",
                "type": "aws_s3_bucket_public_access_block",
                "change": {
                    "actions": ["create"],
                    "after": {"bucket": "my-bucket"}
                }
            }
        ]
    }

    resources = extract_resources(plan)

    assert "my-bucket" in resources
    assert resources["my-bucket"]["aws_s3_bucket"] is not None
    assert resources["my-bucket"]["aws_s3_bucket_public_access_block"] is not None


def test_unchanged_resource_still_evaluated():
    """Unchanged resources should still be evaluated."""
    plan = {
        "resource_changes": [
            {
                "address": "aws_s3_bucket.test",
                "type": "aws_s3_bucket",
                "change": {
                    "actions": ["no-op"],  # Unchanged
                    "before": {"bucket": "my-bucket"},
                    "after": {"bucket": "my-bucket"}
                }
            }
        ]
    }

    resources = extract_resources(plan)

    assert "my-bucket" in resources
    assert resources["my-bucket"]["aws_s3_bucket"] is not None


def test_resource_with_no_bucket_attribute():
    """Resources without bucket attribute should not crash."""
    plan = {
        "resource_changes": [
            {
                "address": "aws_s3_bucket.test",
                "type": "aws_s3_bucket",
                "change": {
                    "actions": ["create"],
                    "after": {}  # No bucket attribute
                }
            }
        ]
    }

    resources = extract_resources(plan)

    # Should gracefully handle missing bucket attribute
    assert len(resources) == 0 or None not in resources


def test_policy_with_string_resource_not_array():
    """Policy with Resource as string (not array) should be handled."""
    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Deny",
                "Principal": "*",
                "Action": "s3:*",
                "Resource": "arn:aws:s3:::test-bucket/*",  # String, not array
                "Condition": {
                    "Bool": {
                        "aws:SecureTransport": "false"
                    }
                }
            }
        ]
    }

    from rules.https_policy import check_https_policy

    resource = {
        "change": {
            "after": {
                "bucket": "test-bucket",
                "policy": json.dumps(policy)
            },
            "after_unknown": {}
        }
    }

    result = check_https_policy("test-bucket", resource)

    # Should handle string resource gracefully
    assert result["state"] in ["PASS", "FAIL"]
