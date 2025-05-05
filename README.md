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

### Contract Interaction (Coming Soon)
- Deploy contracts
- Call contract methods
- Execute contract transactions
- Contract event listening
- ABI handling

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

## Security

- Private keys are stored in memory only
- All sensitive operations require proper authentication
- Environment variables for configuration
- Input validation and sanitization
- Rate limiting for API endpoints
- Gas limit validation
- Nonce management
- Transaction signing security

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