# HubSpot Data Extraction System - Database Design Documentation

## Overview

This database design supports a HubSpot data extraction system that tracks extraction jobs and stores HubSpot entities (companies, deals, and pipelines) with full audit trails and performance optimization.

## Architecture Principles

- **Thread-Safe Operations**: All database operations use scoped sessions and proper connection pooling
- **Cascade Relationships**: Parent-child relationships with automatic cleanup
- **Performance Optimization**: Strategic indexing for common query patterns
- **Data Integrity**: Unique constraints to prevent duplicate records
- **Audit Trail**: Complete lifecycle tracking with timestamps
- **Flexibility**: JSON fields for storing complete HubSpot property sets

## Database Schema

### Base Model Architecture

All models inherit from `BaseModel` which provides:
- **UUID Primary Keys**: String-based UUIDs for distributed system compatibility
- **Audit Timestamps**: `created_at` and `updated_at` with automatic updates
- **Dictionary Serialization**: Built-in `to_dict()` method

```sql
-- Common fields for all tables
id VARCHAR PRIMARY KEY DEFAULT uuid4()
created_at TIMESTAMP NOT NULL DEFAULT NOW()
updated_at TIMESTAMP NOT NULL DEFAULT NOW() ON UPDATE NOW()
```

## Core Tables

### 1. extraction_jobs

**Purpose**: Tracks the complete lifecycle of HubSpot data extraction operations

```sql
CREATE TABLE extraction_jobs (
    id VARCHAR PRIMARY KEY,
    connection_id VARCHAR(255) UNIQUE NOT NULL,
    status VARCHAR(50) NOT NULL,
    start_time TIMESTAMP NOT NULL DEFAULT NOW(),
    end_time TIMESTAMP NULL,
    message TEXT NULL,
    error_details TEXT NULL,
    progress_percentage INTEGER DEFAULT 0,
    total_records_extracted INTEGER DEFAULT 0,
    companies_extracted INTEGER DEFAULT 0,
    deals_extracted INTEGER DEFAULT 0,
    pipelines_extracted INTEGER DEFAULT 0,
    extraction_duration_seconds INTEGER NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);
```

**Key Features**:
- Unique `connection_id` for external system integration
- Status tracking: `pending`, `running`, `completed`, `failed`, `cancelled`
- Progress metrics with detailed extraction counts
- Performance monitoring with duration tracking

**Indexes**:
```sql
CREATE INDEX idx_extraction_job_status_start ON extraction_jobs(status, start_time);
CREATE INDEX idx_extraction_job_connection ON extraction_jobs(connection_id);
CREATE INDEX idx_extraction_job_created_status ON extraction_jobs(created_at, status);
```

### 2. hubspot_companies

**Purpose**: Stores HubSpot company records with comprehensive business information

```sql
CREATE TABLE hubspot_companies (
    id VARCHAR PRIMARY KEY,
    job_id VARCHAR NOT NULL REFERENCES extraction_jobs(id) ON DELETE CASCADE,
    connection_id VARCHAR(255) NOT NULL,
    hubspot_company_id VARCHAR(50) NOT NULL,
    name VARCHAR(500) NULL,
    domain VARCHAR(255) NULL,
    industry VARCHAR(255) NULL,
    description TEXT NULL,
    city VARCHAR(255) NULL,
    state VARCHAR(255) NULL,
    country VARCHAR(255) NULL,
    timezone VARCHAR(100) NULL,
    annual_revenue VARCHAR(50) NULL,
    number_of_employees VARCHAR(50) NULL,
    hubspot_created_date TIMESTAMP NULL,
    hubspot_updated_date TIMESTAMP NULL,
    properties JSONB NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);
```

**Key Features**:
- Flexible revenue/employee storage as strings to handle various formats
- Complete HubSpot properties stored as JSON for extensibility
- Normalized core fields for efficient querying
- Geographic information for territory analysis

**Constraints & Indexes**:
```sql
ALTER TABLE hubspot_companies ADD CONSTRAINT uq_company_connection_hubspot_id 
    UNIQUE(connection_id, hubspot_company_id);

CREATE INDEX idx_company_name ON hubspot_companies(name);
CREATE INDEX idx_company_domain ON hubspot_companies(domain);
CREATE INDEX idx_company_industry ON hubspot_companies(industry);
CREATE INDEX idx_company_city_state ON hubspot_companies(city, state);
CREATE INDEX idx_company_hubspot_created ON hubspot_companies(hubspot_created_date);
```

### 3. hubspot_deals

**Purpose**: Stores HubSpot deal records with pipeline and financial information

```sql
CREATE TABLE hubspot_deals (
    id VARCHAR PRIMARY KEY,
    job_id VARCHAR NOT NULL REFERENCES extraction_jobs(id) ON DELETE CASCADE,
    connection_id VARCHAR(255) NOT NULL,
    hubspot_deal_id VARCHAR(50) NOT NULL,
    dealname VARCHAR(500) NULL,
    amount NUMERIC(15,2) NULL,
    amount_raw VARCHAR(50) NULL,
    pipeline_id VARCHAR(50) NULL,
    pipeline_label VARCHAR(255) NULL,
    dealstage_id VARCHAR(50) NULL,
    dealstage_label VARCHAR(255) NULL,
    closedate TIMESTAMP NULL,
    hubspot_created_date TIMESTAMP NULL,
    hubspot_updated_date TIMESTAMP NULL,
    deal_type VARCHAR(100) NULL,
    deal_priority VARCHAR(50) NULL,
    associated_company_id VARCHAR(50) NULL,
    company_name VARCHAR(500) NULL,
    properties JSONB NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);
```

**Key Features**:
- Precise monetary values using `NUMERIC(15,2)`
- Dual amount storage (parsed and raw) for data integrity
- Denormalized company information for performance
- Pipeline and stage tracking for sales funnel analysis
- Deal lifecycle timestamps

**Constraints & Indexes**:
```sql
ALTER TABLE hubspot_deals ADD CONSTRAINT uq_deal_connection_hubspot_id 
    UNIQUE(connection_id, hubspot_deal_id);

CREATE INDEX idx_deal_name ON hubspot_deals(dealname);
CREATE INDEX idx_deal_amount ON hubspot_deals(amount);
CREATE INDEX idx_deal_pipeline_stage ON hubspot_deals(pipeline_id, dealstage_id);
CREATE INDEX idx_deal_closedate ON hubspot_deals(closedate);
CREATE INDEX idx_deal_created_date ON hubspot_deals(hubspot_created_date);
CREATE INDEX idx_deal_company ON hubspot_deals(associated_company_id);
```

### 4. hubspot_deal_pipelines

**Purpose**: Stores HubSpot pipeline definitions with complete stage information

```sql
CREATE TABLE hubspot_deal_pipelines (
    id VARCHAR PRIMARY KEY,
    job_id VARCHAR NOT NULL REFERENCES extraction_jobs(id) ON DELETE CASCADE,
    connection_id VARCHAR(255) NOT NULL,
    hubspot_pipeline_id VARCHAR(50) NOT NULL,
    label VARCHAR(255) NULL,
    display_order INTEGER NULL,
    active BOOLEAN DEFAULT TRUE,
    pipeline_type VARCHAR(100) NULL,
    created_at_hubspot TIMESTAMP NULL,
    updated_at_hubspot TIMESTAMP NULL,
    properties JSONB NULL,
    stages_data JSONB NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);
```

**Key Features**:
- Pipeline metadata with ordering and status
- Separate JSON storage for stages data for efficient querying
- Support for different pipeline types (deals, tickets, etc.)
- HubSpot timestamp preservation

**Constraints & Indexes**:
```sql
ALTER TABLE hubspot_deal_pipelines ADD CONSTRAINT uq_pipeline_connection_hubspot_id 
    UNIQUE(connection_id, hubspot_pipeline_id);

CREATE INDEX idx_pipeline_label ON hubspot_deal_pipelines(label);
CREATE INDEX idx_pipeline_active ON hubspot_deal_pipelines(active);
CREATE INDEX idx_pipeline_display_order ON hubspot_deal_pipelines(display_order);
```

## Relationships

### Entity Relationship Diagram

```
extraction_jobs (1) ─┐
                     ├─── hubspot_companies (N)
                     ├─── hubspot_deals (N)
                     └─── hubspot_deal_pipelines (N)
```

### Cascade Behavior

- **CASCADE DELETE**: When an extraction job is deleted, all associated HubSpot records are automatically removed
- **LAZY LOADING**: Relationships use dynamic lazy loading for memory efficiency
- **BACK REFERENCES**: Bidirectional relationships for convenient navigation

## Database Configuration

### Connection Settings

```python
# Thread-safe configuration
pool_size=10                 # Base connection pool size
max_overflow=20             # Additional connections under load
pool_pre_ping=True          # Connection health checks
pool_recycle=3600           # Refresh connections hourly
```

### Session Management

```python
# Thread-safe session handling
SessionFactory = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Session = scoped_session(SessionFactory)

@contextmanager
def get_db_session():
    session = Session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
        Session.remove()
```

## Performance Optimization

### Indexing Strategy

1. **Primary Access Patterns**:
   - Job status and timeline queries
   - HubSpot ID lookups
   - Company/deal searches by name
   - Pipeline and stage filtering

2. **Composite Indexes**:
   - Multi-column indexes for common filter combinations
   - Status + timestamp for job monitoring
   - Pipeline + stage for deal analysis

3. **JSON Indexing**:
   - PostgreSQL JSONB with GIN indexes on properties columns
   - Optimized for property key existence and value searches

### Query Optimization Features

- **Unique Constraints**: Prevent duplicate data and enable fast uniqueness checks
- **Foreign Key Indexes**: Automatic indexing on all foreign key columns
- **Strategic Denormalization**: Company names in deals table for join avoidance

## Data Integrity

### Constraints

1. **Unique Constraints**:
   - `(connection_id, hubspot_*_id)` combinations prevent duplicates
   - Single `connection_id` per extraction job

2. **Foreign Key Constraints**:
   - CASCADE DELETE maintains referential integrity
   - NOT NULL on critical relationship fields

3. **Data Validation**:
   - Status enums enforced at application level
   - Timestamp consistency checks
   - Amount precision constraints

### Audit Trail

- Full lifecycle tracking with creation and update timestamps
- Original HubSpot timestamps preserved
- Job progress and duration metrics
- Error detail preservation for debugging

## Extensions and Scalability

### JSON Field Usage

- **Flexible Schema**: Complete HubSpot properties stored as JSON
- **Backward Compatibility**: New HubSpot fields automatically captured
- **Query Flexibility**: PostgreSQL JSONB operators for complex filtering

### Horizontal Scaling Considerations

- **Partitioning Ready**: Date-based partitioning possible on `created_at`
- **Connection Isolation**: `connection_id` enables tenant-based sharding
- **Read Replicas**: Read-heavy analytics queries can use dedicated replicas

### Monitoring and Maintenance

```python
def get_db_stats():
    """Connection pool health monitoring"""
    return {
        'pool_size': pool.size(),
        'checked_in': pool.checkedin(),
        'checked_out': pool.checkedout(),
        'overflow': pool.overflow(),
        'invalid': pool.invalid()
    }
```

## Common Query Patterns

### Job Monitoring
```sql
-- Active jobs with progress
SELECT connection_id, status, progress_percentage, 
       EXTRACT(EPOCH FROM (NOW() - start_time)) as runtime_seconds
FROM extraction_jobs 
WHERE status IN ('pending', 'running');
```

### Sales Pipeline Analysis
```sql
-- Deal value by pipeline stage
SELECT p.label as pipeline, d.dealstage_label, 
       COUNT(*) as deal_count, SUM(d.amount) as total_value
FROM hubspot_deals d
JOIN hubspot_deal_pipelines p ON d.pipeline_id = p.hubspot_pipeline_id
WHERE d.connection_id = p.connection_id
GROUP BY p.label, d.dealstage_label;
```

### Company Activity Report
```sql
-- Recent company updates with deal activity
SELECT c.name, c.industry, COUNT(d.id) as deal_count, 
       MAX(d.hubspot_updated_date) as last_deal_activity
FROM hubspot_companies c
LEFT JOIN hubspot_deals d ON c.hubspot_company_id = d.associated_company_id
WHERE c.connection_id = d.connection_id
GROUP BY c.id, c.name, c.industry
ORDER BY last_deal_activity DESC;
```

This database design provides a robust foundation for HubSpot data extraction with excellent performance characteristics, data integrity, and extensibility for future requirements.