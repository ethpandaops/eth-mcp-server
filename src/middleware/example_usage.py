"""
Example usage of the ResponseFormatterMiddleware and StreamingFormatter

This file demonstrates how to use the response formatting features
in your FastAPI endpoints.
"""

from fastapi import FastAPI, Request
from typing import AsyncGenerator
from src.middleware import StreamingFormatter, format_response_data
import asyncio


# Example 1: Using StreamingFormatter for large transaction history
async def get_large_transaction_history(
    address: str,
    start_block: int,
    end_block: int
) -> AsyncGenerator:
    """
    Example generator that yields transaction data.
    In a real implementation, this would fetch from blockchain.
    """
    for block_num in range(start_block, end_block + 1):
        # Simulate fetching transactions from a block
        yield {
            "blockNumber": block_num,
            "from": address,
            "to": "0x742d35Cc6634C0532925a3b844Bc9e7595f6e842",
            "value": "1000000000000000000",
            "gas": 21000,
            "gasPrice": "20000000000",
            "hash": f"0x{'0' * 40}{block_num:024x}",
            "timestamp": 1234567890 + block_num
        }
        
        # Simulate some processing time
        await asyncio.sleep(0.01)


# Example endpoint using streaming
async def stream_transaction_history(request: Request):
    """
    Example endpoint that streams large transaction history.
    """
    # Get request ID from middleware
    request_id = getattr(request.state, "request_id", "unknown")
    
    # Initialize streaming formatter
    formatter = StreamingFormatter(chain_id=1, chunk_size=50)
    
    # Create data generator
    data_gen = get_large_transaction_history(
        address="0x742d35Cc6634C0532925a3b844Bc9e7595f6e842",
        start_block=1,
        end_block=1000
    )
    
    # Return streaming response
    return formatter.create_streaming_response(
        data_generator=data_gen,
        request_id=request_id,
        item_type="transactions",
        compress=True
    )


# Example 2: Manually formatting responses
async def custom_formatted_endpoint(request: Request):
    """
    Example endpoint with custom response formatting.
    """
    request_id = getattr(request.state, "request_id", "unknown")
    start_time = time.time()
    
    try:
        # Perform some operation
        result = {
            "data": "Custom response data",
            "customField": "value"
        }
        
        # Format response manually
        return format_response_data(
            data=result,
            request_id=request_id,
            chain_id=1,
            is_error=False,
            processing_time=time.time() - start_time
        )
        
    except Exception as e:
        # Format error response manually
        return format_response_data(
            data={
                "message": str(e),
                "details": {"error_type": type(e).__name__}
            },
            request_id=request_id,
            chain_id=1,
            is_error=True,
            error_code=-32603,
            processing_time=time.time() - start_time
        )


# Example 3: Integration with existing endpoints
"""
The ResponseFormatterMiddleware automatically formats all responses,
so your existing endpoints don't need to change. The middleware will:

1. Add metadata to all responses
2. Ensure consistent structure
3. Handle compression automatically
4. Add request tracking

Your existing code like:

    return MCPResponse(
        id=request.id,
        result={
            "address": wallet["address"],
            "privateKey": wallet["privateKey"],
            "chainId": chain_id
        }
    )

Will be automatically formatted to:

    {
        "result": {
            "address": "0x...",
            "privateKey": "0x...",
            "chainId": 1
        },
        "metadata": {
            "timestamp": "2024-01-20T10:30:00Z",
            "request_id": "uuid-here",
            "chain_id": 1,
            "processing_time": "0.123s",
            "status": "success"
        }
    }

Error responses are also automatically formatted:

    {
        "error": {
            "code": -32000,
            "message": "Error message",
            "details": {...}
        },
        "metadata": {
            "timestamp": "2024-01-20T10:30:00Z",
            "request_id": "uuid-here",
            "chain_id": 1,
            "processing_time": "0.123s",
            "status": "error"
        }
    }
"""