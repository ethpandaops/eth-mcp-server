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
        elif param_type == 'bool':
            if not isinstance(filter_value, (bool, list)):
                raise ValueError(
                    f"Event '{event_name}' filter '{filter_name}' must be a boolean or list, "
                    f"got {type(filter_value).__name__}"
                )
            if isinstance(filter_value, list):
                for val in filter_value:
                    if val is not None and not isinstance(val, bool):
                        raise ValueError(
                            f"Event '{event_name}' filter '{filter_name}' list values must be booleans or None"
                        )
        elif param_type.startswith('bytes'):
            if not isinstance(filter_value, (str, bytes, list)):
                raise ValueError(
                    f"Event '{event_name}' filter '{filter_name}' must be a string, bytes, or list, "
                    f"got {type(filter_value).__name__}"
                )
            if isinstance(filter_value, str) and not filter_value.startswith('0x'):
                raise ValueError(
                    f"Event '{event_name}' filter '{filter_name}' must start with 0x"
                )
            elif isinstance(filter_value, list):
                for val in filter_value:
                    if val is not None:
                        if isinstance(val, str) and not val.startswith('0x'):
                            raise ValueError(
                                f"Event '{event_name}' filter '{filter_name}' list string values must start with 0x"
                            )