# Phase 4 Deployment Guide

## Current Status

Phase 4 implementation (AgentCore scoring + Dashboard) is complete but deployment is blocked by a binary compatibility issue.

### ✅ What's Done
1. **Phase 4 Code**: AgentCore job scoring, Dashboard API (6 endpoints), auto-apply scoring integration
2. **Frontend**: Deployed to Vercel (https://jobapptracker-n60pbf6ah-sabinmas-projects.vercel.app)
3. **AWS Infrastructure**: Lambda function, S3 bucket, RDS database, IAM roles configured
4. **Database Migration Script**: `infra/add_scoring_to_jobs.sql` ready

### 🔴 Current Block
**Windows binary dependencies** in Lambda deployment package:
- Error: `Runtime.ImportModuleError: Unable to import module 'lambda_handler': No module named 'pydantic_core._pydantic_core'`
- Cause: `pydantic_core` compiled as Windows `.pyd` file, not compatible with AWS Lambda Linux environment
- Package built on Windows contains: `_pydantic_core.cp313-win_amd64.pyd`

## Solution: Rebuild on Linux

### Option 1: Using Docker (Recommended)

```bash
# Create a Docker container with Linux environment
docker run -it --rm -v $(pwd):/app python:3.13-slim /bin/bash

# Inside container
cd /app
mkdir -p deploy-package-linux
pip install -r infra/requirements-lambda.txt -t deploy-package-linux --platform manylinux2014_x86_64 --only-binary=:all:
cp -r backend/app deploy-package-linux/
cp backend/lambda_handler.py deploy-package-linux/
cd deploy-package-linux
zip -r ../lambda-deploy-linux.zip .
```

### Option 2: Using GitHub Actions CI/CD

Create `.github/workflows/deploy-lambda.yml`:
```yaml
name: Deploy Lambda

on:
  push:
    branches: [main]
    paths: ['backend/**', 'infra/**']

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Build deployment package
        run: |
          mkdir deploy-package
          pip install -r infra/requirements-lambda.txt -t deploy-package
          cp -r backend/app deploy-package/
          cp backend/lambda_handler.py deploy-package/
          cd deploy-package
          zip -r ../lambda-deploy-linux.zip .
      - name: Upload to S3
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1
      - name: Deploy Lambda
        run: |
          aws s3 cp lambda-deploy-linux.zip s3://jobtracker-documents-245091941294/deploy/
          aws lambda update-function-code --function-name jobtracker-api --s3-bucket jobtracker-documents-245091941294 --s3-key deploy/lambda-deploy-linux.zip --region us-east-1
```

### Option 3: Manual Linux Build

If you have access to a Linux machine (WSL, EC2, etc.):

```bash
# On Linux machine
cd /path/to/JobApplicationTracker
mkdir -p deploy-package-linux
pip install -r infra/requirements-lambda.txt -t deploy-package-linux
cp -r backend/app deploy-package-linux/
cp backend/lambda_handler.py deploy-package-linux/
cd deploy-package-linux
zip -r ../lambda-deploy-linux.zip .

# Upload and deploy
aws s3 cp lambda-deploy-linux.zip s3://jobtracker-documents-245091941294/deploy/
aws lambda update-function-code --function-name jobtracker-api --s3-bucket jobtracker-documents-245091941294 --s-key deploy/lambda-deploy-linux.zip --region us-east-1
```

## Complete Deployment Steps

### Step 1: Apply Database Migration

```sql
# Apply scoring columns to jobs table
psql postgresql://jobadmin:YOUR_DB_PASSWORD_HERE@YOUR_RDS_ENDPOINT_HERE:5432/jobtracker < infra/add_scoring_to_jobs.sql
```

Migration adds 6 columns:
- `ai_score` (1-10): Overall match score
- `score_breakdown` (JSON): Detailed scoring by category
- `strengths` (Text[]): Key matching strengths
- `concerns` (Text[]): Potential concerns
- `scoring_reasoning` (Text): AI reasoning for score
- `last_scored_at` (Timestamp)

### Step 2: Update Lambda Environment Variables

```bash
# Get real Cerebras API key from https://cerebras.ai
CEREBRAS_API_KEY="your-actual-key-here"

aws lambda update-function-configuration \
  --function-name jobtracker-api \
  --environment "Variables={
    S3_BUCKET=jobtracker-documents-245091941294,
    DATABASE_URL=postgresql+asyncpg://jobadmin:YOUR_DB_PASSWORD_HERE@YOUR_RDS_ENDPOINT_HERE:5432/jobtracker,
    ENVIRONMENT=production,
    CEREBRAS_API_KEY=$CEREBRAS_API_KEY,
    LOG_LEVEL=INFO,
    MIN_SCORE_TO_APPLY=8
  }" \
  --region us-east-1
```

### Step 3: Configure Vercel Frontend

1. Go to Vercel Dashboard → JobApplicationTracker project
2. Settings → Environment Variables
3. Add/Update: `VITE_API_URL=https://4elmr535rxhpo5ktgdaxrjejai0jyeie.lambda-url.us-east-1.on.aws`
4. Redeploy

### Step 4: Test End-to-End

```bash
# Test Lambda health
curl https://4elmr535rxhpo5ktgdaxrjejai0jyeie.lambda-url.us-east-1.on.aws/health

# Test dashboard endpoints
curl https://4elmr535rxhpo5ktgdaxrjejai0jyeie.lambda-url.us-east-1.on.aws/api/dashboard/health
curl https://4elmr535rxhpo5ktgdaxrjejai0jyeie.lambda-url.us-east-1.on.aws/api/dashboard/metrics?days=7

# Test frontend
open https://jobapptracker-n60pbf6ah-sabinmas-projects.vercel.app
```

## Phase 4 Features Ready

Once deployed, these features will be available:

### 1. AgentCore Job Scoring
- **AI Scoring**: 1-10 scale based on salary, skills, company, growth, location
- **Score Breakdown**: Detailed JSON with category weights and scores
- **Reasoning**: AI-generated explanation for each score
- **Strengths/Concerns**: Lists of matching strengths and potential concerns

### 2. Dashboard API (6 Endpoints)
- `/api/dashboard/metrics` - Overall application metrics
- `/api/dashboard/job-discovery` - Job source analysis
- `/api/dashboard/scoring-distribution` - Score breakdown
- `/api/dashboard/application-timeline` - Application progress
- `/api/dashboard/ats-performance` - ATS platform success rates
- `/api/dashboard/recommendations` - AI job recommendations

### 3. Auto-Apply Scoring Integration
- Filters jobs by minimum score (default: ≥8/10)
- Prioritizes high-score jobs for auto-application
- Logs scoring decisions for transparency

### 4. Visual Dashboard (Frontend)
- Real-time metrics with Recharts visualizations
- Score distribution charts
- Application timeline
- ATS performance comparison
- Job recommendation cards

## Troubleshooting

### Lambda Fails to Start
```bash
# Check logs
aws logs describe-log-streams --log-group-name "/aws/lambda/jobtracker-api" --region us-east-1 --order-by LastEventTime --descending --limit 5
aws logs get-log-events --log-group-name "/aws/lambda/jobtracker-api" --log-stream-name "2026/06/05/[$LATEST]..." --region us-east-1

# Test directly
aws lambda invoke --function-name jobtracker-api --invocation-type RequestResponse --region us-east-1 --log-type Tail --payload '{"requestContext": {"http": {"method": "GET", "path": "/health"}}}' output.txt
```

### Database Connection Issues
- Verify RDS instance is running
- Check security groups allow Lambda access (port 5432)
- Test connection: `psql "host=YOUR_RDS_ENDPOINT_HERE port=5432 dbname=jobtracker user=jobadmin password=YOUR_DB_PASSWORD_HERE"`

### Frontend API Errors
- Check browser console for CORS errors
- Verify `VITE_API_URL` is correct in Vercel
- Test API directly with curl

## Performance Optimization

### Lambda Configuration
- **Memory**: 512MB (adequate for FastAPI + DB connections)
- **Timeout**: 300 seconds (5 minutes for long operations)
- **Concurrency**: Consider setting reserved concurrency if high traffic expected

### Database Optimization
- Add indexes on new scoring columns for filtering
- Consider materialized views for dashboard queries
- Regular vacuum/analyze on jobs table

### Caching Strategy
- Implement Redis for frequently accessed dashboard data
- Cache job scoring results for 24 hours
- Use CloudFront CDN for static assets

## Monitoring & Alerts

### CloudWatch Alarms
- Lambda errors > 5% in 5 minutes
- Lambda duration > 250 seconds
- RDS CPU > 80%

### Dashboard Health Checks
- Daily automated test of all API endpoints
- Database connection monitoring
- Job scoring accuracy sampling

## Next Phases (Future)

### Phase 5: Advanced Analytics
- Predictive modeling of application success
- Salary negotiation recommendations
- Interview performance tracking

### Phase 6: Multi-User & Teams
- Team collaboration features
- Role-based access control
- Shared job boards

### Phase 7: Mobile App
- React Native mobile application
- Push notifications for job matches
- Quick apply from mobile

---

**Deployment Priority**: Fix Linux binary dependency → Apply DB migration → Update Lambda → Connect frontend → Test end-to-end

**Estimated Time**: 30-60 minutes once Linux build environment is available

**Success Criteria**: Lambda health endpoint returns 200, dashboard loads data, job scoring works


## ✅ BINARY COMPATIBILITY FIXED

A Linux-compatible deployment package has been built using Docker:

**Fixed Package**: `infra/lambda-deploy-linux-fixed.zip` (27 MB)

**Key Fix**: Contains `_pydantic_core.cpython-312-x86_64-linux-gnu.so` (Linux binary) instead of Windows `.pyd` file

**Build Method**: Docker-based build using `python:3.12-slim` image

## Updated Deployment Steps

### 1. Upload Fixed Package to S3
```bash
aws s3 cp infra/lambda-deploy-linux-fixed.zip s3://jobapptracker-deployments/lambda-deploy-linux-fixed.zip
```

### 2. Update Lambda Function
```bash
aws lambda update-function-code \
  --function-name jobapptracker-api \
  --s3-bucket jobapptracker-deployments \
  --s3-key lambda-deploy-linux-fixed.zip
```

### 3. Set Cerebras API Key
```bash
aws lambda update-function-configuration \
  --function-name jobapptracker-api \
  --environment "Variables={CEREBRAS_API_KEY=YOUR_CEREBRAS_API_KEY_HERE}"
```

### 4. Apply Database Migration
```sql
-- Connect to RDS and run:
\i infra/add_scoring_to_jobs.sql
```

### 5. Test Deployment
```bash
# Get Function URL
aws lambda get-function-url-config --function-name jobapptracker-api

# Test health endpoint (replace YOUR_URL)
curl https://YOUR_URL.lambda-url.us-east-1.on.aws/health
```

## Verification

Check package contains Linux binaries:
```bash
# List pydantic_core files in package
unzip -l infra/lambda-deploy-linux-fixed.zip | grep pydantic_core
```

Should show: `_pydantic_core.cpython-312-x86_64-linux-gnu.so` (Linux) ✅
Not: `_pydantic_core.cp313-win_amd64.pyd` (Windows) ❌

## Package Contents
- ✅ All dependencies compiled for Linux x86_64
- ✅ Python 3.12 compatible
- ✅ Amazon Linux 2023 compatible
- ✅ FastAPI + all routers included
- ✅ Lambda handler: `lambda_handler.handler`