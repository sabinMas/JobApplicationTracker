# Deploy Lambda container image to ECR and update the function
# Usage: .\infra\scripts\deploy-lambda.ps1 [-SkipBuild]

param(
    [switch]$SkipBuild,
    [string]$Region = "us-east-1",
    [string]$AccountId = "245091941294",
    [string]$RepoName = "jobtracker-api",
    [string]$FunctionName = "jobtracker-api"
)

$ErrorActionPreference = "Stop"
$EcrUri = "$AccountId.dkr.ecr.$Region.amazonaws.com"
$ImageUri = "$EcrUri/${RepoName}:latest"

Write-Host "`n=== Deploy Lambda ===" -ForegroundColor Green

# Ensure ECR repo exists
Write-Host "[1/4] Ensuring ECR repo exists..." -ForegroundColor Yellow
$ErrorActionPreference = "Continue"
aws ecr describe-repositories --repository-names $RepoName --region $Region 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) {
    aws ecr create-repository --repository-name $RepoName --region $Region | Out-Null
    Write-Host "  Created repo: $RepoName" -ForegroundColor Gray
}
$ErrorActionPreference = "Stop"

if (-not $SkipBuild) {
    # Login to ECR first (buildx pushes during build)
    Write-Host "[2/4] Logging in to ECR..." -ForegroundColor Yellow
    $loginCmd = "aws ecr get-login-password --region $Region | docker login --username AWS --password-stdin $EcrUri"
    cmd /c $loginCmd
    if ($LASTEXITCODE -ne 0) { throw "ECR login failed" }

    # Build and push. Lambda requires a plain single-arch manifest:
    # --provenance=false --sbom=false strips the OCI attestation manifests
    # that newer buildx adds, which Lambda rejects as "media type not supported".
    Write-Host "[3/4] Building and pushing image..." -ForegroundColor Yellow
    docker buildx build --provenance=false --sbom=false --platform linux/amd64 `
        -f Dockerfile.lambda -t "${ImageUri}" --push .
    if ($LASTEXITCODE -ne 0) { throw "Docker build/push failed" }
} else {
    Write-Host "[2-3/4] Skipping build (--SkipBuild)" -ForegroundColor Gray
}

# Update Lambda to use new image
Write-Host "[4/4] Updating Lambda function..." -ForegroundColor Yellow
aws lambda update-function-code `
    --function-name $FunctionName `
    --image-uri $ImageUri `
    --region $Region | Out-Null

Write-Host "`nDone! Lambda updated with image: $ImageUri" -ForegroundColor Green
Write-Host "Function URL: " -NoNewline
aws lambda get-function-url-config --function-name $FunctionName --region $Region --query 'FunctionUrl' --output text 2>$null
Write-Host ""
