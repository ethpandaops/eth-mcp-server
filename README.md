# Ethereum MCP Server

WARNING: THIS REPO IS HIGHLY EXPERIMENTAL AND LIKELY TO NOT WORK AT THIS MOMENT. IT'S UNDER ACTIVE DEVELOPMENT AND WE WILL UPDATE THIS WARNING ONCE IT'S CONSIDERED SAFE TO RUN.

A comprehensive Ethereum MCP server implementation with wallet management, transaction handling, and contract interaction capabilities. Built with FastAPI and Web3.py.

## Features

### Wallet Management
- Create new wallets
- Import existing wallets
- List managed wallets
- Check ETH balances
- Secure private key handling

### Transaction Management
- Send ETH transactions
- Get transaction details
- Get transaction receipts
- Gas estimation
- Nonce management
- Transaction monitoring

### Contract Interaction
- Deploy contracts with ABI
- Load existing contracts
- Call state-changing methods
- Read contract state
- Query contract events
- ABI management

#### Deploy Contract
Deploy a new contract with its bytecode and ABI:
```json
{
  "method": "eth_deployContract",
  "params": {
    "from": "0x742d35Cc6634C0532925a3b844Bc9e7595f62b8e",
    "abi": [...],  // Contract ABI array
    "bytecode": "0x608060...",  // Contract bytecode
    "constructorArgs": ["arg1", 123]  // Optional constructor arguments
  }
}
```

#### Load Contract
Load an existing deployed contract:
```json
{
  "method": "eth_loadContract",
  "params": {
    "address": "0x1234567890123456789012345678901234567890",
    "abi": [...]  // Contract ABI array
  }
}
```

#### Call Contract Method (State-Changing)
Execute a transaction that changes contract state:
```json
{
  "method": "eth_callContractMethod",
  "params": {
    "contractAddress": "0x1234567890123456789012345678901234567890",
    "methodName": "transfer",
    "args": ["0x742d35Cc6634C0532925a3b844Bc9e7595f62b8e", 1000],
    "from": "0x742d35Cc6634C0532925a3b844Bc9e7595f62b8e"
  }
}
```

#### Read Contract State
Call a view/pure function without sending a transaction:
```json
{
  "method": "eth_readContract",
  "params": {
    "contractAddress": "0x1234567890123456789012345678901234567890",
    "methodName": "balanceOf",
    "args": ["0x742d35Cc6634C0532925a3b844Bc9e7595f62b8e"]
  }
}
```

#### Query Contract Events
Retrieve past events from a contract:
```json
{
  "method": "eth_getContractEvents",
  "params": {
    "contractAddress": "0x1234567890123456789012345678901234567890",
    "eventName": "Transfer",
    "fromBlock": 0,
    "toBlock": "latest",
    "filters": {  // Optional event filters
      "from": "0x742d35Cc6634C0532925a3b844Bc9e7595f62b8e"
    }
  }
}
```

**Note:** All contract interaction methods require the contract ABI (Application Binary Interface) to properly encode/decode function calls and events. The ABI must be provided as a JSON array following the standard Ethereum ABI format.

### Token Management (Coming Soon)
- ERC20 balance checking
- ERC20 transfers
- NFT metadata retrieval
- NFT transfers
- Token approval management

### Advanced Features (Coming Soon)
- EIP-7702 delegation
- Event log retrieval
- Partial withdrawals
- Full withdrawals
- Batch operations

## Quick Start

1. Install dependencies:
```bash
uv venv
source .venv/bin/activate
uv pip install -e .
```

2. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. Run the server:
```bash
python src/server.py
```

## API Methods

### Wallet Methods
```json
{
  "method": "eth_createWallet",
  "params": {}
}

{
  "method": "eth_importWallet",
  "params": {
    "privateKey": "0x..."
  }
}

{
  "method": "eth_listWallets",
  "params": {}
}

{
  "method": "eth_getBalance",
  "params": {
    "address": "0x..."
  }
}
```

### Transaction Methods
```json
{
  "method": "eth_sendTransaction",
  "params": {
    "from": "0x...",
    "to": "0x...",
    "value": "0x...",
    "gas": "0x...",
    "gasPrice": "0x..."
  }
}

{
  "method": "eth_getTransaction",
  "params": {
    "hash": "0x..."
  }
}

{
  "method": "eth_getTransactionReceipt",
  "params": {
    "hash": "0x..."
  }
}

{
  "method": "eth_estimateGas",
  "params": {
    "from": "0x...",
    "to": "0x...",
    "value": "0x..."
  }
}
```

## Development

### Project Structure
```
src/
├── server.py           # Main FastAPI server
├── core/              # Core functionality
│   ├── wallet.py      # Wallet management
│   ├── transaction.py # Transaction handling
│   ├── contract.py    # Contract interaction
│   └── token.py       # Token/NFT handling
├── models/            # Data models
└── utils/             # Utilities
```

### Running Tests
```bash
pytest
```

### Code Style
```bash
ruff check .
ruff format .
```

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

MIT 