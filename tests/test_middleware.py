"""
Comprehensive test suite for all middleware functionality.

Tests cover:
1. Error handler middleware - exception handling, error formatting
2. Request validator middleware - decorator usage, validation failures
3. Response formatter middleware - success formatting, error formatting
4. Request ID tracking - generation, propagation
5. Metadata addition - timestamp, chain ID, processing time
6. Response compression - large responses, threshold
7. Streaming responses - chunked data, metadata
8. Concurrent requests - thread safety, context isolation
9. Async compatibility - async functions, await handling
10. Performance impact - minimal overhead verification
"""

import asyncio
import gzip
import json
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, Mock, patch
import pytest
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import ValidationError

# Import middleware components
from src.middleware.error_handler import (
    ErrorHandler, MCPError, WalletNotFoundError, InvalidAddressError,
    TransactionFailedError, ErrorCode, handle_mcp_error, parse_web3_error
)
from src.middleware.request_validator import (
    validate_request, EthereumAddress, PrivateKey, HexString,
    TransactionParams, ContractDeployParams, sanitize_hex_input,
    validate_address_checksum, validate_transaction_params,
    validate_value_bounds
)
from src.middleware.response_formatter import (
    ResponseFormatterMiddleware, StreamingFormatter, format_response_data
)


class TestErrorHandler:
    """Test suite for error handler middleware."""
    
    @pytest.fixture
    def error_handler(self):
        """Create error handler instance."""
        return ErrorHandler(debug=True)
    
    def test_mcp_error_creation(self):
        """Test MCPError creation and formatting."""
        error = WalletNotFoundError("test_wallet")
        
        assert error.code == ErrorCode.WALLET_NOT_FOUND
        assert "test_wallet" in error.message
        assert error.status_code == 404
        assert error.details["wallet_name"] == "test_wallet"
        
        # Test to_dict formatting
        error_dict = error.to_dict()
        assert "error" in error_dict
        assert error_dict["error"]["code"] == "WALLET_NOT_FOUND"
        assert "request_id" in error_dict["error"]
        assert "timestamp" in error_dict["error"]
    
    def test_error_handler_mcp_errors(self, error_handler):
        """Test handling of MCPError exceptions."""
        error = InvalidAddressError("0xinvalid", "Invalid checksum")
        result = error_handler.handle_error(error)
        
        assert result["error"]["code"] == "INVALID_ADDRESS"
        assert "0xinvalid" in result["error"]["message"]
        assert result["error"]["details"]["reason"] == "Invalid checksum"
    
    def test_error_handler_web3_exceptions(self, error_handler):
        """Test handling of Web3 exceptions."""
        from web3.exceptions import InvalidAddress, TransactionNotFound
        
        # Test InvalidAddress
        error = InvalidAddress("0xinvalid")
        result = error_handler.handle_error(error)
        assert result["error"]["code"] == "INVALID_ADDRESS"
        
        # Test TransactionNotFound
        error = TransactionNotFound("Transaction '0xabc123' not found")
        result = error_handler.handle_error(error)
        assert result["error"]["code"] == "TRANSACTION_NOT_FOUND"
        assert "0xabc123" in result["error"]["details"]["transaction_hash"]
    
    def test_error_handler_context(self, error_handler):
        """Test request context handling."""
        request_id = "test-request-123"
        context = {
            "method": "test_method",
            "params": {"param1": "value1"},
            "address": "0x123"
        }
        
        error_handler.set_request_context(request_id, context)
        
        # Create error that uses context
        error = Exception("Test error")
        result = error_handler.handle_error(error, request_id)
        
        # Verify context was used (in debug mode)
        assert result["error"]["code"] == "INTERNAL_ERROR"
        assert "Test error" in str(result["error"]["details"])
        
        # Clear context
        error_handler.clear_request_context(request_id)
        assert request_id not in error_handler._request_context
    
    @pytest.mark.asyncio
    async def test_handle_mcp_error_decorator(self):
        """Test handle_mcp_error decorator."""
        call_count = 0
        
        @handle_mcp_error
        async def test_function(params: Dict[str, Any]):
            nonlocal call_count
            call_count += 1
            if params.get("should_fail"):
                raise WalletNotFoundError("missing_wallet")
            return {"result": "success"}
        
        # Test successful execution
        result = await test_function({"should_fail": False})
        assert result["result"] == "success"
        assert call_count == 1
        
        # Test error handling
        with pytest.raises(Exception) as exc_info:
            await test_function({"should_fail": True})
        
        assert "missing_wallet" in str(exc_info.value)
        assert call_count == 2
    
    def test_parse_web3_error(self):
        """Test Web3 error parsing."""
        from web3.exceptions import ContractLogicError
        
        # Test insufficient funds
        error = ContractLogicError("execution reverted: insufficient funds for transfer")
        parsed = parse_web3_error(error)
        assert parsed.code == ErrorCode.INSUFFICIENT_FUNDS
        
        # Test nonce too low
        error = ContractLogicError("nonce too low")
        parsed = parse_web3_error(error)
        assert parsed.code == ErrorCode.NONCE_TOO_LOW
        
        # Test gas too low
        error = ContractLogicError("out of gas")
        parsed = parse_web3_error(error)
        assert parsed.code == ErrorCode.GAS_TOO_LOW


class TestRequestValidator:
    """Test suite for request validator middleware."""
    
    def test_ethereum_address_validation(self):
        """Test Ethereum address validation."""
        # Valid addresses
        valid_checksum = "0x5aAeb6053F3E94C9b9A09f33669435E7Ef1BeAed"
        assert EthereumAddress.validate(valid_checksum) == valid_checksum
        
        # Convert to checksum
        lowercase = "0x5aaeb6053f3e94c9b9a09f33669435e7ef1beaed"
        result = EthereumAddress.validate(lowercase)
        assert result == valid_checksum
        
        # Invalid addresses
        with pytest.raises(ValueError, match="42 characters"):
            EthereumAddress.validate("0x123")
        
        with pytest.raises(ValueError, match="start with 0x"):
            EthereumAddress.validate("5aAeb6053F3E94C9b9A09f33669435E7Ef1BeAed")
        
        with pytest.raises(TypeError):
            EthereumAddress.validate(12345)
    
    def test_private_key_validation(self):
        """Test private key validation."""
        # Valid private key
        valid_key = "0x" + "a" * 64
        assert PrivateKey.validate(valid_key) == valid_key
        
        # Invalid private keys
        with pytest.raises(ValueError, match="66 characters"):
            PrivateKey.validate("0x123")
        
        with pytest.raises(ValueError):
            PrivateKey.validate("not_a_hex_key")
    
    def test_hex_string_validation(self):
        """Test hex string validation."""
        # Valid hex strings
        assert HexString.validate("0x") == "0x"
        assert HexString.validate("0x123abc") == "0x123abc"
        
        # Invalid hex strings
        with pytest.raises(ValueError):
            HexString.validate("0xGHI")
        
        with pytest.raises(ValueError):
            HexString.validate("123abc")  # Missing 0x prefix
    
    def test_transaction_params_validation(self):
        """Test transaction parameters validation."""
        # Valid transaction
        params = {
            "from": "0x5aAeb6053F3E94C9b9A09f33669435E7Ef1BeAed",
            "to": "0x5aAeb6053F3E94C9b9A09f33669435E7Ef1BeAed",
            "value": 1000000,
            "gas": 21000,
            "gasPrice": 20000000000
        }
        
        tx = TransactionParams(**params)
        assert tx.from_address == params["from"]
        assert tx.value == params["value"]
        
        # Test EIP-1559 validation
        with pytest.raises(ValidationError):
            TransactionParams(
                gasPrice=1000,
                maxFeePerGas=2000  # Can't specify both
            )
    
    def test_contract_deploy_params_validation(self):
        """Test contract deployment parameters validation."""
        # Valid deployment
        params = {
            "bytecode": "0x608060405234801561001057600080fd5b50",
            "abi": [{"type": "constructor"}],
            "from": "0x5aAeb6053F3E94C9b9A09f33669435E7Ef1BeAed"
        }
        
        deploy = ContractDeployParams(**params)
        assert deploy.bytecode == params["bytecode"]
        
        # Empty bytecode
        with pytest.raises(ValidationError, match="empty"):
            ContractDeployParams(
                bytecode="0x",
                abi=[{"type": "constructor"}],
                from_address="0x5aAeb6053F3E94C9b9A09f33669435E7Ef1BeAed"
            )
        
        # Empty ABI
        with pytest.raises(ValidationError, match="empty"):
            ContractDeployParams(
                bytecode="0x123",
                abi=[],
                from_address="0x5aAeb6053F3E94C9b9A09f33669435E7Ef1BeAed"
            )
    
    @pytest.mark.asyncio
    async def test_validate_request_decorator_async(self):
        """Test validate_request decorator with async functions."""
        @validate_request(TransactionParams)
        async def send_transaction(params: Dict[str, Any]):
            return {"success": True, "params": params}
        
        # Valid params
        valid_params = {
            "from": "0x5aAeb6053F3E94C9b9A09f33669435E7Ef1BeAed",
            "to": "0x5aAeb6053F3E94C9b9A09f33669435E7Ef1BeAed",
            "value": 1000
        }
        
        result = await send_transaction(params=valid_params)
        assert result["success"] is True
        assert result["params"]["value"] == 1000
        
        # Invalid params
        invalid_params = {"from": "invalid_address"}
        with pytest.raises(ValueError, match="Validation failed"):
            await send_transaction(params=invalid_params)
    
    def test_validate_request_decorator_sync(self):
        """Test validate_request decorator with sync functions."""
        @validate_request(TransactionParams)
        def send_transaction_sync(params: Dict[str, Any]):
            return {"success": True, "params": params}
        
        # Valid params
        valid_params = {
            "from": "0x5aAeb6053F3E94C9b9A09f33669435E7Ef1BeAed",
            "value": "0x3e8"  # Hex value
        }
        
        result = send_transaction_sync(params=valid_params)
        assert result["success"] is True
        assert result["params"]["value"] == 1000  # Converted from hex
    
    def test_sanitize_hex_input(self):
        """Test hex input sanitization."""
        # Valid hex
        assert sanitize_hex_input("0x123abc") == "0x123abc"
        assert sanitize_hex_input("0X123ABC") == "0x123abc"  # Lowercase
        
        # Odd length padding
        assert sanitize_hex_input("0x123") == "0x0123"
        
        # Invalid hex
        with pytest.raises(ValueError):
            sanitize_hex_input("not_hex")
        
        with pytest.raises(ValueError):
            sanitize_hex_input("0xGHI")
    
    def test_validate_value_bounds(self):
        """Test value bounds validation."""
        # Valid values
        assert validate_value_bounds(1000, min_val=0, max_val=10000) == 1000
        assert validate_value_bounds("0x3e8") == 1000  # Hex string
        assert validate_value_bounds("1000") == 1000  # String
        
        # Out of bounds
        with pytest.raises(ValueError, match="less than"):
            validate_value_bounds(-1, min_val=0)
        
        with pytest.raises(ValueError, match="exceed"):
            validate_value_bounds(1000, max_val=500)


class TestResponseFormatter:
    """Test suite for response formatter middleware."""
    
    @pytest.fixture
    def app(self):
        """Create test FastAPI app."""
        app = FastAPI()
        
        @app.get("/test")
        async def test_endpoint():
            return {"data": "test"}
        
        @app.get("/error")
        async def error_endpoint():
            raise HTTPException(status_code=400, detail="Test error")
        
        @app.get("/stream")
        async def stream_endpoint():
            async def generate():
                for i in range(5):
                    yield f"chunk{i}\n"
            
            return StreamingResponse(generate())
        
        return app
    
    @pytest.fixture
    def middleware(self, app):
        """Create response formatter middleware."""
        return ResponseFormatterMiddleware(
            app,
            chain_id=1,
            compress_threshold=100,
            pretty_print=True
        )
    
    @pytest.mark.asyncio
    async def test_success_response_formatting(self, app):
        """Test successful response formatting."""
        middleware = ResponseFormatterMiddleware(app, chain_id=1)
        
        # Mock request and response
        request = MagicMock(spec=Request)
        request.url.path = "/test"
        request.state = MagicMock()
        
        # Create mock response
        response = MagicMock(spec=Response)
        response.status_code = 200
        response.headers = {}
        response.media_type = "application/json"
        
        # Mock body iterator
        body_data = json.dumps({"data": "test"}).encode()
        
        async def body_iterator():
            yield body_data
        
        response.body_iterator = body_iterator()
        
        # Mock call_next
        async def call_next(req):
            return response
        
        # Process response
        formatted = await middleware.dispatch(request, call_next)
        
        # Verify headers
        assert "X-Request-ID" in formatted.headers
        assert formatted.headers["X-Chain-ID"] == "1"
        assert "X-Processing-Time" in formatted.headers
    
    @pytest.mark.asyncio
    async def test_error_response_formatting(self, app):
        """Test error response formatting."""
        middleware = ResponseFormatterMiddleware(app, chain_id=1)
        
        request = MagicMock(spec=Request)
        request.url.path = "/error"
        request.state = MagicMock()
        
        # Create error response
        error_body = json.dumps({"detail": "Test error"}).encode()
        response = MagicMock(spec=Response)
        response.status_code = 400
        response.headers = {}
        response.media_type = "application/json"
        
        async def body_iterator():
            yield error_body
        
        response.body_iterator = body_iterator()
        
        async def call_next(req):
            return response
        
        formatted = await middleware.dispatch(request, call_next)
        
        # Parse response body
        body = formatted.body
        if isinstance(body, bytes):
            data = json.loads(body.decode())
        else:
            data = json.loads(body)
        
        assert "error" in data
        assert data["metadata"]["status"] == "error"
    
    @pytest.mark.asyncio
    async def test_response_compression(self, app):
        """Test response compression for large payloads."""
        middleware = ResponseFormatterMiddleware(
            app,
            chain_id=1,
            compress_threshold=50  # Low threshold for testing
        )
        
        request = MagicMock(spec=Request)
        request.url.path = "/test"
        request.state = MagicMock()
        
        # Create large response
        large_data = {"data": "x" * 100}  # Large enough to trigger compression
        response = MagicMock(spec=Response)
        response.status_code = 200
        response.headers = {}
        response.media_type = "application/json"
        
        async def body_iterator():
            yield json.dumps(large_data).encode()
        
        response.body_iterator = body_iterator()
        
        async def call_next(req):
            return response
        
        formatted = await middleware.dispatch(request, call_next)
        
        # Check compression
        assert formatted.headers.get("Content-Encoding") == "gzip"
        
        # Verify compressed content
        if isinstance(formatted.body, bytes):
            decompressed = gzip.decompress(formatted.body)
            data = json.loads(decompressed.decode())
            assert "result" in data
    
    @pytest.mark.asyncio
    async def test_streaming_response_formatting(self, app):
        """Test streaming response formatting."""
        middleware = ResponseFormatterMiddleware(app, chain_id=1)
        
        request = MagicMock(spec=Request)
        request.url.path = "/stream"
        request.state = MagicMock()
        
        # Create streaming response
        async def generate():
            yield b"chunk1\n"
            yield b"chunk2\n"
        
        response = StreamingResponse(generate())
        response.headers = {}
        
        async def call_next(req):
            return response
        
        formatted = await middleware.dispatch(request, call_next)
        
        # Verify it's still a streaming response
        assert isinstance(formatted, StreamingResponse)
        assert "X-Stream-Format" in formatted.headers
        assert formatted.headers["X-Stream-Format"] == "jsonlines"
    
    def test_format_response_data_utility(self):
        """Test format_response_data utility function."""
        # Success formatting
        result = format_response_data(
            {"value": 123},
            request_id="test-123",
            chain_id=1,
            processing_time=0.123
        )
        
        assert result["result"]["value"] == 123
        assert result["metadata"]["request_id"] == "test-123"
        assert result["metadata"]["chain_id"] == 1
        assert result["metadata"]["processing_time"] == "0.123s"
        assert result["metadata"]["status"] == "success"
        
        # Error formatting
        error_result = format_response_data(
            {"message": "Error occurred", "details": {"code": 500}},
            request_id="test-456",
            chain_id=1,
            is_error=True,
            error_code=-32000
        )
        
        assert error_result["error"]["code"] == -32000
        assert error_result["error"]["message"] == "Error occurred"
        assert error_result["metadata"]["status"] == "error"
    
    @pytest.mark.asyncio
    async def test_streaming_formatter(self):
        """Test StreamingFormatter for large datasets."""
        formatter = StreamingFormatter(chain_id=1, chunk_size=2)
        
        async def data_generator():
            for i in range(5):
                yield {"id": i, "value": f"item{i}"}
        
        response = formatter.create_streaming_response(
            data_generator(),
            request_id="test-stream",
            item_type="test_items",
            compress=False
        )
        
        # Collect all chunks
        chunks = []
        async for chunk in response.body_iterator:
            chunks.append(json.loads(chunk.decode().strip()))
        
        # Verify metadata chunks
        assert chunks[0]["metadata"]["stream_start"] is True
        assert chunks[-1]["metadata"]["stream_end"] is True
        assert chunks[-1]["metadata"]["total_items"] == 5
        
        # Verify data chunks
        data_chunks = [c for c in chunks if "data" in c]
        assert len(data_chunks) == 3  # 5 items with chunk_size=2
        assert len(data_chunks[0]["data"]) == 2
        assert len(data_chunks[2]["data"]) == 1  # Last chunk


class TestMiddlewareIntegration:
    """Test middleware integration and interaction."""
    
    @pytest.mark.asyncio
    async def test_request_id_propagation(self):
        """Test request ID propagation through middleware stack."""
        app = FastAPI()
        
        captured_request_id = None
        
        @app.get("/test")
        async def test_endpoint(request: Request):
            nonlocal captured_request_id
            captured_request_id = getattr(request.state, "request_id", None)
            return {"status": "ok"}
        
        # Add middleware
        middleware = ResponseFormatterMiddleware(app, chain_id=1)
        
        # Mock request
        request = MagicMock(spec=Request)
        request.url.path = "/test"
        request.state = MagicMock()
        
        # Create response
        async def call_next(req):
            # Simulate endpoint execution
            req.state.request_id = getattr(req.state, "request_id", "default")
            response = Response(
                content=json.dumps({"status": "ok"}),
                media_type="application/json"
            )
            response.headers = {}
            
            async def body_iterator():
                yield response.body
            
            response.body_iterator = body_iterator()
            return response
        
        result = await middleware.dispatch(request, call_next)
        
        # Verify request ID was set
        assert hasattr(request.state, "request_id")
        assert result.headers["X-Request-ID"] == request.state.request_id
    
    @pytest.mark.asyncio
    async def test_error_handler_with_formatter(self):
        """Test error handler integration with response formatter."""
        app = FastAPI()
        error_handler = ErrorHandler(debug=True)
        
        @app.get("/test")
        @handle_mcp_error
        async def test_endpoint():
            raise WalletNotFoundError("test_wallet")
        
        # Add response formatter
        middleware = ResponseFormatterMiddleware(app, chain_id=1)
        
        request = MagicMock(spec=Request)
        request.url.path = "/test"
        request.state = MagicMock()
        
        # Mock the error response
        async def call_next(req):
            try:
                await test_endpoint()
            except Exception as e:
                error_dict = error_handler.handle_error(e)
                response = Response(
                    content=json.dumps(error_dict),
                    status_code=404,
                    media_type="application/json"
                )
                response.headers = {}
                
                async def body_iterator():
                    yield response.body
                
                response.body_iterator = body_iterator()
                return response
        
        result = await middleware.dispatch(request, call_next)
        
        # Parse response
        body = result.body
        if isinstance(body, bytes):
            data = json.loads(body.decode())
        else:
            data = json.loads(body)
        
        assert data["error"]["code"] == "WALLET_NOT_FOUND"
        assert data["metadata"]["status"] == "error"
    
    @pytest.mark.asyncio
    async def test_concurrent_request_isolation(self):
        """Test that concurrent requests maintain isolated contexts."""
        error_handler = ErrorHandler()
        
        async def process_request(request_id: str, should_fail: bool):
            # Set context
            error_handler.set_request_context(request_id, {
                "request_id": request_id,
                "should_fail": should_fail
            })
            
            # Simulate processing delay
            await asyncio.sleep(0.01)
            
            if should_fail:
                error = Exception(f"Error for {request_id}")
                result = error_handler.handle_error(error, request_id)
                assert request_id in str(result)
            
            # Clear context
            error_handler.clear_request_context(request_id)
        
        # Run concurrent requests
        tasks = []
        for i in range(10):
            request_id = f"req-{i}"
            should_fail = i % 2 == 0
            tasks.append(process_request(request_id, should_fail))
        
        await asyncio.gather(*tasks)
        
        # Verify all contexts are cleared
        assert len(error_handler._request_context) == 0
    
    def test_performance_overhead(self):
        """Test middleware performance overhead."""
        import timeit
        
        # Test validation overhead
        @validate_request(TransactionParams)
        def validated_function(params):
            return params
        
        def unvalidated_function(params):
            return params
        
        valid_params = {
            "from": "0x5aAeb6053F3E94C9b9A09f33669435E7Ef1BeAed",
            "value": 1000
        }
        
        # Measure overhead
        validated_time = timeit.timeit(
            lambda: validated_function(params=valid_params),
            number=1000
        )
        
        unvalidated_time = timeit.timeit(
            lambda: unvalidated_function(valid_params),
            number=1000
        )
        
        overhead_ratio = validated_time / unvalidated_time
        
        # Validation should add less than 5x overhead for simple cases
        assert overhead_ratio < 5.0
        
        print(f"Validation overhead: {overhead_ratio:.2f}x")


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_malformed_addresses(self):
        """Test handling of various malformed addresses."""
        malformed = [
            "",  # Empty
            "0x",  # Just prefix
            "0x00",  # Too short
            "0x" + "g" * 40,  # Invalid hex chars
            "0x" + "0" * 41,  # Too long (41 chars)
            "0x" + "0" * 39,  # Too short (39 chars)
            " 0x" + "0" * 40,  # Leading space
            "0x" + "0" * 40 + " ",  # Trailing space
        ]
        
        for addr in malformed:
            with pytest.raises((ValueError, TypeError)):
                EthereumAddress.validate(addr)
    
    def test_extreme_values(self):
        """Test handling of extreme numeric values."""
        # Max uint256
        max_uint256 = 2**256 - 1
        assert validate_value_bounds(max_uint256) == max_uint256
        
        # Over max uint256
        with pytest.raises(ValueError):
            validate_value_bounds(2**256)
        
        # Negative values
        with pytest.raises(ValueError):
            validate_value_bounds(-1)
        
        # Very large gas values
        with pytest.raises(ValueError):
            from src.middleware.request_validator import GasLimit
            GasLimit.validate(10**9)  # 1 billion gas
    
    @pytest.mark.asyncio
    async def test_empty_response_handling(self):
        """Test handling of empty responses."""
        app = FastAPI()
        
        @app.get("/empty")
        async def empty_endpoint():
            return Response(content=b"", status_code=204)
        
        middleware = ResponseFormatterMiddleware(app, chain_id=1)
        
        request = MagicMock(spec=Request)
        request.url.path = "/empty"
        request.state = MagicMock()
        
        async def call_next(req):
            response = Response(content=b"", status_code=204)
            response.headers = {}
            
            async def body_iterator():
                yield b""
            
            response.body_iterator = body_iterator()
            return response
        
        result = await middleware.dispatch(request, call_next)
        
        # Should handle empty response gracefully
        assert result.status_code == 204
    
    def test_unicode_handling(self):
        """Test handling of unicode in error messages."""
        error = MCPError(
            code=ErrorCode.INTERNAL_ERROR,
            message="Error with unicode: café ☕ 中文",
            details={"unicode_data": "测试 🚀"}
        )
        
        error_dict = error.to_dict()
        assert "café" in error_dict["error"]["message"]
        assert "测试" in error_dict["error"]["details"]["unicode_data"]
        
        # Ensure JSON serialization works
        json_str = json.dumps(error_dict)
        parsed = json.loads(json_str)
        assert parsed["error"]["message"] == error_dict["error"]["message"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])