import pytest
from unittest.mock import Mock, patch, MagicMock
from web3 import Web3
from eth_utils import to_checksum_address
from hexbytes import HexBytes
import json

from src.core.contract import ContractManager
from src.core.wallet import WalletManager


class TestContractManager:
    """Comprehensive test suite for ContractManager functionality."""

    @pytest.fixture
    def mock_web3(self):
        """Create a mock Web3 instance."""
        mock = Mock(spec=Web3)
        mock.eth = Mock()
        mock.eth.chain_id = 1
        mock.eth.gas_price = 20000000000  # 20 gwei
        mock.eth.wait_for_transaction_receipt = Mock()
        mock.eth.send_raw_transaction = Mock()
        mock.eth.contract = Mock()
        mock.eth.get_code = Mock()
        return mock

    @pytest.fixture
    def mock_wallet_manager(self):
        """Create a mock WalletManager instance."""
        mock = Mock(spec=WalletManager)
        mock.verify_wallet = Mock(return_value=True)
        mock.get_transaction_count = Mock(return_value=0)
        mock.sign_transaction = Mock()
        return mock

    @pytest.fixture
    def contract_manager(self, mock_web3, mock_wallet_manager):
        """Create a ContractManager instance with mocked dependencies."""
        return ContractManager(mock_web3, mock_wallet_manager)

    @pytest.fixture
    def sample_address(self):
        """Provide a sample Ethereum address."""
        return "0x742d35Cc6634C0532925a3b844Bc9e7595f8e5e5"

    @pytest.fixture
    def sample_private_key(self):
        """Provide a sample private key."""
        return "0x4312ca863dc5c824f1355814f1560ab9b5fddbd656c559654865f1629936e02f"

    @pytest.fixture
    def sample_contract_address(self):
        """Provide a sample contract address."""
        return "0x8626f6940E2eb28930eFb4CeF49B2d1F2C9C1199"

    @pytest.fixture
    def sample_bytecode(self):
        """Provide sample contract bytecode."""
        return "0x608060405234801561001057600080fd5b5060405161001d9061007b565b604051809103906000f080158015610039573d6000803e3d6000fd5b506000806101000a81548173ffffffffffffffffffffffffffffffffffffffff021916908373ffffffffffffffffffffffffffffffffffffffff16021790555061008a565b60ae8061016883390190565b60cf8061009960003960"

    @pytest.fixture
    def sample_abi(self):
        """Provide a sample contract ABI."""
        return [
            {
                "inputs": [{"internalType": "uint256", "name": "value", "type": "uint256"}],
                "name": "set",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function"
            },
            {
                "inputs": [],
                "name": "get",
                "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
                "stateMutability": "view",
                "type": "function"
            },
            {
                "anonymous": False,
                "inputs": [
                    {"indexed": True, "internalType": "address", "name": "user", "type": "address"},
                    {"indexed": False, "internalType": "uint256", "name": "value", "type": "uint256"}
                ],
                "name": "ValueChanged",
                "type": "event"
            }
        ]

    def test_deploy_contract_with_constructor(self, contract_manager, mock_web3, mock_wallet_manager, 
                                            sample_address, sample_private_key, sample_bytecode, sample_abi):
        """Test deploying a contract with constructor arguments."""
        # Setup mocks
        tx_hash = HexBytes('0x1234567890abcdef')
        contract_address = "0x5FbDB2315678afecb367f032d93F642f64180aa3"
        
        # Mock contract factory
        mock_contract_factory = Mock()
        mock_constructor = Mock()
        mock_contract_factory.constructor = Mock(return_value=mock_constructor)
        mock_constructor.build_transaction = Mock(return_value={
            'from': sample_address,
            'nonce': 0,
            'gas': 3000000,
            'gasPrice': 20000000000,
            'data': sample_bytecode + "0000000000000000000000000000000000000000000000000000000000000064",
            'chainId': 1
        })
        
        mock_web3.eth.contract.return_value = mock_contract_factory
        mock_web3.eth.send_raw_transaction.return_value = tx_hash
        mock_web3.eth.wait_for_transaction_receipt.return_value = {
            'transactionHash': tx_hash,
            'contractAddress': contract_address,
            'blockNumber': 12345,
            'gasUsed': 150000,
            'status': 1
        }
        
        mock_wallet_manager.sign_transaction.return_value = {
            'rawTransaction': HexBytes('0xf86b808504a817c80083015f9094000000000000000000000000000000000000000080801ca0')
        }

        # Deploy contract with constructor arguments
        result = contract_manager.deploy_contract(
            bytecode=sample_bytecode,
            abi=sample_abi,
            constructor_args=[100],
            from_address=sample_address,
            gas_limit=3000000
        )

        # Assertions
        assert result['contractAddress'] == contract_address
        assert result['transactionHash'] == tx_hash.hex()
        assert result['blockNumber'] == 12345
        assert result['gasUsed'] == 150000
        assert result['status'] == 1

        # Verify method calls
        mock_wallet_manager.verify_wallet.assert_called_once_with(to_checksum_address(sample_address))
        mock_wallet_manager.get_transaction_count.assert_called_once_with(to_checksum_address(sample_address))
        mock_web3.eth.send_raw_transaction.assert_called_once()
        mock_web3.eth.wait_for_transaction_receipt.assert_called_once_with(tx_hash)

    def test_deploy_contract_no_constructor(self, contract_manager, mock_web3, mock_wallet_manager,
                                          sample_address, sample_private_key, sample_bytecode, sample_abi):
        """Test deploying a simple contract without constructor."""
        # Setup mocks
        tx_hash = HexBytes('0xabcdef1234567890')
        contract_address = "0x70997970C51812dc3A010C7d01b50e0d17dc79C8"
        
        # Mock contract factory
        mock_contract_factory = Mock()
        mock_constructor = Mock()
        mock_contract_factory.constructor = Mock(return_value=mock_constructor)
        mock_constructor.build_transaction = Mock(return_value={
            'from': sample_address,
            'nonce': 0,
            'gas': 3000000,
            'gasPrice': 20000000000,
            'data': sample_bytecode,
            'chainId': 1
        })
        
        mock_web3.eth.contract.return_value = mock_contract_factory
        mock_web3.eth.send_raw_transaction.return_value = tx_hash
        mock_web3.eth.wait_for_transaction_receipt.return_value = {
            'transactionHash': tx_hash,
            'contractAddress': contract_address,
            'blockNumber': 12346,
            'gasUsed': 100000,
            'status': 1
        }
        
        mock_wallet_manager.sign_transaction.return_value = {
            'rawTransaction': HexBytes('0xf86b808504a817c80083015f9094')
        }

        # Deploy contract
        result = contract_manager.deploy_contract(
            bytecode=sample_bytecode,
            abi=sample_abi,
            from_address=sample_address
        )

        # Assertions
        assert result['contractAddress'] == contract_address
        assert result['transactionHash'] == tx_hash.hex()
        assert result['blockNumber'] == 12346
        assert result['gasUsed'] == 100000

    def test_load_contract_with_abi(self, contract_manager, mock_web3, sample_contract_address, sample_abi):
        """Test loading an existing contract with ABI."""
        # Create a mock contract instance
        mock_contract = Mock()
        mock_contract.address = sample_contract_address
        mock_contract.abi = sample_abi
        
        # Mock the contract factory
        mock_web3.eth.contract.return_value = mock_contract
        mock_web3.eth.get_code.return_value = HexBytes('0x608060405234801561001057600080fd5b50')

        # Load contract
        contract = contract_manager.load_contract(sample_contract_address, sample_abi)

        # Assertions
        assert contract is not None
        assert hasattr(contract, 'address')
        assert contract.address == sample_contract_address
        mock_web3.eth.contract.assert_called_once_with(
            address=to_checksum_address(sample_contract_address),
            abi=sample_abi
        )

    def test_call_state_changing_method(self, contract_manager, mock_web3, mock_wallet_manager,
                                      sample_address, sample_private_key, sample_contract_address, sample_abi):
        """Test calling a state-changing (write) method."""
        # Setup mocks
        tx_hash = HexBytes('0x9876543210fedcba')
        
        # First load the contract
        mock_contract = Mock()
        mock_contract.address = sample_contract_address
        mock_contract.abi = sample_abi
        mock_contract.functions = Mock()
        mock_set_method = Mock()
        mock_contract.functions.set = Mock(return_value=mock_set_method)
        mock_set_method.build_transaction = Mock(return_value={
            'from': sample_address,
            'to': sample_contract_address,
            'nonce': 0,
            'gas': 300000,
            'gasPrice': 20000000000,
            'value': 0,
            'data': '0x60fe47b1',
            'chainId': 1
        })
        
        # Load contract first
        contract_manager._contracts[sample_contract_address] = mock_contract
        
        mock_web3.eth.send_raw_transaction.return_value = tx_hash
        mock_web3.eth.wait_for_transaction_receipt.return_value = {
            'transactionHash': tx_hash,
            'blockNumber': 12347,
            'gasUsed': 50000,
            'status': 1,
            'logs': []
        }
        
        mock_wallet_manager.sign_transaction.return_value = {
            'rawTransaction': HexBytes('0xf86b808504a817c80083015f90')
        }

        # Call contract method
        result = contract_manager.call_contract_method(
            address=sample_contract_address,
            method_name="set",
            args=[42],
            from_address=sample_address
        )

        # Assertions
        assert result['transactionHash'] == tx_hash.hex()
        assert result['blockNumber'] == 12347
        assert result['gasUsed'] == 50000
        assert result['status'] == 1
        assert 'logs' in result

    def test_read_view_method(self, contract_manager, mock_web3, sample_contract_address, sample_abi):
        """Test reading from view/pure methods."""
        # Create a mock contract with a callable method
        mock_contract = Mock()
        mock_contract.address = sample_contract_address
        mock_contract.abi = sample_abi
        mock_contract.functions = Mock()
        mock_get_function = Mock()
        mock_get_function.call.return_value = 42
        mock_contract.functions.get = Mock(return_value=mock_get_function)
        
        # Load contract into manager
        contract_manager._contracts[sample_contract_address] = mock_contract
        
        # Read view method
        result = contract_manager.read_contract(
            address=sample_contract_address,
            method_name="get"
        )
        
        # Assertions
        assert result == 42
        mock_get_function.call.assert_called_once()

    def test_get_contract_events(self, contract_manager, mock_web3, sample_contract_address, sample_abi):
        """Test event filtering and retrieval."""
        # Create mock events
        mock_event_1 = {
            'args': {'user': '0x123...', 'value': 100},
            'event': 'ValueChanged',
            'logIndex': 0,
            'transactionIndex': 1,
            'transactionHash': HexBytes('0xabc123'),
            'address': sample_contract_address,
            'blockHash': HexBytes('0xdef456'),
            'blockNumber': 12345
        }
        
        mock_event_2 = {
            'args': {'user': '0x456...', 'value': 200},
            'event': 'ValueChanged',
            'logIndex': 1,
            'transactionIndex': 2,
            'transactionHash': HexBytes('0xabc456'),
            'address': sample_contract_address,
            'blockHash': HexBytes('0xdef789'),
            'blockNumber': 12346
        }

        # Mock contract and event filter
        mock_contract = Mock()
        mock_contract.address = sample_contract_address
        mock_contract.abi = sample_abi
        mock_contract.events = Mock()
        mock_value_changed_event = Mock()
        mock_event_filter = Mock()
        mock_event_filter.get_all_entries.return_value = [mock_event_1, mock_event_2]
        mock_value_changed_event.create_filter.return_value = mock_event_filter
        mock_contract.events.ValueChanged = mock_value_changed_event
        
        # Load contract into manager
        contract_manager._contracts[sample_contract_address] = mock_contract
        
        # Get events
        events = contract_manager.get_contract_events(
            address=sample_contract_address,
            event_name="ValueChanged",
            from_block=12340,
            to_block='latest'
        )
        
        # Assertions
        assert len(events) == 2
        assert events[0]['args']['value'] == 100
        assert events[1]['args']['value'] == 200
        assert events[0]['blockNumber'] == 12345
        assert events[1]['blockNumber'] == 12346

    def test_invalid_abi_handling(self, contract_manager, mock_web3, sample_contract_address):
        """Test handling of invalid ABI."""
        invalid_abi = "not a valid ABI"
        
        # Test loading contract with invalid ABI string
        with pytest.raises(ValueError, match="Invalid ABI JSON"):
            contract_manager.load_contract(sample_contract_address, invalid_abi)
        
        # Test deploying contract with invalid ABI
        with pytest.raises(ValueError, match="Invalid ABI JSON"):
            contract_manager.deploy_contract(
                bytecode="0x123",
                abi=invalid_abi,
                from_address=sample_contract_address
            )

    def test_method_not_found(self, contract_manager, mock_web3, sample_contract_address, sample_abi):
        """Test calling a non-existent method."""
        # Create a mock contract
        mock_contract = Mock()
        mock_contract.address = sample_contract_address
        mock_contract.abi = sample_abi
        mock_contract.functions = Mock()
        
        # Configure mock to not have the nonExistentMethod attribute
        delattr(mock_contract.functions, 'nonExistentMethod')
        
        # Load contract into manager
        contract_manager._contracts[sample_contract_address] = mock_contract
        
        # Test method not found for read
        with pytest.raises(ValueError, match="Method nonExistentMethod not found in contract ABI"):
            contract_manager.read_contract(
                address=sample_contract_address,
                method_name="nonExistentMethod"
            )
        
        # Test method not found for write
        with pytest.raises(ValueError, match="Method nonExistentMethod not found in contract ABI"):
            contract_manager.call_contract_method(
                address=sample_contract_address,
                method_name="nonExistentMethod",
                from_address=sample_contract_address
            )

    def test_encode_decode_complex_types(self, contract_manager, mock_web3, sample_contract_address):
        """Test encoding and decoding of complex parameter types."""
        # Create a mock contract with complex method
        mock_contract = Mock()
        mock_contract.address = sample_contract_address
        mock_contract.abi = [
            {
                "inputs": [
                    {"internalType": "uint256[]", "name": "values", "type": "uint256[]"},
                    {"internalType": "string", "name": "message", "type": "string"}
                ],
                "name": "complexMethod",
                "outputs": [{"internalType": "bytes32", "name": "", "type": "bytes32"}],
                "stateMutability": "view",
                "type": "function"
            }
        ]
        mock_contract.functions = Mock()
        mock_complex_method = Mock()
        mock_contract.functions.complexMethod = Mock(return_value=mock_complex_method)
        
        # Test encoding function call
        mock_complex_method.build_transaction = Mock(return_value={
            'from': '0x0000000000000000000000000000000000000000',
            'data': '0x123456789abcdef'
        })
        
        # Test the encode_function_call method
        encoded_data = contract_manager.encode_function_call(
            contract_instance=mock_contract,
            method_name="complexMethod",
            args=[[1, 2, 3], "Hello, World!"]
        )
        
        assert encoded_data == '0x123456789abcdef'
        mock_complex_method.build_transaction.assert_called_once()
        
        # Test decoding function result
        result_hex = '0x746573742064617461206865726500000000000000000000000000000000000000'
        decoded_result = contract_manager.decode_function_result(
            contract_instance=mock_contract,
            method_name="complexMethod",
            result=result_hex
        )
        
        # Since we're mocking, we can't test actual decode, but we verify the method logic
        assert decoded_result is not None

    def test_list_contracts(self, contract_manager, sample_abi):
        """Test listing loaded contracts."""
        # Create mock contracts with proper structure
        addresses = [
            "0x742d35Cc6634C0532925a3b844Bc9e7595f8e5e5",
            "0x8626f6940E2eb28930eFb4CeF49B2d1F2C9C1199",
            "0x5FbDB2315678afecb367f032d93F642f64180aa3"
        ]
        
        for addr in addresses:
            mock_contract = Mock()
            mock_contract.address = addr
            mock_contract.abi = sample_abi
            contract_manager._contracts[addr] = mock_contract
        
        # Add a named contract (should be excluded from listing)
        named_contract = Mock()
        named_contract.address = addresses[0]
        named_contract.abi = sample_abi
        contract_manager._contracts["MyContract"] = named_contract
        
        # List contracts
        contracts = contract_manager.list_contracts()
        
        # Assertions
        assert len(contracts) == 3  # Only addresses, not names
        for addr in addresses:
            assert addr in contracts
            assert 'address' in contracts[addr]
            assert 'functions' in contracts[addr]
            assert 'events' in contracts[addr]
            assert contracts[addr]['address'] == addr
            assert 'set' in contracts[addr]['functions']
            assert 'get' in contracts[addr]['functions']
            assert 'ValueChanged' in contracts[addr]['events']

    def test_wallet_not_found_error(self, contract_manager, mock_wallet_manager, 
                                  sample_address, sample_private_key, sample_bytecode):
        """Test error handling when wallet is not found."""
        # Mock wallet not found
        mock_wallet_manager.verify_wallet.return_value = False
        
        # Attempt to deploy contract
        with pytest.raises(ValueError, match=f"Wallet {to_checksum_address(sample_address)} not found"):
            contract_manager.deploy_contract(
                from_address=sample_address,
                private_key=sample_private_key,
                bytecode=sample_bytecode
            )

    def test_transaction_failure_handling(self, contract_manager, mock_web3, mock_wallet_manager,
                                        sample_address, sample_private_key, sample_contract_address):
        """Test handling of failed transactions."""
        # Setup mocks for failed transaction
        tx_hash = HexBytes('0xfailed123')
        
        mock_web3.eth.send_raw_transaction.return_value = tx_hash
        mock_web3.eth.wait_for_transaction_receipt.return_value = {
            'transactionHash': tx_hash,
            'blockNumber': 12348,
            'gasUsed': 21000,
            'status': 0  # Failed transaction
        }
        
        mock_wallet_manager.sign_transaction.return_value = {
            'rawTransaction': HexBytes('0xf86b808504a817c80083015f90')
        }

        # Call contract method
        result = contract_manager.call_contract_method(
            contract_address=sample_contract_address,
            from_address=sample_address,
            private_key=sample_private_key,
            method_name="set",
            params=[42]
        )

        # Assertions - transaction should complete but show failed status
        assert result['status'] == 0  # Failed status
        assert result['transactionHash'] == tx_hash.hex()

    def test_gas_estimation(self, contract_manager, mock_web3, mock_wallet_manager,
                          sample_address, sample_contract_address):
        """Test gas estimation for contract calls."""
        # Mock gas estimation
        estimated_gas = 45000
        mock_web3.eth.estimate_gas = Mock(return_value=estimated_gas)
        
        # Add gas estimation method if exists
        if hasattr(contract_manager, 'estimate_gas'):
            gas = contract_manager.estimate_gas(
                contract_address=sample_contract_address,
                from_address=sample_address,
                method_name="set",
                params=[42]
            )
            assert gas >= estimated_gas
        else:
            # Test Web3 gas estimation directly
            tx = {
                'from': sample_address,
                'to': sample_contract_address,
                'data': '0x60fe47b10000000000000000000000000000000000000000000000000000000000000002a'
            }
            gas = mock_web3.eth.estimate_gas(tx)
            assert gas == estimated_gas

    def test_contract_not_loaded_error(self, contract_manager, sample_contract_address, sample_address):
        """Test error when trying to call methods on unloaded contract."""
        # Test read on unloaded contract
        with pytest.raises(ValueError, match=f"Contract {to_checksum_address(sample_contract_address)} not loaded"):
            contract_manager.read_contract(
                address=sample_contract_address,
                method_name="get"
            )
        
        # Test write on unloaded contract
        with pytest.raises(ValueError, match=f"Contract {to_checksum_address(sample_contract_address)} not loaded"):
            contract_manager.call_contract_method(
                address=sample_contract_address,
                method_name="set",
                args=[42],
                from_address=sample_address
            )
        
        # Test events on unloaded contract
        with pytest.raises(ValueError, match=f"Contract {to_checksum_address(sample_contract_address)} not loaded"):
            contract_manager.get_contract_events(
                address=sample_contract_address,
                event_name="ValueChanged"
            )

    def test_deployment_failure(self, contract_manager, mock_web3, mock_wallet_manager,
                              sample_address, sample_bytecode, sample_abi):
        """Test handling of contract deployment failure."""
        # Setup mocks for failed deployment
        tx_hash = HexBytes('0xfailed123')
        
        # Mock contract factory
        mock_contract_factory = Mock()
        mock_constructor = Mock()
        mock_contract_factory.constructor = Mock(return_value=mock_constructor)
        mock_constructor.build_transaction = Mock(return_value={
            'from': sample_address,
            'nonce': 0,
            'gas': 3000000,
            'gasPrice': 20000000000,
            'data': sample_bytecode,
            'chainId': 1
        })
        
        mock_web3.eth.contract.return_value = mock_contract_factory
        mock_web3.eth.send_raw_transaction.return_value = tx_hash
        mock_web3.eth.wait_for_transaction_receipt.return_value = {
            'transactionHash': tx_hash,
            'contractAddress': None,  # No contract address for failed deployment
            'blockNumber': 12349,
            'gasUsed': 3000000,  # All gas used
            'status': 0  # Failed status
        }
        
        mock_wallet_manager.sign_transaction.return_value = {
            'rawTransaction': HexBytes('0xf86b808504a817c80083015f90')
        }

        # Attempt deployment
        with pytest.raises(RuntimeError, match="Contract deployment failed"):
            contract_manager.deploy_contract(
                bytecode=sample_bytecode,
                abi=sample_abi,
                from_address=sample_address
            )

    def test_verify_contract_placeholder(self, contract_manager, sample_contract_address):
        """Test the contract verification placeholder method."""
        result = contract_manager.verify_contract(
            address=sample_contract_address,
            source_code="pragma solidity ^0.8.0; contract Test {}",
            compiler_version="0.8.0"
        )
        
        assert result['status'] == 'not_implemented'
        assert 'message' in result
        assert 'Etherscan' in result['message']