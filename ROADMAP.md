# JobApplicationTracker - Strategic Roadmap 2026

**Vision**: 10 high-quality applications per day to niche jobs matching user expertise, with intelligent routing, observability, and future AI orchestration.

**Current User**: Mason (single user, personal use, quality over quantity)

---

## Phase 1: Foundation (Weeks 1-2) — **START HERE**

### Priority Ranking (by ROI)

#### 🥇 **Tier 1: Observability & Resilience** (Days 1-4)
*Without visibility & recovery, scaling is reckless.*

**Tasks**:
1. **Structured Logging System**
   - Migrate from print() to Python logging + structured JSON logs
   - Log to CloudWatch (AWS Lambda native integration)
   - Fields: timestamp, session_id, application_id, step, status, error, duration
   - Impact: Debug failures, identify patterns, measure success rates

2. **Application Failure Tracking**
   - Add `retry_count`, `last_error`, `error_history[]` to Application model
   - Implement retry logic: exponential backoff (1s, 4s, 16s, 64s)
   - Max 3 retries per application, different ATS detection on retry
   - Impact: 80%+ applications recover from transient failures

3. **Monitoring Dashboard (Simple)**
   - Metrics to track:
     - Applications submitted today/week/month
     - Success rate (submitted / attempted)
     - Average time per application
     - Top failing ATS platforms
     - Top job sources
   - Store metrics in RDS (one metric row per application submission attempt)
   - Frontend: GET /api/metrics endpoint returning timeseries data

**Effort**: 2-3 days  
**Impact**: Unblock scaling, gain confidence in automation quality

---

#### 🥈 **Tier 2: Intelligent Routing** (Days 5-8)
*Route jobs to the best automation method per ATS platform.*

**Tasks**:
1. **ATS API Integration Framework**
   - Create `services/ats_routers/` with platform-specific handlers:
     ```
     ats_routers/
     ├── base.py              # Abstract router
     ├── greenhouse.py        # Greenhouse API
     ├── lever.py             # Lever API
     ├── workday.py           # Workday API
     ├── linkedin.py          # LinkedIn API
     └── form_fallback.py     # Generic form filler (current)
     ```
   - Each router has `can_handle(job_url)` and `submit(job, profile)` methods
   - Decision tree: Greenhouse URL → use Greenhouse API, else → form filler

2. **Greenhouse API Integration** (First platform)
   - Authenticate with Greenhouse user account
   - POST /api/ats/greenhouse/auth (stores credentials securely in .env)
   - For Greenhouse jobs: API call instead of form filling (95% success rate vs 70% form)
   - Fallback to form filling if API fails

3. **Lever API Integration** (Second priority)
   - Similar to Greenhouse
   - Lever uses different JSON schema

**Effort**: 3-4 days  
**Impact**: 15-20% faster, 10-15% higher success rate on known platforms

---

#### 🥉 **Tier 3: Job Source Expansion** (Days 9-14)
*Feed the system more quality jobs to apply to.*

**Tasks**:
1. **LinkedIn API Integration**
   - Setup LinkedIn Developer App
   - OAuth flow: `POST /api/auth/linkedin` → browser redirect → callback
   - Scrape authenticated: Jobs in feed matching criteria
   - Store as Job source="linkedin_api"
   - Cron job: Daily refresh of LinkedIn feed

2. **GitHub Jobs API**
   - GET https://jobs.github.com/positions.json
   - Parse & store (no auth needed)
   - Daily sync

3. **Angel List (Wellfound) API**
   - Query by skills, location
   - Store startup jobs

4. **RSS Feed Support**
   - Accept custom RSS URL: `POST /api/jobs/subscribe-rss`
   - Fetch hourly, parse, store new jobs

5. **Existing Scrapers Enhancement**
   - LinkedIn web scrape (without API) for non-authenticated users
   - Indeed enhanced parsing
   - Custom company career pages (allow user to add URLs)

**Effort**: 4-5 days  
**Impact**: 10x more jobs available per day

---

### Phase 1 Deliverables
- ✅ Structured logging + CloudWatch integration
- ✅ Retry logic + failure recovery
- ✅ Metrics tracking + monitoring endpoint
- ✅ ATS router framework (decision logic)
- ✅ Greenhouse API working end-to-end
- ✅ LinkedIn API + GitHub + Angel List integrations
- ✅ RSS feed subscription support

**Output**: System can handle 10 applications/day with visibility into success/failure

---

## Phase 2: Serverless Infrastructure (Weeks 3-4)

### AWS Lambda Migration

**Context**: Current = Railway (always-on). Target = Lambda (pay-per-invocation).

**Architecture**:
```
User Request
  ↓
API Gateway (REST endpoint)
  ↓
Lambda Container (FastAPI/Uvicorn inside Lambda)
  ↓
RDS PostgreSQL (AWS Managed)
  ↓
S3 (Resume PDFs, generated docs)
  ↓
CloudWatch (Logs, Metrics)
  ↓
SQS (Job queue for scheduler)
  ↓
EventBridge (Cron for daily sync)
```

**Tasks**:
1. **Lambda Containerization**
   - Create `docker/lambda.Dockerfile` (based on current Dockerfile)
   - Test locally with SAM CLI
   - Deploy via AWS CDK or CloudFormation

2. **RDS Migration**
   - Provision AWS RDS PostgreSQL
   - Update `DATABASE_URL` env var
   - Run schema migration (create tables)
   - Test connection pooling (RDS Proxy for Lambda)

3. **S3 Integration**
   - Move resume PDFs from `data/documents/` to S3
   - Update Document model: `s3_key` instead of `file_path`
   - Serve downloads via S3 presigned URLs

4. **SQS Job Queue**
   - Replace in-memory scheduler with SQS
   - Lambda consumer: polls SQS every 5 minutes
   - Processes queued applications (retry logic)
   - DLQ for permanently failed jobs

5. **EventBridge Scheduler**
   - Daily job sync: trigger `POST /api/jobs/sync` at 8 AM
   - Refresh LinkedIn, GitHub, Indeed feeds
   - User-configurable via `PUT /api/scheduler/config`

**Effort**: 5-7 days  
**Impact**: 90% cost reduction + infinite scalability

---

## Phase 3: Enhanced AI & Routing (Weeks 5-6)

### AgentCore Integration (Exploratory)

**Hypothesis**: AgentCore can orchestrate multi-step workflows better than sequential code.

**Potential Uses**:
1. **Intelligent Job Scoring**
   - AgentCore agent: "Score this job 1-10 for fit"
   - Inputs: job description + user profile + past applications
   - Output: score + reasoning
   - Apply only to score ≥ 8

2. **Adaptive Form Filling**
   - Agent: "This form asks unusual questions. How should I fill them?"
   - Inputs: form fields + job description + user profile
   - Output: field→value mapping + confidence scores
   - Only auto-fill if confidence > 95%

3. **Failure Analysis**
   - Agent: "Why did this application fail?"
   - Inputs: error logs + form screenshot
   - Output: root cause + suggested fix
   - Escalate to human if unrecoverable

**Next Steps**: 
- Evaluate AgentCore pricing/latency vs Cerebras
- Pilot one workflow (e.g., job scoring)
- Compare results vs current system

**Timeline**: Week 5-6 (exploratory, not blocking other work)

---

## Phase 4: Strands Workflow Integration (Weeks 7-8)

### Strands as Workflow Orchestrator

**Vision**: Model the bulk auto-apply process as a Strands workflow.

**Workflow Design**:
```
START
  ↓
[GATHER] Fetch candidate profile + matching jobs
  ↓
FOR EACH job:
  ├─ [SCORE] Use AgentCore to evaluate fit
  ├─ [DECIDE] Apply only if score ≥ 8?
  │   ├─ NO → skip
  │   └─ YES → continue
  ├─ [ROUTE] Greenhouse API or form filler?
  ├─ [SUBMIT] Execute submission
  ├─ [VERIFY] Success?
  │   ├─ YES → mark as "applied"
  │   ├─ NO → queue for retry
  │   └─ ERROR → human review
  └─ [TRACK] Log metrics
  ↓
END
```

**Benefits**:
- Visual workflow design (Strands UI)
- Automatic error handling + retries
- Human-in-the-loop checkpoints
- Performance monitoring per step

**Timeline**: Week 7-8 (requires AgentCore metrics first)

---

## Phase 5: Contact & Email Tracking (Weeks 9-10)

### Post-Application Follow-up

**Tasks**:
1. **Email Tracking Setup**
   - Integrate SendGrid or AWS SES
   - For each application, record:
     - Application email sent timestamp
     - First open (if trackable)
     - Link clicks
   - Store in Application `email_opened_at`, `email_first_clicked_at`

2. **Phone Number Tracking**
   - Record call logs (if using Twilio)
   - Parse voicemail transcriptions
   - Store in Application `phone_call_log[]`

3. **Interview Notifications**
   - Monitor email for interview requests (keyword matching)
   - Alert user via SMS/Slack
   - Parse meeting times from email, add to calendar

4. **Status Progression Tracking**
   - Auto-update Application status based on email:
     - "Interview scheduled" → status = "phone_screen"
     - "Offer extended" → status = "offer"
     - "Rejected" → status = "rejected"

**Effort**: 3-4 days  
**Impact**: Complete feedback loop on job applications

---

## Phase 6: Niche Job Intelligence (Weeks 11-12)

### ML-Powered Job Recommendations

**Tasks**:
1. **Job Relevance Scoring**
   - Offline: Process all available jobs through ML model
   - Score by: skill match, seniority, company, location, salary
   - Store score in Job `relevance_score` (0-100)
   - Only suggest jobs with score ≥ 75

2. **Underrated Job Detection**
   - Track: Application count per job (from public ATS boards)
   - Low application count = less competition
   - Recommend low-competition jobs matching user profile
   - (e.g., "This startup job 3 people applied vs 500 for Google")

3. **Company Research Auto-Population**
   - For each job, fetch company info: size, funding, glassdoor rating, recent news
   - Store in Job `company_metadata` JSON
   - Help user make informed decisions

**Effort**: 4-5 days  
**Impact**: 10x better job matching (quality over quantity)

---

## Implementation Priority Summary

### **Week 1 (Days 1-5): Start Here → Maximum Impact**

| Day | Task | Why |
|-----|------|-----|
| 1-2 | Structured logging + CloudWatch | Unblock confident scaling |
| 2-3 | Retry logic + failure tracking | Stop losing applications to transient errors |
| 4 | Greenhouse API integration | 15-20% faster, more reliable |
| 5 | Monitoring dashboard | Prove ROI to yourself |

**Commit Message**: `feat: observability & intelligent routing foundation`

### **Week 2 (Days 6-10): Scale Job Discovery**

| Day | Task |
|-----|------|
| 6-7 | LinkedIn API + GitHub Jobs |
| 8 | Angel List + RSS support |
| 9-10 | Enhanced Indeed/LinkedIn web scrapers |

**Commit Message**: `feat: multi-source job discovery (5x more jobs)`

### **Week 3-4 (Days 11-20): Lambda Migration**

| Day | Task |
|-----|------|
| 11-13 | Lambda containerization + RDS |
| 14-15 | S3 storage + SQS queue |
| 16-17 | EventBridge cron jobs |
| 18-20 | Testing + cost optimization |

**Commit Message**: `infra: AWS Lambda + serverless architecture`

---

## Success Metrics (After Phase 1)

After implementing Week 1-2, measure:

✅ **10 applications submitted per day** (goal)  
✅ **Success rate ≥ 90%** (submitted successfully)  
✅ **Avg time per application ≤ 2 min** (including retry)  
✅ **Zero manual intervention required**  
✅ **Detailed logs for every failure** (root cause analysis)  
✅ **Job quality score ≥ 8/10** (relevance to Mason's profile)

---

## Open Questions for Mason

1. **LinkedIn Authentication**: Do you want to authenticate with your real LinkedIn account?
   - *Implication*: Can access authenticated job feed, but LinkedIn may block automation. Alternative: web scraping (slower but undetectable).

2. **Workday & Other Large Enterprise ATS**: Many Fortune 500 companies use Workday.
   - Should we prioritize Workday API after Greenhouse/Lever?
   - Or focus on startup/mid-market jobs first (simpler ATS)?

3. **Application Quality Filters**: 10/day is ambitious but achievable.
   - What's your minimum job quality threshold?
   - Minimum salary? Location preferences? Company size? Industry?
   - Should system auto-reject jobs outside these criteria?

4. **Interview Prep Module** (Post-Phase 6):
   - Once you're getting interviews, want mock interview bot with Cerebras/AgentCore?
   - Practice technical + behavioral questions?

5. **Budget**: What's your AWS budget comfort zone?
   - Estimate for Phase 2 (Lambda): $5-20/month (depends on application volume)
   - Estimate for storage (S3): $0.50-2/month
   - Estimate for RDS: $10-30/month (shared tier)

---

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| Job boards block automation | Rotating user agents, randomized delays, respect robots.txt |
| ATS platform changes selectors | Frequent selector refresh, fallback to form filler, manual override |
| LinkedIn ToS violation | Use web scraping vs API (slower but permitted) |
| Lambda cold starts (latency) | Provisioned concurrency, keep Python runtime warm |
| Data loss on S3 | Enable versioning + cross-region replication |
| False positives in job scoring | Manual review of jobs with score 7-9, feedback loop |

---

## Next Action: Start Phase 1, Day 1

**Immediate tasks**:
1. Read this roadmap & confirm direction
2. Choose: structured logging framework (Python `logging` or `structlog`)
3. Choose: CloudWatch integration method (AWS Lambda SDK or 3rd party)
4. Clone repo + create `feature/observability` branch
5. I'll write the logging system + first test

**Estimated time**: 30 min for you (approval + choice), 4-6 hours me (implementation + testing)

---

**Ready to proceed?** I can start Phase 1, Day 1 (Observability) immediately.

