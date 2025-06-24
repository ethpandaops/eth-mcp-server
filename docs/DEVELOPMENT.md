# Development Guide

## Project Overview

The Ethereum MCP Server is a comprehensive server implementation that provides wallet management, transaction handling, and smart contract interaction capabilities for Ethereum networks. Built with FastAPI and Web3.py, it follows the Model Context Protocol (MCP) for standardized communication.

### Architecture

The project follows a modular architecture with clear separation of concerns:

```
eth-mcp-server/
├── src/
│   ├── server.py           # Main FastAPI server with MCP endpoints
│   ├── core/              # Core business logic
│   │   ├── wallet.py      # Wallet creation, import, and management
│   │   ├── transaction.py # Transaction building and monitoring
│   │   └── contract.py    # Smart contract deployment and interaction
│   ├── models/            # Pydantic data models
│   │   └── contract.py    # Contract-related data models
│   └── utils/             # Utility functions
│       └── validation.py  # Input validation helpers
└── tests/                 # Test suite
    ├── test_contract.py   # Contract manager tests
    └── run_contract_tests.py # Test runner
```

### Key Components

1. **MCP Server** (`src/server.py`): FastAPI application handling MCP requests/responses
2. **Wallet Manager** (`src/core/wallet.py`): Manages Ethereum wallets and private keys
3. **Transaction Manager** (`src/core/transaction.py`): Handles transaction creation, signing, and monitoring
4. **Contract Manager** (`src/core/contract.py`): Manages smart contract deployment and interaction

## Prerequisites

- Python 3.10 or higher
- Git
- Access to an Ethereum RPC endpoint (local or remote)
- Basic understanding of Ethereum and Web3 concepts

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/eth-mcp-server.git
cd eth-mcp-server
```

### 2. Set Up Virtual Environment

Using `uv` (recommended):
```bash
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

Or using standard Python:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 3. Install Dependencies

Using `uv`:
```bash
uv pip install -e .
```

Or using pip:
```bash
pip install -e .
```

## Environment Variables

Create a `.env` file in the project root with the following variables:

```bash
# Ethereum RPC endpoint (required)
ETH_RPC_URL=http://localhost:8545

# Chain ID (optional, auto-detected if not set)
CHAIN_ID=1

# Logging level (optional)
LOG_LEVEL=INFO

# Server configuration (optional)
HOST=0.0.0.0
PORT=8000
```

### Environment Variable Reference

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `ETH_RPC_URL` | Ethereum node RPC endpoint | `http://192.168.50.70:8545` | No |
| `CHAIN_ID` | Ethereum chain ID | Auto-detected | No |
| `LOG_LEVEL` | Logging verbosity (DEBUG, INFO, WARNING, ERROR) | INFO | No |
| `HOST` | Server host binding | 0.0.0.0 | No |
| `PORT` | Server port | 8000 | No |

## Running the Server

### Development Mode

```bash
python src/server.py
```

### Production Mode

Using uvicorn directly:
```bash
uvicorn src.server:app --host 0.0.0.0 --port 8000 --reload
```

### Verifying the Server

Check if the server is running:
```bash
curl http://localhost:8000/health
```

## Project Structure Explained

### `/src/server.py`
Main entry point containing:
- FastAPI application setup
- MCP request/response models
- Request routing and method handlers
- WebSocket endpoints for real-time monitoring

### `/src/core/`
Core business logic modules:

#### `wallet.py`
- Wallet generation using eth-account
- Private key import/export
- Balance checking
- Nonce management

#### `transaction.py`
- Transaction building and gas estimation
- Transaction signing
- Receipt retrieval
- Real-time transaction monitoring

#### `contract.py`
- Contract deployment with constructor arguments
- ABI management
- Method encoding/decoding
- Event log filtering

### `/src/models/`
Pydantic models for:
- Request/response validation
- Type safety
- Automatic documentation

### `/src/utils/`
Helper functions for:
- Address validation
- Hex conversion
- Error handling

## Adding New Features

### 1. Adding a New MCP Method

To add a new method to the server:

```python
# In src/server.py

elif request.method == "eth_newMethod":
    # Extract parameters
    param1 = request.params.get("param1")
    
    # Validate parameters
    if not param1:
        raise HTTPException(status_code=400, detail="param1 is required")
    
    # Call appropriate manager
    result = some_manager.new_method(param1)
    
    # Return response
    return MCPResponse(
        id=request.id,
        result={
            "data": result,
            "chainId": chain_id
        }
    )
```

### 2. Adding a New Manager

Create a new manager in `src/core/`:

```python
# src/core/new_manager.py
from web3 import Web3

class NewManager:
    def __init__(self, w3: Web3):
        self.w3 = w3
    
    def new_method(self, param: str) -> dict:
        # Implementation
        return {"result": "data"}
```

Then integrate it in `server.py`:

```python
from src.core.new_manager import NewManager

# Initialize with other managers
new_manager = NewManager(w3)
```

### 3. Adding WebSocket Support

For real-time features:

```python
@app.websocket("/ws/feature/{param}")
async def monitor_feature(websocket: WebSocket, param: str):
    await websocket.accept()
    
    try:
        # Set up monitoring
        async def callback(data):
            await websocket.send_json(data)
        
        # Start monitoring
        manager.start_monitoring(param, callback)
        
        # Keep connection alive
        while True:
            data = await websocket.receive_text()
            if data == "stop":
                break
    finally:
        manager.stop_monitoring(param)
        await websocket.close()
```

## Debugging Tips

### 1. Enable Debug Logging

Set environment variable:
```bash
export LOG_LEVEL=DEBUG
```

Or add to your code:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### 2. Test Individual Components

Use the Python REPL:
```python
from web3 import Web3
from src.core.wallet import WalletManager

w3 = Web3(Web3.HTTPProvider("http://localhost:8545"))
wallet_mgr = WalletManager(w3)
wallet = wallet_mgr.create_wallet()
print(wallet)
```

### 3. Monitor Network Requests

Use Web3.py middleware:
```python
from web3.middleware import geth_poa_middleware

# For PoA networks
w3.middleware_onion.inject(geth_poa_middleware, layer=0)

# Enable request logging
import logging
logging.getLogger("web3.RequestManager").setLevel(logging.DEBUG)
```

### 4. Common Issues and Solutions

#### Connection Issues
```
Error: Could not connect to RPC endpoint
```
**Solution**: Verify your `ETH_RPC_URL` is correct and the node is running.

#### Gas Estimation Failures
```
Error: Gas estimation failed
```
**Solution**: Ensure the from address has sufficient balance and the transaction is valid.

#### Contract Deployment Failures
```
Error: Contract deployment failed
```
**Solution**: Check that:
- The bytecode is valid
- Constructor arguments match the ABI
- The account has sufficient ETH for gas

#### Invalid ABI Errors
```
Error: Invalid ABI JSON
```
**Solution**: Ensure the ABI is:
- Valid JSON format
- Properly escaped if passed as a string
- Contains the methods you're trying to call

### 5. Using the Test Client

Test your endpoints with the included test client:
```bash
python test_server.py
```

This will run through various operations and help identify issues.

## Development Best Practices

### 1. Code Style

Follow PEP 8 and use the configured linters:
```bash
# Format code
ruff format .

# Check for issues
ruff check .
```

### 2. Type Hints

Always use type hints for better code clarity:
```python
def process_transaction(
    from_address: str,
    to_address: str,
    value: int
) -> Dict[str, Any]:
    # Implementation
```

### 3. Error Handling

Use appropriate exceptions and error messages:
```python
try:
    result = web3_operation()
except Web3Exception as e:
    raise HTTPException(
        status_code=400,
        detail=f"Web3 operation failed: {str(e)}"
    )
```

### 4. Testing

Write tests for new features:
```python
def test_new_feature():
    # Arrange
    manager = NewManager(mock_web3)
    
    # Act
    result = manager.new_method("param")
    
    # Assert
    assert result["status"] == "success"
```

## Contributing

1. Create a feature branch: `git checkout -b feature/your-feature`
2. Make your changes and add tests
3. Run tests: `pytest`
4. Format code: `ruff format .`
5. Create a pull request

## Resources

- [Web3.py Documentation](https://web3py.readthedocs.io/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Ethereum JSON-RPC Specification](https://ethereum.org/en/developers/docs/apis/json-rpc/)
- [MCP Protocol Specification](https://github.com/modelcontextprotocol/specification)