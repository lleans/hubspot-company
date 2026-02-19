from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Index, Text
from sqlalchemy.orm import relationship
from models.base import BaseModel

class ExtractionJob(BaseModel):
    """
    Represents a HubSpot data extraction job.
    Tracks the complete lifecycle and metadata of each extraction operation.
    """
    __tablename__ = 'extraction_jobs'
    
    # Job identification
    connection_id = Column(String(255), unique=True, nullable=False, index=True)
    
    # Job status and lifecycle
    status = Column(String(50), nullable=False, index=True)  # pending, running, completed, failed, cancelled
    start_time = Column(DateTime, nullable=False, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=True)
    
    # Job details
    message = Column(Text, nullable=True)
    error_details = Column(Text, nullable=True)
    
    # Progress tracking
    progress_percentage = Column(Integer, default=0)
    total_records_extracted = Column(Integer, default=0)
    companies_extracted = Column(Integer, default=0)
    deals_extracted = Column(Integer, default=0)
    pipelines_extracted = Column(Integer, default=0)
    
    # Performance metrics
    extraction_duration_seconds = Column(Integer, nullable=True)
    
    # Relationships with cascade delete
    companies = relationship(
        'HubSpotCompany', 
        back_populates='job', 
        cascade='all, delete-orphan',
        lazy='dynamic'
    )
    deals = relationship(
        'HubSpotDeal', 
        back_populates='job', 
        cascade='all, delete-orphan',
        lazy='dynamic'
    )
    pipelines = relationship(
        'HubSpotDealPipeline', 
        back_populates='job', 
        cascade='all, delete-orphan',
        lazy='dynamic'
    )
    
    # Strategic indexes for performance
    __table_args__ = (
        Index('idx_extraction_job_status_start', 'status', 'start_time'),
        Index('idx_extraction_job_connection', 'connection_id'),
        Index('idx_extraction_job_created_status', 'created_at', 'status'),
    )
    
    @property
    def is_active(self):
        """Check if job is currently active (running or pending)"""
        return self.status in ['pending', 'running']
    
    @property
    def is_completed(self):
        """Check if job completed successfully"""
        return self.status == 'completed'
    
    @property
    def has_failed(self):
        """Check if job failed"""
        return self.status == 'failed'
    
    def calculate_duration(self):
        """Calculate job duration in seconds"""
        if self.start_time and self.end_time:
            delta = self.end_time - self.start_time
            return int(delta.total_seconds())
        return None
    
    def to_dict(self):
        """Enhanced dictionary representation"""
        result = super().to_dict()
        result.update({
            'is_active': self.is_active,
            'is_completed': self.is_completed,
            'has_failed': self.has_failed,
            'duration_seconds': self.calculate_duration()
        })
        return result
    
    def __repr__(self):
        return f"<ExtractionJob(id={self.id}, connection_id={self.connection_id}, status={self.status})>"
    
