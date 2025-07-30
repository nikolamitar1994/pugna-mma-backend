"""
Logging Configuration for UFC Wikipedia Scraper
===============================================

Comprehensive logging setup for the Wikipedia scraper with structured
logging, error tracking, and performance monitoring.
"""

import logging
import logging.handlers
import os
import sys
from datetime import datetime
from typing import Dict, Any
from django.conf import settings


class ScraperFormatter(logging.Formatter):
    """Custom formatter for scraper logs with color support"""
    
    # Color codes for different log levels
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
        'ENDC': '\033[0m'       # End color
    }
    
    def __init__(self, use_colors=False):
        super().__init__()
        self.use_colors = use_colors
        
        # Format with detailed context
        self.detailed_format = (
            '%(asctime)s - %(name)s - %(levelname)s - '
            '[%(filename)s:%(lineno)d] - %(funcName)s() - %(message)s'
        )
        
        # Simple format for console
        self.simple_format = (
            '%(asctime)s - %(levelname)s - %(message)s'
        )
    
    def format(self, record):
        # Choose format based on logger name
        if 'scrapers' in record.name:
            fmt = self.detailed_format
        else:
            fmt = self.simple_format
        
        # Apply colors if enabled
        if self.use_colors and hasattr(record, 'levelname'):
            color = self.COLORS.get(record.levelname, '')
            record.levelname = f"{color}{record.levelname}{self.COLORS['ENDC']}"
        
        formatter = logging.Formatter(fmt)
        return formatter.format(record)


class ScraperStatsHandler(logging.Handler):
    """Custom handler to collect scraping statistics"""
    
    def __init__(self):
        super().__init__()
        self.stats = {
            'events_processed': 0,
            'fighters_created': 0,
            'errors_count': 0,
            'warnings_count': 0,
            'start_time': None,
            'end_time': None,
            'errors': [],
            'warnings': []
        }
    
    def emit(self, record):
        """Process log record and update statistics"""
        
        if not self.stats['start_time']:
            self.stats['start_time'] = datetime.now()
        
        # Count by level
        if record.levelno >= logging.ERROR:
            self.stats['errors_count'] += 1
            self.stats['errors'].append({
                'timestamp': datetime.now(),
                'message': record.getMessage(),
                'module': record.module,
                'function': record.funcName
            })
        elif record.levelno >= logging.WARNING:
            self.stats['warnings_count'] += 1
            self.stats['warnings'].append({
                'timestamp': datetime.now(),
                'message': record.getMessage(),
                'module': record.module
            })
        
        # Parse specific events from messages
        message = record.getMessage().lower()
        
        if 'created fighter:' in message:
            self.stats['fighters_created'] += 1
        elif 'created event:' in message or 'updated event:' in message:
            self.stats['events_processed'] += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """Get current statistics"""
        
        stats = self.stats.copy()
        stats['end_time'] = datetime.now()
        
        if stats['start_time']:
            duration = stats['end_time'] - stats['start_time']
            stats['duration_seconds'] = duration.total_seconds()
        
        return stats
    
    def reset_stats(self):
        """Reset statistics"""
        
        self.stats = {
            'events_processed': 0,
            'fighters_created': 0,
            'errors_count': 0,
            'warnings_count': 0,
            'start_time': None,
            'end_time': None,
            'errors': [],
            'warnings': []
        }


def setup_scraper_logging(
    log_level: str = 'INFO',
    log_file: str = None,
    use_colors: bool = True,
    enable_stats: bool = True
) -> Dict[str, Any]:
    """
    Setup comprehensive logging for UFC Wikipedia scraper
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_file: Path to log file (None for no file logging)
        use_colors: Enable colored console output
        enable_stats: Enable statistics collection
        
    Returns:
        Dictionary with logger configuration info
    """
    
    # Convert log level string to logging constant
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Get or create the main scraper logger
    logger = logging.getLogger('events.scrapers')
    logger.setLevel(numeric_level)
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Console handler with custom formatter
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_formatter = ScraperFormatter(use_colors=use_colors)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    handlers_info = {
        'console': {
            'level': log_level,
            'colors': use_colors,
            'formatter': 'ScraperFormatter'
        }
    }
    
    # File handler if specified
    if log_file:
        try:
            # Ensure log directory exists
            log_dir = os.path.dirname(log_file)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir)
            
            # Create rotating file handler
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=10*1024*1024,  # 10MB
                backupCount=5
            )
            file_handler.setLevel(numeric_level)
            
            # File formatter (no colors)
            file_formatter = ScraperFormatter(use_colors=False)
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)
            
            handlers_info['file'] = {
                'path': log_file,
                'level': log_level,
                'max_size': '10MB',
                'backup_count': 5
            }
            
        except Exception as e:
            logger.warning(f"Could not setup file logging: {e}")
    
    # Statistics handler
    stats_handler = None
    if enable_stats:
        stats_handler = ScraperStatsHandler()
        stats_handler.setLevel(logging.DEBUG)  # Capture all levels for stats
        logger.addHandler(stats_handler)
        
        handlers_info['stats'] = {
            'enabled': True,
            'handler': stats_handler
        }
    
    # Set up child loggers for different components
    components = [
        'events.scrapers.wikipedia_base',
        'events.scrapers.fighter_extractor',
        'events.scrapers.event_processor',
        'events.scrapers.wikipedia_ufc_scraper'
    ]
    
    for component in components:
        comp_logger = logging.getLogger(component)
        comp_logger.setLevel(numeric_level)
        # Child loggers will inherit handlers from parent
    
    # Log setup completion
    logger.info(f"Scraper logging initialized - Level: {log_level}")
    if log_file:
        logger.info(f"File logging enabled: {log_file}")
    
    return {
        'success': True,
        'level': log_level,
        'handlers': handlers_info,
        'stats_handler': stats_handler
    }


def get_scraper_logger(name: str = None) -> logging.Logger:
    """
    Get configured scraper logger
    
    Args:
        name: Logger name (defaults to events.scrapers)
        
    Returns:
        Configured logger instance
    """
    
    if name:
        return logging.getLogger(f'events.scrapers.{name}')
    else:
        return logging.getLogger('events.scrapers')


class LogContext:
    """Context manager for structured logging with additional context"""
    
    def __init__(self, logger: logging.Logger, operation: str, **context):
        self.logger = logger
        self.operation = operation
        self.context = context
        self.start_time = None
    
    def __enter__(self):
        self.start_time = datetime.now()
        
        context_str = ', '.join(f"{k}={v}" for k, v in self.context.items())
        self.logger.info(f"Starting {self.operation} - {context_str}")
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = datetime.now() - self.start_time
        duration_ms = int(duration.total_seconds() * 1000)
        
        if exc_type:
            self.logger.error(
                f"Failed {self.operation} after {duration_ms}ms - "
                f"Error: {exc_type.__name__}: {exc_val}"
            )
        else:
            self.logger.info(f"Completed {self.operation} in {duration_ms}ms")


class PerformanceLogger:
    """Logger for performance monitoring and metrics"""
    
    def __init__(self, logger: logging.Logger = None):
        self.logger = logger or get_scraper_logger('performance')
        self.metrics = {}
    
    def time_operation(self, operation_name: str):
        """Decorator for timing operations"""
        
        def decorator(func):
            def wrapper(*args, **kwargs):
                start_time = datetime.now()
                
                try:
                    result = func(*args, **kwargs)
                    
                    duration = datetime.now() - start_time
                    duration_ms = int(duration.total_seconds() * 1000)
                    
                    self.logger.debug(f"Operation '{operation_name}' completed in {duration_ms}ms")
                    
                    # Store metric
                    if operation_name not in self.metrics:
                        self.metrics[operation_name] = []
                    self.metrics[operation_name].append(duration_ms)
                    
                    return result
                    
                except Exception as e:
                    duration = datetime.now() - start_time
                    duration_ms = int(duration.total_seconds() * 1000)
                    
                    self.logger.error(f"Operation '{operation_name}' failed after {duration_ms}ms: {e}")
                    raise
            
            return wrapper
        return decorator
    
    def log_memory_usage(self, operation: str = ""):
        """Log current memory usage"""
        
        try:
            import psutil
            import os
            
            process = psutil.Process(os.getpid())
            memory_info = process.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024
            
            self.logger.debug(f"Memory usage {operation}: {memory_mb:.1f} MB")
            
        except ImportError:
            self.logger.debug("psutil not available for memory monitoring")
        except Exception as e:
            self.logger.debug(f"Could not get memory usage: {e}")
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance metrics summary"""
        
        summary = {}
        
        for operation, times in self.metrics.items():
            if times:
                summary[operation] = {
                    'count': len(times),
                    'total_ms': sum(times),
                    'avg_ms': sum(times) / len(times),
                    'min_ms': min(times),
                    'max_ms': max(times)
                }
        
        return summary


def configure_django_logging():
    """Configure Django logging settings for scraper"""
    
    # Ensure Django logging doesn't interfere
    if hasattr(settings, 'LOGGING'):
        # Add scraper-specific configuration to Django logging
        scraper_config = {
            'version': 1,
            'disable_existing_loggers': False,
            'formatters': {
                'scraper': {
                    '()': ScraperFormatter,
                    'use_colors': False
                }
            },
            'handlers': {
                'scraper_console': {
                    'level': 'INFO',
                    'class': 'logging.StreamHandler',
                    'formatter': 'scraper'
                }
            },
            'loggers': {
                'events.scrapers': {
                    'handlers': ['scraper_console'],
                    'level': 'INFO',
                    'propagate': False
                }
            }
        }
        
        # Merge with existing Django logging config
        if hasattr(settings, 'LOGGING'):
            # Update existing configuration
            for key, value in scraper_config.items():
                if key in settings.LOGGING:
                    settings.LOGGING[key].update(value)
                else:
                    settings.LOGGING[key] = value
        else:
            settings.LOGGING = scraper_config