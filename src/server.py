from fastapi import FastAPI, WebSocket, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Optional, Union, Any
from web3 import Web3
from dotenv import load_dotenv
import os
from src.core.wallet import WalletManager
from src.core.transaction import TransactionManager
from src.core.contract import ContractManager

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

# Initialize FastAPI app
app = FastAPI(title="Ethereum MCP Server")

# Initialize Web3 and get chain ID
w3 = Web3(Web3.HTTPProvider(os.getenv("ETH_RPC_URL", "http://192.168.50.70:8545")))
chain_id = int(os.getenv("CHAIN_ID", w3.eth.chain_id))

# Initialize managers
wallet_manager = WalletManager(w3)
transaction_manager = TransactionManager(w3, wallet_manager)
contract_manager = ContractManager(w3, wallet_manager)

# Store active WebSocket connections
active_monitors: Dict[str, WebSocket] = {}

@app.post("/mcp")
async def handle_mcp_request(request: MCPRequest) -> MCPResponse:
    """Handle MCP requests"""
    try:
        if request.method == "eth_createWallet":
            wallet = wallet_manager.create_wallet()
            return MCPResponse(
                id=request.id,
                result={
                    "address": wallet["address"],
                    "privateKey": wallet["privateKey"],
                    "chainId": chain_id
                }
            )
            
        elif request.method == "eth_importWallet":
            private_key = request.params.get("privateKey")
            if not private_key:
                raise HTTPException(status_code=400, detail="Private key is required")
                
            wallet = wallet_manager.import_wallet(private_key)
            return MCPResponse(
                id=request.id,
                result={
                    "address": wallet["address"],
                    "privateKey": wallet["privateKey"],
                    "chainId": chain_id
                }
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
                raise HTTPException(status_code=400, detail="Address is required")
                
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
                raise HTTPException(status_code=400, detail="Address is required")
                
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
                raise HTTPException(status_code=400, detail="Address is required")
                
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
                raise HTTPException(status_code=400, detail="Missing required parameters")
                
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
                raise HTTPException(status_code=400, detail="Missing required parameters")
                
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
            bytecode = request.params.get("bytecode")
            abi = request.params.get("abi")
            constructor_args = request.params.get("constructor_args", [])
            from_address = request.params.get("from_address")
            gas_limit = request.params.get("gas_limit", 3000000)
            
            if not all([bytecode, abi, from_address]):
                raise HTTPException(status_code=400, detail="Missing required parameters: bytecode, abi, from_address")
                
            result = contract_manager.deploy_contract(
                bytecode=bytecode,
                abi=abi,
                constructor_args=constructor_args,
                from_address=from_address,
                gas_limit=gas_limit
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
                raise HTTPException(status_code=400, detail="Missing required parameters: address, abi")
                
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
            address = request.params.get("address")
            method = request.params.get("method")
            args = request.params.get("args", [])
            from_address = request.params.get("from_address")
            value = request.params.get("value", 0)
            gas_limit = request.params.get("gas_limit", 100000)
            
            if not all([address, method, from_address]):
                raise HTTPException(status_code=400, detail="Missing required parameters: address, method, from_address")
                
            result = contract_manager.call_contract_method(
                address=address,
                method=method,
                args=args,
                from_address=from_address,
                value=value,
                gas_limit=gas_limit
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
                raise HTTPException(status_code=400, detail="Missing required parameters: address, method")
                
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
            address = request.params.get("address")
            event_name = request.params.get("event_name")
            from_block = request.params.get("from_block", "latest")
            to_block = request.params.get("to_block", "latest")
            filters = request.params.get("filters", {})
            
            if not all([address, event_name]):
                raise HTTPException(status_code=400, detail="Missing required parameters: address, event_name")
                
            events = contract_manager.get_contract_events(
                address=address,
                event_name=event_name,
                from_block=from_block,
                to_block=to_block,
                filters=filters
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
            raise HTTPException(status_code=400, detail=f"Unsupported method: {request.method}")
            
    except Exception as e:
        return MCPResponse(
            id=request.id,
            error={
                "code": -32000,
                "message": str(e)
            }
        )

@app.websocket("/ws/transactions/{address}")
async def monitor_transactions(websocket: WebSocket, address: str):
    """WebSocket endpoint for monitoring transactions"""
    await websocket.accept()
    active_monitors[address] = websocket
    
    try:
        # Define callback for transaction monitoring
        async def callback(tx):
            await websocket.send_json(tx)
        
        # Start monitoring
        transaction_manager.start_monitoring(address, callback)
        
        # Keep connection alive
        while True:
            data = await websocket.receive_text()
            if data == "stop":
                break
                
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        # Cleanup
        if address in active_monitors:
            del active_monitors[address]
        transaction_manager.stop_monitoring(address)
        await websocket.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 