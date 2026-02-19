import pytest
import os
import sys
import time
from datetime import datetime

# Add the parent directory to sys.path to allow imports from the project
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app
from models.database import get_db_session
from models import ExtractionJob



@pytest.mark.real_creds
@pytest.mark.skipif(not os.getenv("HUBSPOT_API_TOKEN"), reason="HUBSPOT_API_TOKEN environment variable not set")
def test_real_extraction_flow(client):
    """
    Integration test for the complete extraction flow using real HubSpot credentials.
    
    This test will:
    1. Start an extraction job with real HubSpot API token
    2. Poll for status until job completes or timeout
    3. Verify the extracted data
    4. Clean up by removing the extraction data
    
    Requires: HUBSPOT_API_TOKEN environment variable to be set
    """
    # Get API token from environment
    real_token = os.getenv("HUBSPOT_API_TOKEN")
    assert real_token, "HUBSPOT_API_TOKEN must be set in environment"
    
    connection_id = f"test-real-flow-{int(time.time())}"
    
    # 1. Start extraction job
    # Note: Currently using new API format. Legacy format compatibility should be added to the API
    start_resp = client.post("/scan/start", json={
        "config": {
            "scanId": connection_id,
            "auth": {
                "accessToken": real_token
            },
            "type": ["companies", "deals", "pipelines"],
            "extraction": {
                "batch_size": 100
            }
        }
    })
    assert start_resp.status_code == 202
    job_id = start_resp.json.get("scanId")
    assert job_id is not None
    
    # 2. Poll for status until complete
    timeout_seconds = 240  # Allow up to 4 minutes for the extraction to complete
    poll_interval = 5  # Check every 5 seconds
    elapsed = 0
    
    status = None
    while elapsed < timeout_seconds:
        status_resp = client.get(f"/scan/status/{connection_id}")
        assert status_resp.status_code == 200
        status = status_resp.json.get("status")
        
        # Print progress information
        print(f"Status: {status}, Progress: {status_resp.json.get('progress', {}).get('percentage', 0)}%, "
              f"Records: {status_resp.json.get('progress', {}).get('recordsProcessed', 0)}")
        
        if status in ["completed", "failed"]:
            break
            
        time.sleep(poll_interval)
        elapsed += poll_interval
    
    # If we timed out waiting
    assert elapsed < timeout_seconds, f"Timed out waiting for extraction to complete. Last status: {status}"
    
    # If the job failed
    assert status == "completed", f"Extraction job failed: {status_resp.json.get('message')}"
    
    # 3. Verify extraction results
    result_resp = client.get(f"/scan/result/{connection_id}")
    assert result_resp.status_code == 200
    
    # Basic validation of the response structure
    assert "data" in result_resp.json
    assert "companies" in result_resp.json["data"]
    assert "deals" in result_resp.json["data"]
    assert "pipelines" in result_resp.json["data"]
    
    # Log some stats about what we extracted
    print(f"Extracted {len(result_resp.json['data']['companies'])} companies")
    print(f"Extracted {len(result_resp.json['data']['deals'])} deals")
    print(f"Extracted {len(result_resp.json['data']['pipelines'])} pipelines")
    
    # Validate at least some data was extracted (assuming test account has data)
    # If the account has no data, these assertions may need adjustment
    total_extracted = len(result_resp.json['data']['companies']) + len(result_resp.json['data']['deals']) + len(result_resp.json['data']['pipelines'])
    
    # For real credentials test, we expect at least some data (even if just pipelines)
    assert total_extracted > 0, "No data was extracted from HubSpot account"
    
    if len(result_resp.json['data']['companies']) > 0:
        # Verify company has expected fields
        company = result_resp.json['data']['companies'][0]
        assert "hubspot_company_id" in company
        assert "name" in company
    
    if len(result_resp.json['data']['deals']) > 0:
        # Verify deal has expected fields
        deal = result_resp.json['data']['deals'][0]
        assert "hubspot_deal_id" in deal
        # Check for deal name (we added deal_name as alias, but original field is dealname)
        assert "deal_name" in deal or "dealname" in deal
    
    if len(result_resp.json['data']['pipelines']) > 0:
        # Verify pipeline has expected fields
        pipeline = result_resp.json['data']['pipelines'][0]
        assert "pipeline_id" in pipeline or "hubspot_pipeline_id" in pipeline
        assert "pipeline_name" in pipeline or "label" in pipeline
        assert "stages" in pipeline or "stages_data" in pipeline
    
    # 4. Clean up by removing extraction data
    remove_resp = client.delete(f"/scan/remove/{connection_id}")
    assert remove_resp.status_code == 200
    assert "message" in remove_resp.json
    assert "removed successfully" in remove_resp.json["message"].lower()
    
    # Verify data was actually removed
    check_resp = client.get(f"/scan/result/{connection_id}")
    assert check_resp.status_code == 404

@pytest.mark.real_creds
@pytest.mark.skipif(not os.getenv("HUBSPOT_API_TOKEN"), reason="HUBSPOT_API_TOKEN environment variable not set")
def test_real_extraction_with_cancellation(client):
    """
    Test starting a real extraction job and then cancelling it
    
    This test will:
    1. Start an extraction job with real HubSpot API token
    2. Wait a short time for the job to start processing
    3. Cancel the job
    4. Verify the job was cancelled
    5. Clean up
    
    Requires: HUBSPOT_API_TOKEN environment variable to be set
    """
    # Get API token from environment
    real_token = os.getenv("HUBSPOT_API_TOKEN")
    assert real_token, "HUBSPOT_API_TOKEN must be set in environment"
    
    connection_id = f"test-cancel-flow-{int(time.time())}"
    
    # 1. Start extraction job
    # Note: Currently using new API format. Legacy format compatibility should be added to the API
    start_resp = client.post("/scan/start", json={
        "config": {
            "scanId": connection_id,
            "auth": {
                "accessToken": real_token
            },
            "type": ["companies", "deals", "pipelines"],
            "extraction": {
                "batch_size": 100
            }
        }
    })
    assert start_resp.status_code == 202
    job_id = start_resp.json.get("scanId")
    assert job_id is not None
    
    # 2. Wait a short time for the job to start processing
    time.sleep(5)  # Give it 5 seconds to start
    
    # 3. Cancel the job
    cancel_resp = client.post(f"/scan/{connection_id}/cancel")
    # The job might complete quickly, so we accept successful cancellation (200), 
    # "job already completed" (400), or "job not found" (404) as valid responses
    assert cancel_resp.status_code in [200, 400, 404], f"Unexpected status code: {cancel_resp.status_code}, response: {cancel_resp.json}"
    
    if cancel_resp.status_code == 200:
        # Job was successfully cancelled
        assert "message" in cancel_resp.json
        assert "cancelled" in cancel_resp.json["message"].lower()
        
        # 4. Verify the job was cancelled
        status_resp = client.get(f"/scan/status/{connection_id}")
        assert status_resp.status_code == 200
        
        # The job might still be in the process of cancelling, so poll until it's fully cancelled
        timeout_seconds = 30  # Allow up to 30 seconds for cancellation to complete
        poll_interval = 2  # Check every 2 seconds
        elapsed = 0
        
        while elapsed < timeout_seconds:
            status_resp = client.get(f"/scan/status/{connection_id}")
            assert status_resp.status_code == 200
            status = status_resp.json.get("status")
            
            if status == "cancelled":
                break
                
            time.sleep(poll_interval)
            elapsed += poll_interval
        
        assert status == "cancelled", f"Job wasn't cancelled, status: {status}"
    elif cancel_resp.status_code == 404:
        # Job completed so quickly that it's no longer found for cancellation
        message = cancel_resp.json.get('message', 'No message') if cancel_resp.json else 'Job not found'
        print(f"Job completed before cancellation could be attempted: {message}")
        
        # Verify the job status is indeed completed
        status_resp = client.get(f"/scan/status/{connection_id}")
        assert status_resp.status_code == 200
        status = status_resp.json.get("status")
        assert status in ["completed", "failed"], f"Expected completed/failed status, got: {status}"
    else:
        # Job already completed, which is also a valid scenario for this test
        message = cancel_resp.json.get('message', 'No message') if cancel_resp.json else 'No message'
        print(f"Job completed before cancellation: {message}")
        
        # Verify the job status is indeed completed
        status_resp = client.get(f"/scan/status/{connection_id}")
        assert status_resp.status_code == 200
        status = status_resp.json.get("status")
        assert status in ["completed", "failed"], f"Expected completed/failed status, got: {status}"
    
    # 5. Clean up
    remove_resp = client.delete(f"/scan/remove/{connection_id}")
    assert remove_resp.status_code == 200
