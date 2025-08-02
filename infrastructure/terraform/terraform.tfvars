# Terraform Variables for CheckGuard AI Production Deployment

# Project Configuration
project_name = "checkguard"
environment = "production"
aws_region = "us-east-2"

# Authentication Keys (from .env.development)
clerk_secret_key = "REDACTED_CLERK_KEY_1"
clerk_publishable_key = "pk_test_YmlnLWZseS0xNi5jbGVyay5hY2NvdW50cy5kZXYk"
gemini_api_key = "REDACTED_GEMINI_KEY"

# GitHub Repository (actual repository)
github_repository = "ymehili/CheckGuard"

# Optional SSL Certificate ARN (leave empty for HTTP-only initially)
ssl_certificate_arn = ""

# Billing Protection Configuration
daily_budget_limit = 10
billing_alert_email = "youssefmehili@gmail.com"