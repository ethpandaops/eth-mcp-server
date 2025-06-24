# Response Formatter Middleware

The Response Formatter Middleware ensures consistent response structure across all endpoints in the Ethereum MCP Server.

## Features

1. **Consistent Response Structure**: All responses follow a standard format with `result` and `metadata` fields
2. **Automatic Metadata**: Adds timestamp, request ID, chain ID, and processing time to every response
3. **Error Handling**: Formats errors consistently with error codes and details
4. **Response Compression**: Automatically compresses large responses (>1KB by default)
5. **Streaming Support**: Supports streaming large datasets efficiently
6. **Pretty Printing**: Optional pretty printing for development

## Response Formats

### Success Response
```json
{
  "result": {
    "address": "0x742d35Cc6634C0532925a3b844Bc9e7595f6e842",
    "balance": "1000000000000000000",
    "chainId": 1
  },
  "metadata": {
    "timestamp": "2024-01-20T10:30:00Z",
    "request_id": "550e8400-e29b-41d4-a716-446655440000",
    "chain_id": 1,
    "processing_time": "0.123s",
    "status": "success"
  }
}
```

### Error Response
```json
{
  "error": {
    "code": -32000,
    "message": "Address is required",
    "details": {}
  },
  "metadata": {
    "timestamp": "2024-01-20T10:30:00Z",
    "request_id": "550e8400-e29b-41d4-a716-446655440000",
    "chain_id": 1,
    "processing_time": "0.045s",
    "status": "error"
  }
}
```

## Configuration

The middleware is configured in `server.py`:

```python
app.add_middleware(
    ResponseFormatterMiddleware,
    chain_id=chain_id,
    compress_threshold=1024,  # Compress responses larger than 1KB
    pretty_print=os.getenv("PRETTY_PRINT", "false").lower() == "true",
    compression_level=6
)
```

### Environment Variables

- `PRETTY_PRINT`: Set to "true" for formatted JSON output (development)
- `CHAIN_ID`: Override the detected chain ID

## Streaming Large Datasets

For large datasets like transaction histories, use the `StreamingFormatter`:

```python
# Example endpoint for streaming transaction history
@app.get("/stream/transactions/{address}")
async def stream_transaction_history(request: Request, address: str):
    formatter = StreamingFormatter(chain_id=chain_id, chunk_size=50)
    
    return formatter.create_streaming_response(
        data_generator=transaction_generator(),
        request_id=request_id,
        item_type="transactions",
        compress=True
    )
```

### Streaming Response Format

Streaming responses use newline-delimited JSON (NDJSON):

```json
{"metadata": {"timestamp": "2024-01-20T10:30:00Z", "request_id": "...", "chain_id": 1, "stream_start": true}}
{"data": [{"blockNumber": 1, "from": "0x...", ...}, ...], "chunk_metadata": {"chunk_size": 50, "total_items": 50}}
{"data": [{"blockNumber": 51, "from": "0x...", ...}, ...], "chunk_metadata": {"chunk_size": 50, "total_items": 100}}
{"metadata": {"stream_end": true, "total_items": 150, "timestamp": "2024-01-20T10:30:05Z"}}
```

## Response Headers

The middleware adds custom headers to all responses:

- `X-Request-ID`: Unique request identifier
- `X-Chain-ID`: Ethereum chain ID
- `X-Processing-Time`: Request processing time
- `Content-Encoding`: "gzip" when response is compressed
- `X-Stream-Format`: "jsonlines" for streaming responses

## Usage in Endpoints

### Standard Endpoints

No changes needed! The middleware automatically formats all responses:

```python
@app.post("/mcp")
async def handle_mcp_request(request: MCPRequest) -> MCPResponse:
    # Your existing code remains unchanged
    return MCPResponse(
        id=request.id,
        result={"address": wallet["address"], "chainId": chain_id}
    )
```

### Custom Formatting

For custom formatting needs:

```python
from src.middleware import format_response_data

# Manually format a response
formatted = format_response_data(
    data={"custom": "data"},
    request_id=request_id,
    chain_id=chain_id,
    is_error=False,
    processing_time=0.123
)
```

## Benefits

1. **Consistency**: All API responses follow the same structure
2. **Debugging**: Request IDs help trace issues across logs
3. **Performance**: Automatic compression reduces bandwidth
4. **Monitoring**: Processing time helps identify slow endpoints
5. **Integration**: Works seamlessly with FastMCP/MCP protocol