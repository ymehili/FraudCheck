# GitHub Secrets Configuration for CheckGuard AI

This document contains the GitHub repository secrets needed for the CI/CD pipeline to deploy to AWS.

## Required GitHub Secrets

Configure the following secrets in your GitHub repository under Settings > Secrets and Variables > Actions:

### AWS Authentication
```
AWS_ROLE_ARN=arn:aws:iam::233442448767:role/checkguard-github-actions-role
AWS_REGION=us-east-2
```

## Infrastructure Information

The following infrastructure has been deployed to AWS:

### Application URLs
- **Application URL**: http://checkguard-alb-1390527999.us-east-2.elb.amazonaws.com
- **API URL**: http://checkguard-alb-1390527999.us-east-2.elb.amazonaws.com/api  
- **API Documentation**: http://checkguard-alb-1390527999.us-east-2.elb.amazonaws.com/docs

### Key Resources
- **ECS Cluster**: checkguard-cluster
- **ECR Repositories**: 
  - Backend: 233442448767.dkr.ecr.us-east-2.amazonaws.com/checkguard-backend
  - Frontend: 233442448767.dkr.ecr.us-east-2.amazonaws.com/checkguard-frontend
- **VPC**: vpc-06a36e4fd06bc2eeb
- **ALB**: checkguard-alb-1390527999.us-east-2.elb.amazonaws.com

### Secrets Manager
- Database credentials: arn:aws:secretsmanager:us-east-2:233442448767:secret:checkguard/database-37qpTA
- Redis credentials: arn:aws:secretsmanager:us-east-2:233442448767:secret:checkguard/redis-OvzeDf
- Clerk secrets: arn:aws:secretsmanager:us-east-2:233442448767:secret:checkguard/clerk-kiCPWF
- Gemini API: arn:aws:secretsmanager:us-east-2:233442448767:secret:checkguard/gemini-MkO8jH

## Setup Instructions

1. Go to your GitHub repository: https://github.com/your-org/checkguard-ai
2. Navigate to Settings > Secrets and Variables > Actions
3. Click "New repository secret" for each secret above
4. Enter the secret name and value exactly as shown

## Testing the Deployment

Once secrets are configured:

1. Create a new branch called `deploy` from main:
   ```bash
   git checkout -b deploy
   git push origin deploy
   ```

2. The GitHub Actions workflow will automatically:
   - Run tests
   - Build Docker images
   - Push to ECR
   - Deploy to ECS
   - Run database migrations
   - Perform health checks

3. Monitor the deployment at: https://github.com/your-org/checkguard-ai/actions

## Verification

After deployment completes, verify the application is running:
- Visit: http://checkguard-alb-1390527999.us-east-2.elb.amazonaws.com
- API health check: http://checkguard-alb-1390527999.us-east-2.elb.amazonaws.com/health
- API docs: http://checkguard-alb-1390527999.us-east-2.elb.amazonaws.com/docs

## AWS Account Information
- **Account ID**: 233442448767
- **Region**: us-east-2
- **Environment**: production