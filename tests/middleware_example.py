"""
Example demonstrating comprehensive middleware usage in an Ethereum MCP Server.

This example shows how to:
1. Set up error handling
2. Apply request validation
3. Format responses consistently
4. Handle streaming data
5. Track request IDs
"""

import asyncio
import json
from typing import Dict, Any, AsyncGenerator
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse

from src.middleware.error_handler import (
    ErrorHandler, handle_mcp_error, WalletNotFoundError,
    InvalidAddressError, TransactionFailedError
)
from src.middleware.request_validator import (
    validate_request, TransactionParams, ContractDeployParams,
    validate_address_checksum
)
from src.middleware.response_formatter import (
    ResponseFormatterMiddleware, StreamingFormatter
)


# Initialize components
app = FastAPI(title="Ethereum MCP Server Example")
error_handler = ErrorHandler(debug=True)

# Add response formatter middleware
app.add_middleware(
    ResponseFormatterMiddleware,
    chain_id=1,  # Mainnet
    compress_threshold=1024,
    pretty_print=True
)


# Example endpoints with full middleware stack

@app.post("/wallet/create")
@handle_mcp_error
async def create_wallet(request: Request, name: str, password: str = None):
    """Create a new wallet with error handling."""
    # Simulate wallet creation
    if name == "existing_wallet":
        raise WalletNotFoundError(name)
    
    return {
        "wallet": {
            "name": name,
            "address": "0x5aAeb6053F3E94C9b9A09f33669435E7Ef1BeAed",
            "created": True
        }
    }


@app.post("/transaction/send")
@handle_mcp_error
@validate_request(TransactionParams)
async def send_transaction(request: Request, params: Dict[str, Any]):
    """Send transaction with validation and error handling."""
    # Access validated params
    from_addr = params.get("from")
    to_addr = params.get("to")
    value = params.get("value", 0)
    
    # Simulate transaction
    if value > 1000000:
        raise TransactionFailedError(
            tx_hash="0x123abc",
            reason="Insufficient funds"
        )
    
    return {
        "transaction": {
            "hash": "0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
            "from": from_addr,
            "to": to_addr,
            "value": value,
            "status": "pending"
        }
    }


@app.post("/contract/deploy")
@handle_mcp_error
@validate_request(ContractDeployParams)
async def deploy_contract(request: Request, params: Dict[str, Any]):
    """Deploy contract with full validation."""
    # Access validated params
    bytecode = params["bytecode"]
    abi = params["abi"]
    from_addr = params["from"]
    
    # Simulate deployment
    return {
        "deployment": {
            "contract_address": "0x1234567890123456789012345678901234567890",
            "transaction_hash": "0xdeadbeef",
            "from": from_addr,
            "gas_used": 1500000
        }
    }


@app.get("/blocks/stream")
async def stream_blocks(request: Request, from_block: int = 0, to_block: int = 10):
    """Stream blocks with formatted response."""
    formatter = StreamingFormatter(chain_id=1, chunk_size=5)
    
    async def generate_blocks():
        for i in range(from_block, to_block + 1):
            yield {
                "number": i,
                "hash": f"0x{'0' * 62}{i:02x}",
                "timestamp": 1234567890 + i * 12,
                "transactions": []
            }
            await asyncio.sleep(0.1)  # Simulate network delay
    
    # Request ID is set by middleware
    request_id = getattr(request.state, "request_id", "unknown")
    
    return formatter.create_streaming_response(
        generate_blocks(),
        request_id=request_id,
        item_type="blocks",
        compress=True
    )


@app.get("/address/{address}/validate")
@handle_mcp_error
async def validate_address(address: str):
    """Validate an Ethereum address."""
    try:
        checksummed = validate_address_checksum(address)
        return {
            "valid": True,
            "address": address,
            "checksummed": checksummed,
            "is_contract": False  # Would check on-chain
        }
    except ValueError as e:
        raise InvalidAddressError(address, str(e))


# Example of custom error handling
@app.exception_handler(MCPError)
async def mcp_exception_handler(request: Request, exc: MCPError):
    """Custom handler for MCP errors."""
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict()
    )


# Example client code
async def example_client():
    """Example client demonstrating middleware features."""
    import httpx
    
    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        # 1. Create wallet (with error handling)
        try:
            response = await client.post(
                "/wallet/create",
                params={"name": "test_wallet", "password": "secret"}
            )
            print("Wallet created:", response.json())
        except httpx.HTTPStatusError as e:
            print("Error creating wallet:", e.response.json())
        
        # 2. Send transaction (with validation)
        tx_params = {
            "from": "0x5aAeb6053F3E94C9b9A09f33669435E7Ef1BeAed",
            "to": "0x5aAeb6053F3E94C9b9A09f33669435E7Ef1BeAed",
            "value": 1000,
            "gas": 21000,
            "gasPrice": 20000000000
        }
        
        response = await client.post(
            "/transaction/send",
            json={"params": tx_params}
        )
        result = response.json()
        print("\nTransaction sent:")
        print(f"  Hash: {result['result']['transaction']['hash']}")
        print(f"  Request ID: {result['metadata']['request_id']}")
        print(f"  Processing time: {result['metadata']['processing_time']}")
        
        # 3. Validate address
        response = await client.get(
            "/address/0x5aaeb6053f3e94c9b9a09f33669435e7ef1beaed/validate"
        )
        print("\nAddress validation:", response.json())
        
        # 4. Stream blocks
        print("\nStreaming blocks:")
        async with client.stream("GET", "/blocks/stream?from_block=0&to_block=5") as response:
            async for line in response.aiter_lines():
                if line:
                    chunk = json.loads(line)
                    if "data" in chunk:
                        for block in chunk["data"]:
                            print(f"  Block #{block['number']}: {block['hash']}")
                    elif "metadata" in chunk:
                        if chunk["metadata"].get("stream_end"):
                            print(f"  Stream complete: {chunk['metadata']['total_items']} blocks")


def main():
    """Run the example server."""
    import uvicorn
    
    print("Starting Ethereum MCP Server with full middleware stack...")
    print("=" * 60)
    print("Features:")
    print("- Error handling with custom exceptions")
    print("- Request validation with Pydantic models")
    print("- Response formatting with metadata")
    print("- Request ID tracking")
    print("- Response compression")
    print("- Streaming support")
    print("=" * 60)
    
    # Run server
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    # To run the client example:
    # python middleware_example.py client
    
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "client":
        asyncio.run(example_client())
    else:
        main()