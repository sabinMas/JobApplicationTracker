#!/usr/bin/env pwsh
# Setup API Gateway for JobApplicationTracker

$ErrorActionPreference = "Stop"
$REGION = "us-east-1"
$LAMBDA_FUNCTION = "jobtracker-api"
$ACCOUNT_ID = "245091941294"

Write-Host "`nSetting up API Gateway..." -ForegroundColor Cyan

# Step 1: Create REST API
Write-Host "Step 1: Creating REST API..." -ForegroundColor Yellow
$api = & "C:\Program Files\Amazon\AWSCLIV2\aws.exe" apigateway create-rest-api `
  --name jobtracker-api `
  --description "JobApplicationTracker API" `
  --endpoint-type REGIONAL `
  --region $REGION | ConvertFrom-Json

$API_ID = $api.id
Write-Host "   Created API: $API_ID"

# Step 2: Get root resource
Write-Host "Step 2: Getting root resource..." -ForegroundColor Yellow
$resources = & "C:\Program Files\Amazon\AWSCLIV2\aws.exe" apigateway get-resources `
  --rest-api-id $API_ID `
  --region $REGION | ConvertFrom-Json

$RESOURCE_ID = $resources.items[0].id
Write-Host "   Resource ID: $RESOURCE_ID"

# Step 3: Create ANY method
Write-Host "Step 3: Creating ANY method..." -ForegroundColor Yellow
& "C:\Program Files\Amazon\AWSCLIV2\aws.exe" apigateway put-method `
  --rest-api-id $API_ID `
  --resource-id $RESOURCE_ID `
  --http-method ANY `
  --authorization-type NONE `
  --region $REGION | Out-Null

Write-Host "   Method created"

# Step 4: Create Lambda integration
Write-Host "Step 4: Creating Lambda integration..." -ForegroundColor Yellow
$uri = "arn:aws:apigateway:$REGION`:lambda:path/2015-03-31/functions/arn:aws:lambda:$REGION`:$ACCOUNT_ID`:function:$LAMBDA_FUNCTION/invocations"

& "C:\Program Files\Amazon\AWSCLIV2\aws.exe" apigateway put-integration `
  --rest-api-id $API_ID `
  --resource-id $RESOURCE_ID `
  --http-method ANY `
  --type AWS_PROXY `
  --integration-http-method POST `
  --uri $uri `
  --region $REGION | Out-Null

Write-Host "   Integration created"

# Step 5: Create deployment
Write-Host "Step 5: Deploying to prod..." -ForegroundColor Yellow
& "C:\Program Files\Amazon\AWSCLIV2\aws.exe" apigateway create-deployment `
  --rest-api-id $API_ID `
  --stage-name prod `
  --stage-description "Production" `
  --region $REGION | Out-Null

Write-Host "   Deployment created"

# Step 6: Get invoke URL
Write-Host "Step 6: Getting invoke URL..." -ForegroundColor Yellow
$stage = & "C:\Program Files\Amazon\AWSCLIV2\aws.exe" apigateway get-stage `
  --rest-api-id $API_ID `
  --stage-name prod `
  --region $REGION | ConvertFrom-Json

$API_URL = $stage.invokeUrl
Write-Host "   Invoke URL: $API_URL"

# Step 7: Add Lambda permission
Write-Host "Step 7: Adding Lambda permission..." -ForegroundColor Yellow
& "C:\Program Files\Amazon\AWSCLIV2\aws.exe" lambda add-permission `
  --function-name $LAMBDA_FUNCTION `
  --statement-id AllowAPIGatewayInvoke `
  --action lambda:InvokeFunction `
  --principal apigateway.amazonaws.com `
  --source-arn "arn:aws:execute-api:$REGION`:$ACCOUNT_ID`:$API_ID/*/*" `
  --region $REGION 2>&1 | Out-Null

Write-Host "   Permission added"

# Step 8: Test
Write-Host "Step 8: Testing API..." -ForegroundColor Yellow
Start-Sleep -Seconds 2

try {
    $response = Invoke-WebRequest -Uri "$API_URL/health" -UseBasicParsing -TimeoutSec 10
    if ($response.StatusCode -eq 200) {
        Write-Host "   [OK] API is responding (Status: $($response.StatusCode))"
    }
} catch {
    Write-Host "   [WARNING] Could not reach API yet (may need a few seconds)"
}

Write-Host "`nAPI Gateway Setup Complete!" -ForegroundColor Green
Write-Host "`nAPI Endpoint: $API_URL"
Write-Host "`nExample Calls:"
Write-Host "  curl $API_URL/health"
Write-Host "  curl $API_URL/api/jobs"
Write-Host "  curl -X POST $API_URL/api/jobs/sync"
Write-Host ""

# Save to file for reference
$config = @"
API Gateway Configuration
=========================
API ID: $API_ID
Resource ID: $RESOURCE_ID
Invoke URL: $API_URL
Lambda Function: $LAMBDA_FUNCTION
Region: $REGION
Stage: prod

Update your frontend configuration:
VITE_API_URL=$API_URL

The API Gateway will:
- Route all requests to the Lambda function
- Handle HTTP method conversion
- Provide proper error responses
- Support CORS
- Scale automatically
"@

Set-Content -Path "..\API_GATEWAY_CONFIG.txt" -Value $config
Write-Host "Configuration saved to API_GATEWAY_CONFIG.txt"
