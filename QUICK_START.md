# Quick Start - Fix Blank Page

## TL;DR

Your frontend shows blank because the backend isn't reachable. We're fixing it with a domain name.

---

## What You Just Did ✅

1. Registered domain: `studio-sabin-jobs.click`
2. Fixed npm vulnerabilities
3. Created setup guides

---

## What's Happening Now ⏳

Domain is registering in Route 53 (check AWS console).

---

## What You Need to Do Next

### When Domain is Registered (AWS will notify you):

**1. Verify DNS (run in terminal):**
```bash
nslookup studio-sabin-jobs.click
# Should return: 54.237.223.146
```

**2. SSH into EC2 and run HTTPS setup:**
```bash
ssh -i your-key.pem ec2-user@54.237.223.146

# Install certbot
sudo yum install certbot python3-certbot-nginx -y

# Get SSL certificate
sudo certbot certonly --standalone -d studio-sabin-jobs.click --agree-tos -m admin@studio-sabin-jobs.click

# Copy the full HTTPS setup from EC2_HTTPS_SETUP.md and apply to nginx
```

**3. Update Vercel environment:**
- Go to: https://vercel.com/dashboard
- Project: JobApplicationTracker
- Settings → Environment Variables
- Change `BACKEND_API_URL` from `http://54.237.223.146` to `https://studio-sabin-jobs.click`

**4. Redeploy:**
```bash
git push origin master
```

---

## Result

✅ Frontend loads without blank page
✅ Dashboard shows data
✅ No more mixed-content warnings

---

## Full Guides

- **HTTPS Setup:** `EC2_HTTPS_SETUP.md`
- **Env Variable:** `VERCEL_ENV_UPDATE.md`
- **Complete Checklist:** `FINAL_SETUP_CHECKLIST.md`
- **Troubleshooting:** `DEPLOYMENT_CHECKLIST.md`

---

## Questions?

Read the guides above. They have step-by-step instructions.
