"""
Tests for the ResponseFormatterMiddleware
"""

# import pytest  # Optional for running with pytest
import json
import gzip
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from src.middleware import ResponseFormatterMiddleware, StreamingFormatter, format_response_data


def test_response_formatter_success():
    """Test successful response formatting."""
    app = FastAPI()
    app.add_middleware(
        ResponseFormatterMiddleware,
        chain_id=1,
        compress_threshold=1024,
        pretty_print=False
    )
    
    @app.post("/test")
    async def test_endpoint():
        return {"data": "test", "value": 123}
    
    client = TestClient(app)
    response = client.post("/test")
    
    assert response.status_code == 200
    data = response.json()
    
    # Check structure
    assert "result" in data
    assert "metadata" in data
    
    # Check result
    assert data["result"]["data"] == "test"
    assert data["result"]["value"] == 123
    
    # Check metadata
    metadata = data["metadata"]
    assert metadata["chain_id"] == 1
    assert metadata["status"] == "success"
    assert "timestamp" in metadata
    assert "request_id" in metadata
    assert "processing_time" in metadata


def test_response_formatter_error():
    """Test error response formatting."""
    app = FastAPI()
    app.add_middleware(
        ResponseFormatterMiddleware,
        chain_id=1,
        compress_threshold=1024,
        pretty_print=False
    )
    
    @app.post("/test")
    async def test_endpoint():
        raise HTTPException(status_code=400, detail="Test error")
    
    client = TestClient(app)
    response = client.post("/test")
    
    assert response.status_code == 400
    data = response.json()
    
    # Check structure
    assert "error" in data
    assert "metadata" in data
    
    # Check error
    assert data["error"]["code"] == -32000
    assert data["error"]["message"] == "Test error"
    
    # Check metadata
    metadata = data["metadata"]
    assert metadata["chain_id"] == 1
    assert metadata["status"] == "error"


def test_response_compression():
    """Test response compression for large payloads."""
    app = FastAPI()
    app.add_middleware(
        ResponseFormatterMiddleware,
        chain_id=1,
        compress_threshold=100,  # Low threshold for testing
        pretty_print=False
    )
    
    @app.post("/test")
    async def test_endpoint():
        # Create large response
        return {"data": "x" * 1000}
    
    client = TestClient(app)
    response = client.post("/test")
    
    assert response.status_code == 200
    assert response.headers.get("content-encoding") == "gzip"
    
    # Decompress and verify
    decompressed = gzip.decompress(response.content)
    data = json.loads(decompressed.decode())
    assert len(data["result"]["data"]) == 1000


def test_format_response_data():
    """Test the format_response_data utility function."""
    
    # Test success response
    formatted = format_response_data(
        data={"test": "value"},
        request_id="test-123",
        chain_id=1,
        is_error=False,
        processing_time=0.123
    )
    
    assert formatted["result"] == {"test": "value"}
    assert formatted["metadata"]["request_id"] == "test-123"
    assert formatted["metadata"]["chain_id"] == 1
    assert formatted["metadata"]["status"] == "success"
    assert formatted["metadata"]["processing_time"] == "0.123s"
    
    # Test error response
    formatted = format_response_data(
        data={"message": "Error occurred", "details": {"code": "E001"}},
        request_id="test-456",
        chain_id=1,
        is_error=True,
        error_code=-32001
    )
    
    assert formatted["error"]["code"] == -32001
    assert formatted["error"]["message"] == "Error occurred"
    assert formatted["error"]["details"] == {"code": "E001"}
    assert formatted["metadata"]["status"] == "error"


def test_streaming_formatter():
    """Test the StreamingFormatter for large datasets."""
    import asyncio
    
    async def test_generator():
        for i in range(5):
            yield {"id": i, "value": f"item_{i}"}
    
    async def run_test():
        formatter = StreamingFormatter(chain_id=1, chunk_size=2)
        
        # Collect streamed data
        chunks = []
        async def collect_stream():
            gen = test_generator()
            response = formatter.create_streaming_response(
                data_generator=gen,
                request_id="test-stream",
                item_type="items",
                compress=False
            )
            
            # Simulate reading the stream
            async for chunk in response.body_iterator:
                chunks.append(chunk.decode())
        
        await collect_stream()
        
        # Parse chunks
        parsed_chunks = [json.loads(chunk) for chunk in chunks if chunk.strip()]
        
        # First chunk should be metadata
        assert parsed_chunks[0]["metadata"]["stream_start"] == True
        assert parsed_chunks[0]["metadata"]["chain_id"] == 1
        
        # Data chunks
        data_chunks = [c for c in parsed_chunks if "data" in c]
        assert len(data_chunks) == 3  # 5 items with chunk_size=2 = 3 chunks
        
        # Last chunk should be end metadata
        assert parsed_chunks[-1]["metadata"]["stream_end"] == True
        assert parsed_chunks[-1]["metadata"]["total_items"] == 5
    
    # Run async test
    asyncio.run(run_test())


def test_mcp_response_format_preservation():
    """Test that MCP response format is preserved and enhanced."""
    app = FastAPI()
    app.add_middleware(
        ResponseFormatterMiddleware,
        chain_id=1,
        compress_threshold=1024,
        pretty_print=False
    )
    
    @app.post("/mcp")
    async def mcp_endpoint():
        # Simulate MCP response
        return {
            "id": 1,
            "result": {
                "address": "0x742d35Cc6634C0532925a3b844Bc9e7595f6e842",
                "balance": "1000000000000000000",
                "chainId": 1
            }
        }
    
    client = TestClient(app)
    response = client.post("/mcp")
    
    assert response.status_code == 200
    data = response.json()
    
    # Original result should be preserved
    assert data["result"]["address"] == "0x742d35Cc6634C0532925a3b844Bc9e7595f6e842"
    assert data["result"]["balance"] == "1000000000000000000"
    assert data["result"]["chainId"] == 1
    
    # Metadata should be added
    assert "metadata" in data
    assert data["metadata"]["chain_id"] == 1


if __name__ == "__main__":
    test_response_formatter_success()
    test_response_formatter_error()
    test_response_compression()
    test_format_response_data()
    test_streaming_formatter()
    test_mcp_response_format_preservation()
    print("All tests passed!")