import pytest
import uuid
import os
import sys
from datetime import datetime, timedelta, timezone

# Add the parent directory to sys.path to allow imports from the project
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from models.database import get_db_session
from models import ExtractionJob, HubSpotCompany, HubSpotDeal, HubSpotDealPipeline

# Import app factory for testing
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import create_app

@pytest.fixture(scope="session")
def app():
    """Create Flask app for testing"""
    app = create_app("testing")
    with app.app_context():
        yield app

@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()

@pytest.fixture(scope="module")
def test_connection_id():
    """Generate a unique connection ID for tests"""
    return str(uuid.uuid4())

@pytest.fixture(scope="module")
def hubspot_token():
    """Get HubSpot token from environment or use a mock one for tests"""
    return os.getenv("HUBSPOT_API_TOKEN", "pat-na1-mock-token-for-tests")

@pytest.fixture
def mock_companies():
    """Create sample company data for tests"""
    return [
        {
            "hubspot_company_id": "12345",
            "name": "Acme Corporation",
            "domain": "acme.com",
            "properties": {
                "description": "Industry leader in innovative solutions",
                "industry": "Technology",
                "annual_revenue": 1000000
            }
        },
        {
            "hubspot_company_id": "67890",
            "name": "XYZ Enterprises",
            "domain": "xyz.com",
            "properties": {
                "description": "Global logistics company",
                "industry": "Transportation",
                "annual_revenue": 5000000
            }
        }
    ]

@pytest.fixture
def mock_deals():
    """Create sample deal data for tests"""
    return [
        {
            "deal_id": "deal-1",
            "deal_name": "Enterprise Software Package",
            "hubspot_company_id": "12345",
            "pipeline_id": "pipeline-1",
            "stage_id": "stage-2",
            "amount": 50000,
            "properties": {
                "priority": "High",
                "expected_close_date": "2025-12-31"
            }
        },
        {
            "deal_id": "deal-2",
            "deal_name": "Support Contract",
            "hubspot_company_id": "67890",
            "pipeline_id": "pipeline-1",
            "stage_id": "stage-1",
            "amount": 10000,
            "properties": {
                "priority": "Medium",
                "expected_close_date": "2025-09-30"
            }
        }
    ]

@pytest.fixture
def mock_pipelines():
    """Create sample pipeline data for tests"""
    return [
        {
            "pipeline_id": "pipeline-1",
            "pipeline_name": "Standard Sales Pipeline",
            "active": True,
            "stages": [
                {
                    "stage_id": "stage-1",
                    "label": "Qualification",
                    "display_order": 0,
                    "probability": 0.2
                },
                {
                    "stage_id": "stage-2",
                    "label": "Proposal",
                    "display_order": 1,
                    "probability": 0.5
                },
                {
                    "stage_id": "stage-3",
                    "label": "Closed Won",
                    "display_order": 2,
                    "probability": 1.0
                }
            ]
        },
        {
            "pipeline_id": "pipeline-2",
            "pipeline_name": "Partner Sales Pipeline",
            "active": True,
            "stages": [
                {
                    "stage_id": "p2-stage-1",
                    "label": "Partner Qualification",
                    "display_order": 0,
                    "probability": 0.3
                },
                {
                    "stage_id": "p2-stage-2",
                    "label": "Partner Closed",
                    "display_order": 1,
                    "probability": 1.0
                }
            ]
        }
    ]

@pytest.fixture
def seeded_job(app):
    """Create a completed extraction job with sample company, deal, and pipeline data"""
    connection_id = str(uuid.uuid4())
    job_id = None
    
    with get_db_session() as session:
        # Create job
        job = ExtractionJob(
            connection_id=connection_id,
            status="completed",
            start_time=datetime.now(timezone.utc) - timedelta(minutes=5),
            end_time=datetime.now(timezone.utc),
            message="Extraction completed successfully",
            progress_percentage=100,
            total_records_extracted=3,  # 1 company + 1 deal + 1 pipeline
            companies_extracted=1,
            deals_extracted=1,
            pipelines_extracted=1,
            extraction_duration_seconds=120
        )
        session.add(job)
        session.flush()
        job_id = job.id
        
        # Add company
        company = HubSpotCompany(
            hubspot_company_id="12345",
            job_id=job_id,
            connection_id=connection_id,
            name="Acme Corporation",
            domain="acme.com",
            city="Springfield",
            state="IL",
            country="United States",
            industry="Technology",
            hubspot_created_date=datetime.now(timezone.utc) - timedelta(days=30),
            properties={
                "description": "Industry leader in innovative solutions",
                "website": "https://acme.com",
                "number_of_employees": "500",
                "phone": "555-123-4567"
            }
        )
        session.add(company)
        session.flush()
        
        # Add deal pipeline
        pipeline = HubSpotDealPipeline(
            hubspot_pipeline_id="pipeline-123",
            job_id=job_id,
            connection_id=connection_id,
            label="Standard Sales Pipeline",
            display_order=1,
            active=True,
            created_at_hubspot=datetime.now(timezone.utc) - timedelta(days=45),
            stages_data=[
                {
                    "stage_id": "stage-1",
                    "label": "Qualification",
                    "display_order": 0,
                    "probability": 0.2
                },
                {
                    "stage_id": "stage-2",
                    "label": "Proposal",
                    "display_order": 1,
                    "probability": 0.5
                }
            ]
        )
        session.add(pipeline)
        session.flush()
        
        # Add deal
        deal = HubSpotDeal(
            hubspot_deal_id="deal-123",
            job_id=job_id,
            connection_id=connection_id,
            associated_company_id="12345",
            dealname="Enterprise Software Package",
            pipeline_id="pipeline-123",
            dealstage_id="stage-2",
            amount=50000.00,
            closedate=datetime.now(timezone.utc) + timedelta(days=30),
            hubspot_created_date=datetime.now(timezone.utc) - timedelta(days=15),
            hubspot_updated_date=datetime.now(timezone.utc) - timedelta(days=2),
            deal_type="new_business",
            deal_priority="High",
            properties={
                "description": "Enterprise-wide software deployment",
                "priority": "High",
                "expected_value": 45000
            }
        )
        session.add(deal)
    
    # At this point, the session is committed due to context manager
    
    # Find and return the job for use in tests
    with get_db_session() as session:
        job = session.query(ExtractionJob).filter_by(connection_id=connection_id).first()
        # Convert to dict to avoid DetachedInstanceError when session closes
        job_dict = job.to_dict() if job else None
        yield job_dict
    
    # Clean up after tests
    with get_db_session() as session:
        session.query(HubSpotDeal).filter_by(connection_id=connection_id).delete()
        session.query(HubSpotDealPipeline).filter_by(connection_id=connection_id).delete()
        session.query(HubSpotCompany).filter_by(connection_id=connection_id).delete()
        session.query(ExtractionJob).filter_by(connection_id=connection_id).delete()

@pytest.fixture
def pending_job(app):
    """Create a pending extraction job"""
    connection_id = str(uuid.uuid4())
    
    with get_db_session() as session:
        job = ExtractionJob(
            connection_id=connection_id,
            status="pending",
            start_time=datetime.now(timezone.utc),
            message="Extraction job pending",
            progress_percentage=0
        )
        session.add(job)
    
    # Retrieve the job from database to ensure we have the latest state
    with get_db_session() as session:
        job = session.query(ExtractionJob).filter_by(connection_id=connection_id).first()
        # Convert to dict to avoid DetachedInstanceError when session closes
        job_dict = job.to_dict() if job else None
        yield job_dict
    
    # Clean up
    with get_db_session() as session:
        session.query(ExtractionJob).filter_by(connection_id=connection_id).delete()
