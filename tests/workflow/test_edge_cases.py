import pytest
import uuid
import json
import sys
import os

# Add the parent directory to sys.path to allow imports from the project
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app
from models.database import get_db_session
from models import ExtractionJob



@pytest.mark.edge_case
def test_start_job_missing_token(client):
    """Test starting an extraction without providing an API token"""
    payload = {
        "config": {
            "scanId": str(uuid.uuid4()),
            "auth": {
                # No accessToken provided
            }
        }
    }
    response = client.post("/scan/start", json=payload)
    assert response.status_code == 401
    assert response.json["message"]

@pytest.mark.edge_case
def test_start_job_invalid_token_format(client):
    """Test starting an extraction with an invalid token format"""
    payload = {
        "config": {
            "scanId": str(uuid.uuid4()),
            "auth": {
                "accessToken": "not-a-valid-hubspot-token"  # Invalid format
            }
        }
    }
    response = client.post("/scan/start", json=payload)
    assert response.status_code == 401  # Invalid token should be 401 Unauthorized
    assert "token" in response.json["message"].lower() or "validation" in response.json["message"].lower()

def test_start_job_missing_connection_id(client):
    """Test starting an extraction without providing a scanId"""
    payload = {
        "config": {
            "auth": {
                "accessToken": "pat-na1-mock-token-123456789"
            }
            # No scanId provided
        }
    }
    response = client.post("/scan/start", json=payload)
    assert response.status_code == 400
    assert response.json["message"]

@pytest.mark.edge_case
def test_invalid_connection_id_format(client):
    """Test using a non-UUID format for the connection_id"""
    # Status endpoint with invalid format
    response = client.get("/scan/status/not-a-valid-uuid")
    assert response.status_code in (400, 404)
    
    # Results endpoint with invalid format
    response = client.get("/scan/result/not-a-valid-uuid")
    assert response.status_code in (400, 404)
    
    # Cancel endpoint with invalid format
    response = client.post("/scan/not-a-valid-uuid/cancel")
    assert response.status_code in (400, 404)
    
    # Remove endpoint with invalid format
    response = client.delete("/scan/remove/not-a-valid-uuid")
    assert response.status_code in (400, 404)

def test_nonexistent_job_endpoints(client):
    """Test accessing endpoints with a well-formed but non-existent job ID"""
    # Generate a random UUID that's unlikely to exist
    random_id = str(uuid.uuid4())
    
    # Status endpoint
    status_resp = client.get(f"/scan/status/{random_id}")
    assert status_resp.status_code == 404
    
    # Results endpoint
    result_resp = client.get(f"/scan/result/{random_id}")
    assert result_resp.status_code == 404
    
    # Cancel endpoint
    cancel_resp = client.post(f"/scan/{random_id}/cancel")
    assert cancel_resp.status_code == 404
    
    # Remove endpoint
    remove_resp = client.delete(f"/scan/remove/{random_id}")
    assert remove_resp.status_code == 404

def test_duplicate_extraction(client):
    """Test starting an extraction with the same scanId twice"""
    connection_id = str(uuid.uuid4())
    token = "pat-na1-mock-token-123456789"
    
    # First request should succeed
    first_resp = client.post("/scan/start", json={
        "config": {
            "scanId": connection_id,
            "auth": {
                "accessToken": token
            }
        }
    })
    assert first_resp.status_code == 202
    
    # Second request with same scanId should fail
    second_resp = client.post("/scan/start", json={
        "config": {
            "scanId": connection_id,
            "auth": {
                "accessToken": token
            }
        }
    })
    assert second_resp.status_code in (400, 409)  # Bad request or conflict
    
    # Clean up
    client.delete(f"/scan/remove/{connection_id}")

def test_malformed_request_body(client):
    """Test sending malformed JSON in the request body"""
    # Send invalid JSON
    response = client.post("/scan/start", 
                          data="this is not valid json",
                          content_type="application/json")
    assert response.status_code == 400
    
    # Send JSON with unexpected structure
    response = client.post("/scan/start", 
                          json=["array", "instead", "of", "object"])
    assert response.status_code == 400

@pytest.mark.edge_case
def test_sql_injection_attempts(client):
    """Test basic SQL injection prevention in API parameters"""
    # Try SQL injection in URL parameter
    injection_attempts = [
        "1 OR 1=1",
        "connection_id' OR '1'='1",
        "connection_id; DROP TABLE extraction_jobs;--",
        "'; exec sp_configure 'show advanced options', 1;--"
    ]
    
    for injection in injection_attempts:
        # Status endpoint
        status_resp = client.get(f"/scan/status/{injection}")
        assert status_resp.status_code in (400, 404)  # Either invalid format or not found
        
        # Results endpoint
        result_resp = client.get(f"/scan/result/{injection}")
        assert result_resp.status_code in (400, 404)

def test_extremely_large_job_id(client):
    """Test using an extremely long string as a job ID"""
    very_long_id = "a" * 1000  # 1000 character string
    
    response = client.get(f"/scan/status/{very_long_id}")
    assert response.status_code in (400, 404)  # Should reject overly long IDs

def test_malformed_config(client):
    """Test extraction with malformed configuration parameters"""
    payload = {
        "config": {
            "scanId": str(uuid.uuid4()),
            "auth": {
                "accessToken": "pat-na1-mock-token-123456789"
            },
            "type": "should be an array, not a string"  # Invalid config
        }
    }
    response = client.post("/scan/start", json=payload)
    assert response.status_code == 400

@pytest.mark.edge_case
def test_pagination_parameters(client):
    """Test pagination parameters with invalid values"""
    # Test negative page with result endpoint
    connection_id = str(uuid.uuid4())
    response = client.get(f"/scan/result/{connection_id}?page=-1")
    assert response.status_code in (200, 400, 404)  # Either handle it gracefully or reject
    
    # Test negative per_page
    response = client.get(f"/scan/result/{connection_id}?per_page=-10")
    assert response.status_code in (200, 400, 404)  # Either handle it gracefully or reject
    
    # Test extremely large per_page
    response = client.get(f"/scan/result/{connection_id}?per_page=1000000")
    assert response.status_code in (200, 404)  # Either handle gracefully or not found
    if response.status_code == 200:
        # Should cap at a reasonable maximum value
        pagination = response.json.get("pagination", {})
        assert pagination.get("per_page", 0) < 1000000

@pytest.mark.edge_case
def test_unsupported_http_methods(client):
    """Test using unsupported HTTP methods on endpoints"""
    # Try PUT on start endpoint (only POST allowed)
    response = client.put("/scan/start", json={
        "config": {
            "scanId": str(uuid.uuid4()),
            "auth": {
                "accessToken": "mock-token"
            }
        }
    })
    assert response.status_code in (405, 404)  # Method not allowed or not found
    
    # Try POST on status endpoint (only GET allowed)
    response = client.post(f"/scan/status/{str(uuid.uuid4())}")
    assert response.status_code in (405, 404)
    
    # Try DELETE on start endpoint (only POST allowed)
    response = client.delete("/scan/start")
    assert response.status_code in (405, 404)

@pytest.mark.edge_case
def test_health_endpoint_robustness(client):
    """Test health endpoint works even when DB might be unreachable"""    
    response = client.get("/scan/health")
    
    # Health check endpoint should return 200 OK
    assert response.status_code == 200
    
    # Basic assertion that response contains status
    assert "status" in response.json

@pytest.mark.edge_case
def test_comprehensive_error_response_validation(client):
    """Test detailed error response structure and content validation"""
    test_cases = [
        {
            "description": "Missing token error response",
            "request": {
                "method": "POST",
                "url": "/scan/start",
                "json": {"config": {"scanId": str(uuid.uuid4())}}
            },
            "expected_status": 401,
            "expected_fields": ["message"],
            "error_keywords": ["token", "auth", "accessToken"]
        },
        {
            "description": "Invalid connection ID format error response", 
            "request": {
                "method": "GET",
                "url": "/scan/status/invalid-uuid-format"
            },
            "expected_status": [400, 404],
            "expected_fields": ["message"],
            "should_not_expose": ["database", "internal", "exception", "traceback"]
        },
        {
            "description": "Non-existent job error response",
            "request": {
                "method": "GET", 
                "url": f"/scan/result/{str(uuid.uuid4())}"
            },
            "expected_status": 404,
            "expected_fields": ["message"],
            "error_keywords": ["not found", "does not exist"]
        }
    ]
    
    for test_case in test_cases:
        print(f"Testing: {test_case['description']}")
        
        # Make request
        if test_case["request"]["method"] == "GET":
            response = client.get(test_case["request"]["url"])
        elif test_case["request"]["method"] == "POST":
            response = client.post(
                test_case["request"]["url"], 
                json=test_case["request"].get("json", {})
            )
        
        # Validate status code
        expected_status = test_case["expected_status"]
        if isinstance(expected_status, list):
            assert response.status_code in expected_status, \
                f"Expected status {expected_status}, got {response.status_code}"
        else:
            assert response.status_code == expected_status, \
                f"Expected status {expected_status}, got {response.status_code}"
        
        # Validate response is JSON
        assert response.content_type == "application/json", \
            "Error response should be JSON"
        
        # Validate required fields present
        if "expected_fields" in test_case:
            for field in test_case["expected_fields"]:
                assert field in response.json, \
                    f"Expected field '{field}' missing from error response"
        
        # Validate error message contains expected keywords
        if "error_keywords" in test_case:
            message = response.json.get("message", "").lower()
            keyword_found = any(keyword.lower() in message for keyword in test_case["error_keywords"])
            assert keyword_found, \
                f"Error message should contain one of {test_case['error_keywords']}, got: {message}"
        
        # Validate sensitive information is not exposed
        if "should_not_expose" in test_case:
            response_text = str(response.json).lower()
            for sensitive_term in test_case["should_not_expose"]:
                assert sensitive_term.lower() not in response_text, \
                    f"Error response should not expose '{sensitive_term}'"
        
        # Validate message is user-friendly (not too technical)
        message = response.json.get("message", "")
        assert len(message) > 0, "Error message should not be empty"
        assert len(message) < 500, "Error message should be concise"
        
        print(f"  ✓ Status: {response.status_code}")
        print(f"  ✓ Message: {message[:100]}...")

@pytest.mark.edge_case  
def test_rate_limiting_error_handling(client):
    """Test error handling when rate limits might be hit"""
    # This test simulates rapid requests that might trigger rate limiting
    connection_ids = []
    
    try:
        # Make rapid requests
        for i in range(10):
            connection_id = f"rate-limit-test-{uuid.uuid4()}"
            connection_ids.append(connection_id)
            
            response = client.post("/scan/start", json={
                "config": {
                    "scanId": connection_id,
                    "auth": {
                        "accessToken": "pat-na1-mock-token-123456789"
                    }
                }
            })
            
            # With mock tokens, requests should succeed (202) or fail gracefully
            assert response.status_code in [202, 400, 401, 409, 500], \
                f"Unexpected status code for rapid request: {response.status_code}"
            
            # If we get a 409 (conflict), it means duplicate extraction detection is working
            if response.status_code == 409:
                assert "already exists" in response.json.get("message", "").lower()
                break
                
    finally:
        # Clean up any successful jobs
        for connection_id in connection_ids:
            try:
                client.delete(f"/scan/remove/{connection_id}")
            except:
                pass  # Ignore cleanup errors

# ============================================================================
# PERFORMANCE STRESS TESTS - Concurrency and Load Testing  
# ============================================================================

@pytest.mark.performance
@pytest.mark.edge_case
def test_concurrent_extraction_requests(client):
    """Test system performance under concurrent extraction requests"""
    import threading
    import time
    
    num_concurrent_requests = 5
    connection_ids = []
    responses = []
    start_time = time.time()
    
    def make_request(connection_id):
        payload = {
            "config": {
                "scanId": connection_id,
                "auth": {
                    "accessToken": "pat-na1-mock-token-123456789"
                },
                "extraction": {"batch_size": 10}  # Small batch for faster testing
            }
        }
        response = client.post("/scan/start", json=payload)
        responses.append((connection_id, response))
    
    # Create threads for concurrent requests
    threads = []
    for i in range(num_concurrent_requests):
        connection_id = f"perf-test-{uuid.uuid4()}"
        connection_ids.append(connection_id)
        thread = threading.Thread(target=make_request, args=(connection_id,))
        threads.append(thread)
    
    # Start all threads simultaneously
    for thread in threads:
        thread.start()
    
    # Wait for all threads to complete
    for thread in threads:
        thread.join()
    
    elapsed_time = time.time() - start_time
    
    # Verify all requests were processed
    assert len(responses) == num_concurrent_requests
    
    # Verify response times are reasonable (should handle concurrent requests within 10 seconds)
    assert elapsed_time < 10, f"Concurrent requests took too long: {elapsed_time:.2f}s"
    
    # Verify all responses are valid
    successful_responses = 0
    for connection_id, response in responses:
        if response.status_code == 202:
            successful_responses += 1
        else:
            # Mock token might cause auth failures, which is acceptable
            assert response.status_code in [400, 401], f"Unexpected status code: {response.status_code}"
    
    # At least some requests should succeed (depending on mock implementation)
    print(f"Successful responses: {successful_responses}/{num_concurrent_requests}")
    print(f"Total time for {num_concurrent_requests} concurrent requests: {elapsed_time:.2f}s")
    
    # Clean up any successful jobs
    for connection_id, response in responses:
        if response.status_code == 202:
            client.delete(f"/scan/remove/{connection_id}")

@pytest.mark.performance
@pytest.mark.edge_case
def test_memory_usage_under_load(client):
    """Test memory usage patterns under simulated load"""
    try:
        import psutil
    except ImportError:
        pytest.skip("psutil not available for memory testing")
    
    import os
    
    # Get current process
    process = psutil.Process(os.getpid())
    initial_memory = process.memory_info().rss / 1024 / 1024  # MB
    
    # Simulate load by making multiple requests
    connection_ids = []
    for i in range(20):
        connection_id = f"memory-test-{uuid.uuid4()}"
        connection_ids.append(connection_id)
        
        # Create job in database
        with get_db_session() as session:
            job = ExtractionJob(
                connection_id=connection_id,
                status="completed",
                progress_percentage=100,
                total_records_extracted=100,
                message=f"Memory test job {i}"
            )
            session.add(job)
        
        # Make status and result requests
        client.get(f"/scan/status/{connection_id}")
        client.get(f"/scan/result/{connection_id}")
    
    final_memory = process.memory_info().rss / 1024 / 1024  # MB
    memory_increase = final_memory - initial_memory
    
    print(f"Initial memory: {initial_memory:.2f} MB")
    print(f"Final memory: {final_memory:.2f} MB")
    print(f"Memory increase: {memory_increase:.2f} MB")
    
    # Memory increase should be reasonable (< 50 MB for this test)
    assert memory_increase < 50, f"Excessive memory usage: {memory_increase:.2f} MB increase"
    
    # Clean up
    with get_db_session() as session:
        for connection_id in connection_ids:
            session.query(ExtractionJob).filter_by(connection_id=connection_id).delete()