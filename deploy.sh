#!/bin/bash

# JobApplicationTracker - Quick Deploy Script
# Supports Railway and Vercel

set -e

echo "🚀 JobApplicationTracker Deployment Setup"
echo "=========================================="
echo ""

# Check if git is initialized
if [ ! -d ".git" ]; then
    echo "❌ Git repo not initialized. Run: git init"
    exit 1
fi

echo "✓ Git repo detected"
echo ""

# Prompt for deployment choice
echo "Which platform do you want to deploy to?"
echo "1) Railway (recommended for backend)"
echo "2) Render (alternative backend option)"
echo "3) Both"
read -p "Enter choice (1-3): " choice

echo ""
echo "Setting up deployment..."
echo ""

if [ "$choice" = "1" ] || [ "$choice" = "3" ]; then
    echo "📋 Railway Backend Deployment"
    echo "=============================="
    echo ""
    echo "1. Go to: https://railway.app"
    echo "2. Click 'New Project' → 'Deploy from GitHub'"
    echo "3. Select this repo: JobApplicationTracker"
    echo "4. Railway will auto-detect the Dockerfile ✓"
    echo ""
    echo "5. Set these environment variables:"
    echo "   - CEREBRAS_API_KEY: <your-key>"
    echo "   - ALLOWED_ORIGINS: <frontend-url>"
    echo "   - ENVIRONMENT: production"
    echo ""
    echo "6. Deploy! Railway will auto-build and run."
    echo ""
fi

if [ "$choice" = "2" ] || [ "$choice" = "3" ]; then
    echo "📋 Render Backend Deployment"
    echo "============================="
    echo ""
    echo "1. Go to: https://render.com"
    echo "2. Click 'New +' → 'Web Service'"
    echo "3. Connect your GitHub repo"
    echo "4. Configure:"
    echo "   - Name: jobtracker-backend"
    echo "   - Environment: Docker"
    echo "   - Region: Choose closest to you"
    echo ""
    echo "5. Set environment variables:"
    echo "   - CEREBRAS_API_KEY: <your-key>"
    echo "   - ALLOWED_ORIGINS: <frontend-url>"
    echo ""
    echo "6. Deploy!"
    echo ""
fi

echo "📋 Frontend Deployment (Vercel)"
echo "==============================="
echo ""
echo "1. Go to: https://vercel.com"
echo "2. Click 'New Project' → Import from GitHub"
echo "3. Select JobApplicationTracker repo"
echo "4. Set Root Directory: frontend"
echo "5. Environment Variables:"
echo "   - VITE_API_URL: <your-backend-url>"
echo ""
echo "6. Deploy!"
echo ""

echo "✅ Deployment ready!"
echo ""
echo "Next steps:"
echo "1. Get your Cerebras API key: https://cerebras.ai"
echo "2. Deploy backend to Railway/Render"
echo "3. Deploy frontend to Vercel"
echo "4. Set ALLOWED_ORIGINS to your frontend URL"
echo "5. Visit your frontend URL"
echo ""
echo "📖 Full guide: see DEPLOYMENT.md"
