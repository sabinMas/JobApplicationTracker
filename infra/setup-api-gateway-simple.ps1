#!/usr/bin/env pwsh
# Simple API Gateway setup

$ErrorActionPreference = "Stop"
$REGION = "us-east-1"
$LAMBDA_FUNCTION = "jobtracker-api"
$ACCOUNT_ID = "245091941294"

Write-Host "`nSetting up API Gateway..." -ForegroundColor Cyan

# Create REST API
Write-Host "Creating REST API..." -ForegroundColor Yellow
$api = & "C:\Program Files\Amazon\AWSCLIV2\aws.exe" apigateway create-rest-api `
  --name jobtracker-api `
  --description "JobApplicationTracker API" `
  --region $REGION | ConvertFrom-Json

$API_ID = $api.id
Write-Host "   API ID: $API_ID"

# Get root resource
Write-Host "Getting root resource..." -ForegroundColor Yellow
$resources = & "C:\Program Files\Amazon\AWSCLIV2\aws.exe" apigateway get-resources `
  --rest-api-id $API_ID `
  --region $REGION | ConvertFrom-Json

$RESOURCE_ID = $resources.items[0].id
Write-Host "   Resource ID: $RESOURCE_ID"

# Create ANY method
Write-Host "Creating ANY method..." -ForegroundColor Yellow
& "C:\Program Files\Amazon\AWSCLIV2\aws.exe" apigateway put-method `
  --rest-api-id $API_ID `
  --resource-id $RESOURCE_ID `
  --http-method ANY `
  --authorization-type NONE `
  --region $REGION | Out-Null

# Create Lambda integration
Write-Host "Creating Lambda integration..." -ForegroundColor Yellow
$uri = "arn:aws:apigateway:$REGION`:lambda:path/2015-03-31/functions/arn:aws:lambda:$REGION`:$ACCOUNT_ID`:function:$LAMBDA_FUNCTION/invocations"

& "C:\Program Files\Amazon\AWSCLIV2\aws.exe" apigateway put-integration `
  --rest-api-id $API_ID `
  --resource-id $RESOURCE_ID `
  --http-method ANY `
  --type AWS_PROXY `
  --integration-http-method POST `
  --uri $uri `
  --region $REGION | Out-Null

# Deploy
Write-Host "Deploying API..." -ForegroundColor Yellow
& "C:\Program Files\Amazon\AWSCLIV2\aws.exe" apigateway create-deployment `
  --rest-api-id $API_ID `
  --stage-name prod `
  --description "Production" `
  --region $REGION | Out-Null

# Get URL
Write-Host "Getting invoke URL..." -ForegroundColor Yellow
$stage = & "C:\Program Files\Amazon\AWSCLIV2\aws.exe" apigateway get-stage `
  --rest-api-id $API_ID `
  --stage-name prod `
  --region $REGION | ConvertFrom-Json

$API_URL = $stage.invokeUrl

# Add Lambda permission
Write-Host "Adding Lambda permission..." -ForegroundColor Yellow
& "C:\Program Files\Amazon\AWSCLIV2\aws.exe" lambda add-permission `
  --function-name $LAMBDA_FUNCTION `
  --statement-id AllowAPIGatewayInvoke `
  --action lambda:InvokeFunction `
  --principal apigateway.amazonaws.com `
  --source-arn "arn:aws:execute-api:$REGION`:$ACCOUNT_ID`:$API_ID/*/*" `
  --region $REGION 2>&1 | Out-Null

# Test
Write-Host "`nTesting API..." -ForegroundColor Yellow
Start-Sleep -Seconds 3

try {
    $response = Invoke-WebRequest -Uri "$API_URL/health" -UseBasicParsing -TimeoutSec 10 -ErrorAction Stop
    Write-Host "   [OK] API responding (Status: $($response.StatusCode))"
    $content = $response.Content | ConvertFrom-Json
    Write-Host "   Response: $($content | ConvertTo-Json -Compress)"
} catch {
    Write-Host "   [WARNING] Could not reach API yet: $_"
}

Write-Host "`n========== API Gateway Ready ==========" -ForegroundColor Green
Write-Host "`nInvoke URL: $API_URL`n"
Write-Host "Update your frontend:"
Write-Host "  VITE_API_URL=$API_URL`n"
Write-Host "Test endpoints:"
Write-Host "  curl $API_URL/health"
Write-Host "  curl $API_URL/api/jobs"
Write-Host "  curl -X POST $API_URL/api/jobs/sync"
Write-Host ""
