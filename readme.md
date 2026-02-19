# HubSpot Extraction Service

A modern, enterprise-grade HubSpot data extraction service built with Flask-RESTX, SQLAlchemy, and PostgreSQL. Features ThreadPoolExecutor-based concurrent processing, interactive API documentation, real-time progress tracking, and comprehensive observability.

## 🌟 Features

- 🚀 **ThreadPoolExecutor-Based Processing**: Production-ready concurrent extraction using Python's standard library
- 📊 **Complete CRM Data**: Extract companies, deals, pipelines, and deal stage history with full timeline tracking
- 🔄 **Sales Analytics**: Track deal progression, stage durations, sales velocity, and bottleneck identification
- 🎯 **Scan-Based API**: Modern REST API using unique scan IDs for simple client integration
- 🏗️ **Layered Architecture**: Clean separation of API, Service, and Data layers with proper dependency injection
- 📈 **Real-Time Monitoring**: Health checks, thread pool monitoring, and structured logging
- 🔒 **Robust Error Handling**: Custom exceptions with retry logic, timeout protection, and graceful degradation
- 📚 **Interactive API Documentation**: Full Swagger/OpenAPI documentation with live testing at `/docs/`
- 🐳 **Docker Support**: Multi-environment Docker configurations with production-ready setup
- ⚡ **Performance Optimized**: Connection pooling, batch processing, strategic indexing, and concurrency limiting
- 🧪 **Production Ready**: Comprehensive error handling, graceful shutdown, and automatic resource cleanup
- 📦 **CSV Export**: Built-in CSV download functionality for extracted data

## 📊 Data Extraction Capabilities

### What Gets Extracted

**🏢 Companies**
- Organization details (name, domain, industry, description)
- Location data (city, state, country, timezone)
- Business metrics (annual revenue, employee count)
- Complete HubSpot properties as flexible JSON
- Creation and modification timestamps

**💰 Deals**
- Sales opportunities with amounts and currencies
- Current pipeline stages and probabilities
- Associated companies and relationships
- Close dates and deal priorities
- Deal types and custom properties

**📋 Pipelines**
- Sales process templates and workflows
- Stage definitions with close probabilities
- Pipeline configurations and display orders
- Active/inactive pipeline management

**⏰ Deal Stage History** (Advanced Analytics)
- Complete timeline of all stage changes
- Duration spent in each stage (days/hours)
- User attribution for stage changes
- Stage transition patterns and velocity
- Historical trend analysis

### 📈 Analytics Capabilities

- **Sales Cycle Analysis**: Average time from first stage to close
- **Stage Performance**: Identify bottlenecks and conversion rates  
- **Sales Velocity**: Track deal progression speed and acceleration
- **Pipeline Health**: Monitor deals stuck in stages or regressing
- **Historical Trends**: Compare performance over time periods
- **User Activity**: Track who's moving deals and how fast
- **Conversion Funnels**: Stage-to-stage conversion analysis

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- PostgreSQL 13+ (or SQLite for development)
- HubSpot API Token (Private App with `crm.objects.companies.read`, `crm.objects.deals.read`, `crm.objects.pipelines.read` scopes)

### Local Development

1. **Clone and Setup**
   ```bash
   git clone <repository-url>
   cd hubspot-extraction-service
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Environment Configuration**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration:
   # DATABASE_URL=postgresql://user:password@localhost:5432/hubspot_db
   # LOG_LEVEL=INFO
   # MAX_WORKER_THREADS=5
   ```

3. **Database Setup**
   ```bash
   # Initialize database tables
   python -c "from models.database import init_db; init_db()"
   ```

4. **Run the Service**
   ```bash
   python app.py
   ```

5. **Access Documentation**
   - **Interactive API Documentation**: http://localhost:4045/docs/
   - **OpenAPI Specification**: http://localhost:4045/swagger.json
   - **Health Check**: http://localhost:4045/scan/health
   - **Service Statistics**: http://localhost:4045/scan/stats

**Note**: Development environment uses port 4045. Production environment uses port 3012.

### 🐳 Docker Development

```bash
# Start all services with hot reload
docker-compose -f docker/docker-compose.dev.yml up --build

# Run tests
docker-compose -f docker/docker-compose.dev.yml run --rm test

# View logs
docker-compose -f docker/docker-compose.dev.yml logs -f app

# Access shell
docker-compose -f docker/docker-compose.dev.yml exec app bash
```

## 🔗 API Usage

### Modern Scan-Based Workflow

The API uses unique `scanId` for all operations with comprehensive configuration options:

```javascript
// 1. Start extraction with comprehensive configuration
const response = await fetch('/scan/start', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        config: {
            scanId: 'company-deals-extraction-2024-001',
            type: ['deals', 'companies'],
            auth: {
                accessToken: 'pat-na1-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx'
            },
            extraction: {
                extractDeals: true,
                extractCompanies: true,
                batchSize: 100,
                maxRecords: 10000
            },
            filters: {
                dealStage: ['negotiation', 'closed-won'],
                amountMin: 10000,
                amountMax: 1000000,
                createdAfter: '2024-01-01',
                createdBefore: '2024-12-31',
                pipelineId: 'default'
            },
            options: {
                includeCustomProperties: true,
                includeAssociations: true,
                includeStageHistory: true
            }
        }
    })
});

const { scanId, status, message, startedAt, metadata } = await response.json();

// 2. Monitor real-time progress
const statusResponse = await fetch(`/scan/status/${scanId}`);
const statusData = await statusResponse.json();
console.log(`Progress: ${statusData.progress.percentage}%`);
console.log(`Current: ${statusData.progress.currentOperation}`);

// 3. Get paginated results when completed
const resultsResponse = await fetch(`/scan/result/${scanId}?limit=100&offset=0`);
const extractionData = await resultsResponse.json();

// 4. Download as CSV
const csvResponse = await fetch(`/scan/download/${scanId}`);
const csvBlob = await csvResponse.blob();
const csvUrl = URL.createObjectURL(csvBlob);

// 5. Cancel if needed
await fetch(`/scan/cancel/${scanId}`, { method: 'POST' });

// 6. Clean up when done
await fetch(`/scan/remove/${scanId}`, { method: 'DELETE' });
```

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/scan/start` | POST | Start extraction scan with comprehensive config |
| `/scan/status/{scanId}` | GET | Get real-time scan status and progress |
| `/scan/result/{scanId}` | GET | Get extraction results with pagination |
| `/scan/download/{scanId}` | GET | Download results as CSV file |
| `/scan/cancel/{scanId}` | POST | Cancel running scan |
| `/scan/remove/{scanId}` | DELETE | Remove scan and all associated data |
| `/scan/stats` | GET | Get comprehensive service statistics |
| `/scan/health` | GET | Service health check with system metrics |

### Enhanced Response Structure

```json
{
  "scanId": "company-deals-extraction-2024-001",
  "status": "completed",
  "total_records": 2500,
  "extraction_summary": {
    "companies_count": 150,
    "deals_count": 720,
    "pipelines_count": 5,
    "custom_properties": 85,
    "associations": 1200,
    "avg_processing_time_ms": 1250,
    "started_at": "2024-01-15T10:30:00.000Z",
    "completed_at": "2024-01-15T10:38:30.000Z",
    "duration_seconds": 510
  },
  "data": {
    "companies": [
      {
        "id": "company_123",
        "name": "Acme Corporation",
        "domain": "acme.com",
        "industry": "Technology",
        "annual_revenue": 5000000,
        "employee_count": 150,
        "created_date": "2024-01-10T14:30:00.000Z",
        "custom_properties": {
          "customer_tier": "Enterprise",
          "renewal_date": "2024-12-31"
        }
      }
    ],
    "deals": [
      {
        "id": "deal_456",
        "name": "Enterprise Software License",
        "amount": 50000,
        "currency": "USD",
        "stage": "negotiation",
        "probability": 75,
        "close_date": "2024-02-15",
        "owner_name": "John Smith",
        "company_name": "Acme Corporation",
        "pipeline_name": "Sales Pipeline",
        "stage_history": [
          {
            "stage": "qualification",
            "entered_at": "2024-01-05T09:30:00.000Z",
            "duration_days": 3
          },
          {
            "stage": "negotiation",
            "entered_at": "2024-01-08T14:15:00.000Z",
            "duration_days": 7,
            "is_current": true
          }
        ]
      }
    ],
    "pipelines": [
      {
        "id": "sales-pipeline",
        "label": "Sales Pipeline",
        "type": "deals",
        "active": true,
        "stages": [
          {
            "id": "qualification",
            "label": "Qualification",
            "probability": 10,
            "display_order": 1
          },
          {
            "id": "negotiation",
            "label": "Negotiation",
            "probability": 75,
            "display_order": 2
          }
        ]
      }
    ]
  },
  "metadata": {
    "extractionTypes": ["deals", "companies"],
    "filtersApplied": {
      "dealStage": ["negotiation", "closed-won"],
      "amountMin": 10000,
      "dateRange": "2024-01-01 to 2024-12-31"
    },
    "customPropertiesIncluded": true,
    "associationsIncluded": true,
    "pagination": {
      "offset": 0,
      "limit": 100,
      "total_records": 2500
    }
  }
}
```

## 🏗️ Architecture

### Service Layers
```
┌─────────────────────────────────────────────────────────┐
│                    API Layer                            │
│  Flask-RESTX Routes, Swagger UI, OpenAPI 3.0            │
├─────────────────────────────────────────────────────────┤
│                 Service Layer                           │
│  Business Logic, ThreadPoolExecutor, Job Management     │
├─────────────────────────────────────────────────────────┤
│                 Data Layer                              │
│  SQLAlchemy Models, Database Operations, Serialization  │
├─────────────────────────────────────────────────────────┤
│               External Services                         │
│  HubSpot API Client, Rate Limiting, Error Handling      │
└─────────────────────────────────────────────────────────┘
```

### Database Schema

**Core Tables:**
- `extraction_jobs` - Job lifecycle and metadata tracking
- `hubspot_companies` - Company records with business data
- `hubspot_deals` - Deal/opportunity records with amounts
- `hubspot_deal_pipelines` - Sales process definitions
- `hubspot_deal_stage_history` - Complete stage change timeline

**Key Design Features:**
- Cascading deletes for data consistency
- Strategic indexes for query performance optimization
- JSONB columns for flexible HubSpot properties storage
- Proper foreign key relationships with referential integrity
- Scan-based data isolation

### Threading Model

- **🎯 ThreadPoolExecutor**: Python's standard library thread pool for robust concurrent processing
- **⚡ Worker Threads**: Configurable worker pool (default: 5 workers) for extraction jobs
- **🔄 Future-Based Control**: Built-in job cancellation and status tracking using Python Futures
- **🧹 Automatic Cleanup**: Dead thread detection and automatic resource cleanup
- **📊 Real-Time Monitoring**: Thread pool statistics and active job tracking

## 🧪 Testing

```bash
# Run all tests with coverage
pytest --cov=. --cov-report=html --cov-report=term

# Run tests by category (using pytest markers)
pytest -m integration -v            # Integration tests with HubSpot API
pytest -m edge_case -v              # Edge case and error handling tests
pytest -m performance -v            # Performance and concurrency tests
pytest -m real_creds -v             # Real HubSpot API tests (requires token)

# Run tests by file
pytest tests/workflow/test_extraction_api_with_seeded_db.py -v    # Seeded data tests
pytest tests/workflow/test_extraction_flow_with_real_credentials.py -v  # Real API tests
pytest tests/workflow/test_edge_cases.py -v                       # Edge case tests

# Skip real credentials tests (for CI/CD)
pytest -m "not real_creds" -v

# Real extraction tests (requires HUBSPOT_API_TOKEN environment variable)
HUBSPOT_API_TOKEN=your_token_here pytest -m real_creds -v
```

### Docker Testing

```bash
# Run all tests in Docker environment
docker-compose -f docker/docker-compose.test.yml up test_all

# Run specific test categories in Docker
docker-compose -f docker/docker-compose.test.yml up test_integration
docker-compose -f docker/docker-compose.test.yml up test_edge_cases

# Run performance tests (separate profile)
docker-compose -f docker/docker-compose.test.yml --profile performance up test_performance

# Run real credentials tests (requires HUBSPOT_API_TOKEN)
export HUBSPOT_API_TOKEN=your_token_here
docker-compose -f docker/docker-compose.test.yml --profile real-api up test_real_credentials

### Docker Test Services Overview

| Docker Service | Test Category | Command | Profile | Purpose |
|----------------|---------------|---------|---------|---------|
| `test_all` | All tests | `pytest tests/ -v --cov=.` | default | Complete test suite with coverage reports |
| `test_unit` | Unit tests | `pytest -m unit -v` | default | Data validation and structure testing |
| `test_integration` | Integration tests | `pytest -m integration -v` | default | API workflow with seeded data |
| `test_edge_cases` | Edge case tests | `pytest -m edge_case -v` | default | Error handling and security testing |
| `test_performance` | Performance tests | `pytest -m performance -v` | performance | Response time and concurrency testing |
| `test_real_credentials` | Real API tests | `pytest -m real_creds -v` | real-api | Live HubSpot API integration testing |
```

### Test Coverage Areas

**Integration Testing** (pytest marker: `integration`)
- ✅ End-to-end API workflow with seeded database data
- ✅ Real HubSpot API integration with live credentials
- ✅ Database operations and job lifecycle management
- ✅ Job status tracking and result retrieval

**Edge Case Testing** (pytest marker: `edge_case`)
- ✅ Input validation and malformed request handling
- ✅ Authentication and authorization error responses
- ✅ Security testing and SQL injection protection
- ✅ Error response structure validation

**Performance Testing** (pytest marker: `performance`)
- ✅ Concurrent extraction request handling
- ✅ Status polling performance and timeout management
- ✅ Memory usage monitoring under load
- ✅ API endpoint response time validation

**Real Credentials Testing** (pytest marker: `real_creds`)
- ✅ Live HubSpot API data extraction and validation
- ✅ Job cancellation with real API interactions
- ✅ Data quality validation from actual HubSpot accounts
- ✅ Rate limiting and API error handling

### Detailed Test Functionality Matrix

The following table provides a comprehensive overview of what each test category covers, which endpoints are tested, and example responses.

| Test Category | Test Files | Endpoints Tested | Functionality | Example Response |
|---------------|------------|------------------|---------------|------------------|
| **test_unit** | `test_extraction_api_with_seeded_db.py` | N/A (Data validation only) | • Company data structure validation<br>• Deal data structure validation<br>• Pipeline data structure validation<br>• Data relationships validation<br>• Mock data consistency checks | ```json<br>{<br>  "hubspot_company_id": "12345",<br>  "name": "Acme Corporation",<br>  "domain": "acme.com",<br>  "properties": {...}<br>}``` |
| **test_integration** | `test_extraction_api_with_seeded_db.py` | • `POST /scan/start`<br>• `GET /scan/status/{connection_id}`<br>• `GET /scan/result/{connection_id}`<br>• `GET /scan/stats`<br>• `GET /scan/health` | • Complete API workflow with seeded data<br>• Job lifecycle management<br>• Status tracking and progress monitoring<br>• Result retrieval and data validation<br>• Statistics and health monitoring | ```json<br>{<br>  "status": "completed",<br>  "progress": {<br>    "percentage": 100,<br>    "recordsProcessed": 3<br>  },<br>  "data": {<br>    "companies": [...],<br>    "deals": [...],<br>    "pipelines": [...]<br>  }<br>}``` |
| **test_edge_cases** | `test_edge_cases.py` | • `POST /scan/start` (error cases)<br>• `GET /scan/status/{connection_id}` (not found)<br>• `GET /scan/result/{connection_id}` (not found)<br>• `POST /scan/cancel/{connection_id}` (invalid states) | • Input validation and malformed requests<br>• Authentication error handling<br>• SQL injection protection<br>• Concurrent request stress testing<br>• Memory usage monitoring<br>• Error response structure validation | ```json<br>{<br>  "error": "Invalid request format",<br>  "message": "Missing required field: token",<br>  "status_code": 400<br>}``` |
| **test_performance** | `test_extraction_api_with_seeded_db.py`<br>`test_edge_cases.py` | • `GET /scan/status/{connection_id}` (50x polling)<br>• `GET /scan/result/{connection_id}` (large datasets)<br>• `POST /scan/cancel/{connection_id}` (timeout)<br>• `GET /scan/health`<br>• `GET /scan/stats` | • Status polling performance (< 100ms avg)<br>• Large result retrieval (< 5 seconds)<br>• Job cancellation response time (< 1 second)<br>• API endpoint response times (< 2 seconds)<br>• Concurrent request handling | ```json<br>{<br>  "performance_metrics": {<br>    "avg_response_time": "0.045s",<br>    "total_polls": 50,<br>    "total_time": "2.25s"<br>  }<br>}``` |
| **test_real_credentials** | `test_extraction_flow_with_real_credentials.py` | • `POST /scan/start` (real API)<br>• `GET /scan/status/{connection_id}` (real progress)<br>• `GET /scan/result/{connection_id}` (real data)<br>• `POST /scan/cancel/{connection_id}` (real cancellation)<br>• `DELETE /scan/remove/{connection_id}` (cleanup) | • Live HubSpot API integration<br>• Real data extraction and validation<br>• Job cancellation with actual API<br>• Data quality validation<br>• Rate limiting handling<br>• End-to-end workflow testing | ```json<br>{<br>  "status": "completed",<br>  "data": {<br>    "companies": [<br>      {<br>        "hubspot_company_id": "12345",<br>        "name": "Real Company",<br>        "domain": "realcompany.com"<br>      }<br>    ],<br>    "deals": [...],<br>    "pipelines": [...]<br>  },<br>  "summary": {<br>    "total_records": 15,<br>    "companies_count": 5,<br>    "deals_count": 8,<br>    "pipelines_count": 2<br>  }<br>}``` |

## 🚀 Deployment

### Production Docker

```bash
# Build and deploy with production optimizations
docker-compose -f docker/docker-compose.prod.yml up --build -d

# View logs with timestamps
docker-compose -f docker/docker-compose.prod.yml logs -f --timestamps

# Scale the application horizontally
docker-compose -f docker/docker-compose.prod.yml up --scale app=3

# Health check
curl http://localhost:4045/scan/health

# Monitor service statistics
curl http://localhost:4045/scan/stats
```

### Environment Variables

**Database Configuration**
```bash
DATABASE_URL=postgresql://username:password@host:port/database
```

**Performance Tuning**
```bash
MAX_WORKER_THREADS=5              # ThreadPoolExecutor worker count
BATCH_SIZE=100                    # Records per API batch
REQUEST_TIMEOUT=30                # General request timeout (seconds)
HUBSPOT_API_TIMEOUT=30           # HubSpot API timeout (seconds)
```

**HubSpot API Configuration**
```bash
HUBSPOT_API_BASE_URL=https://api.hubapi.com
COMPANY_PROPERTIES=name,domain,industry,city,state,country,annualrevenue,numberofemployees
DEAL_PROPERTIES=dealname,amount,pipeline,dealstage,closedate,createdate
```

**Logging and Monitoring**
```bash
LOG_LEVEL=INFO                   # DEBUG, INFO, WARNING, ERROR
PORT=4045                       # Service port (development: 4045, production: 3012)
```

### Health Monitoring

The service provides comprehensive health monitoring:

- **`/scan/health`** - Overall service health with database, thread pool, and system metrics
- **`/scan/stats`** - Detailed service statistics including performance metrics
- **Structured Logging** - Clean, minimal logging for production environments
- **HTTP Status Codes** - Proper status codes for monitoring systems integration

## 🔒 Security

- ✅ **Input Validation**: Comprehensive Marshmallow schemas for all API inputs
- ✅ **HubSpot API Token Validation**: Real-time token verification with format checking
- ✅ **No Credential Storage**: Tokens passed per-request, never stored or logged
- ✅ **SQL Injection Protection**: SQLAlchemy ORM with parameterized queries
- ✅ **Rate Limiting Infrastructure**: Built-in HubSpot API rate limiting with backoff
- ✅ **Error Information Disclosure Prevention**: Sanitized error responses
- ✅ **Scan Isolation**: Data isolated per scanId for multi-tenant usage
- ✅ **Resource Limits**: Configurable concurrency limits to prevent DoS
- ✅ **CORS Support**: Configurable CORS for secure cross-origin requests

## 📊 Sales Analytics Examples

### Stage Duration Analysis
```sql
-- Average time spent in each stage across all deals
SELECT 
    stage_label,
    AVG(duration_days) as avg_days,
    COUNT(*) as deal_count
FROM hubspot_deal_stage_history 
WHERE duration_days IS NOT NULL
GROUP BY stage_label
ORDER BY avg_days DESC;
```

### Bottleneck Identification
```sql
-- Find deals stuck in stages for more than 30 days
SELECT 
    h.hubspot_deal_id,
    d.dealname,
    h.stage_label,
    h.duration_days,
    h.change_date
FROM hubspot_deal_stage_history h
JOIN hubspot_deals d ON h.hubspot_deal_id = d.hubspot_deal_id
WHERE h.is_current_stage = true 
  AND h.duration_days > 30
ORDER BY h.duration_days DESC;
```

### Conversion Rate Analysis
```sql
-- Stage-to-stage conversion rates
SELECT 
    stage_label,
    COUNT(*) as entered_stage,
    COUNT(CASE WHEN is_current_stage = false THEN 1 END) as exited_stage,
    ROUND(
        COUNT(CASE WHEN is_current_stage = false THEN 1 END) * 100.0 / COUNT(*), 
        2
    ) as conversion_rate_percent
FROM hubspot_deal_stage_history 
GROUP BY stage_label
ORDER BY conversion_rate_percent DESC;
```

### Sales Velocity Tracking
```sql
-- Deals with fastest progression through pipeline
SELECT 
    d.dealname,
    d.amount,
    MIN(h.change_date) as first_stage_date,
    MAX(h.change_date) as current_stage_date,
    COUNT(h.id) as total_stage_changes,
    EXTRACT(DAY FROM MAX(h.change_date) - MIN(h.change_date)) as total_cycle_days
FROM hubspot_deals d
JOIN hubspot_deal_stage_history h ON d.hubspot_deal_id = h.hubspot_deal_id
GROUP BY d.id, d.dealname, d.amount
HAVING COUNT(h.id) > 1
ORDER BY total_cycle_days ASC
LIMIT 10;
```

## 🔧 Troubleshooting

### Common Issues and Solutions

**1. ThreadPoolExecutor Shutdown Issues**
- ✅ **Fixed**: Python version compatibility for shutdown timeout parameter
- ✅ **Auto-cleanup**: Graceful shutdown with proper thread termination

**2. Concurrent Request Deadlocks**  
- ✅ **Fixed**: ThreadPoolExecutor with timeout-based locking
- ✅ **Concurrency Limiting**: Maximum concurrent extractions enforced

**3. JSON Serialization Errors**
- ✅ **Fixed**: Automatic datetime and Decimal serialization in base models
- ✅ **Recursive Handling**: Deep serialization of nested objects

**4. Memory Leaks from Stale State**
- ✅ **Fixed**: Comprehensive state cleanup on job completion
- ✅ **Force Cleanup**: Emergency cleanup functionality for stuck jobs

**5. HubSpot API Rate Limiting**
- ✅ **Built-in Handling**: Automatic retry with exponential backoff
- ✅ **Respectful Delays**: Configurable delays between API requests

### Monitoring and Debugging

```bash
# Check overall service health
curl http://localhost:4045/scan/health

# Get comprehensive service statistics
curl http://localhost:4045/scan/stats

# Check specific scan status
curl http://localhost:4045/scan/status/your-scan-id

# Download results as CSV
curl http://localhost:4045/scan/download/your-scan-id -o results.csv

# Check logs for detailed debugging
tail -f hubspot_extraction.log | grep ERROR
```

## 🎯 Performance Optimization

### Recommended Production Settings

```bash
# Environment variables for optimal performance
MAX_WORKER_THREADS=10            # Adjust based on CPU cores
BATCH_SIZE=100                   # Optimal for HubSpot API
REQUEST_TIMEOUT=60              # Longer timeout for large datasets
HUBSPOT_API_TIMEOUT=45          # Allow for API response time
LOG_LEVEL=WARNING               # Reduce log volume in production

# Database connection pool settings
DATABASE_URL=postgresql://user:pass@host:5432/db?pool_size=20&max_overflow=30
```

### Performance Monitoring

- **Thread Pool Metrics**: Monitor active/pending threads via `/stats`
- **Database Performance**: Monitor connection pool usage and query performance
- **HubSpot API Limits**: Track rate limit usage and response times
- **Memory Usage**: Monitor memory consumption for large extractions
- **Extraction Durations**: Track average and peak extraction times

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Add comprehensive tests for new functionality
4. Ensure all tests pass (`pytest --cov=.`)
5. Update documentation if needed
6. Submit a pull request with detailed description

### Development Guidelines
- Follow PEP 8 style guidelines
- Add type hints for all functions
- Include docstrings for public methods
- Write tests for new features
- Update README for significant changes
- Test with both PostgreSQL and SQLite

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Flask-RESTX** for excellent API documentation and interactive UI
- **SQLAlchemy** for robust ORM capabilities and database abstraction
- **ThreadPoolExecutor** for production-ready concurrent processing
- **HubSpot** for comprehensive CRM API and developer resources
- **PostgreSQL** for reliable data storage and advanced features
- **OpenAPI/Swagger** for standardized API documentation

---

**Built with ❤️ for sales teams who need reliable, scalable HubSpot data extraction and analytics.**

## 📚 Additional Resources

- [HubSpot API Documentation](https://developers.hubspot.com/docs/api/overview)
- [Flask-RESTX Documentation](https://flask-restx.readthedocs.io/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [ThreadPoolExecutor Documentation](https://docs.python.org/3/library/concurrent.futures.html#threadpoolexecutor)
- [OpenAPI Specification](https://swagger.io/specification/)

For technical support and feature requests, please open an issue on the repository.

## 📋 Test Response Examples

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