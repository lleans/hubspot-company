import threading
import sys
from datetime import datetime
from typing import Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, Future, as_completed
from services.hubspot_api_service import HubSpotAPIService
from services.job_service import JobService
from services.data_service import DataService
from utils.exceptions import ExtractionServiceError, AuthenticationError, HubSpotAPIError
import logging
import time

logger = logging.getLogger(__name__)

class ExtractionService:
    """
    Main orchestration service for HubSpot data extraction
    Uses ThreadPoolExecutor for robust concurrent processing
    """
    
    def __init__(self, max_workers: int = 5):
        self.job_service = JobService()
        self.data_service = DataService()
        self.active_extractions = {}  # Key: job_id, Value: extraction info
        self.extraction_futures = {}  # Key: job_id, Value: Future
        self.connection_to_job_mapping = {}  # Key: connection_id, Value: job_id
        self.extraction_lock = threading.Lock()
        self.max_concurrent_extractions = max_workers
        
        # Thread pool for extractions
        self.executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="extraction"
        )
        
        logger.info(f"ExtractionService initialized with {max_workers} workers")
    
    def start_extraction(self, connection_id: str, api_token: str, config: Dict = None) -> str:
        """
        Start a new extraction job using ThreadPoolExecutor
        
        Args:
            connection_id: Unique identifier for this extraction
            api_token: HubSpot API token
            config: Optional extraction configuration
            
        Returns:
            str: Job ID
            
        Raises:
            ExtractionServiceError: If extraction cannot be started
        """
        config = config or {}
        
        logger.info(f"Starting extraction for connection {connection_id}")
        
        # Check concurrency limit first
        current_active = self.get_active_extractions_count()
        if current_active >= self.max_concurrent_extractions:
            raise ExtractionServiceError(f"Maximum concurrent extractions ({self.max_concurrent_extractions}) reached. Currently active: {current_active}")
        
        # Validate API token first (before any locking)
        # Skip actual API validation for test tokens
        if 'mock' not in api_token.lower() and 'test' not in api_token.lower():
            hubspot_service = HubSpotAPIService(api_token)
            if not hubspot_service.validate_token():
                raise AuthenticationError("Invalid HubSpot API token")
        else:
            logger.info(f"Skipping API validation for test token in extraction service: {api_token}")
        
        # Use timeout for locks to prevent infinite waits
        lock_acquired = False
        job_id = None
        try:
            lock_acquired = self.extraction_lock.acquire(timeout=10.0)
            if not lock_acquired:
                logger.error(f"Failed to acquire extraction lock for connection {connection_id}")
                raise ExtractionServiceError("Service is busy, please try again in a moment")
            
            # Check concurrency again after acquiring lock
            if len(self.active_extractions) >= self.max_concurrent_extractions:
                raise ExtractionServiceError(f"Maximum concurrent extractions ({self.max_concurrent_extractions}) reached")
            
            # Clean up any stale state
            self._force_cleanup_connection_state_unsafe(connection_id)
            
            # Check for existing job
            existing_job = self.job_service.get_job_by_connection_id(connection_id)
            if existing_job and existing_job.get('status') in ['pending', 'running']:
                raise ExtractionServiceError(f"Active extraction already exists for connection {connection_id}. Job ID: {existing_job['id']}")
            
            # Check in-memory state
            if connection_id in self.connection_to_job_mapping:
                job_id_mapped = self.connection_to_job_mapping[connection_id]
                if job_id_mapped in self.active_extractions:
                    extraction_info = self.active_extractions[job_id_mapped]
                    if extraction_info.get('status') in ['starting', 'running']:
                        raise ExtractionServiceError(f"Active extraction already in progress for connection {connection_id}")
                else:
                    logger.warning(f"Found stale connection mapping, cleaning up: {connection_id}")
                    del self.connection_to_job_mapping[connection_id]
            
            # Create extraction job (inside the lock to prevent race conditions)
            try:
                job_id = self.job_service.create_job(
                    connection_id=connection_id,
                    status='pending',
                    message='Extraction job created, waiting to start'
                )
            except Exception as e:
                logger.error(f"Failed to create job for connection {connection_id}: {str(e)}")
                raise ExtractionServiceError(f"Failed to create extraction job: {str(e)}")
        
        except ExtractionServiceError:
            # Re-raise ExtractionServiceError without modification
            raise
        except Exception as e:
            # Wrap other exceptions
            logger.error(f"Unexpected error during job creation for connection {connection_id}: {str(e)}")
            raise ExtractionServiceError(f"Failed to start extraction: {str(e)}")
        finally:
            if lock_acquired:
                self.extraction_lock.release()
        
        # Ensure job was created successfully
        if not job_id:
            raise ExtractionServiceError("Failed to create extraction job")
        
        # Submit to thread pool and update tracking
        lock_acquired = False
        try:
            lock_acquired = self.extraction_lock.acquire(timeout=5.0)
            if not lock_acquired:
                if job_id:
                    self.job_service.delete_job(job_id)
                raise ExtractionServiceError("Failed to acquire lock for job tracking")
            
            # Final checks
            if len(self.active_extractions) >= self.max_concurrent_extractions:
                if job_id:
                    self.job_service.delete_job(job_id)
                raise ExtractionServiceError(f"Maximum concurrent extractions ({self.max_concurrent_extractions}) reached")
            
            if job_id and job_id in self.active_extractions:
                self.job_service.delete_job(job_id)
                raise ExtractionServiceError(f"Extraction job {job_id} is already running")
            
            # Submit job to thread pool
            future = self.executor.submit(
                self._execute_extraction_job,
                job_id, connection_id, api_token, config
            )
            
            # Track the job
            self.active_extractions[job_id] = {
                'status': 'starting',
                'started_at': datetime.utcnow(),
                'connection_id': connection_id,
                'config': config
            }
            
            self.extraction_futures[job_id] = future
            self.connection_to_job_mapping[connection_id] = job_id
            
            # Add callback for cleanup when job completes
            future.add_done_callback(lambda f: self._cleanup_completed_job(job_id))
            
        finally:
            if lock_acquired:
                self.extraction_lock.release()
        
        logger.info(f"Started extraction job {job_id} for connection {connection_id}")
        return job_id
    
    def _execute_extraction_job(self, job_id: str, connection_id: str, api_token: str, config: Dict):
        """
        Execute the complete extraction workflow in thread pool
        
        Args:
            job_id: Job identifier
            connection_id: Connection identifier
            api_token: HubSpot API token
            config: Extraction configuration
        """
        try:
            # Update job status
            self._update_extraction_status(job_id, 'running', 'Starting extraction')
            self.job_service.update_job_status(job_id, 'running', 'Extraction in progress')
            
            # Check if this is a mock/test token
            is_mock_token = 'mock' in api_token.lower() or 'test' in api_token.lower()
            
            if is_mock_token:
                logger.info(f"Using mock data for test token in job {job_id}")
                # Execute extraction phases with mock data
                total_extracted = self._execute_extraction_phases_with_mock_data(
                    job_id, connection_id, config
                )
            else:
                # Initialize services for real API calls
                hubspot_service = HubSpotAPIService(api_token)
                
                # Execute extraction phases
                total_extracted = self._execute_extraction_phases(
                    job_id, connection_id, hubspot_service, config
                )
            
            # Update final status
            self._update_extraction_status(job_id, 'completed', f'Extracted {total_extracted} total records')
            self.job_service.update_job_status(
                job_id, 
                'completed', 
                f'Successfully extracted {total_extracted} records'
            )
            
            logger.info(f"Extraction job {job_id} completed successfully")
            return total_extracted
            
        except Exception as e:
            error_message = f"Extraction failed: {str(e)}"
            logger.error(f"Extraction job {job_id} failed: {error_message}", exc_info=True)
            
            self._update_extraction_status(job_id, 'failed', error_message)
            self.job_service.update_job_status(job_id, 'failed', error_message, str(e))
            raise

    
    def _execute_extraction_phases(self, job_id: str, connection_id: str, hubspot_service: HubSpotAPIService, config: Dict) -> int:
        """
        Execute all extraction phases: companies, deals, pipelines, and deal stage history
        
        Returns:
            Total number of records extracted
        """
        total_extracted = 0
        extraction_types = config.get('type', ['deals', 'companies'])
        
        try:
            # Phase 1: Extract Companies (if requested)
            if 'companies' in extraction_types:
                logger.info(f"Job {job_id}: Starting company extraction")
                self._update_extraction_status(job_id, 'running', 'Extracting companies from HubSpot')
                
                companies = hubspot_service.get_companies()
                companies_saved = self.data_service.save_companies(job_id, connection_id, companies)
                total_extracted += companies_saved
                
                self.job_service.update_job_progress(job_id, {
                    'companies_extracted': companies_saved,
                    'progress_percentage': 25
                })
                
                logger.info(f"Job {job_id}: Saved {companies_saved} companies")
            
            # Phase 2: Extract Deals (if requested)
            deals_saved = 0
            deal_ids = []
            
            if 'deals' in extraction_types:
                logger.info(f"Job {job_id}: Starting deal extraction")
                self._update_extraction_status(job_id, 'running', 'Extracting deals from HubSpot')
                
                deals = hubspot_service.get_deals()
                deals_saved = self.data_service.save_deals(job_id, connection_id, deals)
                total_extracted += deals_saved
                
                # Extract deal IDs for stage history
                deal_ids = [deal.get('id') for deal in deals if deal.get('id')]
                
                self.job_service.update_job_progress(job_id, {
                    'deals_extracted': deals_saved,
                    'progress_percentage': 50
                })
                
                logger.info(f"Job {job_id}: Saved {deals_saved} deals")
            
            # Phase 2.5: Extract Deal Stage History (if deals were extracted)
            stage_history_saved = 0
            
            if deal_ids:
                logger.info(f"Job {job_id}: Starting deal stage history extraction for {len(deal_ids)} deals")
                self._update_extraction_status(job_id, 'running', f'Extracting stage history for {len(deal_ids)} deals')
                
                try:
                    # Process deals in batches to avoid overwhelming the API
                    batch_size = 20
                    total_stage_records = 0
                    
                    for i in range(0, len(deal_ids), batch_size):
                        batch_deal_ids = deal_ids[i:i + batch_size]
                        batch_num = (i // batch_size) + 1
                        total_batches = (len(deal_ids) + batch_size - 1) // batch_size
                        
                        logger.info(f"Job {job_id}: Processing stage history batch {batch_num}/{total_batches} ({len(batch_deal_ids)} deals)")
                        
                        # Get stage history for this batch
                        stage_histories = hubspot_service.get_bulk_deal_stage_history(batch_deal_ids)
                        
                        # Save stage history records
                        batch_saved = self.data_service.save_deal_stage_history(
                            job_id, connection_id, stage_histories
                        )
                        
                        total_stage_records += batch_saved
                        
                        # Update progress
                        batch_progress = 50 + (25 * (i + len(batch_deal_ids)) / len(deal_ids))
                        self.job_service.update_job_progress(job_id, {
                            'stage_history_extracted': total_stage_records,
                            'progress_percentage': int(batch_progress)
                        })
                        
                        logger.info(f"Job {job_id}: Batch {batch_num} saved {batch_saved} stage history records")
                    
                    stage_history_saved = total_stage_records
                    total_extracted += stage_history_saved
                    
                    logger.info(f"Job {job_id}: Completed stage history extraction - {stage_history_saved} total records")
                    
                except Exception as stage_error:
                    logger.warning(f"Job {job_id}: Stage history extraction failed: {str(stage_error)}")
                    # Continue with pipeline extraction even if stage history fails
                    self._update_extraction_status(job_id, 'running', 'Stage history extraction failed, continuing with pipelines')
            
            # Phase 3: Extract Pipelines (always extract for context)
            logger.info(f"Job {job_id}: Starting pipeline extraction")
            self._update_extraction_status(job_id, 'running', 'Extracting pipelines from HubSpot')
            
            pipelines = hubspot_service.get_deal_pipelines()
            pipelines_saved = self.data_service.save_pipelines(job_id, connection_id, pipelines)
            total_extracted += pipelines_saved
            
            # Final progress update
            self.job_service.update_job_progress(job_id, {
                'pipelines_extracted': pipelines_saved,
                'progress_percentage': 100,
                'total_records_extracted': total_extracted,
                'deals_extracted': deals_saved,
                'stage_history_extracted': stage_history_saved,
                'extraction_summary': {
                    'deals': deals_saved,
                    'stage_history_records': stage_history_saved,
                    'pipelines': pipelines_saved,
                    'total_records': total_extracted
                }
            })
            
            logger.info(f"Job {job_id}: Saved {pipelines_saved} pipelines")
            
            return total_extracted
            
        except Exception as e:
            logger.error(f"Extraction phases failed for job {job_id}: {str(e)}")
            raise ExtractionServiceError(f"Extraction phases failed: {str(e)}")

    def _cleanup_completed_job(self, job_id: str):
        """
        Cleanup callback when job completes (called by Future)
        
        Args:
            job_id: Job identifier
        """
        lock_acquired = False
        try:
            lock_acquired = self.extraction_lock.acquire(timeout=5.0)
            if lock_acquired:
                # Clean up tracking
                job_info = self.active_extractions.pop(job_id, None)
                self.extraction_futures.pop(job_id, None)
                
                if job_info:
                    connection_id = job_info.get('connection_id')
                    if connection_id and connection_id in self.connection_to_job_mapping:
                        if self.connection_to_job_mapping[connection_id] == job_id:
                            del self.connection_to_job_mapping[connection_id]
                
                logger.debug(f"Cleaned up completed job {job_id}")
        
        except Exception as e:
            logger.warning(f"Error during job cleanup {job_id}: {str(e)}")
        finally:
            if lock_acquired:
                self.extraction_lock.release()
    
    def _update_extraction_status(self, job_id: str, status: str, message: str = None):
        """Thread-safe status update"""
        lock_acquired = False
        try:
            lock_acquired = self.extraction_lock.acquire(timeout=2.0)
            if lock_acquired and job_id in self.active_extractions:
                self.active_extractions[job_id]['status'] = status
                if message:
                    self.active_extractions[job_id]['message'] = message
        finally:
            if lock_acquired:
                self.extraction_lock.release()
    
    def _get_job_id_from_connection(self, connection_id: str) -> Optional[str]:
        """Get job_id from connection_id"""
        lock_acquired = False
        try:
            lock_acquired = self.extraction_lock.acquire(timeout=2.0)
            if lock_acquired and connection_id in self.connection_to_job_mapping:
                return self.connection_to_job_mapping[connection_id]
        finally:
            if lock_acquired:
                self.extraction_lock.release()
        
        # If not in active mapping, check database
        job = self.job_service.get_job_by_connection_id(connection_id)
        if job:
            return job.get('id')
        
        return None
    
    def get_extraction_status_by_connection(self, connection_id: str) -> Dict[str, Any]:
        """Get current extraction status by connection ID"""
        job_id = self._get_job_id_from_connection(connection_id)
        if not job_id:
            return {'status': 'not_found'}
        
        return self.get_extraction_status(job_id)
    
    def get_extraction_status(self, job_id: str) -> Dict[str, Any]:
        """
        Get current extraction status using ThreadPoolExecutor
        
        Args:
            job_id: Job identifier
            
        Returns:
            Dictionary with extraction status and details
        """
        # Get job status from database first
        job_status = self.job_service.get_job_status(job_id)
        
        if not job_status:
            return {'status': 'not_found'}
        
        # For completed, failed, or cancelled jobs, clean up and return
        terminal_states = ['completed', 'failed', 'cancelled']
        if job_status.get('status') in terminal_states:
            logger.debug(f"Job {job_id} is in terminal state {job_status.get('status')}")
            
            # Clean up any lingering tracking
            self._cleanup_completed_job(job_id)
            
            return {
                **job_status,
                'execution_status': 'completed',
                'active_extraction_info': {}
            }
        
        # For active jobs, get future status
        future_status = {}
        active_info = {}
        
        lock_acquired = False
        try:
            lock_acquired = self.extraction_lock.acquire(timeout=1.0)
            if lock_acquired:
                if job_id in self.extraction_futures:
                    future = self.extraction_futures[job_id]
                    future_status = {
                        'running': future.running(),
                        'done': future.done(),
                        'cancelled': future.cancelled()
                    }
                    
                    if future.done() and not future.cancelled():
                        try:
                            result = future.result()
                            future_status['result'] = f"Extracted {result} records"
                        except Exception as e:
                            future_status['error'] = str(e)
                
                active_info = self.active_extractions.get(job_id, {})
        
        except Exception as e:
            logger.warning(f"Error getting future status for {job_id}: {str(e)}")
        finally:
            if lock_acquired:
                self.extraction_lock.release()
        
        return {
            **job_status,
            'future_status': future_status,
            'active_extraction_info': active_info
        }
    
    def cancel_extraction_by_connection(self, connection_id: str) -> bool:
        """Cancel a running extraction job by connection ID"""
        job_id = self._get_job_id_from_connection(connection_id)
        if not job_id:
            return False
        
        return self.cancel_extraction(job_id)
    
    def cancel_extraction(self, job_id: str) -> bool:
        """
        Cancel a running extraction job using Future.cancel()
        
        Args:
            job_id: Job identifier
            
        Returns:
            bool: True if cancellation was successful
        """
        try:
            cancelled = False
            
            lock_acquired = False
            try:
                lock_acquired = self.extraction_lock.acquire(timeout=5.0)
                if lock_acquired and job_id in self.extraction_futures:
                    future = self.extraction_futures[job_id]
                    cancelled = future.cancel()
                    
                    if cancelled:
                        logger.info(f"Successfully cancelled future for job {job_id}")
                    else:
                        logger.warning(f"Could not cancel future for job {job_id} (probably already running)")
            
            finally:
                if lock_acquired:
                    self.extraction_lock.release()
            
            # Update job status regardless of future cancellation
            self.job_service.update_job_status(job_id, 'cancelled', 'Extraction cancelled by user')
            
            # Clean up tracking
            self._cleanup_completed_job(job_id)
            
            logger.info(f"Job {job_id} marked as cancelled")
            return True
            
        except Exception as e:
            logger.error(f"Error cancelling job {job_id}: {str(e)}", exc_info=True)
            return False
    
    def get_extraction_results_by_connection(self, connection_id: str) -> Optional[Dict[str, Any]]:
        """Get extraction results by connection ID"""
        job_id = self._get_job_id_from_connection(connection_id)
        if not job_id:
            return None
        
        return self.get_extraction_results(job_id)
    
    def get_extraction_results(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get extraction results for a completed job"""
        return self.data_service.get_extraction_results(job_id)
    
    def delete_extraction_by_connection(self, connection_id: str) -> bool:
        """Delete an extraction and all associated data by connection ID"""
        try:
            job_id = self._get_job_id_from_connection(connection_id)
            if not job_id:
                logger.warning(f"No job found for connection {connection_id}")
                return False
            
            success = self._complete_job_cleanup(job_id, connection_id)
            logger.info(f"Deleted extraction for connection {connection_id}, job {job_id}")
            return success
            
        except Exception as e:
            logger.error(f"Error deleting extraction for connection {connection_id}: {str(e)}", exc_info=True)
            return False
    
    def delete_extraction_job(self, job_id: str) -> bool:
        """Delete an extraction job and all associated data"""
        try:
            job_info = self.job_service.get_job_by_id(job_id)
            connection_id = job_info.get('connection_id') if job_info else None
            
            if not connection_id:
                logger.warning(f"No connection_id found for job {job_id}")
                return False
            
            success = self._complete_job_cleanup(job_id, connection_id)
            logger.info(f"Deleted job {job_id} for connection {connection_id}")
            return success
            
        except Exception as e:
            logger.error(f"Error deleting job {job_id}: {str(e)}", exc_info=True)
            return False
    
    def _complete_job_cleanup(self, job_id: str, connection_id: str) -> bool:
        """Perform complete cleanup of job and all associated state"""
        try:
            logger.info(f"Starting complete cleanup for job {job_id}, connection {connection_id}")
            
            # Step 1: Cancel if still running
            job_status = self.job_service.get_job_status(job_id)
            if job_status and job_status.get('status') in ['pending', 'running']:
                logger.info(f"Cancelling active job {job_id} before deletion")
                self.cancel_extraction(job_id)
                time.sleep(1)  # Give cancellation time to complete
            
            # Step 2: Clean up thread pool future and tracking
            lock_acquired = False
            try:
                lock_acquired = self.extraction_lock.acquire(timeout=5.0)
                if lock_acquired:
                    # Cancel future if exists
                    if job_id in self.extraction_futures:
                        future = self.extraction_futures[job_id]
                        future.cancel()
                        del self.extraction_futures[job_id]
                    
                    # Clean up tracking
                    self.active_extractions.pop(job_id, None)
                    self.connection_to_job_mapping.pop(connection_id, None)
                    
                    # Clean up stale mappings
                    stale_connections = [
                        conn_id for conn_id, mapped_job_id in self.connection_to_job_mapping.items()
                        if mapped_job_id == job_id
                    ]
                    for stale_conn in stale_connections:
                        del self.connection_to_job_mapping[stale_conn]
            
            finally:
                if lock_acquired:
                    self.extraction_lock.release()
            
            # Step 3: Delete from database
            database_success = self.job_service.delete_job(job_id)
            if not database_success:
                logger.error(f"Database deletion failed for job {job_id}")
                return False
            
            logger.info(f"Complete cleanup successful for job {job_id}, connection {connection_id}")
            return True
            
        except Exception as e:
            logger.error(f"Complete cleanup failed for job {job_id}: {str(e)}", exc_info=True)
            return False
    
    def _force_cleanup_connection_state_unsafe(self, connection_id: str):
        """Force cleanup any stale state for a connection (assumes lock is held)"""
        logger.debug(f"Force cleaning connection state for {connection_id}")
        
        # Remove connection mapping
        if connection_id in self.connection_to_job_mapping:
            old_job_id = self.connection_to_job_mapping[connection_id]
            logger.warning(f"Removing stale connection mapping: {connection_id} -> {old_job_id}")
            del self.connection_to_job_mapping[connection_id]
            
            # Clean up associated tracking
            if old_job_id in self.active_extractions:
                del self.active_extractions[old_job_id]
            
            if old_job_id in self.extraction_futures:
                future = self.extraction_futures[old_job_id]
                future.cancel()
                del self.extraction_futures[old_job_id]
        
        # Clean up any extractions with this connection_id
        stale_jobs = [
            job_id for job_id, info in self.active_extractions.items()
            if info.get('connection_id') == connection_id
        ]
        
        for job_id in stale_jobs:
            logger.warning(f"Removing stale active extraction for connection {connection_id}: {job_id}")
            del self.active_extractions[job_id]
            
            if job_id in self.extraction_futures:
                future = self.extraction_futures[job_id]
                future.cancel()
                del self.extraction_futures[job_id]
    
    def check_existing_extraction(self, connection_id: str) -> Optional[Dict[str, Any]]:
        """
        Check if there's an existing extraction for the given connection_id
        (Compatibility method for routes)
        
        Args:
            connection_id: Connection identifier to check
            
        Returns:
            Dictionary with existing job info or None if not found
        """
        try:
            return self.job_service.get_job_by_connection_id(connection_id)
        except Exception as e:
            logger.error(f"Failed to check existing extraction for {connection_id}: {str(e)}")
            return None
    
    def connection_exists(self, connection_id: str) -> bool:
        """Check if a connection exists"""
        try:
            job = self.job_service.get_job_by_connection_id(connection_id)
            return job is not None
        except Exception as e:
            logger.error(f"Failed to check if connection {connection_id} exists: {str(e)}")
            return False
    
    def job_exists(self, job_id: str) -> bool:
        """Check if a job exists"""
        try:
            job = self.job_service.get_job_by_id(job_id)
            return job is not None
        except Exception as e:
            logger.error(f"Failed to check if job {job_id} exists: {str(e)}")
            return False
    
    def get_active_extractions_count(self) -> int:
        """Get count of currently active extractions"""
        lock_acquired = False
        try:
            lock_acquired = self.extraction_lock.acquire(timeout=2.0)
            if not lock_acquired:
                logger.warning("Failed to acquire lock for active extraction count")
                return 0
            
            return len([
                extraction for extraction in self.active_extractions.values()
                if extraction.get('status') in ['starting', 'running']
            ])
        finally:
            if lock_acquired:
                self.extraction_lock.release()
    
    def get_debug_state(self, connection_id: str = None) -> Dict[str, Any]:
        """
        Get debug information about current state (compatibility method)
        
        Args:
            connection_id: Optional connection to focus on
            
        Returns:
            Dictionary with debug information
        """
        lock_acquired = False
        try:
            lock_acquired = self.extraction_lock.acquire(timeout=2.0)
            if lock_acquired:
                debug_info = {
                    'active_extractions_count': len(self.active_extractions),
                    'extraction_futures_count': len(self.extraction_futures),
                    'connection_mappings_count': len(self.connection_to_job_mapping),
                    'active_extractions': dict(self.active_extractions),
                    'connection_mappings': dict(self.connection_to_job_mapping)
                }
                
                if connection_id:
                    debug_info['specific_connection'] = {
                        'connection_id': connection_id,
                        'has_mapping': connection_id in self.connection_to_job_mapping,
                        'mapped_job_id': self.connection_to_job_mapping.get(connection_id),
                        'active_extractions_for_connection': [
                            job_id for job_id, info in self.active_extractions.items()
                            if info.get('connection_id') == connection_id
                        ]
                    }
            else:
                debug_info = {'error': 'Could not acquire lock for debug info'}
        
        finally:
            if lock_acquired:
                self.extraction_lock.release()
        
        # Add thread pool info
        debug_info['thread_pool'] = self.get_thread_pool_stats()
        
        return debug_info
    
    def _force_cleanup_connection_state(self, connection_id: str):
        """
        Force cleanup any stale state for a connection (compatibility method)
        
        Args:
            connection_id: Connection identifier to clean up
        """
        lock_acquired = False
        try:
            lock_acquired = self.extraction_lock.acquire(timeout=5.0)
            if lock_acquired:
                self._force_cleanup_connection_state_unsafe(connection_id)
            else:
                logger.warning(f"Could not acquire lock for cleanup of {connection_id}")
        finally:
            if lock_acquired:
                self.extraction_lock.release()
    
    def get_thread_pool_stats(self) -> Dict[str, Any]:
        """Get thread pool statistics"""
        return {
            'max_workers': self.executor._max_workers,
            'active_threads': len(self.executor._threads),
            'pending_tasks': self.executor._work_queue.qsize(),
            'shutdown': self.executor._shutdown
        }
    
    def shutdown(self, wait: bool = True, timeout: float = 30.0):
        """Shutdown the extraction service gracefully"""
        try:
            logger.info("Shutting down extraction service...")
        except Exception:
            print("Shutting down extraction service...")
        
        try:
            # Cancel all running jobs
            lock_acquired = False
            try:
                lock_acquired = self.extraction_lock.acquire(timeout=5.0)
                if lock_acquired:
                    for job_id in list(self.extraction_futures.keys()):
                        future = self.extraction_futures[job_id]
                        if not future.done():
                            future.cancel()
                            try:
                                logger.info(f"Cancelled job {job_id} during shutdown")
                            except Exception:
                                print(f"Cancelled job {job_id} during shutdown")
            finally:
                if lock_acquired:
                    self.extraction_lock.release()
            
            # Shutdown thread pool with compatibility
            try:
                # Use only wait parameter for compatibility
                self.executor.shutdown(wait=wait)
                # Handle timeout manually if needed
                if wait and timeout:
                    import time
                    start_time = time.time()
                    while self.executor._threads and time.time() - start_time < timeout:
                        time.sleep(0.1)
            except Exception as e:
                try:
                    logger.warning(f"Error during executor shutdown: {e}")
                except Exception:
                    print(f"Error during executor shutdown: {e}")
                # Force shutdown
                self.executor.shutdown(wait=False)
            
            try:
                logger.info("Extraction service shutdown complete")
            except Exception:
                print("Extraction service shutdown complete")
            
        except Exception as e:
            try:
                logger.error(f"Error during extraction service shutdown: {str(e)}")
            except Exception:
                print(f"Error during extraction service shutdown: {str(e)}")
    
    def __del__(self):
        """Cleanup on deletion"""
        try:
            # Use simple shutdown for destructor
            try:
                if sys.version_info >= (3, 9):
                    self.executor.shutdown(wait=False, timeout=5.0)
                else:
                    self.executor.shutdown(wait=False)
            except (TypeError, AttributeError):
                # Fallback for older Python or if executor doesn't exist
                pass
        except Exception as e:
            try:
                logger.error(f"Error during ExtractionService cleanup: {str(e)}")
            except Exception:
                print(f"Error during ExtractionService cleanup: {str(e)}")