# Testing Guide

## Testing Philosophy

The eth-mcp-server project follows a comprehensive testing strategy that emphasizes:

- **Unit Testing**: Testing individual components in isolation
- **Integration Testing**: Testing component interactions
- **End-to-End Testing**: Testing complete workflows
- **Mock-First Approach**: Using mocks to isolate components and avoid network dependencies
- **Behavior-Driven Testing**: Tests describe expected behavior, not implementation details

## Testing Stack

- **pytest**: Primary testing framework
- **pytest-asyncio**: Async test support
- **unittest.mock**: Mocking framework
- **coverage.py**: Code coverage analysis

## Running Tests

### Quick Start

Run all tests:
```bash
pytest
```

Run with verbose output:
```bash
pytest -v
```

Run specific test file:
```bash
pytest tests/test_contract.py
```

Run specific test:
```bash
pytest tests/test_contract.py::TestContractManager::test_deploy_contract_with_constructor
```

### Test Coverage

Run tests with coverage:
```bash
pytest --cov=src --cov-report=html --cov-report=term
```

View HTML coverage report:
```bash
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows
```

### Continuous Testing

Watch for changes and re-run tests:
```bash
pytest-watch
```

Or using pytest directly:
```bash
pytest --looponfail
```

## Writing Tests

### Test Structure

Tests follow a consistent structure:

```python
class TestComponentName:
    """Test suite for ComponentName functionality."""
    
    @pytest.fixture
    def setup_data(self):
        """Provide test data."""
        return {"key": "value"}
    
    def test_specific_behavior(self, setup_data):
        """Test that component exhibits specific behavior."""
        # Arrange
        component = Component()
        
        # Act
        result = component.method(setup_data)
        
        # Assert
        assert result["status"] == "success"
```

### Mocking Guidelines

#### 1. Mock External Dependencies

Always mock Web3 and network calls:

```python
@pytest.fixture
def mock_web3():
    """Create a mock Web3 instance."""
    mock = Mock(spec=Web3)
    mock.eth = Mock()
    mock.eth.chain_id = 1
    mock.eth.gas_price = 20000000000
    return mock
```

#### 2. Mock Manager Dependencies

When testing managers, mock their dependencies:

```python
@pytest.fixture
def mock_wallet_manager():
    """Create a mock WalletManager."""
    mock = Mock(spec=WalletManager)
    mock.verify_wallet = Mock(return_value=True)
    mock.get_transaction_count = Mock(return_value=0)
    return mock
```

#### 3. Use Realistic Mock Data

Mock data should resemble real Ethereum data:

```python
@pytest.fixture
def sample_transaction_receipt():
    """Provide a realistic transaction receipt."""
    return {
        'transactionHash': HexBytes('0x123...'),
        'blockNumber': 12345,
        'gasUsed': 21000,
        'status': 1,
        'logs': []
    }
```

### Testing Async Code

Use pytest-asyncio for async tests:

```python
import pytest

@pytest.mark.asyncio
async def test_async_method():
    """Test asynchronous functionality."""
    manager = AsyncManager()
    result = await manager.async_method()
    assert result is not None
```

### Testing Error Cases

Always test error conditions:

```python
def test_invalid_address_error(self, manager):
    """Test that invalid addresses raise appropriate errors."""
    with pytest.raises(ValueError, match="Invalid Ethereum address"):
        manager.process_address("invalid_address")

def test_insufficient_balance_error(self, manager, mock_web3):
    """Test handling of insufficient balance."""
    mock_web3.eth.get_balance.return_value = 0
    
    with pytest.raises(InsufficientBalanceError):
        manager.send_transaction(value=1000000)
```

## Test Categories

### 1. Unit Tests

Test individual functions and methods:

```python
def test_wallet_creation(self, wallet_manager):
    """Test wallet creation generates valid address and key."""
    wallet = wallet_manager.create_wallet()
    
    assert Web3.is_address(wallet['address'])
    assert wallet['privateKey'].startswith('0x')
    assert len(wallet['privateKey']) == 66
```

### 2. Integration Tests

Test component interactions:

```python
def test_contract_deployment_flow(self, contract_manager, wallet_manager):
    """Test complete contract deployment flow."""
    # Create wallet
    wallet = wallet_manager.create_wallet()
    
    # Deploy contract
    result = contract_manager.deploy_contract(
        from_address=wallet['address'],
        bytecode=SAMPLE_BYTECODE,
        abi=SAMPLE_ABI
    )
    
    assert result['contractAddress'] is not None
    assert result['status'] == 1
```

### 3. End-to-End Tests

Test complete user workflows:

```python
def test_token_transfer_workflow(self, test_client):
    """Test complete token transfer workflow."""
    # Create wallets
    sender = create_test_wallet(test_client)
    receiver = create_test_wallet(test_client)
    
    # Deploy token contract
    token = deploy_test_token(test_client, sender)
    
    # Transfer tokens
    result = transfer_tokens(
        test_client,
        token['address'],
        sender,
        receiver,
        amount=100
    )
    
    assert result['status'] == 'success'
```

## Performance Testing

### Load Testing

Test server performance under load:

```python
import asyncio
import aiohttp

async def load_test_endpoint(url: str, num_requests: int):
    """Test endpoint with concurrent requests."""
    async with aiohttp.ClientSession() as session:
        tasks = []
        for _ in range(num_requests):
            task = session.post(url, json={"method": "eth_listWallets"})
            tasks.append(task)
        
        responses = await asyncio.gather(*tasks)
        success_count = sum(1 for r in responses if r.status == 200)
        
        print(f"Success rate: {success_count}/{num_requests}")
```

### Benchmark Tests

Measure operation performance:

```python
import pytest
import time

@pytest.mark.benchmark
def test_wallet_creation_performance(benchmark, wallet_manager):
    """Benchmark wallet creation performance."""
    result = benchmark(wallet_manager.create_wallet)
    assert result['address'] is not None
```

## Test Data Management

### Fixtures

Common test fixtures in `conftest.py`:

```python
# tests/conftest.py
import pytest
from web3 import Web3

@pytest.fixture(scope="session")
def test_addresses():
    """Provide test Ethereum addresses."""
    return {
        "alice": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
        "bob": "0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC",
        "contract": "0x5FbDB2315678afecb367f032d93F642f64180aa3"
    }

@pytest.fixture
def test_private_keys():
    """Provide test private keys (DO NOT USE IN PRODUCTION)."""
    return {
        "alice": "0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d",
        "bob": "0x5de4111afa1a4b94908f83103eb1f1706367c2e68ca870fc3fb9a804cdab365a"
    }
```

### Test Data Files

Store complex test data in separate files:

```json
// tests/data/sample_abi.json
[
  {
    "inputs": [],
    "name": "getValue",
    "outputs": [{"type": "uint256"}],
    "type": "function"
  }
]
```

Load in tests:
```python
import json

@pytest.fixture
def sample_abi():
    """Load sample ABI from file."""
    with open("tests/data/sample_abi.json") as f:
        return json.load(f)
```

## CI/CD Integration

### GitHub Actions

Tests run automatically on:
- Push to main branch
- Pull requests
- Scheduled runs (daily)

See `.github/workflows/test.yml` for configuration.

### Pre-commit Hooks

Install pre-commit hooks:
```bash
pre-commit install
```

Configure in `.pre-commit-config.yaml`:
```yaml
repos:
  - repo: local
    hooks:
      - id: tests
        name: Run tests
        entry: pytest
        language: system
        pass_filenames: false
        always_run: true
```

## Testing Best Practices

### 1. Test Naming

Use descriptive test names:
```python
# Good
def test_deploy_contract_with_constructor_args_succeeds():
    pass

# Bad
def test_deploy():
    pass
```

### 2. Test Independence

Tests should not depend on each other:
```python
# Good - Each test sets up its own state
def test_transfer_tokens(self):
    wallet = create_wallet()
    tokens = mint_tokens(wallet)
    transfer_tokens(wallet, recipient, tokens)

# Bad - Depends on previous test state
def test_transfer_tokens(self, shared_wallet):
    # Assumes wallet has tokens from previous test
    transfer_tokens(shared_wallet, recipient, 100)
```

### 3. Assertion Messages

Provide clear assertion messages:
```python
assert result['status'] == 1, f"Transaction failed with status {result['status']}"
```

### 4. Test Coverage Requirements

Maintain minimum coverage levels:
- Overall: 80%
- Core modules: 90%
- New features: 95%

### 5. Mock vs Real Testing

Balance mocking with integration tests:
- Unit tests: Heavy mocking
- Integration tests: Mock external services only
- E2E tests: Use test networks when possible

## Debugging Failed Tests

### 1. Verbose Output

```bash
pytest -vv --tb=short
```

### 2. Print Debugging

```python
def test_complex_operation(self, capfd):
    """Test with captured output."""
    result = complex_operation()
    
    # Capture print statements
    out, err = capfd.readouterr()
    print(f"Operation output: {out}")
    
    assert result['status'] == 'success'
```

### 3. Interactive Debugging

```python
def test_failing_operation(self):
    """Test with debugger."""
    import pdb; pdb.set_trace()
    result = failing_operation()
    assert result is not None
```

Or use pytest's built-in debugger:
```bash
pytest --pdb
```

### 4. Test Isolation

Run single test in isolation:
```bash
pytest -k "test_specific_function" -s
```

## Common Testing Patterns

### 1. Parameterized Tests

Test multiple inputs:
```python
@pytest.mark.parametrize("address,expected", [
    ("0x742d35Cc6634C0532925a3b844Bc9e7595f8e5e5", True),
    ("invalid_address", False),
    ("", False),
    (None, False),
])
def test_address_validation(self, address, expected):
    """Test address validation with various inputs."""
    assert is_valid_address(address) == expected
```

### 2. Testing Exceptions

```python
def test_contract_not_found_error(self, manager):
    """Test appropriate error for missing contract."""
    with pytest.raises(ContractNotFoundError) as exc_info:
        manager.call_contract_method("0xinvalid", "method")
    
    assert "Contract not found" in str(exc_info.value)
    assert exc_info.value.address == "0xinvalid"
```

### 3. Testing Events

```python
def test_event_emission(self, contract, mock_web3):
    """Test that contract emits expected events."""
    # Setup mock event
    mock_event = Mock()
    mock_event.processReceipt.return_value = [
        {"args": {"user": "0x123", "value": 100}}
    ]
    
    # Execute transaction
    tx_receipt = contract.set_value(100)
    
    # Verify event
    events = mock_event.processReceipt(tx_receipt)
    assert len(events) == 1
    assert events[0]["args"]["value"] == 100
```

## Test Maintenance

### Regular Tasks

1. **Update test dependencies**: Monthly
2. **Review test coverage**: Weekly
3. **Refactor slow tests**: Quarterly
4. **Update mock data**: When Ethereum specs change

### Test Documentation

Document complex test scenarios:
```python
def test_complex_defi_interaction(self):
    """
    Test DeFi protocol interaction.
    
    Scenario:
    1. User deposits ETH into lending protocol
    2. User borrows stablecoin against collateral
    3. User swaps stablecoin for another token
    4. User repays loan with interest
    
    This tests the complete flow including:
    - Approval management
    - Multi-step transactions
    - Event monitoring
    - Balance verification
    """
    # Test implementation
```

## Resources

- [pytest Documentation](https://docs.pytest.org/)
- [pytest-asyncio Documentation](https://pytest-asyncio.readthedocs.io/)
- [unittest.mock Documentation](https://docs.python.org/3/library/unittest.mock.html)
- [Coverage.py Documentation](https://coverage.readthedocs.io/)
- [Web3.py Testing Guide](https://web3py.readthedocs.io/en/stable/testing.html)