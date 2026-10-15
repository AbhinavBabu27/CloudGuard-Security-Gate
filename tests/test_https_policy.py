"""
Tests for HTTPS-Only Policy security check.
"""

import json
import pytest
from rules.https_policy import check_https_policy


def test_valid_https_policy():
    """Valid Deny with SecureTransport should PASS."""
    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Deny",
                "Principal": "*",
                "Action": "s3:*",
                "Resource": [
                    "arn:aws:s3:::test-bucket",
                    "arn:aws:s3:::test-bucket/*"
                ],
                "Condition": {
                    "Bool": {
                        "aws:SecureTransport": "false"
                    }
                }
            }
        ]
    }

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

    assert result["state"] == "PASS"
    assert "HTTPS-only" in result["message"]


def test_missing_policy_resource():
    """Missing policy resource should FAIL."""
    result = check_https_policy("test-bucket", None)

    assert result["state"] == "FAIL"
    assert "not configured" in result["message"]


def test_policy_string_is_empty():
    """Empty policy string should FAIL."""
    resource = {
        "change": {
            "after": {
                "bucket": "test-bucket",
                "policy": ""
            },
            "after_unknown": {}
        }
    }

    result = check_https_policy("test-bucket", resource)

    assert result["state"] == "FAIL"
    assert "empty" in result["message"].lower()


def test_malformed_json_policy():
    """Malformed JSON should return ERROR."""
    resource = {
        "change": {
            "after": {
                "bucket": "test-bucket",
                "policy": '{"invalid json"'
            },
            "after_unknown": {}
        }
    }

    result = check_https_policy("test-bucket", resource)

    assert result["state"] == "ERROR"
    assert "not valid JSON" in result["message"]


def test_missing_statement_array():
    """Policy without Statement array should return ERROR."""
    policy = {"Version": "2012-10-17"}

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

    assert result["state"] == "ERROR"
    assert "Statement" in result["message"]


def test_empty_statement_array():
    """Policy with empty Statement array should FAIL."""
    policy = {"Version": "2012-10-17", "Statement": []}

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

    assert result["state"] == "FAIL"
    assert "no statements" in result["message"].lower()


def test_deny_but_wrong_condition():
    """Deny statement without SecureTransport should FAIL."""
    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Deny",
                "Principal": "*",
                "Action": "s3:*",
                "Resource": ["arn:aws:s3:::test-bucket", "arn:aws:s3:::test-bucket/*"],
                "Condition": {
                    "IpAddress": {
                        "aws:SourceIp": "192.168.0.0/16"
                    }
                }
            }
        ]
    }

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

    assert result["state"] == "FAIL"
    assert "HTTPS-only" in result["message"]


def test_securetransport_true_not_false():
    """SecureTransport set to 'true' should FAIL."""
    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Deny",
                "Principal": "*",
                "Action": "s3:*",
                "Resource": ["arn:aws:s3:::test-bucket", "arn:aws:s3:::test-bucket/*"],
                "Condition": {
                    "Bool": {
                        "aws:SecureTransport": "true"
                    }
                }
            }
        ]
    }

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

    assert result["state"] == "FAIL"
    assert "not 'false'" in result["message"]


def test_missing_resource_coverage():
    """Deny without full resource coverage should FAIL."""
    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Deny",
                "Principal": "*",
                "Action": "s3:*",
                "Resource": ["arn:aws:s3:::test-bucket"],  # Missing bucket/* coverage
                "Condition": {
                    "Bool": {
                        "aws:SecureTransport": "false"
                    }
                }
            }
        ]
    }

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

    assert result["state"] == "FAIL"
    assert "resource coverage" in result["message"].lower()


def test_policy_is_unknown():
    """Unknown policy should return UNKNOWN."""
    resource = {
        "change": {
            "after": {
                "bucket": "test-bucket",
                "policy": None
            },
            "after_unknown": {
                "policy": True
            }
        }
    }

    result = check_https_policy("test-bucket", resource)

    assert result["state"] == "UNKNOWN"
    assert "unknown" in result["message"].lower()


def test_multiple_statements_find_correct_one():
    """Should find correct Deny statement among multiple statements."""
    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": "*",
                "Action": "s3:GetObject",
                "Resource": "arn:aws:s3:::test-bucket/*"
            },
            {
                "Effect": "Deny",
                "Principal": "*",
                "Action": "s3:*",
                "Resource": ["arn:aws:s3:::test-bucket", "arn:aws:s3:::test-bucket/*"],
                "Condition": {
                    "Bool": {
                        "aws:SecureTransport": "false"
                    }
                }
            }
        ]
    }

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

    assert result["state"] == "PASS"
    assert "HTTPS-only" in result["message"]
