class ServiceException(Exception):
    """Base exception for service errors"""
    def __init__(self, message, error_code=None, details=None):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)

class ExtractionServiceError(ServiceException):
    """Raised when extraction operations fail"""
    pass

class HubSpotAPIError(ServiceException):
    """Raised when HubSpot API calls fail"""
    def __init__(self, message, status_code=None, response=None):
        self.status_code = status_code
        self.response = response
        super().__init__(message)

class DatabaseError(ServiceException):
    """Raised when database operations fail"""
    pass

class ValidationError(ServiceException):
    """Raised when input validation fails"""
    pass

class AuthenticationError(ServiceException):
    """Raised when authentication fails"""
    pass

class ThreadManagerError(ServiceException):
    """Raised when thread management operations fail"""
    pass