"""
Job sync scheduler service.

Manages periodic job synchronization from configured sources.
"""

import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional

from .job_sources import JobSourceManager
from ..logging_config import get_logger

# Defer logger
_logger = None


def get_logger_instance():
    global _logger
    if _logger is None:
        _logger = get_logger(__name__)
    return _logger


class JobSyncScheduler:
    """Manages scheduled job synchronization."""
    
    def __init__(self, job_manager: JobSourceManager):
        """
        Initialize scheduler with job manager.
        
        Args:
            job_manager: JobSourceManager instance
        """
        self.job_manager = job_manager
        self.is_running = False
        self.last_sync_at = None
        self.next_sync_at = None
        self.sync_interval_minutes = 60  # Default: hourly
    
    def set_sync_interval(self, minutes: int) -> None:
        """
        Set job sync interval in minutes.
        
        Args:
            minutes: Interval between syncs (minimum 5 minutes)
            
        Raises:
            ValueError: If minutes < 5
        """
        if minutes < 5:
            raise ValueError("Sync interval must be at least 5 minutes")
        
        self.sync_interval_minutes = minutes
        logger = get_logger_instance()
        logger.info("Job sync interval updated", extra_fields={
            "interval_minutes": minutes,
        })
    
    def get_config(self) -> Dict:
        """
        Get current scheduler configuration.
        
        Returns:
            Dict with scheduler config
        """
        return {
            "is_running": self.is_running,
            "interval_minutes": self.sync_interval_minutes,
            "last_sync_at": self.last_sync_at.isoformat() if self.last_sync_at else None,
            "next_sync_at": self.next_sync_at.isoformat() if self.next_sync_at else None,
            "sources_count": len(self.job_manager.sources),
            "sources": list(self.job_manager.sources.keys()),
        }
    
    async def sync_now(self) -> Dict:
        """
        Execute job sync immediately.
        
        Returns:
            Dict with sync results: {added, duplicates, errors, duration_ms}
        """
        logger = get_logger_instance()
        
        start_time = datetime.now(timezone.utc)
        logger.info("Starting on-demand job sync", extra_fields={
            "sources_count": len(self.job_manager.sources),
        })
        
        try:
            # Execute sync
            stats = await self.job_manager.sync()
            
            # Update tracking
            self.last_sync_at = datetime.now(timezone.utc)
            self.next_sync_at = self.last_sync_at + timedelta(minutes=self.sync_interval_minutes)
            
            # Calculate duration
            duration_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
            
            # Log results
            logger.info("Job sync completed successfully", extra_fields={
                "duration_ms": duration_ms,
                "added": stats.get("added", 0),
                "duplicates": stats.get("duplicates", 0),
                "errors": stats.get("errors", 0),
            })
            
            return {
                "status": "success",
                "timestamp": start_time.isoformat(),
                "duration_ms": duration_ms,
                "stats": stats,
            }
        
        except Exception as e:
            logger.error(f"Job sync failed: {e}", extra_fields={
                "error": str(e),
            })
            
            # Update next retry time
            self.next_sync_at = datetime.now(timezone.utc) + timedelta(minutes=5)
            
            return {
                "status": "error",
                "timestamp": start_time.isoformat(),
                "error": str(e),
                "next_retry_at": self.next_sync_at.isoformat(),
            }
    
    async def schedule_periodic_sync(self, interval_minutes: int = 60) -> None:
        """
        Run periodic job sync in background.
        
        This is a coroutine that runs indefinitely. In production,
        use AWS EventBridge or similar for scheduled execution.
        
        Args:
            interval_minutes: Sync interval in minutes
        """
        logger = get_logger_instance()
        
        self.set_sync_interval(interval_minutes)
        self.is_running = True
        
        logger.info("Starting periodic job sync scheduler", extra_fields={
            "interval_minutes": interval_minutes,
        })
        
        while self.is_running:
            try:
                # Execute sync
                await self.sync_now()
                
                # Wait for next sync
                logger.info(f"Job sync waiting {self.sync_interval_minutes} minutes until next sync", extra_fields={
                    "next_sync_at": self.next_sync_at.isoformat() if self.next_sync_at else None,
                })
                
                await asyncio.sleep(self.sync_interval_minutes * 60)
            
            except asyncio.CancelledError:
                logger.info("Periodic job sync scheduler stopped")
                self.is_running = False
                break
            
            except Exception as e:
                logger.error(f"Error in periodic sync: {e}", extra_fields={
                    "error": str(e),
                })
                
                # Wait 5 minutes before retrying
                await asyncio.sleep(5 * 60)


# Global scheduler instance
_scheduler: Optional[JobSyncScheduler] = None


def get_scheduler() -> Optional[JobSyncScheduler]:
    """Get the global scheduler instance."""
    return _scheduler


def set_scheduler(scheduler: JobSyncScheduler) -> None:
    """Set the global scheduler instance."""
    global _scheduler
    _scheduler = scheduler
