\# GitHub Project Health Monitor - Well-Architected Review



\## Architecture



```mermaid

flowchart LR

&#x20;   U\[Browser user] --> A\[API Gateway HTTP API<br>GET /health]

&#x20;   A --> L\[AWS Lambda<br>github-project-health-monitor<br>Runs under LabRole]

&#x20;   L --> S\[AWS Secrets Manager<br>github-health-monitor/api-config]

&#x20;   L --> G\[GitHub REST API<br>microsoft/vscode]

&#x20;   L --> R\[JSON health report<br>score, status, issues, commits, stars, forks]

```



\## Three architecture decisions



1\. API Gateway HTTP API over Lambda Function URL  

&#x20;  I chose API Gateway HTTP API because it gives a browser-accessible public HTTPS endpoint for `/health`. I rejected Lambda Function URL with AWS\_IAM because it requires SigV4 signing and is not simple to open directly in a browser. Pillar: Operational excellence.



2\. Secrets Manager over hard-coded API key  

&#x20;  I chose AWS Secrets Manager for the GitHub token and repo configuration. I rejected hard-coding the token in Lambda code, Terraform variables, or environment literals because that could expose the secret in the repo or Terraform state. Pillar: Security.



3\. Lambda over EC2 or ECS/Fargate  

&#x20;  I chose Lambda because the monitor is small, event-driven, and mostly idle. I rejected EC2 or containers because they add more operational work and can cost more while idle. Pillar: Cost optimization.



\## Findings and replies



1\. Finding: The public API endpoint has no application-level authentication.  

&#x20;  Reply: Accept. It is acceptable for the classroom demo, but production should add an authorizer, API key, or rate limiting.



2\. Finding: The health report is returned to the browser but not stored as history.  

&#x20;  Reply: Accept. I will fix this by storing each report in DynamoDB on-demand.



3\. Finding: There are CloudWatch logs, but no alarm or dashboard yet.  

&#x20;  Reply: Accept. Logs are enough for the current phase, but alarms should be added later.



4\. Finding: LabRole is broad and not least-privilege.  

&#x20;  Reply: Push back for this course because Learner Lab requires using LabRole. In production, I would create a least-privilege Lambda role.

