from fastapi import FastAPI, WebSocket, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List, Optional, Union, Any
from web3 import Web3
from dotenv import load_dotenv
import os
import uuid
import time
import logging
from contextlib import asynccontextmanager

# Import core managers
from src.core.wallet import WalletManager
from src.core.transaction import TransactionManager
from src.core.contract import ContractManager

# Import middleware
from src.middleware.error_handler import (
    ErrorHandler, handle_mcp_error, MCPError,
    InvalidAddressError, InvalidPrivateKeyError, 
    InvalidParametersError, InternalError
)
from src.middleware.request_validator import (
    validate_request, validate_address_checksum,
    EthereumAddress, PrivateKey, HexString,
    WalletImportParams, ContractDeployParams,
    ContractCallParams, EventFilterParams
)
from src.middleware.response_formatter import (
    ResponseFormatterMiddleware, format_response_data
)
from src.utils.logger import (
    get_eth_logger, set_request_id, clear_request_id,
    log_timing, setup_logging
)

# MCP Request/Response Models
class MCPRequest(BaseModel):
    id: Optional[int] = None
    method: str
    params: Dict[str, Any] = {}

class MCPResponse(BaseModel):
    id: Optional[int] = None
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None

# Load environment variables
load_dotenv()

# Initialize logger
logger = get_eth_logger(__name__)

# Initialize error handler
error_handler = ErrorHandler(debug=os.getenv('DEBUG', 'false').lower() == 'true')

# Initialize Web3 and get chain ID
w3 = Web3(Web3.HTTPProvider(os.getenv("ETH_RPC_URL", "http://192.168.50.70:8545")))
chain_id = int(os.getenv("CHAIN_ID", w3.eth.chain_id))

# Initialize managers
wallet_manager = WalletManager(w3)
transaction_manager = TransactionManager(w3, wallet_manager)
contract_manager = ContractManager(w3, wallet_manager)

# Store active WebSocket connections
active_monitors: Dict[str, WebSocket] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and shutdown."""
    # Startup
    logger.info("Starting Ethereum MCP Server", 
                version="1.0.0",
                environment=os.getenv('ENVIRONMENT', 'development'))
    
    # Initialize logging
    setup_logging()
    
    # Log configuration
    logger.info("Server configuration",
                rpc_url=os.getenv("ETH_RPC_URL", "http://192.168.50.70:8545"),
                chain_id=chain_id)
    
    yield
    
    # Shutdown
    logger.info("Shutting down Ethereum MCP Server")
    
    # Cleanup resources
    if hasattr(transaction_manager, 'cleanup'):
        transaction_manager.cleanup()


# Initialize FastAPI app with lifespan
app = FastAPI(
    title="Ethereum MCP Server",
    version="1.0.0",
    description="Model Context Protocol server for Ethereum interactions",
    lifespan=lifespan
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure based on your needs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add response formatter middleware
app.add_middleware(
    ResponseFormatterMiddleware,
    chain_id=chain_id,
    compress_threshold=1024,
    pretty_print=os.getenv('ENVIRONMENT', 'development') == 'development'
)


@app.middleware("http")
async def request_middleware(request: Request, call_next):
    """Request logging and ID tracking middleware."""
    # Generate request ID
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    set_request_id(request_id)
    
    # Log request
    start_time = time.time()
    logger.log_request(
        method=request.method,
        params={
            "path": request.url.path,
            "client": request.client.host if request.client else "unknown"
        }
    )
    
    try:
        # Process request
        response = await call_next(request)
        
        # Log response
        duration = time.time() - start_time
        logger.log_response(
            method=request.method,
            result=response.status_code,
            duration=duration
        )
        
        # Add request ID header
        response.headers["X-Request-ID"] = request_id
        
        return response
        
    except Exception as e:
        # Log error
        duration = time.time() - start_time
        logger.log_error(
            method=request.method,
            error=e,
            context={"duration": duration, "path": request.url.path}
        )
        raise
    finally:
        # Clear request ID
        clear_request_id()


@app.post("/mcp")
@log_timing("mcp_request")
async def handle_mcp_request(request: MCPRequest, req: Request) -> MCPResponse:
    """Handle MCP requests"""
    # Get request ID from state
    request_id = getattr(req.state, 'request_id', str(uuid.uuid4()))
    
    # Set error handler context
    error_handler.set_request_context(request_id, {
        "method": request.method,
        "params": request.params
    })
    
    try:
        # Log the incoming request
        logger.log_request(request.method, request.params)
        
        if request.method == "eth_createWallet":
            wallet = wallet_manager.create_wallet()
            result = {
                "address": wallet["address"],
                "privateKey": wallet["privateKey"],
                "chainId": chain_id
            }
            return MCPResponse(
                id=request.id,
                result=result
            )
            
        elif request.method == "eth_importWallet":
            # Validate parameters
            params = WalletImportParams(**request.params)
            
            wallet = wallet_manager.import_wallet(params.privateKey)
            result = {
                "address": wallet["address"],
                "privateKey": wallet["privateKey"],
                "chainId": chain_id
            }
            return MCPResponse(
                id=request.id,
                result=result
            )
            
        elif request.method == "eth_listWallets":
            wallets = wallet_manager.list_wallets()
            return MCPResponse(
                id=request.id,
                result={
                    "addresses": wallets,
                    "chainId": chain_id
                }
            )
            
        elif request.method == "eth_getBalance":
            address = request.params.get("address")
            if not address:
                raise InvalidParametersError("address", "Address is required")
            
            # Validate address
            address = validate_address_checksum(address)
            
            balance = wallet_manager.get_balance(address)
            return MCPResponse(
                id=request.id,
                result={
                    "balance": str(balance),
                    "chainId": chain_id
                }
            )
            
        elif request.method == "eth_getTransactionCount":
            address = request.params.get("address")
            if not address:
                raise InvalidParametersError("address", "Address is required")
            
            # Validate address
            address = validate_address_checksum(address)
            
            nonce = wallet_manager.get_transaction_count(address)
            return MCPResponse(
                id=request.id,
                result={
                    "count": nonce,
                    "chainId": chain_id
                }
            )
            
        elif request.method == "eth_getTransactionHistory":
            address = request.params.get("address")
            if not address:
                raise InvalidParametersError("address", "Address is required")
            
            # Validate address
            address = validate_address_checksum(address)
            
            start_block = request.params.get("startBlock")
            end_block = request.params.get("endBlock")
            
            history = transaction_manager.get_transaction_history(
                address,
                start_block=int(start_block) if start_block else None,
                end_block=int(end_block) if end_block else None
            )
            
            return MCPResponse(
                id=request.id,
                result={
                    "transactions": history,
                    "chainId": chain_id
                }
            )
            
        elif request.method == "eth_getGasPriceEstimate":
            estimate = transaction_manager.get_gas_price_estimate()
            return MCPResponse(
                id=request.id,
                result={
                    **estimate,
                    "chainId": chain_id
                }
            )
            
        elif request.method == "eth_deployContract":
            from_address = request.params.get("from")
            private_key = request.params.get("privateKey")
            bytecode = request.params.get("bytecode")
            gas = request.params.get("gas", 2000000)
            
            if not all([from_address, private_key, bytecode]):
                raise InvalidParametersError("parameters", "Missing required parameters: from, privateKey, bytecode")
            
            # Validate inputs
            from_address = validate_address_checksum(from_address)
            private_key = PrivateKey.validate(private_key)
            bytecode = HexString.validate(bytecode)
            
            result = contract_manager.deploy_contract(from_address, private_key, bytecode, gas)
            return MCPResponse(
                id=request.id,
                result={
                    **result,
                    "chainId": chain_id
                }
            )
            
        elif request.method == "eth_callContractMethod":
            contract_address = request.params.get("contractAddress")
            from_address = request.params.get("from")
            private_key = request.params.get("privateKey")
            method_name = request.params.get("methodName")
            params = request.params.get("params", [])
            gas = request.params.get("gas", 2000000)
            
            if not all([contract_address, from_address, private_key, method_name]):
                raise InvalidParametersError("parameters", "Missing required parameters")
            
            # Validate inputs
            contract_address = validate_address_checksum(contract_address)
            from_address = validate_address_checksum(from_address)
            private_key = PrivateKey.validate(private_key)
            
            result = contract_manager.call_contract_method(
                contract_address, from_address, private_key, method_name, params, gas
            )
            return MCPResponse(
                id=request.id,
                result={
                    **result,
                    "chainId": chain_id
                }
            )
            
        elif request.method == "contract_deploy":
            # Validate with schema
            params = ContractDeployParams(
                bytecode=request.params.get("bytecode"),
                abi=request.params.get("abi", []),
                args=request.params.get("constructor_args", []),
                from_address=request.params.get("from_address"),
                gas=request.params.get("gas_limit", 3000000)
            )
            
            result = contract_manager.deploy_contract(
                bytecode=params.bytecode,
                abi=params.abi,
                constructor_args=params.args,
                from_address=params.from_address,
                gas_limit=params.gas
            )
            return MCPResponse(
                id=request.id,
                result={
                    **result,
                    "chainId": chain_id
                }
            )
            
        elif request.method == "contract_load":
            address = request.params.get("address")
            abi = request.params.get("abi")
            name = request.params.get("name")
            
            if not all([address, abi]):
                raise InvalidParametersError("parameters", "Missing required parameters: address, abi")
            
            # Validate address
            address = validate_address_checksum(address)
            
            result = contract_manager.load_contract(
                address=address,
                abi=abi,
                name=name
            )
            return MCPResponse(
                id=request.id,
                result={
                    **result,
                    "chainId": chain_id
                }
            )
            
        elif request.method == "contract_call":
            # Validate with schema
            params = ContractCallParams(
                contractAddress=request.params.get("address"),
                method=request.params.get("method"),
                args=request.params.get("args", []),
                from_address=request.params.get("from_address"),
                value=request.params.get("value", 0),
                gas=request.params.get("gas_limit", 100000)
            )
            
            result = contract_manager.call_contract_method(
                address=params.contractAddress,
                method=params.method,
                args=params.args,
                from_address=params.from_address,
                value=params.value,
                gas_limit=params.gas
            )
            return MCPResponse(
                id=request.id,
                result={
                    **result,
                    "chainId": chain_id
                }
            )
            
        elif request.method == "contract_read":
            address = request.params.get("address")
            method = request.params.get("method")
            args = request.params.get("args", [])
            
            if not all([address, method]):
                raise InvalidParametersError("parameters", "Missing required parameters: address, method")
            
            # Validate address
            address = validate_address_checksum(address)
            
            result = contract_manager.read_contract(
                address=address,
                method=method,
                args=args
            )
            return MCPResponse(
                id=request.id,
                result={
                    "result": result,
                    "chainId": chain_id
                }
            )
            
        elif request.method == "contract_events":
            # Validate with schema
            params = EventFilterParams(
                contractAddress=request.params.get("address"),
                eventName=request.params.get("event_name"),
                fromBlock=request.params.get("from_block", "latest"),
                toBlock=request.params.get("to_block", "latest"),
                filters=request.params.get("filters", {})
            )
            
            events = contract_manager.get_contract_events(
                address=params.contractAddress,
                event_name=params.eventName,
                from_block=params.fromBlock,
                to_block=params.toBlock,
                filters=params.filters
            )
            return MCPResponse(
                id=request.id,
                result={
                    "events": events,
                    "chainId": chain_id
                }
            )
            
        elif request.method == "contract_list":
            contracts = contract_manager.list_contracts()
            return MCPResponse(
                id=request.id,
                result={
                    "contracts": contracts,
                    "chainId": chain_id
                }
            )
            
        else:
            raise InvalidParametersError("method", f"Unsupported method: {request.method}")
            
    except MCPError as e:
        # Handle MCP-specific errors
        error_dict = e.to_dict()
        return MCPResponse(
            id=request.id,
            error=error_dict["error"]
        )
    except Exception as e:
        # Handle unexpected errors
        logger.error(f"Unexpected error in {request.method}", exc_info=True)
        error_response = error_handler.handle_error(e, request_id)
        return MCPResponse(
            id=request.id,
            error=error_response["error"]
        )
    finally:
        # Clear error handler context
        error_handler.clear_request_context(request_id)


@app.websocket("/ws/transactions/{address}")
async def monitor_transactions(websocket: WebSocket, address: str):
    """WebSocket endpoint for monitoring transactions"""
    # Generate request ID for WebSocket connection
    request_id = str(uuid.uuid4())
    set_request_id(request_id)
    
    try:
        # Validate address
        address = validate_address_checksum(address)
        
        await websocket.accept()
        active_monitors[address] = websocket
        
        logger.info(f"WebSocket connection established for address monitoring",
                   address=address,
                   request_id=request_id)
        
        # Define callback for transaction monitoring
        async def callback(tx):
            # Format transaction data
            formatted_tx = format_response_data(
                data=tx,
                request_id=request_id,
                chain_id=chain_id,
                is_error=False
            )
            await websocket.send_json(formatted_tx)
        
        # Start monitoring
        transaction_manager.start_monitoring(address, callback)
        
        # Keep connection alive
        while True:
            data = await websocket.receive_text()
            if data == "stop":
                logger.info(f"WebSocket monitoring stopped by client",
                           address=address,
                           request_id=request_id)
                break
                
    except Exception as e:
        logger.error(f"WebSocket error for address {address}",
                    error=str(e),
                    request_id=request_id,
                    exc_info=True)
        # Try to send error to client if connection is still open
        if websocket.client_state.value == 1:  # CONNECTED
            error_data = format_response_data(
                data={"message": str(e)},
                request_id=request_id,
                chain_id=chain_id,
                is_error=True,
                error_code=-32000
            )
            await websocket.send_json(error_data)
    finally:
        # Cleanup
        if address in active_monitors:
            del active_monitors[address]
        transaction_manager.stop_monitoring(address)
        await websocket.close()
        clear_request_id()
        logger.info(f"WebSocket connection closed",
                   address=address,
                   request_id=request_id)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        # Check Web3 connection
        block_number = w3.eth.block_number
        return {
            "status": "healthy",
            "chain_id": chain_id,
            "block_number": block_number,
            "version": "1.0.0"
        }
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        raise HTTPException(status_code=503, detail="Service unavailable")


@app.get("/metrics")
async def get_metrics():
    """Get server metrics."""
    return {
        "active_websockets": len(active_monitors),
        "chain_id": chain_id,
        "loaded_contracts": len(contract_manager.list_contracts()),
        "managed_wallets": len(wallet_manager.list_wallets())
    }


if __name__ == "__main__":
    import uvicorn
    
    # Configure uvicorn logging
    log_config = uvicorn.config.LOGGING_CONFIG
    log_config["formatters"]["access"]["fmt"] = "%(asctime)s - %(levelname)s - %(message)s"
    log_config["formatters"]["default"]["fmt"] = "%(asctime)s - %(levelname)s - %(message)s"
    
    uvicorn.run(
        app,
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", 8000)),
        log_config=log_config,
        access_log=True
    )