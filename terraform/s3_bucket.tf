# Reference Terraform Configuration for Compliant S3 Bucket
# This configuration generates a plan that would pass all CloudGuard checks

terraform {
  required_version = ">= 1.3.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = "us-east-1"
}

# S3 Bucket
resource "aws_s3_bucket" "confidential_docs" {
  bucket = "confidential-docs-prod"

  tags = {
    Name        = "Confidential Documents"
    Environment = "production"
    Purpose     = "Document Storage"
  }
}

# Block all public access
resource "aws_s3_bucket_public_access_block" "confidential_docs" {
  bucket = aws_s3_bucket.confidential_docs.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Enable server-side encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "confidential_docs" {
  bucket = aws_s3_bucket.confidential_docs.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
    bucket_key_enabled = false
  }
}

# Enforce HTTPS-only access
resource "aws_s3_bucket_policy" "confidential_docs" {
  bucket = aws_s3_bucket.confidential_docs.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "DenyUnencryptedObjectUploads"
        Effect    = "Deny"
        Principal = "*"
        Action    = "s3:*"
        Resource = [
          aws_s3_bucket.confidential_docs.arn,
          "${aws_s3_bucket.confidential_docs.arn}/*"
        ]
        Condition = {
          Bool = {
            "aws:SecureTransport" = "false"
          }
        }
      }
    ]
  })

  depends_on = [aws_s3_bucket_public_access_block.confidential_docs]
}

# Set 30-day retention via lifecycle rules
resource "aws_s3_bucket_lifecycle_configuration" "confidential_docs" {
  bucket = aws_s3_bucket.confidential_docs.id

  rule {
    id     = "delete-old-documents"
    status = "Enabled"

    expiration {
      days = 30
    }
  }
}

# Outputs for reference
output "bucket_name" {
  description = "Name of the S3 bucket"
  value       = aws_s3_bucket.confidential_docs.id
}

output "bucket_arn" {
  description = "ARN of the S3 bucket"
  value       = aws_s3_bucket.confidential_docs.arn
}
