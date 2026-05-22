# 🚀 Get JobApplicationTracker Live in 10 Minutes

This guide walks you through deploying the app to production in the fastest way possible.

## Prerequisites

- GitHub account (push your code)
- Cerebras API key (free: https://cerebras.ai)
- Railway account (free tier available: https://railway.app) OR Render account
- Vercel account (free: https://vercel.com)

---

## Step 1: Push to GitHub (2 minutes)

```bash
git add -A
git commit -m "Deploy to production"
git push origin main
```

Make sure your repo is public or connected to Railway/Render.

---

## Step 2: Deploy Backend to Railway (3 minutes)

### Option A: Railway (Recommended)

1. Go to https://railway.app
2. Click **"New Project"**
3. Click **"Deploy from GitHub repo"**
4. Authorize GitHub and select `JobApplicationTracker`
5. Railway auto-detects the Dockerfile ✓
6. Confirm deployment

### Add Environment Variables

In Railway dashboard, go to **Variables** tab:

```
CEREBRAS_API_KEY = [paste-your-cerebras-api-key]
ALLOWED_ORIGINS = https://[your-frontend].vercel.app
ENVIRONMENT = production
```

Your backend URL will be something like:
```
https://jobtracker-prod-xxxxxxx.up.railway.app
```

---

## Step 3: Deploy Frontend to Vercel (3 minutes)

1. Go to https://vercel.com
2. Click **"Add New..."** → **"Project"**
3. Click **"Import Git Repository"**
4. Select `JobApplicationTracker`
5. Click **"Import"**

### Configure

- **Root Directory**: `frontend`
- **Framework**: Vite
- Leave build settings default

### Add Environment Variable

In project settings, go to **Environment Variables**:

```
VITE_API_URL = https://jobtracker-prod-xxxxxxx.up.railway.app
```

Click **Deploy** and wait ~2 minutes.

---

## Step 4: Update CORS (1 minute)

1. Go back to Railway dashboard
2. Go to **Variables**
3. Update:
```
ALLOWED_ORIGINS = https://[your-vercel-domain].vercel.app,https://www.[your-vercel-domain].vercel.app
```
4. Redeploy backend

---

## Step 5: Test It Works ✅

1. Go to your Vercel frontend URL
2. You should see the JobApplicationTracker UI
3. Try the health check: `[your-backend-url]/health`

---

## Step 6: Get Your Cerebras API Key (Free!)

If you don't have it yet:

1. Go to https://cerebras.ai
2. Sign up (free)
3. Create an API key
4. Copy it
5. Paste in Railway variables: `CEREBRAS_API_KEY`
6. Redeploy

---

## Step 7: Set Up Your Profile (2 minutes)

1. Go to your Vercel app
2. Click **Profile**
3. Upload your resume PDF
4. Click **"Extract with AI"**
5. Review and save

---

## Now You Can Use It!

### To Apply to a Job:

1. Go to any job posting (LinkedIn, Indeed, etc.)
2. Copy the URL
3. In app → click **"Add Job"** → paste URL
4. Click **"Import"** (AI extracts details)
5. Click **"Tailor Resume + Cover Letter"** (AI generates custom docs)
6. Click **"Apply Now"** → choose **"Full Auto"**

**That's it!** The app handles everything:
- Fills out the application form
- Uploads your tailored resume
- Submits the application
- Tracks the status

---

## Troubleshooting

### "Can't connect to API"
- Check that `ALLOWED_ORIGINS` in Railway includes your Vercel URL
- Try clearing browser cache
- Check browser console for errors

### "Cerebras API not working"
- Verify your API key is correct
- Go to https://cerebras.ai to check your account
- Make sure you have API usage quota

### "Form filling not working"
- Some forms are JavaScript-heavy; give it a few seconds
- You can always pause and fill manually
- Click the pause button to take control

### "Deployment failed"
- **Railway**: Check build logs in dashboard
- **Vercel**: Check deployment logs in dashboard
- Most likely: Missing environment variables

---

## You're Done! 🎉

Your JobApplicationTracker is now **live and fully operational**.

### What you can do now:

✅ Import any job posting  
✅ Auto-generate tailored resumes  
✅ Auto-generate cover letters  
✅ Full automation for job applications  
✅ Track all your applications in one place  
✅ Support for 10+ ATS platforms  

---

## Next Steps (Optional)

- **Add more jobs**: Paste more job URLs
- **Monitor applications**: Check application status on dashboard
- **Customize docs**: Edit cover letter examples for better AI matching
- **Team usage**: Share your backend with teammates (set ALLOWED_ORIGINS to multiple domains)

---

## Costs

- **Railway Backend**: Free tier or $5-20/month
- **Vercel Frontend**: Free tier
- **Cerebras API**: Free tier (pay-per-use, very cheap)
- **Total**: Essentially **free** to start

---

## Get Help

- Check [DEPLOYMENT.md](./DEPLOYMENT.md) for detailed guide
- See [README.md](./README.md) for full API reference
- Check Vercel/Railway logs if something breaks

---

## That's it! Happy job hunting! 🚀

Your fully automated job application system is now live. Go apply to your dream jobs!
