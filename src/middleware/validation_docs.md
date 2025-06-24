# Request Validation Middleware Documentation

## Overview

The request validation middleware provides comprehensive validation for all Ethereum-related parameters in the MCP server. It uses Pydantic for type validation and includes Ethereum-specific validators for addresses, private keys, transaction values, and more.

## Features

1. **Type Validation**: Automatic type checking and conversion
2. **Ethereum-Specific Validation**: 
   - Checksum validation for addresses
   - Private key format validation
   - Transaction value bounds checking
   - Gas parameter limits
   - Hex string format validation
3. **Decorator-Based**: Easy to apply using `@validate_request` decorator
4. **Clear Error Messages**: Detailed validation error messages
5. **Performance Optimized**: Minimal overhead with caching
6. **Injection Prevention**: Input sanitization to prevent attacks

## Usage

### Basic Usage with Decorator

```python
from src.middleware import validate_request, TransactionParams

@validate_request(TransactionParams)
async def send_transaction(params: dict):
    # params are now validated
    # Access validated parameters safely
    from_address = params['from']
    to_address = params['to']
    value = params.get('value', 0)
    # ... implementation
```

### Available Validation Models

#### TransactionParams
- `from`: Ethereum address (checksummed)
- `to`: Ethereum address (optional)
- `value`: Wei value (non-negative, max uint256)
- `gas`: Gas limit (max 30M)
- `gasPrice`: Gas price (max 10,000 Gwei)
- `maxFeePerGas`: EIP-1559 max fee
- `maxPriorityFeePerGas`: EIP-1559 priority fee
- `data`: Hex encoded data
- `nonce`: Transaction nonce (non-negative)

#### ContractDeployParams
- `bytecode`: Contract bytecode (hex)
- `abi`: Contract ABI (validated structure)
- `args`: Constructor arguments
- `from`: Deployer address
- `gas`: Gas limit
- `gasPrice`: Gas price
- `value`: ETH to send with deployment

#### ContractCallParams
- `contractAddress`: Target contract address
- `method`: Method name to call
- `args`: Method arguments
- `from`: Caller address (optional)
- `gas`: Gas limit
- `gasPrice`: Gas price
- `value`: ETH to send with call

#### WalletCreateParams
- `password`: Optional password for encryption

#### WalletImportParams
- `privateKey`: Private key (64 hex chars)
- `password`: Optional password

#### EventFilterParams
- `contractAddress`: Contract to monitor
- `eventName`: Event name to filter
- `fromBlock`: Starting block
- `toBlock`: Ending block
- `filters`: Additional filter parameters

### Manual Validation

```python
from src.middleware import validate_address_checksum, sanitize_hex_input

# Validate a single address
try:
    valid_addr = validate_address_checksum("0x742d35cc...")
except ValueError as e:
    print(f"Invalid address: {e}")

# Sanitize hex input
clean_hex = sanitize_hex_input("0xabcdef")
```

### Custom Validation Rules

```python
from src.middleware import TransactionParams
from pydantic import validator

class CustomTransactionParams(TransactionParams):
    @validator('value')
    def validate_minimum(cls, v):
        if v < 1000000000000000:  # 0.001 ETH
            raise ValueError('Minimum transaction is 0.001 ETH')
        return v

@validate_request(CustomTransactionParams)
async def send_with_minimum(params: dict):
    # Custom validation applied
    pass
```

## Validation Rules

### Ethereum Addresses
- Must be 42 characters (0x + 40 hex)
- Automatically converts to checksum format
- Validates checksum if provided

### Private Keys
- Must be 66 characters (0x + 64 hex)
- Format validation only (no cryptographic validation)

### Values (Wei)
- Non-negative integers
- Maximum value: 2^256 - 1
- Accepts hex strings (0x prefix)

### Gas Parameters
- Gas limit: 0 < limit ≤ 30,000,000
- Gas price: 0 ≤ price ≤ 10,000 Gwei
- EIP-1559 validation for maxFeePerGas/maxPriorityFeePerGas

### Block Identifiers
- Numeric block numbers
- Hex encoded numbers (0x prefix)
- Special values: 'latest', 'pending', 'earliest'

### Hex Strings
- Must start with 0x
- Valid hexadecimal characters only
- Automatically padded to even length

## Error Handling

Validation errors provide detailed information:

```python
try:
    result = await validated_method(invalid_params)
except ValueError as e:
    # e.g., "Validation failed: from: Invalid Ethereum address; value: Wei value cannot be negative"
    error_message = str(e)
```

## Performance Considerations

1. **Minimal Overhead**: Validation adds < 1ms per request
2. **Cached Validators**: Pydantic caches validation schemas
3. **Early Validation**: Fails fast on first error
4. **Optimized Patterns**: Compiled regex patterns

## Security Features

1. **Input Sanitization**: Prevents hex injection attacks
2. **Bounds Checking**: Prevents overflow/underflow
3. **Type Safety**: Prevents type confusion attacks
4. **Checksum Validation**: Prevents typosquatting

## Integration Example

```python
# In your server.py
from src.middleware import validate_request, get_validation_schema

@app.post("/mcp")
async def handle_mcp_request(request: MCPRequest) -> MCPResponse:
    # Get appropriate validation schema
    schema = get_validation_schema(request.method)
    
    if schema:
        # Apply validation
        @validate_request(schema)
        async def validated_handler(params):
            # Your existing handler logic
            return handle_method(request.method, params)
        
        result = await validated_handler(request.params)
    else:
        # No validation needed
        result = await handle_method(request.method, request.params)
    
    return MCPResponse(id=request.id, result=result)
```

## Best Practices

1. **Always Validate User Input**: Use validation for all external inputs
2. **Use Appropriate Models**: Choose the right validation model for each method
3. **Handle Errors Gracefully**: Catch and return meaningful error messages
4. **Extend When Needed**: Create custom validators for specific requirements
5. **Test Thoroughly**: Validate edge cases and invalid inputs