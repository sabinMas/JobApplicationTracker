@echo off
REM JobApplicationTracker - Quick Deploy Script for Windows

echo.
echo 🚀 JobApplicationTracker Deployment Setup
echo ==========================================
echo.

REM Check if git is initialized
if not exist ".git" (
    echo ❌ Git repo not initialized. Run: git init
    exit /b 1
)

echo ✓ Git repo detected
echo.

echo 📋 Deployment Options
echo ====================
echo.
echo 1. Railway (recommended for backend)
echo 2. Render (alternative backend option)
echo 3. Both
echo.

set /p choice="Enter choice (1-3): "

echo.
echo Setting up deployment...
echo.

if "%choice%"=="1" goto railway
if "%choice%"=="3" goto railway

:render
echo 📋 Render Backend Deployment
echo =============================
echo.
echo 1. Go to: https://render.com
echo 2. Click 'New +' then 'Web Service'
echo 3. Connect your GitHub repo
echo 4. Configure:
echo    - Name: jobtracker-backend
echo    - Environment: Docker
echo.
echo 5. Set environment variables:
echo    - CEREBRAS_API_KEY: [your-api-key]
echo    - ALLOWED_ORIGINS: [your-frontend-url]
echo.
echo 6. Deploy!
echo.

if "%choice%"=="2" goto frontend

:railway
echo 📋 Railway Backend Deployment
echo ==============================
echo.
echo 1. Go to: https://railway.app
echo 2. Click 'New Project' then 'Deploy from GitHub'
echo 3. Select this repo: JobApplicationTracker
echo 4. Railway will auto-detect Dockerfile ✓
echo.
echo 5. Set environment variables:
echo    - CEREBRAS_API_KEY: [your-api-key]
echo    - ALLOWED_ORIGINS: [your-frontend-url]
echo    - ENVIRONMENT: production
echo.
echo 6. Deploy! (Auto-builds and runs)
echo.

:frontend
echo 📋 Frontend Deployment (Vercel)
echo ===============================
echo.
echo 1. Go to: https://vercel.com
echo 2. Click 'New Project' then 'Import from GitHub'
echo 3. Select JobApplicationTracker repo
echo 4. Set Root Directory: frontend
echo.
echo 5. Environment Variables:
echo    - VITE_API_URL: [your-backend-url]
echo.
echo 6. Deploy!
echo.

echo ✅ Deployment ready!
echo.
echo Next steps:
echo 1. Get Cerebras API key: https://cerebras.ai
echo 2. Deploy backend to Railway/Render
echo 3. Deploy frontend to Vercel
echo 4. Set ALLOWED_ORIGINS to your frontend URL
echo 5. Visit your frontend URL
echo.
echo 📖 Full guide: see DEPLOYMENT.md
echo.

pause
