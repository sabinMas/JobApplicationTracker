# Phase 2: Job Source Framework & Scheduler Implementation

## Status: Week 2 (Days 6-10) - IN PROGRESS

### Completed ✅

**Phase 1 Complete (Days 1-5)**:
- [x] Structured logging system (JSON format, CloudWatch ready)
- [x] Retry logic (exponential backoff: 1s, 2s, 4s, max 3 attempts)
- [x] Metrics endpoints (dashboard, errors, summary, retry-candidates)
- [x] Intelligent routing framework (ATS routers abstraction, Greenhouse API)
- [x] All Phase 1 tests passing (21/21)

**Phase 2 Initial Work (Days 6-7)**:
- [x] Job source abstraction framework (JobSource ABC, JobListing class)
- [x] RSS feed job source implementation (RSSJobSource)
- [x] Job source manager (parallel fetching, deduplication, database sync)
- [x] Job listing model in database (Job model with source tracking)
- [x] Jobs router endpoints (list, sync, sources, stats)
- [x] Fixed import paths (rss_source.py, manager.py)
- [x] All 7 job source tests passing

---

## Remaining Phase 2 Tasks (Days 8-10)

### Task 1: Job Scheduler (Daily Sync)
**File**: `backend/app/routers/scheduler.py` (CREATE/UPDATE)

**Deliverables**:
- [ ] Create job sync scheduler
- [ ] Schedule daily job sync at 8 AM
- [ ] Trigger all configured job sources
- [ ] Log sync results
- [ ] Tests for scheduler

**API Endpoints**:
```
POST /api/scheduler/sync - Manual trigger
GET /api/scheduler/config - Get scheduler config
PUT /api/scheduler/config - Update schedule time
GET /api/scheduler/logs - View sync history
```

---

### Task 2: Additional Job Sources (Stubs)
**Files**:
- [ ] `backend/app/services/job_sources/github_source.py`
- [ ] `backend/app/services/job_sources/linkedin_source.py`
- [ ] `backend/app/services/job_sources/angellist_source.py`

**Deliverables** (stub implementations, ready for credentials):
- [ ] GitHub Jobs API source (no auth needed, production-ready)
- [ ] LinkedIn API source (stub, awaiting credentials)
- [ ] Angel List API source (stub, awaiting credentials)
- [ ] Tests for each source

**Note**: LinkedIn and Angel List will need user credentials later

---

### Task 3: Frontend Job Display
**Files**:
- [ ] `frontend/src/pages/Jobs.tsx` - Job listing page
- [ ] `frontend/src/components/JobCard.tsx` - Individual job card
- [ ] `frontend/src/hooks/useJobs.ts` - Job query hook

**Deliverables**:
- [ ] Display jobs by source
- [ ] Filter by status (discovered, applied, rejected)
- [ ] View job details
- [ ] Mark job as applied manually
- [ ] Tests for job UI components

---

### Task 4: Integration Testing
**File**: `backend/test_integration.py` (CREATE)

**Test Cases**:
- [ ] Full sync workflow (fetch → deduplicate → store)
- [ ] API endpoints work end-to-end
- [ ] Database correctly stores jobs
- [ ] Pagination works
- [ ] Filtering works

---

## Blocking Items (User Action Required)

### For Phase 2 Completion:
1. **RSS Feed URLs**: Provide URLs to monitor (e.g., HackerNews Jobs, WeWorkRemotely, etc.)
   - Example: `https://news.ycombinator.com/rss`

### For Phase 3 (Optional now, needed later):
1. **LinkedIn API Credentials** (OAuth 2.0)
   - Client ID
   - Client Secret
   - Redirect URI

2. **GitHub API Token** (Personal Access Token)
   - Token with `public_repo` scope

3. **Angel List API Key**
   - API key from https://angel.co/api

4. **Greenhouse API Key** (for production, optional for testing)
   - Greenhouse account API key

---

## Architecture Notes

### Job Source Framework Structure
```
services/job_sources/
├── base.py              # JobSource ABC, JobListing class
├── manager.py           # JobSourceManager (orchestration)
├── rss_source.py        # ✅ RSSJobSource (working)
├── github_source.py     # 📝 GitHub (stub)
├── linkedin_source.py   # 📝 LinkedIn (stub)
├── angellist_source.py  # 📝 Angel List (stub)
└── __init__.py
```

### Database Model
```
Job:
  id, title, company, location, job_type
  source (rss, github, linkedin, angellist)
  source_url, apply_url
  description, requirements, salary_range
  posted_date, status (discovered, applied, rejected)
  notes, created_at
```

### API Design
```
GET    /api/jobs                          # List jobs
GET    /api/jobs/{id}                     # Job details
POST   /api/jobs/sync                     # Manual sync
GET    /api/jobs/sources                  # List sources
POST   /api/jobs/sources/rss              # Add RSS feed
GET    /api/jobs/stats                    # Statistics
POST   /api/scheduler/sync                # Manual schedule trigger
GET    /api/scheduler/config              # Get schedule config
PUT    /api/scheduler/config              # Update schedule
```

---

## Next Steps

### Immediate (Ready to implement):
1. ✅ Fix import paths (DONE - all tests pass)
2. Create job scheduler endpoint
3. Implement GitHub Jobs source (no auth needed)
4. Create Jobs frontend page

### When User Provides Credentials:
5. LinkedIn OAuth setup
6. Angel List integration
7. Integration testing with real data

### Quality Gates:
- All tests passing locally
- No import errors
- Database schema correct
- API endpoints documented in Swagger

---

## Testing Strategy

**Unit Tests**: 
- Each source tests independently
- Mock API responses
- Test error handling

**Integration Tests**:
- Full sync workflow
- Database transactions
- Deduplication logic

**API Tests**:
- Endpoints return correct schema
- Pagination works
- Filtering works

**Manual Testing**:
- Hit endpoints with real RSS feeds
- Verify jobs appear in UI
- Check database for correct data

---

## Estimated Effort

| Task | Effort | Status |
|------|--------|--------|
| Job Scheduler | 2 hours | Ready to start |
| GitHub Source | 1 hour | Ready to start |
| LinkedIn/AngelList Stubs | 1 hour | Ready to start |
| Frontend Jobs Page | 3 hours | Ready to start |
| Integration Tests | 2 hours | Ready to start |
| **Total** | **9 hours** | **Phase 2 Days 8-10** |

---

## Success Criteria for Phase 2 Completion

- ✅ Job source framework complete (abstraction works)
- ✅ RSS feed integration working
- ✅ Jobs stored in database correctly
- ✅ Scheduler configured and tested
- ✅ GitHub Jobs working
- ✅ LinkedIn/AngelList stubs ready for credentials
- ✅ Frontend displays jobs
- ✅ All tests passing (25+ tests total)
- ✅ User can see 50+ jobs available per day
- ✅ Zero manual intervention to sync jobs

---

**Updated**: June 5, 2026  
**Next Action**: Create job scheduler endpoint (Task 1)
