# AWS Serverless Deployment Guide

**Last Updated**: June 10, 2026  
**Architecture**: Lambda (API) + ECS Fargate (Worker) + SQS + EventBridge

---

## Architecture

```
              ┌──────────────┐
  Vercel  ──► │ API Gateway  │ ──► Lambda (FastAPI + Mangum)
              │ HTTP API v2  │          │
              └──────────────┘          │ enqueue
                                        ▼
                               ┌─────────────────┐
  EventBridge (8AM EST) ──────►│   SQS Queue     │
        ↓ invoke Lambda        │ (scrape/apply)  │
        └──► /run-pipeline     └────────┬────────┘
                                        │ poll
                                        ▼
                               ┌─────────────────┐
                               │  ECS Fargate    │ (min=0, max=3)
                               │  Worker         │ Playwright + MCP
                               │  (FARGATE_SPOT) │
                               └─────────────────┘
```

**Cost estimate**: ~$5–15/month at 10 apps/day ($185 credits available)

---

## Prerequisites

- AWS CLI configured (`aws configure`) with account 245091941294
- Docker Desktop running
- PowerShell 7+
- SSM Parameters set (one-time):
  ```powershell
  aws ssm put-parameter --name /jobtracker/subnet-id --value "subnet-xxx" --type String
  aws ssm put-parameter --name /jobtracker/security-group-id --value "sg-xxx" --type String
  ```

---

## Deploy Steps

### 1. Build and push Lambda image

```powershell
.\infra\scripts\deploy-lambda.ps1
```

### 2. Build and push Worker image

```powershell
# Login to ECR
$ECR = "245091941294.dkr.ecr.us-east-1.amazonaws.com"
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin $ECR

# Build and push
docker build -f Dockerfile.worker -t jobtracker-worker .
docker tag jobtracker-worker "${ECR}/jobtracker-worker:latest"
docker push "${ECR}/jobtracker-worker:latest"
```

### 3. Deploy CloudFormation stack

```powershell
.\infra\scripts\deploy-stack.ps1 `
  -DatabaseUrl "postgresql+asyncpg://user:pass@host:5432/jobtracker" `
  -BudgetEmail "your@email.com" `
  -AllowedOrigins "http://localhost:5173"
```

### 4. Verify

```powershell
# Check Lambda
aws lambda invoke --function-name jobtracker-api --payload '{"rawPath":"/health","requestContext":{"http":{"method":"GET","path":"/health"}},"version":"2.0","routeKey":"$default"}' /dev/stdout

# Check API Gateway endpoint
aws cloudformation describe-stacks --stack-name jobtracker --query 'Stacks[0].Outputs'
```

---

## Key Resources

| Resource | Name/ARN |
|----------|----------|
| Lambda | `jobtracker-api` |
| API Gateway | `jobtracker-api` (HTTP API) |
| SQS Queue | `jobtracker-scraping-tasks` |
| SQS DLQ | `jobtracker-scraping-tasks-dlq` |
| ECS Cluster | `jobtracker-cluster` |
| ECS Service | `worker-service` (min=0, max=3) |
| EventBridge | `jobtracker-daily-pipeline` (8 AM EST) |
| Budget | `jobtracker-monthly` ($30/mo, 80% alert) |
| ECR (Lambda) | `jobtracker-api-lambda` |
| ECR (Worker) | `jobtracker-worker` |
| S3 | `jobtracker-documents-245091941294` |

---

## Environment Variables

### Lambda (set via CloudFormation)
| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL async connection string |
| `ALLOWED_ORIGINS` | Comma-separated CORS origins |
| `SQS_QUEUE_URL` | Auto-resolved from CloudFormation |
| `S3_BUCKET` | Document storage bucket |
| `ENVIRONMENT` | `production` or `staging` |

### Worker (set via CloudFormation)
Same as Lambda plus worker uses IAM task role for AWS service access.

### Frontend (Vercel)
| Variable | Description |
|----------|-------------|
| `VITE_API_URL` | API Gateway endpoint (no trailing slash) |

---

## Auto-Scaling Behavior

The worker service runs at **0 tasks** when idle. When messages appear in SQS:

- **Scale out**: 1 task per 5 messages (target tracking)
- **Scale-out cooldown**: 60 seconds
- **Scale-in cooldown**: 300 seconds (5 min)
- **Max tasks**: 3
- **Capacity provider**: 80% FARGATE_SPOT, 20% FARGATE

After 5 minutes of empty queue, the worker exits and ECS scales to 0.

---

## EventBridge Schedule

- **Cron**: `0 8 * * ? *` (daily 8:00 AM)
- **Timezone**: America/New_York (EST/EDT)
- **Target**: Lambda → `POST /api/scheduler/run-pipeline`
- **Pipeline stages**: Discover → Score → Enrich → Tailor → Submit

---

## Monitoring

```powershell
# Lambda logs
aws logs tail /aws/lambda/jobtracker-api --follow

# Worker logs
aws logs tail /ecs/jobtracker-worker --follow

# Queue depth
aws sqs get-queue-attributes --queue-url <url> --attribute-names ApproximateNumberOfMessagesVisible

# Pipeline run history
curl https://<api-url>/api/scheduler/pipeline-runs
```

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Lambda cold start slow | Increase MemorySize (512→1024 helps CPU too) |
| Worker not scaling up | Check CloudWatch alarm, verify SQS metric |
| CORS errors | Add frontend domain to `ALLOWED_ORIGINS` |
| EventBridge not firing | Check schedule status in EventBridge console |
| DLQ messages piling up | Inspect message bodies, check worker logs |
| Build fails (Playwright) | Worker uses `mcr.microsoft.com/playwright/python:v1.49.0-noble` — browsers pre-installed |

---

## Bedrock Model Access

AWS auto-enables serverless foundation models on first invocation. No manual
"Model Access" page submission needed. The Lambda and Worker roles include
`bedrock:InvokeModel` permissions for all foundation models.

Models used:
- **Haiku** (`anthropic.claude-3-haiku-20240307-v1:0`): Fast extraction, scoring
- **Sonnet** (`anthropic.claude-sonnet-4-20250514-v1:0`): Resume writing, complex reasoning
