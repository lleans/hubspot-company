from datetime import datetime
from typing import List, Dict, Any, Optional
from decimal import Decimal, InvalidOperation
from models.database import get_db_session
from models.extraction_job import ExtractionJob
from models.hubspot_company import HubSpotCompany
from models.hubspot_deal import HubSpotDeal
from models.hubspot_pipeline import HubSpotDealPipeline
from models.hubspot_deal_stage_history import HubSpotDealStageHistory
from utils.exceptions import DatabaseError
import logging

logger = logging.getLogger(__name__)

class DataService:
    """
    Service for processing and storing HubSpot data
    All database operations are properly wrapped in session contexts
    """
    
    def save_companies(self, job_id: str, connection_id: str, companies_data: List[Dict]) -> int:
        """
        Save company data to database
        
        Args:
            job_id: Extraction job ID
            connection_id: Connection identifier
            companies_data: List of company data from HubSpot API
            
        Returns:
            int: Number of companies saved
        """
        try:
            saved_count = 0
            
            with get_db_session() as session:
                for company_data in companies_data:
                    try:
                        company = self._create_company_record(job_id, connection_id, company_data)
                        session.add(company)
                        saved_count += 1
                        
                        if saved_count % 100 == 0:
                            session.flush()  # Periodic flush for large datasets
                            logger.debug(f"Processed {saved_count} companies")
                            
                    except Exception as e:
                        logger.warning(f"Failed to process company {company_data.get('id', 'unknown')}: {str(e)}")
                        continue
                
                logger.info(f"Saved {saved_count} companies for job {job_id}")
                return saved_count
                
        except Exception as e:
            logger.error(f"Failed to save companies for job {job_id}: {str(e)}")
            raise DatabaseError(f"Failed to save companies: {str(e)}")
    
    def save_deals(self, job_id: str, connection_id: str, deals_data: List[Dict]) -> int:
        """
        Save deal data to database
        
        Args:
            job_id: Extraction job ID
            connection_id: Connection identifier
            deals_data: List of deal data from HubSpot API
            
        Returns:
            int: Number of deals saved
        """
        try:
            saved_count = 0
            
            with get_db_session() as session:
                for deal_data in deals_data:
                    try:
                        deal = self._create_deal_record(job_id, connection_id, deal_data)
                        session.add(deal)
                        saved_count += 1
                        
                        if saved_count % 100 == 0:
                            session.flush()  # Periodic flush for large datasets
                            logger.debug(f"Processed {saved_count} deals")
                            
                    except Exception as e:
                        logger.warning(f"Failed to process deal {deal_data.get('id', 'unknown')}: {str(e)}")
                        continue
                
                logger.info(f"Saved {saved_count} deals for job {job_id}")
                return saved_count
                
        except Exception as e:
            logger.error(f"Failed to save deals for job {job_id}: {str(e)}")
            raise DatabaseError(f"Failed to save deals: {str(e)}")
    
    def save_pipelines(self, job_id: str, connection_id: str, pipelines_data: List[Dict]) -> int:
        """
        Save pipeline data to database
        
        Args:
            job_id: Extraction job ID
            connection_id: Connection identifier
            pipelines_data: List of pipeline data from HubSpot API
            
        Returns:
            int: Number of pipelines saved
        """
        try:
            saved_count = 0
            
            with get_db_session() as session:
                for pipeline_data in pipelines_data:
                    try:
                        pipeline = self._create_pipeline_record(job_id, connection_id, pipeline_data)
                        session.add(pipeline)
                        saved_count += 1
                        
                    except Exception as e:
                        logger.warning(f"Failed to process pipeline {pipeline_data.get('id', 'unknown')}: {str(e)}")
                        continue
                
                logger.info(f"Saved {saved_count} pipelines for job {job_id}")
                return saved_count
                
        except Exception as e:
            logger.error(f"Failed to save pipelines for job {job_id}: {str(e)}")
            raise DatabaseError(f"Failed to save pipelines: {str(e)}")
    
    def save_deal_stage_history(self, job_id: str, connection_id: str, stage_histories: Dict[str, List[Dict]]) -> int:
        """
        Save deal stage history data to database
        
        Args:
            job_id: Extraction job ID
            connection_id: Connection identifier
            stage_histories: Dictionary mapping deal_id to list of stage history records
            
        Returns:
            int: Number of stage history records saved
        """
        try:
            saved_count = 0
            
            with get_db_session() as session:
                for deal_id, stage_history_list in stage_histories.items():
                    
                    if not stage_history_list:
                        logger.debug(f"No stage history found for deal {deal_id}")
                        continue
                    
                    for stage_history_data in stage_history_list:
                        try:
                            stage_history_record = self._create_deal_stage_history_record(
                                job_id, connection_id, deal_id, stage_history_data
                            )
                            session.add(stage_history_record)
                            saved_count += 1
                            
                            if saved_count % 50 == 0:
                                session.flush()  # Periodic flush for large datasets
                                logger.debug(f"Processed {saved_count} stage history records")
                                
                        except Exception as e:
                            logger.warning(f"Failed to process stage history for deal {deal_id}, stage {stage_history_data.get('stage_id', 'unknown')}: {str(e)}")
                            continue
                
                logger.info(f"Saved {saved_count} stage history records for job {job_id}")
                return saved_count
                
        except Exception as e:
            logger.error(f"Failed to save deal stage history for job {job_id}: {str(e)}")
            raise DatabaseError(f"Failed to save deal stage history: {str(e)}")
    
    def get_extraction_results(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get complete extraction results for a job including deal stage history
        
        Args:
            job_id: Job identifier
            
        Returns:
            Dictionary with extraction results or None if not found
        """
        try:
            with get_db_session() as session:
                job = session.query(ExtractionJob).filter_by(id=job_id).first()
                
                if not job:
                    return None
                
                # Get all related data and serialize properly
                companies = [self._serialize_record(company.to_dict()) for company in job.companies]
                deals = [self._serialize_record(deal.to_dict()) for deal in job.deals]
                pipelines = [self._serialize_record(pipeline.to_dict()) for pipeline in job.pipelines]
                
                # Get deal stage history
                stage_history = []
                stage_history_count = 0
                
                try:
                    # Get all stage history records for this job
                    stage_history_records = session.query(HubSpotDealStageHistory)\
                        .filter_by(job_id=job_id)\
                        .order_by(HubSpotDealStageHistory.hubspot_deal_id, HubSpotDealStageHistory.stage_order)\
                        .all()
                    
                    stage_history = [self._serialize_record(record.to_dict()) for record in stage_history_records]
                    stage_history_count = len(stage_history)
                    
                    logger.debug(f"Retrieved {stage_history_count} stage history records for job {job_id}")
                    
                except Exception as stage_error:
                    logger.warning(f"Failed to get stage history for job {job_id}: {str(stage_error)}")
                    # Continue without stage history if there's an error
                
                # Serialize job data
                job_dict = self._serialize_record(job.to_dict())
                
                return {
                    'job_id': job_id,
                    'connection_id': job.connection_id,
                    'status': job.status,
                    'extraction_metadata': {
                        'start_time': job_dict.get('start_time'),
                        'end_time': job_dict.get('end_time'),
                        'created_at': job_dict.get('created_at'),
                        'updated_at': job_dict.get('updated_at'),
                        'duration_seconds': job.extraction_duration_seconds,
                        'total_records': job.total_records_extracted,
                        'companies_count': len(companies),
                        'deals_count': len(deals),
                        'pipelines_count': len(pipelines),
                        'stage_history_count': stage_history_count,
                        'progress_percentage': job.progress_percentage,
                        'message': job.message
                    },
                    'companies': companies,
                    'deals': deals,
                    'pipelines': pipelines,
                    'stage_history': stage_history
                }
                
        except Exception as e:
            logger.error(f"Failed to get extraction results for job {job_id}: {str(e)}")
            raise DatabaseError(f"Failed to get extraction results: {str(e)}")
    
    def get_extraction_results_with_analytics(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get extraction results with additional analytics and insights
        
        Args:
            job_id: Job identifier
            
        Returns:
            Dictionary with extraction results plus analytics
        """
        try:
            # Get base extraction results
            results = self.get_extraction_results(job_id)
            
            if not results:
                return None
            
            connection_id = results['connection_id']
            
            # Add analytics if we have stage history data
            analytics = {}
            
            if results.get('stage_history'):
                try:
                    with get_db_session() as session:
                        job = session.query(ExtractionJob).filter_by(id=job_id).first()
                        
                        if job:
                            # Get pipeline analytics for each pipeline in this job
                            pipeline_analytics = []
                            
                            for pipeline in results.get('pipelines', []):
                                pipeline_id = pipeline.get('hubspot_pipeline_id')
                                if pipeline_id:
                                    pipeline_stats = self.get_stage_analytics_for_pipeline(pipeline_id, connection_id)
                                    if pipeline_stats and 'error' not in pipeline_stats:
                                        pipeline_analytics.append(pipeline_stats)
                            
                            # Get bottleneck stages
                            bottlenecks = self.find_bottleneck_stages(connection_id, min_duration_days=14)
                            
                            # Calculate overall velocity metrics
                            from sqlalchemy import func, distinct
                            
                            # Average deal cycle time
                            cycle_time_query = session.query(
                                HubSpotDealStageHistory.hubspot_deal_id,
                                func.sum(HubSpotDealStageHistory.duration_days).label('total_cycle_days')
                            ).filter(HubSpotDealStageHistory.job_id == job_id)\
                             .filter(HubSpotDealStageHistory.duration_days.isnot(None))\
                             .filter(HubSpotDealStageHistory.is_current_stage == False)\
                             .group_by(HubSpotDealStageHistory.hubspot_deal_id)
                            
                            cycle_times = cycle_time_query.all()
                            
                            avg_cycle_time = 0
                            if cycle_times:
                                total_cycle_time = sum(ct.total_cycle_days for ct in cycle_times if ct.total_cycle_days)
                                avg_cycle_time = total_cycle_time / len(cycle_times) if cycle_times else 0
                            
                            # Deal velocity distribution
                            velocity_ranges = {
                                'fast': 0,      # < 30 days
                                'medium': 0,    # 30-60 days  
                                'slow': 0,      # 60-120 days
                                'stuck': 0      # > 120 days
                            }
                            
                            for cycle_time in cycle_times:
                                if cycle_time.total_cycle_days:
                                    days = cycle_time.total_cycle_days
                                    if days < 30:
                                        velocity_ranges['fast'] += 1
                                    elif days < 60:
                                        velocity_ranges['medium'] += 1
                                    elif days < 120:
                                        velocity_ranges['slow'] += 1
                                    else:
                                        velocity_ranges['stuck'] += 1
                            
                            analytics = {
                                'velocity_metrics': {
                                    'avg_cycle_time_days': round(avg_cycle_time, 1),
                                    'total_deals_analyzed': len(cycle_times),
                                    'velocity_distribution': velocity_ranges
                                },
                                'pipeline_analytics': pipeline_analytics,
                                'bottleneck_stages': bottlenecks[:5],  # Top 5 bottlenecks
                                'insights': self._generate_velocity_insights(avg_cycle_time, bottlenecks, velocity_ranges)
                            }
                            
                except Exception as analytics_error:
                    logger.warning(f"Failed to generate analytics for job {job_id}: {str(analytics_error)}")
                    analytics = {'error': 'Analytics generation failed'}
            
            # Add analytics to results
            results['analytics'] = analytics
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to get extraction results with analytics for job {job_id}: {str(e)}")
            raise DatabaseError(f"Failed to get extraction results with analytics: {str(e)}")
    
    def _generate_velocity_insights(self, avg_cycle_time: float, bottlenecks: List[Dict], velocity_ranges: Dict) -> List[str]:
        """Generate human-readable insights from velocity data"""
        insights = []
        
        # Cycle time insights
        if avg_cycle_time > 90:
            insights.append(f"Average deal cycle time of {avg_cycle_time:.1f} days is quite long. Consider optimizing your sales process.")
        elif avg_cycle_time > 60:
            insights.append(f"Average deal cycle time of {avg_cycle_time:.1f} days has room for improvement.")
        elif avg_cycle_time > 0:
            insights.append(f"Average deal cycle time of {avg_cycle_time:.1f} days is performing well.")
        
        # Velocity distribution insights
        total_deals = sum(velocity_ranges.values())
        if total_deals > 0:
            stuck_percentage = (velocity_ranges['stuck'] / total_deals) * 100
            fast_percentage = (velocity_ranges['fast'] / total_deals) * 100
            
            if stuck_percentage > 25:
                insights.append(f"{stuck_percentage:.1f}% of deals are taking over 120 days - investigate long-running deals.")
            elif fast_percentage > 50:
                insights.append(f"{fast_percentage:.1f}% of deals close in under 30 days - excellent velocity!")
        
        # Bottleneck insights
        if bottlenecks:
            worst_bottleneck = bottlenecks[0]
            insights.append(f"'{worst_bottleneck['stage_label']}' is your biggest bottleneck with {worst_bottleneck['avg_duration_days']:.1f} day average.")
        
        # Default insight
        if not insights:
            insights.append("Analyze your stage history data to identify optimization opportunities.")
        
        return insights
    
    def _serialize_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Serialize a record for JSON response, converting datetime objects to ISO strings
        
        Args:
            record: Dictionary that may contain datetime objects
            
        Returns:
            Dictionary with datetime objects converted to strings
        """
        if not isinstance(record, dict):
            return record
        
        serialized = {}
        for key, value in record.items():
            if isinstance(value, datetime):
                # Convert datetime to ISO format string
                serialized[key] = value.isoformat() if value else None
            elif isinstance(value, Decimal):
                # Convert Decimal to float for JSON serialization
                serialized[key] = float(value) if value else None
            elif isinstance(value, dict):
                # Recursively serialize nested dictionaries
                serialized[key] = self._serialize_record(value)
            elif isinstance(value, list):
                # Serialize lists that might contain dictionaries
                serialized[key] = [
                    self._serialize_record(item) if isinstance(item, dict) else 
                    item.isoformat() if isinstance(item, datetime) else 
                    float(item) if isinstance(item, Decimal) else item
                    for item in value
                ]
            else:
                serialized[key] = value
        
        return serialized
    
    def _create_company_record(self, job_id: str, connection_id: str, company_data: Dict) -> HubSpotCompany:
        """Create a HubSpotCompany record from API data"""
        properties = company_data.get('properties', {})
        
        # Extract and clean key fields
        name = self._clean_string(properties.get('name'))
        domain = self._clean_string(properties.get('domain'))
        industry = self._clean_string(properties.get('industry'))
        description = self._clean_string(properties.get('description'))
        
        # Location fields
        city = self._clean_string(properties.get('city'))
        state = self._clean_string(properties.get('state'))
        country = self._clean_string(properties.get('country'))
        timezone = self._clean_string(properties.get('timezone'))
        
        # Business metrics
        annual_revenue = self._clean_string(properties.get('annualrevenue'))
        number_of_employees = self._clean_string(properties.get('numberofemployees'))
        
        return HubSpotCompany(
            job_id=job_id,
            connection_id=connection_id,
            hubspot_company_id=str(company_data.get('id')),
            name=name,
            domain=domain,
            industry=industry,
            description=description,
            city=city,
            state=state,
            country=country,
            timezone=timezone,
            annual_revenue=annual_revenue,
            number_of_employees=number_of_employees,
            hubspot_created_date=company_data.get('created_date'),
            hubspot_updated_date=company_data.get('updated_date'),
            properties=properties
        )
    
    def _create_deal_record(self, job_id: str, connection_id: str, deal_data: Dict) -> HubSpotDeal:
        """Create a HubSpotDeal record from API data"""
        properties = deal_data.get('properties', {})
        
        # Extract and clean key fields
        dealname = self._clean_string(properties.get('dealname'))
        amount_raw = self._clean_string(properties.get('amount'))
        amount = self._parse_currency_amount(amount_raw)
        
        # Pipeline and stage information
        pipeline_id = self._clean_string(properties.get('pipeline'))
        dealstage_id = self._clean_string(properties.get('dealstage'))
        
        # Extract associated company info if available
        associated_company_id = self._clean_string(properties.get('associatedcompanyid'))
        
        return HubSpotDeal(
            job_id=job_id,
            connection_id=connection_id,
            hubspot_deal_id=str(deal_data.get('id')),
            dealname=dealname,
            amount=amount,
            amount_raw=amount_raw,
            pipeline_id=pipeline_id,
            dealstage_id=dealstage_id,
            associated_company_id=associated_company_id,
            closedate=deal_data.get('close_date'),
            hubspot_created_date=deal_data.get('created_date'),
            hubspot_updated_date=deal_data.get('updated_date'),
            properties=properties
        )
    
    def _create_pipeline_record(self, job_id: str, connection_id: str, pipeline_data: Dict) -> HubSpotDealPipeline:
        """Create a HubSpotDealPipeline record from API data"""
        
        # Extract stage data for easier querying
        stages_data = pipeline_data.get('stages', [])
        
        return HubSpotDealPipeline(
            job_id=job_id,
            connection_id=connection_id,
            hubspot_pipeline_id=str(pipeline_data.get('id')),
            label=self._clean_string(pipeline_data.get('label')),
            display_order=pipeline_data.get('displayOrder'),
            active=pipeline_data.get('active', True),
            created_at_hubspot=pipeline_data.get('created_date'),
            updated_at_hubspot=pipeline_data.get('updated_date'),
            properties=pipeline_data.get('raw_data', pipeline_data),
            stages_data=stages_data
        )
    
    def _create_deal_stage_history_record(self, job_id: str, connection_id: str, deal_id: str, stage_data: Dict) -> HubSpotDealStageHistory:
        """Create a HubSpotDealStageHistory record from stage data"""
        
        # Extract stage information
        stage_id = self._clean_string(stage_data.get('stage_id'))
        entry_timestamp = stage_data.get('entry_timestamp')
        entry_date = stage_data.get('entry_date')
        
        # Duration information
        duration_days = stage_data.get('duration_days')
        duration_hours = stage_data.get('duration_hours')
        stage_order = stage_data.get('stage_order')
        is_current_stage = stage_data.get('is_current_stage', False)
        
        # Parse timestamp if available
        change_timestamp = None
        change_date = None
        
        if entry_timestamp:
            change_timestamp = entry_timestamp
            # Convert from milliseconds to datetime if needed
            if entry_date:
                change_date = entry_date
            else:
                try:
                    from datetime import datetime
                    change_date = datetime.fromtimestamp(entry_timestamp / 1000)
                except (ValueError, OSError, TypeError):
                    logger.warning(f"Could not parse timestamp {entry_timestamp} for deal {deal_id}")
        
        # Extract metadata
        change_source = self._clean_string(stage_data.get('source', 'property_history'))
        change_user_id = self._clean_string(stage_data.get('user_id'))
        
        # Try to extract stage label and pipeline info from raw event data
        stage_label = None
        pipeline_id = None
        pipeline_label = None
        stage_probability = None
        
        raw_event = stage_data.get('raw_event')
        if raw_event and isinstance(raw_event, dict):
            stage_label = self._clean_string(raw_event.get('stage_label'))
            pipeline_id = self._clean_string(raw_event.get('pipeline_id'))
            pipeline_label = self._clean_string(raw_event.get('pipeline_label'))
            stage_probability = raw_event.get('probability')
        
        # Determine if this is a closed stage
        is_closed_stage = False
        stage_type = 'open'
        
        if stage_id:
            stage_id_lower = stage_id.lower()
            if 'closed' in stage_id_lower or 'won' in stage_id_lower:
                is_closed_stage = True
                stage_type = 'closed_won' if 'won' in stage_id_lower else 'closed_lost'
        
        return HubSpotDealStageHistory(
            job_id=job_id,
            connection_id=connection_id,
            deal_id=deal_id,  # This should be the internal deal record ID if you have FK relationship
            hubspot_deal_id=deal_id,  # The actual HubSpot deal ID
            hubspot_stage_id=stage_id,
            stage_label=stage_label,
            pipeline_id=pipeline_id,
            pipeline_label=pipeline_label,
            change_timestamp=change_timestamp,
            change_date=change_date,
            duration_days=duration_days,
            duration_hours=duration_hours,
            is_current_stage=is_current_stage,
            change_source=change_source,
            change_user_id=change_user_id,
            stage_order=stage_order,
            stage_probability=stage_probability,
            is_closed_stage=is_closed_stage,
            stage_type=stage_type,
            raw_stage_data=stage_data,
            raw_properties=raw_event
        )
    
    def _clean_string(self, value: Any) -> Optional[str]:
        """Clean and validate string values"""
        if value is None:
            return None
        
        if isinstance(value, str):
            cleaned = value.strip()
            return cleaned if cleaned else None
        
        return str(value)
    
    def _parse_currency_amount(self, amount_str: str) -> Optional[Decimal]:
        """Parse currency amount string to Decimal"""
        if not amount_str:
            return None
        
        try:
            # Remove common currency symbols and formatting
            cleaned = amount_str.replace('$', '').replace(',', '').replace(' ', '')
            
            # Handle empty or non-numeric strings
            if not cleaned or cleaned == '0':
                return None
            
            return Decimal(cleaned)
            
        except (InvalidOperation, ValueError, TypeError):
            logger.debug(f"Could not parse amount: {amount_str}")
            return None
    
    def get_company_count(self, job_id: str) -> int:
        """Get count of companies for a job"""
        try:
            with get_db_session() as session:
                return session.query(HubSpotCompany).filter_by(job_id=job_id).count()
        except Exception as e:
            logger.error(f"Failed to get company count for job {job_id}: {str(e)}")
            return 0
    
    def get_deal_count(self, job_id: str) -> int:
        """Get count of deals for a job"""
        try:
            with get_db_session() as session:
                return session.query(HubSpotDeal).filter_by(job_id=job_id).count()
        except Exception as e:
            logger.error(f"Failed to get deal count for job {job_id}: {str(e)}")
            return 0
    
    def get_pipeline_count(self, job_id: str) -> int:
        """Get count of pipelines for a job"""
        try:
            with get_db_session() as session:
                return session.query(HubSpotDealPipeline).filter_by(job_id=job_id).count()
        except Exception as e:
            logger.error(f"Failed to get pipeline count for job {job_id}: {str(e)}")
            return 0
    
    def get_deal_stage_history_count(self, job_id: str) -> int:
        """Get count of stage history records for a job"""
        try:
            with get_db_session() as session:
                return session.query(HubSpotDealStageHistory).filter_by(job_id=job_id).count()
        except Exception as e:
            logger.error(f"Failed to get stage history count for job {job_id}: {str(e)}")
            return 0
    
    def get_deal_stage_history_for_deal(self, deal_id: str, connection_id: str = None) -> List[Dict[str, Any]]:
        """
        Get stage history for a specific deal
        
        Args:
            deal_id: HubSpot deal ID
            connection_id: Optional connection filter
            
        Returns:
            List of stage history records ordered by stage_order
        """
        try:
            with get_db_session() as session:
                query = session.query(HubSpotDealStageHistory)\
                    .filter(HubSpotDealStageHistory.hubspot_deal_id == deal_id)\
                    .order_by(HubSpotDealStageHistory.stage_order.asc())
                
                if connection_id:
                    query = query.filter(HubSpotDealStageHistory.connection_id == connection_id)
                
                results = query.all()
                
                return [self._serialize_record(record.to_dict()) for record in results]
                
        except Exception as e:
            logger.error(f"Failed to get stage history for deal {deal_id}: {str(e)}")
            return []
    
    def get_stage_analytics_for_pipeline(self, pipeline_id: str, connection_id: str = None) -> Dict[str, Any]:
        """
        Get analytics for a specific pipeline
        
        Args:
            pipeline_id: HubSpot pipeline ID
            connection_id: Optional connection filter
            
        Returns:
            Dictionary with stage analytics
        """
        try:
            with get_db_session() as session:
                from sqlalchemy import func, distinct
                
                query = session.query(
                    HubSpotDealStageHistory.hubspot_stage_id,
                    HubSpotDealStageHistory.stage_label,
                    func.count(distinct(HubSpotDealStageHistory.hubspot_deal_id)).label('deals_count'),
                    func.avg(HubSpotDealStageHistory.duration_days).label('avg_duration_days'),
                    func.min(HubSpotDealStageHistory.duration_days).label('min_duration_days'),
                    func.max(HubSpotDealStageHistory.duration_days).label('max_duration_days')
                ).filter(HubSpotDealStageHistory.pipeline_id == pipeline_id)\
                 .filter(HubSpotDealStageHistory.duration_days.isnot(None))\
                 .filter(HubSpotDealStageHistory.duration_days > 0)
                
                if connection_id:
                    query = query.filter(HubSpotDealStageHistory.connection_id == connection_id)
                
                results = query.group_by(
                    HubSpotDealStageHistory.hubspot_stage_id,
                    HubSpotDealStageHistory.stage_label
                ).all()
                
                stage_analytics = []
                total_avg_duration = 0
                
                for result in results:
                    avg_duration = float(result.avg_duration_days) if result.avg_duration_days else 0
                    total_avg_duration += avg_duration
                    
                    stage_analytics.append({
                        'stage_id': result.hubspot_stage_id,
                        'stage_label': result.stage_label,
                        'deals_count': result.deals_count,
                        'avg_duration_days': avg_duration,
                        'min_duration_days': float(result.min_duration_days) if result.min_duration_days else 0,
                        'max_duration_days': float(result.max_duration_days) if result.max_duration_days else 0
                    })
                
                return {
                    'pipeline_id': pipeline_id,
                    'total_stages_analyzed': len(stage_analytics),
                    'total_avg_cycle_time_days': total_avg_duration,
                    'stage_breakdown': stage_analytics
                }
                
        except Exception as e:
            logger.error(f"Failed to get stage analytics for pipeline {pipeline_id}: {str(e)}")
            return {'error': str(e)}
    
    def find_bottleneck_stages(self, connection_id: str = None, min_duration_days: int = 30) -> List[Dict[str, Any]]:
        """
        Find stages where deals get stuck for too long
        
        Args:
            connection_id: Optional connection filter
            min_duration_days: Minimum days to consider a bottleneck
            
        Returns:
            List of bottleneck stages with statistics
        """
        try:
            with get_db_session() as session:
                from sqlalchemy import func
                
                query = session.query(
                    HubSpotDealStageHistory.hubspot_stage_id,
                    HubSpotDealStageHistory.stage_label,
                    HubSpotDealStageHistory.pipeline_id,
                    func.avg(HubSpotDealStageHistory.duration_days).label('avg_duration'),
                    func.count(HubSpotDealStageHistory.id).label('deals_count'),
                    func.max(HubSpotDealStageHistory.duration_days).label('max_duration')
                ).filter(HubSpotDealStageHistory.duration_days >= min_duration_days)
                
                if connection_id:
                    query = query.filter(HubSpotDealStageHistory.connection_id == connection_id)
                
                results = query.group_by(
                    HubSpotDealStageHistory.hubspot_stage_id,
                    HubSpotDealStageHistory.stage_label,
                    HubSpotDealStageHistory.pipeline_id
                ).order_by(func.avg(HubSpotDealStageHistory.duration_days).desc()).all()
                
                bottlenecks = []
                for result in results:
                    bottlenecks.append({
                        'stage_id': result.hubspot_stage_id,
                        'stage_label': result.stage_label,
                        'pipeline_id': result.pipeline_id,
                        'avg_duration_days': float(result.avg_duration),
                        'deals_affected': result.deals_count,
                        'max_duration_days': float(result.max_duration),
                        'severity': 'high' if result.avg_duration > 60 else 'medium'
                    })
                
                return bottlenecks
                
        except Exception as e:
            logger.error(f"Failed to find bottleneck stages: {str(e)}")
            return []