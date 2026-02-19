import uuid
from datetime import datetime
from decimal import Decimal
from sqlalchemy import Column, String, DateTime
from sqlalchemy.orm import declarative_base

Base = declarative_base()

def generate_uuid():
    return str(uuid.uuid4())

class BaseModel(Base):
    __abstract__ = True
    
    id = Column(String, primary_key=True, default=generate_uuid)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def to_dict(self):
        """Convert model to dictionary with JSON serialization support"""
        result = {}
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            
            # Handle datetime objects
            if isinstance(value, datetime):
                result[column.name] = value.isoformat() if value else None
            # Handle Decimal objects
            elif isinstance(value, Decimal):
                result[column.name] = float(value) if value else None
            # Handle other types
            else:
                result[column.name] = value
                
        return result
    