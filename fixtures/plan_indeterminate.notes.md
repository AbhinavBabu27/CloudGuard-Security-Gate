# plan_indeterminate.json

## What This Fixture Represents

A bucket configuration where **some security settings are computed or unknown** at plan time. This represents a real-world scenario where Terraform will determine certain values only during `terraform apply`.

Common reasons for computed values:
- Values derived from variables or data sources
- Values that depend on AWS API responses
- Dynamic policy generation from templates

## Resources Included

- **aws_s3_bucket**: Bucket named `confidential-docs-v2`
- **aws_s3_bucket_public_access_block**: All blocks enabled ✓ (known)
- **aws_s3_bucket_server_side_encryption_configuration**: Algorithm is **UNKNOWN** (marked in after_unknown)
- **aws_s3_bucket_policy**: Policy string is **UNKNOWN** (marked in after_unknown)
- **aws_s3_bucket_lifecycle_configuration**: Expiration set to 30 days ✓ (known)

## Expected Check Results

| Check | Result | Reason |
|-------|--------|--------|
| Public Access Block | ✓ PASS | All four blocks enabled (known values) |
| Encryption | ⚠ UNKNOWN | Algorithm value is marked unknown in plan (will be determined at apply) |
| HTTPS-Only Policy | ⚠ UNKNOWN | Policy string is marked unknown (will be determined at apply) |
| 30-Day Retention | ✓ PASS | Lifecycle rule with 30-day expiration (known value) |

**Overall: UNKNOWN** (cannot fully verify; re-run after `terraform apply`)

## What This Fixture Tests Locally

✅ Detection of unknown values in encryption.rule[0].apply_server_side_encryption_by_default.sse_algorithm
✅ Detection of unknown policy string value
✅ Correct result aggregation when mix of PASS and UNKNOWN exist (UNKNOWN takes precedence)
✅ Clear messaging: which checks couldn't be verified and why
✅ Conservative evaluation (UNKNOWN != PASS)

## When Values Are Marked Unknown

In Terraform plan JSON, `after_unknown` marks which fields are computed:

```json
"after_unknown": {
  "rule": [
    {
      "apply_server_side_encryption_by_default": {
        "sse_algorithm": true
      }
    }
  ]
}
```

This means: "The sse_algorithm field will be known at apply time, not now."

## Real-World Example

Configuration that produces unknown values:
```hcl
locals {
  encryption_algo = var.use_kms ? "aws:kms" : "AES256"
}

resource "aws_s3_bucket_server_side_encryption_configuration" "example" {
  bucket = aws_s3_bucket.example.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = local.encryption_algo  # Unknown until var.use_kms is resolved
    }
  }
}

resource "aws_s3_bucket_policy" "example" {
  bucket = aws_s3_bucket.example.id
  policy = data.aws_iam_policy_document.https_only.json  # Unknown until data source is fetched
}
```

## Handling Unknown Values

CloudGuard's approach:
- **Doesn't assume PASS**: Unknown values don't automatically pass security checks
- **Explicit messaging**: Tells user which checks couldn't be verified
- **Actionable**: User can re-run the checker after `terraform apply` when values are known
- **Conservative**: If you can't prove it's secure, it's not claimed as PASS

## Next Steps After Planning

```bash
# 1. Run checker now (produces UNKNOWN)
python checker.py plan.json

# 2. Apply infrastructure
terraform apply

# 3. Generate new plan
terraform plan -json > plan_applied.json

# 4. Re-run checker (should produce PASS if config is correct)
python checker.py plan_applied.json
```

## Terraform Plan Structure Notes

- **format_version**: "1.2"
- **resource_changes**: 5 resources included
- **after_unknown**: Shows which fields are computed (true = unknown)
  - `rule[0].apply_server_side_encryption_by_default.sse_algorithm: true` = algorithm unknown
  - `policy: true` = entire policy string unknown
- **after values**: Some fields show null or placeholder values when unknown

## Edge Case: Partial Unknown Values

This fixture also demonstrates that some values can be known while others are unknown:
- Public access block: all known ✓
- Encryption algorithm: unknown ⚠
- Policy: unknown ⚠
- Retention days: known ✓
