import os
from dotenv import load_dotenv

load_dotenv()

class BaseConfig:
    """Base configuration class"""
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # Database configuration
    DATABASE_URL = os.getenv('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Application settings
    BATCH_SIZE = int(os.getenv('BATCH_SIZE', 100))
    REQUEST_TIMEOUT = int(os.getenv('REQUEST_TIMEOUT', 30))
    MAX_RETRIES = int(os.getenv('MAX_RETRIES', 3))
    
    # HubSpot API settings
    HUBSPOT_API_BASE_URL = 'https://api.hubapi.com'
    HUBSPOT_API_TIMEOUT = int(os.getenv('HUBSPOT_API_TIMEOUT', 30))
    HUBSPOT_COMPANY_URL = f'{HUBSPOT_API_BASE_URL}/crm/v3/objects/companies'
    HUBSPOT_DEAL_URL = f'{HUBSPOT_API_BASE_URL}/crm/v3/objects/deals'
    HUBSPOT_PIPELINE_URL = f'{HUBSPOT_API_BASE_URL}/crm/v3/pipelines/deals'
    
    # Default properties to extract
    COMPANY_PROPERTIES = os.getenv(
        'COMPANY_PROPERTIES', 
        'name,domain,industry,city,state,country,annualrevenue,numberofemployees,timezone,description,createdate'
    )
    DEAL_PROPERTIES = os.getenv(
        'DEAL_PROPERTIES', 
        'dealname,amount,pipeline,dealstage,closedate,createdate'
    )
    
    # Threading configuration
    MAX_WORKER_THREADS = int(os.getenv('MAX_WORKER_THREADS', 5))
    THREAD_POOL_SIZE = int(os.getenv('THREAD_POOL_SIZE', 10))
    
    # Logging configuration
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FORMAT = os.getenv('LOG_FORMAT', 'json')
    LOG_DIR = os.getenv('LOG_DIR', '/app/logs')
    LOG_FILE = os.getenv('LOG_FILE', 'app.jsonl')
    LOG_MAX_BYTES = int(os.getenv('LOG_MAX_BYTES', 10485760))  # 10MB
    LOG_BACKUP_COUNT = int(os.getenv('LOG_BACKUP_COUNT', 5))
    CONSOLE_LOGGING = os.getenv('CONSOLE_LOGGING', 'true').lower() == 'true'
    FILE_LOGGING = os.getenv('FILE_LOGGING', 'true').lower() == 'true'

class DevelopmentConfig(BaseConfig):
    """Development configuration"""
    DEBUG = True
    LOG_LEVEL = 'DEBUG'
    LOG_FORMAT = os.getenv('DEV_LOG_FORMAT', 'text')  # More readable format for development
    LOG_DIR = os.getenv('DEV_LOG_DIR', './logs')
    LOG_FILE = os.getenv('DEV_LOG_FILE', 'hubspot_extraction_dev.log')
    CONSOLE_LOGGING = True
    FILE_LOGGING = os.getenv('DEV_FILE_LOGGING', 'true').lower() == 'true'
    DATABASE_URL = os.getenv('DEV_DATABASE_URL', 'postgresql://user:password@localhost:5440/hubspot_dev')

class StagingConfig(BaseConfig):
    """Staging configuration"""
    DEBUG = False
    LOG_LEVEL = 'INFO'
    LOG_FORMAT = 'json'
    LOG_DIR = os.getenv('STAGING_LOG_DIR', '/app/logs')
    LOG_FILE = os.getenv('STAGING_LOG_FILE', 'hubspot_extraction_staging.jsonl')
    LOG_MAX_BYTES = int(os.getenv('STAGING_LOG_MAX_BYTES', 20971520))  # 20MB
    LOG_BACKUP_COUNT = int(os.getenv('STAGING_LOG_BACKUP_COUNT', 10))
    # FIXED: Use DATABASE_URL first, then fallback to staging-specific ones
    DATABASE_URL = os.getenv('DATABASE_URL') or os.getenv('STAGING_DATABASE_URL') or os.getenv('STAGE_DATABASE_URL')
    # Slightly more worker threads than dev but fewer than production
    MAX_WORKER_THREADS = int(os.getenv('MAX_WORKER_THREADS', 8))
    THREAD_POOL_SIZE = int(os.getenv('THREAD_POOL_SIZE', 16))

class ProductionConfig(BaseConfig):
    """Production configuration"""
    DEBUG = False
    LOG_LEVEL = 'WARNING'
    LOG_FORMAT = 'json'
    LOG_DIR = os.getenv('PROD_LOG_DIR', '/app/logs')
    LOG_FILE = os.getenv('PROD_LOG_FILE', 'hubspot_extraction.jsonl')
    LOG_MAX_BYTES = int(os.getenv('PROD_LOG_MAX_BYTES', 52428800))  # 50MB
    LOG_BACKUP_COUNT = int(os.getenv('PROD_LOG_BACKUP_COUNT', 20))
    # In production, we might want to disable console logging
    CONSOLE_LOGGING = os.getenv('PROD_CONSOLE_LOGGING', 'false').lower() == 'true'
    FILE_LOGGING = True
    DATABASE_URL = os.getenv('DATABASE_URL') or os.getenv('PROD_DATABASE_URL') or os.getenv('PRODUCTION_DATABASE_URL')

class TestingConfig(BaseConfig):
    """Testing configuration"""
    TESTING = True
    DEBUG = True
    LOG_LEVEL = 'DEBUG'
    LOG_FORMAT = 'text'  # More readable for tests
    LOG_DIR = os.getenv('TEST_LOG_DIR', './logs/test')
    LOG_FILE = os.getenv('TEST_LOG_FILE', 'hubspot_extraction_test.log')
    # For testing, we typically want console output but might disable file logging
    CONSOLE_LOGGING = True
    FILE_LOGGING = os.getenv('TEST_FILE_LOGGING', 'false').lower() == 'true'
    # Use environment variable first, fallback to docker network address
    DATABASE_URL = os.getenv('DATABASE_URL') or os.getenv('TEST_DATABASE_URL') or os.getenv('TESTING_DATABASE_URL') or 'postgresql://test_user:test_password@test_db:5432/test_db'

# Map environment names to configuration classes
# Include multiple key mappings for each environment for flexibility
config_map = {
    'development': DevelopmentConfig,
    'dev': DevelopmentConfig,
    
    'staging': StagingConfig,
    'stage': StagingConfig,
    
    'production': ProductionConfig,
    'prod': ProductionConfig,
    
    'testing': TestingConfig,
    'test': TestingConfig
}

def get_config():
    """Get configuration based on environment"""
    env = os.getenv('FLASK_ENV', 'development').lower()
    
    # Get the appropriate configuration class
    config_class = config_map.get(env, DevelopmentConfig)
    
    # Log the selected environment and database URL for debugging
    config_instance = config_class()
    print(f"Loading configuration for environment: {env}")
    print(f"DATABASE_URL configured: {config_instance.DATABASE_URL is not None}")
    if config_instance.DATABASE_URL:
        # Only show the part after @ for security
        db_url_safe = config_instance.DATABASE_URL.split('@')[-1] if '@' in config_instance.DATABASE_URL else 'local'
        print(f"Database target: {db_url_safe}")
    
    return config_instance