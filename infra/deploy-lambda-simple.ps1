#!/usr/bin/env pwsh
# Simple Lambda deployment script

$ErrorActionPreference = "Stop"

Write-Host "`nDeploying Lambda Update..." -ForegroundColor Cyan

# Configuration
$LAMBDA_FUNCTION = "jobtracker-api"
$S3_BUCKET = "jobtracker-documents-245091941294"
$S3_KEY = "deploy/lambda-deploy.zip"
$REGION = "us-east-1"
$BACKEND_DIR = "..\backend"
$DEPLOY_DIR = "..\deploy-package"
$ZIP_FILE = "..\lambda-deploy.zip"

# Step 1: Clean
Write-Host "Step 1: Cleaning up..." -ForegroundColor Yellow
if (Test-Path $DEPLOY_DIR) { Remove-Item -Recurse -Force $DEPLOY_DIR }
New-Item -ItemType Directory -Path $DEPLOY_DIR | Out-Null

# Step 2: Install dependencies
Write-Host "Step 2: Installing dependencies..." -ForegroundColor Yellow
Push-Location $BACKEND_DIR
pip install -r requirements.txt -t ..\deploy-package --quiet
Pop-Location

# Step 3: Copy code
Write-Host "Step 3: Copying code..." -ForegroundColor Yellow
Copy-Item -Recurse "$BACKEND_DIR\app" "$DEPLOY_DIR\app"
Copy-Item "$BACKEND_DIR\lambda_handler.py" "$DEPLOY_DIR\lambda_handler.py"

# Step 4: Create zip
Write-Host "Step 4: Creating zip package..." -ForegroundColor Yellow
if (Test-Path $ZIP_FILE) { Remove-Item $ZIP_FILE }
Compress-Archive -Path "$DEPLOY_DIR\*" -CompressionLevel Fastest -DestinationPath $ZIP_FILE
Write-Host "   Package created"

# Step 5: Upload to S3
Write-Host "Step 5: Uploading to S3..." -ForegroundColor Yellow
& "C:\Program Files\Amazon\AWSCLIV2\aws.exe" s3 cp $ZIP_FILE "s3://$S3_BUCKET/$S3_KEY" --region $REGION

# Step 6: Update Lambda
Write-Host "Step 6: Updating Lambda function..." -ForegroundColor Yellow
& "C:\Program Files\Amazon\AWSCLIV2\aws.exe" lambda update-function-code `
  --function-name $LAMBDA_FUNCTION `
  --s3-bucket $S3_BUCKET `
  --s3-key $S3_KEY `
  --region $REGION

# Step 7: Wait for deployment
Write-Host "Step 7: Waiting for deployment..." -ForegroundColor Yellow
Start-Sleep -Seconds 15

# Step 8: Check status
Write-Host "Step 8: Checking deployment status..." -ForegroundColor Yellow
$status = & "C:\Program Files\Amazon\AWSCLIV2\aws.exe" lambda get-function `
  --function-name $LAMBDA_FUNCTION `
  --region $REGION `
  --query 'Configuration.LastUpdateStatus' `
  --output text
Write-Host "   Status: $status"

Write-Host "`nDeployment Complete!" -ForegroundColor Green
Write-Host "Lambda URL: https://slysl7v476awcx4754dv5osg3e0jjzqf.lambda-url.us-east-1.on.aws/"
Write-Host ""
