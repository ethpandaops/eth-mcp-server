"""Example usage of the request validation middleware.

This file demonstrates how to use the validation middleware in your methods.
"""

from src.middleware import (
    validate_request,
    validate_address_checksum,
    sanitize_hex_input,
    TransactionParams,
    ContractDeployParams,
    ContractCallParams,
)


# Example 1: Using the decorator on async functions
@validate_request(TransactionParams)
async def send_transaction(params: dict):
    """Send a transaction with validated parameters."""
    # At this point, all parameters have been validated
    print(f"Sending transaction from {params.get('from')} to {params.get('to')}")
    print(f"Value: {params.get('value', 0)} wei")
    print(f"Gas limit: {params.get('gas')}")
    # ... actual transaction logic here
    return {"txHash": "0x123..."}


# Example 2: Using the decorator on sync functions
@validate_request(ContractDeployParams)
def deploy_contract(params: dict):
    """Deploy a contract with validated parameters."""
    print(f"Deploying contract from {params['from']}")
    print(f"Bytecode length: {len(params['bytecode'])} chars")
    print(f"Constructor args: {params.get('args', [])}")
    # ... actual deployment logic here
    return {"address": "0xabc..."}


# Example 3: Using the decorator with contract calls
@validate_request(ContractCallParams)
async def call_contract_method(params: dict):
    """Call a contract method with validated parameters."""
    print(f"Calling method {params['method']} on {params['contractAddress']}")
    print(f"Arguments: {params.get('args', [])}")
    # ... actual contract call logic here
    return {"result": "0x456..."}


# Example 4: Manual validation without decorator
def manual_validation_example():
    """Example of manual parameter validation."""
    
    # Validate an address
    try:
        valid_address = validate_address_checksum("0x742d35Cc6634C0532925a3b844Bc9e7595f6AEd")
        print(f"Valid checksummed address: {valid_address}")
    except ValueError as e:
        print(f"Address validation error: {e}")
    
    # Sanitize hex input
    try:
        clean_hex = sanitize_hex_input("0xabcdef123")
        print(f"Sanitized hex: {clean_hex}")
    except ValueError as e:
        print(f"Hex validation error: {e}")
    
    # Validate transaction parameters manually
    tx_params = {
        "from": "0x742d35Cc6634C0532925a3b844Bc9e7595f6AEd",
        "to": "0x123d35Cc6634C0532925a3b844Bc9e7595f6AEd",
        "value": "1000000000000000000",  # 1 ETH in wei
        "gas": 21000,
        "gasPrice": "20000000000"  # 20 Gwei
    }
    
    try:
        validated = TransactionParams(**tx_params)
        print(f"Validated transaction: {validated.dict()}")
    except ValueError as e:
        print(f"Transaction validation error: {e}")


# Example 5: Handling validation errors
async def handle_validation_errors():
    """Example of handling validation errors gracefully."""
    
    @validate_request(TransactionParams)
    async def risky_transaction(params: dict):
        return {"success": True}
    
    # Invalid parameters
    invalid_params = {
        "from": "not_an_address",
        "value": -1000,  # Negative value
        "gas": 999999999  # Too high
    }
    
    try:
        result = await risky_transaction(params=invalid_params)
    except ValueError as e:
        # print(f"Caught validation error: {e}")  # Commented out for CI
        # Handle the error appropriately
        return {"error": str(e)}


# Example 6: Custom validation logic
class CustomTransactionValidator(TransactionParams):
    """Extended validator with custom rules."""
    
    @validator('value')
    def validate_minimum_value(cls, v):
        """Ensure minimum transaction value."""
        if v < 1000000000000000:  # Less than 0.001 ETH
            raise ValueError('Transaction value must be at least 0.001 ETH')
        return v
    
    @validator('to')
    def validate_not_blacklisted(cls, v):
        """Check address against blacklist."""
        blacklist = ["0x0000000000000000000000000000000000000000"]
        if v and v in blacklist:
            raise ValueError('Cannot send to blacklisted address')
        return v


@validate_request(CustomTransactionValidator)
async def send_transaction_custom(params: dict):
    """Send transaction with custom validation rules."""
    return {"txHash": "0xabc..."}


if __name__ == "__main__":
    # Run examples
    import asyncio
    
    print("=== Manual Validation Example ===")
    manual_validation_example()
    
    print("\n=== Async Validation Example ===")
    asyncio.run(send_transaction(params={
        "from": "0x742d35Cc6634C0532925a3b844Bc9e7595f6AEd",
        "to": "0x123d35Cc6634C0532925a3b844Bc9e7595f6AEd",
        "value": "1000000000000000000",
        "gas": 21000
    }))
    
    print("\n=== Error Handling Example ===")
    asyncio.run(handle_validation_errors())