from datetime import datetime
from sqlalchemy import Column, String, ForeignKey, Index, DateTime, Float, Boolean, Integer, Text, BigInteger, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from models.base import BaseModel

class HubSpotDealStageHistory(BaseModel):
    """
    Stores the timeline/history of deal stage changes
    Tracks how deals move through pipeline stages over time
    
    This table captures the complete journey of a deal through different stages,
    enabling sales velocity analysis, bottleneck identification, and cycle time measurement.
    """
    __tablename__ = 'hubspot_deal_stage_history'
    
    # Foreign key relationships
    job_id = Column(String, ForeignKey('extraction_jobs.id', ondelete='CASCADE'), nullable=False, index=True)
    connection_id = Column(String(255), nullable=False, index=True)
    deal_id = Column(String, ForeignKey('hubspot_deals.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # HubSpot specific identifiers
    hubspot_deal_id = Column(String(50), nullable=False, index=True)
    hubspot_stage_id = Column(String(100), nullable=False, index=True)
    
    # Stage information
    stage_label = Column(String(255), nullable=True, index=True)
    pipeline_id = Column(String(50), nullable=True, index=True)
    pipeline_label = Column(String(255), nullable=True)
    
    # Timeline information
    change_timestamp = Column(BigInteger, nullable=True)  # HubSpot timestamp in milliseconds
    change_date = Column(DateTime, nullable=True, index=True)  # Converted datetime for easier querying
    duration_days = Column(Float, nullable=True)  # Days spent in this stage
    duration_hours = Column(Float, nullable=True)  # Hours spent in this stage
    is_current_stage = Column(Boolean, default=False, index=True)
    
    # Change metadata
    change_source = Column(String(100), nullable=True)  # How the change was made (API, UI, automation, etc.)
    change_source_id = Column(String(100), nullable=True)  # ID of user/system that made change
    change_user_id = Column(String(50), nullable=True)  # HubSpot user ID who made the change
    change_user_email = Column(String(255), nullable=True)  # Email of user who made the change
    
    # Sequence and ordering
    stage_order = Column(Integer, nullable=True, index=True)  # Order in the sequence of changes (0 = first stage)
    stage_sequence_number = Column(Integer, nullable=True)  # Sequential number within pipeline stages
    
    # Stage properties and metadata
    stage_probability = Column(Float, nullable=True)  # Probability of closing (0.0 to 1.0)
    is_closed_stage = Column(Boolean, default=False, index=True)  # Whether this is a final stage (won/lost)
    stage_type = Column(String(50), nullable=True)  # open, closed_won, closed_lost
    
    # Additional context
    deal_amount_at_time = Column(String(50), nullable=True)  # Deal amount when stage changed
    previous_stage_id = Column(String(100), nullable=True)  # Previous stage ID for transition tracking
    next_stage_id = Column(String(100), nullable=True)  # Next stage ID (if known)
    
    # Raw data from HubSpot for complete context
    raw_stage_data = Column(JSONB, nullable=True)  # Complete stage change data from HubSpot
    raw_properties = Column(JSONB, nullable=True)  # Any additional properties at time of change
    
    # Relationship back to deal
    deal = relationship('HubSpotDeal', back_populates='stage_history')
    
    # Constraints and indexes for performance
    __table_args__ = (
        # Unique constraint to prevent duplicate stage history entries
        UniqueConstraint('connection_id', 'hubspot_deal_id', 'hubspot_stage_id', 'change_timestamp', 
                        name='uq_stage_history_deal_stage_time'),
        
        # Performance indexes
        Index('idx_stage_history_deal_timeline', 'hubspot_deal_id', 'change_date'),
        Index('idx_stage_history_connection_stage', 'connection_id', 'hubspot_stage_id'),
        Index('idx_stage_history_current_stages', 'is_current_stage', 'change_date'),
        Index('idx_stage_history_deal_sequence', 'hubspot_deal_id', 'stage_order'),
        Index('idx_stage_history_stage_performance', 'hubspot_stage_id', 'duration_days'),
        Index('idx_stage_history_pipeline_analysis', 'pipeline_id', 'hubspot_stage_id', 'duration_days'),
        Index('idx_stage_history_closed_stages', 'is_closed_stage', 'stage_type', 'change_date'),
        Index('idx_stage_history_user_activity', 'change_user_id', 'change_date'),
    )
    
    def get_duration_formatted(self) -> str:
        """Get human-readable duration"""
        if not self.duration_days:
            return "Unknown"
        
        days = int(self.duration_days)
        if days < 1:
            if self.duration_hours and self.duration_hours >= 1:
                hours = int(self.duration_hours)
                return f"{hours} hour{'s' if hours != 1 else ''}"
            else:
                return "< 1 hour"
        elif days == 1:
            return "1 day"
        elif days < 7:
            return f"{days} days"
        elif days < 30:
            weeks = days // 7
            remaining_days = days % 7
            if remaining_days == 0:
                return f"{weeks} week{'s' if weeks != 1 else ''}"
            else:
                return f"{weeks}w {remaining_days}d"
        else:
            months = days // 30
            remaining_days = days % 30
            if remaining_days == 0:
                return f"{months} month{'s' if months != 1 else ''}"
            else:
                return f"{months}m {remaining_days}d"
    
    def is_forward_progression(self) -> bool:
        """Check if this represents forward movement in the sales process"""
        # This would need pipeline stage order data to determine
        # For now, assume any non-closed-lost movement is forward
        return self.stage_type != 'closed_lost'
    
    def is_regression(self) -> bool:
        """Check if this represents backward movement in the sales process"""
        # Implementation would depend on stage order logic
        return False  # Placeholder
    
    def get_velocity_score(self) -> float:
        """Calculate velocity score (lower is better - faster progression)"""
        if not self.duration_days or self.duration_days <= 0:
            return 0.0
        
        # Simple velocity score: probability gain per day
        if self.stage_probability:
            return self.stage_probability / self.duration_days
        
        return 0.0
    
    def to_dict(self):
        """Enhanced dictionary representation"""
        result = super().to_dict()
        result.update({
            'duration_formatted': self.get_duration_formatted(),
            'is_forward_progression': self.is_forward_progression(),
            'is_regression': self.is_regression(),
            'velocity_score': self.get_velocity_score()
        })
        return result
    
    def __repr__(self):
        return f"<HubSpotDealStageHistory(deal_id={self.hubspot_deal_id}, stage={self.stage_label}, date={self.change_date})>"


# Additional utility functions for stage history analysis

def calculate_average_stage_duration(stage_id: str, connection_id: str = None):
    """
    Calculate average duration for a specific stage across all deals
    
    Args:
        stage_id: Stage ID to analyze
        connection_id: Optional connection filter
        
    Returns:
        Average duration in days
    """
    from models.database import get_db_session
    from sqlalchemy import func
    
    try:
        with get_db_session() as session:
            query = session.query(func.avg(HubSpotDealStageHistory.duration_days))\
                          .filter(HubSpotDealStageHistory.hubspot_stage_id == stage_id)\
                          .filter(HubSpotDealStageHistory.duration_days.isnot(None))\
                          .filter(HubSpotDealStageHistory.duration_days > 0)
            
            if connection_id:
                query = query.filter(HubSpotDealStageHistory.connection_id == connection_id)
            
            result = query.scalar()
            return float(result) if result else 0.0
            
    except Exception as e:
        return 0.0

def get_stage_conversion_rates(pipeline_id: str, connection_id: str = None):
    """
    Calculate conversion rates between stages in a pipeline
    
    Args:
        pipeline_id: Pipeline ID to analyze
        connection_id: Optional connection filter
        
    Returns:
        Dictionary with stage conversion data
    """
    from models.database import get_db_session
    from sqlalchemy import func, distinct
    
    try:
        with get_db_session() as session:
            # Get all stages and their entry counts
            query = session.query(
                HubSpotDealStageHistory.hubspot_stage_id,
                HubSpotDealStageHistory.stage_label,
                func.count(distinct(HubSpotDealStageHistory.hubspot_deal_id)).label('deals_entered')
            ).filter(HubSpotDealStageHistory.pipeline_id == pipeline_id)
            
            if connection_id:
                query = query.filter(HubSpotDealStageHistory.connection_id == connection_id)
            
            results = query.group_by(
                HubSpotDealStageHistory.hubspot_stage_id,
                HubSpotDealStageHistory.stage_label
            ).all()
            
            return [
                {
                    'stage_id': result.hubspot_stage_id,
                    'stage_label': result.stage_label,
                    'deals_entered': result.deals_entered
                }
                for result in results
            ]
            
    except Exception as e:
        return []

def identify_bottleneck_stages(connection_id: str = None, min_duration_days: int = 30):
    """
    Identify stages where deals get stuck for too long
    
    Args:
        connection_id: Optional connection filter
        min_duration_days: Minimum days to consider a bottleneck
        
    Returns:
        List of bottleneck stages with statistics
    """
    from models.database import get_db_session
    from sqlalchemy import func
    
    try:
        with get_db_session() as session:
            query = session.query(
                HubSpotDealStageHistory.hubspot_stage_id,
                HubSpotDealStageHistory.stage_label,
                func.avg(HubSpotDealStageHistory.duration_days).label('avg_duration'),
                func.count(HubSpotDealStageHistory.id).label('deals_count'),
                func.max(HubSpotDealStageHistory.duration_days).label('max_duration')
            ).filter(HubSpotDealStageHistory.duration_days >= min_duration_days)
            
            if connection_id:
                query = query.filter(HubSpotDealStageHistory.connection_id == connection_id)
            
            results = query.group_by(
                HubSpotDealStageHistory.hubspot_stage_id,
                HubSpotDealStageHistory.stage_label
            ).order_by(func.avg(HubSpotDealStageHistory.duration_days).desc()).all()
            
            return [
                {
                    'stage_id': result.hubspot_stage_id,
                    'stage_label': result.stage_label,
                    'avg_duration_days': float(result.avg_duration),
                    'deals_affected': result.deals_count,
                    'max_duration_days': float(result.max_duration)
                }
                for result in results
            ]
            
    except Exception as e:
        return []