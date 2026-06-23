# Vercel Environment Variable Update

## Action Required in Vercel Dashboard

**Project:** JobApplicationTracker
**Environment:** Production (and Preview if desired)

### Update This Variable:

**Current Value:**
```
BACKEND_API_URL = http://54.237.223.146
```

**New Value:**
```
BACKEND_API_URL = http://studio-sabin-jobs.click
```

### Steps:

1. Go to: https://vercel.com/dashboard
2. Select: JobApplicationTracker project
3. Settings → Environment Variables
4. Find: `BACKEND_API_URL`
5. Edit the value to: `http://studio-sabin-jobs.click`
6. Save

### After Updating:

- Git push to trigger redeploy:
  ```bash
  git push origin master
  ```
- Or manually redeploy from Vercel dashboard

### Timeline:

- Domain registration: **In Progress** (usually 5-30 min)
- DNS propagation: **5-30 min** after registration completes
- Test: `ping studio-sabin-jobs.click` should resolve to 54.237.223.146
