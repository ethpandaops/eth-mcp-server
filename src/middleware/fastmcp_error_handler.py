"""
FastMCP-compatible error handling integration.

This module provides error handling that integrates with FastMCP's
tool decorator system.
"""

from functools import wraps
from typing import Any, Callable, Dict, Optional
import asyncio

from fastmcp import MCPError as FastMCPError

from .error_handler import (
    ErrorCode,
    MCPError,
    WalletNotFoundError,
    WalletAlreadyExistsError,
    InvalidAddressError,
    InvalidPrivateKeyError,
    InsufficientFundsError,
    NonceTooLowError,
    GasTooLowError,
    TransactionFailedError,
    TransactionNotFoundError,
    ContractNotFoundError,
    MethodNotFoundError,
    InvalidABIError,
    InvalidParametersError,
    InternalError,
    RateLimitedError,
    error_handler,
)


def mcp_error_to_fastmcp(error: MCPError) -> FastMCPError:
    """
    Convert our custom MCPError to FastMCP's MCPError format.
    
    Args:
        error: Our custom MCPError instance
        
    Returns:
        FastMCP-compatible error
    """
    error_dict = error.to_dict()["error"]
    return FastMCPError(
        code=error.status_code,
        message=error_dict["message"],
        data={
            "error_code": error_dict["code"],
            "details": error_dict["details"],
            "request_id": error_dict["request_id"],
            "timestamp": error_dict["timestamp"],
        }
    )


def fastmcp_error_handler(func: Callable) -> Callable:
    """
    Decorator for handling errors in FastMCP tool functions.
    
    This decorator catches exceptions and converts them to FastMCP-compatible
    errors with our structured error format.
    
    Usage:
        @mcp.tool()
        @fastmcp_error_handler
        async def my_tool(param: str) -> str:
            # Tool implementation
    """
    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except MCPError as e:
            # Convert our error to FastMCP error
            raise mcp_error_to_fastmcp(e)
        except Exception as e:
            # Handle unexpected errors
            error_response = error_handler.handle_error(e)
            internal_error = InternalError(str(e))
            internal_error.details = error_response["error"]["details"]
            raise mcp_error_to_fastmcp(internal_error)
    
    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except MCPError as e:
            # Convert our error to FastMCP error
            raise mcp_error_to_fastmcp(e)
        except Exception as e:
            # Handle unexpected errors
            error_response = error_handler.handle_error(e)
            internal_error = InternalError(str(e))
            internal_error.details = error_response["error"]["details"]
            raise mcp_error_to_fastmcp(internal_error)
    
    # Return appropriate wrapper based on function type
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper


class FastMCPErrorMiddleware:
    """
    Middleware class for integrating error handling with FastMCP server.
    
    Usage:
        from fastmcp import FastMCP
        from src.middleware.fastmcp_error_handler import FastMCPErrorMiddleware
        
        mcp = FastMCP("Ethereum MCP Server")
        error_middleware = FastMCPErrorMiddleware(debug=True)
        
        # Apply middleware to all tools
        mcp.add_middleware(error_middleware)
    """
    
    def __init__(self, debug: bool = False):
        """
        Initialize the middleware.
        
        Args:
            debug: Whether to include debug information in errors
        """
        error_handler.debug = debug
    
    async def __call__(self, request: Dict[str, Any], next_handler: Callable) -> Any:
        """
        Process the request through error handling.
        
        Args:
            request: The incoming request
            next_handler: The next handler in the chain
            
        Returns:
            The response or error
        """
        import uuid
        request_id = str(uuid.uuid4())
        
        try:
            # Set request context
            error_handler.set_request_context(request_id, {
                "method": request.get("method"),
                "params": request.get("params", {}),
            })
            
            # Process the request
            response = await next_handler(request)
            
            # Clear context on success
            error_handler.clear_request_context(request_id)
            
            return response
            
        except FastMCPError:
            # Re-raise FastMCP errors as-is
            error_handler.clear_request_context(request_id)
            raise
            
        except MCPError as e:
            # Convert our errors to FastMCP errors
            error_handler.clear_request_context(request_id)
            raise mcp_error_to_fastmcp(e)
            
        except Exception as e:
            # Handle unexpected errors
            error_response = error_handler.handle_error(e, request_id)
            error_handler.clear_request_context(request_id)
            
            internal_error = InternalError(str(e))
            internal_error.details = error_response["error"]["details"]
            raise mcp_error_to_fastmcp(internal_error)


# Export all error classes for easy import
__all__ = [
    "fastmcp_error_handler",
    "FastMCPErrorMiddleware",
    "mcp_error_to_fastmcp",
    "ErrorCode",
    "MCPError",
    "WalletNotFoundError",
    "WalletAlreadyExistsError",
    "InvalidAddressError",
    "InvalidPrivateKeyError",
    "InsufficientFundsError",
    "NonceTooLowError",
    "GasTooLowError",
    "TransactionFailedError",
    "TransactionNotFoundError",
    "ContractNotFoundError",
    "MethodNotFoundError",
    "InvalidABIError",
    "InvalidParametersError",
    "InternalError",
    "RateLimitedError",
]