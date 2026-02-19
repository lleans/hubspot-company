import time
import logging
from functools import wraps
from marshmallow import ValidationError
from flask import request, jsonify
from utils.exceptions import ServiceException

logger = logging.getLogger(__name__)

def retry_on_failure(max_retries=3, delay=1, backoff=2, exceptions=(Exception,)):
    """
    Decorator to retry function calls on failure with exponential backoff
    
    Args:
        max_retries: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        backoff: Backoff multiplier for delay
        exceptions: Tuple of exceptions to catch and retry
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            current_delay = delay
            
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    retries += 1
                    if retries >= max_retries:
                        logger.error(f"Function {func.__name__} failed after {max_retries} retries: {str(e)}")
                        raise e
                    
                    logger.warning(f"Attempt {retries} failed for {func.__name__}, retrying in {current_delay}s: {str(e)}")
                    time.sleep(current_delay)
                    current_delay *= backoff
            
        return wrapper
    return decorator

def validate_and_sanitize_input(schema_class):
    """
    Decorator to validate and sanitize input using Marshmallow schema
    
    Args:
        schema_class: Marshmallow schema class for validation
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                schema = schema_class()
                json_data = request.get_json()
                
                if json_data is None:
                    return jsonify({
                        'error': 'Validation failed',
                        'message': 'Request must contain JSON data'
                    }), 400
                
                validated_data = schema.load(json_data)
                return func(validated_data, *args, **kwargs)
                
            except ValidationError as err:
                logger.warning(f"Validation error in {func.__name__}: {err.messages}")
                return jsonify({
                    'error': 'Validation failed',
                    'message': 'Invalid request data',
                    'details': err.messages
                }), 400
                
            except Exception as e:
                logger.error(f"Unexpected error in validation decorator: {str(e)}")
                return jsonify({
                    'error': 'Internal server error',
                    'message': 'An unexpected error occurred during validation'
                }), 500
        
        return wrapper
    return decorator

def log_execution_time(func):
    """Decorator to log function execution time"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            logger.info(f"{func.__name__} executed in {execution_time:.2f} seconds")
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"{func.__name__} failed after {execution_time:.2f} seconds: {str(e)}")
            raise
    return wrapper

def handle_service_exceptions(func):
    """Decorator to handle service exceptions and return appropriate HTTP responses"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ValidationError as e:
            return jsonify({
                'error': 'Validation failed',
                'message': str(e)
            }), 400
        except ServiceException as e:
            return jsonify({
                'error': type(e).__name__,
                'message': e.message,
                'details': e.details
            }), 500
        except Exception as e:
            logger.error(f"Unexpected error in {func.__name__}: {str(e)}", exc_info=True)
            return jsonify({
                'error': 'Internal server error',
                'message': 'An unexpected error occurred'
            }), 500
    return wrapper