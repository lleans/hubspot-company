# app.py - Fixed version
import logging
import atexit
import signal
import os
import sys
from flask import Flask
from flask_cors import CORS
from flask_restx import Api
from config import get_config
from api.routes import scan_api as extraction_api
from models.database import init_db, check_db_connection

# Import the Loki logging framework
from loki_logger import (
    setup_loki_logging, 
    get_logger, 
    configure_flask_logging,
    log_performance,
    TimedOperation
)

def create_app(config_name=None):
    """Application factory"""
    app = Flask(__name__)
    
    # Load configuration
    config = get_config()
    app.config.from_object(config)
    
    # Debug: Print configuration to see what's loaded
    print(f"DEBUG: DATABASE_URL = {getattr(config, 'DATABASE_URL', 'NOT_SET')}")
    print(f"DEBUG: Config type = {type(config)}")
    
    # Initialize CORS - Fixed CORS configuration for Swagger
    CORS(app, origins="*", allow_headers=["Content-Type", "Authorization", "X-Request-ID"])
    
    # Initialize Flask-RESTX API with proper Swagger configuration - FIXED
    api = Api(
        app,
        version='1.0.0',
        title='HubSpot Extraction Service API',
        description='Robust HubSpot data extraction service with ThreadPoolExecutor-based concurrent processing and comprehensive job management',
        doc='/docs/',  # Make sure this route is accessible
        validate=True,
        prefix='',  # Add explicit prefix
        ordered=True,  # Keep endpoints ordered
        authorizations={
            'Bearer': {
                'type': 'apiKey',
                'in': 'header',
                'name': 'Authorization',
                'description': 'Add "Bearer " before your HubSpot API token'
            }
        },
    )
    
    # Register namespaces with explicit path - FIXED
    api.add_namespace(extraction_api, path='/scan')
    
    # Setup Loki logging
    setup_logging(getattr(config, 'LOG_LEVEL', 'INFO'))
    
    # Get logger after logging is setup
    logger = get_logger(__name__)
    
    # Initialize database with better error handling
    with app.app_context():
        try:
            # Check if DATABASE_URL is properly set
            if not hasattr(config, 'DATABASE_URL') or not config.DATABASE_URL:
                logger.error("DATABASE_URL is not configured in config object")
                logger.info(f"Available config attributes: {dir(config)}")
            else:
                logger.info(f"Initializing database with URL: {config.DATABASE_URL.split('@')[-1] if '@' in config.DATABASE_URL else 'local'}")
                init_db()
                logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}", exc_info=True)
    
    # Verify database connection with better error handling
    try:
        if check_db_connection():
            logger.info("Database connection successful")
        else:
            logger.error("Failed to connect to database on startup")
    except Exception as e:
        logger.error(f"Database connection check failed: {e}", exc_info=True)
    
    # Add a simple health check route to verify the app is working
    @app.route('/health-simple')
    def health_simple():
        return {'status': 'ok', 'message': 'Service is running'}, 200
    
    # Add route to redirect root to docs
    @app.route('/')
    def index():
        return {'message': 'HubSpot Extraction Service API', 'docs': '/docs/'}, 200
    
    return app

def setup_logging(log_level='INFO'):
    """Configure application logging with Loki integration"""
    try:
        # Setup Loki logging
        setup_loki_logging(
            service_name="hubspot-extraction-service",
            service_version="1.0.0",
            log_level=log_level,
            log_file="hubspot_extraction.jsonl",
            console_output=True,
            file_output=True
        )
        
        # Reduce noise from some libraries
        logging.getLogger('werkzeug').setLevel(logging.WARNING)
        logging.getLogger('requests').setLevel(logging.WARNING)
        
    except Exception as e:
        # Fallback to basic logging if Loki setup fails
        logging.basicConfig(
            level=getattr(logging, log_level.upper(), logging.INFO),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        print(f"Warning: Loki logging setup failed, using basic logging: {e}")

@log_performance("graceful_shutdown")
def graceful_shutdown():
    """Gracefully shutdown the extraction service"""
    logger = get_logger(__name__)
    
    try:
        logger.info(
            "Initiating graceful shutdown...",
            extra={
                "operation": "service_shutdown",
                "event_type": "lifecycle"
            }
        )
        
        # Import here to avoid circular imports
        try:
            from api.routes import extraction_service
            
            with TimedOperation(logger, "shutdown_executor_pool", 
                                component="extraction_service") as op:
                extraction_service.shutdown(wait=True, timeout=30.0)
        except ImportError as e:
            logger.warning(f"Could not import extraction_service for shutdown: {e}")
            
        logger.info(
            "Extraction service shutdown complete",
            extra={
                "operation": "service_shutdown",
                "status": "success",
                "event_type": "lifecycle"
            }
        )
    except Exception as e:
        logger.error(
            f"Error during extraction service shutdown: {str(e)}",
            extra={
                "operation": "service_shutdown",
                "status": "error",
                "error": str(e),
                "event_type": "lifecycle"
            },
            exc_info=True
        )
    
    logger.info("Shutdown complete", 
                extra={
                    "operation": "service_shutdown",
                    "phase": "complete",
                    "event_type": "lifecycle"
                })
    sys.exit(0)

# Register shutdown handlers
atexit.register(graceful_shutdown)
signal.signal(signal.SIGTERM, lambda sig, frame: graceful_shutdown())
signal.signal(signal.SIGINT, lambda sig, frame: graceful_shutdown())

def init_app():
    """Initialize and configure the application"""
    app = create_app()
    
    # Configure Flask-specific logging
    try:
        configure_flask_logging(
            app,
            service_name="hubspot-extraction-service",
            service_version="2.0.0"
        )
    except Exception as e:
        print(f"Warning: Flask logging configuration failed: {e}")
    
    return app

app = init_app()

if __name__ == '__main__':
    config = get_config()
    port = int(os.getenv('PORT', 4045))
    
    logger = get_logger(__name__)
    
    # Log application startup with rich context
    logger.info(
        f"Starting HubSpot Extraction Service on port {port}",
        extra={
            "operation": "service_startup",
            "port": port,
            "environment": os.getenv('ENVIRONMENT', 'development'),
            "debug_mode": getattr(config, 'DEBUG', False),
            "event_type": "lifecycle"
        }
    )
    
    logger.info(
        f"ThreadPoolExecutor-based concurrent processing enabled",
        extra={
            "operation": "service_startup",
            "feature": "concurrent_processing",
            "implementation": "ThreadPoolExecutor"
        }
    )
    
    logger.info(
        f"API Documentation available at: http://localhost:{port}/docs/",
        extra={
            "operation": "service_startup",
            "docs_url": f"http://localhost:{port}/docs/",
            "feature": "api_documentation"
        }
    )
    
    # Run the application
    app.run(
        host='0.0.0.0', 
        port=port,
        debug=getattr(config, 'DEBUG', False),
        threaded=True  # Enable threading for better concurrent handling
    )