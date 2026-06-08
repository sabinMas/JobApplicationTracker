#!/bin/bash
# Build Lambda deployment package on Linux
# Run this on a Linux machine or in Docker

set -e  # Exit on error

echo "=== Building Lambda Deployment Package for Linux ==="
echo ""

# Configuration
PROJECT_ROOT="$(pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"
DEPLOY_DIR="$PROJECT_ROOT/deploy-package-linux"
DEPLOY_ZIP="$PROJECT_ROOT/lambda-deploy-linux.zip"
REQUIREMENTS_FILE="$PROJECT_ROOT/infra/requirements-lambda.txt"

echo "Project root: $PROJECT_ROOT"
echo "Backend dir: $BACKEND_DIR"
echo "Deploy dir: $DEPLOY_DIR"
echo "Requirements: $REQUIREMENTS_FILE"
echo ""

# Clean up old deployment
if [ -d "$DEPLOY_DIR" ]; then
    echo "Removing old deploy-package-linux..."
    rm -rf "$DEPLOY_DIR"
fi

if [ -f "$DEPLOY_ZIP" ]; then
    echo "Removing old lambda-deploy-linux.zip..."
    rm -f "$DEPLOY_ZIP"
fi

# Create deployment directory
echo "Creating deployment directory..."
mkdir -p "$DEPLOY_DIR"

# Install dependencies
echo "Installing dependencies..."
pip install -r "$REQUIREMENTS_FILE" -t "$DEPLOY_DIR" --platform manylinux2014_x86_64 --only-binary=:all:

# Copy application code
echo "Copying application code..."
cp -r "$BACKEND_DIR/app" "$DEPLOY_DIR/"
cp "$BACKEND_DIR/lambda_handler.py" "$DEPLOY_DIR/"

# Create zip file
echo "Creating deployment zip..."
cd "$DEPLOY_DIR"
zip -r "$DEPLOY_ZIP" . > /dev/null

# Calculate sizes
PACKAGE_SIZE=$(du -sh "$DEPLOY_DIR" | cut -f1)
ZIP_SIZE=$(du -h "$DEPLOY_ZIP" | cut -f1)

echo ""
echo "=== Build Complete ==="
echo "Package directory: $DEPLOY_DIR ($PACKAGE_SIZE)"
echo "Zip file: $DEPLOY_ZIP ($ZIP_SIZE)"
echo ""
echo "Next steps:"
echo "1. Upload to S3: aws s3 cp lambda-deploy-linux.zip s3://jobtracker-documents-245091941294/deploy/"
echo "2. Update Lambda: aws lambda update-function-code --function-name jobtracker-api --s3-bucket jobtracker-documents-245091941294 --s3-key deploy/lambda-deploy-linux.zip --region us-east-1"
echo "3. Test: curl https://4elmr535rxhpo5ktgdaxrjejai0jyeie.lambda-url.us-east-1.on.aws/health"
echo ""

# Verify key files exist
echo "Verifying key files..."
if [ -f "$DEPLOY_DIR/lambda_handler.py" ]; then
    echo "✓ lambda_handler.py"
else
    echo "✗ Missing: lambda_handler.py"
fi

if [ -d "$DEPLOY_DIR/app" ]; then
    echo "✓ app directory"
else
    echo "✗ Missing: app directory"
fi

if [ -f "$DEPLOY_DIR/pydantic_core/_pydantic_core.so" ] || [ -f "$DEPLOY_DIR/pydantic_core/_pydantic_core.cpython*.so" ]; then
    echo "✓ pydantic_core has Linux .so file"
elif [ -f "$DEPLOY_DIR/pydantic_core/_pydantic_core.cp313-win_amd64.pyd" ]; then
    echo "⚠ WARNING: pydantic_core has Windows .pyd file (will fail on Lambda)"
else
    echo "⚠ pydantic_core not found or has unexpected format"
fi

echo ""
echo "Note: AWS Lambda runs on Amazon Linux 2. Make sure dependencies are compiled"
echo "for manylinux2014_x86_64 or use --only-binary=:all: flag."