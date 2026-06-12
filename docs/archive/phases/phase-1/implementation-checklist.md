# Phase 1 Implementation Checklist: Days 1-10

**Goal**: Foundation for 10 quality applications/day with full observability & intelligent routing

---

## Week 1: Observability & Resilience (Days 1-5)

### Day 1-2: Structured Logging System

#### [ ] Task 1.1: Migrate from print() to Python logging

**File**: `backend/app/logging_config.py` (NEW)

```python
import logging
import json
from datetime import datetime, timezone
import sys

class JsonFormatter(logging.Formatter):
    """Convert log records to structured JSON"""
    def format(self, record):
        return json.dumps({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "extra": getattr(record, "extra_fields", {}),
        })

def setup_logging(environment: str = "development"):
    """Initialize structured logging"""
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    
    # Console handler (JSON format)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(JsonFormatter())
    root_logger.addHandler(console_handler)
    
    # Future: Add CloudWatch handler for production
    if environment == "production":
        import watchtower
        cw_handler = watchtower.CloudWatchLogHandler(
            log_group="JobApplicationTracker",
            stream_name="production",
        )
        cw_handler.setFormatter(JsonFormatter())
        root_logger.addHandler(cw_handler)
    
    return root_logger
```

**Usage in code**:
```python
import logging
logger = logging.getLogger(__name__)

@router.post("/api/auto-apply/full/{app_id}")
async def full_auto_apply(app_id: int, db: AsyncSession = Depends(get_db)):
    logger.info("Starting auto-apply", extra={"extra_fields": {"app_id": app_id}})
    try:
        # ... do work
        logger.info("Auto-apply succeeded", extra={"extra_fields": {"app_id": app_id, "duration_ms": 5000}})
    except Exception as e:
        logger.error(f"Auto-apply failed: {e}", extra={"extra_fields": {"app_id": app_id, "error": str(e)}})
```

**Acceptance Criteria**:
- ✅ All prints in routers/services replaced with logger calls
- ✅ JSON format on console (test: `docker-compose up` produces JSON logs)
- ✅ Fields: timestamp, level, logger, message, function, line, extra_fields
- ✅ No errors in logs

---

#### [ ] Task 1.2: Add CloudWatch integration (AWS SDK)

**File**: `backend/app/logging_config.py` (UPDATE)

```python
import watchtower  # pip install watchtower

def setup_logging(environment: str = "development"):
    # ... existing code ...
    
    if environment == "production":
        cw_handler = watchtower.CloudWatchLogHandler(
            log_group="/aws/lambda/JobApplicationTracker",
            stream_name="auto-apply",
        )
        cw_handler.setFormatter(JsonFormatter())
        root_logger.addHandler(cw_handler)
```

**Test**:
```bash
# Add to backend/requirements.txt
watchtower==3.0.1

# Test locally (requires AWS credentials)
export AWS_REGION=us-east-1
export ENVIRONMENT=production
python -c "from app.logging_config import setup_logging; logger = setup_logging('production'); logger.info('Test message')"
```

**Acceptance Criteria**:
- ✅ watchtower dependency added
- ✅ CloudWatch logs appear in AWS Console
- ✅ Log group auto-created: `/aws/lambda/JobApplicationTracker`
- ✅ No performance degradation (async logging)

---

#### [ ] Task 1.3: Create metrics tracking model

**File**: `backend/app/models.py` (ADD)

```python
class ApplicationMetric(Base):
    """Track each application submission attempt for analytics"""
    __tablename__ = "application_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=False)
    attempt_number = Column(Integer, default=1)  # Retry count
    
    # Timing
    start_time = Column(DateTime(timezone=True), server_default=func.now())
    end_time = Column(DateTime(timezone=True), nullable=True)
    duration_ms = Column(Integer, nullable=True)
    
    # Status
    status = Column(String(50))  # success / failed / pending / submitted_unverified
    error_message = Column(Text, nullable=True)
    ats_platform_detected = Column(String(50))
    
    # AI metrics
    form_fields_detected = Column(Integer, nullable=True)
    fields_filled = Column(Integer, nullable=True)
    
    # Debug
    log_entries = Column(JSON, default=list)  # [{timestamp, step, message}]
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
```

**Acceptance Criteria**:
- ✅ Model created + migration run
- ✅ Metrics table has 50+ rows (test: run 10 applications)
- ✅ Query works: `SELECT COUNT(*) FROM application_metrics WHERE status = 'success'`

---

#### [ ] Task 1.4: Update auto_apply.py to record metrics

**File**: `backend/app/routers/auto_apply.py` (UPDATE)

```python
@router.post("/api/auto-apply/full/{app_id}")
async def full_auto_apply(app_id: int, db: AsyncSession = Depends(get_db)):
    import time
    from ..models import ApplicationMetric
    
    start_time = time.time()
    
    # Determine retry count
    existing_metrics = await db.execute(
        select(ApplicationMetric).where(ApplicationMetric.application_id == app_id)
    )
    retry_count = len(existing_metrics.scalars().all()) + 1
    
    metric = ApplicationMetric(
        application_id=app_id,
        attempt_number=retry_count,
    )
    db.add(metric)
    await db.commit()
    await db.refresh(metric)
    
    try:
        # ... existing auto-apply logic ...
        result = await full_auto_apply_logic(...)
        
        # Update metric
        metric.status = result["status"]
        metric.duration_ms = int((time.time() - start_time) * 1000)
        metric.ats_platform_detected = result.get("ats_platform")
        metric.form_fields_detected = result.get("fields_count")
        metric.fields_filled = result.get("filled_count")
        metric.log_entries = result.get("log", [])
        
        await db.commit()
        
        return result
        
    except Exception as e:
        metric.status = "failed"
        metric.error_message = str(e)
        metric.duration_ms = int((time.time() - start_time) * 1000)
        await db.commit()
        
        logger.error(f"Auto-apply failed", extra={"extra_fields": {
            "app_id": app_id,
            "retry": retry_count,
            "error": str(e),
            "duration_ms": metric.duration_ms,
        }})
        raise
```

**Acceptance Criteria**:
- ✅ Every application submission records a metric
- ✅ Metrics include: status, duration, error, fields detected/filled
- ✅ Retry count tracked
- ✅ Test: `GET /api/metrics` returns data

---

### Day 2-3: Retry Logic & Failure Recovery

#### [ ] Task 2.1: Implement exponential backoff retry mechanism

**File**: `backend/app/services/retry_service.py` (NEW)

```python
import asyncio
from enum import Enum
from datetime import datetime, timedelta, timezone

class RetryStrategy(Enum):
    EXPONENTIAL = "exponential"
    LINEAR = "linear"
    IMMEDIATE = "immediate"

async def should_retry(
    error: Exception,
    attempt: int,
    max_attempts: int = 3,
) -> tuple[bool, int]:
    """
    Determine if we should retry and wait time in seconds.
    
    Returns: (should_retry, wait_seconds)
    """
    if attempt >= max_attempts:
        return False, 0
    
    # Don't retry auth/validation errors
    if isinstance(error, ValueError):  # Field validation
        return False, 0
    if "validation" in str(error).lower():
        return False, 0
    
    # Retry network/timeout errors
    if isinstance(error, (asyncio.TimeoutError, ConnectionError)):
        return True, 2 ** attempt  # Exponential: 2s, 4s, 8s
    
    # Retry form detection failures (sometimes transient)
    if "form" in str(error).lower() or "field" in str(error).lower():
        return True, 2 ** attempt
    
    # Default: don't retry unknown errors
    return False, 0


async def execute_with_retry(
    func,
    *args,
    max_attempts: int = 3,
    on_retry_callback=None,
    **kwargs
):
    """Execute function with automatic retry on failure"""
    attempt = 0
    last_error = None
    
    while attempt < max_attempts:
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            attempt += 1
            should_retry, wait_time = await should_retry(e, attempt - 1, max_attempts)
            last_error = e
            
            if not should_retry:
                raise
            
            if on_retry_callback:
                await on_retry_callback(attempt, wait_time, e)
            
            await asyncio.sleep(wait_time)
    
    raise last_error
```

**Usage**:
```python
from .retry_service import execute_with_retry

async def auto_apply_with_retry(app_id: int, db: AsyncSession):
    async def _apply():
        return await full_auto_apply_logic(app_id, db)
    
    async def _on_retry(attempt, wait_time, error):
        logger.info(f"Retrying (attempt {attempt}), waiting {wait_time}s", 
                    extra={"extra_fields": {"app_id": app_id, "error": str(error)}})
    
    return await execute_with_retry(_apply, max_attempts=3, on_retry_callback=_on_retry)
```

**Acceptance Criteria**:
- ✅ Retry logic handles transient errors
- ✅ Exponential backoff works (test: 2s, 4s, 8s)
- ✅ Non-retryable errors fail immediately
- ✅ Logging at each retry
- ✅ Test: Simulate network timeout, confirm retry

---

#### [ ] Task 2.2: Add retry_count & error_history to Application model

**File**: `backend/app/models.py` (UPDATE)

```python
class Application(Base):
    # ... existing fields ...
    
    retry_count = Column(Integer, default=0)
    last_error = Column(Text, nullable=True)
    error_history = Column(JSON, default=list)  # [{timestamp, error, status}]
    last_retry_at = Column(DateTime(timezone=True), nullable=True)
    next_retry_at = Column(DateTime(timezone=True), nullable=True)
```

**Acceptance Criteria**:
- ✅ Migration applied
- ✅ Error history populated on each retry
- ✅ next_retry_at set to trigger scheduler

---

#### [ ] Task 2.3: Create scheduled retry job

**File**: `backend/app/routers/scheduler.py` (UPDATE)

```python
from datetime import datetime, timezone

@router.post("/api/scheduler/retry-failed")
async def retry_failed_applications(
    db: AsyncSession = Depends(get_db),
):
    """
    Find applications that failed and are ready for retry.
    Runs hourly.
    """
    now = datetime.now(timezone.utc)
    
    # Find applications ready for retry
    result = await db.execute(
        select(Application).where(
            and_(
                Application.status == "pending",
                Application.retry_count < 3,
                or_(
                    Application.next_retry_at.is_(None),
                    Application.next_retry_at <= now,
                ),
            )
        )
    )
    failed_apps = result.scalars().all()
    
    retried_count = 0
    for app in failed_apps:
        try:
            logger.info(f"Retrying application {app.id} (attempt {app.retry_count + 1})")
            result = await full_auto_apply(app.id, db)
            if result["status"] == "success":
                retried_count += 1
        except Exception as e:
            app.last_error = str(e)
            app.error_history.append({
                "timestamp": now.isoformat(),
                "error": str(e),
                "attempt": app.retry_count + 1,
            })
            app.retry_count += 1
            app.next_retry_at = now + timedelta(seconds=2 ** app.retry_count)
    
    await db.commit()
    
    return {
        "total_retried": retried_count,
        "still_pending": len(failed_apps) - retried_count,
    }
```

**Acceptance Criteria**:
- ✅ Endpoint works
- ✅ Finds pending applications
- ✅ Retries with exponential backoff
- ✅ Error history populated
- ✅ Test: Simulate failure, wait, confirm retry attempt

---

### Day 4: Monitoring Dashboard & Metrics Endpoint

#### [ ] Task 4.1: Create metrics aggregation endpoint

**File**: `backend/app/routers/metrics.py` (NEW)

```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timedelta, timezone
from ..database import get_db
from ..models import ApplicationMetric, Application

router = APIRouter(prefix="/api/metrics", tags=["metrics"])

@router.get("/dashboard")
async def get_metrics_dashboard(db: AsyncSession = Depends(get_db)):
    """Get metrics for last 7 days"""
    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)
    
    # Overall stats
    total_result = await db.execute(
        select(func.count(ApplicationMetric.id)).where(
            ApplicationMetric.created_at >= week_ago
        )
    )
    total_attempts = total_result.scalar() or 0
    
    # Success rate
    success_result = await db.execute(
        select(func.count(ApplicationMetric.id)).where(
            and_(
                ApplicationMetric.created_at >= week_ago,
                ApplicationMetric.status == "success",
            )
        )
    )
    successful = success_result.scalar() or 0
    success_rate = (successful / total_attempts * 100) if total_attempts > 0 else 0
    
    # Average duration
    duration_result = await db.execute(
        select(func.avg(ApplicationMetric.duration_ms)).where(
            ApplicationMetric.created_at >= week_ago
        )
    )
    avg_duration_ms = duration_result.scalar() or 0
    
    # By ATS platform
    ats_result = await db.execute(
        select(
            ApplicationMetric.ats_platform_detected,
            func.count(ApplicationMetric.id),
            func.sum(case((ApplicationMetric.status == "success", 1), else_=0)),
        ).where(ApplicationMetric.created_at >= week_ago)
        .group_by(ApplicationMetric.ats_platform_detected)
    )
    ats_breakdown = [
        {
            "platform": row[0] or "unknown",
            "attempts": row[1],
            "successful": row[2],
        }
        for row in ats_result.all()
    ]
    
    # Daily timeseries (for chart)
    daily_result = await db.execute(
        select(
            func.date(ApplicationMetric.created_at).label("date"),
            func.count(ApplicationMetric.id).label("attempts"),
            func.sum(case((ApplicationMetric.status == "success", 1), else_=0)).label("successful"),
        ).where(ApplicationMetric.created_at >= week_ago)
        .group_by(func.date(ApplicationMetric.created_at))
        .order_by(func.date(ApplicationMetric.created_at))
    )
    daily_data = [
        {
            "date": str(row[0]),
            "attempts": row[1],
            "successful": row[2],
            "success_rate": (row[2] / row[1] * 100) if row[1] > 0 else 0,
        }
        for row in daily_result.all()
    ]
    
    return {
        "period": {"start": week_ago.isoformat(), "end": now.isoformat()},
        "summary": {
            "total_attempts": total_attempts,
            "successful": successful,
            "success_rate_pct": round(success_rate, 1),
            "avg_duration_ms": round(avg_duration_ms, 0),
        },
        "by_ats_platform": ats_breakdown,
        "daily_timeseries": daily_data,
        "today": await _get_today_stats(db),
    }

async def _get_today_stats(db: AsyncSession):
    """Stats for today only"""
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    result = await db.execute(
        select(
            func.count(ApplicationMetric.id),
            func.sum(case((ApplicationMetric.status == "success", 1), else_=0)),
        ).where(ApplicationMetric.created_at >= today_start)
    )
    total, successful = result.first()
    
    return {
        "attempts": total or 0,
        "successful": successful or 0,
        "success_rate": (successful / total * 100) if total else 0,
    }

@router.get("/errors")
async def get_recent_errors(
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
):
    """Get recent application errors"""
    result = await db.execute(
        select(ApplicationMetric).where(
            ApplicationMetric.status == "failed"
        ).order_by(ApplicationMetric.created_at.desc())
        .limit(limit)
    )
    errors = result.scalars().all()
    
    return [
        {
            "application_id": e.application_id,
            "error": e.error_message,
            "attempt": e.attempt_number,
            "timestamp": e.created_at.isoformat(),
            "ats_platform": e.ats_platform_detected,
        }
        for e in errors
    ]
```

**Register in main.py**:
```python
from .routers import metrics
app.include_router(metrics.router)
```

**Acceptance Criteria**:
- ✅ GET /api/metrics/dashboard returns summary + timeseries
- ✅ GET /api/metrics/errors returns recent failures
- ✅ Test: `curl http://localhost:8000/api/metrics/dashboard`
- ✅ Success rate calculated correctly

---

#### [ ] Task 4.2: Create simple frontend metrics display

**File**: `frontend/src/pages/Metrics.tsx` (NEW)

```typescript
import { useQuery } from '@tanstack/react-query'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend } from 'recharts'

export function MetricsPage() {
  const { data, isLoading } = useQuery({
    queryKey: ['metrics'],
    queryFn: async () => {
      const res = await fetch('/api/metrics/dashboard')
      return res.json()
    },
    refetchInterval: 60000, // Refresh every minute
  })

  if (isLoading) return <div>Loading metrics...</div>

  const { summary, daily_timeseries, by_ats_platform, today } = data

  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid grid-cols-4 gap-4">
        <Card title="Total Attempts" value={summary.total_attempts} />
        <Card title="Successful" value={summary.successful} />
        <Card title="Success Rate" value={`${summary.success_rate_pct}%`} />
        <Card title="Avg Duration" value={`${summary.avg_duration_ms}ms`} />
      </div>

      {/* Today */}
      <div className="bg-white p-4 rounded">
        <h3>Today</h3>
        <p>{today.attempts} attempts • {today.successful} successful ({today.success_rate}%)</p>
      </div>

      {/* Daily Chart */}
      <div className="bg-white p-4 rounded">
        <LineChart width={800} height={300} data={daily_timeseries}>
          <CartesianGrid />
          <XAxis dataKey="date" />
          <YAxis />
          <Tooltip />
          <Legend />
          <Line type="monotone" dataKey="successful" stroke="#22c55e" />
          <Line type="monotone" dataKey="attempts" stroke="#0066cc" />
        </LineChart>
      </div>

      {/* By ATS Platform */}
      <div className="bg-white p-4 rounded">
        <h3>By ATS Platform</h3>
        <table className="w-full">
          <thead>
            <tr>
              <th>Platform</th>
              <th>Attempts</th>
              <th>Successful</th>
              <th>Success Rate</th>
            </tr>
          </thead>
          <tbody>
            {by_ats_platform.map((row) => (
              <tr key={row.platform}>
                <td>{row.platform}</td>
                <td>{row.attempts}</td>
                <td>{row.successful}</td>
                <td>{((row.successful / row.attempts) * 100).toFixed(1)}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function Card({ title, value }) {
  return (
    <div className="bg-white p-4 rounded border">
      <p className="text-gray-600 text-sm">{title}</p>
      <p className="text-2xl font-bold">{value}</p>
    </div>
  )
}
```

**Add route to App.tsx**:
```typescript
import { MetricsPage } from './pages/Metrics'

// In Routes:
<Route path="/metrics" element={<MetricsPage />} />

// In NAV:
{ to: '/metrics', icon: BarChart3, label: 'Metrics', end: false },
```

**Acceptance Criteria**:
- ✅ Page displays summary statistics
- ✅ Daily timeseries chart shows trend
- ✅ ATS platform breakdown visible
- ✅ Auto-refreshes every minute
- ✅ Test: Navigate to http://localhost:3000/metrics

---

**End of Day 4 Deliverable**: Full observability stack complete. Can see real-time metrics.

---

## Week 1, Day 5: Intelligent Routing Foundation

#### [ ] Task 5.1: Create ATS router abstraction

**File**: `backend/app/services/ats_routers/base.py` (NEW)

```python
from abc import ABC, abstractmethod
from typing import Optional, Dict

class ATSRouter(ABC):
    """Base class for ATS platform handlers"""
    
    @abstractmethod
    async def can_handle(self, apply_url: str) -> bool:
        """Check if this router can handle the URL"""
        pass
    
    @abstractmethod
    async def submit_application(
        self,
        application_id: int,
        job_url: str,
        profile: dict,
        resume_path: Optional[str] = None,
        cover_letter_path: Optional[str] = None,
    ) -> dict:
        """
        Submit application using this ATS platform.
        
        Returns: {
            "status": "success|failed|submitted_unverified",
            "duration_ms": 5000,
            "message": "Application submitted",
            "ats_platform": "greenhouse",
        }
        """
        pass
```

**File**: `backend/app/services/ats_routers/form_fallback.py` (NEW)

```python
# This is the existing playwright + form-filling logic
# Refactored into a router that falls back for unknown ATS

from .base import ATSRouter

class FormFillerRouter(ATSRouter):
    """Generic form filler for unknown ATS platforms"""
    
    async def can_handle(self, apply_url: str) -> bool:
        """Generic form filler always accepts (last resort)"""
        return True
    
    async def submit_application(self, ...):
        # Existing full_auto_apply_logic from auto_apply.py
        return await existing_playwright_logic(...)
```

**File**: `backend/app/services/ats_routers/greenhouse.py` (NEW)

```python
import httpx
from .base import ATSRouter

class GreenhouseRouter(ATSRouter):
    """Greenhouse ATS direct API submission"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GREENHOUSE_API_KEY")
    
    async def can_handle(self, apply_url: str) -> bool:
        return "greenhouse" in apply_url.lower()
    
    async def submit_application(
        self,
        application_id: int,
        job_url: str,
        profile: dict,
        resume_path: Optional[str] = None,
        cover_letter_path: Optional[str] = None,
    ) -> dict:
        """Submit via Greenhouse API instead of form filling"""
        
        # Extract job ID from URL
        job_id = self._extract_job_id(job_url)
        
        # Build API payload
        payload = {
            "first_name": profile.get("full_name", "").split()[0],
            "last_name": profile.get("full_name", "").split()[-1],
            "email": profile.get("email"),
            "phone": profile.get("phone"),
            "resume": open(resume_path, "rb") if resume_path else None,
            "cover_letter": open(cover_letter_path, "rb") if cover_letter_path else None,
        }
        
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"https://api.greenhouse.io/v1/jobs/{job_id}/applications",
                    data=payload,
                    auth=("", self.api_key),
                    timeout=30,
                )
            
            if resp.status_code in [200, 201]:
                return {
                    "status": "success",
                    "duration_ms": 2000,
                    "message": "Application submitted via Greenhouse API",
                    "ats_platform": "greenhouse",
                }
            else:
                return {
                    "status": "failed",
                    "message": f"Greenhouse API error: {resp.status_code}",
                    "ats_platform": "greenhouse",
                }
        
        except Exception as e:
            logger.error(f"Greenhouse API error: {e}")
            return {
                "status": "failed",
                "message": str(e),
                "ats_platform": "greenhouse",
            }
    
    def _extract_job_id(self, url: str) -> str:
        # Parse URL: https://company.greenhouse.io/jobs/123456
        import re
        match = re.search(r'/jobs/(\d+)', url)
        return match.group(1) if match else ""
```

**File**: `backend/app/services/ats_routers/__init__.py` (NEW)

```python
from .form_fallback import FormFillerRouter
from .greenhouse import GreenhouseRouter

ROUTERS = [
    GreenhouseRouter(),
    FormFillerRouter(),  # Always last (fallback)
]

async def route_and_submit(
    application_id: int,
    job_url: str,
    profile: dict,
    resume_path: str,
    cover_letter_path: str,
) -> dict:
    """Route application to appropriate handler"""
    
    for router in ROUTERS:
        if await router.can_handle(job_url):
            logger.info(f"Using router: {router.__class__.__name__}")
            return await router.submit_application(
                application_id,
                job_url,
                profile,
                resume_path,
                cover_letter_path,
            )
    
    # Should never reach here (FormFillerRouter accepts everything)
    return {"status": "failed", "message": "No suitable router found"}
```

**Acceptance Criteria**:
- ✅ Router abstraction created
- ✅ FormFillerRouter + GreenhouseRouter implemented
- ✅ Route selection logic works
- ✅ Test: Pass Greenhouse URL, confirm API submission attempted

---

#### [ ] Task 5.2: Update auto_apply.py to use routers

**File**: `backend/app/routers/auto_apply.py` (UPDATE)

```python
from ..services.ats_routers import route_and_submit

@router.post("/api/auto-apply/full/{app_id}")
async def full_auto_apply(app_id: int, db: AsyncSession = Depends(get_db)):
    # ... get application, job, profile, documents ...
    
    result = await route_and_submit(
        application_id=app_id,
        job_url=job.apply_url,
        profile=profile_dict,
        resume_path=resume_path,
        cover_letter_path=cover_letter_path,
    )
    
    # ... save metrics, update status ...
    return result
```

**Acceptance Criteria**:
- ✅ Integration works
- ✅ Greenhouse jobs use API
- ✅ Unknown ATS falls back to form filler
- ✅ Test: Create Greenhouse job + application, trigger auto-apply, verify API call

---

**End of Week 1 Deliverable**: 
- ✅ Full observability (logging + metrics)
- ✅ Retry logic with exponential backoff
- ✅ Monitoring dashboard
- ✅ Intelligent routing framework (Greenhouse API ready)

**Status**: Ready for Week 2 (job source expansion)

---

## Week 2: Job Source Expansion (Days 6-10)

### [ ] Task 6: LinkedIn API Integration
### [ ] Task 7: GitHub Jobs Integration
### [ ] Task 8: Angel List Integration  
### [ ] Task 9: RSS Feed Support
### [ ] Task 10: Metrics validation (confirm 10+ new jobs/day)

**(Details for Week 2 to follow in separate section)**

---

## Validation & Testing

### Post-Phase 1 Test Suite

```bash
# 1. Logging works
curl http://localhost:8000/api/health
# Check: stdout contains JSON logs

# 2. Retry logic
# Create job, create app, manually fail it, wait, check retry

# 3. Metrics dashboard
curl http://localhost:8000/api/metrics/dashboard
# Check: JSON response with timeseries

# 4. Greenhouse routing
# Create Greenhouse job, run auto-apply, check logs for API call
```

---

## Blockers & Dependencies

| Task | Blocker | Resolution |
|------|---------|-----------|
| CloudWatch logs | AWS credentials | Use IAM role (Lambda) or local credentials |
| Greenhouse API | API key | Get from Greenhouse admin panel |
| Metrics display | Recharts library | Already in package.json |

---

**Next Steps**: Start Day 1 (Logging). Confirm roadmap + get AWS access details.

