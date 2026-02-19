from marshmallow import Schema, fields, validate, validates, ValidationError
from datetime import datetime

class AuthConfigSchema(Schema):
    """Schema for authentication configuration"""
    accessToken = fields.Str(
        required=True,
        validate=validate.Length(min=10),
        metadata={'description': 'HubSpot Private App Access Token'}
    )

class ExtractionConfigSchema(Schema):
    """Schema for extraction configuration"""
    extractDeals = fields.Bool(
        load_default=True,
        metadata={'description': 'Whether to extract deals'}
    )
    extractCompanies = fields.Bool(
        load_default=True,
        metadata={'description': 'Whether to extract companies'}
    )
    batchSize = fields.Int(
        load_default=100,
        validate=validate.Range(min=1, max=1000),
        metadata={'description': 'Batch size for API requests'}
    )
    maxRecords = fields.Int(
        load_default=10000,
        validate=validate.Range(min=1),
        metadata={'description': 'Maximum number of records to extract'}
    )

class FiltersSchema(Schema):
    """Schema for data filters"""
    dealStage = fields.List(
        fields.Str(),
        load_default=list,
        metadata={'description': 'Filter by deal stages'}
    )
    amountMin = fields.Float(
        allow_none=True,
        validate=validate.Range(min=0),
        metadata={'description': 'Minimum deal amount'}
    )
    amountMax = fields.Float(
        allow_none=True,
        validate=validate.Range(min=0),
        metadata={'description': 'Maximum deal amount'}
    )
    createdAfter = fields.Date(
        allow_none=True,
        metadata={'description': 'Filter records created after this date'}
    )
    createdBefore = fields.Date(
        allow_none=True,
        metadata={'description': 'Filter records created before this date'}
    )
    pipelineId = fields.Str(
        allow_none=True,
        metadata={'description': 'Filter by pipeline ID'}
    )
    priority = fields.List(
        fields.Str(validate=validate.OneOf(['HIGH', 'MEDIUM', 'LOW'])),
        load_default=list,
        metadata={'description': 'Filter by priority levels'}
    )
    category = fields.List(
        fields.Str(),
        load_default=list,
        metadata={'description': 'Filter by categories'}
    )

class OptionsSchema(Schema):
    """Schema for extraction options"""
    includeCustomProperties = fields.Bool(
        load_default=False,
        metadata={'description': 'Include custom properties in extraction'}
    )
    includeAssociations = fields.Bool(
        load_default=False,
        metadata={'description': 'Include object associations'}
    )
    includeStageHistory = fields.Bool(
        load_default=False,
        metadata={'description': 'Include deal stage history'}
    )

class ExtractionStartConfigSchema(Schema):
    """Schema for the main extraction configuration"""
    scanId = fields.Str(
        required=True,
        validate=[
            validate.Length(min=1, max=255),
            validate.Regexp(r'^[a-zA-Z0-9_-]+$', error='Invalid characters in scanId')
        ],
        metadata={'description': 'Unique identifier for this extraction scan'}
    )
    type = fields.List(
        fields.Str(validate=validate.OneOf(['deals', 'companies'])),
        load_default=['deals', 'companies'],
        metadata={'description': 'Types of data to extract'}
    )
    auth = fields.Nested(
        AuthConfigSchema,
        required=True,
        metadata={'description': 'Authentication configuration'}
    )
    extraction = fields.Nested(
        ExtractionConfigSchema,
        load_default=dict,
        metadata={'description': 'Extraction configuration'}
    )
    filters = fields.Nested(
        FiltersSchema,
        load_default=dict,
        metadata={'description': 'Data filtering options'}
    )
    options = fields.Nested(
        OptionsSchema,
        load_default=dict,
        metadata={'description': 'Additional extraction options'}
    )

class ExtractionStartSchema(Schema):
    """Schema for starting an extraction job"""
    config = fields.Nested(
        ExtractionStartConfigSchema,
        required=True,
        metadata={'description': 'Extraction configuration'}
    )
    
    @validates('config')
    def validate_config(self, value):
        if not isinstance(value, dict):
            raise ValidationError('Config must be a dictionary')

class ProgressSchema(Schema):
    """Schema for progress information"""
    percentage = fields.Int(
        validate=validate.Range(min=0, max=100),
        metadata={'description': 'Progress percentage (0-100)'}
    )
    recordsProcessed = fields.Int(
        metadata={'description': 'Number of records processed'}
    )
    recordsTotal = fields.Int(
        metadata={'description': 'Total number of records to process'}
    )
    currentOperation = fields.Str(
        metadata={'description': 'Description of current operation'}
    )

class ExtractionMetadataSchema(Schema):
    """Schema for extraction metadata"""
    totalEstimatedRecords = fields.Int(
        metadata={'description': 'Total estimated records to extract'}
    )
    estimatedDuration = fields.Str(
        metadata={'description': 'Estimated duration string'}
    )
    extractionTypes = fields.List(
        fields.Str(),
        metadata={'description': 'Types of data being extracted'}
    )
    companiesExtracted = fields.Int(
        metadata={'description': 'Number of companies extracted'}
    )
    dealsExtracted = fields.Int(
        metadata={'description': 'Number of deals extracted'}
    )
    pipelinesExtracted = fields.Int(
        metadata={'description': 'Number of pipelines extracted'}
    )
    batchesCompleted = fields.Int(
        metadata={'description': 'Number of batches completed'}
    )
    batchesTotal = fields.Int(
        metadata={'description': 'Total number of batches'}
    )

class ExtractionStatusSchema(Schema):
    """Schema for extraction status response"""
    scanId = fields.Str(
        metadata={'description': 'Scan identifier'}
    )
    status = fields.Str(
        validate=validate.OneOf(['started', 'running', 'completed', 'failed', 'cancelled']),
        metadata={'description': 'Current scan status'}
    )
    progress = fields.Nested(
        ProgressSchema,
        metadata={'description': 'Progress information'}
    )
    startedAt = fields.DateTime(
        format='iso8601',
        allow_none=True,
        metadata={'description': 'Scan start time'}
    )
    estimatedCompletion = fields.DateTime(
        format='iso8601',
        allow_none=True,
        metadata={'description': 'Estimated completion time'}
    )
    message = fields.Str(
        allow_none=True,
        metadata={'description': 'Status message'}
    )
    metadata = fields.Nested(
        ExtractionMetadataSchema,
        metadata={'description': 'Additional metadata'}
    )
    error = fields.Str(
        allow_none=True,
        metadata={'description': 'Error information if applicable'}
    )

class ExtractionSummarySchema(Schema):
    """Schema for extraction summary"""
    companies_count = fields.Int(
        metadata={'description': 'Number of companies extracted'}
    )
    deals_count = fields.Int(
        metadata={'description': 'Number of deals extracted'}
    )
    pipelines_count = fields.Int(
        metadata={'description': 'Number of pipelines extracted'}
    )
    custom_properties = fields.Int(
        metadata={'description': 'Number of custom properties extracted'}
    )
    associations = fields.Int(
        metadata={'description': 'Number of associations extracted'}
    )
    avg_processing_time_ms = fields.Float(
        metadata={'description': 'Average processing time in milliseconds'}
    )
    started_at = fields.DateTime(
        format='iso8601',
        metadata={'description': 'Extraction start time'}
    )
    completed_at = fields.DateTime(
        format='iso8601',
        metadata={'description': 'Extraction completion time'}
    )
    duration_seconds = fields.Int(
        metadata={'description': 'Total extraction duration in seconds'}
    )

class ExtractionDataSchema(Schema):
    """Schema for extraction data"""
    companies = fields.List(
        fields.Dict(),
        metadata={'description': 'List of extracted companies'}
    )
    deals = fields.List(
        fields.Dict(),
        metadata={'description': 'List of extracted deals'}
    )
    pipelines = fields.List(
        fields.Dict(),
        metadata={'description': 'List of extracted pipelines'}
    )

class ExtractionResultsSchema(Schema):
    """Schema for extraction results response"""
    scanId = fields.Str(
        metadata={'description': 'Scan identifier'}
    )
    status = fields.Str(
        metadata={'description': 'Scan status'}
    )
    total_records = fields.Int(
        metadata={'description': 'Total number of records extracted'}
    )
    extraction_summary = fields.Nested(
        ExtractionSummarySchema,
        metadata={'description': 'Extraction summary information'}
    )
    data = fields.Nested(
        ExtractionDataSchema,
        metadata={'description': 'Extracted data'}
    )
    metadata = fields.Dict(
        metadata={'description': 'Additional metadata including filters and options'}
    )

class SystemChecksSchema(Schema):
    """Schema for system health checks"""
    database = fields.Str(
        metadata={'description': 'Database connection status'}
    )
    database_pool = fields.Str(
        metadata={'description': 'Database connection pool status'}
    )
    thread_manager = fields.Str(
        metadata={'description': 'Thread manager status'}
    )
    active_extractions = fields.Str(
        metadata={'description': 'Active extractions status'}
    )
    memory_usage = fields.Str(
        metadata={'description': 'Memory usage information'}
    )
    disk_space = fields.Str(
        metadata={'description': 'Disk space information'}
    )

class SystemStatsSchema(Schema):
    """Schema for system statistics"""
    uptime_seconds = fields.Int(
        metadata={'description': 'System uptime in seconds'}
    )
    total_extractions_today = fields.Int(
        metadata={'description': 'Total extractions performed today'}
    )
    successful_extractions = fields.Int(
        metadata={'description': 'Number of successful extractions'}
    )
    failed_extractions = fields.Int(
        metadata={'description': 'Number of failed extractions'}
    )
    average_extraction_time = fields.Str(
        metadata={'description': 'Average extraction time'}
    )

class HealthCheckSchema(Schema):
    """Schema for health check response"""
    status = fields.Str(
        validate=validate.OneOf(['healthy', 'degraded', 'unhealthy']),
        metadata={'description': 'Overall health status'}
    )
    timestamp = fields.DateTime(
        format='iso8601',
        metadata={'description': 'Health check timestamp'}
    )
    service = fields.Str(
        metadata={'description': 'Service name'}
    )
    version = fields.Str(
        metadata={'description': 'Service version'}
    )
    checks = fields.Nested(
        SystemChecksSchema,
        metadata={'description': 'Individual health checks'}
    )
    system_stats = fields.Nested(
        SystemStatsSchema,
        metadata={'description': 'System statistics'}
    )

class ThreadStatusSchema(Schema):
    """Schema for thread status response"""
    thread_pool = fields.Dict(
        metadata={'description': 'Thread pool status information'}
    )
    active_extractions = fields.Int(
        metadata={'description': 'Number of active extraction threads'}
    )
    extraction_service = fields.Dict(
        metadata={'description': 'Extraction service status'}
    )

class ErrorResponseSchema(Schema):
    """Schema for error responses"""
    error = fields.Str(
        metadata={'description': 'Error type'}
    )
    message = fields.Str(
        metadata={'description': 'Error message'}
    )
    details = fields.Dict(
        allow_none=True,
        metadata={'description': 'Additional error details'}
    )
    timestamp = fields.DateTime(
        format='iso8601',
        metadata={'description': 'Error timestamp'}
    )

class ServiceInfoSchema(Schema):
    """Schema for service information"""
    name = fields.Str(
        metadata={'description': 'Service name'}
    )
    version = fields.Str(
        metadata={'description': 'Service version'}
    )
    uptime_seconds = fields.Int(
        metadata={'description': 'Service uptime in seconds'}
    )
    api_framework = fields.Str(
        metadata={'description': 'API framework used'}
    )

class ExtractionStatsSchema(Schema):
    """Schema for extraction statistics"""
    total_scans = fields.Int(
        metadata={'description': 'Total number of scans performed'}
    )
    successful_scans = fields.Int(
        metadata={'description': 'Number of successful scans'}
    )
    failed_scans = fields.Int(
        metadata={'description': 'Number of failed scans'}
    )
    cancelled_scans = fields.Int(
        metadata={'description': 'Number of cancelled scans'}
    )
    active_scans = fields.Int(
        metadata={'description': 'Number of currently active scans'}
    )
    queued_scans = fields.Int(
        metadata={'description': 'Number of queued scans'}
    )

class PerformanceStatsSchema(Schema):
    """Schema for performance statistics"""
    average_scan_duration_seconds = fields.Float(
        metadata={'description': 'Average scan duration in seconds'}
    )
    fastest_scan_duration_seconds = fields.Float(
        metadata={'description': 'Fastest scan duration in seconds'}
    )
    slowest_scan_duration_seconds = fields.Float(
        metadata={'description': 'Slowest scan duration in seconds'}
    )
    total_records_extracted = fields.Int(
        metadata={'description': 'Total records extracted across all scans'}
    )
    average_records_per_scan = fields.Float(
        metadata={'description': 'Average records per scan'}
    )

class DataBreakdownSchema(Schema):
    """Schema for data breakdown statistics"""
    companies_extracted = fields.Int(
        metadata={'description': 'Total companies extracted'}
    )
    deals_extracted = fields.Int(
        metadata={'description': 'Total deals extracted'}
    )
    pipelines_extracted = fields.Int(
        metadata={'description': 'Total pipelines extracted'}
    )

class SystemResourcesSchema(Schema):
    """Schema for system resources"""
    memory_usage_mb = fields.Float(
        metadata={'description': 'Memory usage in MB'}
    )
    memory_limit_mb = fields.Float(
        metadata={'description': 'Memory limit in MB'}
    )
    cpu_usage_percent = fields.Float(
        metadata={'description': 'CPU usage percentage'}
    )
    disk_usage_gb = fields.Float(
        metadata={'description': 'Disk usage in GB'}
    )
    disk_limit_gb = fields.Float(
        metadata={'description': 'Disk limit in GB'}
    )
    active_threads = fields.Int(
        metadata={'description': 'Number of active threads'}
    )
    max_threads = fields.Int(
        metadata={'description': 'Maximum number of threads'}
    )

class HubSpotAPIStatsSchema(Schema):
    """Schema for HubSpot API statistics"""
    requests_today = fields.Int(
        metadata={'description': 'Number of API requests made today'}
    )
    rate_limit_remaining = fields.Int(
        metadata={'description': 'Remaining rate limit'}
    )
    rate_limit_reset = fields.DateTime(
        format='iso8601',
        metadata={'description': 'Rate limit reset time'}
    )
    average_response_time_ms = fields.Float(
        metadata={'description': 'Average API response time in milliseconds'}
    )

class ServiceStatsSchema(Schema):
    """Schema for comprehensive service statistics"""
    service = fields.Nested(
        ServiceInfoSchema,
        metadata={'description': 'Service information'}
    )
    extractions = fields.Nested(
        ExtractionStatsSchema,
        metadata={'description': 'Extraction statistics'}
    )
    performance = fields.Nested(
        PerformanceStatsSchema,
        metadata={'description': 'Performance metrics'}
    )
    data_breakdown = fields.Nested(
        DataBreakdownSchema,
        metadata={'description': 'Data breakdown statistics'}
    )
    system_resources = fields.Nested(
        SystemResourcesSchema,
        metadata={'description': 'System resource usage'}
    )
    hubspot_api = fields.Nested(
        HubSpotAPIStatsSchema,
        metadata={'description': 'HubSpot API statistics'}
    )
    timestamp = fields.DateTime(
        format='iso8601',
        metadata={'description': 'Statistics timestamp'}
    )