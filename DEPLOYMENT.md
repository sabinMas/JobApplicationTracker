# JobApplicationTracker - Deployment Guide

## Overview
This guide covers deploying the JobApplicationTracker to production. The app consists of:
- **Frontend**: React + Vite (deployed to Vercel)
- **Backend**: FastAPI with Playwright (deployed to Railway or Render)

## Prerequisites
- Git repository (initialized)
- Cerebras API key: https://cerebras.ai
- Railway or Render account
- Vercel account (for frontend)

## Backend Deployment (Railway)

### Step 1: Push to GitHub
```bash
git add -A
git commit -m "Add deployment configuration"
git push origin main
```

### Step 2: Connect to Railway
1. Go to https://railway.app
2. Click "New Project"
3. Select "Deploy from GitHub repo"
4. Authorize and select your JobApplicationTracker repo
5. Railway will auto-detect the Dockerfile

### Step 3: Set Environment Variables
In Railway dashboard:
- `CEREBRAS_API_KEY`: Your Cerebras API key
- `DATABASE_URL`: Leave as default (Railway will provide PostgreSQL)
- `ALLOWED_ORIGINS`: Add your frontend domain (e.g., `https://your-frontend.vercel.app`)
- `ENVIRONMENT`: Set to `production`

### Step 4: Deploy
Railway will automatically build and deploy from your main branch.

---

## Frontend Deployment (Vercel)

### Step 1: Update API URL
Edit `frontend/src/main.tsx` or create a config file:
```typescript
const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';
```

### Step 2: Deploy to Vercel
1. Go to https://vercel.com
2. Click "New Project"
3. Select your GitHub repo
4. Set Build settings:
   - **Root Directory**: `frontend`
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`

### Step 3: Set Environment Variables
In Vercel Project Settings:
- `VITE_API_URL`: Your Railway backend URL (e.g., `https://jobtracker-prod-backend.up.railway.app`)

### Step 4: Deploy
Vercel will auto-deploy from main branch.

---

## Alternative Backend Deployment (Render)

### Step 1: Create New Web Service
1. Go to https://render.com
2. Click "New +"
3. Select "Web Service"
4. Connect your GitHub repo

### Step 2: Configure
- **Name**: jobtracker-backend
- **Environment**: Docker
- **Build Command**: `docker build -t jobtracker .`
- **Start Command**: `python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT`

### Step 3: Set Environment Variables
In Render dashboard:
- `CEREBRAS_API_KEY`: Your API key
- `ALLOWED_ORIGINS`: Your frontend domain
- `DATABASE_URL`: Render provides PostgreSQL

### Step 4: Deploy
Render will auto-build and deploy.

---

## Configuration for Production

### Update CORS Origins
Make sure `ALLOWED_ORIGINS` includes your frontend domain:
```
ALLOWED_ORIGINS=https://your-frontend.vercel.app,https://www.your-frontend.vercel.app
```

### Database Considerations
- **Local dev**: SQLite (automatic)
- **Production**: Use Railway/Render's PostgreSQL
  - Update `DATABASE_URL` in environment variables
  - Run migrations if needed

### Playwright Browser
- The Docker image automatically installs Chromium
- Deployed instances run Playwright in headless mode
- No UI visible, but browsers are automated server-side

---

## Full Automation Features

### Automatic Job Application
The app now supports fully automated job applications:

1. **POST /api/auto-apply/full/{application_id}**
   - Auto-fills all form fields
   - Uploads tailored resume + cover letter
   - Submits application
   - Returns status

2. **POST /api/auto-apply/detect-fields/{application_id}**
   - Detects required fields on the form
   - Useful for understanding what data is needed

### Supported ATS Platforms
- Greenhouse
- Lever
- Workday
- Taleo
- LinkedIn
- Indeed
- ZipRecruiter
- Custom forms

### How It Works
1. User uploads profile + resume
2. System generates tailored docs for each job
3. On apply, automation:
   - Opens job application page
   - Auto-fills all detectable fields
   - Uploads documents
   - Submits form
   - Verifies submission

---

## Monitoring & Logs

### Railway
- View logs in railway.app dashboard
- Check "Logs" tab for real-time output

### Render
- View logs in render.com dashboard
- Check "Logs" section

### Common Issues
- **Browser timeouts**: Increase timeout in playwright_service.py
- **Form field detection fails**: Check your ATS platform detection
- **Submission not verified**: Manual review may be needed for some forms

---

## Cost Estimates (as of 2026)

- **Railway**: $5-20/month for backend + Postgres
- **Render**: $5-20/month for backend + Postgres
- **Vercel**: Free tier usually sufficient for frontend
- **Cerebras API**: Pay-per-use (very cheap for API calls)

---

## Security Best Practices

1. **Never commit .env files**
2. **Use environment variables for all secrets**
3. **Enable branch protection on main**
4. **Use HTTPS everywhere**
5. **Validate all user inputs**
6. **Keep dependencies updated**

---

## Rollback
If deployment fails:
- Railway: Click "Redeploy" on previous successful build
- Render: Use deployment history to rollback
- Vercel: Auto-rollback on failed deployments

---

## Support
For issues:
1. Check deployment logs
2. Verify environment variables are set
3. Test locally with Docker: `docker-compose up`
