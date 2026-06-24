"""
Pipeline Visualizer & Job Review Gate

Real-time visualization of jobs moving through the pipeline:
discovered → scored → enriched → prepared → review → submitted

Provides endpoints for:
- Viewing jobs by pipeline stage
- Mandatory human review before submission
- Real-time WebSocket updates (via separate service)
"""

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime
import logging

from ..database import get_db
from ..models import Job, Application, Document
from ..schemas import (
    PipelineJobOut,
    PipelineStageUpdate,
    JobReviewRequest,
    PipelineVisualizerOut,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/pipeline-visualizer", tags=["pipeline-visualizer"])


PIPELINE_STAGES = [
    "discovered",
    "scored",
    "enriched",
    "prepared",
    "review",
    "submitted",
    "skipped",
]


@router.get("/jobs", response_model=PipelineVisualizerOut)
async def get_pipeline_jobs(
    stage: str = Query(None, description="Filter by pipeline stage"),
    limit_per_stage: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> PipelineVisualizerOut:
    """
    Get comprehensive pipeline visualization with job counts by stage.
    
    Args:
        stage: Optional filter for specific stage
        limit_per_stage: Max jobs to return per stage
        db: Database session
    
    Returns:
        PipelineVisualizerOut with job counts and jobs organized by stage
    """
    try:
        # Get total job count
        total_result = await db.execute(select(func.count(Job.id)))
        total_jobs = total_result.scalar() or 0

        by_stage = {}
        jobs_by_stage = {}

        # Query jobs for each stage
        for stage_name in PIPELINE_STAGES:
            count_result = await db.execute(
                select(func.count(Job.id)).where(Job.pipeline_stage == stage_name)
            )
            count = count_result.scalar() or 0
            by_stage[stage_name] = count

            # Get jobs for this stage
            if stage is None or stage == stage_name:
                result = await db.execute(
                    select(Job)
                    .where(Job.pipeline_stage == stage_name)
                    .order_by(Job.created_at.desc())
                    .limit(limit_per_stage)
                )
                jobs = result.scalars().all()
                jobs_by_stage[stage_name] = [
                    PipelineJobOut(
                        id=job.id,
                        title=job.title,
                        company=job.company,
                        location=job.location,
                        source=job.source,
                        apply_url=job.apply_url,
                        score=job.score,
                        score_reasoning=job.score_reasoning,
                        score_strengths=job.score_strengths or [],
                        score_concerns=job.score_concerns or [],
                        pipeline_stage=job.pipeline_stage,
                        enrichment_data=job.enrichment_data,
                        pipeline_data=job.pipeline_data,
                        created_at=job.created_at,
                    )
                    for job in jobs
                ]

        return PipelineVisualizerOut(
            total_jobs=total_jobs,
            by_stage=by_stage,
            jobs_by_stage=jobs_by_stage if stage is None else {stage: jobs_by_stage.get(stage, [])},
            timestamp=datetime.utcnow(),
        )

    except Exception as e:
        logger.error("Error fetching pipeline jobs", extra={"error": str(e)})
        raise HTTPException(status_code=500, detail="Failed to fetch pipeline jobs")


@router.get("/jobs-for-review", response_model=list[PipelineJobOut])
async def get_jobs_for_review(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
) -> list[PipelineJobOut]:
    """
    Get all jobs in "review" stage awaiting human approval before submission.
    
    Args:
        skip: Pagination offset
        limit: Number of jobs to return
        db: Database session
    
    Returns:
        List of jobs awaiting review
    """
    try:
        result = await db.execute(
            select(Job)
            .where(Job.pipeline_stage == "review")
            .order_by(Job.score.desc(), Job.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        jobs = result.scalars().all()

        return [
            PipelineJobOut(
                id=job.id,
                title=job.title,
                company=job.company,
                location=job.location,
                source=job.source,
                apply_url=job.apply_url,
                score=job.score,
                score_reasoning=job.score_reasoning,
                score_strengths=job.score_strengths or [],
                score_concerns=job.score_concerns or [],
                pipeline_stage=job.pipeline_stage,
                enrichment_data=job.enrichment_data,
                pipeline_data=job.pipeline_data,
                created_at=job.created_at,
            )
            for job in jobs
        ]

    except Exception as e:
        logger.error("Error fetching review jobs", extra={"error": str(e)})
        raise HTTPException(status_code=500, detail="Failed to fetch review jobs")


@router.post("/review-job")
async def review_job(
    request: JobReviewRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Handle user review action on a job before submission.
    
    Actions:
    - "approve": Move to prepared stage, create application, and submit
    - "reject": Move to skipped stage
    - "edit": Update cover letter and move to prepared stage
    
    Args:
        request: Review action with job_id and action
        db: Database session
    
    Returns:
        Status of the review action
    """
    try:
        job = await db.execute(select(Job).where(Job.id == request.job_id)).scalar_one_or_none()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        if request.action == "approve":
            job.pipeline_stage = "submitted"
            await db.commit()
            logger.info(f"Job {job.id} approved for submission")
            return {"status": "approved", "job_id": job.id, "message": "Job moved to submission queue"}

        elif request.action == "reject":
            job.pipeline_stage = "skipped"
            await db.commit()
            logger.info(f"Job {job.id} rejected by user")
            return {"status": "rejected", "job_id": job.id, "message": "Job skipped"}

        elif request.action == "edit":
            if not request.edited_cover_letter:
                raise HTTPException(
                    status_code=400,
                    detail="edited_cover_letter required for edit action",
                )
            # Store edited cover letter in pipeline_data
            job.pipeline_data = job.pipeline_data or {}
            job.pipeline_data["edited_cover_letter"] = request.edited_cover_letter
            job.pipeline_stage = "prepared"
            await db.commit()
            logger.info(f"Job {job.id} cover letter edited, moving to prepared stage")
            return {
                "status": "edited",
                "job_id": job.id,
                "message": "Cover letter updated, ready for submission",
            }

        else:
            raise HTTPException(status_code=400, detail=f"Invalid action: {request.action}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error reviewing job", extra={"error": str(e), "job_id": request.job_id})
        raise HTTPException(status_code=500, detail="Failed to process review")


@router.post("/update-stage/{job_id}")
async def update_job_stage(
    job_id: int,
    update: PipelineStageUpdate,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Update a job's pipeline stage (for internal use by automation service).
    
    Args:
        job_id: ID of the job to update
        update: New stage and optional pipeline data
        db: Database session
    
    Returns:
        Confirmation of stage update
    """
    try:
        job = await db.execute(select(Job).where(Job.id == job_id)).scalar_one_or_none()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        if update.pipeline_stage not in PIPELINE_STAGES:
            raise HTTPException(status_code=400, detail=f"Invalid pipeline stage: {update.pipeline_stage}")

        old_stage = job.pipeline_stage
        job.pipeline_stage = update.pipeline_stage

        if update.pipeline_data:
            job.pipeline_data = job.pipeline_data or {}
            job.pipeline_data.update(update.pipeline_data)

        await db.commit()
        logger.info(
            f"Job {job_id} moved from {old_stage} to {update.pipeline_stage}",
            extra={"job_id": job_id},
        )
        return {
            "status": "updated",
            "job_id": job_id,
            "old_stage": old_stage,
            "new_stage": update.pipeline_stage,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error updating job stage", extra={"error": str(e), "job_id": job_id})
        raise HTTPException(status_code=500, detail="Failed to update job stage")


@router.get("/stats")
async def get_pipeline_stats(db: AsyncSession = Depends(get_db)) -> dict:
    """
    Get comprehensive pipeline statistics.
    
    Args:
        db: Database session
    
    Returns:
        Pipeline stats with bottleneck analysis
    """
    try:
        stats = {}
        total_jobs = 0

        for stage in PIPELINE_STAGES:
            result = await db.execute(
                select(func.count(Job.id)).where(Job.pipeline_stage == stage)
            )
            count = result.scalar() or 0
            stats[stage] = count
            total_jobs += count

        # Calculate bottlenecks (stages where jobs are stuck)
        bottlenecks = []
        for stage, count in stats.items():
            if count > 20:  # Threshold for concern
                bottlenecks.append({"stage": stage, "count": count})

        return {
            "total_jobs": total_jobs,
            "by_stage": stats,
            "bottlenecks": bottlenecks,
            "timestamp": datetime.utcnow(),
        }

    except Exception as e:
        logger.error("Error getting pipeline stats", extra={"error": str(e)})
        raise HTTPException(status_code=500, detail="Failed to get pipeline stats")


@router.get("/application/{application_id}/full-review")
async def get_full_application_review(
    application_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Get complete application data for human review.
    
    Returns job details, tailored resume, and tailored cover letter.
    
    Args:
        application_id: ID of the application to review
        db: Database session
    
    Returns:
        Full application with job details, resume, and cover letter content
    """
    try:
        # Get the application
        app_result = await db.execute(
            select(Application).where(Application.id == application_id)
        )
        app = app_result.scalar_one_or_none()
        
        if not app:
            raise HTTPException(status_code=404, detail="Application not found")

        # Get the job
        job_result = await db.execute(
            select(Job).where(Job.id == app.job_id)
        )
        job = job_result.scalar_one_or_none()
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        # Get tailored resume
        resume_content = None
        resume_path = None
        if app.tailored_resume_id:
            doc_result = await db.execute(
                select(Document).where(Document.id == app.tailored_resume_id)
            )
            doc = doc_result.scalar_one_or_none()
            if doc:
                resume_content = doc.content_text
                resume_path = doc.file_path

        # Get tailored cover letter
        cover_letter_content = None
        cover_letter_path = None
        if app.tailored_cover_letter_id:
            doc_result = await db.execute(
                select(Document).where(Document.id == app.tailored_cover_letter_id)
            )
            doc = doc_result.scalar_one_or_none()
            if doc:
                cover_letter_content = doc.content_text
                cover_letter_path = doc.file_path

        return {
            "application_id": app.id,
            "application_status": app.status,
            "job": {
                "id": job.id,
                "title": job.title,
                "company": job.company,
                "location": job.location,
                "job_type": job.job_type,
                "source": job.source,
                "source_url": job.source_url,
                "apply_url": job.apply_url,
                "description": job.description,
                "requirements": job.requirements,
                "salary_range": job.salary_range,
                "score": job.score,
                "score_reasoning": job.score_reasoning,
                "score_strengths": job.score_strengths or [],
                "score_concerns": job.score_concerns or [],
                "posted_date": job.posted_date,
                "pipeline_stage": job.pipeline_stage,
                "created_at": job.created_at.isoformat() if job.created_at else None,
            },
            "tailored_resume": {
                "content": resume_content,
                "path": resume_path,
            },
            "tailored_cover_letter": {
                "content": cover_letter_content,
                "path": cover_letter_path,
            },
            "created_at": app.created_at.isoformat() if app.created_at else None,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching application for review: {e}", extra={"error": str(e)})
        raise HTTPException(status_code=500, detail="Failed to fetch application")


@router.post("/application/{application_id}/approve-and-submit")
async def approve_and_submit_application(
    application_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Approve an application and submit it to the job.
    
    Moves job to 'submitted' stage and triggers auto-apply.
    
    Args:
        application_id: ID of application to approve and submit
        db: Database session
    
    Returns:
        Submission status and result
    """
    try:
        from ..services import auto_apply_service
        
        # Get the application
        app_result = await db.execute(
            select(Application).where(Application.id == application_id)
        )
        app = app_result.scalar_one_or_none()
        
        if not app:
            raise HTTPException(status_code=404, detail="Application not found")

        # Get the job
        job_result = await db.execute(
            select(Job).where(Job.id == app.job_id)
        )
        job = job_result.scalar_one_or_none()
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        # Move job to submitted stage
        job.pipeline_stage = "submitted"

        try:
            # Perform auto-apply submission
            result = await auto_apply_service.run_full_auto_apply(db, application_id)
            
            if result.get("status") == "success":
                app.status = "applied"
                app.applied_date = datetime.utcnow()
                await db.commit()
                
                logger.info(
                    f"Application {application_id} approved and submitted successfully",
                    extra={"job_id": job.id, "result": result.get("message")},
                )

                return {
                    "success": True,
                    "message": "Application submitted successfully",
                    "application_id": application_id,
                    "submission_result": result,
                }
            else:
                # Still mark as submitted even if there was an error
                app.status = "applied"
                app.last_error = result.get("message")
                await db.commit()
                
                logger.warning(
                    f"Application {application_id} submission encountered issues",
                    extra={"job_id": job.id, "error": result.get("message")},
                )

                return {
                    "success": False,
                    "message": f"Submission encountered issues: {result.get('message')}",
                    "application_id": application_id,
                    "submission_result": result,
                }

        except Exception as e:
            app.last_error = str(e)
            await db.commit()
            
            logger.error(
                f"Error submitting application {application_id}: {e}",
                extra={"job_id": job.id, "error": str(e)},
            )

            return {
                "success": False,
                "message": f"Submission error: {str(e)}",
                "application_id": application_id,
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error approving application: {e}", extra={"error": str(e)})
        raise HTTPException(status_code=500, detail="Failed to approve application")


@router.post("/application/{application_id}/reject")
async def reject_application(
    application_id: int,
    rejection_reason: str = Query(None, description="Reason for rejection"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Reject an application and mark it as skipped.
    
    Moves job to 'skipped' stage.
    
    Args:
        application_id: ID of application to reject
        rejection_reason: Optional reason for rejection
        db: Database session
    
    Returns:
        Rejection confirmation
    """
    try:
        # Get the application
        app_result = await db.execute(
            select(Application).where(Application.id == application_id)
        )
        app = app_result.scalar_one_or_none()
        
        if not app:
            raise HTTPException(status_code=404, detail="Application not found")

        # Get the job
        job_result = await db.execute(
            select(Job).where(Job.id == app.job_id)
        )
        job = job_result.scalar_one_or_none()
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        # Move job to skipped stage
        job.pipeline_stage = "skipped"
        app.status = "withdrawn"
        app.notes = rejection_reason or "Rejected during review"

        await db.commit()

        logger.info(
            f"Application {application_id} rejected",
            extra={"job_id": job.id, "reason": rejection_reason},
        )

        return {
            "success": True,
            "message": "Application rejected and marked as skipped",
            "application_id": application_id,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rejecting application: {e}", extra={"error": str(e)})
        raise HTTPException(status_code=500, detail="Failed to reject application")
