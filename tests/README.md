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