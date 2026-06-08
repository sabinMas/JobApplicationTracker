# JobApplicationTracker - Lambda Deployment Script
# Usage: .\infra\deploy.ps1
#
# Prerequisites:
#   - AWS CLI configured (aws configure)
#   - Python 3.11+ installed
#   - pip install -r backend/requirements.txt done
#
# This script:
#   1. Packages the backend code into a Lambda zip
#   2. Creates/updates the Lambda function
#   3. Sets up API Gateway
#   4. Configures EventBridge scheduler

$ErrorActionPreference = "Stop"
$AWS = "C:\Program Files\Amazon\AWSCLIV2\aws.exe"
$REGION = "us-east-1"
$ACCOUNT_ID = "245091941294"
$FUNCTION_NAME = "jobtracker-api"
$ROLE_ARN = "arn:aws:iam::${ACCOUNT_ID}:role/jobtracker-lambda-role"
$S3_BUCKET = "jobtracker-documents-${ACCOUNT_ID}"

Write-Host "=== JobApplicationTracker Lambda Deployment ===" -ForegroundColor Cyan
Write-Host ""

# Step 1: Create deployment package
Write-Host "[1/5] Creating deployment package..." -ForegroundColor Yellow

$DEPLOY_DIR = ".\infra\deploy-package"
$ZIP_FILE = ".\infra\lambda-deploy.zip"

# Clean previous
if (Test-Path $DEPLOY_DIR) { Remove-Item -Recurse -Force $DEPLOY_DIR }
if (Test-Path $ZIP_FILE) { Remove-Item -Force $ZIP_FILE }

# Create package directory
New-Item -ItemType Directory -Path $DEPLOY_DIR -Force | Out-Null

# Install dependencies into package
Write-Host "  Installing dependencies..." -ForegroundColor Gray
pip install -r .\backend\requirements.txt -t $DEPLOY_DIR --quiet 2>$null

# Copy application code
Write-Host "  Copying application code..." -ForegroundColor Gray
Copy-Item -Recurse .\backend\app $DEPLOY_DIR\app
Copy-Item .\backend\lambda_handler.py $DEPLOY_DIR\lambda_handler.py

# Create zip
Write-Host "  Creating zip archive..." -ForegroundColor Gray
Compress-Archive -Path "$DEPLOY_DIR\*" -DestinationPath $ZIP_FILE -Force

$zipSize = (Get-Item $ZIP_FILE).Length / 1MB
Write-Host "  Package size: $([math]::Round($zipSize, 1)) MB" -ForegroundColor Gray

# Step 2: Create or update Lambda function
Write-Host ""
Write-Host "[2/5] Deploying Lambda function..." -ForegroundColor Yellow

$existingFunction = & $AWS lambda get-function --function-name $FUNCTION_NAME --region $REGION 2>$null
if ($LASTEXITCODE -eq 0) {
    # Update existing function
    Write-Host "  Updating existing function..." -ForegroundColor Gray
    & $AWS lambda update-function-code `
        --function-name $FUNCTION_NAME `
        --zip-file "fileb://$ZIP_FILE" `
        --region $REGION `
        --output text --query "FunctionArn" 2>&1
} else {
    # Create new function
    Write-Host "  Creating new function..." -ForegroundColor Gray
    & $AWS lambda create-function `
        --function-name $FUNCTION_NAME `
        --runtime python3.11 `
        --handler lambda_handler.handler `
        --role $ROLE_ARN `
        --zip-file "fileb://$ZIP_FILE" `
        --timeout 300 `
        --memory-size 512 `
        --region $REGION `
        --environment "Variables={ENVIRONMENT=production,S3_BUCKET=$S3_BUCKET,AWS_REGION=$REGION}" `
        --output text --query "FunctionArn" 2>&1
}

# Step 3: Create function URL (simpler than API Gateway for single-function)
Write-Host ""
Write-Host "[3/5] Creating function URL..." -ForegroundColor Yellow

& $AWS lambda create-function-url-config `
    --function-name $FUNCTION_NAME `
    --auth-type NONE `
    --cors "AllowOrigins=*,AllowMethods=*,AllowHeaders=*" `
    --region $REGION 2>$null

$funcUrl = & $AWS lambda get-function-url-config `
    --function-name $FUNCTION_NAME `
    --region $REGION `
    --query "FunctionUrl" --output text 2>&1

Write-Host "  Function URL: $funcUrl" -ForegroundColor Green

# Step 4: Add resource policy for public access
Write-Host ""
Write-Host "[4/5] Configuring access..." -ForegroundColor Yellow

& $AWS lambda add-permission `
    --function-name $FUNCTION_NAME `
    --statement-id FunctionURLAllowPublicAccess `
    --action lambda:InvokeFunctionUrl `
    --principal "*" `
    --function-url-auth-type NONE `
    --region $REGION 2>$null

# Step 5: Create EventBridge rule for daily sync
Write-Host ""
Write-Host "[5/5] Setting up daily sync scheduler..." -ForegroundColor Yellow

& $AWS events put-rule `
    --name jobtracker-daily-sync `
    --schedule-expression "cron(0 13 * * ? *)" `
    --state ENABLED `
    --description "Daily job sync at 8 AM EST (13:00 UTC)" `
    --region $REGION 2>$null

$FUNCTION_ARN = & $AWS lambda get-function `
    --function-name $FUNCTION_NAME `
    --region $REGION `
    --query "Configuration.FunctionArn" --output text 2>&1

& $AWS events put-targets `
    --rule jobtracker-daily-sync `
    --targets "Id=jobtracker-sync,Arn=$FUNCTION_ARN,Input='{\"httpMethod\":\"POST\",\"path\":\"/api/jobs/sync\",\"body\":\"\"}'" `
    --region $REGION 2>$null

# Allow EventBridge to invoke Lambda
& $AWS lambda add-permission `
    --function-name $FUNCTION_NAME `
    --statement-id EventBridgeDailySync `
    --action lambda:InvokeFunction `
    --principal events.amazonaws.com `
    --source-arn "arn:aws:events:${REGION}:${ACCOUNT_ID}:rule/jobtracker-daily-sync" `
    --region $REGION 2>$null

# Done
Write-Host ""
Write-Host "=== Deployment Complete ===" -ForegroundColor Green
Write-Host ""
Write-Host "Resources:" -ForegroundColor Cyan
Write-Host "  Lambda:      $FUNCTION_NAME" -ForegroundColor White
Write-Host "  URL:         $funcUrl" -ForegroundColor White
Write-Host "  S3 Bucket:   $S3_BUCKET" -ForegroundColor White
Write-Host "  Scheduler:   jobtracker-daily-sync (8 AM EST daily)" -ForegroundColor White
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Set DATABASE_URL environment variable on Lambda" -ForegroundColor Gray
Write-Host "  2. Test: curl ${funcUrl}health" -ForegroundColor Gray
Write-Host "  3. Sync jobs: curl -X POST ${funcUrl}api/jobs/sync" -ForegroundColor Gray
Write-Host ""

# Cleanup
Remove-Item -Recurse -Force $DEPLOY_DIR
Write-Host "Done! Cleaned up temp files." -ForegroundColor Green
