# Frontend Integration — Action Plan

**Your live Lambda API is ready. Here's how to connect your frontend.**

---

## Step 1: Update Your Frontend Configuration

### In your React project

#### Option A: Using `.env.local` (Recommended)

Create or edit `.env.local` in your project root:

```
VITE_API_URL=https://slysl7v476awcx4754dv5osg3e0jjzqf.lambda-url.us-east-1.on.aws
```

Then in your code:
```javascript
const apiUrl = import.meta.env.VITE_API_URL
```

#### Option B: Using `vite.config.ts`

Add to your vite config:
```javascript
export default defineConfig({
  define: {
    'import.meta.env.VITE_API_URL': 
      JSON.stringify('https://slysl7v476awcx4754dv5osg3e0jjzqf.lambda-url.us-east-1.on.aws')
  }
})
```

---

## Step 2: Update Your API Client

### If using fetch:

```javascript
// src/api/client.ts (or similar)
const API_URL = import.meta.env.VITE_API_URL

export const fetchJobs = async () => {
  const response = await fetch(`${API_URL}/api/jobs`)
  return response.json()
}

export const syncJobs = async () => {
  const response = await fetch(`${API_URL}/api/jobs/sync`, {
    method: 'POST'
  })
  return response.json()
}

export const getMetrics = async () => {
  const response = await fetch(`${API_URL}/api/metrics/dashboard`)
  return response.json()
}
```

### If using axios:

```javascript
import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL
})

export const jobsApi = {
  fetchJobs: () => api.get('/api/jobs'),
  syncJobs: () => api.post('/api/jobs/sync'),
  getMetrics: () => api.get('/api/metrics/dashboard')
}
```

### If using React Query:

```javascript
import { useQuery, useMutation } from '@tanstack/react-query'

const API_URL = import.meta.env.VITE_API_URL

export const useJobs = () => {
  return useQuery({
    queryKey: ['jobs'],
    queryFn: async () => {
      const res = await fetch(`${API_URL}/api/jobs`)
      return res.json()
    }
  })
}

export const useSyncJobs = () => {
  return useMutation({
    mutationFn: async () => {
      const res = await fetch(`${API_URL}/api/jobs/sync`, {
        method: 'POST'
      })
      return res.json()
    }
  })
}
```

---

## Step 3: Test the Connection

### Simple test in browser console:

```javascript
const API_URL = 'https://slysl7v476awcx4754dv5osg3e0jjzqf.lambda-url.us-east-1.on.aws'

// Health check
fetch(`${API_URL}/health`).then(r => r.json()).then(console.log)

// Get jobs
fetch(`${API_URL}/api/jobs`).then(r => r.json()).then(console.log)

// Trigger sync
fetch(`${API_URL}/api/jobs/sync`, {method: 'POST'}).then(r => r.json()).then(console.log)
```

### Using curl from terminal:

```bash
# Health check
curl https://slysl7v476awcx4754dv5osg3e0jjzqf.lambda-url.us-east-1.on.aws/health

# Get jobs
curl https://slysl7v476awcx4754dv5osg3e0jjzqf.lambda-url.us-east-1.on.aws/api/jobs

# Trigger sync
curl -X POST https://slysl7v476awcx4754dv5osg3e0jjzqf.lambda-url.us-east-1.on.aws/api/jobs/sync
```

---

## Step 4: Handle CORS (If Needed)

The Lambda function already has CORS enabled for all origins:
```
Allow-Origin: *
Allow-Methods: GET, POST, PUT, DELETE, OPTIONS
Allow-Headers: *
```

If you still have CORS issues, they're likely local development issues:

```javascript
// If developing locally, browser may need credentials
fetch(`${API_URL}/api/jobs`, {
  credentials: 'include'  // Include cookies if needed
})
```

---

## Step 5: Available Endpoints

### Health Check
```bash
GET /health
Response: {"status":"ok","service":"JobApplicationTracker","db_initialized":false}
```

### Fetch Jobs
```bash
GET /api/jobs?source=github&limit=50
Response: [{"id":1,"title":"Senior Backend Engineer","source":"github",...}]
```

### Trigger Job Sync
```bash
POST /api/jobs/sync
Response: {"status":"syncing","sources_active":5,"next_sync_in_seconds":3600}
```

### Get Scheduler Status
```bash
GET /api/scheduler/jobs/status
Response: {"last_sync_at":"2026-06-05T17:00:00","next_sync_at":"2026-06-05T18:00:00"}
```

### Get Metrics
```bash
GET /api/metrics/dashboard?days=7
Response: {"total_applications":42,"success_rate":0.856,"by_ats_platform":[...]}
```

---

## Step 6: Monitor in CloudWatch

```bash
# View logs in real-time
aws logs tail /aws/lambda/jobtracker-api --follow

# Follow logs for your requests
aws logs tail /aws/lambda/jobtracker-api --follow --since 1m
```

---

## Example React Component

```javascript
import { useEffect, useState } from 'react'

export function JobsList() {
  const [jobs, setJobs] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const API_URL = import.meta.env.VITE_API_URL

  useEffect(() => {
    const fetchJobs = async () => {
      setLoading(true)
      try {
        const response = await fetch(`${API_URL}/api/jobs`)
        const data = await response.json()
        setJobs(data)
      } catch (err) {
        setError(err.message)
      } finally {
        setLoading(false)
      }
    }

    fetchJobs()
  }, [])

  const handleSync = async () => {
    setLoading(true)
    try {
      const response = await fetch(`${API_URL}/api/jobs/sync`, {
        method: 'POST'
      })
      const data = await response.json()
      console.log('Sync result:', data)
      // Re-fetch jobs after sync
      const jobsResponse = await fetch(`${API_URL}/api/jobs`)
      const jobsData = await jobsResponse.json()
      setJobs(jobsData)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  if (loading) return <div>Loading...</div>
  if (error) return <div>Error: {error}</div>

  return (
    <div>
      <button onClick={handleSync}>Sync Jobs</button>
      <ul>
        {jobs.map(job => (
          <li key={job.id}>{job.title} - {job.source}</li>
        ))}
      </ul>
    </div>
  )
}
```

---

## Troubleshooting

### "CORS error" or "no response"
- Check if Lambda URL is correct
- Ensure you're using HTTPS (not HTTP)
- Check browser DevTools Network tab
- Run `curl` to test directly

### "Database connection error" in response
- Lambda can't reach PostgreSQL
- Check AWS CloudWatch logs
- Verify database is running
- Check security group allows port 5432

### "404 Not Found"
- Check endpoint path (must start with `/`)
- Verify Lambda function is deployed
- Test with `/health` first

### Application works locally but not on frontend
- Ensure `.env.local` is loaded (restart dev server)
- Check `import.meta.env.VITE_API_URL` is not undefined
- Use `console.log(import.meta.env)` to debug

---

## Verification Checklist

- [ ] `.env.local` updated with Lambda URL
- [ ] Frontend dev server restarted
- [ ] API URL loaded in app (test with console.log)
- [ ] `/health` endpoint responding
- [ ] `/api/jobs` endpoint returning data
- [ ] Jobs displaying in UI
- [ ] Sync button working
- [ ] CloudWatch logs showing requests

---

## Next Actions

1. **Update `.env.local`** with the Lambda URL
2. **Restart your dev server** (`npm run dev`)
3. **Test health endpoint** in browser console
4. **Display jobs** in your UI
5. **Add sync button** to trigger manual sync
6. **Monitor logs** as you test

---

## Lambda URL (For Reference)

```
https://slysl7v476awcx4754dv5osg3e0jjzqf.lambda-url.us-east-1.on.aws/
```

Copy this into your `.env.local` as `VITE_API_URL`

---

**Ready to connect? Start with Step 1! 🚀**
