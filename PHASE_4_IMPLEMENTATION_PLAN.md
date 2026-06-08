# Phase 4 Implementation Plan — AgentCore + Dashboard

**Objective**: Add intelligent job scoring and visual dashboard control panel  
**Timeline**: 6-7 days (Days 1-7 of Phase 4)  
**Start Date**: June 5, 2026  
**Target Completion**: June 11, 2026  

---

## 📊 Phase 4 Scope

### Component 1: AgentCore Job Scoring (Days 1-3)
- Score jobs 1-10 based on relevance
- Only submit to jobs scoring ≥ 8/10
- Track scoring statistics
- Expected improvement: 30%+ quality increase

### Component 2: Visual Dashboard (Days 3-7)
- Real-time application status display
- Metrics and analytics
- Manual controls (trigger sync, view logs)
- Charts and visualizations
- Expected delivery: Full production-grade dashboard

---

## 🎯 Day-by-Day Breakdown

### Day 1: AgentCore Scoring Design & Setup

**Morning (2-3 hours)**:
- [ ] Design job scoring criteria
- [ ] Create Cerebras prompt for scoring
- [ ] Define database schema updates
- [ ] Test scoring with 10 sample jobs

**Afternoon (2-3 hours)**:
- [ ] Create `job_scorer.py` service
- [ ] Implement Cerebras integration
- [ ] Add score field to database
- [ ] Add scoring migration

**Deliverable**: Scoring service working, tested with sample jobs

---

### Day 2: Scoring Integration & Auto-Apply Filter

**Morning (2-3 hours)**:
- [ ] Integrate scoring into job fetching pipeline
- [ ] Add `min_score` parameter to auto-apply
- [ ] Update auto-apply router to skip low-score jobs
- [ ] Add score logging and tracking

**Afternoon (2-3 hours)**:
- [ ] Test with 100+ real jobs
- [ ] Refine scoring prompt based on results
- [ ] Verify accuracy of scoring
- [ ] Test database migrations

**Deliverable**: Auto-apply only submits jobs ≥ 8/10

---

### Day 3: Scoring Refinement & Lambda Deployment

**Morning (2-3 hours)**:
- [ ] Analyze scoring patterns
- [ ] Refine scoring weights
- [ ] Add scoring statistics endpoint
- [ ] Create scoring performance report

**Afternoon (2-3 hours)**:
- [ ] Update Lambda deployment package
- [ ] Test scoring in Lambda environment
- [ ] Deploy to production
- [ ] Verify EventBridge execution with new code

**Deliverable**: AgentCore scoring live in production

---

### Day 4: Dashboard Foundation & UI Setup

**Morning (3-4 hours)**:
- [ ] Design dashboard layout
- [ ] Create React components structure
- [ ] Set up chart library (Recharts)
- [ ] Create API service for dashboard calls

**Afternoon (2-3 hours)**:
- [ ] Create metrics endpoint in backend
- [ ] Test API connection
- [ ] Build basic dashboard shell
- [ ] Set up WebSocket for real-time updates (optional)

**Deliverable**: Dashboard skeleton with API integration

---

### Day 5: Dashboard Metrics & Visualizations

**Morning (3-4 hours)**:
- [ ] Implement metrics calculation
- [ ] Create success rate chart
- [ ] Create ATS platform breakdown chart
- [ ] Create application timeline

**Afternoon (3-4 hours)**:
- [ ] Add scoring distribution chart
- [ ] Create job source breakdown
- [ ] Add response rate metrics
- [ ] Create error tracking display

**Deliverable**: Full metrics dashboard with charts

---

### Day 6: Dashboard Controls & Features

**Morning (3-4 hours)**:
- [ ] Add manual sync trigger button
- [ ] Add job filtering/search
- [ ] Create application detail view
- [ ] Add CloudWatch logs viewer

**Afternoon (2-3 hours)**:
- [ ] Add configuration panel
- [ ] Create alert/notification system
- [ ] Add refresh controls
- [ ] Test all interactive features

**Deliverable**: Fully functional dashboard with controls

---

### Day 7: Testing, Optimization & Production Deployment

**Morning (3-4 hours)**:
- [ ] End-to-end testing
- [ ] Performance optimization
- [ ] Error handling and edge cases
- [ ] Mobile responsiveness

**Afternoon (2-3 hours)**:
- [ ] Final QA
- [ ] Deploy to production
- [ ] Monitor for errors
- [ ] Create user documentation

**Deliverable**: Phase 4 complete, deployed, tested

---

## 🏗️ Architecture Overview

### AgentCore Scoring Pipeline

```
Job Fetched
    ↓
Extract Job Details (title, company, description, salary)
    ↓
Send to Cerebras for Scoring
    ↓
Cerebras Returns Score (1-10)
    ↓
Store in Database
    ↓
Auto-Apply Decision:
  ├─ If score ≥ 8/10 → Submit application
  └─ If score < 8/10 → Skip (log reason)
```

### Dashboard Real-Time Pipeline

```
Frontend Dashboard
    ↓
API Calls (/api/metrics, /api/applications, /api/jobs)
    ↓
Backend Lambda Function
    ↓
Query PostgreSQL Database
    ↓
Format JSON Response
    ↓
Return to Frontend
    ↓
Update Charts & Visualizations
```

---

## 📋 Implementation Checklist

### AgentCore Scoring

- [ ] Design scoring criteria
- [ ] Create `app/services/job_scorer.py`
- [ ] Add Cerebras integration
- [ ] Add database migration
- [ ] Update auto-apply router
- [ ] Add scoring statistics endpoint
- [ ] Test with real jobs
- [ ] Deploy to Lambda
- [ ] Monitor production

### Dashboard Frontend

- [ ] Create React components
- [ ] Design layout and styling
- [ ] Implement metrics calculations
- [ ] Create charts (Recharts)
- [ ] Add manual controls
- [ ] Add real-time updates
- [ ] Test all features
- [ ] Deploy to production
- [ ] Monitor for errors

### Backend Updates

- [ ] Create metrics endpoint
- [ ] Update job endpoint with scores
- [ ] Add application detail endpoint
- [ ] Create CloudWatch logs endpoint
- [ ] Add error handling
- [ ] Performance optimize queries
- [ ] Deploy to Lambda
- [ ] Test all endpoints

---

## 🔧 Technical Stack

### AgentCore Scoring
- **API**: Cerebras AI
- **Integration**: Async HTTP
- **Storage**: PostgreSQL (new `score` column)
- **Cache**: In-memory during auto-apply

### Dashboard
- **Frontend**: React 18 + Vite + Tailwind
- **Charts**: Recharts (bar, line, pie charts)
- **API Client**: React Query (caching + real-time)
- **State Management**: React hooks
- **Backend**: FastAPI + SQLAlchemy
- **Database**: PostgreSQL
- **Deployment**: AWS Lambda (no changes needed)

---

## 📈 Success Metrics

### AgentCore Scoring
- ✅ 100% of jobs scored
- ✅ Scores distributed 1-10 (not all the same)
- ✅ Auto-apply filters working (only ≥8/10)
- ✅ No API rate limiting issues
- ✅ Scoring accuracy ≥ 90%

### Dashboard
- ✅ Loads in <2 seconds
- ✅ All metrics displaying correctly
- ✅ Charts rendering smoothly
- ✅ Manual controls working
- ✅ Real-time updates working
- ✅ Mobile responsive

---

## 🚀 Deployment Strategy

### Phase 4A: AgentCore (Days 1-3)
1. Develop and test locally
2. Update Lambda deployment package
3. Deploy to production
4. Monitor for 24 hours
5. Adjust scoring if needed

### Phase 4B: Dashboard (Days 4-7)
1. Develop locally
2. Test with real data from Lambda
3. Deploy to production
4. Monitor for errors
5. Iterate on UX

---

## 📚 Files to Create/Update

### New Files
- `backend/app/services/job_scorer.py` — Scoring service
- `backend/app/routers/dashboard.py` — Dashboard endpoints
- `backend/migrations/add_job_score.sql` — Database migration
- `frontend/src/pages/Dashboard.tsx` — Dashboard page
- `frontend/src/components/MetricsChart.tsx` — Chart component
- `frontend/src/components/ApplicationsList.tsx` — App list
- `frontend/src/components/ControlPanel.tsx` — Controls

### Updated Files
- `backend/app/main.py` — Add dashboard routes
- `backend/app/models.py` — Add score field
- `backend/app/routers/auto_apply.py` — Use scoring filter
- `backend/app/routers/jobs.py` — Return scores
- `frontend/src/App.tsx` — Add dashboard route
- `backend/lambda_handler.py` — Update if needed

---

## 💡 Key Decisions

### Scoring Algorithm
- Use Cerebras with custom prompt
- Score based on:
  - Job relevance to skills
  - Salary alignment
  - Company reputation
  - Growth opportunity
  - Location/remote status

### Dashboard UX
- Minimalist, clean design
- Real-time metrics
- Dark mode support
- Mobile first responsive
- One-click controls

### Performance
- Cache metrics (5-min TTL)
- Lazy load charts
- Optimize database queries
- Use API pagination

---

## ⚠️ Risks & Mitigation

| Risk | Probability | Mitigation |
|------|-------------|-----------|
| Cerebras API rate limiting | Medium | Implement backoff + caching |
| Dashboard performance issues | Low | Optimize queries + lazy load |
| Scoring inaccuracy | Medium | Human review + refine prompt |
| Database migration failures | Low | Test migration script first |
| Frontend breaking on old data | Low | Add data validation |

---

## 📞 Support Resources

- Cerebras API docs: https://docs.cerebras.ai
- Recharts docs: https://recharts.org
- FastAPI docs: https://fastapi.tiangolo.com
- React Query docs: https://tanstack.com/query

---

## 🎯 Phase 4 Complete Criteria

When Phase 4 is done, you should have:

✅ **AgentCore Scoring**
- Jobs scored by relevance
- Only submit ≥8/10
- Tracking statistics
- Live in production

✅ **Visual Dashboard**
- Real-time application status
- Metrics and charts
- Manual controls
- Live in production

✅ **Combined Impact**
- 30% quality improvement (scoring)
- Full visibility (dashboard)
- Manual override capability
- Production-grade system

---

**Start Date**: June 5, 2026  
**Target Completion**: June 11, 2026  
**Status**: 🟢 READY TO START  

Let's build Phase 4! 🚀
