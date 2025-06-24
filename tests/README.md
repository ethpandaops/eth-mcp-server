# Ethereum MCP Server Tests

This directory contains comprehensive test suites for the Ethereum MCP Server components.

## Test Files

### test_contract.py
Comprehensive test suite for the ContractManager functionality. Includes tests for:

1. **Contract Deployment**
   - `test_deploy_contract_with_constructor` - Deploy contracts with constructor arguments
   - `test_deploy_contract_no_constructor` - Deploy simple contracts without constructor
   - `test_deployment_failure` - Handle deployment failures gracefully

2. **Contract Loading**
   - `test_load_contract_with_abi` - Load existing contracts with ABI

3. **Contract Interaction**
   - `test_call_state_changing_method` - Test write/state-changing methods
   - `test_read_view_method` - Test view/pure methods (read-only)
   - `test_encode_decode_complex_types` - Test complex parameter encoding/decoding

4. **Event Handling**
   - `test_get_contract_events` - Filter and retrieve contract events

5. **Error Handling**
   - `test_invalid_abi_handling` - Validate ABI format
   - `test_method_not_found` - Handle calls to non-existent methods
   - `test_wallet_not_found_error` - Handle missing wallet errors
   - `test_transaction_failure_handling` - Handle failed transactions
   - `test_contract_not_loaded_error` - Handle calls to unloaded contracts

6. **Utility Functions**
   - `test_list_contracts` - List all loaded contracts
   - `test_gas_estimation` - Estimate gas for transactions
   - `test_verify_contract_placeholder` - Placeholder for contract verification

## Running Tests

### Run all contract tests:
```bash
pytest tests/test_contract.py -v
```

### Run specific test:
```bash
pytest tests/test_contract.py::TestContractManager::test_deploy_contract_with_constructor -v
```

### Run with coverage:
```bash
pytest tests/test_contract.py --cov=src.core.contract --cov-report=html
```

### Using the test runner script:
```bash
python tests/run_contract_tests.py
```

## Test Structure

All tests use pytest fixtures for dependency injection:
- `mock_web3` - Mocked Web3 instance
- `mock_wallet_manager` - Mocked WalletManager instance
- `contract_manager` - ContractManager instance with mocked dependencies
- `sample_*` - Sample test data (addresses, keys, bytecode, ABI)

Tests follow the Arrange-Act-Assert pattern and use mocking to isolate the ContractManager functionality from external dependencies.

## Integration Tests

The integration tests (`test_integration.py`) provide comprehensive end-to-end testing of the MCP server endpoints:

### Test Coverage

1. **test_wallet_creation_and_transaction_flow**
   - Creates wallets
   - Checks balances
   - Gets transaction counts
   - Lists all wallets

2. **test_contract_deployment_flow**
   - Deploys contracts
   - Loads contracts
   - Calls contract methods
   - Reads contract state
   - Lists contracts

3. **test_error_handling_flow**
   - Tests invalid methods
   - Tests missing parameters
   - Tests invalid data formats
   - Verifies error propagation

4. **test_concurrent_operations**
   - Creates multiple wallets in parallel
   - Tests concurrent balance checks
   - Verifies thread safety

5. **test_large_data_handling**
   - Tests with many wallets
   - Tests large transaction history queries
   - Verifies performance with large datasets

6. **test_rate_limiting**
   - Sends rapid requests
   - Measures request times
   - Tests server behavior under load

7. **test_request_validation**
   - Tests parameter validation
   - Tests edge cases
   - Verifies input sanitization

8. **test_response_formatting**
   - Verifies MCP response structure
   - Tests successful responses
   - Tests error responses

9. **test_websocket_connection**
   - Tests WebSocket lifecycle
   - Tests transaction monitoring
   - Verifies real-time updates

10. **test_performance_benchmarks**
    - Benchmarks wallet creation
    - Benchmarks balance checks
    - Benchmarks gas estimates
    - Provides performance metrics

## Running Integration Tests

### Method 1: Using the test runner (recommended)
```bash
cd tests
./run_integration_tests.py
```

This will:
- Check if the MCP server is running
- Start the server if needed
- Run all integration tests
- Stop the server if it was started by the script

### Method 2: Using pytest directly
First, ensure the MCP server is running:
```bash
# In one terminal
python -m uvicorn src.server:app --host 0.0.0.0 --port 8000

# In another terminal
pytest tests/test_integration.py -v
```

### Method 3: Run specific tests
```bash
# Run a specific test class
pytest tests/test_integration.py::TestIntegration -v

# Run a specific test method
pytest tests/test_integration.py::TestIntegration::test_wallet_creation_and_transaction_flow -v
```

### Method 4: Run all tests
```bash
# Run both unit and integration tests
pytest tests/ -v
```

## Test Configuration

The integration tests use:
- FastAPI TestClient for HTTP testing
- Default test server at `http://localhost:8000`
- Sample contract bytecode for deployment tests
- Concurrent operations with ThreadPoolExecutor

## Performance Benchmarks

The performance tests measure:
- Average operation time
- Operations per second
- Response time under load

Expected performance targets:
- Wallet creation: < 1 second
- Balance checks: < 500ms
- Gas estimates: < 500ms

## Troubleshooting

1. **Server not starting**: Check if port 8000 is already in use
2. **Connection errors**: Ensure ETH_RPC_URL is properly configured
3. **Test failures**: Check if the Ethereum node is accessible
4. **WebSocket tests**: Note that TestClient has limitations for WebSocket testing