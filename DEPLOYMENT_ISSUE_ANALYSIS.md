# JobApplicationTracker Deployment Issues — Analysis & Remediation Plan

**Date**: June 19, 2026  
**Status**: Dashboard fails to load | EC2 deployment incomplete | Vercel env misconfigured

---

## 🔴 Root Causes Identified

### 1. **Missing nginx + SSL on EC2** (CRITICAL)
**Problem**: 
- `infra/scripts/setup-ec2.sh` installs and starts uvicorn on `0.0.0.0:8000` (HTTP, no SSL)
- No nginx reverse proxy is installed to:
  - Serve HTTPS on port 443
  - Proxy `/api/*` requests to uvicorn `:8000`
  - Handle SSL certificates

**Current State**:
- Frontend `.env.production` points to `VITE_API_URL=https://54.237.223.146`
- Frontend code appends `/api` → requests go to `https://54.237.223.146/api`
- EC2 is NOT listening on HTTPS 443; only uvicorn on HTTP 8000 is running
- **Result**: All API calls from frontend fail with mixed-content/connection errors

**Evidence**: 
```bash
git log shows: "fix: correct EC2 API URL — remove :8000 port, nginx serves HTTPS on 443"
# But nginx is never actually installed in setup-ec2.sh
```

---

### 2. **Frontend Environment Variable Misconfiguration** (CRITICAL)
**Problem**:
- `.env.production` has hardcoded IP: `VITE_API_URL=https://54.237.223.146`
- This is the EC2 instance's public IP, but:
  - Only works if it has a stable elastic IP (currently it's ephemeral)
  - No port specified; frontend expects HTTPS 443
  - Not set in **Vercel dashboard environment variables** (the real source of truth)

**Current State**:
- Vercel frontend at: `https://frontend-six-flame-47.vercel.app/`
- Its `VITE_API_URL` is **undefined/not configured in Vercel**
- Falls back to relative `/api` (which tries to call the frontend's own origin)
- **Result**: Frontend can't reach backend, dashboard API calls fail

**Evidence**:
```bash
cat frontend/.env.production
# Output: VITE_API_URL=https://54.237.223.146
# ^ This is a local file, not synced to Vercel
```

---

### 3. **GitHub Actions CI Reports Success but EC2 Not Fully Deployed** (MEDIUM)
**Problem**:
- CI job "Deploy to EC2" shows ✅ success
- But the deployment SSH script only:
  - Pulls latest code
  - Installs Python deps
  - Restarts `jobtracker` systemd service
- **Does not**:
  - Install nginx
  - Generate SSL certs (Let's Encrypt / self-signed)
  - Configure SSL reverse proxy

**Evidence**:
```bash
git log: "Deploy to EC2" job last ran — shows success
# But EC2 is in broken state (no HTTPS, no nginx)
```

---

## 📋 Remediation Plan

### **Phase 1: Fix EC2 Deployment (Add nginx + SSL)**

#### Step 1a: Create `infra/scripts/setup-ec2-nginx.sh`
Install and configure nginx as SSL reverse proxy:
```bash
# Install nginx
sudo dnf install -y nginx certbot python3-certbot-nginx

# Create /etc/nginx/conf.d/jobtracker.conf
# - Listen on 443 (HTTPS)
# - Proxy all requests to uvicorn :8000
# - Auto-redirect 80 → 443

# Generate SSL cert (self-signed for now, or Let's Encrypt)
# Note: Public cert requires domain name + DNS

# Restart nginx
sudo systemctl enable nginx
sudo systemctl start nginx
```

**Impact**: EC2 will serve HTTPS on 443, proxy to backend on 8000.

#### Step 1b: Update GitHub Actions to run nginx setup
- Modify `.github/workflows/ci.yml` deploy step to run `setup-ec2-nginx.sh` after pulling code

**Timeline**: ~15 minutes

---

### **Phase 2: Fix Frontend Environment Variables (Vercel)**

#### Step 2a: Determine correct backend URL
Two options:
1. **If using EC2 with elastic IP**: `VITE_API_URL=https://your-stable-ip.com` (requires domain)
2. **If using AWS API Gateway/Lambda**: `VITE_API_URL=https://xxxxxxxxxx.execute-api.us-east-1.amazonaws.com`

**Current recommendation**: EC2 approach (simpler) but requires elastic IP + domain.

#### Step 2b: Set in Vercel dashboard
1. Go to: https://vercel.com/sabinmas-projects/jobapptracker/settings/environment-variables
2. Add/update variable:
   ```
   Name: VITE_API_URL
   Value: https://<YOUR-BACKEND-URL> (no port, no /api suffix)
   Environments: Production
   ```
3. Click "Save" → Vercel auto-redeploys

**Impact**: Frontend will call correct backend API.

**Timeline**: ~5 minutes

---

### **Phase 3: Verify Connectivity (Testing)**

#### Step 3a: Test EC2 health
```bash
# From your local machine
curl -k https://54.237.223.146/api/health
# Expected: {"status": "ok", ...}
```

#### Step 3b: Test frontend dashboard
1. Open: https://frontend-six-flame-47.vercel.app/
2. Wait for dashboard to load
3. Verify metrics appear (not error message)

**Timeline**: ~5 minutes

---

## 🚀 Implementation Order

| Order | Task | Owner | Estimated Time | Blocking? |
|-------|------|-------|-----------------|-----------|
| 1 | Create `setup-ec2-nginx.sh` | Backend Agent | 20 min | YES |
| 2 | Manual run nginx setup on EC2 | Manual (or Vercel deploy) | 15 min | YES |
| 3 | Verify HTTPS works: `curl -k https://54.237.223.146/api/health` | Manual | 5 min | YES |
| 4 | Update `.github/workflows/ci.yml` to include nginx setup | Backend Agent | 10 min | NO (but good for CI/CD) |
| 5 | Determine final backend URL (elastic IP + domain, or keep temp IP) | User decision | 5 min | MEDIUM |
| 6 | Set `VITE_API_URL` in Vercel dashboard | Manual | 5 min | YES |
| 7 | Verify frontend loads dashboard without errors | Manual | 5 min | YES |

---

## 🎯 Success Criteria

After remediation, all of these should pass:

```bash
# 1. EC2 HTTPS endpoint returns 200
curl -k https://54.237.223.146/api/health
# Response: {"status": "ok", ...}

# 2. Frontend loads without CORS errors
# Open: https://frontend-six-flame-47.vercel.app/
# Network tab: /api/dashboard/metrics returns 200, not CORS error

# 3. Dashboard page loads with real data
# Dashboard should show:
# - Jobs discovered (count)
# - Applications (count)
# - Score distribution (chart)
# - No red error boxes
```

---

## 📝 Notes

- **EC2 Public IP**: 54.237.223.146 (ephemeral — will change on reboot)
  - For stability: AWS → EC2 → Elastic IPs → Associate one to this instance
  - Then use elastic IP in `VITE_API_URL`
  
- **SSL Certificates**: 
  - Option A (simple, works now): Self-signed cert on EC2
  - Option B (production): Use Let's Encrypt with domain name
  
- **ALLOWED_ORIGINS**: Must include:
  - `https://frontend-six-flame-47.vercel.app`
  - `https://jobapptracker-n60pbf6ah-sabinmas-projects.vercel.app`
  - (Check `backend/.env` on EC2)

---

## 🔗 Key Files to Update

| File | Change | Why |
|------|--------|-----|
| `infra/scripts/setup-ec2-nginx.sh` | **CREATE** | Install nginx reverse proxy |
| `.github/workflows/ci.yml` | Update deploy step | Run nginx setup on CI/CD |
| `frontend/.env.production` | Keep as-is (or remove) | This is overridden by Vercel env vars |
| Vercel dashboard env vars | **SET `VITE_API_URL`** | Frontend reads this at build time |
| `backend/.env` (on EC2 instance) | Verify `ALLOWED_ORIGINS` | Already done, but verify during debug |

---

## 🛠️ Next Steps (For Claude Code Agent)

1. **Create `infra/scripts/setup-ec2-nginx.sh`** with nginx + SSL configuration
2. **Update `.github/workflows/ci.yml`** to call the new script
3. **Provide instructions** for user to:
   - Manually run nginx setup, OR
   - Trigger a new CI/CD deploy to EC2
   - Set `VITE_API_URL` in Vercel dashboard
   - Verify dashboard loads

---

**Prepared by**: Claude Code  
**Status**: Ready for implementation
