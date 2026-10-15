# CloudGuard Quick Start

## Installation

No special installation required. Python 3.6+ is all you need.

## Run Checker on Fixtures

```bash
# Test 1: Compliant configuration (should PASS)
python checker.py fixtures/plan_compliant.json
# Expected exit code: 0

# Test 2: Non-compliant configuration (should FAIL)
python checker.py fixtures/plan_non_compliant.json
# Expected exit code: 1

# Test 3: Indeterminate configuration (should UNKNOWN)
python checker.py fixtures/plan_indeterminate.json
# Expected exit code: 2
```

## Run Tests

```bash
# Install pytest (optional, for running unit tests)
pip install pytest

# Run all tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_https_policy.py -v

# Run with coverage report
python -m pytest tests/ --cov=rules --cov=checker
```

## Understanding Exit Codes

| Exit Code | Meaning |
|-----------|---------|
| 0 | All buckets PASS all checks |
| 1 | At least one bucket FAIL one or more checks |
| 2 | No failures, but at least one check UNKNOWN (can't verify) |
| 3 | Error processing the plan file (invalid JSON, missing file, etc.) |

## Quick Test Script

Save as `test_all.sh` (or run commands manually):

```bash
#!/bin/bash

echo "=== Testing CloudGuard ==="
echo ""

echo "Test 1: Compliant Configuration"
python checker.py fixtures/plan_compliant.json
CODE1=$?
echo "Exit code: $CODE1 (expected: 0)"
echo ""

echo "Test 2: Non-Compliant Configuration"
python checker.py fixtures/plan_non_compliant.json
CODE2=$?
echo "Exit code: $CODE2 (expected: 1)"
echo ""

echo "Test 3: Indeterminate Configuration"
python checker.py fixtures/plan_indeterminate.json
CODE3=$?
echo "Exit code: $CODE3 (expected: 2)"
echo ""

echo "=== Unit Tests ==="
python -m pytest tests/ -v --tb=short
CODE4=$?
echo ""

if [ $CODE1 -eq 0 ] && [ $CODE2 -eq 1 ] && [ $CODE3 -eq 2 ] && [ $CODE4 -eq 0 ]; then
    echo "✓ All tests passed!"
    exit 0
else
    echo "✗ Some tests failed"
    exit 1
fi
```

## Directory Structure

```
CloudGuard/
├── checker.py              ← Main entry point
├── rules/                  ← Security check modules
│   ├── public_access_block.py
│   ├── encryption.py
│   ├── https_policy.py
│   └── retention.py
├── fixtures/               ← Test plan JSON files
│   ├── plan_compliant.json
│   ├── plan_compliant.notes.md
│   ├── plan_non_compliant.json
│   ├── plan_non_compliant.notes.md
│   ├── plan_indeterminate.json
│   └── plan_indeterminate.notes.md
├── tests/                  ← Unit tests (43 tests)
│   ├── test_public_access_block.py
│   ├── test_encryption.py
│   ├── test_https_policy.py
│   ├── test_retention.py
│   └── test_edge_cases.py
├── terraform/              ← Reference configuration
│   └── s3_bucket.tf
└── docs/
    ├── README.md
    ├── DESIGN.md
    ├── TESTING.md
    └── IMPLEMENTATION_SUMMARY.md
```

## What Gets Checked

CloudGuard validates 4 security requirements for S3 buckets:

1. **Public Access Block** - All four blocks must be enabled
   - block_public_acls
   - block_public_policy
   - ignore_public_acls
   - restrict_public_buckets

2. **Encryption** - Must use AES256 or aws:kms
   - Requires: aws_s3_bucket_server_side_encryption_configuration
   - sse_algorithm must be specified

3. **HTTPS-Only Access** - Bucket policy must deny non-HTTPS
   - Requires: Deny statement with aws:SecureTransport: false condition
   - Must cover both bucket and objects (arn:aws:s3:::bucket and arn:aws:s3:::bucket/*)

4. **30-Day Retention** - Objects expire within 30 days
   - Requires: Lifecycle expiration rule with days ≤ 30
   - Status must be Enabled

## Interpreting Results

### ✓ PASS
Configuration is correct and secure. No action needed.

### ✗ FAIL
Configuration is missing or incorrect. Must be fixed before deployment.

### ⚠ UNKNOWN
Value will be known at apply time (computed). Re-run after `terraform apply`.

### ✗ ERROR (shown as FAIL)
Data is corrupted or malformed. Fix the configuration.

## Example Output

### Compliant Bucket
```
Resource: aws_s3_bucket.confidential_docs
============================================================
✓ Public Access Block: PASS
✓ Encryption: PASS
✓ HTTPS-Only Policy: PASS
✓ 30-Day Retention: PASS

Overall Result: PASS
```

### Non-Compliant Bucket
```
Resource: aws_s3_bucket.public_logs
============================================================
✗ Public Access Block: FAIL
  └─ Public access block not configured
✓ Encryption: PASS
✗ HTTPS-Only Policy: FAIL
  └─ No bucket policy configured
✗ 30-Day Retention: FAIL
  └─ Expiration exceeds 30 days (45 days)

Overall Result: FAIL
```

### Indeterminate Bucket
```
Resource: aws_s3_bucket.confidential_docs_v2
============================================================
✓ Public Access Block: PASS
⚠ Encryption: UNKNOWN
  └─ Encryption algorithm is unknown (computed)
⚠ HTTPS-Only Policy: UNKNOWN
  └─ Policy is unknown (computed at apply time)
✓ 30-Day Retention: PASS

Overall Result: UNKNOWN
```

## Common Issues

### "No S3 buckets found in plan"
- Check that your plan includes S3 resources
- Ensure resource types start with `aws_s3_bucket`

### "Plan file not found"
- Verify the path to the plan JSON file is correct
- Use absolute or relative paths: `python checker.py ./fixtures/plan_compliant.json`

### "Plan file is not valid JSON"
- Make sure the plan file is valid JSON
- Use a JSON validator to check syntax

### Test failures
- Run with `-v` flag for verbose output: `pytest tests/ -v`
- Check the specific test that failed
- Review the fixture data that the test uses

## Next Steps

1. **Run the checker on fixtures** to verify it works
2. **Run the unit tests** to ensure correctness
3. **Review the documentation** to understand limitations
4. **Integrate into your workflow** (CI/CD, pre-commit hooks, etc.)
5. **Add real Terraform integration** when CLI becomes available

## For More Details

- **Architecture**: See `DESIGN.md`
- **Testing guide**: See `TESTING.md`
- **Implementation details**: See `IMPLEMENTATION_SUMMARY.md`
- **Full README**: See `README.md`
