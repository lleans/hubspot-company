# HubSpot CompanyDeal Extraction Service: API Test Workflow Documentation

---

## Table of Contents

1. **Introduction**
2. **Test Types Overview**
3. **Workflow Steps for Seeded Data Tests**
4. **Workflow Steps for Real Extraction Tests**
5. **Common Assertions and Validations**
6. **API Endpoints Tested and Their Test Cases**
7. **Edge Case Tests**
8. **Test Configuration and Fixtures**
9. **Conclusion**

---

The outlined test workflows and edge case validations ensure comprehensive coverage of the HubSpot CompanyDeal Extraction Service API. The test suite provides:

### Coverage Areas
- **Unit Testing**: Individual endpoint functionality with mocked data
- **Integration Testing**: End-to-end workflows with real HubSpot API
- **Edge Case Testing**: Security, validation, and error handling
- **Performance Testing**: Timeout handling and long-running job management

### Key Benefits
1. **Seeded Data Tests**: Fast, reliable testing without external dependencies
2. **Real Extraction Tests**: Validates actual HubSpot API integration and data quality
3. **Edge Case Tests**: Ensures API robustness and security
4. **Comprehensive Fixtures**: Reusable test data and setup for consistent testing

### Test Execution Strategy
- **Development**: Run seeded data and edge case tests for quick feedback
- **Integration**: Run real extraction tests in staging environment
- **CI/CD**: Automated execution of full test suite with appropriate environment variables
- **Security**: Regular execution of edge case tests to validate security measures

### Data Validation
The test suite thoroughly validates:
- **Companies**: HubSpot company records with properties and associations
- **Deals**: Deal records with amounts, stages, and pipeline associations  
- **Pipelines**: Deal pipeline structures with stages and probabilities
- **Job Management**: Extraction job lifecycle and status transitions

This comprehensive approach helps maintain high quality and reliability of the CompanyDeal extraction service across development, testing, and production environments.

### Running the Tests

```bash
# Run all tests
pytest

# Run only seeded data tests  
pytest tests/workflow/test_extraction_api_with_seeded_db.py

# Run only edge case tests
pytest tests/workflow/test_edge_cases.py

# Run real extraction tests (requires HUBSPOT_API_TOKEN)
HUBSPOT_API_TOKEN=your_token_here pytest tests/workflow/test_extraction_flow_with_real_credentials.py

# Run with verbose output
pytest -v

# Run specific test
pytest tests/workflow/test_edge_cases.py::test_start_job_missing_token
```se Tests**
8. **Test Configuration and Fixtures**
9. **Conclusion**

---

## 1. Introduction

This document outlines the API testing workflow for the HubSpot CompanyDeal Extraction Service. The service extracts companies, deals, and deal pipelines from HubSpot. Three primary types of tests are described:

* **Seeded Data Tests:** Tests that use pre-populated database entries to validate API behavior without requiring actual HubSpot API calls.
* **Real Extraction Tests:** Tests that interact with the HubSpot API in real-time using valid API tokens, performing actual data extraction.
* **Edge Case Tests:** Tests that ensure robustness against invalid inputs and unexpected client behaviors.

The test suite includes the following test files:
- `test_extraction_api_with_seeded_db.py` - Tests with pre-seeded database data
- `test_extraction_flow_with_real_credentials.py` - Integration tests with real HubSpot API
- `test_edge_cases.py` - Edge case and error handling tests
- `conftest.py` - Shared test fixtures and utilities

---

## 2. Test Types Overview

| Test Type             | Description                                                                                  | Use Case                                           |
| --------------------- | -------------------------------------------------------------------------------------------- | -------------------------------------------------- |
| Seeded Data Tests     | Use predefined data inserted directly into the test database for controlled, fast tests     | Validating API logic without external dependencies |
| Real Extraction Tests | Use real HubSpot API tokens to trigger actual extractions and validate live integration     | End-to-end integration with HubSpot API           |
| Edge Case Tests       | Validate API behavior with invalid inputs and unexpected scenarios                          | Ensure API robustness and proper error handling   |

---

## 3. Workflow Steps for Seeded Data Tests

**File:** `test_extraction_api_with_seeded_db.py`

### Test Fixtures
- **seeded_job**: Creates a completed extraction job with sample company, deal, and pipeline data
- **pending_job**: Creates a pending extraction job for testing cancellation

### Test Flow
1. **Setup**: Seed the database with:
   - Extraction job with status "completed"
   - Sample HubSpot company (Acme Corporation)
   - Sample deal pipeline with stages
   - Sample deal associated with company and pipeline
2. **Status Check**: Query `/api/scan/status/{connection_id}` for the seeded job
3. **Fetch Results**: Retrieve extraction results from `/api/scan/result/{connection_id}`
4. **List Jobs**: Test `/api/jobs/jobs` endpoint with pagination
5. **Job Statistics**: Test `/api/jobs/statistics` endpoint
6. **Health Check**: Confirm `/api/system/health` endpoint functionality
7. **Cancel Job**: Cancel a pending job via `/api/scan/{connection_id}/cancel`
8. **Remove Job**: Remove extraction data via `/api/scan/remove/{connection_id}`
9. **Start Job**: Test starting a new job with mock token

---

## 4. Workflow Steps for Real Extraction Tests

**File:** `test_extraction_flow_with_real_credentials.py`

### Prerequisites
- Requires `HUBSPOT_API_TOKEN` environment variable to be set
- Tests are skipped if the environment variable is not present
- Uses `@pytest.mark.skipif` decorator for conditional execution

### Test Flow 1: Complete Extraction Flow
1. **Start Extraction**: Send POST to `/api/scan/start` with real HubSpot API token
2. **Poll Status**: Continuously check `/api/scan/status/{connection_id}` with:
   - 4-minute timeout (240 seconds)
   - 5-second polling interval
   - Progress monitoring and logging
3. **Validate Completion**: Ensure job status is "completed" (not "failed")
4. **Retrieve Results**: Fetch extracted data from `/api/scan/result/{connection_id}`
5. **Validate Data Structure**: Verify presence of companies, deals, and pipelines arrays
6. **Validate Data Fields**: Check required fields in extracted records
7. **Cleanup**: Remove extraction data via `/api/scan/remove/{connection_id}`

### Test Flow 2: Extraction with Cancellation
1. **Start Extraction**: Send POST to `/api/scan/start` with real API token
2. **Brief Wait**: Allow 5 seconds for job to start processing
3. **Cancel Job**: Send POST to `/api/scan/{connection_id}/cancel`
4. **Handle Race Condition**: Accept both successful cancellation (200) and already completed (400)
5. **Verify Cancellation**: Poll status until job is cancelled or confirm completion
6. **Cleanup**: Remove extraction data

---

## 5. Common Assertions and Validations

### Response Status Codes
* **202 Accepted**: For starting new extraction jobs
* **200 OK**: For successful data retrieval, status checks, job operations
* **400 Bad Request**: For invalid input data or malformed requests
* **401 Unauthorized**: For invalid or missing API tokens
* **404 Not Found**: For non-existent job IDs or resources
* **405 Method Not Allowed**: For unsupported HTTP methods
* **409 Conflict**: For duplicate job creation attempts

### Job Status Validation
* Job status values: `pending`, `in_progress`, `completed`, `failed`, `cancelled`
* Progress percentage: 0-100 for in-progress jobs, 100 for completed jobs
* Timing fields: `start_time`, `end_time`, `extraction_duration_seconds`
* Record counts: `total_records_extracted`, `companies_extracted`, `deals_extracted`, `pipelines_extracted`

### Data Structure Validation
**Companies**: Must contain `hubspot_company_id`, `name`, `domain`, and `properties` fields
**Deals**: Must contain `hubspot_deal_id`, `dealname` (or `deal_name`), `amount`, and associated company/pipeline IDs
**Pipelines**: Must contain `pipeline_id`, `pipeline_name`, `active` status, and `stages` array with stage details

### Pagination and Statistics
* Pagination info includes `total`, `page`, `per_page`, and `pages` counts
* Statistics include `total_jobs`, `completed_jobs`, and `average_extraction_time`
* Pagination handles edge cases like negative values and oversized requests

### Error Handling
* Meaningful error messages in response JSON
* Proper handling of SQL injection attempts
* Validation of UUID format for job IDs
* Graceful handling of malformed JSON requests

---

## 6. API Endpoints Tested and Their Test Cases

| Endpoint                              | HTTP Method | Tested In                    | Description                                         |
| ------------------------------------- | ----------- | ---------------------------- | --------------------------------------------------- |
| `/api/scan/start`                     | POST        | Seeded Data & Real Tests     | Start a new extraction job with API token          |
| `/api/scan/status/{connection_id}`    | GET         | All Test Types               | Get status of extraction job                        |
| `/api/scan/result/{connection_id}`    | GET         | Seeded Data & Real Tests     | Get extraction results (companies, deals, pipelines)|
| `/api/scan/{connection_id}/cancel`    | POST        | Seeded Data & Real Tests     | Cancel a running or pending extraction job          |
| `/api/scan/remove/{connection_id}`    | DELETE      | All Test Types               | Remove extraction data and job record               |
| `/api/jobs/jobs`                      | GET         | Seeded Data Tests            | List all extraction jobs with pagination           |
| `/api/jobs/statistics`                | GET         | Seeded Data Tests            | Get extraction job statistics and metrics          |
| `/api/system/health`                  | GET         | All Test Types               | Check API health status                             |

### Endpoint-Specific Test Cases

#### `/api/scan/start`
- **Valid Request**: Token + connection_id + optional config
- **Missing Token**: Returns 400 with error message
- **Invalid Token Format**: Returns 401 unauthorized
- **Missing Connection ID**: Returns 400 with error message
- **Duplicate Connection ID**: Returns 400/409 conflict
- **Malformed Config**: Returns 400 for invalid config structure

#### Status and Result Endpoints
- **Valid UUID**: Returns job data or 404 if not found
- **Invalid UUID Format**: Returns 400 bad request
- **Non-existent Job**: Returns 404 not found
- **SQL Injection Attempts**: Properly sanitized, returns 400/404

#### Job Management Endpoints
- **Cancel Completed Job**: Returns 400 (cannot cancel completed job)
- **Cancel Pending/Running Job**: Returns 200 with success message
- **Remove Existing Job**: Returns 200 with confirmation
- **Remove Non-existent Job**: Returns 404

#### Pagination and Statistics
- **Default Pagination**: Returns first page with default page size
- **Custom Page/Size**: Honors valid pagination parameters
- **Invalid Pagination**: Handles negative values gracefully
- **Oversized Requests**: Caps at maximum reasonable values

---

## 7. Edge Case Tests

**File:** `test_edge_cases.py`

### Description

Edge case tests focus on verifying how the API handles invalid inputs, unexpected or duplicate requests, and missing data. This helps ensure the service is robust and provides meaningful error responses.

### Detailed Edge Cases Tested

#### Authentication and Authorization
| Test Case | Description | Expected Response |
|-----------|-------------|-------------------|
| `test_start_job_missing_token` | Start extraction without API token | 400 Bad Request with error message |
| `test_start_job_invalid_token_format` | Use malformed HubSpot token | 401 Unauthorized with token error |

#### Request Validation
| Test Case | Description | Expected Response |
|-----------|-------------|-------------------|
| `test_start_job_missing_connection_id` | Start extraction without connection_id | 400 Bad Request with error message |
| `test_invalid_connection_id_format` | Use non-UUID format for connection_id | 400 Bad Request or 404 Not Found |
| `test_malformed_request_body` | Send invalid JSON or wrong structure | 400 Bad Request |
| `test_malformed_config` | Send config as string instead of object | 400 Bad Request |

#### Job Management Edge Cases
| Test Case | Description | Expected Response |
|-----------|-------------|-------------------|
| `test_nonexistent_job_endpoints` | Access endpoints with valid but non-existent UUID | 404 Not Found for all endpoints |
| `test_duplicate_extraction` | Start extraction with same connection_id twice | 400 Bad Request or 409 Conflict |

#### Security and Input Validation
| Test Case | Description | Expected Response |
|-----------|-------------|-------------------|
| `test_sql_injection_attempts` | Try SQL injection in URL parameters | 400 Bad Request or 404 Not Found |
| `test_extremely_large_job_id` | Use 1000-character string as job ID | 400 Bad Request or 404 Not Found |

#### HTTP Method Validation
| Test Case | Description | Expected Response |
|-----------|-------------|-------------------|
| `test_unsupported_http_methods` | Use wrong HTTP methods on endpoints | 405 Method Not Allowed or 404 Not Found |

#### Pagination Edge Cases
| Test Case | Description | Expected Response |
|-----------|-------------|-------------------|
| `test_pagination_parameters` | Test negative page/per_page values | 200 OK with graceful handling or 400 Bad Request |
| Large per_page values | Test extremely large per_page values | 200 OK with capped values |

#### System Robustness
| Test Case | Description | Expected Response |
|-----------|-------------|-------------------|
| `test_health_endpoint_robustness` | Health check works even with DB issues | 200 OK with status information |

### Security Testing Patterns

The edge case tests include several security-focused validations:

1. **SQL Injection Prevention**: Tests common SQL injection patterns in URL parameters
2. **Input Sanitization**: Validates handling of oversized inputs and malformed data
3. **Authentication Bypass**: Ensures proper token validation
4. **Method Override**: Confirms only allowed HTTP methods work
5. **Resource Exhaustion**: Tests behavior with extremely large pagination requests

### Error Response Validation

All edge case tests verify that error responses:
- Return appropriate HTTP status codes
- Include meaningful error messages in JSON format
- Don't expose sensitive system information
- Handle edge cases gracefully without crashes

---

## 8. Test Configuration and Fixtures

### pytest Configuration (`pytest.ini`)

The test suite uses the following pytest configuration:

```ini
[pytest]
testpaths = .
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v
filterwarnings =
    ignore::DeprecationWarning
    ignore::PendingDeprecationWarning
markers =
    real_creds: Tests that require actual HubSpot credentials
```

### Shared Fixtures (`conftest.py`)

#### Core Fixtures
- **`test_connection_id`**: Generates unique UUID for test isolation
- **`hubspot_token`**: Provides real or mock HubSpot API token from environment

#### Mock Data Fixtures
- **`mock_companies`**: Sample company data with properties like name, domain, industry
- **`mock_deals`**: Sample deal data with amounts, stages, and associated companies
- **`mock_pipelines`**: Sample pipeline data with stages, probabilities, and ordering

#### Database Fixtures
- **`seeded_job`**: Creates completed extraction job with full dataset
- **`pending_job`**: Creates pending job for cancellation testing

### Environment Variables

| Variable | Purpose | Required For |
|----------|---------|--------------|
| `HUBSPOT_API_TOKEN` | Real HubSpot API access | Real extraction tests |
| Database connection settings | Test database access | All tests |

### Test Data Structure

#### Sample Company Data
```json
{
  "hubspot_company_id": "12345",
  "name": "Acme Corporation", 
  "domain": "acme.com",
  "city": "Springfield",
  "state": "IL",
  "country": "United States",
  "industry": "Technology",
  "properties": {
    "description": "Industry leader in innovative solutions",
    "website": "https://acme.com",
    "number_of_employees": "500"
  }
}
```

#### Sample Deal Data
```json
{
  "hubspot_deal_id": "deal-123",
  "dealname": "Enterprise Software Package",
  "associated_company_id": "12345",
  "pipeline_id": "pipeline-123", 
  "dealstage_id": "stage-2",
  "amount": 50000.00,
  "deal_type": "new_business",
  "deal_priority": "High"
}
```

#### Sample Pipeline Data
```json
{
  "hubspot_pipeline_id": "pipeline-123",
  "label": "Standard Sales Pipeline",
  "display_order": 1,
  "active": true,
  "stages_data": [
    {
      "stage_id": "stage-1",
      "label": "Qualification", 
      "display_order": 0,
      "probability": 0.2
    }
  ]
}
```

---

## 9. Conclusion

The outlined test workflows and edge case validations ensure comprehensive coverage of the HubSpot CompanyDeal Extraction Service API. Seeded data tests verify the API logic and database interactions efficiently, real extraction tests validate the live integration with HubSpot, and edge case tests guarantee the API’s resilience and proper error handling.

