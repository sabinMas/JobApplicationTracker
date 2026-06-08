# Decision Framework: Key Strategic Choices

**Purpose**: Document critical decisions for JobApplicationTracker evolution  
**Audience**: Mason (user), Future developers, AI agents  
**Status**: Active (update as decisions are made)

---

## Decision 1: Quality vs. Quantity Target

**Question**: 10 quality applications per day — how do we define "quality"?

**Context**:
- Current system applies to any job matching basic filters
- Risk: 90% rejection rate on low-quality matches wastes time on both ends
- Opportunity: Focus on 10 perfect matches > 100 mediocre matches

**Options**:

| Option | Approach | Pros | Cons | ROI |
|--------|----------|------|------|-----|
| **Threshold-based** | Only apply if job score ≥ 8/10 by AI | High precision, low rejection | May miss good jobs, slow discovery | ⭐⭐⭐⭐⭐ |
| **Manual review** | Human reviews each job before auto-apply | Full control, no surprises | Defeats purpose (defeats automation) | ⭐⭐ |
| **ML ranking** | Train model on past applications → predict fit | Learns from feedback, improves over time | Requires historical data (cold start) | ⭐⭐⭐⭐ |
| **Niche detection** | Find underrated jobs (low application count) | Less competition, more callbacks | May be lower quality on average | ⭐⭐⭐ |

**Decision**: **Threshold-based + Niche detection** (Phase 1 + Phase 6)

- **Phase 1-4**: Implement AI job scoring (8/10 threshold)
- **Phase 6**: Add niche detection (low-competition jobs)
- **Future**: Layer in ML ranking as we accumulate data

**Implementation**:
```python
# Scoring logic (cerebras_service.py)
async def score_job_fit(job: dict, profile: dict, past_applications: list) -> dict:
    """
    Score job 1-10 for fit.
    Returns: {"score": 8, "reasoning": "...", "flags": [...]}
    """
    # Use AgentCore or Cerebras
    # Inputs: job desc + profile + past rejections
    # Output: score, reasoning, red flags
    
# Decision logic (auto_apply.py)
if job_score >= 8:
    apply()
elif job_score >= 7 and is_niche_job(job):
    apply()  # Niche jobs with lower score worth trying
else:
    skip()
```

**Success Metric**: 
- ✅ 10 applications per day
- ✅ < 5% immediate rejections (score too low)
- ✅ > 30% phone screen rate (quality working)

---

## Decision 2: ATS API vs. Form Filling

**Question**: For major ATS platforms (Greenhouse, Workday, Lever), use API or form?

**Context**:
- APIs: 95% success, direct, faster, more reliable
- Forms: 70% success, slower, fragile to UI changes
- Trade-off: API requires authentication (store credentials)

**Options**:

| Option | Method | Auth Required | Success Rate | Speed | Security |
|--------|--------|---|---|---|---|
| **API-first** | Use ATS APIs when available | Yes (OAuth/keys) | 95% | 2-5s | Medium (store creds) |
| **Form-first** | Fall back to form only | No | 70% | 20-60s | High (no creds stored) |
| **Hybrid** | Try API, fall back to form | Optional | 95%+ | 2-60s | Medium |

**Decision**: **Hybrid (API-first, form fallback)**

- **Phase 2**: Implement Greenhouse + Lever APIs
- **Phase 3**: Add Workday API
- **Phase 4**: LinkedIn API
- **Fallback**: Form filler for everything else

**Implementation**:
```python
# Precedence order (in ats_routers/__init__.py)
1. Greenhouse API (if auth available)
2. Lever API
3. Workday API
4. LinkedIn API
5. Generic form filler (last resort)

# User setup:
POST /api/ats/greenhouse/authorize
→ OAuth flow → store refresh token in .env
→ Future: Use refresh token to call API directly
```

**Credentials Storage**:
- **Local dev**: `.env` file (git-ignored)
- **Production (Lambda)**: AWS Secrets Manager
- **Never**: Commit credentials to repo

**Success Metric**:
- ✅ Greenhouse jobs: 90%+ API success
- ✅ Unknown ATS jobs: 70%+ form success
- ✅ Overall: > 80% success rate

---

## Decision 3: Observability: CloudWatch vs. Alternatives

**Question**: Where should logs & metrics live?

**Context**:
- Local dev: stdout (console)
- Production: Centralized logging essential (Lambda doesn't persist)
- Options: CloudWatch, DataDog, Splunk, ELK

**Options**:

| Option | Cost | Setup | Power | AWS Native |
|--------|------|-------|-------|-----------|
| **CloudWatch** | $0-10/mo | 5 min | Good | ✅ Yes |
| **DataDog** | $30-100/mo | 10 min | Excellent | ❌ No (3rd party) |
| **Splunk** | $100+/mo | Complex | Powerful | ❌ No (3rd party) |
| **ELK Stack** | Self-hosted | 1 day | Powerful | ❌ DIY |

**Decision**: **CloudWatch (Phase 1) + DataDog (Phase 3 optional)**

- **Phase 1**: CloudWatch (native to Lambda, cheap, sufficient)
- **Phase 3**: Optional DataDog for enhanced analytics if needed

**Implementation**:
```python
# logging_config.py
if environment == "production":
    # CloudWatch via watchtower
    cw_handler = watchtower.CloudWatchLogHandler(
        log_group="/aws/lambda/JobApplicationTracker",
    )
    root_logger.addHandler(cw_handler)

# CloudWatch queries:
# - Find failed applications: status="failed"
# - Success rate by ATS: ats_platform_detected, status
# - Performance trends: avg(duration_ms) over time
```

**Success Metric**:
- ✅ All logs in CloudWatch within 5 seconds
- ✅ Can query: "Show me failed Greenhouse submissions in last 24 hours"
- ✅ Cost < $5/month

---

## Decision 4: Job Discovery: Depth vs. Breadth

**Question**: Focus on few job boards (quality) or many (quantity)?

**Context**:
- Goal: 10 quality applications/day
- Strategy: More sources = more quality matches available
- Risk: Too many sources = duplicates, noise, maintenance burden

**Current Board Coverage**:
- ✅ LinkedIn (manual)
- ✅ Indeed (manual)
- ✅ Greenhouse (board scraping)
- ✅ Lever (board scraping)
- ❌ GitHub Jobs
- ❌ Angel List
- ❌ LinkedIn API (authenticated)
- ❌ RSS feeds (custom sources)

**Options**:

| Option | Boards | Setup | Coverage |
|--------|--------|-------|----------|
| **Minimal** | LinkedIn, Indeed | 1 day | 60% of market |
| **Comprehensive** | + GitHub, Angel List, RSS | 3 days | 85% of market |
| **Exhaustive** | + LinkedIn API, Workable, custom | 1 week | 95%+ of market |

**Decision**: **Comprehensive (Phase 2)**

- **Week 2**: Add GitHub, Angel List, RSS
- **Phase 3+**: LinkedIn API, other platforms as needed

**Board Priority** (by Mason's profile relevance):
1. **LinkedIn** (largest pool, good filtering)
2. **Angel List** (startup/tech focused → likely match)
3. **GitHub** (dev-centric, high quality)
4. **Indeed** (broad, volume)
5. **RSS feeds** (niche boards, company career pages)

**Deduplication Strategy**:
```python
# Avoid applying twice to same job
async def is_duplicate_job(new_job_url: str, db: AsyncSession):
    existing = await db.execute(
        select(Job).where(Job.source_url == new_job_url)
    )
    return existing.scalar_one_or_none() is not None

# Merge jobs from different sources
if existing_job and new_job_source != existing_job.source:
    # Update existing to note multiple sources
    existing_job.source = f"{existing_job.source},{new_job_source}"
```

**Success Metric**:
- ✅ 50+ new jobs/day available
- ✅ < 10% duplicates
- ✅ 10 quality matches available for applying

---

## Decision 5: Resume Tailoring: Aggressive vs. Conservative

**Question**: How much should we customize resume for each job?

**Context**:
- Current: Cerebras rewrites entire resume per job
- Risk: ATS parsers may reject heavily modified PDFs
- Opportunity: Personalization increases callback rates

**Options**:

| Option | Approach | Customization | ATS-Safe | Manual Review |
|--------|----------|---|---|---|
| **Conservative** | Minor tweaks (keyword matching only) | Low | ✅ Yes | No |
| **Balanced** | Reorder bullet points, highlight relevant skills | Medium | ✅ Yes | Optional |
| **Aggressive** | Rewrite sections, change summary, add metrics | High | ⚠️ Maybe | Required |

**Decision**: **Balanced (current) + Option to review**

- Keep current Cerebras tailoring (reordering + keyword emphasis)
- Add human review option for aggressive customization
- A/B test resume versions to measure callback impact

**Implementation**:
```python
# Tailor resume (balanced)
async def tailor_resume(job: dict, base_resume: str, profile: dict):
    prompt = """
    Tailor this resume for this specific job:
    - Reorder bullet points to highlight most relevant experience
    - Emphasize skills matching job requirements
    - Use keywords from job description naturally
    - DO NOT invent new experience
    - Keep factual accuracy
    """
    # Result: markdown resume (user can review before applying)

# Optional: Include flag for manual review
application.resume_review_required = True  # For aggressive rewrites
```

**Success Metric**:
- ✅ Phone screen rate > 30% (indicates good tailoring)
- ✅ No ATS rejections due to resume format
- ✅ A/B test: tailored vs. untailored (measure callback delta)

---

## Decision 6: Email Tracking: Privacy vs. Intelligence

**Question**: Track when recruiter opens your email?

**Context**:
- Privacy: Email tracking = privacy concern (for recruiters viewing)
- Intelligence: Know if recruiter engaged (helps prioritize follow-ups)
- Technical: Third-party services (HubSpot, Mailgun) handle this

**Options**:

| Option | Method | Privacy | Data Accuracy | Cost |
|--------|--------|---------|---|---|
| **No tracking** | Send email normally | ✅ | N/A | $0 |
| **Third-party** | Mailgun/HubSpot pixels | ⚠️ Tracker visible | 80% | $20-50/mo |
| **Simple logging** | Log send time only | ✅ | N/A | $0 |
| **Manual follow-up** | User checks email status manually | ✅ | 100% | $0 |

**Decision**: **Simple logging + Manual follow-up (Phase 2)**

- **Phase 2**: Track email send timestamps
- **Phase 5**: Optional integration with email tracking service if user wants
- Default: Respect recruiter privacy, user can add tracking if desired

**Implementation**:
```python
# Simple approach (Phase 2)
class Application(Base):
    follow_up_sent_at = Column(DateTime(timezone=True), nullable=True)
    follow_up_count = Column(Integer, default=0)
    status_changes = Column(JSON, default=list)  # Track status progression

# Future (Phase 5): Optional integration
if user_has_tracking_enabled:
    # Use Mailgun or HubSpot API
    send_tracked_email(...)
```

**Success Metric**:
- ✅ Can see when follow-up emails were sent
- ✅ Track application progression (pending → in_review → interview → etc.)
- ✅ User can manually update status based on email contents

---

## Decision 7: AgentCore vs. Cerebras for AI Tasks

**Question**: When to use AgentCore vs. Cerebras?

**Context**:
- Cerebras: Fast, cheap, simple LLM calls (extraction, tailoring, mapping)
- AgentCore: Orchestration, multi-step workflows, reasoning
- Trade-off: Cerebras is simpler; AgentCore is more powerful

**Current Use Cases**:

| Task | Current (Cerebras) | Future (AgentCore)? |
|------|-----|---|
| Resume extraction | ✅ Cerebras | Maybe AgentCore |
| Resume tailoring | ✅ Cerebras | Keep Cerebras |
| Cover letter gen | ✅ Cerebras | Keep Cerebras |
| Form field mapping | ✅ Cerebras | Maybe AgentCore |
| **Job fit scoring** | ❌ Not yet | **Yes, AgentCore** |
| **Failure analysis** | ❌ Not yet | **Yes, AgentCore** |
| **Interview prep** | ❌ Not yet | **Yes, AgentCore** |

**Decision**: **Hybrid approach**

- **Keep Cerebras**: Extraction, tailoring, mapping (fast, cheap, deterministic)
- **Add AgentCore**: Scoring, analysis, multi-step reasoning (complex decisions)
- **Fallback**: If AgentCore unavailable, use heuristics

**Implementation**:
```python
# cereb as_service.py (existing)
async def extract_profile(resume_text) -> dict:  # Cerebras
async def tailor_resume(job_desc, base_resume, profile) -> str:  # Cerebras

# agent_core_service.py (new)
async def score_job_fit(job: dict, profile: dict) -> dict:  # AgentCore
async def analyze_failure(error: dict, screenshots: list) -> dict:  # AgentCore

# Usage:
score = await agentcore.score_job_fit(job, profile)
if score >= 8:
    await auto_apply(job)
```

**Success Metric**:
- ✅ Job scoring uses AgentCore (better logic)
- ✅ Cerebras used for simple extraction (cost savings)
- ✅ System works with or without AgentCore (graceful degradation)

---

## Decision 8: Multi-User Support Timing

**Question**: When to add multi-user support (vs. single-user for now)?

**Context**:
- Current: Single profile, single user
- Goal: Scale to multiple friends/users?
- Risk: Multi-user adds complexity (auth, data isolation, billing)
- Timeline: Not urgent (Phase 4+ based on roadmap)

**Options**:

| Option | Timeline | Effort | Risk |
|--------|----------|--------|------|
| **Now** | Phase 1 | 1 week extra | Blocks MVP delivery |
| **Later** | Phase 4 | 1 week | Refactor needed |
| **Never** | N/A | $0 | Single-user forever |

**Decision**: **Phase 4 (post-Lambda migration, post-observability)**

- **Rationale**: Get single-user system working perfectly first
- **Approach**: Design with multi-user in mind (use `user_id` FK from start), but don't implement auth yet
- **Trigger**: When ready to onboard friends or monetize

**Future Design** (sketched now, implemented later):
```python
# Add to models.py (not yet enforced)
class User(Base):
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True)
    oauth_provider = Column(String)  # google, github, etc
    # ...

# Applications now belongs to user
class Application(Base):
    user_id = Column(Integer, ForeignKey("user.id"))  # Add in Phase 4
    # ... rest unchanged

# All endpoints add user context
async def get_applications(user_id: int, db: AsyncSession):
    # Filter by user_id
```

**Success Metric**:
- ✅ Phase 1-3: Single-user system works perfectly
- ✅ Phase 4: Can add `user_id` without breaking existing code

---

## Decision 9: Cover Letter Generation

**Question**: Placeholder for now — when/how to implement?

**Context**:
- Current: Not implemented (just exists in API)
- Challenge: Quality cover letters hard to generate
- Value: Some ATS platforms require them

**Options**:

| Option | Approach | Quality | Time | Effort |
|--------|----------|---------|------|--------|
| **Cerebras** | Use Cerebras (like tailoring) | Medium (generic) | 5-30s | 1 day |
| **AgentCore** | Multi-step reasoning + examples | High (personalized) | 10-30s | 2 days |
| **Template** | Use templates, fill with profile | Low (cookie-cutter) | 1s | 3 hours |
| **Skip** | Don't generate, use provided | N/A | N/A | $0 |

**Decision**: **Skip for Phase 1, Cerebras for Phase 3**

- **Phase 1-2**: Many ATS don't require cover letters; skip for now
- **Phase 3**: Implement via Cerebras (simple, fast)
- **Phase 5+**: Enhance with AgentCore if needed

**Implementation (Phase 3)**:
```python
@router.post("/api/ai/generate-cover-letter")
async def generate_cover_letter(job_id: int, db: AsyncSession = Depends(get_db)):
    job = await db.get(Job, job_id)
    profile = await db.get(Profile, 1)
    
    # Get example cover letters if user has any
    examples = await db.execute(
        select(Document).where(
            and_(
                Document.type == "cover_letter",
                Document.variant == "base",
            )
        ).limit(3)
    )
    example_texts = [doc.content_text for doc in examples.scalars().all()]
    
    # Generate via Cerebras
    cover_letter = await cerebras.generate_cover_letter(
        job.description,
        job.company,
        job.title,
        profile_dict,
        example_texts,
    )
    
    # Save and return
    doc = Document(
        type="cover_letter",
        variant="tailored",
        job_id=job_id,
        filename=f"{job.id}_cover_letter.txt",
        content_text=cover_letter,
    )
    db.add(doc)
    await db.commit()
    
    return {"cover_letter": cover_letter, "document_id": doc.id}
```

**Success Metric**:
- ✅ Cover letters generated on-demand
- ✅ Uploaded to ATS platforms alongside resume
- ✅ Quality reviews needed? Ask user for feedback

---

## Decision 10: Monitoring Stack: Real-time vs. Batch Analytics

**Question**: Real-time monitoring or batch dashboards?

**Context**:
- Real-time: See failures as they happen (5-10s latency)
- Batch: Aggregated reports once per day
- Trade-off: Real-time = more infrastructure, batch = simpler

**Options**:

| Option | Latency | Infrastructure | Cost | Alerting |
|--------|---------|---|---|---|
| **Real-time (WebSocket)** | 5-10s | WebSocket server | Medium | ✅ Instant |
| **Polling (5s)** | 5s | Simple REST | Low | ✅ Soon |
| **Polling (1m)** | 60s | Simple REST | Low | ⚠️ Delayed |
| **Batch (daily)** | 24h | None | Low | ❌ Late |

**Decision**: **Polling (5s intervals) for Phase 1-2**

- **Phase 1**: Metrics dashboard polls every 5s (good UX, low cost)
- **Phase 2**: Optional WebSocket for live application streaming (Lambda not ideal for long-lived connections)
- **Phase 3**: Consider webhook notifications (Slack, email) for key events

**Implementation (existing)**:
```typescript
// frontend/pages/Metrics.tsx
const { data, isLoading } = useQuery({
    queryKey: ['metrics'],
    queryFn: async () => fetch('/api/metrics/dashboard').then(r => r.json()),
    refetchInterval: 5000,  // Polls every 5 seconds
})
```

**Success Metric**:
- ✅ Metrics update every 5 seconds
- ✅ User sees failures within 10 seconds
- ✅ Minimal server resource usage

---

## Summary: All Decisions

| # | Decision | Choice | Rationale | Phase |
|---|----------|--------|-----------|-------|
| 1 | Quality vs. Quantity | Threshold (8/10) + Niche | Focus on best matches | Phase 1-6 |
| 2 | ATS API vs. Forms | Hybrid (API-first) | Better success rate | Phase 2 |
| 3 | Observability | CloudWatch | AWS native, cheap | Phase 1 |
| 4 | Job Sources | Comprehensive | 85% market coverage | Phase 2 |
| 5 | Resume Tailoring | Balanced | Effective, ATS-safe | Phase 1 |
| 6 | Email Tracking | Simple (no privacy issues) | Respect privacy | Phase 2 |
| 7 | AI Tools | Hybrid (Cerebras + AgentCore) | Each tool for its strength | Phase 1-3 |
| 8 | Multi-User | Phase 4 | Get single-user perfect first | Phase 4 |
| 9 | Cover Letters | Skip Phase 1, Cerebras Phase 3 | Not critical for MVP | Phase 3 |
| 10 | Monitoring | Polling (5s) | Good UX, low cost | Phase 1 |

---

## How to Use This Document

1. **Before implementing**, check if a decision has been made
2. **Rationale is listed** — understand why (not just what)
3. **Update when priorities change** — this is a living document
4. **Link from code comments** — reference decision when code depends on it

Example comment:
```python
# DECISION 2: Hybrid ATS routing (see DECISION_FRAMEWORK.md)
# API-first for known platforms, form-filler fallback
for router in ROUTERS:  # Ordered by platform priority
    if await router.can_handle(job_url):
        return await router.submit_application(...)
```

---

**Last Updated**: June 2026  
**Next Review**: After Phase 1 (Week 2)  
**Owned By**: Mason (user), AI Agent, Development Team

