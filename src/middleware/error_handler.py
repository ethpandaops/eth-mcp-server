"""
Comprehensive error handling middleware for the Ethereum MCP Server.

This module provides centralized error handling, custom exception classes,
and structured error responses compatible with FastMCP.
"""

import logging
import traceback
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional, Union

from web3.exceptions import (
    ContractLogicError,
    InvalidAddress,
    NameNotFound,
    TimeExhausted,
    TransactionNotFound,
    ValidationError,
    Web3Exception,
)

logger = logging.getLogger(__name__)


class ErrorCode(str, Enum):
    """Enumeration of all possible error codes."""
    
    # Wallet errors
    WALLET_NOT_FOUND = "WALLET_NOT_FOUND"
    WALLET_ALREADY_EXISTS = "WALLET_ALREADY_EXISTS"
    
    # Address/Key errors
    INVALID_ADDRESS = "INVALID_ADDRESS"
    INVALID_PRIVATE_KEY = "INVALID_PRIVATE_KEY"
    
    # Transaction errors
    INSUFFICIENT_FUNDS = "INSUFFICIENT_FUNDS"
    NONCE_TOO_LOW = "NONCE_TOO_LOW"
    GAS_TOO_LOW = "GAS_TOO_LOW"
    TRANSACTION_FAILED = "TRANSACTION_FAILED"
    TRANSACTION_NOT_FOUND = "TRANSACTION_NOT_FOUND"
    
    # Contract errors
    CONTRACT_NOT_FOUND = "CONTRACT_NOT_FOUND"
    METHOD_NOT_FOUND = "METHOD_NOT_FOUND"
    INVALID_ABI = "INVALID_ABI"
    INVALID_PARAMETERS = "INVALID_PARAMETERS"
    
    # System errors
    INTERNAL_ERROR = "INTERNAL_ERROR"
    RATE_LIMITED = "RATE_LIMITED"


class MCPError(Exception):
    """Base exception class for all MCP server errors."""
    
    def __init__(
        self,
        code: ErrorCode,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        status_code: int = 500,
    ):
        self.code = code
        self.message = message
        self.details = details or {}
        self.status_code = status_code
        self.request_id = str(uuid.uuid4())
        self.timestamp = datetime.utcnow().isoformat() + "Z"
        super().__init__(message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary format."""
        return {
            "error": {
                "code": self.code.value,
                "message": self.message,
                "details": self.details,
                "request_id": self.request_id,
                "timestamp": self.timestamp,
            }
        }


# Custom exception classes for different error types

class WalletError(MCPError):
    """Base class for wallet-related errors."""
    pass


class WalletNotFoundError(WalletError):
    """Raised when a wallet is not found."""
    
    def __init__(self, wallet_name: str):
        super().__init__(
            code=ErrorCode.WALLET_NOT_FOUND,
            message=f"Wallet '{wallet_name}' not found",
            details={"wallet_name": wallet_name},
            status_code=404
        )


class WalletAlreadyExistsError(WalletError):
    """Raised when attempting to create a wallet that already exists."""
    
    def __init__(self, wallet_name: str):
        super().__init__(
            code=ErrorCode.WALLET_ALREADY_EXISTS,
            message=f"Wallet '{wallet_name}' already exists",
            details={"wallet_name": wallet_name},
            status_code=409
        )


class AddressError(MCPError):
    """Base class for address-related errors."""
    pass


class InvalidAddressError(AddressError):
    """Raised when an invalid Ethereum address is provided."""
    
    def __init__(self, address: str, reason: Optional[str] = None):
        super().__init__(
            code=ErrorCode.INVALID_ADDRESS,
            message=f"Invalid Ethereum address: {address}",
            details={"address": address, "reason": reason},
            status_code=400
        )


class InvalidPrivateKeyError(AddressError):
    """Raised when an invalid private key is provided."""
    
    def __init__(self, reason: Optional[str] = None):
        super().__init__(
            code=ErrorCode.INVALID_PRIVATE_KEY,
            message="Invalid private key",
            details={"reason": reason},
            status_code=400
        )


class TransactionError(MCPError):
    """Base class for transaction-related errors."""
    pass


class InsufficientFundsError(TransactionError):
    """Raised when account has insufficient funds for transaction."""
    
    def __init__(self, required: str, available: str, address: str):
        super().__init__(
            code=ErrorCode.INSUFFICIENT_FUNDS,
            message="Insufficient funds for transaction",
            details={
                "required": required,
                "available": available,
                "address": address
            },
            status_code=400
        )


class NonceTooLowError(TransactionError):
    """Raised when transaction nonce is too low."""
    
    def __init__(self, provided_nonce: int, expected_nonce: int):
        super().__init__(
            code=ErrorCode.NONCE_TOO_LOW,
            message=f"Nonce too low: provided {provided_nonce}, expected {expected_nonce}",
            details={
                "provided_nonce": provided_nonce,
                "expected_nonce": expected_nonce
            },
            status_code=400
        )


class GasTooLowError(TransactionError):
    """Raised when gas limit is too low."""
    
    def __init__(self, provided_gas: int, required_gas: int):
        super().__init__(
            code=ErrorCode.GAS_TOO_LOW,
            message=f"Gas limit too low: provided {provided_gas}, required at least {required_gas}",
            details={
                "provided_gas": provided_gas,
                "required_gas": required_gas
            },
            status_code=400
        )


class TransactionFailedError(TransactionError):
    """Raised when a transaction fails."""
    
    def __init__(self, tx_hash: str, reason: str):
        super().__init__(
            code=ErrorCode.TRANSACTION_FAILED,
            message=f"Transaction failed: {reason}",
            details={
                "transaction_hash": tx_hash,
                "reason": reason
            },
            status_code=500
        )


class TransactionNotFoundError(TransactionError):
    """Raised when a transaction is not found."""
    
    def __init__(self, tx_hash: str):
        super().__init__(
            code=ErrorCode.TRANSACTION_NOT_FOUND,
            message=f"Transaction not found: {tx_hash}",
            details={"transaction_hash": tx_hash},
            status_code=404
        )


class ContractError(MCPError):
    """Base class for contract-related errors."""
    pass


class ContractNotFoundError(ContractError):
    """Raised when a contract is not found."""
    
    def __init__(self, address: str):
        super().__init__(
            code=ErrorCode.CONTRACT_NOT_FOUND,
            message=f"Contract not found at address: {address}",
            details={"contract_address": address},
            status_code=404
        )


class MethodNotFoundError(ContractError):
    """Raised when a contract method is not found."""
    
    def __init__(self, method_name: str, contract_address: str):
        super().__init__(
            code=ErrorCode.METHOD_NOT_FOUND,
            message=f"Method '{method_name}' not found in contract",
            details={
                "method_name": method_name,
                "contract_address": contract_address
            },
            status_code=404
        )


class InvalidABIError(ContractError):
    """Raised when contract ABI is invalid."""
    
    def __init__(self, reason: str):
        super().__init__(
            code=ErrorCode.INVALID_ABI,
            message=f"Invalid contract ABI: {reason}",
            details={"reason": reason},
            status_code=400
        )


class InvalidParametersError(MCPError):
    """Raised when invalid parameters are provided."""
    
    def __init__(self, parameter_name: str, reason: str):
        super().__init__(
            code=ErrorCode.INVALID_PARAMETERS,
            message=f"Invalid parameter '{parameter_name}': {reason}",
            details={
                "parameter_name": parameter_name,
                "reason": reason
            },
            status_code=400
        )


class InternalError(MCPError):
    """Raised for internal server errors."""
    
    def __init__(self, message: str = "Internal server error"):
        super().__init__(
            code=ErrorCode.INTERNAL_ERROR,
            message=message,
            status_code=500
        )


class RateLimitedError(MCPError):
    """Raised when rate limit is exceeded."""
    
    def __init__(
        self,
        retry_after: int,
        limit: int,
        window: str,
        remaining: int = 0
    ):
        super().__init__(
            code=ErrorCode.RATE_LIMITED,
            message="Rate limit exceeded",
            details={
                "retry_after": retry_after,
                "limit": limit,
                "window": window,
                "remaining": remaining
            },
            status_code=429
        )


class ErrorHandler:
    """Central error handler for the MCP server."""
    
    def __init__(self, debug: bool = False):
        self.debug = debug
        self._request_context = {}
    
    def set_request_context(self, request_id: str, context: Dict[str, Any]):
        """Set context for current request."""
        self._request_context[request_id] = context
    
    def clear_request_context(self, request_id: str):
        """Clear context for completed request."""
        self._request_context.pop(request_id, None)
    
    def handle_error(
        self,
        error: Exception,
        request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Handle any exception and return structured error response.
        
        Args:
            error: The exception to handle
            request_id: Optional request ID for tracking
            
        Returns:
            Dictionary containing structured error response
        """
        if request_id is None:
            request_id = str(uuid.uuid4())
        
        # Get request context if available
        context = self._request_context.get(request_id, {})
        
        # Log the error with context
        logger.error(
            f"Error handling request {request_id}: {str(error)}",
            exc_info=True,
            extra={"request_id": request_id, "context": context}
        )
        
        # Handle MCP errors
        if isinstance(error, MCPError):
            return error.to_dict()
        
        # Handle Web3 exceptions
        if isinstance(error, InvalidAddress):
            mcp_error = InvalidAddressError(
                address=str(error),
                reason="Invalid checksum or format"
            )
            return mcp_error.to_dict()
        
        if isinstance(error, TransactionNotFound):
            tx_hash = str(error).split("'")[1] if "'" in str(error) else "unknown"
            mcp_error = TransactionNotFoundError(tx_hash=tx_hash)
            return mcp_error.to_dict()
        
        if isinstance(error, ContractLogicError):
            # Parse contract logic errors
            error_msg = str(error)
            if "insufficient funds" in error_msg.lower():
                mcp_error = InsufficientFundsError(
                    required="unknown",
                    available="unknown",
                    address=context.get("address", "unknown")
                )
            elif "nonce too low" in error_msg.lower():
                mcp_error = NonceTooLowError(
                    provided_nonce=0,
                    expected_nonce=0
                )
            else:
                mcp_error = TransactionFailedError(
                    tx_hash=context.get("tx_hash", "unknown"),
                    reason=error_msg
                )
            return mcp_error.to_dict()
        
        if isinstance(error, ValidationError):
            mcp_error = InvalidParametersError(
                parameter_name=context.get("parameter", "unknown"),
                reason=str(error)
            )
            return mcp_error.to_dict()
        
        if isinstance(error, TimeExhausted):
            mcp_error = TransactionFailedError(
                tx_hash=context.get("tx_hash", "unknown"),
                reason="Transaction timeout"
            )
            return mcp_error.to_dict()
        
        if isinstance(error, Web3Exception):
            # Generic Web3 exception
            mcp_error = InternalError(
                message=f"Web3 error: {str(error)}"
            )
            return mcp_error.to_dict()
        
        # Handle all other exceptions
        mcp_error = InternalError()
        error_dict = mcp_error.to_dict()
        
        # Add debug information if enabled
        if self.debug:
            error_dict["error"]["details"]["exception_type"] = type(error).__name__
            error_dict["error"]["details"]["exception_message"] = str(error)
            error_dict["error"]["details"]["traceback"] = traceback.format_exc()
        
        return error_dict


# Global error handler instance
error_handler = ErrorHandler()


def handle_mcp_error(func):
    """
    Decorator for handling errors in MCP server methods.
    
    Usage:
        @handle_mcp_error
        async def some_method(self, params):
            # Method implementation
    """
    async def wrapper(*args, **kwargs):
        request_id = str(uuid.uuid4())
        try:
            # Extract parameters for context
            params = kwargs.get("params", {})
            if len(args) > 1 and isinstance(args[1], dict):
                params = args[1]
            
            # Set request context
            error_handler.set_request_context(request_id, {
                "method": func.__name__,
                "params": params,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            # Execute the function
            result = await func(*args, **kwargs)
            
            # Clear context on success
            error_handler.clear_request_context(request_id)
            
            return result
            
        except Exception as e:
            # Handle the error
            error_response = error_handler.handle_error(e, request_id)
            
            # Clear context
            error_handler.clear_request_context(request_id)
            
            # Raise the error in a format compatible with FastMCP
            raise Exception(error_response["error"]["message"])
    
    return wrapper


def parse_web3_error(error: Union[Web3Exception, ContractLogicError]) -> MCPError:
    """
    Parse Web3 exceptions and convert to appropriate MCP errors.
    
    Args:
        error: The Web3 exception to parse
        
    Returns:
        Appropriate MCPError instance
    """
    error_msg = str(error).lower()
    
    # Check for common patterns
    if "insufficient funds" in error_msg:
        # Try to extract amounts from error message
        return InsufficientFundsError(
            required="unknown",
            available="unknown",
            address="unknown"
        )
    
    if "nonce too low" in error_msg:
        # Try to extract nonce values
        return NonceTooLowError(provided_nonce=0, expected_nonce=0)
    
    if "gas too low" in error_msg or "out of gas" in error_msg:
        return GasTooLowError(provided_gas=0, required_gas=0)
    
    if "invalid address" in error_msg:
        return InvalidAddressError(address="unknown")
    
    if "execution reverted" in error_msg:
        return TransactionFailedError(
            tx_hash="unknown",
            reason="Contract execution reverted"
        )
    
    # Default to internal error
    return InternalError(message=f"Web3 error: {str(error)}")