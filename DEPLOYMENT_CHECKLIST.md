# Deployment Checklist - Fix Blank Page Issue

## 🔴 CRITICAL: What's Wrong Right Now

Your deployed frontend shows a **blank white page** because the backend connection is failing silently. Here's why:

### Root Cause Analysis

1. **Frontend calls** `/api/*` (relative path)
2. **Vercel proxy functions** (`api/proxy.ts`) try to reach the backend
3. **Proxy uses** `BACKEND_API_URL` environment variable
4. **Vercel env var** is either not set, misconfigured, or the EC2 backend isn't reachable from Vercel

### Result
- API calls fail silently
- React app crashes loading data
- User sees blank page

---

## ✅ Step-by-Step Fix

### Step 1: Verify/Set Vercel Environment Variables

**Access:** https://vercel.com → JobApplicationTracker → Settings → Environment Variables

**Required for all environments (Production, Preview, Development):**

```
BACKEND_API_URL = http://54.237.223.146
```

**Double-check:**
- ✅ Variable name is **exactly** `BACKEND_API_URL` (case-sensitive)
- ✅ Value is your EC2 backend IP or domain
- ✅ Applied to **Production** environment (minimum requirement)
- ✅ No trailing slash (`http://54.237.223.146/` is wrong)

### Step 2: Trigger Redeploy

After setting the env var, redeploy:

**Option A: Git Push (automatic)**
```bash
cd JobApplicationTracker
git push origin master
```

**Option B: Manual Redeploy (Vercel Dashboard)**
1. Go to Deployments tab
2. Click the latest deployment
3. Click "Redeploy"

### Step 3: Verify the Fix

After deployment completes (~2 min):

1. **Open** https://frontend-six-flame-47.vercel.app (or your Vercel URL)
2. **Open DevTools** (F12)
3. **Check Network tab:**
   - Should see successful requests to `/api/dashboard/metrics`
   - Status should be `200` (not `502` or `404`)
4. **Check Console tab:**
   - No errors like "Failed to fetch"

### Step 4: If Still Showing Blank Page

**Troubleshoot in this order:**

#### A. Check Vercel Function Logs
1. Vercel Dashboard → Deployments → Details
2. Look for errors in the Function logs for `api/proxy.ts`
3. Common errors:
   - `ECONNREFUSED` → EC2 backend not reachable
   - `DEPTH_ZERO_SELF_SIGNED_CERT` → SSL cert issue (this is expected and handled)
   - `getaddrinfo ENOTFOUND` → DNS resolution failed

#### B. Verify EC2 Backend is Running
1. AWS Console → EC2 → Instances
2. Check `jobtracker-ec2` status: should be **Running** ✅
3. Check instance health: should be **2/2 checks passed**

#### C. Test Backend Directly
From your terminal:
```bash
curl -v http://54.237.223.146/api/dashboard/metrics?days=7
```

You should see a JSON response with metrics (even if all zeros).

#### D. Check EC2 Security Group
1. AWS Console → EC2 → Security Groups
2. Find the security group attached to `jobtracker-ec2`
3. Verify **Inbound rule** allows traffic on port 80:
   - Protocol: TCP
   - Port: 80
   - Source: 0.0.0.0/0 (or Vercel's IP range for production)

#### E. Check FastAPI Backend Logs
SSH into EC2 and check the backend:
```bash
ssh -i your-key.pem ec2-user@54.237.223.146
tail -f /var/log/backend.log  # or wherever you log
```

---

## 🟡 MEDIUM PRIORITY: Additional Fixes (Already Applied)

### ✅ Fixed: npm Vulnerabilities
- **Status:** DONE ✅
- **What:** Ran `npm audit fix` to patch 8 vulnerabilities
- **Impact:** Improves security, reduces warnings
- **Commit:** `fix: resolve npm vulnerabilities and add environment setup guide`

### 🔧 TODO: Reduce Bundle Size
- **Current:** 547 kB (exceeds 500 kB recommendation)
- **How:** Add dynamic imports/code-splitting in Vite config
- **Impact:** Faster page load for end users

### 🔧 TODO: Add HTTPS to Backend
- **Current:** Backend is plain HTTP (works locally, but creates mixed-content warnings)
- **Options:**
  - A: nginx + Let's Encrypt on EC2
  - B: AWS ALB with HTTPS termination
- **Priority:** After fixing the blank page issue

### 🔧 TODO: Populate Dashboard Data
- **Current:** All metrics show 0
- **Reason:** Scraper hasn't run yet
- **How:** Trigger pipeline to scrape job listings
- **Priority:** Low (affects UX, not functionality)

---

## 📋 Checklist: Verify Everything Works

After redeploy, verify:

- [ ] Frontend loads without blank page
- [ ] Dashboard shows at least some data (even if metrics are still 0)
- [ ] Network requests to `/api/*` return 200 status
- [ ] No console errors about failed API calls
- [ ] Can navigate between pages without errors

---

## 🚨 If Redeploy Doesn't Help

Try these troubleshooting commands:

```bash
# 1. Clear Vercel cache
vercel env list  # just to verify env is there

# 2. Check the deployed environment
curl -i https://frontend-six-flame-47.vercel.app/api/dashboard/metrics?days=7

# 3. Look for logs in Vercel dashboard
# Settings → Functions → Logs

# 4. Redeploy with --prod flag
git push origin master  # or
vercel --prod
```

---

## 📞 Questions?

If you're still stuck:
1. Share screenshot of Vercel environment variables
2. Share curl output from testing the backend directly
3. Share console errors from DevTools
4. Check Vercel Functions logs for proxy errors
