# Build proper Linux package using Docker
Write-Host "Building proper Linux package with Docker..." -ForegroundColor Green

# Clean output
Remove-Item -Recurse -Force infra/docker-output-proper -ErrorAction SilentlyContinue
mkdir -Force infra/docker-output-proper | Out-Null

Write-Host "1. Building Docker image..." -ForegroundColor Yellow
docker build -t lambda-linux-builder -f infra/Dockerfile.linux-build .

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Docker build failed" -ForegroundColor Red
    exit 1
}

Write-Host "2. Running container to create package..." -ForegroundColor Yellow
docker run --rm -v "${PWD}\infra\docker-output-proper:/output" lambda-linux-builder

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Docker run failed" -ForegroundColor Red
    exit 1
}

Write-Host "3. Verifying package..." -ForegroundColor Yellow

if (Test-Path "infra\docker-output-proper\lambda-deploy-linux-proper.zip") {
    $zipSize = (Get-Item "infra\docker-output-proper\lambda-deploy-linux-proper.zip").Length / 1MB
    
    # Check for pydantic_core files
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $zip = [System.IO.Compression.ZipFile]::OpenRead("$PWD\infra\docker-output-proper\lambda-deploy-linux-proper.zip")
    $pydanticFiles = $zip.Entries | Where-Object {$_.FullName -like "*pydantic_core*"} | Select-Object -First 5 FullName
    $zip.Dispose()
    
    Write-Host "✅ Proper Linux package created!" -ForegroundColor Green
    Write-Host "   File: infra/docker-output-proper/lambda-deploy-linux-proper.zip" -ForegroundColor Green
    Write-Host "   Size: $([math]::Round($zipSize, 2)) MB" -ForegroundColor Green
    
    Write-Host "   pydantic_core files found:" -ForegroundColor Gray
    foreach ($file in $pydanticFiles) {
        Write-Host "   - $file" -ForegroundColor Gray
    }
    
    # Copy to main location
    Copy-Item "infra\docker-output-proper\lambda-deploy-linux-proper.zip" "infra\lambda-deploy-linux-fixed.zip" -Force
    Write-Host "   Copied to: infra/lambda-deploy-linux-fixed.zip" -ForegroundColor Green
    
} else {
    Write-Host "❌ Package not created" -ForegroundColor Red
    exit 1
}