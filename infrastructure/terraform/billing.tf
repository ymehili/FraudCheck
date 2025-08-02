# AWS Billing Protection and Cost Management

# Variables for billing configuration
variable "daily_budget_limit" {
  description = "Daily budget limit in USD"
  type        = number
  default     = 10
}

variable "billing_alert_email" {
  description = "Email address for billing alerts"
  type        = string
  default     = "admin@checkguard.ai"
}

# SNS Topic for billing alerts
resource "aws_sns_topic" "billing_alerts" {
  name = "${var.project_name}-billing-alerts"

  tags = {
    Environment = var.environment
    Project     = var.project_name
    Purpose     = "BillingAlerts"
  }
}

# SNS Topic subscription for email alerts
resource "aws_sns_topic_subscription" "billing_email" {
  topic_arn = aws_sns_topic.billing_alerts.arn
  protocol  = "email"
  endpoint  = var.billing_alert_email
}

# IAM role for Budget actions
resource "aws_iam_role" "budget_actions" {
  name = "${var.project_name}-budget-actions-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "budgets.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Environment = var.environment
    Project     = var.project_name
    Purpose     = "BudgetActions"
  }
}

# IAM policy for budget actions to deny new resource creation
resource "aws_iam_policy" "budget_actions_policy" {
  name        = "${var.project_name}-budget-actions-policy"
  description = "Policy to restrict resource creation when budget is exceeded"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Deny"
        Action = [
          "ec2:RunInstances",
          "ec2:CreateTags",
          "ecs:CreateService",
          "ecs:UpdateService",
          "rds:CreateDBInstance",
          "rds:CreateDBCluster",
          "elasticache:CreateCacheCluster",
          "elasticache:CreateReplicationGroup",
          "s3:CreateBucket",
          "lambda:CreateFunction",
          "elasticloadbalancing:CreateLoadBalancer",
          "cloudfront:CreateDistribution"
        ]
        Resource = "*"
        Condition = {
          StringEquals = {
            "aws:RequestedRegion" = var.aws_region
          }
        }
      }
    ]
  })

  tags = {
    Environment = var.environment
    Project     = var.project_name
    Purpose     = "BudgetActions"
  }
}

# Attach policy to role
resource "aws_iam_role_policy_attachment" "budget_actions" {
  role       = aws_iam_role.budget_actions.name
  policy_arn = aws_iam_policy.budget_actions_policy.arn
}

# Daily Budget with alerts and actions
resource "aws_budgets_budget" "daily_limit" {
  name         = "${var.project_name}-daily-budget"
  budget_type  = "COST"
  limit_amount = var.daily_budget_limit
  limit_unit   = "USD"
  time_unit    = "DAILY"
  time_period_start = "2025-01-01_00:00"

  cost_filter {
    name = "Service"
    values = [
      "Amazon Elastic Compute Cloud - Compute",
      "Amazon Relational Database Service",
      "Amazon Elastic Container Service",
      "Amazon Elastic Container Registry (ECR)", 
      "Amazon Simple Storage Service",
      "Amazon CloudWatch",
      "Amazon Route 53",
      "Elastic Load Balancing",
      "AWS Certificate Manager",
      "AWS Secrets Manager"
    ]
  }

  # Budget notifications
  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                 = 50
    threshold_type            = "PERCENTAGE"
    notification_type         = "ACTUAL"
    subscriber_email_addresses = [var.billing_alert_email]
    subscriber_sns_topic_arns   = [aws_sns_topic.billing_alerts.arn]
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                 = 80
    threshold_type            = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = [var.billing_alert_email]
    subscriber_sns_topic_arns   = [aws_sns_topic.billing_alerts.arn]
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                 = 100
    threshold_type            = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = [var.billing_alert_email]
    subscriber_sns_topic_arns   = [aws_sns_topic.billing_alerts.arn]
  }


  tags = {
    Environment = var.environment
    Project     = var.project_name
    Purpose     = "DailyBudgetLimit"
  }
}

# Monthly Budget for additional oversight
resource "aws_budgets_budget" "monthly_limit" {
  name         = "${var.project_name}-monthly-budget"
  budget_type  = "COST"
  limit_amount = var.daily_budget_limit * 30  # 30 days worth
  limit_unit   = "USD"
  time_unit    = "MONTHLY"
  time_period_start = "2025-01-01_00:00"

  cost_filter {
    name = "Service"
    values = [
      "Amazon Elastic Compute Cloud - Compute",
      "Amazon Relational Database Service",
      "Amazon Elastic Container Service",
      "Amazon Elastic Container Registry (ECR)", 
      "Amazon Simple Storage Service",
      "Amazon CloudWatch",
      "Amazon Route 53",
      "Elastic Load Balancing",
      "AWS Certificate Manager",
      "AWS Secrets Manager"
    ]
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                 = 80
    threshold_type            = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = [var.billing_alert_email]
    subscriber_sns_topic_arns   = [aws_sns_topic.billing_alerts.arn]
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                 = 100
    threshold_type            = "PERCENTAGE"
    notification_type          = "FORECASTED"
    subscriber_email_addresses = [var.billing_alert_email]
    subscriber_sns_topic_arns   = [aws_sns_topic.billing_alerts.arn]
  }

  tags = {
    Environment = var.environment
    Project     = var.project_name
    Purpose     = "MonthlyBudgetLimit"
  }
}

# CloudWatch Billing Alarm for immediate alerts
resource "aws_cloudwatch_metric_alarm" "high_billing" {
  alarm_name          = "${var.project_name}-high-billing-alarm"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "EstimatedCharges"
  namespace           = "AWS/Billing"
  period              = "86400"  # 24 hours
  statistic           = "Maximum"
  threshold           = var.daily_budget_limit * 0.9  # Alert at 90% of daily limit
  alarm_description   = "This metric monitors AWS billing charges"
  alarm_actions       = [aws_sns_topic.billing_alerts.arn]
  treat_missing_data  = "notBreaching"

  dimensions = {
    Currency = "USD"
  }

  tags = {
    Environment = var.environment
    Project     = var.project_name
    Purpose     = "BillingAlarm"
  }
}

# Output billing protection information
output "billing_protection_info" {
  description = "Billing protection configuration details"
  value = {
    daily_budget_limit = var.daily_budget_limit
    monthly_budget_limit = var.daily_budget_limit * 30
    sns_topic_arn = aws_sns_topic.billing_alerts.arn
    budget_role_arn = aws_iam_role.budget_actions.arn
    cloudwatch_alarm = aws_cloudwatch_metric_alarm.high_billing.alarm_name
  }
}