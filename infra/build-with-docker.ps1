# PowerShell script to build Lambda deployment package using Docker
# This ensures binary compatibility with AWS Lambda's Linux environment

Write-Host "Building Lambda deployment package with Docker..." -ForegroundColor Green

# Create output directory
New-Item -ItemType Directory -Force -Path "infra\docker-output" | Out-Null

# Build Docker image
docker build -t lambda-builder -f infra/Dockerfile.lambda-build .

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Docker build failed" -ForegroundColor Red
    exit 1
}

# Run container to create zip file (container exits immediately after creating file)
docker run --rm -v "${PWD}\infra\docker-output:/tmp/output" lambda-builder true

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Docker run failed" -ForegroundColor Red
    exit 1
}

# Check if file was created
if (Test-Path "infra\docker-output\lambda-deploy-linux-fixed.zip") {
    $fileSize = (Get-Item "infra\docker-output\lambda-deploy-linux-fixed.zip").Length / 1MB
    Write-Host "✅ Deployment package created: infra\docker-output\lambda-deploy-linux-fixed.zip" -ForegroundColor Green
    Write-Host "Size: $([math]::Round($fileSize, 2)) MB" -ForegroundColor Green
} else {
    Write-Host "❌ Failed to create deployment package" -ForegroundColor Red
    exit 1
}