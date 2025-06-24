# Ethereum MCP Server Architecture

## Overview

The Ethereum MCP Server is built on a modular architecture that provides a clean separation of concerns and enables easy extension and maintenance. The server implements the Model Context Protocol (MCP) to interact with Ethereum nodes.

## Core Components

### 1. Server Layer (`src/server.py`)
- FastAPI/FastMCP application
- MCP method registration and routing
- WebSocket support for real-time updates
- Middleware integration
- Health and metrics endpoints

### 2. Core Managers (`src/core/`)
Each manager handles a specific domain:

#### WalletManager (`wallet.py`)
- Wallet creation and import
- Private key management (in-memory only)
- Transaction signing
- Balance queries

#### TransactionManager (`transaction.py`)
- Transaction sending and monitoring
- Gas estimation and optimization
- Transaction history
- Receipt retrieval
- WebSocket monitoring

#### ContractManager (`contract.py`)
- Contract deployment with ABI
- Method encoding/decoding
- Event filtering
- Contract state queries

### 3. Data Models (`src/models/`)
Pydantic models for type safety:
- `wallet.py`: Wallet-related models
- `transaction.py`: Transaction models
- `contract.py`: Contract interaction models

### 4. Middleware (`src/middleware/`)

#### Error Handler
- Global exception handling
- Structured error responses
- Web3 error parsing
- Request context tracking

#### Request Validator
- Parameter type validation
- Ethereum-specific format validation
- Input sanitization
- Bounds checking

#### Response Formatter
- Consistent response structure
- Metadata injection
- Response compression
- Streaming support

### 5. Utilities (`src/utils/`)

#### Validation (`validation.py`)
- Address validation with checksum
- Transaction parameter validation
- ABI structure validation
- Input sanitization

#### Logger (`logger.py`)
- Structured logging
- Request tracking
- Performance metrics
- Environment-based formatting

#### Web3 Utilities (`web3.py`)
- Connection management
- Network detection
- Common Web3 operations

## Request Flow

```
Client Request
    ↓
FastMCP Server
    ↓
Request Middleware (ID generation, logging)
    ↓
Request Validator (parameter validation)
    ↓
MCP Method Handler
    ↓
Core Manager (business logic)
    ↓
Web3 Provider (blockchain interaction)
    ↓
Response Formatter (structure, metadata)
    ↓
Error Handler (if exception)
    ↓
Client Response
```

## Key Design Decisions

### 1. Stateless Architecture
- No persistent storage
- Wallets stored in memory only
- Scalable horizontally

### 2. Middleware Pattern
- Cross-cutting concerns handled centrally
- Easy to add new middleware
- Consistent behavior across endpoints

### 3. Type Safety
- Pydantic models throughout
- Type hints for all functions
- Runtime validation

### 4. Error Handling
- Structured error responses
- No stack traces in production
- Clear error codes and messages

### 5. Async First
- Async/await throughout
- Non-blocking I/O
- WebSocket support

## Security Considerations

### 1. Private Key Handling
- Never logged or persisted
- Stored in memory only
- Cleared on server restart

### 2. Input Validation
- All inputs validated
- SQL injection prevention
- XSS protection

### 3. Rate Limiting
- Built-in support
- Configurable limits
- Per-method granularity

## Performance Optimizations

### 1. Connection Pooling
- Reused Web3 connections
- Persistent WebSocket connections
- Efficient resource usage

### 2. Response Compression
- Automatic for large responses
- Configurable threshold
- Gzip compression

### 3. Caching
- Method result caching (planned)
- ABI caching
- Gas price caching

## Extensibility

### Adding New MCP Methods
1. Create method in appropriate manager
2. Add models if needed
3. Register in server.py
4. Add tests
5. Update documentation

### Adding New Middleware
1. Create middleware class
2. Add to server startup
3. Test interaction with existing middleware
4. Document behavior

### Supporting New Networks
1. Update Web3 configuration
2. Add network-specific parameters
3. Test thoroughly
4. Update documentation

## Testing Strategy

### Unit Tests
- Each manager fully tested
- All utilities tested
- Mock Web3 interactions

### Integration Tests
- End-to-end flows
- Middleware interaction
- Error propagation

### Performance Tests
- Load testing
- Concurrent operations
- Memory usage

## Monitoring and Observability

### Logging
- Structured JSON logs
- Request tracking
- Performance metrics

### Metrics
- Request counts
- Error rates
- Response times
- Active connections

### Health Checks
- `/health` endpoint
- Web3 connection status
- Resource usage

## Future Enhancements

### Phase 4: Token Management
- ERC20 operations
- NFT support
- Token approval management

### Phase 5: Advanced Features
- EIP-7702 delegation
- Partial withdrawals
- Batch operations

### Phase 6: Production Hardening
- Rate limiting implementation
- API key authentication
- Persistent storage option
- Multi-node support