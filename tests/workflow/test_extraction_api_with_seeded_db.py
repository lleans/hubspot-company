import pytest
import uuid
import sys
import os
import time
from datetime import datetime, timedelta, timezone

# Add the parent directory to sys.path to allow imports from the project
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app
from models.database import get_db_session
from models import ExtractionJob, HubSpotCompany, HubSpotDeal, HubSpotDealPipeline




@pytest.mark.integration
def test_get_status_with_seeded_job(client, seeded_job):
    """Test retrieving status of a completed extraction job"""
    response = client.get(f"/scan/status/{seeded_job['connection_id']}")
    assert response.status_code == 200
    assert response.json["status"] == "completed"
    assert response.json["progress"]["percentage"] == 100
    assert response.json["progress"]["recordsProcessed"] == 3
    assert response.json["metadata"]["companiesExtracted"] == 1
    assert response.json["metadata"]["dealsExtracted"] == 1
    assert response.json["metadata"]["pipelinesExtracted"] == 1

@pytest.mark.integration
def test_get_result_with_seeded_job(client, seeded_job):
    """Test retrieving results of a completed extraction job"""
    response = client.get(f"/scan/result/{seeded_job['connection_id']}")
    assert response.status_code == 200
    assert response.json["status"] == "completed"
    
    # Verify companies data structure and required fields
    assert "data" in response.json
    assert "companies" in response.json["data"]
    assert len(response.json["data"]["companies"]) == 1
    company = response.json["data"]["companies"][0]
    assert company["name"] == "Acme Corporation"
    assert company["domain"] == "acme.com"
    # Verify required company fields per documentation
    assert "hubspot_company_id" in company
    assert "properties" in company
    assert company["hubspot_company_id"] == "12345"
    
    # Verify deals data structure and required fields
    assert "deals" in response.json["data"]
    assert len(response.json["data"]["deals"]) == 1
    deal = response.json["data"]["deals"][0]
    assert deal["dealname"] == "Enterprise Software Package"
    assert deal["amount"] == 50000.00
    # Verify required deal fields per documentation
    assert "hubspot_deal_id" in deal
    assert "associated_company_id" in deal
    assert deal["hubspot_deal_id"] == "deal-123"
    
    # Verify pipelines data structure and required fields
    assert "pipelines" in response.json["data"]
    assert len(response.json["data"]["pipelines"]) == 1
    pipeline = response.json["data"]["pipelines"][0]
    assert pipeline["label"] == "Standard Sales Pipeline"
    assert len(pipeline["stages_data"]) == 2
    # Verify required pipeline fields per documentation
    assert "hubspot_pipeline_id" in pipeline
    assert "active" in pipeline
    assert pipeline["hubspot_pipeline_id"] == "pipeline-123"
    assert pipeline["active"] == True

@pytest.mark.integration
@pytest.mark.skip(reason="Jobs list endpoint not implemented in current API design")
def test_list_jobs(client, seeded_job):
    """Test listing all extraction jobs"""
    # This functionality is not available in the current API design
    # Jobs are accessed individually by scan_id via /scan/status/{scan_id}
    pass

@pytest.mark.integration
def test_job_statistics(client, seeded_job):
    """Test retrieving job statistics"""
    response = client.get("/scan/stats")
    assert response.status_code == 200
    assert "extractions" in response.json
    assert response.json["extractions"]["total_scans"] >= 1
    assert "successful_scans" in response.json["extractions"]
    assert "performance" in response.json

@pytest.mark.integration
def test_health_check(client):
    """Test health check endpoint"""
    response = client.get("/scan/health")
    assert response.status_code == 200
    assert "status" in response.json
    assert response.json["status"] in ["healthy", "unhealthy"]

def test_cancel_pending_job(client, pending_job):
    """Test cancelling a pending extraction job"""
    response = client.post(f"/scan/cancel/{pending_job['connection_id']}")
    assert response.status_code == 200
    assert "message" in response.json
    assert "cancelled" in response.json["message"].lower()
    
    # Verify job status has been updated
    status_response = client.get(f"/scan/status/{pending_job['connection_id']}")
    assert status_response.status_code == 200
    assert status_response.json["status"] == "cancelled"

def test_remove_job(client, seeded_job):
    """Test removing extraction data"""
    response = client.delete(f"/scan/remove/{seeded_job['connection_id']}")
    assert response.status_code == 200
    assert "message" in response.json
    assert response.json["message"]
    
    # Verify job and related data are gone
    result_response = client.get(f"/scan/result/{seeded_job['connection_id']}")
    assert result_response.status_code == 404

def test_start_job(client):
    """Test starting a new extraction job with mock token"""
    token = "pat-na1-mocktoken-123456789"
    payload = {
        "connection_id": str(uuid.uuid4()),
        "token": token,
        "config": {
            "include_stage_history": True, 
            "batch_size": 100      
        }
    }
    
    response = client.post("/scan/start", json=payload)
    assert response.status_code == 202
    assert "job_id" in response.json
    assert "connection_id" in response.json
    assert "status" in response.json
    
    # Clean up the job
    job_id = response.json["job_id"]
    with get_db_session() as session:
        session.query(ExtractionJob).filter_by(id=job_id).delete()

# ============================================================================
# UNIT TESTS - Data Validation using Mock Data
# ============================================================================

@pytest.mark.unit
def test_company_data_validation(mock_companies):
    """Test company data structure validation using mock data"""
    for company_data in mock_companies:
        # Verify required fields are present
        assert "hubspot_company_id" in company_data
        assert "name" in company_data
        assert "domain" in company_data
        assert "properties" in company_data
        
        # Verify data types
        assert isinstance(company_data["hubspot_company_id"], str)
        assert isinstance(company_data["name"], str)
        assert isinstance(company_data["domain"], str)
        assert isinstance(company_data["properties"], dict)
        
        # Verify business logic constraints
        assert len(company_data["name"]) > 0
        assert "." in company_data["domain"]  # Basic domain format check

@pytest.mark.unit
def test_deal_data_validation(mock_deals):
    """Test deal data structure validation using mock data"""
    for deal_data in mock_deals:
        # Verify required fields are present
        assert "deal_id" in deal_data
        assert "deal_name" in deal_data
        assert "hubspot_company_id" in deal_data
        assert "pipeline_id" in deal_data
        assert "stage_id" in deal_data
        assert "amount" in deal_data
        assert "properties" in deal_data
        
        # Verify data types
        assert isinstance(deal_data["deal_id"], str)
        assert isinstance(deal_data["deal_name"], str)
        assert isinstance(deal_data["hubspot_company_id"], str)
        assert isinstance(deal_data["amount"], (int, float))
        assert isinstance(deal_data["properties"], dict)
        
        # Verify business logic constraints
        assert deal_data["amount"] > 0  # Deal amount should be positive
        assert len(deal_data["deal_name"]) > 0

@pytest.mark.unit
def test_pipeline_data_validation(mock_pipelines):
    """Test pipeline data structure validation using mock data"""
    for pipeline_data in mock_pipelines:
        # Verify required fields are present
        assert "pipeline_id" in pipeline_data
        assert "pipeline_name" in pipeline_data
        assert "active" in pipeline_data
        assert "stages" in pipeline_data
        
        # Verify data types
        assert isinstance(pipeline_data["pipeline_id"], str)
        assert isinstance(pipeline_data["pipeline_name"], str)
        assert isinstance(pipeline_data["active"], bool)
        assert isinstance(pipeline_data["stages"], list)
        
        # Verify stages structure
        assert len(pipeline_data["stages"]) > 0
        for stage in pipeline_data["stages"]:
            assert "stage_id" in stage
            assert "label" in stage
            assert "display_order" in stage
            assert "probability" in stage
            
            # Verify stage data types
            assert isinstance(stage["stage_id"], str)
            assert isinstance(stage["label"], str)
            assert isinstance(stage["display_order"], int)
            assert isinstance(stage["probability"], (int, float))
            
            # Verify business logic constraints
            assert 0 <= stage["probability"] <= 1.0  # Probability should be between 0 and 1
            assert stage["display_order"] >= 0

@pytest.mark.unit
def test_data_relationships(mock_companies, mock_deals, mock_pipelines):
    """Test data relationships between companies, deals, and pipelines"""
    # Extract IDs for relationship validation
    company_ids = {company["hubspot_company_id"] for company in mock_companies}
    pipeline_ids = {pipeline["pipeline_id"] for pipeline in mock_pipelines}
    
    # Extract stage IDs from all pipelines
    stage_ids = set()
    for pipeline in mock_pipelines:
        for stage in pipeline["stages"]:
            stage_ids.add(stage["stage_id"])
    
    # Verify deal relationships
    for deal in mock_deals:
        # Deal should reference existing company
        assert deal["hubspot_company_id"] in company_ids, \
            f"Deal {deal['deal_id']} references non-existent company {deal['hubspot_company_id']}"
        
        # Deal should reference existing pipeline
        assert deal["pipeline_id"] in pipeline_ids, \
            f"Deal {deal['deal_id']} references non-existent pipeline {deal['pipeline_id']}"
        
        # Deal should reference existing stage
        assert deal["stage_id"] in stage_ids, \
            f"Deal {deal['deal_id']} references non-existent stage {deal['stage_id']}"

@pytest.mark.unit
def test_mock_data_consistency(mock_companies, mock_deals, mock_pipelines):
    """Test that mock data is internally consistent"""
    # Use fixtures properly via dependency injection
    companies = mock_companies
    deals = mock_deals
    pipelines = mock_pipelines
    
    # Verify we have data
    assert len(companies) > 0, "Mock companies should not be empty"
    assert len(deals) > 0, "Mock deals should not be empty"
    assert len(pipelines) > 0, "Mock pipelines should not be empty"
    
    # Verify no duplicate IDs within each dataset
    company_ids = [c["hubspot_company_id"] for c in companies]
    assert len(company_ids) == len(set(company_ids)), "Duplicate company IDs found"
    
    deal_ids = [d["deal_id"] for d in deals]
    assert len(deal_ids) == len(set(deal_ids)), "Duplicate deal IDs found"
    
    pipeline_ids = [p["pipeline_id"] for p in pipelines]
    assert len(pipeline_ids) == len(set(pipeline_ids)), "Duplicate pipeline IDs found"

# ============================================================================
# PERFORMANCE TESTS - Basic Performance and Response Time Testing
# ============================================================================

@pytest.mark.performance
def test_status_polling_performance(client):
    """Test performance of status polling operations"""
    # Create a mock job first
    connection_id = str(uuid.uuid4())
    
    with get_db_session() as session:
        job = ExtractionJob(
            connection_id=connection_id,
            status="in_progress",
            progress_percentage=50,
            message="Test job in progress"
        )
        session.add(job)
        session.commit()
    
    # Measure status polling performance
    num_polls = 50
    start_time = time.time()
    
    for i in range(num_polls):
        response = client.get(f"/scan/status/{connection_id}")
        assert response.status_code == 200
        assert response.json["status"] == "in_progress"
    
    elapsed_time = time.time() - start_time
    avg_response_time = elapsed_time / num_polls
    
    # Status polls should be very fast (< 100ms average)
    assert avg_response_time < 0.1, f"Status polling too slow: {avg_response_time:.3f}s average"
    
    print(f"Average status poll response time: {avg_response_time:.3f}s")
    print(f"Total time for {num_polls} status polls: {elapsed_time:.2f}s")
    
    # Clean up
    with get_db_session() as session:
        session.query(ExtractionJob).filter_by(connection_id=connection_id).delete()

@pytest.mark.performance
def test_large_result_retrieval_performance(client):
    """Test performance when retrieving large result sets"""
    connection_id = str(uuid.uuid4())
    
    # Create a job with simulated large dataset
    with get_db_session() as session:
        job = ExtractionJob(
            connection_id=connection_id,
            status="completed",
            progress_percentage=100,
            total_records_extracted=1000,  # Simulate large dataset
            companies_extracted=300,
            deals_extracted=500,
            pipelines_extracted=200,
            message="Large dataset extraction completed"
        )
        session.add(job)
        session.commit()
    
    # Measure result retrieval performance
    start_time = time.time()
    response = client.get(f"/scan/result/{connection_id}")
    elapsed_time = time.time() - start_time
    
    assert response.status_code == 200
    
    # Large result retrieval should complete within reasonable time (< 5 seconds)
    assert elapsed_time < 5, f"Large result retrieval too slow: {elapsed_time:.2f}s"
    
    print(f"Large result retrieval time: {elapsed_time:.3f}s")
    
    # Clean up
    with get_db_session() as session:
        session.query(ExtractionJob).filter_by(connection_id=connection_id).delete()

@pytest.mark.performance
def test_job_cancellation_timeout(client):
    """Test job cancellation timeout handling"""
    connection_id = str(uuid.uuid4())
    
    # Create a running job
    with get_db_session() as session:
        job = ExtractionJob(
            connection_id=connection_id,
            status="running",
            progress_percentage=25,
            message="Job in progress, ready for cancellation test"
        )
        session.add(job)
        session.commit()
    
    # Test cancellation response time
    start_time = time.time()
    response = client.post(f"/scan/cancel/{connection_id}")
    elapsed_time = time.time() - start_time
    
    # Cancellation should be immediate (< 1 second)
    assert elapsed_time < 1, f"Job cancellation too slow: {elapsed_time:.2f}s"
    assert response.status_code == 200
    
    print(f"Job cancellation response time: {elapsed_time:.3f}s")
    
    # Clean up
    with get_db_session() as session:
        session.query(ExtractionJob).filter_by(connection_id=connection_id).delete()

@pytest.mark.performance
def test_api_endpoint_response_times(client):
    """Test response times for all major API endpoints"""
    endpoints_to_test = [
        ("GET", "/scan/health"),
        ("GET", "/scan/stats"),
    ]
    
    response_times = {}
    
    for method, endpoint in endpoints_to_test:
        start_time = time.time()
        
        if method == "GET":
            response = client.get(endpoint)
        elif method == "POST":
            response = client.post(endpoint)
        
        elapsed_time = time.time() - start_time
        response_times[endpoint] = elapsed_time
        
        # All endpoints should respond quickly (< 2 seconds)
        assert elapsed_time < 2, f"Endpoint {endpoint} too slow: {elapsed_time:.2f}s"
        assert response.status_code == 200
    
    # Print performance summary
    print("\nAPI Endpoint Response Times:")
    for endpoint, time_taken in response_times.items():
        print(f"  {endpoint}: {time_taken:.3f}s")
    
    avg_response_time = sum(response_times.values()) / len(response_times)
    print(f"Average response time: {avg_response_time:.3f}s")
    
    # Average response time should be very fast
    assert avg_response_time < 0.5, f"Average response time too slow: {avg_response_time:.3f}s"
