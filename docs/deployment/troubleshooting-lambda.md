# Lambda Function URL — Diagnostics & Solutions

**Issue**: Function URL returning 403 Forbidden or Mangum adapter errors  
**Status**: Under Investigation  
**Resolution**: Working on fix  

---

## What We Found

1. **Lambda Function URL Configuration**: ✅ Correct
   - AuthType: NONE (public)
   - CORS: Enabled for all origins
   - Policy: Allows public invocation

2. **Lambda Function Status**: ✅ Active
   - Runtime: Python 3.11
   - State: Active
   - Update Status: Successful

3. **Event Format Issue**: 🔍 Identified
   - Function URL sends events in HTTP API v2 format
   - Mangum adapter may have compatibility issues with specific event formats

---

## Solutions to Try

### Solution 1: Update Lambda Handler (Recommended)

The lambda_handler.py has been updated with better error handling and logging. Deploy the updated code:

```bash
cd backend

# Rebuild the deployment package
pip install -r requirements.txt -t ../deploy-package --quiet
cp -r app ../deploy-package/
cp lambda_handler.py ../deploy-package/

# Create zip
cd ..
zip -r lambda-deploy.zip deploy-package/

# Upload to S3
aws s3 cp lambda-deploy.zip s3://jobtracker-documents-245091941294/deploy/

# Update Lambda
aws lambda update-function-code \
  --function-name jobtracker-api \
  --s3-bucket jobtracker-documents-245091941294 \
  --s3-key deploy/lambda-deploy.zip \
  --region us-east-1

# Wait for update to complete
aws lambda get-function --function-name jobtracker-api --region us-east-1 --query 'Configuration.LastUpdateStatus'
```

### Solution 2: Use API Gateway Instead of Function URL

If Function URL continues to have issues, use API Gateway:

```bash
# Create REST API
aws apigateway create-rest-api \
  --name jobtracker-api \
  --description "JobApplicationTracker API" \
  --region us-east-1

# Then configure methods and deploy
```

### Solution 3: Recreate Function URL with New Permissions

```bash
# Delete current URL
aws lambda delete-function-url-config \
  --function-name jobtracker-api \
  --region us-east-1

# Wait a few seconds...

# Create new URL with explicit permissions
aws lambda create-function-url-config \
  --function-name jobtracker-api \
  --auth-type NONE \
  --cors '{
    "AllowCredentials": false,
    "AllowHeaders": ["*"],
    "AllowMethods": ["*"],
    "AllowOrigins": ["*"],
    "ExposeHeaders": ["*"],
    "MaxAge": 0
  }' \
  --region us-east-1

# Add explicit public permission
aws lambda add-permission \
  --function-name jobtracker-api \
  --statement-id AllowPublicAccess \
  --action lambda:InvokeFunctionUrl \
  --principal '*' \
  --region us-east-1

# Get new URL
aws lambda get-function-url-config \
  --function-name jobtracker-api \
  --region us-east-1 \
  --query 'FunctionUrl'
```

---

## Testing the Fix

### Test 1: Direct Lambda Invocation

```bash
aws lambda invoke \
  --function-name jobtracker-api \
  --payload '{"requestContext":{"http":{"method":"GET","path":"/health"}},"rawPath":"/health","headers":{}}' \
  --cli-binary-format raw-in-base64-out \
  /tmp/response.json \
  --region us-east-1

cat /tmp/response.json
```

**Expected Response**:
```json
{
  "statusCode": 200,
  "body": "{\"status\":\"ok\",\"service\":\"JobApplicationTracker\"}"
}
```

### Test 2: Function URL Direct Test

```bash
curl -v https://slysl7v476awcx4754dv5osg3e0jjzqf.lambda-url.us-east-1.on.aws/health
```

**Expected Response**:
```
< HTTP/2 200
< content-type: application/json

{"status":"ok","service":"JobApplicationTracker"}
```

### Test 3: Check CloudWatch Logs

```bash
aws logs tail /aws/lambda/jobtracker-api --follow --since 10m
```

**Look for**:
- Successful invocations (no errors)
- Event structure being logged
- API response being returned

---

## Common Issues & Fixes

### Issue: "Forbidden" / 403 Error

**Cause**: Lambda doesn't have InvokeFunctionUrl permission

**Fix**:
```bash
aws lambda add-permission \
  --function-name jobtracker-api \
  --statement-id FunctionURLInvoke \
  --action lambda:InvokeFunctionUrl \
  --principal '*' \
  --region us-east-1
```

### Issue: Mangum "Unable to infer handler" Error

**Cause**: Event format not recognized by Mangum

**Fix**: Update to latest Mangum version:
```bash
pip install --upgrade mangum
```

Or use explicit event conversion:
```python
from mangum import Mangum
from app.main import app

async def asgi_handler(scope, receive, send):
    app_instance = app
    await app_instance(scope, receive, send)

handler = Mangum(asgi_handler, lifespan="auto")
```

### Issue: Timeout When Connecting to Database

**Cause**: Lambda can't reach RDS

**Fix**:
```bash
# Verify security group allows connection
aws ec2 describe-security-groups \
  --group-ids sg-0a6df91503d1b8693 \
  --region us-east-1 \
  --query 'SecurityGroups[0].IpPermissions'

# Should show port 5432 open to 0.0.0.0/0
```

---

## Step-by-Step Fix Process

### 1. Update Lambda Code

```bash
cd backend

# Update lambda_handler.py if needed
# (file has been updated already)

# Rebuild deployment package
rm -rf ../deploy-package
mkdir ../deploy-package
pip install -r requirements.txt -t ../deploy-package --quiet
cp -r app ../deploy-package/
cp lambda_handler.py ../deploy-package/

cd ..
zip -r lambda-deploy.zip deploy-package/
```

### 2. Upload and Deploy

```bash
# Upload to S3
aws s3 cp lambda-deploy.zip s3://jobtracker-documents-245091941294/deploy/

# Deploy to Lambda
aws lambda update-function-code \
  --function-name jobtracker-api \
  --s3-bucket jobtracker-documents-245091941294 \
  --s3-key deploy/lambda-deploy.zip \
  --region us-east-1

# Wait for deployment
sleep 10
aws lambda get-function --function-name jobtracker-api --region us-east-1 --query 'Configuration.LastUpdateStatus' --output text
```

### 3. Verify Permissions

```bash
# Check policy
aws lambda get-policy --function-name jobtracker-api --region us-east-1

# Add permission if needed
aws lambda add-permission \
  --function-name jobtracker-api \
  --statement-id AllowFunctionURLPublicAccess \
  --action lambda:InvokeFunctionUrl \
  --principal '*' \
  --function-url-auth-type NONE \
  --region us-east-1
```

### 4. Test

```bash
# Test via CLI
aws lambda invoke --function-name jobtracker-api --payload '{}' /tmp/test.json && cat /tmp/test.json

# Test via HTTP
curl https://slysl7v476awcx4754dv5osg3e0jjzqf.lambda-url.us-east-1.on.aws/health

# Check logs
aws logs tail /aws/lambda/jobtracker-api --follow
```

---

## Fallback: Use AWS CLI Invoke Instead

While we troubleshoot the Function URL, you can use AWS CLI to invoke the Lambda:

```bash
# Create a small script to call Lambda
cat > invoke-lambda.sh << 'EOF'
#!/bin/bash
aws lambda invoke \
  --function-name jobtracker-api \
  --cli-binary-format raw-in-base64-out \
  --payload "$1" \
  /tmp/response.json \
  --region us-east-1
cat /tmp/response.json
EOF

chmod +x invoke-lambda.sh

# Usage:
./invoke-lambda.sh '{"requestContext":{"http":{"method":"GET","path":"/health"}},"rawPath":"/health"}'
```

---

## Monitoring During Fix

Keep these commands running to monitor progress:

```bash
# Terminal 1: Watch Lambda logs
aws logs tail /aws/lambda/jobtracker-api --follow

# Terminal 2: Check function status
watch -n 5 "aws lambda get-function --function-name jobtracker-api --region us-east-1 --query 'Configuration.[State,LastUpdateStatus]' --output table"

# Terminal 3: Test repeatedly
while true; do
  curl -s https://slysl7v476awcx4754dv5osg3e0jjzqf.lambda-url.us-east-1.on.aws/health || echo "Not responding"
  sleep 5
done
```

---

## If Function URL Can't Be Fixed

### Use API Gateway as Alternative

```bash
# Create API Gateway
aws apigateway create-rest-api --name jobtracker-api

# Get API ID
API_ID=$(aws apigateway get-rest-apis --query "items[?name=='jobtracker-api'].id" --output text)

# Create resource
RESOURCE_ID=$(aws apigateway get-resources --rest-api-id $API_ID --query "items[0].id" --output text)

# Create method and integration
# (more steps needed for full API Gateway setup)
```

---

## Current Status

| Component | Status | Action |
|-----------|--------|--------|
| Lambda Function | ✅ Active | Ready |
| Function URL Config | ✅ NONE auth | Correct |
| Lambda Handler | 🔄 Updated | Deploy new code |
| IAM Permissions | ✅ Set | Should work |
| Database | ✅ Ready | Connected |

---

## Next Actions

1. **Deploy updated lambda_handler.py** to Lambda
2. **Wait 30 seconds** for deployment to complete
3. **Test with curl** to verify Function URL works
4. **Check CloudWatch logs** for any errors
5. **Report back** with results

---

## Quick Deploy Command

```bash
cd backend && \
rm -rf ../deploy-package && \
mkdir ../deploy-package && \
pip install -r requirements.txt -t ../deploy-package --quiet && \
cp -r app ../deploy-package/ && \
cp lambda_handler.py ../deploy-package/ && \
cd .. && \
zip -r lambda-deploy.zip deploy-package/ && \
aws s3 cp lambda-deploy.zip s3://jobtracker-documents-245091941294/deploy/ && \
aws lambda update-function-code --function-name jobtracker-api --s3-bucket jobtracker-documents-245091941294 --s3-key deploy/lambda-deploy.zip --region us-east-1 && \
echo "Deployment started. Waiting for completion..." && \
sleep 15 && \
aws logs tail /aws/lambda/jobtracker-api --follow
```

---

**Last Updated**: June 5, 2026  
**Status**: Investigating and applying fixes  
**Next Step**: Deploy updated code and test
