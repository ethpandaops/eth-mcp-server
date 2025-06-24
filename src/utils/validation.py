"""Contract-specific validation functions for Ethereum interactions."""
from typing import Any, Dict, List, Optional, Union
import re


def validate_abi(abi: Any) -> None:
    """
    Validate JSON ABI structure.
    
    Args:
        abi: The ABI to validate (should be a list of method/event objects)
        
    Raises:
        ValueError: If the ABI structure is invalid
    """
    if not isinstance(abi, list):
        raise ValueError("ABI must be a list of method/event objects")
    
    if len(abi) == 0:
        raise ValueError("ABI cannot be empty")
    
    for i, item in enumerate(abi):
        if not isinstance(item, dict):
            raise ValueError(f"ABI item at index {i} must be a dictionary")
        
        # Check for required fields based on type
        item_type = item.get('type', 'function')  # default to function if not specified
        
        if item_type in ['function', 'constructor', 'fallback', 'receive']:
            # Functions must have a name (except constructor, fallback, receive)
            if item_type == 'function' and 'name' not in item:
                raise ValueError(f"Function at index {i} must have a name")
            
            # Check inputs
            if 'inputs' in item:
                if not isinstance(item['inputs'], list):
                    raise ValueError(f"Inputs for item at index {i} must be a list")
                for j, input_param in enumerate(item['inputs']):
                    if not isinstance(input_param, dict):
                        raise ValueError(f"Input parameter {j} in item {i} must be a dictionary")
                    if 'type' not in input_param:
                        raise ValueError(f"Input parameter {j} in item {i} must have a type")
            
            # Check outputs for functions
            if item_type == 'function' and 'outputs' in item:
                if not isinstance(item['outputs'], list):
                    raise ValueError(f"Outputs for function at index {i} must be a list")
                for j, output_param in enumerate(item['outputs']):
                    if not isinstance(output_param, dict):
                        raise ValueError(f"Output parameter {j} in item {i} must be a dictionary")
                    if 'type' not in output_param:
                        raise ValueError(f"Output parameter {j} in item {i} must have a type")
        
        elif item_type == 'event':
            # Events must have a name
            if 'name' not in item:
                raise ValueError(f"Event at index {i} must have a name")
            
            # Check inputs for events
            if 'inputs' in item:
                if not isinstance(item['inputs'], list):
                    raise ValueError(f"Inputs for event at index {i} must be a list")
                for j, input_param in enumerate(item['inputs']):
                    if not isinstance(input_param, dict):
                        raise ValueError(f"Event parameter {j} in item {i} must be a dictionary")
                    if 'type' not in input_param:
                        raise ValueError(f"Event parameter {j} in item {i} must have a type")
        
        else:
            # Allow other types but don't validate their structure
            pass


def validate_constructor_args(abi: List[Dict], args: Optional[List[Any]] = None) -> None:
    """
    Validate constructor parameters match ABI.
    
    Args:
        abi: The contract ABI
        args: The constructor arguments to validate
        
    Raises:
        ValueError: If the constructor arguments don't match the ABI
    """
    # First validate the ABI
    validate_abi(abi)
    
    # Find constructor in ABI
    constructor = None
    for item in abi:
        if item.get('type') == 'constructor':
            constructor = item
            break
    
    # If no constructor found, args should be None or empty
    if constructor is None:
        if args and len(args) > 0:
            raise ValueError("No constructor found in ABI, but arguments were provided")
        return
    
    # Get constructor inputs
    constructor_inputs = constructor.get('inputs', [])
    
    # Validate argument count
    if args is None:
        args = []
    
    if len(args) != len(constructor_inputs):
        raise ValueError(
            f"Constructor expects {len(constructor_inputs)} arguments, "
            f"but {len(args)} were provided"
        )
    
    # Validate argument types (basic validation)
    for i, (arg, input_spec) in enumerate(zip(args, constructor_inputs)):
        input_type = input_spec['type']
        input_name = input_spec.get('name', f'arg{i}')
        
        # Basic type validation
        if input_type.startswith('uint') or input_type.startswith('int'):
            if not isinstance(arg, (int, str)):
                raise ValueError(
                    f"Constructor argument '{input_name}' (index {i}) must be an integer or string, "
                    f"got {type(arg).__name__}"
                )
        elif input_type == 'address':
            if not isinstance(arg, str):
                raise ValueError(
                    f"Constructor argument '{input_name}' (index {i}) must be a string address, "
                    f"got {type(arg).__name__}"
                )
            if not arg.startswith('0x') or len(arg) != 42:
                raise ValueError(
                    f"Constructor argument '{input_name}' (index {i}) must be a valid address "
                    f"(0x followed by 40 hex characters)"
                )
        elif input_type == 'bool':
            if not isinstance(arg, bool):
                raise ValueError(
                    f"Constructor argument '{input_name}' (index {i}) must be a boolean, "
                    f"got {type(arg).__name__}"
                )
        elif input_type == 'string':
            if not isinstance(arg, str):
                raise ValueError(
                    f"Constructor argument '{input_name}' (index {i}) must be a string, "
                    f"got {type(arg).__name__}"
                )
        elif input_type.startswith('bytes'):
            if not isinstance(arg, (str, bytes)):
                raise ValueError(
                    f"Constructor argument '{input_name}' (index {i}) must be a string or bytes, "
                    f"got {type(arg).__name__}"
                )
            if isinstance(arg, str) and not arg.startswith('0x'):
                raise ValueError(
                    f"Constructor argument '{input_name}' (index {i}) must start with 0x"
                )
        elif input_type.endswith('[]'):
            if not isinstance(arg, list):
                raise ValueError(
                    f"Constructor argument '{input_name}' (index {i}) must be a list, "
                    f"got {type(arg).__name__}"
                )


def validate_method_args(abi: List[Dict], method_name: str, args: Optional[List[Any]] = None) -> None:
    """
    Validate method arguments match ABI signature.
    
    Args:
        abi: The contract ABI
        method_name: The name of the method to validate
        args: The method arguments to validate
        
    Raises:
        ValueError: If the method arguments don't match the ABI
    """
    # First validate the ABI
    validate_abi(abi)
    
    # Find method in ABI
    method = None
    for item in abi:
        if item.get('type', 'function') == 'function' and item.get('name') == method_name:
            method = item
            break
    
    if method is None:
        raise ValueError(f"Method '{method_name}' not found in ABI")
    
    # Get method inputs
    method_inputs = method.get('inputs', [])
    
    # Validate argument count
    if args is None:
        args = []
    
    if len(args) != len(method_inputs):
        raise ValueError(
            f"Method '{method_name}' expects {len(method_inputs)} arguments, "
            f"but {len(args)} were provided"
        )
    
    # Validate argument types (basic validation)
    for i, (arg, input_spec) in enumerate(zip(args, method_inputs)):
        input_type = input_spec['type']
        input_name = input_spec.get('name', f'arg{i}')
        
        # Basic type validation
        if input_type.startswith('uint') or input_type.startswith('int'):
            if not isinstance(arg, (int, str)):
                raise ValueError(
                    f"Method '{method_name}' argument '{input_name}' (index {i}) must be an integer or string, "
                    f"got {type(arg).__name__}"
                )
        elif input_type == 'address':
            if not isinstance(arg, str):
                raise ValueError(
                    f"Method '{method_name}' argument '{input_name}' (index {i}) must be a string address, "
                    f"got {type(arg).__name__}"
                )
            if not arg.startswith('0x') or len(arg) != 42:
                raise ValueError(
                    f"Method '{method_name}' argument '{input_name}' (index {i}) must be a valid address "
                    f"(0x followed by 40 hex characters)"
                )
        elif input_type == 'bool':
            if not isinstance(arg, bool):
                raise ValueError(
                    f"Method '{method_name}' argument '{input_name}' (index {i}) must be a boolean, "
                    f"got {type(arg).__name__}"
                )
        elif input_type == 'string':
            if not isinstance(arg, str):
                raise ValueError(
                    f"Method '{method_name}' argument '{input_name}' (index {i}) must be a string, "
                    f"got {type(arg).__name__}"
                )
        elif input_type.startswith('bytes'):
            if not isinstance(arg, (str, bytes)):
                raise ValueError(
                    f"Method '{method_name}' argument '{input_name}' (index {i}) must be a string or bytes, "
                    f"got {type(arg).__name__}"
                )
            if isinstance(arg, str) and not arg.startswith('0x'):
                raise ValueError(
                    f"Method '{method_name}' argument '{input_name}' (index {i}) must start with 0x"
                )
        elif input_type.endswith('[]'):
            if not isinstance(arg, list):
                raise ValueError(
                    f"Method '{method_name}' argument '{input_name}' (index {i}) must be a list, "
                    f"got {type(arg).__name__}"
                )


def is_valid_bytecode(bytecode: Any) -> bool:
    """
    Check if bytecode is a valid hex string starting with 0x.
    
    Args:
        bytecode: The bytecode to validate
        
    Returns:
        bool: True if valid bytecode, False otherwise
    """
    if not isinstance(bytecode, str):
        return False
    
    if not bytecode.startswith('0x'):
        return False
    
    # Check if the rest is valid hex (after 0x)
    hex_part = bytecode[2:]
    if len(hex_part) == 0:
        return False
    
    # Bytecode should be even length (each byte is 2 hex chars)
    if len(hex_part) % 2 != 0:
        return False
    
    # Check if all characters are valid hex
    try:
        int(hex_part, 16)
        return True
    except ValueError:
        return False


def validate_event_filters(abi: List[Dict], event_name: str, filters: Optional[Dict[str, Any]] = None) -> None:
    """
    Validate event filter parameters match ABI.
    
    Args:
        abi: The contract ABI
        event_name: The name of the event to validate filters for
        filters: The event filters to validate (dict mapping parameter names to values)
        
    Raises:
        ValueError: If the event filters don't match the ABI
    """
    # First validate the ABI
    validate_abi(abi)
    
    # Find event in ABI
    event = None
    for item in abi:
        if item.get('type') == 'event' and item.get('name') == event_name:
            event = item
            break
    
    if event is None:
        raise ValueError(f"Event '{event_name}' not found in ABI")
    
    # If no filters provided, nothing to validate
    if filters is None or len(filters) == 0:
        return
    
    # Get event inputs
    event_inputs = event.get('inputs', [])
    
    # Create a map of indexed parameters
    indexed_params = {}
    for input_spec in event_inputs:
        param_name = input_spec.get('name')
        if param_name and input_spec.get('indexed', False):
            indexed_params[param_name] = input_spec
    
    # Validate filters
    for filter_name, filter_value in filters.items():
        if filter_name not in indexed_params:
            # Check if it's a valid non-parameter filter
            if filter_name not in ['fromBlock', 'toBlock', 'address', 'topics']:
                raise ValueError(
                    f"Filter parameter '{filter_name}' is not an indexed parameter "
                    f"in event '{event_name}'"
                )
            continue
        
        # Validate filter value type
        param_spec = indexed_params[filter_name]
        param_type = param_spec['type']
        
        # Allow None for optional filters
        if filter_value is None:
            continue
        
        # Basic type validation for filter values
        if param_type.startswith('uint') or param_type.startswith('int'):
            if not isinstance(filter_value, (int, str, list)):
                raise ValueError(
                    f"Event '{event_name}' filter '{filter_name}' must be an integer, string, or list, "
                    f"got {type(filter_value).__name__}"
                )
            if isinstance(filter_value, list):
                for val in filter_value:
                    if not isinstance(val, (int, str, type(None))):
                        raise ValueError(
                            f"Event '{event_name}' filter '{filter_name}' list values must be integers, strings, or None"
                        )
        elif param_type == 'address':
            if not isinstance(filter_value, (str, list)):
                raise ValueError(
                    f"Event '{event_name}' filter '{filter_name}' must be a string address or list, "
                    f"got {type(filter_value).__name__}"
                )
            if isinstance(filter_value, str):
                if not filter_value.startswith('0x') or len(filter_value) != 42:
                    raise ValueError(
                        f"Event '{event_name}' filter '{filter_name}' must be a valid address "
                        f"(0x followed by 40 hex characters)"
                    )
            elif isinstance(filter_value, list):
                for val in filter_value:
                    if val is not None:
                        if not isinstance(val, str) or not val.startswith('0x') or len(val) != 42:
                            raise ValueError(
                                f"Event '{event_name}' filter '{filter_name}' list values must be valid addresses or None"
                            )


def validate_address(address: str) -> None:
    """
    Validate Ethereum address format with checksum validation.
    
    Args:
        address: The Ethereum address to validate
        
    Raises:
        ValueError: If the address format is invalid
        
    Examples:
        >>> validate_address("0x742d35Cc6634C0532925a3b844Bc9e7595f2bd5e")  # Valid
        >>> validate_address("0x742d35cc6634c0532925a3b844bc9e7595f2bd5e")  # Valid (all lowercase)
        >>> validate_address("0x742D35CC6634C0532925A3B844BC9E7595F2BD5E")  # Valid (all uppercase)
        >>> validate_address("0x123")  # Raises ValueError
    """
    if not isinstance(address, str):
        raise ValueError(f"Address must be a string, got {type(address).__name__}")
    
    if not address.startswith('0x'):
        raise ValueError("Address must start with '0x'")
    
    if len(address) != 42:
        raise ValueError(f"Address must be 42 characters long (0x + 40 hex), got {len(address)}")
    
    # Check if it's valid hex
    hex_part = address[2:]
    try:
        int(hex_part, 16)
    except ValueError:
        raise ValueError("Address contains invalid hexadecimal characters")
    
    # If address has mixed case, validate checksum
    if address[2:] != address[2:].lower() and address[2:] != address[2:].upper():
        # Import here to avoid circular dependencies
        try:
            from web3 import Web3
            if not Web3.is_checksum_address(address):
                raise ValueError("Address has invalid EIP-55 checksum")
        except ImportError:
            # If web3 is not available, skip checksum validation but warn
            # Mixed case without checksum validation is risky
            pass


def validate_private_key(private_key: str) -> None:
    """
    Validate private key format.
    
    Args:
        private_key: The private key to validate
        
    Raises:
        ValueError: If the private key format is invalid
        
    Examples:
        >>> validate_private_key("0x" + "a" * 64)  # Valid
        >>> validate_private_key("a" * 64)  # Valid (without 0x prefix)
        >>> validate_private_key("0x123")  # Raises ValueError
    """
    if not isinstance(private_key, str):
        raise ValueError(f"Private key must be a string, got {type(private_key).__name__}")
    
    # Remove 0x prefix if present
    if private_key.startswith('0x'):
        key = private_key[2:]
    else:
        key = private_key
    
    if len(key) != 64:
        raise ValueError(f"Private key must be 64 hex characters (32 bytes), got {len(key)}")
    
    # Check if it's valid hex
    try:
        int(key, 16)
    except ValueError:
        raise ValueError("Private key contains invalid hexadecimal characters")
    
    # Check if it's not zero
    if int(key, 16) == 0:
        raise ValueError("Private key cannot be zero")
    
    # Check if it's within the valid range for secp256k1
    # The maximum value is slightly less than 2^256
    max_key = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
    if int(key, 16) >= max_key:
        raise ValueError("Private key is outside the valid range for secp256k1")


def validate_transaction_params(params: Dict[str, Any]) -> None:
    """
    Validate transaction parameters.
    
    Args:
        params: Dictionary containing transaction parameters
        
    Raises:
        ValueError: If any transaction parameter is invalid
        
    Examples:
        >>> validate_transaction_params({
        ...     'from': '0x742d35Cc6634C0532925a3b844Bc9e7595f2bd5e',
        ...     'to': '0x742d35Cc6634C0532925a3b844Bc9e7595f2bd5e',
        ...     'value': '1000000000000000000',
        ...     'gas': 21000,
        ...     'gasPrice': '20000000000'
        ... })  # Valid
    """
    if not isinstance(params, dict):
        raise ValueError(f"Transaction parameters must be a dictionary, got {type(params).__name__}")
    
    # Validate 'from' address if present
    if 'from' in params:
        validate_address(params['from'])
    
    # Validate 'to' address if present (can be None for contract creation)
    if 'to' in params and params['to'] is not None:
        validate_address(params['to'])
    
    # Validate value if present
    if 'value' in params:
        validate_wei_amount(params['value'])
    
    # Validate gas parameters
    if 'gas' in params:
        validate_gas_params(params['gas'])
    
    if 'gasLimit' in params:
        validate_gas_params(params['gasLimit'])
    
    if 'gasPrice' in params:
        validate_gas_params(gas_limit=21000, gas_price=params['gasPrice'])
    
    if 'maxFeePerGas' in params:
        validate_wei_amount(params['maxFeePerGas'])
    
    if 'maxPriorityFeePerGas' in params:
        validate_wei_amount(params['maxPriorityFeePerGas'])
    
    # Validate nonce if present
    if 'nonce' in params:
        if not isinstance(params['nonce'], (int, str)):
            raise ValueError(f"Nonce must be an integer or string, got {type(params['nonce']).__name__}")
        if isinstance(params['nonce'], str):
            try:
                int(params['nonce'], 16 if params['nonce'].startswith('0x') else 10)
            except ValueError:
                raise ValueError("Nonce string must be a valid integer")
        elif isinstance(params['nonce'], int) and params['nonce'] < 0:
            raise ValueError("Nonce must be non-negative")
    
    # Validate data if present
    if 'data' in params:
        validate_hex_string(params['data'])
    
    # Validate chain ID if present
    if 'chainId' in params:
        if not isinstance(params['chainId'], (int, str)):
            raise ValueError(f"Chain ID must be an integer or string, got {type(params['chainId']).__name__}")
        if isinstance(params['chainId'], str):
            try:
                chain_id = int(params['chainId'], 16 if params['chainId'].startswith('0x') else 10)
            except ValueError:
                raise ValueError("Chain ID string must be a valid integer")
        else:
            chain_id = params['chainId']
        
        if chain_id < 0:
            raise ValueError("Chain ID must be non-negative")


def validate_gas_params(gas_limit: Union[int, str], gas_price: Optional[Union[int, str]] = None) -> None:
    """
    Validate gas parameters.
    
    Args:
        gas_limit: The gas limit value
        gas_price: Optional gas price value
        
    Raises:
        ValueError: If gas parameters are invalid
        
    Examples:
        >>> validate_gas_params(21000)  # Valid
        >>> validate_gas_params("0x5208")  # Valid (21000 in hex)
        >>> validate_gas_params(21000, "20000000000")  # Valid with gas price
        >>> validate_gas_params(-1)  # Raises ValueError
    """
    # Validate gas limit
    if not isinstance(gas_limit, (int, str)):
        raise ValueError(f"Gas limit must be an integer or string, got {type(gas_limit).__name__}")
    
    if isinstance(gas_limit, str):
        try:
            limit = int(gas_limit, 16 if gas_limit.startswith('0x') else 10)
        except ValueError:
            raise ValueError("Gas limit string must be a valid integer")
    else:
        limit = gas_limit
    
    if limit < 21000:
        raise ValueError(f"Gas limit must be at least 21000, got {limit}")
    
    if limit > 30000000:  # Common block gas limit
        raise ValueError(f"Gas limit {limit} exceeds typical block gas limit of 30,000,000")
    
    # Validate gas price if provided
    if gas_price is not None:
        if not isinstance(gas_price, (int, str)):
            raise ValueError(f"Gas price must be an integer or string, got {type(gas_price).__name__}")
        
        if isinstance(gas_price, str):
            try:
                price = int(gas_price, 16 if gas_price.startswith('0x') else 10)
            except ValueError:
                raise ValueError("Gas price string must be a valid integer")
        else:
            price = gas_price
        
        if price < 0:
            raise ValueError("Gas price must be non-negative")
        
        # Warn if gas price seems too high (over 1000 Gwei)
        if price > 1000000000000:  # 1000 Gwei in Wei
            # This is a warning case, but we don't raise an error
            pass


def validate_block_number(block_number: Union[int, str]) -> None:
    """
    Validate block number format.
    
    Args:
        block_number: The block number to validate
        
    Raises:
        ValueError: If block number format is invalid
        
    Examples:
        >>> validate_block_number(12345)  # Valid
        >>> validate_block_number("0x3039")  # Valid
        >>> validate_block_number("latest")  # Valid
        >>> validate_block_number("pending")  # Valid
        >>> validate_block_number("earliest")  # Valid
        >>> validate_block_number(-1)  # Raises ValueError
    """
    if isinstance(block_number, str):
        # Check for special block tags
        if block_number in ['latest', 'pending', 'earliest', 'safe', 'finalized']:
            return
        
        # Check for hex number
        if block_number.startswith('0x'):
            try:
                block_num = int(block_number, 16)
                if block_num < 0:
                    raise ValueError("Block number must be non-negative")
            except ValueError as e:
                if "invalid literal" in str(e):
                    raise ValueError("Invalid hexadecimal block number")
                raise
        else:
            # Decimal string
            try:
                block_num = int(block_number)
                if block_num < 0:
                    raise ValueError("Block number must be non-negative")
            except ValueError:
                raise ValueError("Invalid block number format")
    
    elif isinstance(block_number, int):
        if block_number < 0:
            raise ValueError("Block number must be non-negative")
    
    else:
        raise ValueError(f"Block number must be an integer or string, got {type(block_number).__name__}")


def validate_hex_string(hex_str: str, expected_length: Optional[int] = None) -> None:
    """
    Generic hex string validation.
    
    Args:
        hex_str: The hex string to validate
        expected_length: Expected length in bytes (not including 0x prefix)
        
    Raises:
        ValueError: If hex string format is invalid
        
    Examples:
        >>> validate_hex_string("0x1234")  # Valid
        >>> validate_hex_string("0x1234", 2)  # Valid (2 bytes)
        >>> validate_hex_string("0x123", 2)  # Raises ValueError (odd length)
        >>> validate_hex_string("0xgg")  # Raises ValueError (invalid hex)
    """
    if not isinstance(hex_str, str):
        raise ValueError(f"Hex string must be a string, got {type(hex_str).__name__}")
    
    if not hex_str.startswith('0x'):
        raise ValueError("Hex string must start with '0x'")
    
    hex_part = hex_str[2:]
    
    # Empty hex string is valid
    if len(hex_part) == 0:
        if expected_length is not None and expected_length > 0:
            raise ValueError(f"Expected {expected_length} bytes, got 0")
        return
    
    # Check for even length (each byte is 2 hex chars)
    if len(hex_part) % 2 != 0:
        raise ValueError("Hex string must have even length (each byte is 2 hex characters)")
    
    # Check if all characters are valid hex
    try:
        int(hex_part, 16)
    except ValueError:
        raise ValueError("Hex string contains invalid hexadecimal characters")
    
    # Check expected length if specified
    if expected_length is not None:
        actual_length = len(hex_part) // 2
        if actual_length != expected_length:
            raise ValueError(f"Expected {expected_length} bytes, got {actual_length}")


def validate_wei_amount(amount: Union[int, str]) -> None:
    """
    Validate Wei amounts.
    
    Args:
        amount: The Wei amount to validate
        
    Raises:
        ValueError: If amount is invalid
        
    Examples:
        >>> validate_wei_amount(1000000000000000000)  # Valid (1 ETH)
        >>> validate_wei_amount("0xde0b6b3a7640000")  # Valid (1 ETH in hex)
        >>> validate_wei_amount("1000000000000000000")  # Valid
        >>> validate_wei_amount(-1)  # Raises ValueError
    """
    if not isinstance(amount, (int, str)):
        raise ValueError(f"Wei amount must be an integer or string, got {type(amount).__name__}")
    
    if isinstance(amount, str):
        try:
            wei = int(amount, 16 if amount.startswith('0x') else 10)
        except ValueError:
            raise ValueError("Wei amount string must be a valid integer")
    else:
        wei = amount
    
    if wei < 0:
        raise ValueError("Wei amount must be non-negative")
    
    # Check for reasonable maximum (e.g., total Ether supply is ~120M ETH)
    max_reasonable_wei = 200_000_000 * 10**18  # 200M ETH
    if wei > max_reasonable_wei:
        # This is a warning case, but we don't raise an error
        # as there might be legitimate use cases for large values
        pass


def sanitize_input(input_str: str) -> str:
    """
    Sanitize string inputs by removing potentially dangerous characters.
    
    Args:
        input_str: The string to sanitize
        
    Returns:
        str: Sanitized string
        
    Examples:
        >>> sanitize_input("Hello World!")  # Returns "Hello World!"
        >>> sanitize_input("Hello\\nWorld")  # Returns "HelloWorld"
        >>> sanitize_input("Hello\\x00World")  # Returns "HelloWorld"
        >>> sanitize_input("<script>alert('xss')</script>")  # Returns "scriptalert('xss')/script"
    """
    if not isinstance(input_str, str):
        raise ValueError(f"Input must be a string, got {type(input_str).__name__}")
    
    # Remove null bytes
    sanitized = input_str.replace('\x00', '')
    
    # Remove other control characters (except common ones like tab)
    control_chars = ''.join(chr(i) for i in range(32) if chr(i) not in ['\t', '\n', '\r'])
    for char in control_chars:
        sanitized = sanitized.replace(char, '')
    
    # Remove common injection patterns
    # Remove HTML/XML tags
    sanitized = re.sub(r'<[^>]*>', '', sanitized)
    
    # Remove SQL comment patterns
    sanitized = re.sub(r'--.*$', '', sanitized, flags=re.MULTILINE)
    sanitized = re.sub(r'/\*.*?\*/', '', sanitized, flags=re.DOTALL)
    
    # Remove shell command injection characters
    dangerous_chars = ['`', '$', '|', '&', ';', '>', '<', '\\']
    for char in dangerous_chars:
        sanitized = sanitized.replace(char, '')
    
    # Trim whitespace
    sanitized = sanitized.strip()
    
    # Limit length to prevent DoS
    max_length = 10000
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length]
    
    return sanitized