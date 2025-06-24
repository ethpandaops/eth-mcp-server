"""
Structured logging configuration for Ethereum MCP Server.

Provides JSON-structured logging for production and human-readable format for development,
with support for request tracking, performance metrics, and async-safe operations.
"""

import json
import logging
import sys
import os
import time
from datetime import datetime
from typing import Any, Dict, Optional, Union
from pathlib import Path
from contextvars import ContextVar
from logging.handlers import RotatingFileHandler
from functools import wraps

# Context variable for request ID tracking
request_id_var: ContextVar[Optional[str]] = ContextVar('request_id', default=None)

# Configuration from environment
ENV = os.getenv('ENVIRONMENT', 'development')
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()
LOG_FILE = os.getenv('LOG_FILE', 'logs/eth-mcp-server.log')
MAX_LOG_SIZE = int(os.getenv('MAX_LOG_SIZE', '10485760'))  # 10MB default
BACKUP_COUNT = int(os.getenv('BACKUP_COUNT', '5'))


class StructuredFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        # Add request ID if available
        request_id = request_id_var.get()
        if request_id:
            log_data['request_id'] = request_id
        
        # Add any extra fields
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'created', 'filename', 'funcName',
                          'levelname', 'levelno', 'lineno', 'module', 'msecs',
                          'pathname', 'process', 'processName', 'relativeCreated',
                          'thread', 'threadName', 'getMessage', 'stack_info',
                          'exc_info', 'exc_text']:
                log_data[key] = value
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_data)


class HumanReadableFormatter(logging.Formatter):
    """Human-readable formatter for development."""
    
    def __init__(self):
        super().__init__(
            fmt='%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record with color coding for different levels."""
        # Color codes for different log levels
        colors = {
            'DEBUG': '\033[36m',    # Cyan
            'INFO': '\033[32m',     # Green
            'WARNING': '\033[33m',  # Yellow
            'ERROR': '\033[31m',    # Red
            'CRITICAL': '\033[35m', # Magenta
        }
        reset = '\033[0m'
        
        # Add request ID if available
        request_id = request_id_var.get()
        if request_id:
            record.msg = f"[{request_id[:8]}] {record.msg}"
        
        # Apply color if in development
        if ENV == 'development' and sys.stdout.isatty():
            levelname = record.levelname
            if levelname in colors:
                record.levelname = f"{colors[levelname]}{levelname}{reset}"
        
        return super().format(record)


def setup_logging():
    """Configure logging based on environment."""
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, LOG_LEVEL))
    
    # Remove existing handlers
    root_logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    
    # Choose formatter based on environment
    if ENV == 'production':
        formatter = StructuredFormatter()
    else:
        formatter = HumanReadableFormatter()
    
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # File handler for production
    if ENV == 'production' and LOG_FILE:
        # Create log directory if it doesn't exist
        log_dir = Path(LOG_FILE).parent
        log_dir.mkdir(parents=True, exist_ok=True)
        
        file_handler = RotatingFileHandler(
            LOG_FILE,
            maxBytes=MAX_LOG_SIZE,
            backupCount=BACKUP_COUNT
        )
        file_handler.setFormatter(StructuredFormatter())
        root_logger.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a specific module.
    
    Args:
        name: Module name (typically __name__)
        
    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)


def set_request_id(request_id: str):
    """Set the request ID for the current context."""
    request_id_var.set(request_id)


def clear_request_id():
    """Clear the request ID from the current context."""
    request_id_var.set(None)


class EthMCPLogger:
    """Enhanced logger with convenience methods for Ethereum MCP Server."""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
    
    def log_request(self, method: str, params: Optional[Dict[str, Any]] = None):
        """
        Log an incoming request.
        
        Args:
            method: RPC method name
            params: Request parameters
        """
        self.logger.info(
            f"Request: {method}",
            extra={
                'method': method,
                'params': params,
                'event': 'request_received'
            }
        )
    
    def log_response(self, method: str, result: Any, duration: float):
        """
        Log a successful response.
        
        Args:
            method: RPC method name
            result: Response result
            duration: Request duration in seconds
        """
        self.logger.info(
            f"Response: {method} completed in {duration:.3f}s",
            extra={
                'method': method,
                'duration': duration,
                'event': 'request_completed',
                'result_type': type(result).__name__
            }
        )
    
    def log_error(self, method: str, error: Exception, context: Optional[Dict[str, Any]] = None):
        """
        Log an error with context.
        
        Args:
            method: RPC method name
            error: Exception that occurred
            context: Additional error context
        """
        extra = {
            'method': method,
            'error_type': type(error).__name__,
            'event': 'request_error'
        }
        if context:
            extra.update(context)
        
        self.logger.error(
            f"Error in {method}: {str(error)}",
            exc_info=True,
            extra=extra
        )
    
    def log_performance(self, method: str, duration: float, gas_used: Optional[int] = None):
        """
        Log performance metrics.
        
        Args:
            method: RPC method name
            duration: Operation duration in seconds
            gas_used: Gas consumed (if applicable)
        """
        extra = {
            'method': method,
            'duration': duration,
            'event': 'performance_metric'
        }
        if gas_used is not None:
            extra['gas_used'] = gas_used
        
        self.logger.info(
            f"Performance: {method} - {duration:.3f}s" + 
            (f", gas: {gas_used}" if gas_used else ""),
            extra=extra
        )
    
    def debug(self, msg: str, **kwargs):
        """Debug level logging with extra context."""
        self.logger.debug(msg, extra=kwargs)
    
    def info(self, msg: str, **kwargs):
        """Info level logging with extra context."""
        self.logger.info(msg, extra=kwargs)
    
    def warning(self, msg: str, **kwargs):
        """Warning level logging with extra context."""
        self.logger.warning(msg, extra=kwargs)
    
    def error(self, msg: str, exc_info: bool = False, **kwargs):
        """Error level logging with extra context."""
        self.logger.error(msg, exc_info=exc_info, extra=kwargs)
    
    def critical(self, msg: str, **kwargs):
        """Critical level logging with extra context."""
        self.logger.critical(msg, extra=kwargs)


def get_eth_logger(name: str) -> EthMCPLogger:
    """
    Get an enhanced logger instance with Ethereum MCP-specific methods.
    
    Args:
        name: Module name (typically __name__)
        
    Returns:
        Enhanced logger instance
    """
    return EthMCPLogger(get_logger(name))


def log_timing(method_name: Optional[str] = None):
    """
    Decorator to log method execution time.
    
    Args:
        method_name: Optional custom method name for logging
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            logger = get_eth_logger(func.__module__)
            name = method_name or func.__name__
            
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                logger.log_response(name, result, duration)
                return result
            except Exception as e:
                duration = time.time() - start_time
                logger.log_error(name, e, {'duration': duration})
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            logger = get_eth_logger(func.__module__)
            name = method_name or func.__name__
            
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                logger.log_response(name, result, duration)
                return result
            except Exception as e:
                duration = time.time() - start_time
                logger.log_error(name, e, {'duration': duration})
                raise
        
        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


# Initialize logging on module import
setup_logging()


# Example usage
if __name__ == "__main__":
    # Example of using the logger
    logger = get_eth_logger(__name__)
    
    # Set a request ID for tracking
    set_request_id("req-12345")
    
    # Log various events
    logger.log_request("eth_getBalance", {"address": "0x123...", "block": "latest"})
    logger.log_response("eth_getBalance", "0x1234567890", 0.123)
    logger.log_performance("eth_call", 0.456, gas_used=21000)
    
    # Log with different levels
    logger.debug("Debug message", component="web3")
    logger.info("Processing block", block_number=12345678)
    logger.warning("High gas price", gas_price="100 gwei")
    
    # Log an error
    try:
        raise ValueError("Invalid address format")
    except Exception as e:
        logger.log_error("eth_sendTransaction", e, {"address": "0xinvalid"})
    
    # Clear request ID
    clear_request_id()