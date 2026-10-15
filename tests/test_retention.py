"""
Tests for 30-Day Retention security check.
"""

import pytest
from rules.retention import check_retention


def test_30_day_expiration():
    """30-day expiration should PASS."""
    resource = {
        "change": {
            "after": {
                "bucket": "test-bucket",
                "rule": [
                    {
                        "id": "expire-docs",
                        "status": "Enabled",
                        "expiration": {
                            "days": 30
                        }
                    }
                ]
            },
            "after_unknown": {}
        }
    }

    result = check_retention("test-bucket", resource)

    assert result["state"] == "PASS"
    assert "30" in result["message"]


def test_less_than_30_days():
    """Less than 30 days should PASS."""
    resource = {
        "change": {
            "after": {
                "bucket": "test-bucket",
                "rule": [
                    {
                        "id": "expire-docs",
                        "status": "Enabled",
                        "expiration": {
                            "days": 15
                        }
                    }
                ]
            },
            "after_unknown": {}
        }
    }

    result = check_retention("test-bucket", resource)

    assert result["state"] == "PASS"
    assert "15" in result["message"]


def test_more_than_30_days():
    """More than 30 days should FAIL."""
    resource = {
        "change": {
            "after": {
                "bucket": "test-bucket",
                "rule": [
                    {
                        "id": "expire-docs",
                        "status": "Enabled",
                        "expiration": {
                            "days": 45
                        }
                    }
                ]
            },
            "after_unknown": {}
        }
    }

    result = check_retention("test-bucket", resource)

    assert result["state"] == "FAIL"
    assert "45" in result["message"]
    assert "exceeds" in result["message"].lower()


def test_missing_lifecycle_resource():
    """Missing lifecycle resource should FAIL."""
    result = check_retention("test-bucket", None)

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

    result = check_retention("test-bucket", resource)

    assert result["state"] == "FAIL"
    assert "no lifecycle rules" in result["message"].lower()


def test_disabled_rule():
    """Disabled rule should FAIL."""
    resource = {
        "change": {
            "after": {
                "bucket": "test-bucket",
                "rule": [
                    {
                        "id": "expire-docs",
                        "status": "Disabled",
                        "expiration": {
                            "days": 30
                        }
                    }
                ]
            },
            "after_unknown": {}
        }
    }

    result = check_retention("test-bucket", resource)

    assert result["state"] == "FAIL"
    assert "no enabled" in result["message"].lower()


def test_unknown_expiration_days():
    """Unknown expiration days should return UNKNOWN."""
    resource = {
        "change": {
            "after": {
                "bucket": "test-bucket",
                "rule": [
                    {
                        "id": "expire-docs",
                        "status": "Enabled",
                        "expiration": {
                            "days": None
                        }
                    }
                ]
            },
            "after_unknown": {
                "rule": [
                    {
                        "expiration": {
                            "days": True
                        }
                    }
                ]
            }
        }
    }

    result = check_retention("test-bucket", resource)

    assert result["state"] == "UNKNOWN"
    assert "unknown" in result["message"].lower()


def test_no_expiration_only_noncurrent():
    """Rule with only NoncurrentVersionExpiration should FAIL."""
    resource = {
        "change": {
            "after": {
                "bucket": "test-bucket",
                "rule": [
                    {
                        "id": "expire-old-versions",
                        "status": "Enabled",
                        "noncurrent_version_expiration": {
                            "days": 30
                        }
                    }
                ]
            },
            "after_unknown": {}
        }
    }

    result = check_retention("test-bucket", resource)

    assert result["state"] == "FAIL"
    assert "no enabled lifecycle rule" in result["message"].lower()


def test_multiple_rules_take_most_restrictive():
    """With multiple rules, should take most restrictive (smallest days)."""
    resource = {
        "change": {
            "after": {
                "bucket": "test-bucket",
                "rule": [
                    {
                        "id": "rule1",
                        "status": "Enabled",
                        "expiration": {"days": 60}
                    },
                    {
                        "id": "rule2",
                        "status": "Enabled",
                        "expiration": {"days": 20}
                    }
                ]
            },
            "after_unknown": {}
        }
    }

    result = check_retention("test-bucket", resource)

    assert result["state"] == "PASS"
    assert "20" in result["message"]
