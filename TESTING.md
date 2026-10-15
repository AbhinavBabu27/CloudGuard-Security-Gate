# CloudGuard Testing Guide

## Quick Start

### Run the Checker on Fixtures

```bash
# Test compliant configuration (should PASS)
python checker.py fixtures/plan_compliant.json

# Test non-compliant configuration (should FAIL)
python checker.py fixtures/plan_non_compliant.json

# Test indeterminate configuration (should UNKNOWN)
python checker.py fixtures/plan_indeterminate.json
```

### Run All Unit Tests

```bash
# Using pytest
python -m pytest tests/ -v

# Or with coverage report
python -m pytest tests/ -v --cov=rules --cov=checker
```

## Expected Results for Each Fixture

### 1. plan_compliant.json

**Command:**
```bash
python checker.py fixtures/plan_compliant.json
```

**Expected Output:**
```
Resource: aws_s3_bucket.confidential_docs
============================================================
✓ Public Access Block: PASS
✓ Encryption: PASS
✓ HTTPS-Only Policy: PASS
✓ 30-Day Retention: PASS

Overall Result: PASS

============================================================
SUMMARY
============================================================
  confidential_docs: PASS
```

**Exit Code:** `0`

**What's Tested:**
- All four security checks pass
- Public access blocks all enabled
- Encryption with AES256
- HTTPS policy with proper Deny statement
- Lifecycle expiration at exactly 30 days
- Overall aggregation: PASS (all checks PASS)

---

### 2. plan_non_compliant.json

**Command:**
```bash
python checker.py fixtures/plan_non_compliant.json
```

**Expected Output:**
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

============================================================
SUMMARY
============================================================
  public_logs: FAIL
```

**Exit Code:** `1`

**What's Tested:**
- Public access block missing (FAIL)
- Encryption configured (PASS)
- Policy missing (FAIL)
- Retention exceeds limit (FAIL)
- Overall aggregation: FAIL (multiple checks FAIL)

---

### 3. plan_indeterminate.json

**Command:**
```bash
python checker.py fixtures/plan_indeterminate.json
```

**Expected Output:**
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

============================================================
SUMMARY
============================================================
  confidential_docs_v2: UNKNOWN
```

**Exit Code:** `2`

**What's Tested:**
- Public access block all enabled (PASS)
- Encryption algorithm marked unknown (UNKNOWN)
- Policy marked unknown (UNKNOWN)
- Retention set to 30 days (PASS)
- Overall aggregation: UNKNOWN (PASS + UNKNOWN = UNKNOWN)
- Conservative evaluation: doesn't claim PASS when values unknown

---

## Unit Test Coverage

### Test Categories

#### Public Access Block Tests (8 tests)
```bash
python -m pytest tests/test_public_access_block.py -v
```

**Coverage:**
- ✓ All blocks enabled → PASS
- ✗ One block disabled → FAIL
- ✗ Multiple blocks disabled → FAIL
- ✗ Resource missing → FAIL
- ✗ Empty configuration → FAIL
- ✗ Null values → FAIL
- ⚠ Unknown values → UNKNOWN

#### Encryption Tests (7 tests)
```bash
python -m pytest tests/test_encryption.py -v
```

**Coverage:**
- ✓ AES256 algorithm → PASS
- ✓ KMS algorithm → PASS
- ✗ Missing resource → FAIL
- ✗ Empty rule array → FAIL
- ✗ No algorithm specified → FAIL
- ⚠ Unknown algorithm → UNKNOWN
- ✗ Invalid algorithm → FAIL

#### HTTPS Policy Tests (10 tests)
```bash
python -m pytest tests/test_https_policy.py -v
```

**Coverage:**
- ✓ Valid Deny + SecureTransport pattern → PASS
- ✗ Missing policy → FAIL
- ✗ Empty policy → FAIL
- ✗ Malformed JSON → ERROR
- ✗ Missing Statement array → ERROR
- ✗ Empty Statement array → FAIL
- ✗ Deny without SecureTransport → FAIL
- ✗ SecureTransport set to true → FAIL
- ✗ Missing resource coverage → FAIL
- ⚠ Unknown policy → UNKNOWN
- ✓ Multiple statements (finds correct one) → PASS

#### Retention Tests (8 tests)
```bash
python -m pytest tests/test_retention.py -v
```

**Coverage:**
- ✓ 30-day expiration → PASS
- ✓ Less than 30 days → PASS
- ✗ More than 30 days → FAIL
- ✗ Missing resource → FAIL
- ✗ Empty rule array → FAIL
- ✗ Disabled rule → FAIL
- ⚠ Unknown expiration days → UNKNOWN
- ✗ Only NoncurrentVersionExpiration (no Expiration) → FAIL
- ✓ Multiple rules (takes most restrictive) → PASS

#### Edge Cases & Integration Tests (10 tests)
```bash
python -m pytest tests/test_edge_cases.py -v
```

**Coverage:**
- Multiple buckets in plan
- Non-S3 resources ignored
- Empty plan handling
- Result aggregation: ERROR
- Result aggregation: FAIL
- Result aggregation: UNKNOWN
- Result aggregation: PASS
- Result precedence: FAIL > UNKNOWN
- Result precedence: ERROR > UNKNOWN
- Resource linking by bucket name
- Unchanged resources evaluated
- Malformed resources handled gracefully

---

## Running Tests with Coverage

```bash
# Generate coverage report
python -m pytest tests/ --cov=rules --cov=checker --cov-report=html

# View in browser
open htmlcov/index.html  # macOS
start htmlcov/index.html # Windows
```

---

## Exit Codes

| Code | Meaning | Example |
|------|---------|---------|
| `0` | All resources PASS | All checks pass on all buckets |
| `1` | At least one FAIL | Any bucket fails any check |
| `2` | At least one UNKNOWN | No failures, but some checks can't be verified |
| `3` | Error processing plan | Invalid JSON, missing file, etc. |

---

## Interpreting Output

### PASS (✓)
- Configuration is correct
- Value is known and meets requirement
- Move forward with confidence

### FAIL (✗)
- Configuration is missing or incorrect
- Security requirement not met
- Must be fixed before deployment

### UNKNOWN (⚠)
- Configuration value is computed (will be known at apply time)
- Cannot verify with current plan
- **Action:** Re-run checker after `terraform apply`

### ERROR (✗ shown as FAIL overall)
- Data is malformed (e.g., invalid JSON)
- Cannot safely evaluate
- Must investigate and fix configuration

---

## Debugging Test Failures

### If a unit test fails:

1. **Check test output**: Shows which assertion failed
2. **Review fixture data**: Look at `fixtures/*.notes.md` for what's being tested
3. **Examine rule logic**: Check `rules/*.py` for the validation logic
4. **Reproduce manually**: Run checker on fixture to see actual output

### Example:
```bash
# Test fails
python -m pytest tests/test_https_policy.py::test_valid_https_policy -v

# Manually verify the fixture
python checker.py fixtures/plan_compliant.json

# Check the policy in the fixture
cat fixtures/plan_compliant.json | grep -A 20 "policy"
```

---

## Adding New Tests

When adding tests:
1. Create fixture JSON data in test function
2. Call the rule function with fixture data
3. Assert on state and message
4. Test both happy path and edge cases

Example:
```python
def test_new_scenario():
    resource = {
        "change": {
            "after": { /* your test data */ },
            "after_unknown": {}
        }
    }
    
    result = check_public_access_block("test-bucket", resource)
    
    assert result["state"] == "PASS"
    assert "message" in result
```

---

## Testing Locally vs. Integration Testing

### What These Tests Cover (Local)
✅ Parser logic
✅ Security check evaluation
✅ Result aggregation
✅ Error handling
✅ Edge case scenarios

### What Would Require Integration Testing (Future)
❌ Validation against real Terraform output
❌ AWS API behavior
❌ Real bucket deployment
❌ Actual policy enforcement

---

## Continuous Integration

For CI/CD pipelines:

```bash
# Run all tests, fail if any fail
python -m pytest tests/ -v --tb=short

# Exit code indicates result
echo "Exit code: $?"
```

In your CI pipeline:
```yaml
- name: Run CloudGuard tests
  run: python -m pytest tests/ -v
  
- name: Check plan with CloudGuard
  run: |
    python checker.py fixtures/plan_compliant.json
    if [ $? -eq 0 ]; then
      echo "✓ Plan passed security checks"
    else
      echo "✗ Plan failed security checks"
      exit 1
    fi
```
