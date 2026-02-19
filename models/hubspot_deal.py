from datetime import datetime
from sqlalchemy import Column, String, ForeignKey, Index, UniqueConstraint, DateTime, Text, Numeric
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from models.base import BaseModel

class HubSpotDeal(BaseModel):
    """
    Stores HubSpot deal records with comprehensive pipeline and stage information
    """
    __tablename__ = 'hubspot_deals'
    
    # Foreign key relationships
    job_id = Column(String, ForeignKey('extraction_jobs.id', ondelete='CASCADE'), nullable=False, index=True)
    connection_id = Column(String(255), nullable=False, index=True)
    
    # HubSpot specific fields
    hubspot_deal_id = Column(String(50), nullable=False, index=True)
    
    # Core deal information
    dealname = Column(String(500), nullable=True, index=True)
    amount = Column(Numeric(15, 2), nullable=True)  # Use Numeric for precise monetary values
    amount_raw = Column(String(50), nullable=True)  # Keep original string value
    
    # Pipeline and stage information
    pipeline_id = Column(String(50), nullable=True, index=True)
    pipeline_label = Column(String(255), nullable=True)
    dealstage_id = Column(String(50), nullable=True, index=True)
    dealstage_label = Column(String(255), nullable=True)
    
    # Important dates
    closedate = Column(DateTime, nullable=True, index=True)
    hubspot_created_date = Column(DateTime, nullable=True, index=True)
    hubspot_updated_date = Column(DateTime, nullable=True)
    
    # Deal status and type
    deal_type = Column(String(100), nullable=True)
    deal_priority = Column(String(50), nullable=True)
    
    # Associated company information (denormalized for performance)
    associated_company_id = Column(String(50), nullable=True, index=True)
    company_name = Column(String(500), nullable=True)
    
    # Complete properties as JSON for flexibility
    properties = Column(JSONB, nullable=True)
    
    # Relationship back to job
    job = relationship('ExtractionJob', back_populates='deals')
    
    # NEW: Relationship to stage history
    stage_history = relationship(
        'HubSpotDealStageHistory', 
        back_populates='deal',
        cascade='all, delete-orphan',
        lazy='dynamic',
        order_by='HubSpotDealStageHistory.stage_order'
    )
    
    # Constraints and indexes for performance
    __table_args__ = (
        UniqueConstraint('connection_id', 'hubspot_deal_id', name='uq_deal_connection_hubspot_id'),
        Index('idx_deal_name', 'dealname'),
        Index('idx_deal_amount', 'amount'),
        Index('idx_deal_pipeline_stage', 'pipeline_id', 'dealstage_id'),
        Index('idx_deal_closedate', 'closedate'),
        Index('idx_deal_created_date', 'hubspot_created_date'),
        Index('idx_deal_company', 'associated_company_id'),
    )
    
    def get_display_name(self):
        """Get display name for the deal"""
        return self.dealname or f"Deal {self.hubspot_deal_id}"
    
    def get_formatted_amount(self):
        """Get formatted amount as string"""
        if self.amount:
            return f"${self.amount:,.2f}"
        return self.amount_raw or "N/A"
    
    def is_closed_won(self):
        """Check if deal is closed won (common stage patterns)"""
        if self.dealstage_label:
            closed_won_patterns = ['closed won', 'won', 'completed', 'success']
            return any(pattern in self.dealstage_label.lower() for pattern in closed_won_patterns)
        return False
    
    def is_closed_lost(self):
        """Check if deal is closed lost"""
        if self.dealstage_label:
            closed_lost_patterns = ['closed lost', 'lost', 'cancelled', 'rejected']
            return any(pattern in self.dealstage_label.lower() for pattern in closed_lost_patterns)
        return False
    
    def get_stage_timeline(self):
        """Get chronological stage history"""
        try:
            return [stage.to_dict() for stage in self.stage_history.order_by('stage_order')]
        except Exception:
            # Handle detached instance
            return []
    
    def get_current_stage_duration(self):
        """Get how long deal has been in current stage"""
        try:
            current_stage = self.stage_history.filter_by(is_current_stage=True).first()
            if current_stage:
                return current_stage.get_duration_formatted()
            return "Unknown"
        except Exception:
            # Handle detached instance
            return "Unknown"
    
    def get_total_cycle_time(self):
        """Calculate total time from first stage to current"""
        try:
            stages = list(self.stage_history.order_by('stage_order'))
            if len(stages) < 2:
                return None
            
            first_stage = stages[0]
            current_stage = stages[-1]
            
            if first_stage.change_date and current_stage.change_date:
                delta = current_stage.change_date - first_stage.change_date
                return delta.days
            
            return None
        except Exception:
            # Handle detached instance
            return None
    
    def get_stage_count(self):
        """Get total number of stage changes"""
        try:
            return self.stage_history.count()
        except Exception:
            # Handle detached instance by returning 0
            return 0
    
    def get_average_stage_duration(self):
        """Get average time spent per stage"""
        try:
            stages = list(self.stage_history.filter(
                self.stage_history.duration_days.isnot(None),
                self.stage_history.duration_days > 0
            ))
            
            if not stages:
                return None
            
            total_duration = sum(stage.duration_days for stage in stages)
            return total_duration / len(stages)
        except Exception:
            # Handle detached instance or other errors
            return None
    
    def to_dict(self):
        """Enhanced dictionary representation"""
        result = super().to_dict()
        result.update({
            'display_name': self.get_display_name(),
            'formatted_amount': self.get_formatted_amount(),
            'is_closed_won': self.is_closed_won(),
            'is_closed_lost': self.is_closed_lost(),
            'current_stage_duration': self.get_current_stage_duration(),
            'total_cycle_time_days': self.get_total_cycle_time(),
            'stage_count': self.get_stage_count(),
            'average_stage_duration_days': self.get_average_stage_duration(),
            'stage_timeline': self.get_stage_timeline(),
            # Add compatibility aliases for test consistency
            'deal_name': self.dealname,
            'stage_id': self.dealstage_id,
            'hubspot_company_id': self.associated_company_id
        })
        return result
    
    def __repr__(self):
        return f"<HubSpotDeal(id={self.id}, name={self.dealname}, amount={self.get_formatted_amount()})>"