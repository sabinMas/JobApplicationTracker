#!/usr/bin/env pwsh
<#
.SYNOPSIS
  Deploy updated JobApplicationTracker Lambda code
.DESCRIPTION
  Rebuilds the deployment package and updates the Lambda function
.EXAMPLE
  .\\deploy-lambda-update.ps1
#>

$ErrorActionPreference = "Stop"

Write-Host "`n====== JobApplicationTracker Lambda Update ======" -ForegroundColor Cyan

# Configuration
$LAMBDA_FUNCTION = "jobtracker-api"
$S3_BUCKET = "jobtracker-documents-245091941294"
$S3_KEY = "deploy/lambda-deploy.zip"
$REGION = "us-east-1"
$BACKEND_DIR = "..\backend"
$DEPLOY_DIR = "..\deploy-package"
$ZIP_FILE = "..\lambda-deploy.zip"

Write-Host "`n1. Cleaning up old deployment package..." -ForegroundColor Yellow
if (Test-Path $DEPLOY_DIR) {
    Remove-Item -Recurse -Force $DEPLOY_DIR
}
New-Item -ItemType Directory -Path $DEPLOY_DIR | Out-Null

Write-Host "`n2. Installing dependencies..." -ForegroundColor Yellow
Push-Location $BACKEND_DIR
pip install -r requirements.txt -t ..\deploy-package --quiet
if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to install dependencies" -ForegroundColor Red
    exit 1
}
Pop-Location

Write-Host "`n3. Copying application code..." -ForegroundColor Yellow
Copy-Item -Recurse "$BACKEND_DIR\app" "$DEPLOY_DIR\app"
Copy-Item "$BACKEND_DIR\lambda_handler.py" "$DEPLOY_DIR\lambda_handler.py"
Write-Host "   [OK] Copied app directory"
Write-Host "   [OK] Copied lambda_handler.py"

Write-Host "`n4. Creating deployment zip..." -ForegroundColor Yellow
if (Test-Path $ZIP_FILE) {
    Remove-Item $ZIP_FILE
}
$compress = @{
  Path = "$DEPLOY_DIR\*"
  CompressionLevel = "Fastest"
  DestinationPath = $ZIP_FILE
}
Compress-Archive @compress
$zipSize = (Get-Item $ZIP_FILE).Length / 1MB
Write-Host "   [OK] Created $ZIP_FILE (Size: $([Math]::Round($zipSize, 2)) MB)"

Write-Host "`n5. Uploading to S3..." -ForegroundColor Yellow
& "C:\Program Files\Amazon\AWSCLIV2\aws.exe" s3 cp $ZIP_FILE "s3://$S3_BUCKET/$S3_KEY" --region $REGION
if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to upload to S3" -ForegroundColor Red
    exit 1
}
Write-Host "   ✓ Uploaded to $S3_BUCKET/$S3_KEY"

Write-Host "`n6. Updating Lambda function..." -ForegroundColor Yellow
& "C:\Program Files\Amazon\AWSCLIV2\aws.exe" lambda update-function-code `
  --function-name $LAMBDA_FUNCTION `
  --s3-bucket $S3_BUCKET `
  --s3-key $S3_KEY `
  --region $REGION
if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to update Lambda" -ForegroundColor Red
    exit 1
}
Write-Host "   ✓ Lambda update initiated"

Write-Host "`n7. Waiting for deployment to complete..." -ForegroundColor Yellow
$maxAttempts = 30
$attempt = 0
while ($attempt -lt $maxAttempts) {
    $status = & "C:\Program Files\Amazon\AWSCLIV2\aws.exe" lambda get-function `
      --function-name $LAMBDA_FUNCTION `
      --region $REGION `
      --query 'Configuration.LastUpdateStatus' `
      --output text
    
    if ($status -eq "Successful") {
        Write-Host "   ✓ Deployment successful"
        break
    }
    
    Write-Host "   Status: $status... (waiting)" -ForegroundColor Gray
    Start-Sleep -Seconds 2
    $attempt++
}

if ($attempt -ge $maxAttempts) {
    Write-Host "   ✗ Deployment timed out" -ForegroundColor Red
    exit 1
}

Write-Host "`n8. Verifying Lambda function..." -ForegroundColor Yellow
$config = & "C:\Program Files\Amazon\AWSCLIV2\aws.exe" lambda get-function `
  --function-name $LAMBDA_FUNCTION `
  --region $REGION `
  --query 'Configuration.[State,Runtime,MemorySize,Timeout]' `
  --output text

Write-Host "   Lambda Config: $config"

Write-Host "`n9. Testing Lambda with CLI invocation..." -ForegroundColor Yellow
$testPayload = '{\"requestContext\":{\"http\":{\"method\":\"GET\",\"path\":\"/health\"}},\"rawPath\":\"/health\",\"headers\":{}}'
& "C:\Program Files\Amazon\AWSCLIV2\aws.exe" lambda invoke `
  --function-name $LAMBDA_FUNCTION `
  --payload $testPayload `
  --cli-binary-format raw-in-base64-out `
  "$env:TEMP\lambda-test.json" `
  --region $REGION | Out-Null

$response = Get-Content "$env:TEMP\lambda-test.json" | ConvertFrom-Json
if ($response.statusCode -eq 200 -or $response.FunctionError -eq $null) {
    Write-Host "   ✓ Lambda responding (status code: $($response.statusCode))"
} else {
    Write-Host "   ⚠ Lambda returned: $($response.FunctionError)" -ForegroundColor Yellow
}

Write-Host "`n10. Checking CloudWatch logs..." -ForegroundColor Yellow
$recentLogs = & "C:\Program Files\Amazon\AWSCLIV2\aws.exe" logs tail "/aws/lambda/$LAMBDA_FUNCTION" --since 30s --region $REGION 2>&1 | Select-Object -First 5
if ($recentLogs) {
    Write-Host "    Recent log entries:"
    $recentLogs | ForEach-Object { Write-Host "    $_" }
} else {
    Write-Host "    (No recent logs yet)"
}

Write-Host "`n====== Deployment Complete ✓ ======" -ForegroundColor Green
Write-Host "`nFunction URL: https://slysl7v476awcx4754dv5osg3e0jjzqf.lambda-url.us-east-1.on.aws/"
Write-Host "`nNext steps:"
Write-Host "  1. Test with: curl https://slysl7v476awcx4754dv5osg3e0jjzqf.lambda-url.us-east-1.on.aws/health"
Write-Host "  2. Check logs: aws logs tail /aws/lambda/jobtracker-api --follow"
Write-Host "  3. Update frontend with VITE_API_URL"
Write-Host ""
