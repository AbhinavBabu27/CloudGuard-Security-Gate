# plan_compliant.json

## What This Fixture Represents

A **fully compliant** S3 bucket configuration that passes all security checks. This represents the ideal state for storing confidential documents.

## Resources Included

- **aws_s3_bucket**: Bucket named `confidential-docs-prod` with private ACL
- **aws_s3_bucket_public_access_block**: All four blocks enabled (true)
- **aws_s3_bucket_server_side_encryption_configuration**: AES256 encryption configured
- **aws_s3_bucket_policy**: Policy with Deny statement blocking non-HTTPS access
- **aws_s3_bucket_lifecycle_configuration**: Lifecycle rule deleting objects after 30 days

## Expected Check Results

| Check | Result | Reason |
|-------|--------|--------|
| Public Access Block | ✓ PASS | All four blocks enabled (block_public_acls, block_public_policy, ignore_public_acls, restrict_public_buckets) |
| Encryption | ✓ PASS | Encryption configured with AES256 algorithm |
| HTTPS-Only Policy | ✓ PASS | Policy contains Deny statement with aws:SecureTransport: false condition covering bucket and objects |
| 30-Day Retention | ✓ PASS | Lifecycle rule with Status: Enabled and expiration: days = 30 |

**Overall: PASS**

## What This Fixture Tests Locally

✅ Correct public access block configuration parsing
✅ Encryption algorithm detection (AES256)
✅ Policy JSON parsing and Deny + SecureTransport pattern matching
✅ Lifecycle rule parsing with expiration days validation
✅ Overall result aggregation when all checks pass
✅ Resource linking by bucket name

## What Would Require AWS/Terraform CLI Validation Later

❌ Verify that the policy actually blocks HTTP requests (requires AWS API)
❌ Verify that objects are encrypted (requires KMS/S3 API)
❌ Verify that lifecycle rule deletes objects (requires waiting 30 days or S3 API)
❌ Validate that the plan is generated from real Terraform 1.3.0 code

## Terraform Plan Structure Notes

- **format_version**: "1.2" (standard Terraform plan JSON format)
- **terraform_version**: "1.3.0" (assumed version for structure compatibility)
- **resource_changes**: Array of 5 S3-related resources
- **change.after**: Contains the intended configuration state
- **change.after_unknown**: Marks fields that are unknown/computed at plan time (empty in this case = all known)
- **policy**: Stored as a JSON string (escaped), parsed by the checker

## Example AWS CLI Deployment (Future Validation)

Once Terraform CLI is available:
```bash
terraform init
terraform plan -json > plan.json
python checker.py plan.json
```

Then with AWS access:
```bash
terraform apply
# Verify:
curl -X GET http://confidential-docs-prod.s3.amazonaws.com/  # Should fail
curl -X GET https://confidential-docs-prod.s3.amazonaws.com/ # Should work
aws s3api head-object --bucket confidential-docs-prod --key test-file.txt # Should show encryption
```
