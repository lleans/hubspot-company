from datetime import datetime 
from sqlalchemy import Column, String, ForeignKey, Index, UniqueConstraint, Integer, Text , DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from models.base import BaseModel

class HubSpotCompany(BaseModel):
    """
    Stores HubSpot company records with comprehensive field mapping
    """
    __tablename__ = 'hubspot_companies'
    
    # Foreign key relationships
    job_id = Column(String, ForeignKey('extraction_jobs.id', ondelete='CASCADE'), nullable=False, index=True)
    connection_id = Column(String(255), nullable=False, index=True)
    
    # HubSpot specific fields
    hubspot_company_id = Column(String(50), nullable=False, index=True)
    
    # Core company information
    name = Column(String(500), nullable=True, index=True)
    domain = Column(String(255), nullable=True, index=True)
    industry = Column(String(255), nullable=True, index=True)
    description = Column(Text, nullable=True)
    
    # Location information
    city = Column(String(255), nullable=True)
    state = Column(String(255), nullable=True)
    country = Column(String(255), nullable=True)
    timezone = Column(String(100), nullable=True)
    
    # Business metrics
    annual_revenue = Column(String(50), nullable=True)  # Stored as string to handle various formats
    number_of_employees = Column(String(50), nullable=True)
    
    # HubSpot timestamps
    hubspot_created_date = Column(DateTime, nullable=True)
    hubspot_updated_date = Column(DateTime, nullable=True)
    
    # Complete properties as JSON for flexibility
    properties = Column(JSONB, nullable=True)
    
    # Relationship back to job
    job = relationship('ExtractionJob', back_populates='companies')
    
    # Constraints and indexes for performance and data integrity
    __table_args__ = (
        UniqueConstraint('connection_id', 'hubspot_company_id', name='uq_company_connection_hubspot_id'),
        Index('idx_company_name', 'name'),
        Index('idx_company_domain', 'domain'),
        Index('idx_company_industry', 'industry'),
        Index('idx_company_city_state', 'city', 'state'),
        Index('idx_company_hubspot_created', 'hubspot_created_date'),
    )
    
    def get_display_name(self):
        """Get display name for the company"""
        return self.name or self.domain or f"Company {self.hubspot_company_id}"
    
    def to_dict(self):
        """Enhanced dictionary representation"""
        result = super().to_dict()
        result['display_name'] = self.get_display_name()
        return result
    
    def __repr__(self):
        return f"<HubSpotCompany(id={self.id}, name={self.name}, domain={self.domain})>"