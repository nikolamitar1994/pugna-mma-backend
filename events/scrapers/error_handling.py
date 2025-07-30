"""
Error Handling and Recovery for UFC Wikipedia Scraper
=====================================================

Comprehensive error handling, retry logic, and recovery mechanisms
for robust Wikipedia scraping operations.
"""

import logging
import time
import traceback
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Type, Union
from datetime import datetime, timedelta
from django.db import transaction, IntegrityError
from django.core.exceptions import ValidationError
from requests.exceptions import RequestException, HTTPError, ConnectionError, Timeout

logger = logging.getLogger(__name__)


class ScraperError(Exception):
    """Base exception for scraper errors"""
    
    def __init__(self, message: str, original_error: Exception = None, context: Dict = None):
        super().__init__(message)
        self.original_error = original_error
        self.context = context or {}
        self.timestamp = datetime.now()
    
    def __str__(self):
        base_msg = super().__str__()
        if self.original_error:
            base_msg += f" (caused by {type(self.original_error).__name__}: {self.original_error})"
        return base_msg


class WikipediaAPIError(ScraperError):
    """Wikipedia API specific errors"""
    pass


class FighterExtractionError(ScraperError):
    """Fighter extraction specific errors"""
    pass


class EventProcessingError(ScraperError):
    """Event processing specific errors"""
    pass


class DatabaseError(ScraperError):
    """Database operation errors"""
    pass


class RetryableError(ScraperError):
    """Errors that can be retried"""
    pass


class NonRetryableError(ScraperError):
    """Errors that should not be retried"""
    pass


def classify_error(error: Exception) -> Type[ScraperError]:
    """
    Classify an exception into appropriate scraper error types
    
    Args:
        error: Original exception
        
    Returns:
        Appropriate ScraperError subclass
    """
    
    # Network and API errors (usually retryable)
    if isinstance(error, (ConnectionError, Timeout, HTTPError)):
        return RetryableError
    
    # Database integrity errors (usually not retryable)
    if isinstance(error, IntegrityError):
        return NonRetryableError
    
    # Validation errors (usually not retryable)
    if isinstance(error, ValidationError):
        return NonRetryableError
    
    # General request errors (might be retryable)
    if isinstance(error, RequestException):
        return RetryableError
    
    # Default to retryable
    return RetryableError


def retry_on_failure(
    max_retries: int = 3,
    delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: tuple = (Exception,)
):
    """
    Decorator for retrying functions on failure with exponential backoff
    
    Args:
        max_retries: Maximum number of retry attempts
        delay: Initial delay between retries (seconds)
        backoff_factor: Multiplier for delay between retries
        exceptions: Tuple of exceptions to catch and retry
    """
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                
                except exceptions as e:
                    last_exception = e
                    
                    # Classify the error
                    error_class = classify_error(e)
                    
                    # Don't retry non-retryable errors
                    if error_class == NonRetryableError:
                        logger.error(f"Non-retryable error in {func.__name__}: {e}")
                        raise
                    
                    # Don't retry on the last attempt
                    if attempt == max_retries:
                        break
                    
                    logger.warning(
                        f"Attempt {attempt + 1}/{max_retries + 1} failed for {func.__name__}: {e}. "
                        f"Retrying in {current_delay:.1f}s..."
                    )
                    
                    time.sleep(current_delay)
                    current_delay *= backoff_factor
            
            # All retries exhausted
            logger.error(f"All {max_retries + 1} attempts failed for {func.__name__}")
            raise last_exception
        
        return wrapper
    return decorator


class ErrorCollector:
    """Collects and categorizes errors during scraping operations"""
    
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.recovered_errors = []
        self.start_time = datetime.now()
    
    def add_error(self, error: Exception, context: Dict = None, severity: str = 'error'):
        """
        Add an error to the collection
        
        Args:
            error: The exception that occurred
            context: Additional context about when/where the error occurred
            severity: Error severity ('error', 'warning', 'critical')
        """
        
        error_record = {
            'timestamp': datetime.now(),
            'error': error,
            'error_type': type(error).__name__,
            'message': str(error),
            'context': context or {},
            'severity': severity,
            'traceback': traceback.format_exc()
        }
        
        if severity == 'warning':
            self.warnings.append(error_record)
            logger.warning(f"Warning: {error} - Context: {context}")
        else:
            self.errors.append(error_record)
            logger.error(f"Error: {error} - Context: {context}")
    
    def add_recovered_error(self, error: Exception, recovery_action: str, context: Dict = None):
        """
        Add an error that was successfully recovered from
        
        Args:
            error: The exception that was recovered from
            recovery_action: Description of how the error was handled
            context: Additional context
        """
        
        recovery_record = {
            'timestamp': datetime.now(),
            'error': error,
            'error_type': type(error).__name__,
            'message': str(error),
            'recovery_action': recovery_action,
            'context': context or {}
        }
        
        self.recovered_errors.append(recovery_record)
        logger.info(f"Recovered from error: {error} - Action: {recovery_action}")
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of collected errors"""
        
        duration = datetime.now() - self.start_time
        
        # Group errors by type
        error_types = {}
        for error_record in self.errors:
            error_type = error_record['error_type']
            if error_type not in error_types:
                error_types[error_type] = 0
            error_types[error_type] += 1
        
        return {
            'duration_seconds': duration.total_seconds(),
            'total_errors': len(self.errors),
            'total_warnings': len(self.warnings),
            'total_recovered': len(self.recovered_errors),
            'error_types': error_types,
            'has_critical_errors': any(e['severity'] == 'critical' for e in self.errors),
            'success_rate': self._calculate_success_rate()
        }
    
    def _calculate_success_rate(self) -> float:
        """Calculate approximate success rate based on errors and recoveries"""
        
        total_operations = len(self.errors) + len(self.recovered_errors) + 1  # +1 for successful operations estimate
        if total_operations == 0:
            return 1.0
        
        successful_operations = len(self.recovered_errors) + 1  # Recovered + estimated successful
        return successful_operations / total_operations
    
    def get_detailed_errors(self) -> List[Dict[str, Any]]:
        """Get detailed error information"""
        
        return self.errors.copy()
    
    def has_errors(self) -> bool:
        """Check if any errors were collected"""
        
        return len(self.errors) > 0
    
    def clear(self):
        """Clear all collected errors"""
        
        self.errors.clear()
        self.warnings.clear()
        self.recovered_errors.clear()
        self.start_time = datetime.now()


class SafeOperationContext:
    """Context manager for safe execution of scraping operations"""
    
    def __init__(self, 
                 operation_name: str,
                 error_collector: ErrorCollector = None,
                 continue_on_error: bool = True,
                 recovery_callback: Callable = None):
        self.operation_name = operation_name
        self.error_collector = error_collector or ErrorCollector()
        self.continue_on_error = continue_on_error
        self.recovery_callback = recovery_callback
        self.start_time = None
        self.success = False
    
    def __enter__(self):
        self.start_time = datetime.now()
        logger.info(f"Starting safe operation: {self.operation_name}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = datetime.now() - self.start_time
        duration_ms = int(duration.total_seconds() * 1000)
        
        if exc_type is None:
            self.success = True
            logger.info(f"Safe operation '{self.operation_name}' completed successfully in {duration_ms}ms")
            return True
        
        # Handle the exception
        context = {
            'operation': self.operation_name,
            'duration_ms': duration_ms
        }
        
        # Try recovery callback if provided
        if self.recovery_callback:
            try:
                recovery_result = self.recovery_callback(exc_val, context)
                if recovery_result:
                    self.error_collector.add_recovered_error(
                        exc_val, 
                        f"Recovery callback successful: {recovery_result}",
                        context
                    )
                    self.success = True
                    logger.info(f"Operation '{self.operation_name}' recovered from error")
                    return True  # Suppress the exception
            except Exception as recovery_error:
                logger.error(f"Recovery callback failed: {recovery_error}")
                self.error_collector.add_error(recovery_error, context, 'critical')
        
        # Add error to collector
        severity = 'critical' if not self.continue_on_error else 'error'
        self.error_collector.add_error(exc_val, context, severity)
        
        # Decide whether to suppress the exception
        if self.continue_on_error:
            logger.warning(f"Continuing after error in '{self.operation_name}': {exc_val}")
            return True  # Suppress the exception
        else:
            logger.error(f"Operation '{self.operation_name}' failed critically: {exc_val}")
            return False  # Let the exception propagate


def safe_database_operation(operation_name: str = "database operation"):
    """
    Decorator for safe database operations with transaction handling
    
    Args:
        operation_name: Name of the operation for logging
    """
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                with transaction.atomic():
                    logger.debug(f"Starting database operation: {operation_name}")
                    result = func(*args, **kwargs)
                    logger.debug(f"Database operation completed: {operation_name}")
                    return result
            
            except IntegrityError as e:
                logger.error(f"Database integrity error in {operation_name}: {e}")
                raise DatabaseError(
                    f"Integrity constraint violation in {operation_name}",
                    original_error=e,
                    context={'operation': operation_name}
                )
            
            except ValidationError as e:
                logger.error(f"Validation error in {operation_name}: {e}")
                raise DatabaseError(
                    f"Data validation failed in {operation_name}",
                    original_error=e,
                    context={'operation': operation_name}
                )
            
            except Exception as e:
                logger.error(f"Unexpected database error in {operation_name}: {e}")
                raise DatabaseError(
                    f"Database operation failed: {operation_name}",
                    original_error=e,
                    context={'operation': operation_name}
                )
        
        return wrapper
    return decorator


class CircuitBreaker:
    """
    Circuit breaker pattern implementation for failing operations
    
    Prevents cascading failures by temporarily disabling operations
    that are consistently failing.
    """
    
    def __init__(self, 
                 failure_threshold: int = 5,
                 timeout: int = 60,
                 expected_exception: Type[Exception] = Exception):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = 'CLOSED'  # CLOSED, OPEN, HALF_OPEN
    
    def __call__(self, func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            if self.state == 'OPEN':
                if self._should_attempt_reset():
                    self.state = 'HALF_OPEN'
                    logger.info(f"Circuit breaker for {func.__name__} moving to HALF_OPEN")
                else:
                    raise NonRetryableError(
                        f"Circuit breaker OPEN for {func.__name__}. "
                        f"Too many failures ({self.failure_count})"
                    )
            
            try:
                result = func(*args, **kwargs)
                self._on_success()
                return result
            
            except self.expected_exception as e:
                self._on_failure()
                raise
        
        return wrapper
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset"""
        
        if self.last_failure_time is None:
            return True
        
        time_passed = datetime.now() - self.last_failure_time
        return time_passed.total_seconds() > self.timeout
    
    def _on_success(self):
        """Handle successful operation"""
        
        self.failure_count = 0
        self.state = 'CLOSED'
        if self.last_failure_time:
            logger.info("Circuit breaker reset after successful operation")
            self.last_failure_time = None
    
    def _on_failure(self):
        """Handle failed operation"""
        
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.failure_count >= self.failure_threshold:
            self.state = 'OPEN'
            logger.warning(
                f"Circuit breaker OPEN after {self.failure_count} failures. "
                f"Will retry after {self.timeout} seconds."
            )


def handle_data_quality_issues(data: Dict[str, Any], required_fields: List[str]) -> Dict[str, Any]:
    """
    Handle data quality issues by providing defaults and validation
    
    Args:
        data: Data dictionary to validate
        required_fields: List of required field names
        
    Returns:
        Cleaned and validated data dictionary
    """
    
    cleaned_data = data.copy()
    issues = []
    
    # Check for required fields
    for field in required_fields:
        if field not in cleaned_data or cleaned_data[field] is None:
            issues.append(f"Missing required field: {field}")
            
            # Provide sensible defaults
            if field in ['name', 'event_name']:
                cleaned_data[field] = 'Unknown'
            elif field in ['date', 'event_date']:
                cleaned_data[field] = datetime.now().date()
            elif field.endswith('_count'):
                cleaned_data[field] = 0
            else:
                cleaned_data[field] = ''
    
    # Clean string fields
    for key, value in cleaned_data.items():
        if isinstance(value, str):
            # Remove excessive whitespace
            cleaned_data[key] = ' '.join(value.split())
            
            # Handle common encoding issues
            cleaned_data[key] = cleaned_data[key].encode('utf-8', errors='ignore').decode('utf-8')
    
    # Log data quality issues
    if issues:
        logger.warning(f"Data quality issues found: {issues}")
    
    return cleaned_data


class RobustScraperMixin:
    """
    Mixin class that adds robust error handling to scraper classes
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.error_collector = ErrorCollector()
        self.circuit_breakers = {}
    
    def get_circuit_breaker(self, operation_name: str) -> CircuitBreaker:
        """Get or create circuit breaker for operation"""
        
        if operation_name not in self.circuit_breakers:
            self.circuit_breakers[operation_name] = CircuitBreaker(
                failure_threshold=3,
                timeout=300  # 5 minutes
            )
        
        return self.circuit_breakers[operation_name]
    
    def safe_operation(self, operation_name: str, operation_func: Callable, *args, **kwargs):
        """Execute operation with full error handling"""
        
        circuit_breaker = self.get_circuit_breaker(operation_name)
        
        with SafeOperationContext(
            operation_name,
            error_collector=self.error_collector,
            continue_on_error=True
        ) as ctx:
            return circuit_breaker(operation_func)(*args, **kwargs)
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get summary of all errors encountered"""
        
        return self.error_collector.get_summary()
    
    def reset_error_tracking(self):
        """Reset error tracking"""
        
        self.error_collector.clear()
        self.circuit_breakers.clear()