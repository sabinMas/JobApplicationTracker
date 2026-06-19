# Fix Dashboard Now — Quick Start Guide

**Status**: Ready to deploy fixes  
**Time required**: ~15 minutes total  
**What you need**: EC2 SSH access + Vercel account

---

## 🚀 Option A: Quick Fix (Manual Setup on EC2)

Use this if you want to fix it **right now** without waiting for CI/CD.

### Step 1: Get your EC2 public IP
```bash
echo "54.237.223.146"  # This is your current IP
```

### Step 2: SSH into EC2 and run nginx setup
```bash
# From your local machine
ssh -i /path/to/jobtracker-ec2.pem ec2-user@54.237.223.146

# On EC2, run the nginx setup script:
bash /opt/jobtracker/infra/scripts/setup-ec2-nginx.sh
```

**Expected output**:
```
=== JobApplicationTracker nginx + SSL Setup ===
EC2 Public IP: 54.237.223.146
[1/5] Installing nginx...
[2/5] Setting up SSL certificate...
[3/5] Configuring nginx as reverse proxy...
[4/5] Validating nginx configuration...
[5/5] Starting nginx...

✓ nginx is running on HTTPS port 443
✓ All HTTP traffic redirects to HTTPS
```

### Step 3: Verify nginx is working
```bash
# Still on EC2, test the health endpoint:
curl -k https://localhost/api/health

# Expected response:
# {"status": "ok", "message": "API is running", ...}
```

### Step 4: Exit EC2 and test from your local machine
```bash
# Back on your local machine:
curl -k https://54.237.223.146/api/health

# Should return the same health response
```

---

## Step 5: Update Vercel Environment Variable

### In Vercel Dashboard:

1. Go to: **https://vercel.com/sabinmas-projects/jobapptracker/settings/environment-variables**

2. Find or create the variable `VITE_API_URL`
   - **Name**: `VITE_API_URL`
   - **Value**: `https://54.237.223.146` (no port, no `/api` suffix)
   - **Environments**: Select `Production`

3. Click **Save**

4. Vercel will auto-redeploy the frontend

### Screenshot (if needed):
```
┌─ Environment Variables ───────────────────────┐
│ Name           │ Value                        │
├────────────────┼──────────────────────────────┤
│ VITE_API_URL   │ https://54.237.223.146      │
│ (Environment)  │ Production                   │
└────────────────────────────────────────────────┘
```

---

## Step 6: Verify Dashboard Loads

1. Wait ~2 minutes for Vercel to redeploy
2. Open: **https://frontend-six-flame-47.vercel.app/**
3. The dashboard should load without errors
4. You should see:
   - Jobs discovered (count)
   - Applications (count)
   - Score distribution (chart)

If it still fails, check the browser console (F12) for errors.

---

## 🔄 Option B: Automated Fix (Wait for Next CI Deploy)

If you prefer to let CI/CD handle it:

1. The nginx setup script is now part of the deployment pipeline
2. **Next push to `master`** will automatically:
   - Install nginx
   - Configure SSL reverse proxy
   - Restart services
3. Just update Vercel env var (Step 5 above) manually

---

## 🧪 Troubleshooting

### If nginx setup fails:
```bash
# SSH to EC2 and check nginx status
sudo systemctl status nginx

# View nginx error logs
sudo journalctl -u nginx -n 50 --no-pager

# Check if port 443 is listening
sudo netstat -tulpn | grep 443
```

### If health check returns error:
```bash
# Check if uvicorn backend is running on :8000
curl http://localhost:8000/health

# Check backend service
sudo systemctl status jobtracker

# View backend logs
sudo journalctl -u jobtracker -n 50 --no-pager
```

### If frontend still shows "Failed to load":
1. Check browser Network tab (F12)
2. Verify CORS headers are present (should be from FastAPI)
3. Confirm `VITE_API_URL` is set in Vercel (not in local `.env`)

---

## 📋 Checklist (Before declaring success)

- [ ] SSH to EC2 successful
- [ ] `setup-ec2-nginx.sh` completed without errors
- [ ] `curl -k https://54.237.223.146/api/health` returns 200
- [ ] `VITE_API_URL` set in Vercel dashboard
- [ ] Vercel redeploy triggered (check deployment history)
- [ ] Dashboard page loads (no "Failed to load" message)
- [ ] Dashboard shows real data (jobs, applications, charts)

---

## 🎯 What's Fixed

| Issue | Solution |
|-------|----------|
| No HTTPS on EC2 | nginx with self-signed SSL cert on port 443 |
| No reverse proxy | nginx proxies `/api/*` to uvicorn :8000 |
| Frontend env var missing | `VITE_API_URL` set in Vercel dashboard |
| CORS/mixed-content errors | Consistent HTTPS 443 throughout |

---

## 📚 Files Modified

- **Created**: `infra/scripts/setup-ec2-nginx.sh` ✅
- **Updated**: `.github/workflows/ci.yml` ✅
- **Manual**: Vercel environment variable

---

## ⚡ Quick Reference

```bash
# View nginx config
sudo cat /etc/nginx/conf.d/jobtracker.conf

# Restart nginx (if you make changes)
sudo systemctl restart nginx

# View certificate
sudo openssl x509 -in /etc/nginx/ssl/jobtracker.crt -text -noout | grep -E "Subject|Not Before|Not After"

# Test nginx config without restarting
sudo nginx -t
```

---

**Next**: SSH to EC2 and run Step 2, then update Vercel and test! 🚀
