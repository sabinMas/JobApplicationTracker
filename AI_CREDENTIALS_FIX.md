# AI Extraction Fix Guide

## Problem
Profile extraction (skills, education, work experience, summary) is not working because both AI providers are failing:
- **Bedrock:** Model versions are end-of-life or unavailable in your AWS account
- **Cerebras:** API key is invalid/expired (401 error)

## Root Cause
When users upload resumes, the backend tries to use these AI services to extract structured data. If both fail, it returns an empty profile.

**This has been fixed in the code** (commit `f556644`):
- ✅ Improved extraction prompts to explicitly request all fields
- ✅ Enhanced JSON schema with clear field definitions
- ⚠️ But extraction still fails because credentials are invalid

## Solution

You have **two options**:

### Option 1: Fix Bedrock (Recommended if you have AWS account)

**Problem:** Your Bedrock model IDs are outdated or not available in your account.

**Fix:**
1. Go to AWS Console → Bedrock → Model Catalog
2. Check which Claude models are available in your region
3. Find the ARN or ID of the latest Claude 3.5 or Claude 4 model
4. Update `backend/.env`:
```bash
# Find your actual available models from Bedrock console
BEDROCK_FAST_MODEL=<your-available-claude-model>
BEDROCK_SMART_MODEL=<your-available-claude-model>

# Or request access to Claude models if blocked
```

**Example (if available):**
```bash
BEDROCK_FAST_MODEL=anthropic.claude-3-5-sonnet-20241022-v2:0
BEDROCK_SMART_MODEL=anthropic.claude-3-5-sonnet-20241022-v2:0
```

### Option 2: Fix Cerebras (Quick if you have Cerebras account)

**Problem:** Your Cerebras API key is invalid or expired.

**Fix:**
1. Go to https://www.cerebras.ai/ → Sign in to your account
2. Generate a new API key (or check your existing key)
3. Update `backend/.env`:
```bash
CEREBRAS_API_KEY=<your-new-valid-api-key>
# Force use of Cerebras as primary
AI_PROVIDER=cerebras
```

### Option 3: Set AI_PROVIDER to prefer Cerebras

If Bedrock is too complicated, just use Cerebras as primary:

```bash
# backend/.env
AI_PROVIDER=cerebras
CEREBRAS_API_KEY=<your-valid-api-key>
```

## Verify the Fix

After updating credentials:

```bash
# Restart backend
pkill -f uvicorn
cd backend && uvicorn app.main:app --reload --port 8000 &

# Test extraction
python test_extraction.py

# Expected output:
# - Name: Jane Doe
# - Summary: Full-stack engineer with...
# - Skills (8+): Python, TypeScript, React, ...
# - Experience (2+): Senior Software Engineer @ TechCorp, ...
# - Education (2+): M.S. Computer Science from UC Berkeley, ...
# - Certifications (2+): AWS Certified Solutions Architect, ...
```

## Code Changes Made

✅ **Commit `f556644`:** Improved resume extraction
- Enhanced system prompt to explicitly list all fields
- Added field descriptions to JSON schema
- Clarified that skills and summary are required
- Improved structured output schema for nested objects

This means once you fix the credentials, extraction will immediately work better.

## What Users Will Experience

### Before (Without Credentials)
- Upload resume
- See empty Skills, Education, Work Experience sections
- Must manually fill in all fields

### After (With Credentials Fixed)
- Upload resume
- See extracted data automatically:
  - ✅ Full name, email, phone
  - ✅ Professional summary (2-4 sentences)
  - ✅ Skills (list of all technologies)
  - ✅ Work experience (company, title, date, achievements)
  - ✅ Education (school, degree, field)
  - ✅ Certifications

## Troubleshooting

### Still seeing empty profiles after fixing credentials?

1. **Check backend logs for errors:**
   ```bash
   tail -50 /tmp/backend.log | grep -i "extract\|error"
   ```

2. **Verify .env is loaded:**
   ```bash
   grep CEREBRAS_API_KEY backend/.env
   grep AI_PROVIDER backend/.env
   ```

3. **Restart backend (important!):**
   ```bash
   pkill -f uvicorn
   cd backend && uvicorn app.main:app --reload --port 8000 &
   ```

4. **Test with test_extraction.py again**

### Still getting 401 on Cerebras?

- The API key might be malformed
- Try generating a new one from Cerebras dashboard
- Make sure there are no extra spaces in `backend/.env`

### Bedrock AccessDenied / EOL errors?

- Your AWS account doesn't have access to that Claude version
- Contact AWS Support to enable Claude models on Bedrock
- Or check if you need to request access to newer models
- Fallback: Use Cerebras instead (set `AI_PROVIDER=cerebras`)

## Next Steps

1. **Choose Bedrock or Cerebras** (Option 1 or 2 above)
2. **Update backend/.env** with valid credentials
3. **Restart the backend server**
4. **Test upload** a sample resume to Profile page
5. **Verify** Skills, Education, Work Experience appear

## Impact

Once credentials are fixed:
- Resume uploads will auto-extract all profile fields
- Users can skip manual data entry
- Profile-based features (preferences, resume tailoring) will work better
- Auto-apply will have better data to work with

---

**Questions?** Check your AWS Bedrock account status or Cerebras API key validity.
