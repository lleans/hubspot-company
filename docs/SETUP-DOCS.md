# Hubspot Company Extraction Service Setup Guide

This document provides comprehensive instructions for setting up and running the Hubspot Company Extraction Service in different environments.

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Environment Setup](#environment-setup)
3. [Running the Service](#running-the-service)
4. [Configuration Options](#configuration-options)
5. [Environment Variables](#environment-variables)
6. [Testing](#testing)
7. [Logging Configuration](#logging-configuration)
8. [Data Persistence](#data-persistence)
9. [Troubleshooting](#troubleshooting)
10. [Maintenance Tasks](#maintenance-tasks)

## Prerequisites

Before getting started, ensure you have the following installed:

- Docker (version 20.10+)
- Docker Compose (version 2.0+)
- Git

### Hardware Requirements

- **Development**: 4GB RAM, 2 CPU cores
- **Staging**: 8GB RAM, 4 CPU cores
- **Production**: 16GB RAM, 8 CPU cores, SSD storage

## Environment Setup

### Clone the Repository

```bash
git clone https://github.com/your-org/hubspot-company-extraction-service.git
cd hubspot-company-extraction-service
```

### Environment Configuration

Create a `.env` file in the project root with the appropriate values for your environment:

```bash
# Common settings
SECRET_KEY=your-secure-secret-key
BATCH_SIZE=100
MAX_RETRIES=3

# Database credentials (for staging/production)
POSTGRES_USER=db_username
POSTGRES_PASSWORD=db_secure_password
POSTGRES_DB=hubspot_extraction

# Hubspot API settings
HUBSPOT_API_TIMEOUT=30

# Resource allocation
MAX_WORKER_THREADS=5
THREAD_POOL_SIZE=10

# Logging settings
LOG_LEVEL=INFO
LOG_FORMAT=json
LOG_DIR=/app/logs
LOG_FILE=hubspot_extraction.jsonl
```

### Initialize Configuration Files

Create the Redis configuration file:

```bash
# Create redis.conf file
mkdir -p config
cat > config/redis.conf << EOF
maxmemory 512mb
maxmemory-policy allkeys-lru
appendonly yes
appendfilename "appendonly.aof"
appendfsync everysec
no-appendfsync-on-rewrite no
auto-aof-rewrite-percentage 100
auto-aof-rewrite-min-size 64mb
EOF

# Link it to the right location
ln -s $(pwd)/config/redis.conf ./redis.conf
```

## Running the Service

The service can be run in different environments using Docker Compose profiles.

### Development Environment

For local development with hot-reloading and debugging:

```bash
docker-compose --profile dev up
```

This starts:
- PostgreSQL database on port 5441
- Redis on port 6379
- Development app server on port 4045

Access the development API at: http://localhost:4045/scan/health

### Staging Environment

For testing in a production-like environment:

```bash
docker-compose --profile stage up
```

This starts:
- PostgreSQL database (with staging configuration)
- Shared Redis instance
- Staging app server on port 3013

Access the staging API at: http://localhost:3013/scan/health

### Production Environment

For running in production:

```bash
docker-compose --profile prod up -d
```

This starts:
- PostgreSQL database (with production configuration)
- Shared Redis instance
- Production app server on port 3012

Access the production API at: http://localhost:3012/scan/health

### Starting Multiple Environments

You can run multiple environments simultaneously if needed:

```bash
docker-compose --profile dev --profile stage up
```

## Configuration Options

### Database Configuration

Each environment has its own PostgreSQL instance with different configurations:

- **Development**:
  - Basic configuration for local development
  - Located at: `postgresql://user:password@localhost:5441/hubspot_dev`

- **Staging**:
  - Moderate performance settings
  - 150 max connections
  - 192MB shared buffers

- **Production**:
  - Optimized settings for high performance
  - 200 max connections
  - 256MB shared buffers
  - 1GB effective cache size

### Redis Configuration

A single Redis instance is shared across all environments with the following settings:

- Memory: 512MB maximum
- Policy: allkeys-lru (Least Recently Used eviction)
- Persistence: Append-only file enabled

## Environment Variables

| Variable | Description | Default | Environment |
|----------|-------------|---------|------------|
| SECRET_KEY | Secret key for securing the application | None | All |
| POSTGRES_USER | Database username | Varies | Stage, Prod |
| POSTGRES_PASSWORD | Database password | Varies | Stage, Prod |
| POSTGRES_DB | Database name | Varies | Stage, Prod |
| LOG_LEVEL | Logging level | INFO | All (dev: DEBUG, prod: WARNING) |
| LOG_FORMAT | Format for logs (json/text) | json | All |
| PORT | Application port | Varies | All |
| MAX_WORKER_THREADS | Max number of worker threads | 5 | All (8 for staging) |
| BATCH_SIZE | Batch size for processing | 100 | All |
| HUBSPOT_API_TIMEOUT | Timeout for HubSpot API calls | 30 seconds | All |

## Testing

Run the automated test suite with:

```bash
docker-compose --profile test up
```

This runs a comprehensive test suite with:
- Isolated test database
- Shared Redis instance
- Code coverage reports
- JUnit XML test results

Test artifacts are available in the following volumes:
- `test_coverage`: HTML coverage reports
- `test_results`: JUnit XML test results

### Viewing Test Results

To view HTML coverage reports after tests complete:

```bash
# Find the test coverage volume location
docker volume inspect hubspot-company-extraction-service_test_coverage

# Open the index.html file in your browser
open /var/lib/docker/volumes/hubspot-company-extraction-service_test_coverage/_data/index.html
```

## Logging Configuration

The service uses structured JSON logging optimized for Loki ingestion:

### Log Locations

- **Development**: `./logs/hubspot_extraction_dev.log`
- **Staging**: `/app/logs/hubspot_extraction_staging.jsonl`
- **Production**: `/app/logs/hubspot_extraction.jsonl`

### Viewing Logs

```bash
# Development logs
docker-compose logs app

# Staging logs
docker-compose logs app_stage

# Production logs
docker-compose logs app_prod

# View live logs
docker-compose logs -f app
```

### Log Format

The default log format is JSON with the following structure:

```json
{
  "timestamp": "2025-08-15T10:30:45.123Z",
  "level": "INFO",
  "logger": "extraction_service",
  "message": "Starting extraction",
  "module": "extraction_service",
  "function": "start_extraction",
  "line": 42,
  "service": "hubspot-extraction-service",
  "environment": "production",
  "version": "2.0.0",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "scan_id": "abc123"
}
```

## Data Persistence

The service uses Docker volumes for data persistence:

### Volume Locations

- **Development**:
  - `postgres_dev_data`: PostgreSQL data
  - `dev_logs`: Application logs

- **Staging**:
  - `postgres_stage_data`: PostgreSQL data
  - `app_stage_logs`: Application logs
  - `app_stage_data`: Application data

- **Production**:
  - `postgres_data`: PostgreSQL data
  - `app_logs`: Application logs
  - `app_data`: Application data

- **Shared**:
  - `redis_data`: Redis data for all environments

### Backup and Restore

To backup the PostgreSQL database:

```bash
# Development
docker exec -t hubspot_extraction_db_dev pg_dump -U user hubspot_dev > backup_dev.sql

# Staging
docker exec -t hubspot_extraction_db_stage pg_dump -U $POSTGRES_USER $POSTGRES_DB > backup_stage.sql

# Production
docker exec -t hubspot_extraction_db_prod pg_dump -U $POSTGRES_USER $POSTGRES_DB > backup_prod.sql
```

To restore from backup:

```bash
# Development
cat backup_dev.sql | docker exec -i hubspot_extraction_db_dev psql -U user -d hubspot_dev

# Staging
cat backup_stage.sql | docker exec -i hubspot_extraction_db_stage psql -U $POSTGRES_USER -d $POSTGRES_DB

# Production
cat backup_prod.sql | docker exec -i hubspot_extraction_db_prod psql -U $POSTGRES_USER -d $POSTGRES_DB
```

## Troubleshooting

### Common Issues

#### Connection Refused to Database

Ensure the database is healthy:

```bash
docker-compose ps
```

Check database logs:

```bash
docker-compose logs db  # For development
docker-compose logs db_stage  # For staging
docker-compose logs db_prod  # For production
```

#### Redis Connection Issues

Check Redis logs:

```bash
docker-compose logs redis
```

Verify Redis is running:

```bash
docker exec -it hubspot_extraction_redis redis-cli ping
```

#### Application Errors

Check application logs:

```bash
docker-compose logs app  # For development
docker-compose logs app_stage  # For staging
docker-compose logs app_prod  # For production
```

### Health Checks

Verify service health:

```bash
# Development
curl http://localhost:4045/scan/health

# Staging
curl http://localhost:3013/scan/health

# Production
curl http://localhost:3012/scan/health
```

The health check should return a JSON object with status "healthy" and various health metrics.

### Resource Usage

Check resource usage:

```bash
docker stats
```

## Maintenance Tasks

### Updating the Service

To update the service:

1. Pull the latest code:
   ```bash
   git pull origin main
   ```

2. Rebuild the containers:
   ```bash
   docker-compose --profile <env> build
   ```

3. Restart the service:
   ```bash
   docker-compose --profile <env> up -d
   ```

### Database Maintenance

#### Running Migrations

```bash
# Development
docker-compose exec app python manage.py migrate

# Staging
docker-compose exec app_stage python manage.py migrate

# Production
docker-compose exec app_prod python manage.py migrate
```

#### Database Vacuum

```bash
# Development
docker exec -it hubspot_extraction_db_dev psql -U user -d hubspot_dev -c "VACUUM ANALYZE;"

# Staging
docker exec -it hubspot_extraction_db_stage psql -U $POSTGRES_USER -d $POSTGRES_DB -c "VACUUM ANALYZE;"

# Production
docker exec -it hubspot_extraction_db_prod psql -U $POSTGRES_USER -d $POSTGRES_DB -c "VACUUM ANALYZE;"
```

### Redis Maintenance

#### Monitoring Redis Memory

```bash
docker exec -it hubspot_extraction_redis redis-cli info memory
```

#### Clearing Redis Cache

```bash
docker exec -it hubspot_extraction_redis redis-cli FLUSHALL
```

### Log Rotation

Logs are automatically rotated based on size. To manually rotate logs:

```bash
# Development
docker-compose exec app bash -c "mv /app/logs/hubspot_extraction_dev.log /app/logs/hubspot_extraction_dev.log.1"

# Staging
docker-compose exec app_stage bash -c "mv /app/logs/hubspot_extraction_staging.jsonl /app/logs/hubspot_extraction_staging.jsonl.1"

# Production
docker-compose exec app_prod bash -c "mv /app/logs/hubspot_extraction.jsonl /app/logs/hubspot_extraction.jsonl.1"
```

---

For more detailed information, check the application documentation or contact the development team at support@example.com.