# CompanyDeal Test Execution Guide

This document explains how to run the HubSpot CompanyDeal extraction service test suite.

## Test Types

### 1. All Tests
```powershell
pytest
```

### 2. Seeded Data Tests (Fast tests, no external API required)
```powershell
pytest tests/workflow/test_extraction_api_with_seeded_db.py
```

### 3. Edge Case Tests
```powershell
pytest tests/workflow/test_edge_cases.py
```

### 4. Real Extraction Tests (Requires HubSpot API Token)

#### Step 1: Set Environment Variable
```powershell
$env:HUBSPOT_API_TOKEN="your_token_here"
```

#### Step 2: Verify Environment Variable
```powershell
echo $env:HUBSPOT_API_TOKEN
```

#### Step 3: Run Tests
```powershell
pytest tests/workflow/test_extraction_flow_with_real_credentials.py
```

**Note**: Replace `your_token_here` with your actual HubSpot API token. The environment variable must be set in the same PowerShell session where you run the tests.

### 5. Run Tests by Type
```powershell
# Run unit tests only
pytest -m unit

# Run integration tests only
pytest -m integration

# Run edge case tests only
pytest -m edge_case

# Run performance tests only
pytest -m performance

# Run real credentials tests only
pytest -m real_creds

# Skip real credentials tests
pytest -m "not real_creds"

# Run unit and integration tests
pytest -m "unit or integration"
```

### 6. Run Tests by File
```powershell
# Run file containing integration, unit, and basic performance tests
pytest tests/workflow/test_extraction_api_with_seeded_db.py

# Run real API integration tests
pytest tests/workflow/test_extraction_flow_with_real_credentials.py

# Run edge cases and stress tests
pytest tests/workflow/test_edge_cases.py
```

### 7. Verbose Output
```powershell
pytest -v
```

### 8. Run Specific Tests
```powershell
# Edge case tests
pytest tests/workflow/test_edge_cases.py::test_start_job_missing_token

# Unit tests (now in seeded_db file)
pytest tests/workflow/test_extraction_api_with_seeded_db.py::test_company_data_validation

# Performance tests (distributed across different files)
pytest tests/workflow/test_edge_cases.py::test_concurrent_extraction_requests
pytest tests/workflow/test_extraction_api_with_seeded_db.py::test_status_polling_performance
```

## Docker Testing

The test suite can also be run using Docker containers for isolated testing environments.

### Docker Compose Test Services

```powershell
# Navigate to the project root directory
cd extractions/hubspot/CompanyDeal

# Run all test types (includes coverage reports)
docker-compose -f docker/docker-compose.test.yml up test_all

# Run specific test categories
docker-compose -f docker/docker-compose.test.yml up test_unit
docker-compose -f docker/docker-compose.test.yml up test_integration  
docker-compose -f docker/docker-compose.test.yml up test_edge_cases

# Run performance tests (separate profile)
docker-compose -f docker/docker-compose.test.yml --profile performance up test_performance

# Run real credentials tests (separate profile, requires HUBSPOT_API_TOKEN)
$env:HUBSPOT_API_TOKEN="your_token_here"
docker-compose -f docker/docker-compose.test.yml --profile real-api up test_real_credentials

# Clean up test containers and volumes
docker-compose -f docker/docker-compose.test.yml down -v
```

### Docker Test Services Description

| Service | Purpose | Command Used | Profile |
|---------|---------|--------------|---------|
| `test_all` | Run all tests with coverage | `pytest tests/ -v --cov=.` | default |
| `test_unit` | Unit tests only | `pytest -m unit -v` | default |
| `test_integration` | Integration tests only | `pytest -m integration -v` | default |
| `test_edge_cases` | Edge case tests only | `pytest -m edge_case -v` | default |
| `test_performance` | Performance tests only | `pytest -m performance -v` | performance |
| `test_real_credentials` | Real API tests only | `pytest -m real_creds -v` | real-api |

### Docker Test Services Overview

| Docker Service | Test Category | Command | Profile | Purpose |
|----------------|---------------|---------|---------|---------|
| `test_all` | All tests | `pytest tests/ -v --cov=.` | default | Complete test suite with coverage reports |
| `test_unit` | Unit tests | `pytest -m unit -v` | default | Data validation and structure testing |
| `test_integration` | Integration tests | `pytest -m integration -v` | default | API workflow with seeded data |
| `test_edge_cases` | Edge case tests | `pytest -m edge_case -v` | default | Error handling and security testing |
| `test_performance` | Performance tests | `pytest -m performance -v` | performance | Response time and concurrency testing |
| `test_real_credentials` | Real API tests | `pytest -m real_creds -v` | real-api | Live HubSpot API integration testing |

### Docker Environment Variables

The Docker test environment includes:
- `FLASK_ENV=testing`
- `DATABASE_URL` (test database)
- `REDIS_URL` (test Redis)
- `LOG_LEVEL=DEBUG` (most services) / `WARNING` (performance)
- `PYTHONPATH=/app`
- `HUBSPOT_API_TOKEN` (for real credentials tests only)

### Docker Test Database

The test environment uses an isolated PostgreSQL database:
- **Container**: `hubspot_extraction_test_db_isolated`
- **Port**: `5440` (to avoid conflicts with development database)
- **Database**: `test_db`
- **User**: `test_user`
- **Password**: `test_password`

## Response Format

### Status Response
```json
{
  "status": "completed",
  "progress": {
    "percentage": 100,
    "recordsProcessed": 150
  },
  "message": "Successfully extracted 150 records",
  "start_time": "2025-08-07T21:32:06.283042",
  "end_time": "2025-08-07T21:32:07.295215"
}
```

### Result Response
```json
{
  "data": {
    "companies": [...],
    "deals": [...],
    "pipelines": [...]
  },
  "summary": {
    "total_records": 150,
    "companies_count": 50,
    "deals_count": 75,
    "pipelines_count": 25
  }
}
```

## Environment Requirements

- Python 3.7+
- Install all dependencies: `pip install -r requirements/requirements-test.txt`
- Database connection (test database)
- HubSpot API token (for real credentials tests only)

## Test Types and Coverage

### `test_extraction_api_with_seeded_db.py`
**Integration Tests, Unit Tests, Basic Performance Tests**
- API workflow validation using seeded data
- Mock data fixture validation and data relationship testing
- Database operations and business logic validation
- Basic response time and polling performance testing

### `test_extraction_flow_with_real_credentials.py`
**Real API Integration Tests**
- End-to-end testing using real HubSpot API tokens
- Actual data extraction validation
- Job cancellation functionality testing
- Real API response time validation

### `test_edge_cases.py`
**Edge Case Tests, Stress Tests**
- Input validation and error handling
- Security testing and SQL injection protection
- Concurrent request stress testing
- Memory usage and system load testing

## Detailed Test Functionality Matrix

The following table provides a comprehensive overview of what each test category covers, which endpoints are tested, and example responses.

| Test Category | Test Files | Endpoints Tested | Functionality | Example Response |
|---------------|------------|------------------|---------------|------------------|
| **test_unit** | `test_extraction_api_with_seeded_db.py` | N/A (Data validation only) | • Company data structure validation<br>• Deal data structure validation<br>• Pipeline data structure validation<br>• Data relationships validation<br>• Mock data consistency checks | ```json<br>{<br>  "hubspot_company_id": "12345",<br>  "name": "Acme Corporation",<br>  "domain": "acme.com",<br>  "properties": {...}<br>}``` |
| **test_integration** | `test_extraction_api_with_seeded_db.py` | • `POST /scan/start`<br>• `GET /scan/status/{connection_id}`<br>• `GET /scan/result/{connection_id}`<br>• `GET /scan/stats`<br>• `GET /scan/health` | • Complete API workflow with seeded data<br>• Job lifecycle management<br>• Status tracking and progress monitoring<br>• Result retrieval and data validation<br>• Statistics and health monitoring | ```json<br>{<br>  "status": "completed",<br>  "progress": {<br>    "percentage": 100,<br>    "recordsProcessed": 3<br>  },<br>  "data": {<br>    "companies": [...],<br>    "deals": [...],<br>    "pipelines": [...]<br>  }<br>}``` |
| **test_edge_cases** | `test_edge_cases.py` | • `POST /scan/start` (error cases)<br>• `GET /scan/status/{connection_id}` (not found)<br>• `GET /scan/result/{connection_id}` (not found)<br>• `POST /scan/cancel/{connection_id}` (invalid states) | • Input validation and malformed requests<br>• Authentication error handling<br>• SQL injection protection<br>• Concurrent request stress testing<br>• Memory usage monitoring<br>• Error response structure validation | ```json<br>{<br>  "error": "Invalid request format",<br>  "message": "Missing required field: token",<br>  "status_code": 400<br>}``` |
| **test_performance** | `test_extraction_api_with_seeded_db.py`<br>`test_edge_cases.py` | • `GET /scan/status/{connection_id}` (50x polling)<br>• `GET /scan/result/{connection_id}` (large datasets)<br>• `POST /scan/cancel/{connection_id}` (timeout)<br>• `GET /scan/health`<br>• `GET /scan/stats` | • Status polling performance (< 100ms avg)<br>• Large result retrieval (< 5 seconds)<br>• Job cancellation response time (< 1 second)<br>• API endpoint response times (< 2 seconds)<br>• Concurrent request handling | ```json<br>{<br>  "performance_metrics": {<br>    "avg_response_time": "0.045s",<br>    "total_polls": 50,<br>    "total_time": "2.25s"<br>  }<br>}``` |
| **test_real_credentials** | `test_extraction_flow_with_real_credentials.py` | • `POST /scan/start` (real API)<br>• `GET /scan/status/{connection_id}` (real progress)<br>• `GET /scan/result/{connection_id}` (real data)<br>• `POST /scan/cancel/{connection_id}` (real cancellation)<br>• `DELETE /scan/remove/{connection_id}` (cleanup) | • Live HubSpot API integration<br>• Real data extraction and validation<br>• Job cancellation with actual API<br>• Data quality validation<br>• Rate limiting handling<br>• End-to-end workflow testing | ```json<br>{<br>  "status": "completed",<br>  "data": {<br>    "companies": [<br>      {<br>        "hubspot_company_id": "12345",<br>        "name": "Real Company",<br>        "domain": "realcompany.com"<br>      }<br>    ],<br>    "deals": [...],<br>    "pipelines": [...]<br>  },<br>  "summary": {<br>    "total_records": 15,<br>    "companies_count": 5,<br>    "deals_count": 8,<br>    "pipelines_count": 2<br>  }<br>}``` |

## API Endpoints Covered by Tests

- `POST /scan/start` - Start extraction job
- `GET /scan/status/{connection_id}` - Get job status  
- `GET /scan/result/{connection_id}` - Get extraction results
- `POST /scan/{connection_id}/cancel` - Cancel job
- `DELETE /scan/remove/{connection_id}` - Delete job data
- `GET /jobs/jobs` - List all jobs
- `GET /jobs/statistics` - Get job statistics
- `GET /health` - Health check

## Environment Variable Configuration for Real Credentials Tests

### Step-by-Step Instructions for Windows PowerShell:

#### 1. Open PowerShell
- Press `Win + X` and select "Windows PowerShell" or "Terminal"
- Navigate to the project directory: `cd "E:\Summer Intern\Glynac_AI\Hubspot_Main_V2\Glynac_extraction\extractions\hubspot\CompanyDeal"`

#### 2. Set HubSpot API Token
```powershell
$env:HUBSPOT_API_TOKEN="pat-na2-9a92dd2d-66bf-46f2-abe0-2b862368c823"
```

#### 3. Verify Environment Variable
```powershell
echo $env:HUBSPOT_API_TOKEN
```
**Expected output**: `pat-na2-9a92dd2d-66bf-46f2-abe0-2b862368c823`

#### 4. Run Real Credentials Tests
```powershell
# Option 1: Run directly with pytest
pytest tests/workflow/test_extraction_flow_with_real_credentials.py -v

# Option 2: Run with Docker
docker-compose -f docker/docker-compose.test.yml --profile real-api up test_real_credentials
```

#### 5. Clear Environment Variable (Optional)
```powershell
Remove-Item Env:HUBSPOT_API_TOKEN
```

### Important Notes:
- **Only HUBSPOT_API_TOKEN is required** - CompanyDeal project does not use Redis or other external services
- The environment variable must be set in the same PowerShell session where you run the tests
- If you close PowerShell, you'll need to set the environment variable again
- For Docker tests, the environment variable is automatically passed to the container
- Replace the token value with your actual HubSpot API token
- Database connection is automatically configured for testing environment

## Notes

1. Real credentials tests require a valid HubSpot API token
2. Tests automatically clean up created data
3. Concurrent test execution is safe, each test uses unique connection IDs
4. Docker test environment provides complete isolation from development environment
5. Performance and real credentials tests use separate Docker profiles to avoid accidental execution
6. All API endpoints use the `/scan/` prefix (not `/api/scan/`)
7. Test database runs on port `5440` to avoid conflicts with development database
8. All commands are designed for Windows PowerShell environment

## Test Response Examples

### Successful Job Start Response
```json
{
  "job_id": "27c9b107-2e57-469f-9a09-b3db9fd2d959",
  "connection_id": "27c9b107-2e57-469f-9a09-b3db9fd2d959",
  "status": "pending",
  "message": "Extraction job started successfully"
}
```

### Job Status Response (In Progress)
```json
{
  "status": "in_progress",
  "progress": {
    "percentage": 45,
    "recordsProcessed": 67
  },
  "message": "Extracting companies and deals...",
  "start_time": "2025-08-07T21:32:06.283042",
  "end_time": null
}
```

### Job Status Response (Completed)
```json
{
  "status": "completed",
  "progress": {
    "percentage": 100,
    "recordsProcessed": 150
  },
  "message": "Successfully extracted 150 records",
  "start_time": "2025-08-07T21:32:06.283042",
  "end_time": "2025-08-07T21:32:07.295215",
  "metadata": {
    "companiesExtracted": 50,
    "dealsExtracted": 75,
    "pipelinesExtracted": 25
  }
}
```

### Extraction Results Response
```json
{
  "status": "completed",
  "data": {
    "companies": [
      {
        "hubspot_company_id": "12345",
        "name": "Acme Corporation",
        "domain": "acme.com",
        "industry": "Technology",
        "city": "San Francisco",
        "state": "CA",
        "country": "United States",
        "annual_revenue": 1000000,
        "number_of_employees": 50,
        "properties": {
          "lifecyclestage": "customer",
          "createdate": "2023-01-15T10:30:00Z"
        }
      }
    ],
    "deals": [
      {
        "hubspot_deal_id": "deal-123",
        "dealname": "Enterprise Software Package",
        "amount": 50000.00,
        "pipeline_id": "pipeline-123",
        "dealstage_id": "stage-456",
        "associated_company_id": "12345",
        "company_name": "Acme Corporation",
        "closedate": "2025-12-31T23:59:59Z",
        "properties": {
          "dealstage": "closedwon",
          "createdate": "2024-06-15T14:20:00Z"
        }
      }
    ],
    "pipelines": [
      {
        "hubspot_pipeline_id": "pipeline-123",
        "label": "Standard Sales Pipeline",
        "active": true,
        "display_order": 1,
        "stages_data": [
          {
            "stage_id": "stage-456",
            "label": "Closed Won",
            "display_order": 6,
            "probability": 1.0
          }
        ],
        "properties": {
          "pipeline_type": "standard",
          "createdate": "2023-01-01T00:00:00Z"
        }
      }
    ]
  },
  "summary": {
    "total_records": 150,
    "companies_count": 50,
    "deals_count": 75,
    "pipelines_count": 25
  }
}
```

### Error Response Examples

#### Authentication Error
```json
{
  "error": "Authentication failed",
  "message": "Invalid HubSpot API token provided",
  "status_code": 401
}
```

#### Job Not Found
```json
{
  "error": "Job not found",
  "message": "No extraction job found with connection_id: invalid-id",
  "status_code": 404
}
```

#### Invalid Request Format
```json
{
  "error": "Invalid request format",
  "message": "Missing required field: token",
  "status_code": 400
}
```

### Health Check Response
```json
{
  "status": "healthy",
  "timestamp": "2025-08-07T21:32:06.283042",
  "version": "1.0.0",
  "database": "connected",
  "thread_pool": {
    "active_threads": 2,
    "max_threads": 10,
    "queue_size": 0
  }
}
```

### Statistics Response
```json
{
  "extractions": {
    "total_scans": 150,
    "successful_scans": 142,
    "failed_scans": 8,
    "pending_scans": 0,
    "running_scans": 0
  },
  "performance": {
    "avg_extraction_time": 45.2,
    "fastest_extraction": 12.5,
    "slowest_extraction": 180.3,
    "total_records_extracted": 15000
  },
  "data_summary": {
    "total_companies": 5000,
    "total_deals": 7500,
    "total_pipelines": 2500
  }
}
```
