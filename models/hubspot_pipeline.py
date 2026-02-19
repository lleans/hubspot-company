from datetime import datetime
from sqlalchemy import Column, String, ForeignKey, Index, UniqueConstraint, Integer, Boolean, Text,DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from models.base import BaseModel

class HubSpotDealPipeline(BaseModel):
    """
    Stores HubSpot deal pipeline definitions with complete stage information
    """
    __tablename__ = 'hubspot_deal_pipelines'
    
    # Foreign key relationships
    job_id = Column(String, ForeignKey('extraction_jobs.id', ondelete='CASCADE'), nullable=False, index=True)
    connection_id = Column(String(255), nullable=False, index=True)
    
    # HubSpot specific fields
    hubspot_pipeline_id = Column(String(50), nullable=False, index=True)
    
    # Pipeline information
    label = Column(String(255), nullable=True, index=True)
    display_order = Column(Integer, nullable=True)
    active = Column(Boolean, default=True, nullable=True, index=True)
    
    # Pipeline metadata
    pipeline_type = Column(String(100), nullable=True)  # e.g., 'deals', 'tickets'
    created_at_hubspot = Column(DateTime, nullable=True)
    updated_at_hubspot = Column(DateTime, nullable=True)
    
    # Complete pipeline object including stages as JSON
    properties = Column(JSONB, nullable=True)
    stages_data = Column(JSONB, nullable=True)  # Extracted stages for easier querying
    
    # Relationship back to job
    job = relationship('ExtractionJob', back_populates='pipelines')
    
    # Constraints and indexes
    __table_args__ = (
        UniqueConstraint('connection_id', 'hubspot_pipeline_id', name='uq_pipeline_connection_hubspot_id'),
        Index('idx_pipeline_label', 'label'),
        Index('idx_pipeline_active', 'active'),
        Index('idx_pipeline_display_order', 'display_order'),
    )
    
    def get_stage_count(self):
        """Get number of stages in this pipeline"""
        if self.stages_data and isinstance(self.stages_data, list):
            return len(self.stages_data)
        elif self.properties and 'stages' in self.properties:
            return len(self.properties['stages'])
        return 0
    
    def get_stage_names(self):
        """Get list of stage names in order"""
        stages = []
        if self.stages_data and isinstance(self.stages_data, list):
            for stage in sorted(self.stages_data, key=lambda x: x.get('displayOrder', 0)):
                stages.append(stage.get('label', 'Unknown Stage'))
        elif self.properties and 'stages' in self.properties:
            for stage in sorted(self.properties['stages'], key=lambda x: x.get('displayOrder', 0)):
                stages.append(stage.get('label', 'Unknown Stage'))
        return stages
    
    def get_display_name(self):
        """Get display name for the pipeline"""
        return self.label or f"Pipeline {self.hubspot_pipeline_id}"
    
    def to_dict(self):
        """Enhanced dictionary representation"""
        result = super().to_dict()
        result.update({
            'display_name': self.get_display_name(),
            'stage_count': self.get_stage_count(),
            'stage_names': self.get_stage_names(),
            # Add compatibility aliases for test consistency
            'pipeline_id': self.hubspot_pipeline_id,
            'pipeline_name': self.label,
            'stages': self.stages_data or []
        })
        return result
    
    def __repr__(self):
        return f"<HubSpotDealPipeline(id={self.id}, label={self.label}, stages={self.get_stage_count()})>"