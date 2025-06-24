"""Request validation middleware for Ethereum MCP Server.

This module provides comprehensive validation for all request parameters,
including Ethereum-specific formats, value ranges, and type checking.
"""

from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Union, TypeVar, cast
import re
from decimal import Decimal
from pydantic import BaseModel, Field, validator, ValidationError
from web3 import Web3
from eth_utils import is_checksum_address, to_checksum_address


# Type variable for decorated functions
F = TypeVar('F', bound=Callable[..., Any])


# Constants for validation
MAX_GAS_LIMIT = 30_000_000  # 30M gas - reasonable upper limit
MIN_GAS_PRICE = 0  # Allow 0 for EIP-1559 transactions
MAX_GAS_PRICE = 10_000_000_000_000  # 10,000 Gwei - reasonable upper limit
MAX_WEI_VALUE = 2**256 - 1  # Maximum uint256 value
PRIVATE_KEY_PATTERN = re.compile(r'^0x[a-fA-F0-9]{64}$')
HEX_PATTERN = re.compile(r'^0x[a-fA-F0-9]*$')
BLOCK_NUMBER_PATTERN = re.compile(r'^(0x[a-fA-F0-9]+|latest|pending|earliest|\d+)$')


# Validation Models using Pydantic
class EthereumAddress(str):
    """Validated Ethereum address with checksum validation."""
    
    @classmethod
    def __get_validators__(cls):
        yield cls.validate
    
    @classmethod
    def validate(cls, v: Any) -> str:
        if not isinstance(v, str):
            raise TypeError('Address must be a string')
        
        # Remove whitespace
        v = v.strip()
        
        # Check basic format
        if not v.startswith('0x') or len(v) != 42:
            raise ValueError('Address must be 42 characters long and start with 0x')
        
        # Check if it's a valid hex string
        try:
            int(v[2:], 16)
        except ValueError:
            raise ValueError('Address must be a valid hexadecimal string')
        
        # Validate checksum
        if not is_checksum_address(v):
            # Try to convert to checksum address
            try:
                return to_checksum_address(v)
            except Exception:
                raise ValueError('Invalid Ethereum address')
        
        return v


class PrivateKey(str):
    """Validated private key format."""
    
    @classmethod
    def __get_validators__(cls):
        yield cls.validate
    
    @classmethod
    def validate(cls, v: Any) -> str:
        if not isinstance(v, str):
            raise TypeError('Private key must be a string')
        
        v = v.strip()
        
        if not PRIVATE_KEY_PATTERN.match(v):
            raise ValueError('Private key must be 66 characters (0x + 64 hex chars)')
        
        return v


class HexString(str):
    """Validated hex string."""
    
    @classmethod
    def __get_validators__(cls):
        yield cls.validate
    
    @classmethod
    def validate(cls, v: Any) -> str:
        if not isinstance(v, str):
            raise TypeError('Hex string must be a string')
        
        v = v.strip()
        
        if not HEX_PATTERN.match(v):
            raise ValueError('Invalid hex string format')
        
        return v


class BlockIdentifier(str):
    """Validated block identifier (number, hex, or special values)."""
    
    @classmethod
    def __get_validators__(cls):
        yield cls.validate
    
    @classmethod
    def validate(cls, v: Any) -> str:
        if not isinstance(v, (str, int)):
            raise TypeError('Block identifier must be a string or integer')
        
        v_str = str(v).strip()
        
        if not BLOCK_NUMBER_PATTERN.match(v_str):
            raise ValueError('Invalid block identifier format')
        
        return v_str


class Wei(int):
    """Validated Wei value (non-negative, within bounds)."""
    
    @classmethod
    def __get_validators__(cls):
        yield cls.validate
    
    @classmethod
    def validate(cls, v: Any) -> int:
        if isinstance(v, str):
            # Handle hex strings
            if v.startswith('0x'):
                try:
                    v = int(v, 16)
                except ValueError:
                    raise ValueError('Invalid hex Wei value')
            else:
                try:
                    v = int(v)
                except ValueError:
                    raise ValueError('Invalid Wei value')
        elif not isinstance(v, int):
            raise TypeError('Wei value must be an integer or string')
        
        if v < 0:
            raise ValueError('Wei value cannot be negative')
        
        if v > MAX_WEI_VALUE:
            raise ValueError(f'Wei value exceeds maximum uint256 value')
        
        return v


class GasLimit(int):
    """Validated gas limit."""
    
    @classmethod
    def __get_validators__(cls):
        yield cls.validate
    
    @classmethod
    def validate(cls, v: Any) -> int:
        if isinstance(v, str):
            # Handle hex strings
            if v.startswith('0x'):
                try:
                    v = int(v, 16)
                except ValueError:
                    raise ValueError('Invalid hex gas limit')
            else:
                try:
                    v = int(v)
                except ValueError:
                    raise ValueError('Invalid gas limit')
        elif not isinstance(v, int):
            raise TypeError('Gas limit must be an integer or string')
        
        if v <= 0:
            raise ValueError('Gas limit must be positive')
        
        if v > MAX_GAS_LIMIT:
            raise ValueError(f'Gas limit exceeds maximum allowed value ({MAX_GAS_LIMIT})')
        
        return v


class GasPrice(int):
    """Validated gas price."""
    
    @classmethod
    def __get_validators__(cls):
        yield cls.validate
    
    @classmethod
    def validate(cls, v: Any) -> int:
        if isinstance(v, str):
            # Handle hex strings
            if v.startswith('0x'):
                try:
                    v = int(v, 16)
                except ValueError:
                    raise ValueError('Invalid hex gas price')
            else:
                try:
                    v = int(v)
                except ValueError:
                    raise ValueError('Invalid gas price')
        elif not isinstance(v, int):
            raise TypeError('Gas price must be an integer or string')
        
        if v < MIN_GAS_PRICE:
            raise ValueError(f'Gas price cannot be less than {MIN_GAS_PRICE}')
        
        if v > MAX_GAS_PRICE:
            raise ValueError(f'Gas price exceeds maximum allowed value ({MAX_GAS_PRICE} wei)')
        
        return v


# Validation schemas for different method types
class TransactionParams(BaseModel):
    """Base transaction parameters."""
    from_address: Optional[EthereumAddress] = Field(None, alias='from')
    to: Optional[EthereumAddress] = None
    value: Optional[Wei] = Field(default=0)
    gas: Optional[GasLimit] = Field(None, alias='gas')
    gasPrice: Optional[GasPrice] = Field(None, alias='gasPrice')
    maxFeePerGas: Optional[GasPrice] = Field(None, alias='maxFeePerGas')
    maxPriorityFeePerGas: Optional[GasPrice] = Field(None, alias='maxPriorityFeePerGas')
    data: Optional[HexString] = Field(default='0x')
    nonce: Optional[int] = Field(None, ge=0)
    
    @validator('maxFeePerGas', 'maxPriorityFeePerGas')
    def validate_eip1559(cls, v, values):
        """Validate EIP-1559 parameters."""
        if v is not None and values.get('gasPrice') is not None:
            raise ValueError('Cannot specify both gasPrice and EIP-1559 parameters')
        return v
    
    class Config:
        allow_population_by_field_name = True


class WalletCreateParams(BaseModel):
    """Parameters for wallet creation."""
    password: Optional[str] = None


class WalletImportParams(BaseModel):
    """Parameters for wallet import."""
    privateKey: PrivateKey
    password: Optional[str] = None


class ContractDeployParams(BaseModel):
    """Parameters for contract deployment."""
    bytecode: HexString
    abi: List[Dict[str, Any]]
    args: Optional[List[Any]] = Field(default_factory=list)
    from_address: EthereumAddress = Field(..., alias='from')
    gas: Optional[GasLimit] = None
    gasPrice: Optional[GasPrice] = None
    value: Optional[Wei] = Field(default=0)
    
    @validator('bytecode')
    def validate_bytecode(cls, v):
        """Ensure bytecode is not empty."""
        if len(v) <= 2:  # Just '0x'
            raise ValueError('Bytecode cannot be empty')
        return v
    
    @validator('abi')
    def validate_abi(cls, v):
        """Validate ABI structure."""
        if not v:
            raise ValueError('ABI cannot be empty')
        return v
    
    class Config:
        allow_population_by_field_name = True


class ContractCallParams(BaseModel):
    """Parameters for contract calls."""
    contractAddress: EthereumAddress
    method: str
    args: Optional[List[Any]] = Field(default_factory=list)
    from_address: Optional[EthereumAddress] = Field(None, alias='from')
    gas: Optional[GasLimit] = None
    gasPrice: Optional[GasPrice] = None
    value: Optional[Wei] = Field(default=0)
    
    class Config:
        allow_population_by_field_name = True


class EventFilterParams(BaseModel):
    """Parameters for event filters."""
    contractAddress: EthereumAddress
    eventName: str
    fromBlock: Optional[BlockIdentifier] = Field(default='latest')
    toBlock: Optional[BlockIdentifier] = Field(default='latest')
    filters: Optional[Dict[str, Any]] = Field(default_factory=dict)


# Validation decorator
def validate_request(schema: Optional[type[BaseModel]] = None):
    """Decorator to validate request parameters.
    
    Args:
        schema: Pydantic model class for validation
    
    Returns:
        Decorated function with validation
    """
    def decorator(func: F) -> F:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Extract params from kwargs or first positional arg
            params = kwargs.get('params', {})
            if not params and len(args) > 0:
                # Check if first arg is the params dict
                if isinstance(args[0], dict):
                    params = args[0]
            
            # Apply validation if schema provided
            if schema and params:
                try:
                    validated_params = schema(**params)
                    # Replace params with validated version
                    if 'params' in kwargs:
                        kwargs['params'] = validated_params.dict(by_alias=True, exclude_unset=True)
                    elif len(args) > 0 and isinstance(args[0], dict):
                        args = (validated_params.dict(by_alias=True, exclude_unset=True),) + args[1:]
                except ValidationError as e:
                    # Format validation errors nicely
                    errors = []
                    for error in e.errors():
                        field = ' -> '.join(str(x) for x in error['loc'])
                        msg = error['msg']
                        errors.append(f"{field}: {msg}")
                    
                    raise ValueError(f"Validation failed: {'; '.join(errors)}")
            
            # Call original function
            return await func(*args, **kwargs)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Extract params from kwargs or first positional arg
            params = kwargs.get('params', {})
            if not params and len(args) > 0:
                # Check if first arg is the params dict
                if isinstance(args[0], dict):
                    params = args[0]
            
            # Apply validation if schema provided
            if schema and params:
                try:
                    validated_params = schema(**params)
                    # Replace params with validated version
                    if 'params' in kwargs:
                        kwargs['params'] = validated_params.dict(by_alias=True, exclude_unset=True)
                    elif len(args) > 0 and isinstance(args[0], dict):
                        args = (validated_params.dict(by_alias=True, exclude_unset=True),) + args[1:]
                except ValidationError as e:
                    # Format validation errors nicely
                    errors = []
                    for error in e.errors():
                        field = ' -> '.join(str(x) for x in error['loc'])
                        msg = error['msg']
                        errors.append(f"{field}: {msg}")
                    
                    raise ValueError(f"Validation failed: {'; '.join(errors)}")
            
            # Call original function
            return func(*args, **kwargs)
        
        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return cast(F, async_wrapper)
        else:
            return cast(F, sync_wrapper)
    
    return decorator


# Utility functions for common validations
def sanitize_hex_input(hex_string: str) -> str:
    """Sanitize hex input to prevent injection.
    
    Args:
        hex_string: The hex string to sanitize
        
    Returns:
        Sanitized hex string
        
    Raises:
        ValueError: If invalid hex string
    """
    hex_string = hex_string.strip()
    
    if not HEX_PATTERN.match(hex_string):
        raise ValueError('Invalid hex string format')
    
    # Ensure even length for hex data
    if len(hex_string) % 2 != 0:
        hex_string = '0x0' + hex_string[2:]
    
    return hex_string.lower()


def validate_address_checksum(address: str) -> str:
    """Validate and return checksummed address.
    
    Args:
        address: The address to validate
        
    Returns:
        Checksummed address
        
    Raises:
        ValueError: If invalid address
    """
    try:
        return EthereumAddress.validate(address)
    except Exception as e:
        raise ValueError(f"Invalid address: {str(e)}")


def validate_transaction_params(params: Dict[str, Any]) -> Dict[str, Any]:
    """Validate transaction parameters.
    
    Args:
        params: Transaction parameters
        
    Returns:
        Validated parameters
        
    Raises:
        ValueError: If validation fails
    """
    try:
        tx_params = TransactionParams(**params)
        return tx_params.dict(by_alias=True, exclude_unset=True)
    except ValidationError as e:
        errors = []
        for error in e.errors():
            field = ' -> '.join(str(x) for x in error['loc'])
            msg = error['msg']
            errors.append(f"{field}: {msg}")
        raise ValueError(f"Transaction validation failed: {'; '.join(errors)}")


def validate_value_bounds(value: Union[int, str], min_val: int = 0, 
                         max_val: int = MAX_WEI_VALUE, 
                         param_name: str = "value") -> int:
    """Validate numeric value is within bounds.
    
    Args:
        value: The value to validate
        min_val: Minimum allowed value
        max_val: Maximum allowed value
        param_name: Name of parameter for error messages
        
    Returns:
        Validated integer value
        
    Raises:
        ValueError: If value out of bounds
    """
    try:
        int_value = Wei.validate(value)
    except Exception as e:
        raise ValueError(f"Invalid {param_name}: {str(e)}")
    
    if int_value < min_val:
        raise ValueError(f"{param_name} cannot be less than {min_val}")
    
    if int_value > max_val:
        raise ValueError(f"{param_name} cannot exceed {max_val}")
    
    return int_value


# Method-specific validation schemas mapping
METHOD_VALIDATION_SCHEMAS = {
    'eth_sendTransaction': TransactionParams,
    'eth_sendRawTransaction': None,  # Raw tx is already signed
    'wallet_create': WalletCreateParams,
    'wallet_import': WalletImportParams,
    'contract_deploy': ContractDeployParams,
    'contract_call': ContractCallParams,
    'contract_send': ContractCallParams,
    'event_subscribe': EventFilterParams,
    'event_getLogs': EventFilterParams,
}


def get_validation_schema(method: str) -> Optional[type[BaseModel]]:
    """Get validation schema for a method.
    
    Args:
        method: The method name
        
    Returns:
        Validation schema class or None
    """
    return METHOD_VALIDATION_SCHEMAS.get(method)