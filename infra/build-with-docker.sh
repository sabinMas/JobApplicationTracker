#!/bin/bash

# Script to build Lambda deployment package using Docker
# This ensures binary compatibility with AWS Lambda's Linux environment

set -e

echo "Building Lambda deployment package with Docker..."

# Create output directory
mkdir -p infra/docker-output

# Build Docker image
docker build -t lambda-builder -f infra/Dockerfile.lambda-build .

# Run container to extract zip file
docker run --rm -v $(pwd)/infra/docker-output:/tmp/output lambda-builder

# Check if file was created
if [ -f "infra/docker-output/lambda-deploy-linux-fixed.zip" ]; then
    echo "✅ Deployment package created: infra/docker-output/lambda-deploy-linux-fixed.zip"
    echo "Size: $(du -h infra/docker-output/lambda-deploy-linux-fixed.zip | cut -f1)"
else
    echo "❌ Failed to create deployment package"
    exit 1
fi