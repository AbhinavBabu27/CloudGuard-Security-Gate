# plan_non_compliant.json

## What This Fixture Represents

An **insecure** S3 bucket configuration that violates multiple security requirements. This represents a common misconfiguration scenario where a developer forgets to add security settings.

## Resources Included

- **aws_s3_bucket**: Bucket named `public-logs-bucket` with log-delivery ACL
- **aws_s3_bucket_server_side_encryption_configuration**: AES256 encryption (✓ correct)
- **Missing**: aws_s3_bucket_public_access_block (not configured)
- **Missing**: aws_s3_bucket_policy (not configured)
- **aws_s3_bucket_lifecycle_configuration**: Lifecycle rule with 45-day expiration (exceeds 30-day limit)

## Expected Check Results

| Check | Result | Reason |
|-------|--------|--------|
| Public Access Block | ✗ FAIL | Resource not configured; public access blocks not enabled |
| Encryption | ✓ PASS | Encryption configured with AES256 algorithm |
| HTTPS-Only Policy | ✗ FAIL | Policy resource missing; no bucket policy to enforce HTTPS |
| 30-Day Retention | ✗ FAIL | Lifecycle expiration set to 45 days, exceeds 30-day limit |

**Overall: FAIL** (3 critical security violations)

## What This Fixture Tests Locally

✅ Detection of missing public access block resource (FAIL)
✅ Handling of missing policy resource (FAIL)
✅ Expiration days validation (45 > 30 = FAIL)
✅ Correct result aggregation when multiple checks fail
✅ Symmetric test with compliant fixture (same bucket type, different config)

## Security Issues Demonstrated

1. **No Public Access Block**: Without this, even private ACLs can be overridden by bucket policies or object ACLs
2. **No HTTPS Policy**: Objects can be accessed over unencrypted HTTP connections
3. **Excessive Retention**: Documents stored for 45 days instead of required 30 days; increases data exposure window

## Terraform Plan Structure Notes

- **format_version**: "1.2"
- **resource_changes**: Only 3 resources (bucket, encryption, lifecycle) - no public access block or policy
- **expiration.days**: 45 (triggers FAIL on retention check)
- **all values known** (no after_unknown marked as true)

## Example Fix

To make this compliant, add:

```hcl
resource "aws_s3_bucket_public_access_block" "public_logs" {
  bucket = aws_s3_bucket.public_logs.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_policy" "public_logs" {
  bucket = aws_s3_bucket.public_logs.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "DenyUnencryptedAccess"
        Effect = "Deny"
        Principal = "*"
        Action = "s3:*"
        Resource = [
          aws_s3_bucket.public_logs.arn,
          "${aws_s3_bucket.public_logs.arn}/*"
        ]
        Condition = {
          Bool = {
            "aws:SecureTransport" = "false"
          }
        }
      }
    ]
  })
}
```

And change lifecycle:
```hcl
expiration {
  days = 30  # Change from 45 to 30
}
```
