# Response Formatter Middleware

This middleware provides consistent response formatting for the Ethereum MCP Server.

## Files

- `response_formatter.py`: Main middleware implementation
- `example_usage.py`: Examples of how to use the middleware
- `README.md`: This file

## Key Features

1. **ResponseFormatterMiddleware**: Main middleware class that intercepts all HTTP responses
   - Adds metadata (timestamp, request_id, chainId, processing_time)
   - Ensures consistent response structure
   - Handles automatic compression for large responses
   - Supports pretty printing for development

2. **StreamingFormatter**: Helper class for streaming large datasets
   - Efficient handling of large transaction histories
   - Chunked responses with metadata
   - Automatic compression support

3. **format_response_data**: Utility function for manual response formatting
   - Use when you need custom response formatting
   - Maintains consistency with middleware format

## Integration

The middleware is automatically integrated in `server.py`:

```python
app.add_middleware(
    ResponseFormatterMiddleware,
    chain_id=chain_id,
    compress_threshold=1024,
    pretty_print=os.getenv('ENVIRONMENT', 'development') == 'development'
)
```

## Response Formats

All responses follow one of these formats:

### Success Response
```json
{
  "result": {...},
  "metadata": {
    "timestamp": "ISO 8601 timestamp",
    "request_id": "UUID",
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
    "message": "Error message",
    "details": {...}
  },
  "metadata": {
    "timestamp": "ISO 8601 timestamp",
    "request_id": "UUID",
    "chain_id": 1,
    "processing_time": "0.123s",
    "status": "error"
  }
}
```

## Testing

Run tests with:
```bash
python tests/test_response_formatter.py
```