"""
Tests for Public Access Block security check.
"""

import pytest
from rules.public_access_block import check_public_access_block


def test_all_blocks_enabled():
    """All four blocks enabled should PASS."""
    resource = {
        "change": {
            "after": {
                "bucket": "test-bucket",
                "block_public_acls": True,
                "block_public_policy": True,
                "ignore_public_acls": True,
                "restrict_public_buckets": True,
            },
            "after_unknown": {}
        }
    }

    result = check_public_access_block("test-bucket", resource)

    assert result["state"] == "PASS"
    assert "All public access blocks enabled" in result["message"]


def test_one_block_disabled():
    """If any block is disabled should FAIL."""
    resource = {
        "change": {
            "after": {
                "bucket": "test-bucket",
                "block_public_acls": True,
                "block_public_policy": False,
                "ignore_public_acls": True,
                "restrict_public_buckets": True,
            },
            "after_unknown": {}
        }
    }

    result = check_public_access_block("test-bucket", resource)

    assert result["state"] == "FAIL"
    assert "block_public_policy" in result["message"]


def test_multiple_blocks_disabled():
    """If multiple blocks are disabled should FAIL."""
    resource = {
        "change": {
            "after": {
                "bucket": "test-bucket",
                "block_public_acls": True,
                "block_public_policy": False,
                "ignore_public_acls": False,
                "restrict_public_buckets": True,
            },
            "after_unknown": {}
        }
    }

    result = check_public_access_block("test-bucket", resource)

    assert result["state"] == "FAIL"
    assert "block_public_policy" in result["message"]
    assert "ignore_public_acls" in result["message"]


def test_missing_resource():
    """Missing resource should FAIL."""
    result = check_public_access_block("test-bucket", None)

    assert result["state"] == "FAIL"
    assert "not configured" in result["message"]


def test_null_after_configuration():
    """Empty after configuration should FAIL."""
    resource = {
        "change": {
            "after": {},
            "after_unknown": {}
        }
    }

    result = check_public_access_block("test-bucket", resource)

    assert result["state"] == "FAIL"
    assert "empty" in result["message"].lower()


def test_block_value_is_null():
    """If block value is null (not set) should FAIL."""
    resource = {
        "change": {
            "after": {
                "bucket": "test-bucket",
                "block_public_acls": None,
                "block_public_policy": True,
                "ignore_public_acls": True,
                "restrict_public_buckets": True,
            },
            "after_unknown": {}
        }
    }

    result = check_public_access_block("test-bucket", resource)

    assert result["state"] == "FAIL"
    assert "block_public_acls" in result["message"]


def test_unknown_block_value():
    """If block value is unknown should return UNKNOWN."""
    resource = {
        "change": {
            "after": {
                "bucket": "test-bucket",
                "block_public_acls": True,
                "block_public_policy": True,
                "ignore_public_acls": True,
                "restrict_public_buckets": True,
            },
            "after_unknown": {
                "block_public_acls": True
            }
        }
    }

    result = check_public_access_block("test-bucket", resource)

    assert result["state"] == "UNKNOWN"
    assert "unknown" in result["message"].lower()
