# Final Setup Checklist - studio-sabin-jobs.click

## Current Status

✅ **Completed:**
- npm vulnerabilities fixed (22 packages updated)
- Domain registered: `studio-sabin-jobs.click`
- Documentation created for all steps

⏳ **In Progress:**
- Domain registration completing (Route 53)
- DNS A record pointing to `54.237.223.146`

---

## Next Steps (In Order)

### Phase 1: Wait for Domain Registration (5-30 min)

**Status:** Watch Route 53 dashboard
- Should see status change from "In progress" → "Registered"
- Once complete, DNS should start propagating

**Verify:**
```bash
# Keep running this until it returns 54.237.223.146
nslookup studio-sabin-jobs.click
```

---

### Phase 2: Set Up HTTPS on EC2 (5 minutes)

**When:** After domain is registered and DNS propagates

**Follow:** `EC2_HTTPS_SETUP.md` in this repo

**Quick steps:**
1. SSH into EC2
2. Install certbot
3. Get Let's Encrypt certificate for `studio-sabin-jobs.click`
4. Configure nginx to use the certificate
5. Restart nginx

**Result:** 
- `https://studio-sabin-jobs.click/api/...` works
- HTTP automatically redirects to HTTPS

---

### Phase 3: Update Vercel Environment Variable (2 minutes)

**When:** After HTTPS is verified working

**Follow:** `VERCEL_ENV_UPDATE.md` in this repo

**Steps:**
1. Vercel Dashboard → JobApplicationTracker → Settings → Environment Variables
2. Change `BACKEND_API_URL`:
   ```
   FROM: http://54.237.223.146
   TO:   https://studio-sabin-jobs.click
   ```
3. Save

---

### Phase 4: Redeploy Frontend (2 minutes)

**When:** After Vercel env var is updated

**How:**
```bash
git push origin master
# or manually trigger in Vercel dashboard
```

**What this does:**
- Vercel rebuilds the frontend with new environment
- New env var is available to proxy functions
- Frontend can now reach backend via HTTPS

---

## Verification Checklist

After all phases complete, verify:

- [ ] Domain resolves: `nslookup studio-sabin-jobs.click` → `54.237.223.146`
- [ ] HTTPS works: `curl https://studio-sabin-jobs.click/api/dashboard/metrics`
- [ ] Certificate is valid: Check browser padlock icon
- [ ] Frontend loads: `https://frontend-six-flame-47.vercel.app`
- [ ] No blank page (data loads)
- [ ] Network requests in DevTools show 200 status
- [ ] No console errors

---

## Timeline Summary

| Phase | Task | Time | Status |
|-------|------|------|--------|
| 1 | Domain registration | ~30 min | ⏳ In progress |
| 2 | Set up HTTPS on EC2 | ~5 min | ⏱️ Waiting for Phase 1 |
| 3 | Update Vercel env var | ~2 min | ⏱️ Waiting for Phase 2 |
| 4 | Redeploy frontend | ~2 min | ⏱️ Waiting for Phase 3 |
| **Total** | | **~40 min** | |

---

## Important Links

- 📋 **Setup Guides:**
  - `EC2_HTTPS_SETUP.md` - HTTPS configuration
  - `VERCEL_ENV_UPDATE.md` - Environment variable update
  - `ENVIRONMENT_SETUP.md` - Architecture explanation
  - `DEPLOYMENT_CHECKLIST.md` - Troubleshooting guide

- 🔗 **AWS:**
  - Route 53: https://console.aws.amazon.com/route53

- 🔗 **Vercel:**
  - Dashboard: https://vercel.com/dashboard
  - JobApplicationTracker: https://vercel.com/dashboard/jobtracker

- 🔗 **Frontend:**
  - Deployed: https://frontend-six-flame-47.vercel.app

---

## Questions?

If anything is unclear or fails:

1. Check the relevant `.md` file in this repo
2. Look at the troubleshooting sections
3. Provide:
   - Screenshot of the error
   - Output of the command that failed
   - Current status (which phase you're in)

---

## What This Fixes

✅ **Blank page issue** - Backend is now reachable via HTTPS
✅ **Mixed-content warning** - HTTPS frontend talks to HTTPS backend
✅ **npm vulnerabilities** - All 8 vulnerabilities patched
✅ **Domain routing** - Traffic goes through proper domain name
✅ **Auto-renewal** - SSL certificate auto-renews every 90 days

---

## After This Works

Once the blank page is fixed, next priorities:

- [ ] **Optional:** Reduce bundle size (Vite code-splitting)
- [ ] **Optional:** Populate dashboard with real job data (trigger scraper)
- [ ] **Future:** Add AWS ALB for even better HTTPS handling
