# Bedrock + Amazon Nova Setup Guide

> **TL;DR**: Amazon Nova models (Lite & Pro) are available immediately in Bedrock with NO approval gate. No Claude form needed.

---

## What's Configured

Your app is now set to use **Amazon Nova** models exclusively:

| Use Case | Model | Cost | Notes |
|----------|-------|------|-------|
| Resume extraction, scoring, field mapping | **Nova Lite** | $0.15/1M input, $0.60/1M output | Fast, good quality |
| Resume tailoring, cover letter generation | **Nova Pro** | $0.80/1M input, $3.20/1M output | Higher quality, slightly slower |

Both models:
- ✅ **Available immediately** (no approval form)
- ✅ Support structured output via tool-use
- ✅ Available in us-east-1 and us-west-2
- ✅ Paid via AWS credits (no separate API keys needed)

---

## Prerequisites

### 1. AWS Account with Bedrock Access
```bash
# Verify you have access to Bedrock:
# AWS Console → Bedrock → Overview
# Should show "Bedrock is available in your region"
```

### 2. AWS Credentials Configured
```bash
# Option A: Using AWS CLI profile
export AWS_PROFILE=default

# Option B: Environment variables
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
export AWS_REGION=us-east-1
```

### 3. Python Dependencies
```bash
pip install aioboto3>=12.0.0
```

---

## Verification Steps

### Step 1: Test Bedrock Connection
```bash
cd backend
python test_bedrock_nova.py
```

Expected output:
```
✓ Nova Lite responded: Nova works!
✓ Structured output succeeded: {'name': 'Alice', 'age': 30}
✓ Nova Pro responded: Code flows like streams...
ALL TESTS PASSED ✓
```

**If this fails**, check:
- AWS credentials are set correctly
- Region is correct (us-east-1 or us-west-2)
- Your AWS account has Bedrock access
- Run: `aws bedrock list-foundation-models --region us-east-1`

### Step 2: Test Resume Extraction
```bash
# Start backend with debug logging
cd backend
LOGLEVEL=DEBUG uvicorn app.main:app --reload --port 8000

# In another terminal, start frontend
cd frontend
npm run dev

# Upload a sample resume PDF to http://localhost:5173/profile
# Watch backend console for [EXTRACT] logs
```

Expected logs:
```
[EXTRACT] Parsing resume with AI...
Calling Bedrock Converse: model=amazon.nova-lite-v1:0, structured=True
Bedrock returned structured output successfully
[EXTRACT] ✓ Profile extracted: John Doe
[EXTRACT]   - Skills: 5 found
[EXTRACT]   - Experience: 3 entries
```

### Step 3: Test Full Pipeline
```
1. Profile page → Upload resume → Verify extraction
2. Save profile
3. Go to Preferences → Click "AI Suggest"
4. Go to Pipeline → Click "Run Now"
5. Monitor in Dashboard
```

---

## Configuration Options

### Default (Recommended)
```bash
# Uses Nova Lite for fast operations, Nova Pro for quality
AI_PROVIDER=bedrock
AWS_REGION=us-east-1
# BEDROCK_FAST_MODEL and BEDROCK_SMART_MODEL default to Nova
```

### Custom Models
```bash
# Override if needed (though Nova defaults are optimal)
export BEDROCK_FAST_MODEL=amazon.nova-lite-v1:0
export BEDROCK_SMART_MODEL=amazon.nova-pro-v1:0
```

### Fallback to Cerebras (If Nova unavailable)
```bash
# Only if Bedrock fails, will try Cerebras
export CEREBRAS_API_KEY=your_key
export CEREBRAS_MODEL=llama-3.3-70b
```

---

## Troubleshooting

### "Model is not available in the region"
- Nova Lite/Pro may not be available in all regions yet
- Try: `us-east-1` or `us-west-2`
- Set: `export AWS_REGION=us-east-1`

### "Access Denied" or "Not authorized"
- AWS credentials not set
- Run: `aws sts get-caller-identity` to verify credentials
- Check IAM permissions include `bedrock:InvokeModel`

### "No text response from Bedrock"
- Model may be overloaded or experiencing issues
- Check AWS Bedrock status page
- Fall back to Cerebras (set CEREBRAS_API_KEY)

### "Structured output failed" (tool-use)
- Nova models support tool-use, but schema must be valid JSON
- Check error logs for schema validation issues
- Fall back to Cerebras text parsing

### Resume extraction still showing "fill in manually"
1. Check backend logs: `LOGLEVEL=DEBUG`
2. Run test script: `python test_bedrock_nova.py`
3. Verify AWS credentials: `aws sts get-caller-identity`
4. Try different resume format (more text, less graphics)

---

## Performance Expectations

| Operation | Time | Model |
|-----------|------|-------|
| Extract profile from resume | 3-5s | Nova Lite |
| Score job (1-10) | 2-3s | Nova Lite |
| Generate cover letter | 8-12s | Nova Pro |
| Tailor resume | 10-15s | Nova Pro |

*Times vary based on input length and AWS load*

---

## Cost Estimation

**Assumptions**:
- 10 applications per day (30 working days/month)
- 300 applications/month

| Operation | Count | Cost |
|-----------|-------|------|
| Extract profile | 1 | $0.01 |
| Score jobs | 100 | $0.02 |
| Tailor resumes (Nova Pro) | 30 | $0.03 |
| Generate cover letters (Nova Pro) | 30 | $0.04 |
| **Monthly Total** | | **~$0.10** |

*(Bedrock is significantly cheaper than calling external APIs)*

---

## Next Steps

1. ✅ Run `python test_bedrock_nova.py` to verify setup
2. ✅ Upload a resume and watch extraction happen
3. ✅ Set job preferences and run pipeline
4. ✅ Monitor costs in AWS Bedrock console (virtually free for single user)

---

## References

- [AWS Bedrock Console](https://console.aws.amazon.com/bedrock)
- [Amazon Nova Models](https://aws.amazon.com/bedrock/nova/)
- [Bedrock Pricing](https://aws.amazon.com/bedrock/pricing/)
- [Bedrock API Docs](https://docs.aws.amazon.com/bedrock/latest/userguide/what-is-bedrock.html)

---

**Status**: ✅ Ready for production  
**Models**: Amazon Nova Lite + Pro (no gate)  
**Cost**: Minimal (~$0.10/month for 10 apps/day)
