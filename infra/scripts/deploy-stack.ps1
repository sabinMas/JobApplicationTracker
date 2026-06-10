# Deploy or update the CloudFormation stack
# Prereqs: Lambda and Worker images pushed to ECR, SSM params for subnet/SG set
#
# Usage:
#   .\infra\scripts\deploy-stack.ps1
#   .\infra\scripts\deploy-stack.ps1 -DatabaseUrl "postgresql+asyncpg://..."

param(
    [string]$StackName = "jobtracker",
    [string]$Region = "us-east-1",
    [string]$AccountId = "245091941294",
    [string]$DatabaseUrl = "",
    [string]$AllowedOrigins = "http://localhost:5173",
    [string]$BudgetEmail = "",
    [string]$LambdaRepo = "jobtracker-api-lambda",
    [string]$WorkerRepo = "jobtracker-worker"
)

$ErrorActionPreference = "Stop"
$EcrUri = "$AccountId.dkr.ecr.$Region.amazonaws.com"
$TemplateFile = "infra/aws/cloudformation.yaml"

Write-Host "`n=== Deploy CloudFormation Stack: $StackName ===" -ForegroundColor Green

# Validate required params
if (-not $DatabaseUrl) {
    Write-Host "ERROR: -DatabaseUrl is required" -ForegroundColor Red
    Write-Host "Example: -DatabaseUrl 'postgresql+asyncpg://user:pass@host:5432/jobtracker'" -ForegroundColor Gray
    exit 1
}
if (-not $BudgetEmail) {
    Write-Host "ERROR: -BudgetEmail is required for budget alerts" -ForegroundColor Red
    exit 1
}

$LambdaImageUri = "$EcrUri/${LambdaRepo}:latest"
$WorkerImageUri = "$EcrUri/${WorkerRepo}:latest"

Write-Host "Template:     $TemplateFile"
Write-Host "Lambda image: $LambdaImageUri"
Write-Host "Worker image: $WorkerImageUri"
Write-Host ""

# Deploy/update stack
aws cloudformation deploy `
    --template-file $TemplateFile `
    --stack-name $StackName `
    --capabilities CAPABILITY_NAMED_IAM `
    --parameter-overrides `
        "DatabaseUrl=$DatabaseUrl" `
        "AllowedOrigins=$AllowedOrigins" `
        "LambdaImageUri=$LambdaImageUri" `
        "WorkerImageUri=$WorkerImageUri" `
        "BudgetAlertEmail=$BudgetEmail" `
    --region $Region

if ($LASTEXITCODE -ne 0) {
    Write-Host "Stack deploy failed!" -ForegroundColor Red
    aws cloudformation describe-stack-events `
        --stack-name $StackName `
        --region $Region `
        --query 'StackEvents[?ResourceStatus==`CREATE_FAILED` || ResourceStatus==`UPDATE_FAILED`].[LogicalResourceId, ResourceStatusReason]' `
        --output table
    exit 1
}

Write-Host "`nStack outputs:" -ForegroundColor Green
aws cloudformation describe-stacks `
    --stack-name $StackName `
    --region $Region `
    --query 'Stacks[0].Outputs' `
    --output table

Write-Host "`nDone!" -ForegroundColor Green
