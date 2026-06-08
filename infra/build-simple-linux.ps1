# Simple script to build Linux-compatible Lambda package
# Focuses on core dependencies and handles pydantic_core specially

Write-Host "Building simple Linux-compatible Lambda package..." -ForegroundColor Green

# Clean previous builds
Remove-Item -Recurse -Force infra/linux-simple-package -ErrorAction SilentlyContinue
mkdir -Force infra/linux-simple-package | Out-Null

Write-Host "1. Creating minimal package structure..." -ForegroundColor Yellow

# Copy backend code
Copy-Item -Recurse -Path "backend/*" -Destination "infra/linux-simple-package/" -Exclude "__pycache__", "*.pyc", "venv", ".git", "tests"

Write-Host "2. Installing core dependencies (pure Python only)..." -ForegroundColor Yellow

# Install pure Python dependencies that don't need compilation
$purePythonDeps = @(
    "fastapi==0.115.5",
    "pydantic==2.10.3",
    "pydantic-settings==2.6.1",
    "python-multipart==0.0.17",
    "httpx==0.28.0",
    "beautifulsoup4==4.12.3",
    "openai==1.57.4",
    "python-dotenv==1.0.1",
    "aiofiles==24.1.0",
    "watchtower==3.0.1",
    "mangum==0.21.0",
    "boto3==1.43.24",
    "starlette==0.41.3"
)

# Create requirements file
$reqContent = $purePythonDeps -join "`n"
Set-Content -Path "infra/linux-simple-package/requirements.txt" -Value $reqContent

# Install to package directory
python -m pip install --target "infra/linux-simple-package" @purePythonDeps

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to install pure Python dependencies" -ForegroundColor Red
    exit 1
}

Write-Host "3. Handling pydantic_core specially..." -ForegroundColor Yellow

# pydantic_core is the problematic binary. Let's check what we have
$pydanticCorePath = "infra/linux-simple-package/pydantic_core"
if (Test-Path $pydanticCorePath) {
    Write-Host "   Found pydantic_core, checking binaries..." -ForegroundColor Gray
    Get-ChildItem -Recurse -Path $pydanticCorePath -Filter "*.so" | ForEach-Object {
        Write-Host "   - Found Linux .so: $($_.Name)" -ForegroundColor Green
    }
    Get-ChildItem -Recurse -Path $pydanticCorePath -Filter "*.pyd" | ForEach-Object {
        Write-Host "   - Found Windows .pyd (will cause issues): $($_.Name)" -ForegroundColor Red
        # Remove Windows binaries
        Remove-Item $_.FullName -Force
        Write-Host "   - Removed Windows binary" -ForegroundColor Yellow
    }
}

Write-Host "4. Installing platform-specific dependencies..." -ForegroundColor Yellow

# For Lambda, we need asyncpg and sqlalchemy. Let's try to install them
# These might fail but we'll handle gracefully
try {
    python -m pip install --target "infra/linux-simple-package" "sqlalchemy==2.0.36" 2>&1 | Out-Null
    Write-Host "   - Installed SQLAlchemy" -ForegroundColor Green
} catch {
    Write-Host "   - SQLAlchemy installation failed (may need binary)" -ForegroundColor Yellow
}

# Note: asyncpg requires binary compilation, skip for now
# The application might work without it for basic functionality

Write-Host "5. Creating final ZIP package..." -ForegroundColor Yellow

# Clean up
Remove-Item -Recurse -Force "infra/linux-simple-package/__pycache__" -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force "infra/linux-simple-package/*/__pycache__" -ErrorAction SilentlyContinue
Remove-Item "infra/linux-simple-package/*.pyc" -ErrorAction SilentlyContinue

# Create ZIP file
Add-Type -AssemblyName System.IO.Compression.FileSystem
$compressionLevel = [System.IO.Compression.CompressionLevel]::Optimal
[System.IO.Compression.ZipFile]::CreateFromDirectory("$PWD/infra/linux-simple-package", "$PWD/infra/lambda-deploy-linux-simple.zip", $compressionLevel, $false)

# Verify
$zipSize = (Get-Item "infra/lambda-deploy-linux-simple.zip").Length / 1MB
Write-Host "✅ Simple Linux package created: infra/lambda-deploy-linux-simple.zip" -ForegroundColor Green
Write-Host "   Size: $([math]::Round($zipSize, 2)) MB" -ForegroundColor Green

Write-Host "`nNote: This package uses pure Python dependencies only." -ForegroundColor Yellow
Write-Host "Binary dependencies (asyncpg, pydantic_core compiled) may need manual Linux compilation." -ForegroundColor Yellow