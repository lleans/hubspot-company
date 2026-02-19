from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import joinedload
from sqlalchemy import desc, and_
from models.database import get_db_session
from models.extraction_job import ExtractionJob
from utils.exceptions import DatabaseError
import logging

logger = logging.getLogger(__name__)

class JobService:
    """
    Service for managing extraction job lifecycle and database operations
    All database operations are properly wrapped in session contexts
    """
    
    def create_job(self, connection_id: str, status: str = 'pending', message: str = None) -> str:
        """
        Create a new extraction job
        
        Args:
            connection_id: Unique identifier for this extraction
            status: Initial job status
            message: Optional initial message
            
        Returns:
            str: Created job ID
            
        Raises:
            DatabaseError: If job creation fails
        """
        try:
            with get_db_session() as session:
                job = ExtractionJob(
                    connection_id=connection_id,
                    status=status,
                    start_time=datetime.utcnow(),
                    message=message or f'Job created for connection {connection_id}'
                )
                
                session.add(job)
                session.flush()  # Get the ID without committing
                job_id = job.id
                
                logger.info(f"Created extraction job {job_id} for connection {connection_id}")
                return job_id
                
        except Exception as e:
            logger.error(f"Failed to create job for connection {connection_id}: {str(e)}")
            raise DatabaseError(f"Failed to create extraction job: {str(e)}")
    
    def get_job_by_id(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get job by ID with complete information
        
        Args:
            job_id: Job identifier
            
        Returns:
            Dictionary with job information or None if not found
        """
        try:
            with get_db_session() as session:
                job = session.query(ExtractionJob).filter_by(id=job_id).first()
                
                if not job:
                    return None
                
                # Use to_dict() which handles datetime serialization
                return job.to_dict()
                
        except Exception as e:
            logger.error(f"Failed to get job {job_id}: {str(e)}")
            raise DatabaseError(f"Failed to retrieve job: {str(e)}")
    
    def get_job_by_connection_id(self, connection_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the most recent job by connection ID
        
        Args:
            connection_id: Connection identifier
            
        Returns:
            Dictionary with job information or None if not found
        """
        try:
            with get_db_session() as session:
                # Get the most recent job for this connection_id
                job = session.query(ExtractionJob)\
                    .filter_by(connection_id=connection_id)\
                    .order_by(desc(ExtractionJob.created_at))\
                    .first()
                
                if not job:
                    return None
                
                # Use to_dict() which handles datetime serialization
                return job.to_dict()
                
        except Exception as e:
            logger.error(f"Failed to get job for connection {connection_id}: {str(e)}")
            raise DatabaseError(f"Failed to retrieve job: {str(e)}")
    
    def update_job_status(self, job_id: str, status: str, message: str = None, error_details: str = None) -> bool:
        """
        Update job status and message
        
        Args:
            job_id: Job identifier
            status: New status
            message: Optional status message
            error_details: Optional error details
            
        Returns:
            bool: True if update was successful
        """
        try:
            with get_db_session() as session:
                job = session.query(ExtractionJob).filter_by(id=job_id).first()
                
                if not job:
                    logger.warning(f"Job {job_id} not found for status update")
                    return False
                
                job.status = status
                if message:
                    job.message = message
                if error_details:
                    job.error_details = error_details
                
                # Set end time for terminal states
                if status in ['completed', 'failed', 'cancelled']:
                    job.end_time = datetime.utcnow()
                    job.extraction_duration_seconds = job.calculate_duration()
                
                # Commit is handled by the context manager
                logger.info(f"Updated job {job_id} status to {status}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to update job {job_id} status: {str(e)}")
            raise DatabaseError(f"Failed to update job status: {str(e)}")
    
    def update_job_progress(self, job_id: str, progress_data: Dict[str, Any]) -> bool:
        """
        Update job progress information
        
        Args:
            job_id: Job identifier
            progress_data: Dictionary with progress fields
            
        Returns:
            bool: True if update was successful
        """
        try:
            with get_db_session() as session:
                job = session.query(ExtractionJob).filter_by(id=job_id).first()
                
                if not job:
                    logger.warning(f"Job {job_id} not found for progress update")
                    return False
                
                # Update progress fields
                for field, value in progress_data.items():
                    if hasattr(job, field) and value is not None:
                        setattr(job, field, value)
                
                # Commit is handled by the context manager
                logger.debug(f"Updated job {job_id} progress: {progress_data}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to update job {job_id} progress: {str(e)}")
            raise DatabaseError(f"Failed to update job progress: {str(e)}")
    
    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get job status with summary information
        
        Args:
            job_id: Job identifier
            
        Returns:
            Dictionary with job status or None if not found
        """
        try:
            with get_db_session() as session:
                job = session.query(ExtractionJob).filter_by(id=job_id).first()
                
                if not job:
                    return None
                
                # Get record counts using the relationships
                companies_count = job.companies.count()
                deals_count = job.deals.count()
                pipelines_count = job.pipelines.count()
                
                # Get serialized job data (handles datetime conversion)
                status_info = job.to_dict()
                status_info.update({
                    'companies_count': companies_count,
                    'deals_count': deals_count,
                    'pipelines_count': pipelines_count,
                    'total_records': companies_count + deals_count + pipelines_count
                })
                
                return status_info
                
        except Exception as e:
            logger.error(f"Failed to get job status {job_id}: {str(e)}")
            raise DatabaseError(f"Failed to get job status: {str(e)}")
    
    def get_active_jobs(self) -> List[Dict[str, Any]]:
        """
        Get all active (running or pending) jobs
        
        Returns:
            List of active job dictionaries
        """
        try:
            with get_db_session() as session:
                active_jobs = session.query(ExtractionJob).filter(
                    ExtractionJob.status.in_(['pending', 'running'])
                ).order_by(desc(ExtractionJob.created_at)).all()
                
                return [job.to_dict() for job in active_jobs]
                
        except Exception as e:
            logger.error(f"Failed to get active jobs: {str(e)}")
            raise DatabaseError(f"Failed to get active jobs: {str(e)}")
    
    def get_recent_jobs(self, limit: int = 10, days: int = 7) -> List[Dict[str, Any]]:
        """
        Get recent jobs within specified timeframe
        
        Args:
            limit: Maximum number of jobs to return
            days: Number of days to look back
            
        Returns:
            List of recent job dictionaries
        """
        try:
            with get_db_session() as session:
                cutoff_date = datetime.utcnow() - timedelta(days=days)
                
                recent_jobs = session.query(ExtractionJob).filter(
                    ExtractionJob.created_at >= cutoff_date
                ).order_by(desc(ExtractionJob.created_at)).limit(limit).all()
                
                return [job.to_dict() for job in recent_jobs]
                
        except Exception as e:
            logger.error(f"Failed to get recent jobs: {str(e)}")
            raise DatabaseError(f"Failed to get recent jobs: {str(e)}")
    
    def delete_job(self, job_id: str) -> bool:
        """
        Delete a job and all associated data (cascading delete)
        
        Args:
            job_id: Job identifier
            
        Returns:
            bool: True if deletion was successful
        """
        try:
            with get_db_session() as session:
                job = session.query(ExtractionJob).filter_by(id=job_id).first()
                
                if not job:
                    logger.warning(f"Job {job_id} not found for deletion")
                    return False
                
                # Get counts before deletion for logging
                companies_count = job.companies.count()
                deals_count = job.deals.count()
                pipelines_count = job.pipelines.count()
                
                # Delete the job (cascade will handle related records)
                session.delete(job)
                # Commit is handled by the context manager
                
                logger.info(f"Deleted job {job_id} with {companies_count} companies, {deals_count} deals, {pipelines_count} pipelines")
                return True
                
        except Exception as e:
            logger.error(f"Failed to delete job {job_id}: {str(e)}")
            raise DatabaseError(f"Failed to delete job: {str(e)}")
    
    def cleanup_old_jobs(self, days: int = 30, keep_successful: bool = True) -> int:
        """
        Clean up old jobs based on age and status
        
        Args:
            days: Age threshold in days
            keep_successful: Whether to keep successful jobs
            
        Returns:
            int: Number of jobs deleted
        """
        try:
            with get_db_session() as session:
                cutoff_date = datetime.utcnow() - timedelta(days=days)
                
                query = session.query(ExtractionJob).filter(
                    ExtractionJob.created_at < cutoff_date
                )
                
                # Optionally keep successful jobs
                if keep_successful:
                    query = query.filter(ExtractionJob.status != 'completed')
                
                old_jobs = query.all()
                deleted_count = len(old_jobs)
                
                for job in old_jobs:
                    session.delete(job)
                
                # Commit is handled by the context manager
                logger.info(f"Cleaned up {deleted_count} old jobs older than {days} days")
                return deleted_count
                
        except Exception as e:
            logger.error(f"Failed to cleanup old jobs: {str(e)}")
            raise DatabaseError(f"Failed to cleanup old jobs: {str(e)}")
    
    def get_job_statistics(self) -> Dict[str, Any]:
        """
        Get overall job statistics
        
        Returns:
            Dictionary with job statistics
        """
        try:
            with get_db_session() as session:
                total_jobs = session.query(ExtractionJob).count()
                active_jobs = session.query(ExtractionJob).filter(
                    ExtractionJob.status.in_(['pending', 'running'])
                ).count()
                completed_jobs = session.query(ExtractionJob).filter_by(status='completed').count()
                failed_jobs = session.query(ExtractionJob).filter_by(status='failed').count()
                
                # Get average duration for completed jobs
                completed_with_duration = session.query(ExtractionJob).filter(
                    and_(
                        ExtractionJob.status == 'completed',
                        ExtractionJob.extraction_duration_seconds.isnot(None)
                    )
                ).all()
                
                avg_duration = None
                if completed_with_duration:
                    total_duration = sum(job.extraction_duration_seconds for job in completed_with_duration)
                    avg_duration = total_duration / len(completed_with_duration)
                
                return {
                    'total_jobs': total_jobs,
                    'active_jobs': active_jobs,
                    'completed_jobs': completed_jobs,
                    'failed_jobs': failed_jobs,
                    'success_rate': (completed_jobs / total_jobs * 100) if total_jobs > 0 else 0,
                    'average_extraction_time': avg_duration
                }
                
        except Exception as e:
            logger.error(f"Failed to get job statistics: {str(e)}")
            raise DatabaseError(f"Failed to get job statistics: {str(e)}")
    
    def job_exists(self, job_id: str) -> bool:
        """
        Check if a job exists
        
        Args:
            job_id: Job identifier
            
        Returns:
            bool: True if job exists
        """
        try:
            with get_db_session() as session:
                job = session.query(ExtractionJob).filter_by(id=job_id).first()
                return job is not None
                
        except Exception as e:
            logger.error(f"Failed to check if job {job_id} exists: {str(e)}")
            return False
        
    def get_jobs_paginated(self, page: int = 1, per_page: int = 20, status_filter: str = None) -> tuple:
        """
        Get paginated list of jobs
        
        Args:
            page: Page number (1-based)
            per_page: Number of jobs per page
            status_filter: Optional status filter
            
        Returns:
            Tuple of (jobs_list, total_count)
        """
        try:
            with get_db_session() as session:
                query = session.query(ExtractionJob)
                
                # Apply status filter if provided
                if status_filter:
                    query = query.filter(ExtractionJob.status == status_filter.lower())
                
                # Get total count
                total_count = query.count()
                
                # Apply pagination and ordering
                offset = (page - 1) * per_page
                jobs = query.order_by(desc(ExtractionJob.created_at))\
                    .offset(offset)\
                    .limit(per_page)\
                    .all()
                
                # Convert to dictionaries
                jobs_list = [job.to_dict() for job in jobs]
                
                return jobs_list, total_count
                
        except Exception as e:
            logger.error(f"Failed to get paginated jobs: {str(e)}")
            raise DatabaseError(f"Failed to get paginated jobs: {str(e)}")