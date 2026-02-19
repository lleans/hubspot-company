"""
Loki logging configuration for applications
Provides structured JSON logging optimized for Loki ingestion with Grafana visualization
"""
import logging
import json
import os
import time
import uuid
from datetime import datetime
from functools import wraps
from typing import Dict, Any
from logging.handlers import RotatingFileHandler


class LokiJSONFormatter(logging.Formatter):
    """JSON formatter optimized for Loki ingestion"""
    
    def __init__(self, service_name: str = None, service_version: str = None):
        super().__init__()
        self.service_name = service_name or os.getenv('SERVICE_NAME', 'application')
        self.service_version = service_version or os.getenv('SERVICE_VERSION', '1.0.0')
        self.environment = os.getenv('ENVIRONMENT', os.getenv('FLASK_ENV', 'development'))
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON for Loki"""
        log_data = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'service': self.service_name,
            'environment': self.environment,
            'version': self.service_version,
            'thread': record.thread,
            'process': record.process
        }
        
        # Add custom fields if they exist
        custom_fields = [
            'request_id', 'trace_id', 'span_id', 'user_id', 'session_id',
            'operation', 'duration_ms', 'status_code', 'http_method',
            'endpoint', 'client_ip', 'user_agent', 'error_code',
            'batch_id', 'batch_size', 'page', 'total_processed',
            'retry_count', 'max_retries', 'api_endpoint', 'api_method',
            'response_size', 'memory_usage', 'cpu_usage', 'tenant_id',
            'correlation_id', 'event_type', 'business_event', 'security_event',
            'database_query_time', 'cache_hit', 'queue_size'
        ]
        
        for field in custom_fields:
            if hasattr(record, field):
                log_data[field] = getattr(record, field)
        
        # Add exception details if present
        if record.exc_info:
            log_data['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': self.formatException(record.exc_info)
            }
        
        # Add extra fields from logging call
        if hasattr(record, '__dict__'):
            for key, value in record.__dict__.items():
                if key not in log_data and not key.startswith('_') and key not in [
                    'name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                    'filename', 'module', 'lineno', 'funcName', 'created',
                    'msecs', 'relativeCreated', 'thread', 'threadName',
                    'processName', 'process', 'getMessage', 'exc_info',
                    'exc_text', 'stack_info'
                ]:
                    # Only add serializable values
                    try:
                        json.dumps(value)
                        log_data[key] = value
                    except (TypeError, ValueError):
                        log_data[key] = str(value)
        
        return json.dumps(log_data, ensure_ascii=False, default=str)


def get_log_level_for_env(explicit_level: str = None) -> int:
    """Get appropriate log level based on environment"""
    if explicit_level:
        return getattr(logging, explicit_level.upper(), logging.INFO)
    
    env = os.getenv('ENVIRONMENT', os.getenv('FLASK_ENV', 'development')).lower()
    
    log_levels = {
        'development': logging.DEBUG,    # Show everything for debugging
        'dev': logging.DEBUG,
        'testing': logging.WARNING,      # Reduce noise during tests  
        'test': logging.WARNING,
        'staging': logging.INFO,         # Normal operations
        'stage': logging.INFO,
        'production': logging.INFO,      # Optimized for observability
        'prod': logging.INFO
    }
    
    return log_levels.get(env, logging.INFO)


def setup_loki_logging(
    service_name: str = None,
    service_version: str = None,
    log_level: str = None,
    log_format: str = None,
    log_dir: str = None,
    log_file: str = None,
    console_output: bool = True,
    file_output: bool = True
) -> logging.Logger:
    """
    Setup logging configuration for Loki integration
    
    Args:
        service_name: Name of the service (default: from SERVICE_NAME env var)
        service_version: Version of the service (default: from SERVICE_VERSION env var)
        log_level: Explicit log level (default: environment-based)
        log_format: Log format 'json' or 'text' (default: from LOG_FORMAT env var)
        log_dir: Directory for log files (default: from LOG_DIR env var)
        log_file: Log file name (default: from LOG_FILE env var)
        console_output: Whether to output to console (default: True)
        file_output: Whether to output to file (default: True)
    
    Returns:
        Configured root logger
    """
    
    # Configuration from environment or parameters
    service_name = service_name or os.getenv('SERVICE_NAME', 'application')
    service_version = service_version or os.getenv('SERVICE_VERSION', '1.0.0')
    log_dir = log_dir or os.getenv('LOG_DIR', '/app/logs')
    log_file = log_file or os.getenv('LOG_FILE', 'app.jsonl')
    log_format = (log_format or os.getenv('LOG_FORMAT', 'json')).lower()
    
    # Ensure logs directory exists
    if file_output:
        os.makedirs(log_dir, exist_ok=True)
    
    # Get environment-specific log level
    env_log_level = get_log_level_for_env(log_level)
    env = os.getenv('ENVIRONMENT', os.getenv('FLASK_ENV', 'development')).lower()
    
    # Create formatters
    if log_format == 'json':
        json_formatter = LokiJSONFormatter(service_name, service_version)
        console_formatter = json_formatter  # Use JSON for console in production
    else:
        # Standard text formatter
        json_formatter = LokiJSONFormatter(service_name, service_version)
        console_formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        )
    
    # # Production console formatter (minimal)
    # if env == 'production' and console_output:
    #     console_formatter = logging.Formatter('%(levelname)s: %(message)s')
    
    # Clear existing handlers
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(logging.DEBUG)  # Root level always DEBUG
    
    # File handler for JSON logs (if enabled)
    if file_output:
        log_file_path = os.path.join(log_dir, log_file)
        max_bytes = int(os.getenv('LOG_MAX_BYTES', 10485760))  # 10MB default
        backup_count = int(os.getenv('LOG_BACKUP_COUNT', 5))
        
        file_handler = RotatingFileHandler(
            log_file_path,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setFormatter(json_formatter)
        file_handler.setLevel(logging.DEBUG)  # Always capture everything to file
        root_logger.addHandler(file_handler)
    
    # Console handler (if enabled)
    if console_output:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(console_formatter)
        console_handler.setLevel(env_log_level)
        root_logger.addHandler(console_handler)
    
    # Configure third-party library log levels
    third_party_loggers = {
        'watchdog': logging.WARNING,
        'werkzeug': logging.WARNING,
        'urllib3': logging.WARNING,
        'urllib3.connectionpool': logging.WARNING,
        'requests': logging.WARNING,
        'requests.packages.urllib3': logging.WARNING,
        'sqlalchemy.engine': logging.WARNING,
        'sqlalchemy.pool': logging.WARNING,
        'azure': logging.WARNING,
        'azure.core': logging.WARNING,
        'msal': logging.WARNING,
        'docker': logging.WARNING,
        'redis': logging.WARNING,
        'boto3': logging.WARNING,
        'botocore': logging.WARNING,
        's3transfer': logging.WARNING
    }
    
    if env in ['production', 'prod']:
        # Silence most third-party logs in production
        for logger_name in third_party_loggers:
            logging.getLogger(logger_name).setLevel(logging.ERROR)
    else:
        # Use configured levels for dev/test/staging
        for logger_name, level in third_party_loggers.items():
            logging.getLogger(logger_name).setLevel(level)
    
    # Log the configuration
    setup_logger = logging.getLogger(__name__)
    setup_logger.info(
        f"Logging configured for {env} environment",
        extra={
            'operation': 'logging_setup',
            'service': service_name,
            'version': service_version,
            'environment': env,
            'console_level': logging.getLevelName(env_log_level),
            'file_level': 'DEBUG' if file_output else 'DISABLED',
            'log_file': os.path.join(log_dir, log_file) if file_output else 'DISABLED',
            'log_format': log_format,
            'console_output': console_output,
            'file_output': file_output
        }
    )
    
    return root_logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger with consistent configuration"""
    return logging.getLogger(name)


def log_performance(operation_name: str):
    """Decorator for logging performance metrics"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger = get_logger(func.__module__)
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                end_time = time.time()
                duration_ms = (end_time - start_time) * 1000
                
                logger.info(
                    f"Performance: {operation_name} completed successfully",
                    extra={
                        'operation': operation_name,
                        'function': func.__name__,
                        'duration_ms': round(duration_ms, 2),
                        'status': 'success',
                        'event_type': 'performance'
                    }
                )
                
                return result
                
            except Exception as e:
                end_time = time.time()
                duration_ms = (end_time - start_time) * 1000
                
                logger.error(
                    f"Performance: {operation_name} failed",
                    extra={
                        'operation': operation_name,
                        'function': func.__name__,
                        'duration_ms': round(duration_ms, 2),
                        'status': 'error',
                        'error': str(e),
                        'event_type': 'performance'
                    },
                    exc_info=True
                )
                raise
                
        return wrapper
    return decorator


class ContextLogger:
    """Context manager for adding consistent logging context"""
    
    def __init__(self, logger: logging.Logger, **context):
        self.logger = logger
        self.context = context
        self.old_factory = None
    
    def __enter__(self) -> logging.Logger:
        self.old_factory = logging.getLogRecordFactory()
        
        def record_factory(*args, **kwargs):
            record = self.old_factory(*args, **kwargs)
            for key, value in self.context.items():
                setattr(record, key, value)
            return record
        
        logging.setLogRecordFactory(record_factory)
        return self.logger
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        logging.setLogRecordFactory(self.old_factory)


def generate_correlation_id() -> str:
    """Generate a unique correlation ID"""
    return str(uuid.uuid4())


def log_request_start(
    logger: logging.Logger, 
    request_id: str, 
    operation: str, 
    **extra_context
) -> None:
    """Log the start of a request/operation"""
    logger.info(
        f"Starting {operation}",
        extra={
            'request_id': request_id,
            'operation': f"{operation}_start",
            'phase': 'start',
            'event_type': 'request_lifecycle',
            **extra_context
        }
    )


def log_request_end(
    logger: logging.Logger, 
    request_id: str, 
    operation: str, 
    duration_ms: float = None, 
    status: str = 'success',
    **extra_context
) -> None:
    """Log the end of a request/operation"""
    extra = {
        'request_id': request_id,
        'operation': f"{operation}_end",
        'phase': 'end',
        'status': status,
        'event_type': 'request_lifecycle',
        **extra_context
    }
    
    if duration_ms is not None:
        extra['duration_ms'] = round(duration_ms, 2)
    
    log_level = logging.INFO if status == 'success' else logging.ERROR
    logger.log(
        log_level,
        f"Completed {operation} with status: {status}",
        extra=extra
    )


def log_business_event(
    logger: logging.Logger, 
    event_name: str, 
    **context
) -> None:
    """Log important business events"""
    logger.info(
        f"Business Event: {event_name}",
        extra={
            'operation': 'business_event',
            'event_name': event_name,
            'event_type': 'business',
            'business_event': event_name,
            **context
        }
    )


def log_security_event(
    logger: logging.Logger, 
    event_name: str, 
    severity: str = 'INFO', 
    **context
) -> None:
    """Log security-related events"""
    log_level = getattr(logging, severity.upper(), logging.INFO)
    
    logger.log(
        log_level,
        f"Security Event: {event_name}",
        extra={
            'operation': 'security_event',
            'event_name': event_name,
            'event_type': 'security',
            'security_event': event_name,
            'severity': severity,
            **context
        }
    )


def log_api_call(
    logger: logging.Logger,
    api_name: str,
    method: str = 'GET',
    status_code: int = None,
    duration_ms: float = None,
    endpoint: str = None,
    **context
) -> None:
    """Log external API calls"""
    extra = {
        'operation': 'api_call',
        'api_name': api_name,
        'api_method': method,
        'event_type': 'api_call',
        **context
    }
    
    if endpoint:
        extra['api_endpoint'] = endpoint
    if status_code is not None:
        extra['api_status_code'] = status_code
    if duration_ms is not None:
        extra['api_duration_ms'] = round(duration_ms, 2)
    
    message = f"API call: {method} {api_name}"
    if endpoint:
        message += f" -> {endpoint}"
    
    if status_code and status_code >= 400:
        logger.warning(f"{message} failed with status {status_code}", extra=extra)
    else:
        logger.info(f"{message} completed", extra=extra)


def log_database_operation(
    logger: logging.Logger,
    operation: str,
    table: str = None,
    query_type: str = None,
    duration_ms: float = None,
    affected_rows: int = None,
    **context
) -> None:
    """Log database operations"""
    extra = {
        'operation': 'database_operation',
        'db_operation': operation,
        'event_type': 'database',
        **context
    }
    
    if table:
        extra['db_table'] = table
    if query_type:
        extra['db_query_type'] = query_type
    if duration_ms is not None:
        extra['database_query_time'] = round(duration_ms, 2)
    if affected_rows is not None:
        extra['db_affected_rows'] = affected_rows
    
    message = f"Database operation: {operation}"
    if table:
        message += f" on {table}"
    
    logger.info(message, extra=extra)


def log_cache_operation(
    logger: logging.Logger,
    operation: str,
    cache_key: str,
    hit: bool = None,
    duration_ms: float = None,
    **context
) -> None:
    """Log cache operations"""
    extra = {
        'operation': 'cache_operation',
        'cache_operation': operation,
        'cache_key': cache_key,
        'event_type': 'cache',
        **context
    }
    
    if hit is not None:
        extra['cache_hit'] = hit
    if duration_ms is not None:
        extra['cache_duration_ms'] = round(duration_ms, 2)
    
    hit_status = 'hit' if hit else 'miss' if hit is not None else 'unknown'
    message = f"Cache {operation}: {cache_key} ({hit_status})"
    
    logger.debug(message, extra=extra)


def mask_sensitive_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Mask sensitive data in log context"""
    if not isinstance(data, dict):
        return data
    
    masked_data = data.copy()
    sensitive_fields = {
        'password', 'passwd', 'pwd', 'secret', 'token', 'key', 'auth',
        'authorization', 'credentials', 'credit_card', 'ssn', 'social_security',
        'api_key', 'private_key', 'access_token', 'refresh_token'
    }
    
    for key, value in masked_data.items():
        if any(sensitive in key.lower() for sensitive in sensitive_fields):
            if isinstance(value, str) and len(value) > 4:
                masked_data[key] = f"{value[:2]}***{value[-2:]}"
            else:
                masked_data[key] = "***MASKED***"
        elif key.lower() == 'email' and isinstance(value, str) and '@' in value:
            local, domain = value.split('@', 1)
            masked_data[key] = f"{local[:2]}***@{domain}"
    
    return masked_data


class TimedOperation:
    """Context manager for timing operations with automatic logging"""
    
    def __init__(self, logger: logging.Logger, operation_name: str, **context):
        self.logger = logger
        self.operation_name = operation_name
        self.context = context
        self.start_time = None
        self.request_id = context.get('request_id', generate_correlation_id())
    
    def __enter__(self):
        self.start_time = time.time()
        log_request_start(
            self.logger, 
            self.request_id, 
            self.operation_name, 
            **self.context
        )
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration_ms = (time.time() - self.start_time) * 1000
        status = 'success' if exc_type is None else 'error'
        
        extra_context = self.context.copy()
        if exc_type:
            extra_context.update({
                'error': str(exc_val),
                'error_type': exc_type.__name__
            })
        
        log_request_end(
            self.logger,
            self.request_id,
            self.operation_name,
            duration_ms=duration_ms,
            status=status,
            **extra_context
        )


def configure_flask_logging(app, **kwargs):
    """Configure Flask application logging with Loki"""
    if not app.debug:
        # Only setup Loki logging if not in debug mode
        setup_loki_logging(**kwargs)
    
    # Set app logger level based on config
    app.logger.setLevel(get_log_level_for_env())
    
    # Add request logging middleware
    @app.before_request
    def log_request_info():
        from flask import request, g
        g.request_id = request.headers.get('X-Request-ID', generate_correlation_id())
        g.start_time = time.time()
        
        app.logger.info(
            "HTTP request started",
            extra={
                'request_id': g.request_id,
                'http_method': request.method,
                'endpoint': request.endpoint or request.path,
                'client_ip': request.remote_addr,
                'user_agent': request.headers.get('User-Agent'),
                'operation': 'http_request_start',
                'event_type': 'http_request'
            }
        )
    
    @app.after_request
    def log_request_result(response):
        from flask import g
        duration_ms = (time.time() - g.start_time) * 1000
        
        app.logger.info(
            "HTTP request completed",
            extra={
                'request_id': g.request_id,
                'status_code': response.status_code,
                'duration_ms': round(duration_ms, 2),
                'operation': 'http_request_end',
                'event_type': 'http_request',
                'response_size': response.content_length
            }
        )
        
        return response
    
    return app.logger


# Export main functions
__all__ = [
    'setup_loki_logging',
    'get_logger',
    'log_performance',
    'ContextLogger',
    'log_request_start',
    'log_request_end',
    'log_business_event',
    'log_security_event',
    'log_api_call',
    'log_database_operation',
    'log_cache_operation',
    'mask_sensitive_data',
    'TimedOperation',
    'generate_correlation_id',
    'configure_flask_logging'
]