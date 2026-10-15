# CloudGuard - S3 Security Configuration Checker

CloudGuard is a Python tool that validates S3 bucket security configurations against Terraform plans before deployment. It checks for public access exposure, encryption, HTTPS-only enforcement, and 30-day retention policies.

## Features

- **No prerequisites**: Works with handcrafted Terraform plan JSON fixtures. No AWS account, Terraform CLI, or cloud access required.
- **4 Security Checks**: Public Access Block, Encryption, HTTPS-Only Policy, 30-Day Retention
- **Conservative evaluation**: Unknown or missing security configs never silently pass
- **Clear output**: Human-readable per-bucket assessment with pass/fail/unknown/error states

## Quick Start

### Run checker on a fixture
```bash
python checker.py fixtures/plan_compliant.json
```

### Run all tests
```bash
python -m pytest tests/ -v
```

## Project Structure

```
CloudGuard/
├── checker.py              # Main checker entry point
├── terraform/
│   └── s3_bucket.tf       # Reference Terraform configuration
├── fixtures/
│   ├── plan_compliant.json
│   ├── plan_compliant.notes.md
│   ├── plan_non_compliant.json
│   ├── plan_non_compliant.notes.md
│   ├── plan_indeterminate.json
│   └── plan_indeterminate.notes.md
├── rules/                  # Security check modules
│   ├── public_access_block.py
│   ├── encryption.py
│   ├── https_policy.py
│   └── retention.py
├── tests/                  # Unit and integration tests
│   ├── test_public_access_block.py
│   ├── test_encryption.py
│   ├── test_https_policy.py
│   ├── test_retention.py
│   └── test_edge_cases.py
├── README.md
└── DESIGN.md              # Design rationale
```

## Design & Implementation Notes

- **Terraform Version**: Assumes Terraform 1.3+ and AWS provider 5.0+
- **Plan Structure**: Uses actual Terraform plan JSON (`resource_changes` format)
- **Local Testing Only**: All fixtures are handcrafted; Terraform CLI integration is future work
- **Unversioned Buckets**: Current implementation assumes unversioned S3 buckets
- **Conservative Defaults**: Missing or unknown security configs result in FAIL/UNKNOWN, never PASS

See `DESIGN.md` for detailed architectural rationale.
