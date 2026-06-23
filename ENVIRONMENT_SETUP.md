# Environment Configuration Guide

## Critical Issue: API Routing

This project uses a **Vercel proxy pattern** to avoid CORS and mixed-content issues:

```
Frontend (browser)
    ↓ /api/* (relative path, same origin)
Vercel Functions (proxy.ts, [...path].ts)
    ↓ BACKEND_API_URL env var
EC2 Backend (http://54.237.223.146)
```

### ⚠️ Vercel Environment Variables Required

**In Vercel Dashboard → JobApplicationTracker → Settings → Environment Variables:**

Set these for **Production** environment:

| Variable | Value | Notes |
|----------|-------|-------|
| `BACKEND_API_URL` | `http://54.237.223.146` | EC2 backend URL (or update if IP changes) |

### Why Not VITE_API_URL?

- **VITE_API_URL** is meant for direct browser-to-backend calls (client-side)
- ❌ We don't use it because that would create mixed-content issues (HTTPS frontend → HTTP backend)
- ✅ Instead, we use **Vercel proxy functions** which are server-side (no mixed-content issues)
- The proxy reads `BACKEND_API_URL` and forwards requests securely

### Frontend Environment Files

- `.env.local` - Vercel CLI token (auto-generated, don't edit)
- `.env.production` - Documentation only (frontend doesn't use VITE_API_URL)

### How to Fix the Blank Page Issue

1. **Verify Vercel env var is set:**
   ```
   BACKEND_API_URL = http://54.237.223.146
   ```

2. **Redeploy after setting the env var:**
   ```bash
   git push origin master
   # or manually trigger deployment in Vercel dashboard
   ```

3. **Check browser DevTools → Network tab:**
   - Requests to `/api/*` should succeed
   - Check response status and content

4. **If still failing:**
   - Check `api/proxy.ts` logs in Vercel Functions
   - Verify EC2 is running and accessible
   - Check EC2 security group allows inbound from Vercel IPs (0.0.0.0/0 if testing)

### Security Note on Self-Signed Certs

The proxy currently disables TLS verification:
```typescript
process.env.NODE_TLS_REJECT_UNAUTHORIZED = '0'
```

This is documented in `api/proxy.ts` and `api/[...path].ts` with the note:
- ⚠️ Acceptable only for bare-IP backend with self-signed cert
- 🔧 Long-term: Get EC2 a real domain + Let's Encrypt certificate

### Medium Priority: Fix Bundle Size

Vercel warns the JS bundle is **547 kB** (exceeds 500 kB recommend). Use dynamic imports to code-split the bundle.

### Medium Priority: Fix npm Vulnerabilities

Run:
```bash
npm audit fix
```

This will patch the 8 vulnerabilities (3 moderate, 5 high).

### Medium Priority: Populate Dashboard Data

The backend returns all metrics as zero. The scraper/pipeline needs to be triggered to collect job data.
