# HubSpot Extraction Service - API Documentation

## Overview.

The HubSpot Extraction Service provides a modern REST API built with Flask-RESTX for extracting and managing company deals data from HubSpot CRM platform. Features interactive documentation, real-time progress tracking, and comprehensive error handling.

**Base URLs:**
- Production: `http://localhost:4045`
- Development: `http://localhost:4045`
- **Interactive Documentation**: `http://localhost:4045/docs/` (Swagger UI)
- **OpenAPI Specification**: `http://localhost:4045/swagger.json`

**Service Information:**
- Service: HubSpot Extraction Service.
- Version: 2.0.0
- API Framework: Flask-RESTX with OpenAPI 3.0
- Environment: Production/Development

## Key Features

- **Interactive Documentation**: Full Swagger UI with try-it-out functionality
- **Real-time Progress Tracking**: Live progress updates with percentage completion
- **Comprehensive Validation**: Automatic request/response validation
- **Standardized Error Handling**: Consistent error responses with detailed context
- **Multi-format Support**: JSON responses and CSV downloads
- **Advanced Filtering**: Flexible data filtering and extraction options.

## Authentication

### HubSpot Token Authentication
Each extraction request requires a valid HubSpot Private App Access Token:
- **Token Type**: HubSpot Private App Access Token
- **Format**: `pat-na1-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`
- **Required Scopes**: 
  - `crm.objects.deals.read` - Read deal data
  - `crm.objects.companies.read` - Read company data
  - `crm.objects.pipelines.read` - Read pipeline configurations

## Interactive Documentation

### Swagger UI Features

Access the comprehensive interactive documentation at `http://localhost:4045/docs/`:

- **Try It Out**: Execute API calls directly from the browser
- **Request Examples**: Complete request/response examples for all endpoints
- **Schema Validation**: Real-time validation of API requests
- **Model Definitions**: Clear schemas for all request/response objects
- **Error Documentation**: Detailed error response examples
- **Authentication Testing**: Test HubSpot token authentication

### OpenAPI Specification

Machine-readable API specification available at `http://localhost:4045/swagger.json`:
- **Format**: OpenAPI 3.0.0
- **Content**: Complete API schema with all endpoints, models, and examples
- **Usage**: Import into API testing tools like Postman, Insomnia, or custom applications

## API Endpoints

### Base URL Structure

All endpoints are served from the base URL with the following structure:
- **Health & System**: `http://localhost:4045/health`, `http://localhost:4045/scan/stats`
- **Extraction Operations**: `http://localhost:4045/scan/*`
- **Interactive Docs**: `http://localhost:4045/docs/`

---

# Core Extraction Endpoints

## Start HubSpot Extraction

### `POST /scan/start`

Initiate a new HubSpot company deals extraction scan with comprehensive configuration options.

**Request Body:**
```json
{
  "config": {
    "scanId": "company-deals-extraction-2024-001",
    "type": ["deals", "companies"],
    "auth": {
      "accessToken": "pat-na1-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
    },
    "extraction": {
      "extractDeals": true,
      "extractCompanies": true,
      "batchSize": 100,
      "maxRecords": 10000
    },
    "filters": {
      "dealStage": ["negotiation", "closed-won"],
      "amountMin": 10000,
      "amountMax": 1000000,
      "createdAfter": "2024-01-01",
      "createdBefore": "2024-12-31",
      "pipelineId": "default",
      "priority": ["HIGH", "MEDIUM"],
      "category": ["SUPPORT_REQUEST", "SALES_INQUIRY"]
    },
    "options": {
      "includeCustomProperties": true,
      "includeAssociations": true,
      "includeStageHistory": true
    }
  }
}
```

**Response (202 Accepted):**
```json
{
  "scanId": "company-deals-extraction-2024-001",
  "status": "started",
  "message": "Company deals extraction scan started successfully",
  "startedAt": "2024-01-15T10:30:00.000Z",
  "metadata": {
    "totalEstimatedRecords": 2500,
    "estimatedDuration": "5-10 minutes",
    "extractionTypes": ["deals", "companies"]
  }
}
```

**Error Responses:**
- `400` - Validation failed or invalid configuration
- `401` - Invalid HubSpot API token
- `409` - Active extraction already exists with same scanId
- `500` - Internal server error

---

## Check Extraction Status

### `GET /scan/status/{scanId}`

Get real-time status and progress information for a running extraction.

**Parameters:**
- `scanId` (string, required) - Unique scan identifier

**Response:**
```json
{
  "scanId": "company-deals-extraction-2024-001",
  "status": "running",
  "progress": {
    "percentage": 65,
    "recordsProcessed": 1625,
    "recordsTotal": 2500,
    "currentOperation": "Extracting deals batch 8 of 12"
  },
  "startedAt": "2024-01-15T10:30:00.000Z",
  "estimatedCompletion": "2024-01-15T10:38:00.000Z",
  "message": "Processing deals from sales pipeline...",
  "metadata": {
    "companiesExtracted": 150,
    "dealsExtracted": 720,
    "pipelinesExtracted": 5,
    "batchesCompleted": 8,
    "batchesTotal": 12
  },
  "error": null
}
```

**Status Values:**
- `started` - Scan has been initiated and queued
- `running` - Extraction is actively processing data
- `completed` - Extraction finished successfully
- `failed` - Extraction encountered an error
- `cancelled` - Extraction was cancelled by user

**Error Response (404 - Not Found):**
```json
{
  "error": "Scan Not Found",
  "message": "Scan company-deals-extraction-2024-001 not found",
  "details": null,
  "timestamp": "2024-01-15T10:30:00.000Z"
}
```

---

## Get Extraction Results

### `GET /scan/result/{scanId}`

Retrieve the complete results of a finished extraction with detailed data breakdown.

**Parameters:**
- `scanId` (string, required) - Unique scan identifier

**Response:**
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
        "last_activity": "2024-01-14T16:45:00.000Z",
        "hubspot_owner": "john.smith@company.com",
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
        "created_date": "2024-01-05T09:30:00.000Z",
        "last_modified": "2024-01-14T17:20:00.000Z",
        "stage_history": [
          {
            "stage": "qualification",
            "entered_at": "2024-01-05T09:30:00.000Z",
            "duration_days": 3
          },
          {
            "stage": "negotiation",
            "entered_at": "2024-01-08T14:15:00.000Z",
            "duration_days": 7
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
        "display_order": 1,
        "stages": [
          {
            "id": "qualification",
            "label": "Qualification",
            "probability": 10,
            "display_order": 1,
            "closed_won": false
          },
          {
            "id": "negotiation",
            "label": "Negotiation",
            "probability": 75,
            "display_order": 2,
            "closed_won": false
          },
          {
            "id": "closed-won",
            "label": "Closed Won",
            "probability": 100,
            "display_order": 3,
            "closed_won": true
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
    "associationsIncluded": true
  }
}
```

**Error Response (202 - Not Completed):**
```json
{
  "error": "Scan Not Completed",
  "message": "Scan company-deals-extraction-2024-001 is not completed. Current status: running",
  "details": {
    "currentStatus": "running",
    "progress": 65,
    "estimatedCompletion": "2024-01-15T10:38:00.000Z"
  },
  "timestamp": "2024-01-15T10:35:00.000Z"
}
```

---

## Download Extraction Results

### `GET /scan/download/{scanId}`

Download extraction results as a CSV file with comprehensive data export.

**Parameters:**
- `scanId` (string, required) - Unique scan identifier

**Response:**
- **Content-Type**: `text/csv`
- **Content-Disposition**: `attachment; filename=hubspot_company_deals_{scanId}.csv`
- **File Format**: CSV with headers for company and deal data

**CSV Structure:**
```csv
record_type,id,name,company,amount,stage,created_date,last_modified
company,company_123,Acme Corporation,acme.com,,,2024-01-10T14:30:00.000Z,2024-01-14T16:45:00.000Z
deal,deal_456,Enterprise Software License,Acme Corporation,50000,negotiation,2024-01-05T09:30:00.000Z,2024-01-14T17:20:00.000Z
```

**Error Response (404 - Not Found):**
```json
{
  "error": "Scan Not Found",
  "message": "Scan company-deals-extraction-2024-001 not found or contains no data",
  "details": null,
  "timestamp": "2024-01-15T10:30:00.000Z"
}
```

---

## Cancel Extraction

### `POST /scan/cancel/{scanId}`

Cancel an ongoing extraction operation gracefully.

**Parameters:**
- `scanId` (string, required) - Unique scan identifier

**Response:**
```json
{
  "scanId": "company-deals-extraction-2024-001",
  "status": "cancelled",
  "message": "Company deals extraction scan cancelled successfully",
  "cancelledAt": "2024-01-15T10:35:00.000Z",
  "metadata": {
    "recordsProcessedBeforeCancel": 1200,
    "partialDataAvailable": true,
    "cancellationReason": "User requested"
  }
}
```

**Error Response (400 - Cannot Cancel):**
```json
{
  "error": "Cannot Cancel",
  "message": "Scan company-deals-extraction-2024-001 cannot be cancelled (not found or not active)",
  "details": {
    "currentStatus": "completed",
    "reason": "Scan already completed"
  },
  "timestamp": "2024-01-15T10:35:00.000Z"
}
```

---

## Remove Extraction

### `DELETE /scan/remove/{scanId}`

Remove an extraction job and all associated data permanently.

**Parameters:**
- `scanId` (string, required) - Unique scan identifier

**Response:**
```json
{
  "scanId": "company-deals-extraction-2024-001",
  "message": "Company deals extraction scan and all associated data removed successfully",
  "removedAt": "2024-01-15T10:40:00.000Z",
  "deleted_records": {
    "companies": 150,
    "deals": 720,
    "pipelines": 5,
    "total": 875
  }
}
```

---

# System & Monitoring Endpoints

## System Health Check

### `GET /health`

Comprehensive health check with system component status.

**Response (200 - Healthy):**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:00:00.000Z",
  "service": "HubSpot Extraction Service",
  "version": "2.0.0",
  "api_framework": "Flask-RESTX",
  "checks": {
    "database": "healthy",
    "database_pool": "Pool: 10 connections, Active: 2, Available: 8",
    "thread_manager": "healthy",
    "active_extractions": "2 running, 0 queued",
    "memory_usage": "245MB / 1024MB (24%)",
    "disk_space": "15.2GB / 50GB (30%)"
  },
  "system_stats": {
    "uptime_seconds": 86400,
    "total_extractions_today": 25,
    "successful_extractions": 23,
    "failed_extractions": 2,
    "average_extraction_time": "4.5 minutes"
  }
}
```

**Response (503 - Unhealthy):**
```json
{
  "status": "unhealthy",
  "timestamp": "2024-01-15T10:00:00.000Z",
  "service": "HubSpot Extraction Service",
  "version": "2.0.0",
  "checks": {
    "database": "unhealthy: Connection timeout after 30 seconds",
    "thread_manager": "degraded: 1 thread failed, 2 active",
    "active_extractions": "error: Unable to query extraction status"
  },
  "errors": [
    {
      "component": "database",
      "error": "Connection timeout",
      "since": "2024-01-15T09:55:00.000Z"
    }
  ]
}
```

**Health Status Values:**
- `healthy` - All systems operational
- `degraded` - Some non-critical issues detected
- `unhealthy` - Critical issues requiring attention

---

## Service Statistics

### `GET /scan/stats`

Get comprehensive service statistics and performance metrics.

**Response:**
```json
{
  "service": {
    "name": "HubSpot Company Deals Extraction Service",
    "version": "2.0.0",
    "uptime_seconds": 86400,
    "api_framework": "Flask-RESTX"
  },
  "extractions": {
    "total_scans": 150,
    "successful_scans": 142,
    "failed_scans": 6,
    "cancelled_scans": 2,
    "active_scans": 2,
    "queued_scans": 0
  },
  "performance": {
    "average_scan_duration_seconds": 270,
    "fastest_scan_duration_seconds": 45,
    "slowest_scan_duration_seconds": 1800,
    "total_records_extracted": 125000,
    "average_records_per_scan": 833
  },
  "data_breakdown": {
    "companies_extracted": 12500,
    "deals_extracted": 45000,
    "pipelines_extracted": 150
  },
  "system_resources": {
    "memory_usage_mb": 245,
    "memory_limit_mb": 1024,
    "cpu_usage_percent": 15,
    "disk_usage_gb": 15.2,
    "disk_limit_gb": 50,
    "active_threads": 3,
    "max_threads": 10
  },
  "hubspot_api": {
    "requests_today": 12500,
    "rate_limit_remaining": 875,
    "rate_limit_reset": "2024-01-15T11:00:00.000Z",
    "average_response_time_ms": 250
  },
  "timestamp": "2024-01-15T10:00:00.000Z"
}
```

---

## Thread Status Monitoring

### `GET /system/threads`

Monitor active extraction threads and their status.

**Response:**
```json
{
  "thread_manager": {
    "total_threads": 3,
    "active_threads": 2,
    "idle_threads": 1,
    "max_threads": 10,
    "thread_pool_utilization": 30
  },
  "active_extractions": {
    "company-deals-extraction-2024-001": {
      "thread_id": "thread_001",
      "is_alive": true,
      "status": "running",
      "started_at": "2024-01-15T10:30:00.000Z",
      "progress_percentage": 65,
      "current_operation": "Extracting deals batch 8 of 12"
    },
    "daily-deals-extraction-2024-002": {
      "thread_id": "thread_002",
      "is_alive": true,
      "status": "running",
      "started_at": "2024-01-15T10:25:00.000Z",
      "progress_percentage": 85,
      "current_operation": "Extracting companies batch 4 of 5"
    }
  },
  "completed_extractions": {
    "morning-deals-extraction-2024-001": {
      "thread_id": "thread_003",
      "is_alive": false,
      "status": "completed",
      "started_at": "2024-01-15T09:15:00.000Z",
      "completed_at": "2024-01-15T09:45:00.000Z",
      "duration_seconds": 1800,
      "records_extracted": 2500
    }
  },
  "thread_health": {
    "healthy_threads": 2,
    "failed_threads": 0,
    "stuck_threads": 0,
    "last_health_check": "2024-01-15T10:35:00.000Z"
  }
}
```

---

# Error Handling

## Standard Error Response Format

All error responses follow a consistent format with proper HTTP status codes:

```json
{
  "error": "ERROR_TYPE",
  "message": "Human-readable error description",
  "details": {
    "field": "Additional context",
    "validation_errors": ["Specific validation failures"],
    "error_code": "INTERNAL_ERROR_CODE"
  },
  "timestamp": "2024-01-15T10:30:00.000Z"
}
```

## HTTP Status Codes and Error Types

| HTTP Status | Error Type | Description | Example |
|-------------|------------|-------------|---------|
| 400 | `Validation Error` | Request validation failed | Missing required fields |
| 401 | `Authentication Error` | Invalid HubSpot token | Token expired or invalid |
| 403 | `Authorization Error` | Insufficient permissions | Missing required scopes |
| 404 | `Not Found` | Resource not found | Scan ID doesn't exist |
| 409 | `Conflict` | Resource conflict | Scan already running |
| 422 | `Unprocessable Entity` | Semantic validation failed | Invalid date range |
| 429 | `Rate Limit Exceeded` | Too many requests | HubSpot API rate limit |
| 500 | `Internal Server Error` | Unexpected server error | Database connection failed |
| 502 | `Bad Gateway` | External service error | HubSpot API unavailable |
| 503 | `Service Unavailable` | Service temporarily down | System maintenance |

## Detailed Error Examples

### 400 - Validation Error
```json
{
  "error": "Validation Error",
  "message": "Request validation failed",
  "details": {
    "config": ["Field is required"],
    "config.auth.accessToken": ["Invalid token format"],
    "config.scanId": ["ScanId must be unique"]
  },
  "timestamp": "2024-01-15T10:30:00.000Z"
}
```

### 401 - Authentication Error
```json
{
  "error": "Authentication Error",
  "message": "Invalid HubSpot access token",
  "details": {
    "token_prefix": "pat-na1-xxx",
    "error_code": "INVALID_AUTHENTICATION",
    "suggestion": "Please verify your HubSpot access token is valid and not expired"
  },
  "timestamp": "2024-01-15T10:30:00.000Z"
}
```

### 403 - Authorization Error
```json
{
  "error": "Authorization Error",
  "message": "Insufficient permissions for HubSpot API",
  "details": {
    "required_scopes": ["crm.objects.deals.read", "crm.objects.companies.read"],
    "missing_scopes": ["crm.objects.companies.read"],
    "error_code": "INSUFFICIENT_PERMISSIONS"
  },
  "timestamp": "2024-01-15T10:30:00.000Z"
}
```

### 409 - Conflict Error
```json
{
  "error": "Conflict",
  "message": "Active extraction already exists",
  "details": {
    "existing_scan_id": "weekly-extraction-2024-001",
    "current_status": "running",
    "started_at": "2024-01-15T10:30:00.000Z",
    "suggestion": "Cancel existing scan or use a different scanId"
  },
  "timestamp": "2024-01-15T10:32:00.000Z"
}
```

### 429 - Rate Limit Exceeded
```json
{
  "error": "Rate Limit Exceeded",
  "message": "HubSpot API rate limit exceeded",
  "details": {
    "rate_limit": "100 requests per 10 seconds",
    "retry_after_seconds": 60,
    "reset_time": "2024-01-15T10:31:00.000Z",
    "error_code": "RATE_LIMIT_EXCEEDED"
  },
  "timestamp": "2024-01-15T10:30:00.000Z"
}
```

---

# Configuration & Filtering

## Extraction Configuration Options

### Basic Configuration
```json
{
  "config": {
    "scanId": "unique-identifier",
    "type": ["deals", "companies"],
    "auth": {
      "accessToken": "hubspot-token"
    }
  }
}
```

### Advanced Extraction Options
```json
{
  "extraction": {
    "extractDeals": true,
    "extractCompanies": true,
    "extractPipelines": true,
    "batchSize": 100,
    "maxRecords": 50000,
    "concurrentRequests": 3
  }
}
```

### Comprehensive Filtering
```json
{
  "filters": {
    "dealStage": ["qualification", "negotiation", "closed-won"],
    "amountMin": 1000,
    "amountMax": 1000000,
    "currency": ["USD", "EUR"],
    "createdAfter": "2024-01-01",
    "createdBefore": "2024-12-31",
    "modifiedAfter": "2024-01-01",
    "pipelineId": ["sales-pipeline", "marketing-pipeline"],
    "dealType": ["new-business", "existing-business"],
    "companySize": ["small", "medium", "large"],
    "industry": ["technology", "healthcare", "finance"],
    "leadSource": ["website", "referral", "advertisement"]
  }
}
```

### Advanced Options
```json
{
  "options": {
    "includeCustomProperties": true,
    "includeAssociations": true,
    "includeStageHistory": true,
    "includeActivityHistory": false,
    "includeEngagementData": false,
    "includePipelineMetadata": true,
    "exportFormat": "json",
    "timezone": "America/New_York",
    "dateFormat": "ISO8601"
  }
}
```

## Filter Reference

### Deal Filters
| Filter | Type | Description | Example |
|--------|------|-------------|---------|
| `dealStage` | array | Filter by deal stage names | `["negotiation", "closed-won"]` |
| `amountMin` | number | Minimum deal amount | `10000` |
| `amountMax` | number | Maximum deal amount | `1000000` |
| `currency` | array | Filter by currency codes | `["USD", "EUR"]` |
| `pipelineId` | array | Filter by pipeline IDs | `["sales-pipeline"]` |
| `dealType` | array | Filter by deal type | `["new-business"]` |
| `probability` | object | Filter by probability range | `{"min": 50, "max": 100}` |

### Company Filters
| Filter | Type | Description | Example |
|--------|------|-------------|---------|
| `companySize` | array | Filter by company size | `["small", "medium", "large"]` |
| `industry` | array | Filter by industry | `["technology", "healthcare"]` |
| `annualRevenue` | object | Filter by revenue range | `{"min": 1000000, "max": 10000000}` |
| `employeeCount` | object | Filter by employee count | `{"min": 10, "max": 500}` |

### Contact Filters
| Filter | Type | Description | Example |
|--------|------|-------------|---------|
| `lifecycleStage` | array | Filter by lifecycle stage | `["lead", "customer"]` |
| `leadSource` | array | Filter by lead source | `["website", "referral"]` |
| `jobTitle` | array | Filter by job titles | `["CEO", "VP", "Manager"]` |

### Ticket Filters
| Filter | Type | Description | Example |
|--------|------|-------------|---------|
| `priority` | array | Filter by priority levels | `["HIGH", "MEDIUM", "LOW"]` |
| `category` | array | Filter by ticket categories | `["SUPPORT_REQUEST", "SALES_INQUIRY"]` |
| `ticketStatus` | array | Filter by ticket status | `["OPEN", "PENDING", "CLOSED"]` |

### Contact Filters
| Filter | Type | Description | Example |
|--------|------|-------------|---------|
| `lifecycleStage` | array | Filter by lifecycle stage | `["lead", "customer"]` |
| `leadSource` | array | Filter by lead source | `["website", "referral"]` |
| `jobTitle` | array | Filter by job titles | `["CEO", "VP", "Manager"]` |

### Ticket Filters
| Filter | Type | Description | Example |
|--------|------|-------------|---------|
| `priority` | array | Filter by priority levels | `["HIGH", "MEDIUM", "LOW"]` |
| `category` | array | Filter by ticket categories | `["SUPPORT_REQUEST", "SALES_INQUIRY"]` |
| `ticketStatus` | array | Filter by ticket status | `["OPEN", "PENDING", "CLOSED"]` |

### Date Filters
| Filter | Type | Description | Example |
|--------|------|-------------|---------|
| `createdAfter` | date | Include records created after | `"2024-01-01"` |
| `createdBefore` | date | Include records created before | `"2024-12-31"` |
| `modifiedAfter` | date | Include records modified after | `"2024-01-01"` |
| `modifiedBefore` | date | Include records modified before | `"2024-12-31"` |

---

# Rate Limiting

## Service Rate Limits
- **API Requests**: 1000 requests per hour per IP address
- **Concurrent Extractions**: Maximum 5 concurrent extraction jobs
- **File Downloads**: 100 downloads per hour per IP address

## HubSpot API Rate Limits
- **Standard Rate Limit**: 100 requests per 10 seconds per portal
- **Daily Limit**: 1,000,000 requests per day (varies by subscription)
- **Burst Limit**: 150 requests per 10 seconds (short bursts)

## Rate Limit Headers
```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 875
X-RateLimit-Reset: 1642248000
X-RateLimit-Retry-After: 60
```

## Rate Limit Handling
The service automatically handles rate limits with:
- **Exponential Backoff**: Automatic retry with increasing delays
- **Queue Management**: Requests are queued when limits are reached
- **Intelligent Throttling**: Proactive rate limiting to prevent violations
- **Real-time Monitoring**: Live tracking of rate limit status

---

# Usage Examples

## cURL Examples

### Start Comprehensive Extraction
```bash
curl -X POST http://localhost:4045/scan/start \
  -H "Content-Type: application/json" \
  -d '{
    "config": {
      "scanId": "company-deals-extraction-2024-001",
      "type": ["deals", "companies"],
      "auth": {
        "accessToken": "pat-na1-your-hubspot-token-here"
      },
      "extraction": {
        "extractDeals": true,
        "extractCompanies": true,
        "batchSize": 100,
        "maxRecords": 10000
      },
      "filters": {
        "dealStage": ["negotiation", "closed-won"],
        "amountMin": 10000,
        "createdAfter": "2024-01-01"
      },
      "options": {
        "includeCustomProperties": true,
        "includeAssociations": true,
        "includeStageHistory": true
      }
    }
  }'
```

### Monitor Extraction Progress
```bash
curl http://localhost:4045/scan/status/company-deals-extraction-2024-001
```

### Get Complete Results
```bash
curl http://localhost:4045/scan/result/company-deals-extraction-2024-001
```

### Download CSV Export
```bash
curl -O http://localhost:4045/scan/download/company-deals-extraction-2024-001
```

### Cancel Running Extraction
```bash
curl -X POST http://localhost:4045/scan/cancel/company-deals-extraction-2024-001
```

### Health Check
```bash
curl http://localhost:4045/health
```

### Service Statistics
```bash
curl http://localhost:4045/scan/stats
```