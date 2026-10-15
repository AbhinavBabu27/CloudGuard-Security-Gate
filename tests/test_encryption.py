"""
Tests for Encryption security check.
"""

import pytest
from rules.encryption import check_encryption


def test_aes256_encryption():
    """AES256 encryption should PASS."""
    resource = {
        "change": {
            "after": {
                "bucket": "test-bucket",
                "rule": [
                    {
                        "apply_server_side_encryption_by_default": {
                            "sse_algorithm": "AES256"
                        }
                    }
                ]
            },
            "after_unknown": {}
        }
    }

    result = check_encryption("test-bucket", resource)

    assert result["state"] == "PASS"
    assert "AES256" in result["message"]


def test_kms_encryption():
    """KMS encryption should PASS."""
    resource = {
        "change": {
            "after": {
                "bucket": "test-bucket",
                "rule": [
                    {
                        "apply_server_side_encryption_by_default": {
                            "sse_algorithm": "aws:kms"
                        }
                    }
                ]
            },
            "after_unknown": {}
        }
    }

    result = check_encryption("test-bucket", resource)

    assert result["state"] == "PASS"
    assert "aws:kms" in result["message"]


def test_missing_encryption():
    """Missing encryption resource should FAIL."""
    result = check_encryption("test-bucket", None)

    assert result["state"] == "FAIL"
    assert "not configured" in result["message"]


def test_empty_rule_array():
    """Empty rule array should FAIL."""
    resource = {
        "change": {
            "after": {
                "bucket": "test-bucket",
                "rule": []
            },
            "after_unknown": {}
        }
    }

    result = check_encryption("test-bucket", resource)

    assert result["state"] == "FAIL"
    assert "no encryption rules" in result["message"].lower()


def test_no_algorithm_specified():
    """Rule with no algorithm should FAIL."""
    resource = {
        "change": {
            "after": {
                "bucket": "test-bucket",
                "rule": [
                    {
                        "apply_server_side_encryption_by_default": {
                            "sse_algorithm": None
                        }
                    }
                ]
            },
            "after_unknown": {}
        }
    }

    result = check_encryption("test-bucket", resource)

    assert result["state"] == "FAIL"
    assert "no valid encryption algorithm" in result["message"].lower()


def test_unknown_algorithm():
    """Unknown algorithm should return UNKNOWN."""
    resource = {
        "change": {
            "after": {
                "bucket": "test-bucket",
                "rule": [
                    {
                        "apply_server_side_encryption_by_default": {
                            "sse_algorithm": None
                        }
                    }
                ]
            },
            "after_unknown": {
                "rule": [
                    {
                        "apply_server_side_encryption_by_default": {
                            "sse_algorithm": True
                        }
                    }
                ]
            }
        }
    }

    result = check_encryption("test-bucket", resource)

    assert result["state"] == "UNKNOWN"
    assert "unknown" in result["message"].lower()


def test_invalid_algorithm():
    """Invalid algorithm should FAIL."""
    resource = {
        "change": {
            "after": {
                "bucket": "test-bucket",
                "rule": [
                    {
                        "apply_server_side_encryption_by_default": {
                            "sse_algorithm": "InvalidAlgo"
                        }
                    }
                ]
            },
            "after_unknown": {}
        }
    }

    result = check_encryption("test-bucket", resource)

    assert result["state"] == "FAIL"
    assert "Unknown encryption algorithm" in result["message"]
