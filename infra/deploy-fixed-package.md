# Fixed Linux Deployment Package - Manual Deployment Steps

## Package Created Successfully
✅ **File**: `infra/lambda-deploy-linux-fixed.zip` (27 MB)
✅ **Linux Compatibility**: Contains `_pydantic_core.cpython-312-x86_64-linux-gnu.so` (Linux binary)
✅ **Dependencies**: All requirements installed for Python 3.12 on Linux

## Manual Deployment Steps Required

### 1. Upload Package to S3
```bash
# Using AWS CLI (install first: https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)
aws s3 cp infra/lambda-deploy-linux-fixed.zip s3://jobapptracker-deployments/lambda-deploy-linux-fixed.zip
```

### 2. Update Lambda Function
```bash
# Update Lambda function code with new package
aws lambda update-function-code \
  --function-name jobapptracker-api \
  --s3-bucket jobapptracker-deployments \
  --s3-key lambda-deploy-linux-fixed.zip
```

### 3. Verify Lambda Update
```bash
# Check update status
aws lambda get-function --function-name jobapptracker-api

# Test health endpoint
# Get Function URL
aws lambda get-function-url-config --function-name jobapptracker-api

# Test with curl (replace URL with your actual Function URL)
curl https://[your-function-url].lambda-url.us-east-1.on.aws/health
```

### 4. Apply Database Migration
```bash
# Connect to RDS and run migration
# Using psql (install PostgreSQL client first)
psql -h [rds-endpoint] -U postgres -d jobapptracker -f infra/add_scoring_to_jobs.sql
```

### 5. Configure Environment Variables
Ensure Lambda has these environment variables:
- `DATABASE_URL`: PostgreSQL connection string
- `S3_BUCKET`: jobapptracker-documents
- `OPENAI_API_KEY`: Your OpenAI API key  
- `CEREBRAS_API_KEY`: YOUR_CEREBRAS_API_KEY_HERE
- `ALLOWED_ORIGINS`: https://jobapptracker-n60pbf6ah-sabinmas-projects.vercel.app,http://localhost:5173

### 6. Update Frontend Configuration
Update Vercel frontend (.env or environment variables):
```
VITE_API_URL=https://[your-lambda-function-url].lambda-url.us-east-1.on.aws
```

## Verification Checklist

- [ ] Lambda health endpoint returns `{"status": "ok"}`
- [ ] Database migration applied (check `jobs` table has new columns)
- [ ] Frontend can connect to API
- [ ] AgentCore scoring works (test with `/api/ai/score-job` endpoint)
- [ ] Dashboard endpoints work (`/api/dashboard/*`)

## Troubleshooting

If Lambda still has import errors:
1. Check CloudWatch logs for detailed error messages
2. Verify package contains Linux `.so` files, not Windows `.pyd` files
3. Ensure all dependencies are in the package root (not nested in subdirectories)

## Package Contents Verification
The fixed package now contains:
- ✅ `pydantic_core/_pydantic_core.cpython-312-x86_64-linux-gnu.so` (Linux binary)
- ✅ All Python dependencies compiled for Linux x86_64
- ✅ Application code in root directory
- ✅ Handler: `lambda_handler.handler`