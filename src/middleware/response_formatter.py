"""
Response Formatter Middleware for Ethereum MCP Server

This middleware ensures consistent response structure across all endpoints,
adds metadata, handles errors gracefully, and supports response compression.
"""

import gzip
import json
import time
import uuid
from datetime import datetime
from typing import Any, Dict, Optional, Union, AsyncGenerator
from fastapi import Request, Response
from fastapi.responses import StreamingResponse, JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import Message
import logging

logger = logging.getLogger(__name__)


class ResponseFormatterMiddleware(BaseHTTPMiddleware):
    """
    Middleware that formats all responses with consistent structure and metadata.
    
    Features:
    - Consistent response format for success and error cases
    - Automatic metadata addition (timestamp, request_id, chainId)
    - Response compression for large payloads
    - Pretty printing option for development
    - Streaming support for large datasets
    """
    
    def __init__(
        self,
        app,
        chain_id: int,
        compress_threshold: int = 1024,  # Compress responses larger than 1KB
        pretty_print: bool = False,
        compression_level: int = 6
    ):
        super().__init__(app)
        self.chain_id = chain_id
        self.compress_threshold = compress_threshold
        self.pretty_print = pretty_print
        self.compression_level = compression_level
    
    async def dispatch(self, request: Request, call_next):
        # Generate request ID for tracking
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Record start time
        start_time = time.time()
        
        try:
            # Process the request
            response = await call_next(request)
            
            # Skip formatting for WebSocket connections
            if request.url.path.startswith("/ws/"):
                return response
            
            # Process the response
            return await self._format_response(
                response, request, request_id, start_time
            )
            
        except Exception as e:
            # Handle unexpected errors
            logger.error(f"Unexpected error in middleware: {str(e)}", exc_info=True)
            return await self._create_error_response(
                error_code=-32603,
                error_message="Internal server error",
                error_details=str(e),
                request_id=request_id,
                start_time=start_time
            )
    
    async def _format_response(
        self,
        response: Response,
        request: Request,
        request_id: str,
        start_time: float
    ) -> Response:
        """Format the response with consistent structure and metadata."""
        
        # Handle streaming responses
        if isinstance(response, StreamingResponse):
            return await self._format_streaming_response(
                response, request, request_id, start_time
            )
        
        # Read response body
        body = b""
        async for chunk in response.body_iterator:
            body += chunk
        
        # Parse response body
        try:
            data = json.loads(body.decode())
        except json.JSONDecodeError:
            # If not JSON, return as-is
            return Response(
                content=body,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type
            )
        
        # Format based on response type
        if response.status_code >= 400:
            # Error response
            formatted_data = self._format_error_response(
                data, request_id, start_time
            )
        else:
            # Success response
            formatted_data = self._format_success_response(
                data, request_id, start_time
            )
        
        # Convert to JSON
        json_content = self._serialize_json(formatted_data)
        
        # Compress if needed
        headers = dict(response.headers)
        if len(json_content) > self.compress_threshold:
            json_content = gzip.compress(json_content.encode())
            headers["Content-Encoding"] = "gzip"
        else:
            json_content = json_content.encode()
        
        # Add custom headers
        headers.update({
            "X-Request-ID": request_id,
            "X-Chain-ID": str(self.chain_id),
            "X-Processing-Time": f"{time.time() - start_time:.3f}s"
        })
        
        return Response(
            content=json_content,
            status_code=response.status_code,
            headers=headers,
            media_type="application/json"
        )
    
    async def _format_streaming_response(
        self,
        response: StreamingResponse,
        request: Request,
        request_id: str,
        start_time: float
    ) -> StreamingResponse:
        """Format streaming responses with metadata headers."""
        
        async def generate_formatted_stream():
            """Generate formatted streaming content."""
            # Send metadata as first chunk
            metadata = {
                "metadata": {
                    "timestamp": datetime.utcnow().isoformat(),
                    "request_id": request_id,
                    "chain_id": self.chain_id,
                    "stream_start": True
                }
            }
            yield self._serialize_json(metadata) + "\n"
            
            # Stream original content
            async for chunk in response.body_iterator:
                yield chunk
            
            # Send end metadata
            end_metadata = {
                "metadata": {
                    "stream_end": True,
                    "processing_time": f"{time.time() - start_time:.3f}s"
                }
            }
            yield "\n" + self._serialize_json(end_metadata)
        
        headers = dict(response.headers)
        headers.update({
            "X-Request-ID": request_id,
            "X-Chain-ID": str(self.chain_id),
            "X-Stream-Format": "jsonlines"
        })
        
        return StreamingResponse(
            generate_formatted_stream(),
            status_code=response.status_code,
            headers=headers,
            media_type=response.media_type or "application/x-ndjson"
        )
    
    def _format_success_response(
        self,
        data: Dict[str, Any],
        request_id: str,
        start_time: float
    ) -> Dict[str, Any]:
        """Format successful response with metadata."""
        
        # Extract result from MCPResponse format
        if "result" in data:
            result = data["result"]
        else:
            result = data
        
        # Ensure chainId is included in result if not present
        if isinstance(result, dict) and "chainId" not in result:
            result["chainId"] = self.chain_id
        
        return {
            "result": result,
            "metadata": {
                "timestamp": datetime.utcnow().isoformat(),
                "request_id": request_id,
                "chain_id": self.chain_id,
                "processing_time": f"{time.time() - start_time:.3f}s",
                "status": "success"
            }
        }
    
    def _format_error_response(
        self,
        data: Dict[str, Any],
        request_id: str,
        start_time: float
    ) -> Dict[str, Any]:
        """Format error response with metadata."""
        
        # Extract error from MCPResponse format or HTTPException
        if "error" in data:
            error = data["error"]
        elif "detail" in data:
            # HTTPException format
            error = {
                "code": -32000,
                "message": data["detail"],
                "details": data.get("details", {})
            }
        else:
            error = {
                "code": -32000,
                "message": "Unknown error",
                "details": data
            }
        
        return {
            "error": error,
            "metadata": {
                "timestamp": datetime.utcnow().isoformat(),
                "request_id": request_id,
                "chain_id": self.chain_id,
                "processing_time": f"{time.time() - start_time:.3f}s",
                "status": "error"
            }
        }
    
    async def _create_error_response(
        self,
        error_code: int,
        error_message: str,
        error_details: Any,
        request_id: str,
        start_time: float
    ) -> JSONResponse:
        """Create a formatted error response."""
        
        formatted_error = {
            "error": {
                "code": error_code,
                "message": error_message,
                "details": error_details
            },
            "metadata": {
                "timestamp": datetime.utcnow().isoformat(),
                "request_id": request_id,
                "chain_id": self.chain_id,
                "processing_time": f"{time.time() - start_time:.3f}s",
                "status": "error"
            }
        }
        
        return JSONResponse(
            content=formatted_error,
            status_code=500,
            headers={
                "X-Request-ID": request_id,
                "X-Chain-ID": str(self.chain_id)
            }
        )
    
    def _serialize_json(self, data: Any) -> str:
        """Serialize data to JSON with optional pretty printing."""
        if self.pretty_print:
            return json.dumps(data, indent=2, sort_keys=True)
        return json.dumps(data, separators=(',', ':'))


class StreamingFormatter:
    """
    Helper class for formatting large datasets as streaming responses.
    
    Usage:
        formatter = StreamingFormatter(chain_id=1)
        return formatter.create_streaming_response(
            data_generator=my_large_data_generator(),
            request_id=request_id,
            item_type="transactions"
        )
    """
    
    def __init__(self, chain_id: int, chunk_size: int = 100):
        self.chain_id = chain_id
        self.chunk_size = chunk_size
    
    def create_streaming_response(
        self,
        data_generator: AsyncGenerator,
        request_id: str,
        item_type: str = "items",
        compress: bool = True
    ) -> StreamingResponse:
        """Create a streaming response for large datasets."""
        
        async def format_stream():
            # Send opening metadata
            yield json.dumps({
                "metadata": {
                    "timestamp": datetime.utcnow().isoformat(),
                    "request_id": request_id,
                    "chain_id": self.chain_id,
                    "stream_type": item_type,
                    "stream_start": True
                }
            }) + "\n"
            
            # Stream data in chunks
            chunk = []
            item_count = 0
            
            async for item in data_generator:
                chunk.append(item)
                item_count += 1
                
                if len(chunk) >= self.chunk_size:
                    yield json.dumps({
                        "data": chunk,
                        "chunk_metadata": {
                            "chunk_size": len(chunk),
                            "total_items": item_count
                        }
                    }) + "\n"
                    chunk = []
            
            # Send remaining items
            if chunk:
                yield json.dumps({
                    "data": chunk,
                    "chunk_metadata": {
                        "chunk_size": len(chunk),
                        "total_items": item_count
                    }
                }) + "\n"
            
            # Send closing metadata
            yield json.dumps({
                "metadata": {
                    "stream_end": True,
                    "total_items": item_count,
                    "timestamp": datetime.utcnow().isoformat()
                }
            }) + "\n"
        
        headers = {
            "X-Request-ID": request_id,
            "X-Chain-ID": str(self.chain_id),
            "X-Stream-Format": "jsonlines"
        }
        
        if compress:
            headers["Content-Encoding"] = "gzip"
            
            async def compress_stream():
                compressor = gzip.GzipFile(mode='wb')
                async for chunk in format_stream():
                    compressor.write(chunk.encode())
                    yield compressor.flush()
                compressor.close()
            
            return StreamingResponse(
                compress_stream(),
                media_type="application/x-ndjson",
                headers=headers
            )
        
        return StreamingResponse(
            format_stream(),
            media_type="application/x-ndjson",
            headers=headers
        )


def format_response_data(
    data: Any,
    request_id: str,
    chain_id: int,
    is_error: bool = False,
    error_code: Optional[int] = None,
    processing_time: Optional[float] = None
) -> Dict[str, Any]:
    """
    Utility function to manually format response data.
    
    This can be used in endpoints that need custom formatting.
    """
    
    metadata = {
        "timestamp": datetime.utcnow().isoformat(),
        "request_id": request_id,
        "chain_id": chain_id,
        "status": "error" if is_error else "success"
    }
    
    if processing_time is not None:
        metadata["processing_time"] = f"{processing_time:.3f}s"
    
    if is_error:
        return {
            "error": {
                "code": error_code or -32000,
                "message": data.get("message", "Unknown error"),
                "details": data.get("details", {})
            },
            "metadata": metadata
        }
    
    return {
        "result": data,
        "metadata": metadata
    }