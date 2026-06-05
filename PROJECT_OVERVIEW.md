# JobApplicationTracker — Project Overview & Documentation Index

**Status**: Phase 0 → Phase 1 Ready  
**Last Updated**: June 5, 2026  
**Owner**: Mason  

---

## 📚 Documentation Hierarchy

```
START_HERE.md                    ← Begin here (5 min) ✅
│
├─→ AGENT.md                     Complete technical reference (30 min)
│   ├─ Architecture overview
│   ├─ Database models
│   ├─ Core workflows
│   ├─ API reference (condensed)
│   ├─ Code patterns & conventions
│   └─ Troubleshooting guide
│
├─→ ROADMAP.md                   Strategic plan (20 min)
│   ├─ Phase 1: Observability & Resilience (Week 1-2)
│   ├─ Phase 2: Serverless Infrastructure (Week 3-4)
│   ├─ Phase 3: Enhanced AI & Routing (Week 5-6)
│   ├─ Phase 4: Strands Workflow Integration (Week 7-8)
│   ├─ Phase 5: Contact & Email Tracking (Week 9-10)
│   └─ Phase 6: Niche Job Intelligence (Week 11-12)
│
├─→ DECISION_FRAMEWORK.md        Strategic choices (15 min)
│   ├─ 1. Quality vs. Quantity Target
│   ├─ 2. ATS API vs. Form Filling
│   ├─ 3. Observability: CloudWatch vs. Alternatives
│   ├─ 4. Job Discovery: Depth vs. Breadth
│   ├─ 5. Resume Tailoring: Aggressive vs. Conservative
│   ├─ 6. Email Tracking: Privacy vs. Intelligence
│   ├─ 7. AgentCore vs. Cerebras
│   ├─ 8. Multi-User Support Timing
│   ├─ 9. Cover Letter Generation
│   └─ 10. Monitoring Stack: Real-time vs. Batch
│
└─→ IMPLEMENTATION_CHECKLIST.md  Day-by-day tasks (Reference as needed)
    ├─ Week 1, Days 1-5: Observability + Retry Logic
    ├─ Week 1, Day 4: Monitoring Dashboard
    ├─ Week 1, Day 5: Intelligent Routing Foundation
    └─ Week 2, Days 6-10: Job Source Expansion
```

---

## 🎯 Your Roles

### 1. **User (Mason)**
   - Provide feedback on job matching quality
   - Confirm strategic direction
   - Answer clarifying questions
   - Monitor success metrics

### 2. **Product Manager (Kiro)**
   - Implement Phase 1 (Days 1-5)
   - Create architecture for scaling
   - Make trade-off decisions

### 3. **Future Developer / Agent**
   - Refer to AGENT.md for patterns & conventions
   - Follow IMPLEMENTATION_CHECKLIST.md for tasks
   - Use DECISION_FRAMEWORK.md to understand why decisions were made

---

## 🔄 Project Phases (12 Weeks)

### **Phase 1: Foundation (Weeks 1-2)** ← YOU ARE HERE
**Goal**: 10 quality applications/day with full observability

- **Week 1**: Observability system + retry logic + monitoring dashboard
- **Week 2**: Job source expansion (LinkedIn, GitHub, Angel List, RSS)
- **Output**: MVP ready for Phase 2
- **Success Metrics**: 
  - ✅ 10 applications/day submitted
  - ✅ Success rate ≥ 90%
  - ✅ Visible metrics dashboard
  - ✅ Auto-recovery from errors

---

### **Phase 2: Serverless Infrastructure (Weeks 3-4)**
**Goal**: Deploy to AWS Lambda (pay-per-use, infinite scalability)

- Lambda containerization
- RDS PostgreSQL migration
- S3 storage for documents
- SQS job queue
- EventBridge scheduler
- Cost: ~$10-20/month

---

### **Phase 3: Enhanced AI & Intelligent Routing (Weeks 5-6)**
**Goal**: AgentCore for job scoring; API-first for known ATS platforms

- Greenhouse API integration (working in Phase 1 foundation)
- Lever API integration
- Workday API integration
- AgentCore job scoring (8/10 threshold)
- Cover letter generation (Cerebras)

---

### **Phase 4: Strands Workflow Orchestration (Weeks 7-8)**
**Goal**: Model entire bulk auto-apply as workflow

- Strands workflow design
- Human-in-the-loop checkpoints
- Performance monitoring per step

---

### **Phase 5: Contact & Email Tracking (Weeks 9-10)**
**Goal**: Post-application follow-up visibility

- Email send tracking
- Interview notification parsing
- Application status auto-update
- Phone call logging (Twilio integration)

---

### **Phase 6: Niche Job Intelligence (Weeks 11-12)**
**Goal**: Find underrated, high-quality jobs

- Job relevance scoring (ML)
- Underrated job detection (low application count)
- Company research auto-population
- User feedback loop for scoring

---

## 💡 Why This Sequence?

| Phase | Why First? |
|-------|-----------|
| 1 | Can't scale without observability. Must measure before optimizing. |
| 2 | Lambda is cheapest + most scalable. Unlocks cost efficiency. |
| 3 | Intelligent routing improves success rate 15-20%. Worth doing early. |
| 4 | Strands provides orchestration layer for complex workflows. |
| 5 | Email tracking completes the feedback loop (→ know which apps succeeded). |
| 6 | Niche jobs + ML = highest quality matches (the real value). |

---

## 🛠️ Tech Stack by Component

```
├── Frontend
│   ├── React 18 + Vite
│   ├── Tailwind CSS
│   ├── React Query (data fetching)
│   ├── Recharts (metrics visualization)
│   └── Deployed: Vercel (Phase 2 onwards)
│
├── Backend
│   ├── FastAPI (async web framework)
│   ├── SQLAlchemy (async ORM)
│   ├── Pydantic (validation)
│   ├── Playwright (browser automation)
│   ├── Cerebras AI (extraction, tailoring)
│   └── Deployed: Railway (current) → AWS Lambda (Phase 2)
│
├── Database
│   ├── Local: SQLite (data/app.db)
│   └── Prod: AWS RDS PostgreSQL (Phase 2)
│
├── Storage
│   ├── Local: filesystem (data/documents/)
│   └── Prod: AWS S3 (Phase 2)
│
├── Observability
│   ├── Logging: Python logging → CloudWatch (Phase 1)
│   ├── Metrics: Custom tracking in DB
│   ├── Monitoring: /api/metrics/dashboard
│   └── Future: DataDog (optional, Phase 3+)
│
├── Job Queuing
│   ├── Current: In-memory scheduler
│   └── Phase 2: AWS SQS
│
└── AI & Orchestration
    ├── Cerebras: Extraction, tailoring, mapping
    ├── AgentCore: Job scoring, failure analysis (Phase 3)
    └── Strands: Workflow orchestration (Phase 4)
```

---

## 📊 Success Metrics (Hierarchical)

### **Phase 1 (Weeks 1-2)**
- [ ] 10 applications submitted per day
- [ ] Success rate ≥ 90% (submitted successfully)
- [ ] Average time per application ≤ 2 min
- [ ] Zero manual intervention needed
- [ ] Metrics dashboard visible
- [ ] Retry logic recovers 80%+ of failed applications

### **Phase 2 (Weeks 3-4)**
- [ ] Deploy to AWS Lambda successfully
- [ ] Cost ≤ $20/month for 10 apps/day
- [ ] Auto-scaling works (can burst to 100 apps/day if needed)
- [ ] No cold-start latency issues

### **Phase 3 (Weeks 5-6)**
- [ ] Greenhouse jobs: 95%+ API success rate
- [ ] Overall success rate ≥ 85%
- [ ] AgentCore job scoring active
- [ ] Top ATS platforms routed to APIs

### **Phase 4 (Weeks 7-8)**
- [ ] Strands workflow visible in dashboard
- [ ] Human-in-the-loop checkpoints working
- [ ] Per-step performance metrics tracked

### **Phase 5 (Weeks 9-10)**
- [ ] Email tracking enabled
- [ ] Phone call logging working (if Twilio enabled)
- [ ] Application status auto-updates based on email

### **Phase 6 (Weeks 11-12)**
- [ ] Job relevance scoring active
- [ ] Niche job detection reduces competition
- [ ] User feedback loop improving scoring over time

---

## 🎬 Quick Start Commands

```bash
# Backend setup
cd backend
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt

# Backend run
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
# Visit: http://localhost:8000/docs (Swagger)

# Frontend setup
cd frontend
npm install

# Frontend run
npm run dev
# Visit: http://localhost:5173

# Docker (all-in-one)
docker-compose up
# Backend: http://localhost:8000
# Frontend: http://localhost
```

---

## 🔑 Key Files Map

### Architecture & Design
- **AGENT.md** — Complete technical reference
- **ROADMAP.md** — Strategic roadmap (6 phases)
- **DECISION_FRAMEWORK.md** — 10 key decisions with reasoning
- **IMPLEMENTATION_CHECKLIST.md** — Day-by-day tasks

### Backend Implementation
- `backend/app/main.py` — FastAPI app setup
- `backend/app/models.py` — Database schema
- `backend/app/routers/auto_apply.py` — Full auto-apply endpoint (core logic)
- `backend/app/services/cerebras_service.py` — AI integration
- `backend/app/services/playwright_service.py` — Browser automation
- `backend/app/services/ats_integration.py` — ATS detection & APIs
- `backend/app/services/auto_scheduler.py` — Bulk auto-apply scheduler

### Frontend Implementation
- `frontend/src/App.tsx` — Main routing
- `frontend/src/pages/Dashboard.tsx` — Application tracking
- `frontend/src/pages/Profile.tsx` — User profile & resume upload
- `frontend/src/pages/Documents.tsx` — Resume/cover letter library
- `frontend/src/api/client.ts` — API integration

### Configuration
- `backend/.env` — Environment variables (secrets)
- `backend/.env.example` — Template (git-tracked)
- `backend/requirements.txt` — Python dependencies
- `frontend/package.json` — Node dependencies
- `docker-compose.yml` — Local dev stack

---

## 🚨 Critical Success Factors

### 1. **Observability**
   - Without logs/metrics, can't debug failures
   - Phase 1 Priority #1

### 2. **Quality Over Quantity**
   - 10 perfect applications > 100 mediocre ones
   - Use scoring to filter (8/10 threshold)

### 3. **Intelligent Routing**
   - API for known platforms (95% success)
   - Form filling for unknowns (70% success)
   - Phase 1 Priority #2

### 4. **Resilience**
   - Auto-retry on transient errors
   - Exponential backoff (1s, 4s, 16s, 64s)
   - Don't give up easily

### 5. **Cost Efficiency**
   - AWS Lambda (pay-per-use) vs. always-on servers
   - Phase 2 Priority #1

---

## ⚠️ Risks & Mitigation

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Job boards block automation | 0 applications | Randomized delays, rotating user agents |
| Resume parsing fails | Wrong data applied | Manual review option, feedback loop |
| ATS selectors change | Forms not detectable | Frequent selector updates, API fallback |
| AWS Lambda cold starts | Latency > 5s | Provisioned concurrency, keep-alive |
| Multi-user data isolation fail | Privacy breach | Design with user_id FK from start |
| Cover letters low quality | Rejection | Use examples for style guidance |
| Rate limiting / IP bans | Can't apply | Respectful delays, check robots.txt |

---

## 🎓 How AI Agents Should Use This Project

### Step 1: Orientation
- Read **START_HERE.md** (5 min)
- Read **AGENT.md** sections on architecture (15 min)

### Step 2: Task Selection
- Check **IMPLEMENTATION_CHECKLIST.md** for what's needed
- Reference **DECISION_FRAMEWORK.md** to understand *why*

### Step 3: Implementation
- Follow patterns documented in AGENT.md
- Use async/await, structured logging, database models correctly
- Write tests before shipping

### Step 4: Code Review
- Confirm logging is structured (JSON)
- Check retry logic handles edge cases
- Ensure no secrets in code

---

## 🔐 Security Considerations

### Credentials
- Cerebras API key: `.env` (never commit)
- AWS credentials: IAM role (Lambda native)
- Greenhouse API key: `.env` (Phase 2)
- Database password: AWS Secrets Manager (Phase 2)

### Data Privacy
- No resume PDFs in git history
- S3 bucket encryption enabled (Phase 2)
- Database backups with snapshots (Phase 2)

### ATS Compliance
- Respect `robots.txt` on job boards
- Use reasonable delays between requests
- Don't spam applications (follow job board ToS)

---

## 📈 Growth Path

```
Phase 1: MVP (10 apps/day, local)
  ↓
Phase 2: Scalable (AWS Lambda, infinite capacity)
  ↓
Phase 3: Intelligent (AgentCore scoring, API routing)
  ↓
Phase 4: Orchestrated (Strands workflows)
  ↓
Phase 5: Tracked (Email + phone follow-up)
  ↓
Phase 6: Optimized (ML niche detection)
  ↓
Future: Monetized? (Offer to friends, freemium model?)
```

---

## 💬 Questions to Clarify Before Starting

**For Mason:**

1. **Job Quality Criteria**
   - Minimum salary? ($80k? $120k? $150k+?)
   - Location preference? (remote, hybrid, in-office, specific cities?)
   - Company size? (startup, mid-market, enterprise?)
   - Industry? (tech, finance, healthcare, etc.?)

2. **AWS Access**
   - Do you have an AWS account?
   - If not, want me to guide setup?
   - Region preference? (default: us-east-1)

3. **Cerebras API**
   - Do you have a Cerebras API key?
   - If not, I can guide setup at cerebras.ai

4. **Phase 1 Confirmation**
   - Ready to start Week 1 (observability + retry logic)?
   - Any concerns about approach?

---

## 📞 Support Channels

| Need | Resource |
|------|----------|
| Architecture understanding | AGENT.md |
| Strategic direction | ROADMAP.md |
| Why a decision was made | DECISION_FRAMEWORK.md |
| Day-by-day tasks | IMPLEMENTATION_CHECKLIST.md |
| Quick reference | This file (PROJECT_OVERVIEW.md) |
| Code patterns | AGENT.md → "Code Style & Best Practices" |
| Troubleshooting | AGENT.md → "Troubleshooting Guide" |

---

## ✅ Pre-Flight Checklist

Before Phase 1 starts:

- [ ] Reviewed START_HERE.md
- [ ] Reviewed ROADMAP.md (Phase 1 section)
- [ ] Confirmed job quality criteria
- [ ] AWS account accessible
- [ ] Cerebras API key obtained (or will get)
- [ ] Ready to start Week 1 observability implementation
- [ ] Comfortable with async Python / FastAPI patterns

**All set? Let's go! →** [Start Phase 1 Implementation](IMPLEMENTATION_CHECKLIST.md)

---

**Created**: June 5, 2026  
**Status**: Ready for implementation  
**Next Review**: After Phase 1 completion (Week 2)  
**Maintained By**: Mason (user), Kiro (AI agent)

Welcome to JobApplicationTracker 2.0 🚀

