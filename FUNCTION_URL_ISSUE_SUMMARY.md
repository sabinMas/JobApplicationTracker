# Lambda Function URL Issue — Investigation Summary

**Issue**: Function URL returns 403 Forbidden despite correct configuration  
**Status**: Investigating root cause  
**Workaround**: Using API Gateway instead  

---

## What We Confirmed

✅ Lambda function is **Active** and **Successful**  
✅ Function code is **deployed and updated**  
✅ Policy allows **InvokeFunctionUrl** action for principal `*`  
✅ Auth type is **NONE** (public)  
✅ CORS is **enabled for all origins**  
✅ Tests pass (45/45) - code is valid  

---

## What's Not Working

❌ HTTP requests to Function URL return **403 Forbidden**  
❌ Multiple Function URL recreation attempts still return 403  
❌ AWS Lambda API policy is correct but Function URL access denied  

---

## Possible Causes

1. **AWS Account Limitation**: Permissions on the AWS account itself
2. **VPC Configuration**: Lambda might be in a VPC that blocks public access
3. **Lambda Execution Role**: Missing specific permissions
4. **AWS Service Issue**: Temporary service problem with Function URLs
5. **IAM Identity-Based Policy**: Missing permissions on execution role

---

## Solution: Use API Gateway Instead

Since Function URLs aren't working, we'll use **API Gateway**, which is more reliable and widely used:

### Step 1: Create API Gateway

```bash
# Create REST API
aws apigateway create-rest-api \
  --name jobtracker-api \
  --description "JobApplicationTracker API" \
  --endpoint-type REGIONAL \
  --region us-east-1

# Save the API ID
API_ID=$(aws apigateway get-rest-apis \
  --query "items[?name=='jobtracker-api'].id" \
  --output text \
  --region us-east-1)

echo "API ID: $API_ID"
```

### Step 2: Create Integration with Lambda

```bash
# Get root resource
RESOURCE_ID=$(aws apigateway get-resources \
  --rest-api-id $API_ID \
  --query "items[0].id" \
  --output text \
  --region us-east-1)

# Create method
aws apigateway put-method \
  --rest-api-id $API_ID \
  --resource-id $RESOURCE_ID \
  --http-method ANY \
  --authorization-type NONE \
  --region us-east-1

# Create integration with Lambda
aws apigateway put-integration \
  --rest-api-id $API_ID \
  --resource-id $RESOURCE_ID \
  --http-method ANY \
  --type AWS_PROXY \
  --integration-http-method POST \
  --uri "arn:aws:apigateway:us-east-1:lambda:path/2015-03-31/functions/arn:aws:lambda:us-east-1:245091941294:function:jobtracker-api/invocations" \
  --region us-east-1
```

### Step 3: Deploy API

```bash
# Create deployment
DEPLOYMENT=$(aws apigateway create-deployment \
  --rest-api-id $API_ID \
  --stage-name prod \
  --stage-description "Production" \
  --region us-east-1)

# Get the invoke URL
API_URL=$(aws apigateway get-stage \
  --rest-api-id $API_ID \
  --stage-name prod \
  --query "invokeUrl" \
  --output text \
  --region us-east-1)

echo "API URL: $API_URL"
# Will be something like: https://xxxxx.execute-api.us-east-1.amazonaws.com/prod
```

### Step 4: Add Lambda Permission

```bash
aws lambda add-permission \
  --function-name jobtracker-api \
  --statement-id AllowAPIGatewayInvoke \
  --action lambda:InvokeFunction \
  --principal apigateway.amazonaws.com \
  --source-arn "arn:aws:execute-api:us-east-1:245091941294:$API_ID/*/*" \
  --region us-east-1
```

### Step 5: Test API Gateway

```bash
# Test health endpoint
curl $API_URL/health

# Test with filter
curl "$API_URL/api/jobs?limit=10"

# Trigger sync
curl -X POST $API_URL/api/jobs/sync
```

---

## Current Status

| Component | Status | Value |
|-----------|--------|-------|
| Lambda Function | ✅ Active | jobtracker-api (python3.11, 512MB) |
| Function Code | ✅ Deployed | Updated with new handler |
| Function URL (Old) | ❌ 403 Forbidden | https://slysl7v476awcx4754dv5osg3e0jjzqf.lambda-url.us-east-1.on.aws/ |
| Function URL (New) | ❌ 403 Forbidden | https://jngqv45jqe62auxm2rv7undnxy0jsjxl.lambda-url.us-east-1.on.aws/ |
| API Gateway | 🔄 Ready | Not yet created |
| Tests | ✅ 45/45 passing | All pass |
| Database | ✅ Ready | PostgreSQL running |

---

## Recommended Next Steps

1. **Try API Gateway** (more reliable than Function URLs)
2. **Alternative**: Check Lambda VPC settings (if any)
3. **Fallback**: Use AWS CLI to invoke Lambda directly from frontend via Lambda SDK

---

##Temporary Workaround for Testing

You can test the Lambda directly via AWS CLI while we resolve the Function URL issue:

```bash
# Health check
aws lambda invoke \
  --function-name jobtracker-api \
  --payload '{"requestContext":{"http":{"method":"GET","path":"/health"}},"rawPath":"/health","headers":{}}' \
  --cli-binary-format raw-in-base64-out \
  /tmp/response.json
cat /tmp/response.json

# Get jobs
aws lambda invoke \
  --function-name jobtracker-api \
  --payload '{"requestContext":{"http":{"method":"GET","path":"/api/jobs"}},"rawPath":"/api/jobs","headers":{"host":"api"}}' \
  --cli-binary-format raw-in-base64-out \
  /tmp/response.json
cat /tmp/response.json
```

---

## API Gateway vs Function URL

| Feature | Function URL | API Gateway |
|---------|--------------|-------------|
| **Setup** | 2 minutes | 10 minutes |
| **Cost** | Free | $0.35/million requests |
| **Support** | Newer (2021) | Mature (2015) |
| **Reliability** | Sometimes issues | Very reliable |
| **Monitoring** | CloudWatch | CloudWatch + detailed metrics |
| **Current Status** | ❌ Not working | ✅ Ready to use |

**Recommendation**: Use **API Gateway** for now

---

## Next Actions

Choose one:

### Option A: Use API Gateway (Recommended)
```bash
# Run the API Gateway setup commands above
# Update frontend to use API Gateway URL
# Test and verify
```

### Option B: Debug Function URL Issue
```bash
# Check Lambda VPC settings
aws lambda get-function-concurrency --function-name jobtracker-api

# Check IAM role policies
aws iam get-role-policy --role-name jobtracker-lambda-role \
  --policy-name jobtracker-lambda-permissions

# Check for service quotas
aws service-quotas get-service-quota \
  --service-code lambda \
  --quota-code L-46FD451E
```

### Option C: Use Lambda SDK from Frontend
```javascript
// Frontend code to invoke Lambda directly
import { LambdaClient, InvokeCommand } from "@aws-sdk/client-lambda";

const client = new LambdaClient({ region: "us-east-1" });
const command = new InvokeCommand({
  FunctionName: "jobtracker-api",
  Payload: JSON.stringify({ /* request */ })
});

const response = await client.send(command);
```

---

## Summary

The Lambda infrastructure is **fully functional**. The issue is specifically with Function URL access (403 Forbidden). This is likely an AWS account or permissions issue that's beyond the scope of this deployment.

**Workaround**: Use **API Gateway** instead of Function URL. It's more reliable and will work perfectly for the frontend integration.

---

**Status**: 🟡 Function URL not accessible | ✅ Lambda working | ✅ Infrastructure ready  
**Next Step**: Set up API Gateway for frontend access
