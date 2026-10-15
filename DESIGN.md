# CloudGuard Design & Rationale

## Core Principles

1. **No Cloud Prerequisites**: Designed to work with handcrafted Terraform plan JSON fixtures. Terraform CLI and AWS account are optional (future validation only).
2. **Conservative Evaluation**: Unknown or missing security-critical configurations never silently pass.
3. **Terraform Plan Format**: Uses actual Terraform plan JSON structure (`resource_changes` array) to stay close to real infrastructure-as-code workflows.

## Architecture

### Main Components

- **checker.py**: Parses plan JSON, orchestrates security checks, formats output
- **rules/***: Individual security check modules (public_access_block, encryption, https_policy, retention)
- **fixtures/**: Handcrafted plan JSON files representing three scenarios

### Data Flow

```
Plan JSON
    ↓
[Parse & Extract Resources]
    ↓
[Link Related Resources by Bucket Name]
    ↓
[Evaluate Each Security Check]
    ↓
[Aggregate Results: ERROR > FAIL > UNKNOWN > PASS]
    ↓
[Format & Output Report]
```

## The 4 Security Checks

### 1. Public Access Block
- **What**: All four public access blocks enabled
- **Resources**: `aws_s3_bucket_public_access_block`
- **Result States**: PASS | FAIL | UNKNOWN

### 2. Encryption
- **What**: Server-side encryption configured (AES256 or KMS)
- **Resources**: `aws_s3_bucket_server_side_encryption_configuration`
- **Result States**: PASS | FAIL | UNKNOWN | ERROR

### 3. HTTPS-Only Policy
- **What**: Bucket policy with Deny statement blocking non-HTTPS (`aws:SecureTransport: false`)
- **Resources**: `aws_s3_bucket_policy`
- **Pattern**: `Effect: Deny` + `Condition.Bool.aws:SecureTransport: false` + resource coverage
- **Result States**: PASS | FAIL | UNKNOWN | ERROR

### 4. 30-Day Retention
- **What**: Lifecycle expiration rule deletes objects within 30 days
- **Resources**: `aws_s3_bucket_lifecycle_configuration`
- **Constraint**: Unversioned buckets only (v1 limitation)
- **Result States**: PASS | FAIL | UNKNOWN

## Result Aggregation Logic

For a single S3 bucket:
```
IF any check returns ERROR
  → Overall: FAIL (data integrity issue)
ELSE IF any check returns FAIL
  → Overall: FAIL (security violation)
ELSE IF any check returns UNKNOWN
  → Overall: UNKNOWN (cannot fully verify)
ELSE IF all checks return PASS
  → Overall: PASS
```

## Data Handling

### Resource Presence
- **Resource missing**: FAIL (security config incomplete)
- **Resource present but disabled**: FAIL
- **Resource present and enabled**: Evaluate values

### Values
- **Value is null**: FAIL (not set; defaults to insecure)
- **Value is false/wrong**: FAIL (explicitly insecure)
- **Value is `{"unknown": true}`**: UNKNOWN (can't verify until apply)
- **Value is malformed (policy)**: ERROR

### Resource Linking
- Resources are linked by bucket name (the `bucket` attribute)
- Example: `aws_s3_bucket.example` (bucket: "my-bucket") links with `aws_s3_bucket_public_access_block.example` (bucket: "my-bucket")

## Terraform Plan JSON Structure

We use the actual plan format:
```json
{
  "format_version": "1.2",
  "terraform_version": "1.3.0",
  "resource_changes": [
    {
      "address": "aws_s3_bucket.confidential_docs",
      "type": "aws_s3_bucket",
      "change": {
        "actions": ["create"],
        "before": null,
        "after": { /* resource attributes */ },
        "after_unknown": { /* which values are unknown */ }
      }
    }
  ]
}
```

**Why this format?**
- Matches what `terraform plan -json` produces
- Allows seamless integration when Terraform CLI becomes available
- Familiar to Terraform users

## Fixtures

Three handcrafted plan JSON files, minimal but complete:

1. **plan_compliant.json**: All checks PASS
2. **plan_non_compliant.json**: Multiple checks FAIL
3. **plan_indeterminate.json**: Mix of PASS and UNKNOWN

Each has a corresponding `.notes.md` file explaining what's being tested.

## Testing Strategy

### Unit Tests (~25 tests)
- Test each security check in isolation
- Use plan JSON fragments or minimal complete plans
- Cover: nominal cases, edge cases, error cases

### Test Scope
- Local parsing and evaluation only
- No Terraform CLI invocation
- No AWS API calls
- Fixture-based (handcrafted plan JSON)

## Known Limitations

### Current Version (v1)
1. **Unversioned buckets only**: No support for versioning + lifecycle interactions
2. **Policy pattern validation**: Only recognizes the documented Deny + SecureTransport pattern; other valid patterns not supported
3. **Policy resource coverage**: Basic check (resources array must include bucket and objects); doesn't validate complex conditions
4. **Lifecycle filters**: Doesn't validate rule filters/prefixes (assumes rules apply to all objects)
5. **No AWS validation**: Can't verify policies actually work, encryption keys are valid, lifecycle rules execute

### Future Work (v2+)
- [ ] Terraform CLI integration (validate against real plan output)
- [ ] AWS account integration (deploy and test real bucket behavior)
- [ ] Versioned bucket support
- [ ] Additional policy patterns
- [ ] JSON output format option

## Local vs. Integration Testing

### What We Validate Locally
- ✅ Plan JSON parsing and resource extraction
- ✅ Security config presence/absence
- ✅ Configuration values (blocks, algorithms, expiration days)
- ✅ Policy structure and Deny + SecureTransport pattern
- ✅ Unknown value handling (UNKNOWN not PASS)
- ✅ Result aggregation logic

### What Requires Terraform CLI & AWS Later
- ❌ Validate fixture structure against real plan output
- ❌ Test against actual Terraform configurations
- ❌ Verify policy blocks HTTP (requires AWS)
- ❌ Verify encryption works (requires AWS KMS)
- ❌ Verify lifecycle deletes objects (requires AWS S3, time passage)

## Exit Codes

- `0`: All resources PASS
- `1`: At least one resource FAIL
- `2`: At least one resource UNKNOWN (no FAIL)
- `3`: Error parsing or processing plan (malformed input)

## Assumptions

1. **Terraform Version**: 1.3+
2. **AWS Provider**: 5.0+
3. **Bucket Model**: Unversioned (no multi-version retention)
4. **Policy Format**: Uses standard AWS policy JSON syntax
5. **Resource Naming**: Resources have unique addresses in the plan

## Security Considerations

This tool performs *static analysis* of configuration. It does NOT:
- Deploy infrastructure
- Make AWS API calls
- Require credentials or access
- Test actual S3 behavior
- Verify encryption key strength
- Check IAM permissions in detail

It DOES:
- Validate configuration structure and values
- Flag missing security configurations
- Highlight unknown/computed values that can't be verified
- Provide human-readable security assessment
