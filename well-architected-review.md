# GitHub Project Health Monitor - Well-Architected Review

## Architecture

Browser user
   |
   v
API Gateway HTTP API
GET /health
   |
   v
AWS Lambda
github-project-health-monitor
Runs under LabRole
   |
   |-- Reads GitHub token and repo config from AWS Secrets Manager
   |
   |-- Calls GitHub REST API for microsoft/vscode
   |
   v
Returns JSON health report:
repository name, health score, status, open issues, recent commits, stars, forks, and last checked time

## Three architecture decisions

1. API Gateway HTTP API over Lambda Function URL

I chose API Gateway HTTP API because it gives a browser-accessible public HTTPS endpoint for /health. I rejected Lambda Function URL with AWS_IAM because it requires SigV4 signing and is not simple to open directly in a browser. Pillar: Operational excellence.

2. Secrets Manager over hard-coded API key

I chose AWS Secrets Manager for the GitHub token and repo configuration. I rejected hard-coding the token in Lambda code, Terraform variables, or environment literals because that could expose the secret in the repo or Terraform state. Pillar: Security.

3. Lambda over EC2 or ECS/Fargate

I chose Lambda because the monitor is small, event-driven, and mostly idle. I rejected EC2 or containers because they add more operational work and can cost more while idle. Pillar: Cost optimization.

## Findings and replies

1. Finding: The public API endpoint has no application-level authentication.

Reply: Accept. It is acceptable for the classroom demo, but production should add an authorizer, API key, or rate limiting.

2. Finding: The health report is returned to the browser but not stored as history.

Reply: Accept. I will fix this by storing each report in DynamoDB on-demand.

3. Finding: There are CloudWatch logs, but no alarm or dashboard yet.

Reply: Accept. Logs are enough for the current phase, but alarms should be added later.

4. Finding: LabRole is broad and not least-privilege.

Reply: Push back for this course because Learner Lab requires using LabRole. In production, I would create a least-privilege Lambda role.