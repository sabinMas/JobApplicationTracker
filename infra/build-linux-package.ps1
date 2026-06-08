# PowerShell script to build Linux-compatible Lambda deployment package
# Uses manylinux wheels for binary compatibility

Write-Host "Building Linux-compatible Lambda deployment package..." -ForegroundColor Green

# Clean previous builds
Remove-Item -Recurse -Force infra/linux-package -ErrorAction SilentlyContinue
mkdir -Force infra/linux-package | Out-Null

# Create a temporary virtual environment for downloading Linux wheels
$tempDir = "infra/temp-linux-build"
Remove-Item -Recurse -Force $tempDir -ErrorAction SilentlyContinue
mkdir -Force $tempDir | Out-Null

Write-Host "1. Downloading Linux-compatible wheels..." -ForegroundColor Yellow

# First, let's create a simplified requirements file without problematic packages
# We'll handle feedparser separately since it has sgmllib3k dependency issues
$simpleRequirements = @"
fastapi==0.115.5
sqlalchemy[asyncio]==2.0.36
asyncpg==0.30.0
pydantic==2.10.3
pydantic-settings==2.6.1
python-multipart==0.0.17
httpx==0.28.0
beautifulsoup4==4.12.3
openai==1.57.4
python-dotenv==1.0.1
aiofiles==24.1.0
watchtower==3.0.1
mangum==0.21.0
boto3==1.43.24
starlette==0.41.3
"@

Set-Content -Path "$tempDir/requirements-simple.txt" -Value $simpleRequirements

# Download wheels for Linux x86_64 (manylinux2014 compatible with Amazon Linux 2023)
# Using pip download with platform, python version, and implementation constraints
python -m pip download `
    --only-binary=:all: `
    --platform manylinux2014_x86_64 `
    --python-version 312 `
    --implementation cp `
    --abi cp312 `
    --dest "$tempDir/wheels" `
    -r "$tempDir/requirements-simple.txt"

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to download Linux wheels" -ForegroundColor Red
    exit 1
}

Write-Host "2. Installing wheels to package directory..." -ForegroundColor Yellow

# Install downloaded wheels to package directory
python -m pip install `
    --target "infra/linux-package" `
    --no-index `
    --find-links "$tempDir/wheels" `
    -r infra/requirements-lambda.txt

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to install wheels" -ForegroundColor Red
    exit 1
}

Write-Host "3. Copying application code..." -ForegroundColor Yellow

# Copy backend code
Copy-Item -Recurse -Path "backend/*" -Destination "infra/linux-package/" -Exclude "__pycache__", "*.pyc", "venv", ".git"

Write-Host "4. Cleaning package..." -ForegroundColor Yellow

# Remove unnecessary files
Remove-Item -Recurse -Force "infra/linux-package/__pycache__" -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force "infra/linux-package/*/__pycache__" -ErrorAction SilentlyContinue
Remove-Item "infra/linux-package/*.pyc" -ErrorAction SilentlyContinue

Write-Host "5. Creating ZIP archive..." -ForegroundColor Yellow

# Create ZIP file
Add-Type -AssemblyName System.IO.Compression.FileSystem
$compressionLevel = [System.IO.Compression.CompressionLevel]::Optimal
[System.IO.Compression.ZipFile]::CreateFromDirectory("$PWD/infra/linux-package", "$PWD/infra/lambda-deploy-linux-fixed.zip", $compressionLevel, $false)

# Clean up temp directory
Remove-Item -Recurse -Force $tempDir -ErrorAction SilentlyContinue

# Verify the package
$zipSize = (Get-Item "infra/lambda-deploy-linux-fixed.zip").Length / 1MB
Write-Host "✅ Linux deployment package created: infra/lambda-deploy-linux-fixed.zip" -ForegroundColor Green
Write-Host "   Size: $([math]::Round($zipSize, 2)) MB" -ForegroundColor Green

# Check for pydantic_core files
Write-Host "6. Verifying pydantic_core compatibility..." -ForegroundColor Yellow
Add-Type -AssemblyName System.IO.Compression.FileSystem
$zip = [System.IO.Compression.ZipFile]::OpenRead("$PWD/infra/lambda-deploy-linux-fixed.zip")
$pydanticCoreFiles = $zip.Entries | Where-Object {$_.FullName -like "*pydantic_core*"} | Select-Object -First 10 FullName
$zip.Dispose()

Write-Host "   Found pydantic_core files:" -ForegroundColor Green
foreach ($file in $pydanticCoreFiles) {
    Write-Host "   - $file" -ForegroundColor Gray
}