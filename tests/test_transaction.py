import pytest
from unittest.mock import Mock, MagicMock, patch, AsyncMock, call
from web3 import Web3
from eth_utils import to_checksum_address
from hexbytes import HexBytes
import asyncio
from datetime import datetime

from src.core.transaction import TransactionManager
from src.core.wallet import WalletManager


@pytest.fixture
def mock_w3():
    """Create a mock Web3 instance."""
    w3 = Mock(spec=Web3)
    w3.eth = Mock()
    w3.eth.account = Mock()
    return w3


@pytest.fixture
def mock_wallet_manager():
    """Create a mock WalletManager instance."""
    manager = Mock(spec=WalletManager)
    return manager


@pytest.fixture
def transaction_manager(mock_w3, mock_wallet_manager):
    """Create a TransactionManager instance with mocked dependencies."""
    return TransactionManager(mock_w3, mock_wallet_manager)


class TestTransactionManager:
    """Test cases for TransactionManager functionality."""

    def test_send_transaction_success(self, transaction_manager, mock_w3, mock_wallet_manager):
        """Test successful transaction sending."""
        # Setup
        from_address = "0x742d35Cc6634C0532925a3b844Bc9e7595f4b0d0"
        to_address = "0x742d35Cc6634C0532925a3b844Bc9e7595f4b0d1"
        tx_params = {
            'from': from_address,
            'to': to_address,
            'value': 1000000000000000000,  # 1 ETH
            'gas': 21000,
            'gasPrice': 20000000000
        }
        
        mock_wallet_manager.verify_wallet.return_value = True
        mock_wallet_manager.sign_transaction.return_value = {
            'rawTransaction': HexBytes('0x1234567890abcdef')
        }
        mock_w3.eth.send_raw_transaction.return_value = HexBytes('0xabcdef1234567890')
        
        # Execute
        tx_hash = transaction_manager.send_transaction(tx_params)
        
        # Assert
        assert tx_hash == '0xabcdef1234567890'
        mock_wallet_manager.verify_wallet.assert_called_once_with(to_checksum_address(from_address))
        mock_wallet_manager.sign_transaction.assert_called_once_with(to_checksum_address(from_address), tx_params)
        mock_w3.eth.send_raw_transaction.assert_called_once()

    def test_send_transaction_insufficient_funds(self, transaction_manager, mock_w3, mock_wallet_manager):
        """Test transaction with insufficient balance."""
        # Setup
        from_address = "0x742d35Cc6634C0532925a3b844Bc9e7595f4b0d0"
        tx_params = {
            'from': from_address,
            'to': "0x742d35Cc6634C0532925a3b844Bc9e7595f4b0d1",
            'value': 1000000000000000000
        }
        
        mock_wallet_manager.verify_wallet.return_value = True
        mock_wallet_manager.sign_transaction.side_effect = Exception("insufficient funds for gas * price + value")
        
        # Execute & Assert
        with pytest.raises(Exception, match="insufficient funds"):
            transaction_manager.send_transaction(tx_params)

    def test_send_transaction_invalid_recipient(self, transaction_manager, mock_wallet_manager):
        """Test transaction with invalid recipient address."""
        # Setup
        tx_params = {
            'from': "0x742d35Cc6634C0532925a3b844Bc9e7595f4b0d0",
            'to': "invalid_address",
            'value': 1000000000000000000
        }
        
        mock_wallet_manager.verify_wallet.return_value = True
        mock_wallet_manager.sign_transaction.side_effect = ValueError("invalid address")
        
        # Execute & Assert
        with pytest.raises(ValueError, match="invalid address"):
            transaction_manager.send_transaction(tx_params)

    def test_estimate_gas(self, transaction_manager, mock_w3):
        """Test gas estimation."""
        # Setup
        tx_params = {
            'from': "0x742d35Cc6634C0532925a3b844Bc9e7595f4b0d0",
            'to': "0x742d35Cc6634C0532925a3b844Bc9e7595f4b0d1",
            'value': 1000000000000000000
        }
        mock_w3.eth.estimate_gas.return_value = 21000
        
        # Execute
        gas_estimate = transaction_manager.estimate_gas(tx_params)
        
        # Assert
        assert gas_estimate == 21000
        mock_w3.eth.estimate_gas.assert_called_once_with(tx_params)

    def test_get_transaction_by_hash(self, transaction_manager, mock_w3):
        """Test transaction retrieval by hash."""
        # Setup
        tx_hash = "0xabcdef1234567890"
        mock_tx = {
            'hash': HexBytes(tx_hash),
            'nonce': 10,
            'blockHash': HexBytes('0x1234567890abcdef'),
            'blockNumber': 12345,
            'transactionIndex': 5,
            'from': "0x742d35Cc6634C0532925a3b844Bc9e7595f4b0d0",
            'to': "0x742d35Cc6634C0532925a3b844Bc9e7595f4b0d1",
            'value': 1000000000000000000,
            'gasPrice': 20000000000,
            'gas': 21000,
            'input': '0x',
            'v': 27,
            'r': 123456789,
            's': 987654321
        }
        mock_w3.eth.get_transaction.return_value = mock_tx
        
        # Execute
        transaction = transaction_manager.get_transaction(tx_hash)
        
        # Assert
        assert transaction['hash'] == tx_hash
        assert transaction['nonce'] == 10
        assert transaction['from'] == mock_tx['from']
        assert transaction['to'] == mock_tx['to']
        assert transaction['value'] == str(mock_tx['value'])
        mock_w3.eth.get_transaction.assert_called_once_with(tx_hash)

    def test_get_transaction_receipt(self, transaction_manager, mock_w3):
        """Test transaction receipt retrieval."""
        # Setup
        tx_hash = "0xabcdef1234567890"
        mock_receipt = {
            'transactionHash': HexBytes(tx_hash),
            'blockHash': HexBytes('0x1234567890abcdef'),
            'blockNumber': 12345,
            'from': "0x742d35Cc6634C0532925a3b844Bc9e7595f4b0d0",
            'to': "0x742d35Cc6634C0532925a3b844Bc9e7595f4b0d1",
            'contractAddress': None,
            'cumulativeGasUsed': 21000,
            'gasUsed': 21000,
            'effectiveGasPrice': 20000000000,
            'status': 1,
            'logs': [
                {
                    'address': "0x742d35Cc6634C0532925a3b844Bc9e7595f4b0d2",
                    'topics': [HexBytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef')],
                    'data': '0x0000000000000000000000000000000000000000000000000de0b6b3a7640000',
                    'blockNumber': 12345,
                    'transactionHash': HexBytes(tx_hash),
                    'logIndex': 0,
                    'blockHash': HexBytes('0x1234567890abcdef')
                }
            ]
        }
        mock_w3.eth.get_transaction_receipt.return_value = mock_receipt
        
        # Execute
        receipt = transaction_manager.get_transaction_receipt(tx_hash)
        
        # Assert
        assert receipt['transactionHash'] == tx_hash
        assert receipt['status'] == 1
        assert receipt['gasUsed'] == 21000
        assert len(receipt['logs']) == 1
        assert receipt['logs'][0]['address'] == mock_receipt['logs'][0]['address']
        mock_w3.eth.get_transaction_receipt.assert_called_once_with(tx_hash)

    def test_get_transaction_not_found(self, transaction_manager, mock_w3):
        """Test retrieval of non-existent transaction."""
        # Setup
        tx_hash = "0xnonexistent"
        mock_w3.eth.get_transaction.side_effect = Exception("Transaction not found")
        
        # Execute & Assert
        with pytest.raises(Exception, match="Transaction not found"):
            transaction_manager.get_transaction(tx_hash)

    def test_get_nonce(self, transaction_manager, mock_w3):
        """Test nonce management."""
        # Setup
        address = "0x742d35Cc6634C0532925a3b844Bc9e7595f4b0d0"
        mock_w3.eth.get_transaction_count.return_value = 10
        
        # Execute
        nonce = transaction_manager.get_transaction_count(address)
        
        # Assert
        assert nonce == 10
        mock_w3.eth.get_transaction_count.assert_called_once_with(to_checksum_address(address), 'latest')

    def test_get_gas_price(self, transaction_manager, mock_w3):
        """Test gas price retrieval."""
        # Setup
        mock_w3.eth.gas_price = 20000000000  # 20 gwei
        
        # Execute
        gas_price = transaction_manager.get_gas_price()
        
        # Assert
        assert gas_price == 20000000000

    def test_transaction_history(self, transaction_manager, mock_w3):
        """Test transaction history retrieval."""
        # Setup
        address = "0x742d35Cc6634C0532925a3b844Bc9e7595f4b0d0"
        mock_w3.eth.block_number = 100
        
        # Mock blocks with transactions
        mock_blocks = []
        for i in range(98, 101):
            block = Mock()
            block.transactions = [
                {
                    'hash': HexBytes(f'0xhash{i}'),
                    'nonce': i,
                    'blockHash': HexBytes(f'0xblock{i}'),
                    'blockNumber': i,
                    'transactionIndex': 0,
                    'from': address,
                    'to': "0x742d35Cc6634C0532925a3b844Bc9e7595f4b0d1",
                    'value': 1000000000000000000,
                    'gasPrice': 20000000000,
                    'gas': 21000,
                    'input': '0x',
                    'v': 27,
                    'r': 123456789,
                    's': 987654321
                }
            ]
            mock_blocks.append(block)
        
        mock_w3.eth.get_block.side_effect = mock_blocks
        
        # Mock timestamp for formatting
        with patch.object(transaction_manager.w3.eth, 'get_block') as mock_get_block_ts:
            mock_get_block_ts.return_value = {'timestamp': 1640000000}
            
            # Execute
            history = transaction_manager.get_transaction_history(address, 98, 100)
        
        # Assert
        assert len(history) == 3
        assert all(tx['from'] == address for tx in history)
        assert mock_w3.eth.get_block.call_count == 3

    def test_transaction_history_with_filters(self, transaction_manager, mock_w3):
        """Test filtered transaction history retrieval."""
        # Setup
        address = "0x742d35Cc6634C0532925a3b844Bc9e7595f4b0d0"
        other_address = "0x742d35Cc6634C0532925a3b844Bc9e7595f4b0d1"
        mock_w3.eth.block_number = 100
        
        # Mock block with mixed transactions
        block = Mock()
        block.transactions = [
            {
                'hash': HexBytes('0xhash1'),
                'nonce': 1,
                'blockHash': HexBytes('0xblock1'),
                'blockNumber': 100,
                'transactionIndex': 0,
                'from': address,
                'to': other_address,
                'value': 1000000000000000000,
                'gasPrice': 20000000000,
                'gas': 21000,
                'input': '0x',
                'v': 27,
                'r': 123456789,
                's': 987654321
            },
            {
                'hash': HexBytes('0xhash2'),
                'nonce': 2,
                'blockHash': HexBytes('0xblock1'),
                'blockNumber': 100,
                'transactionIndex': 1,
                'from': other_address,
                'to': address,
                'value': 500000000000000000,
                'gasPrice': 20000000000,
                'gas': 21000,
                'input': '0x',
                'v': 27,
                'r': 123456789,
                's': 987654321
            },
            {
                'hash': HexBytes('0xhash3'),
                'nonce': 3,
                'blockHash': HexBytes('0xblock1'),
                'blockNumber': 100,
                'transactionIndex': 2,
                'from': "0x0000000000000000000000000000000000000000",
                'to': other_address,
                'value': 100000000000000000,
                'gasPrice': 20000000000,
                'gas': 21000,
                'input': '0x',
                'v': 27,
                'r': 123456789,
                's': 987654321
            }
        ]
        mock_w3.eth.get_block.return_value = block
        
        # Mock timestamp
        with patch.object(transaction_manager.w3.eth, 'get_block') as mock_get_block_ts:
            mock_get_block_ts.return_value = {'timestamp': 1640000000}
            
            # Execute
            history = transaction_manager.get_transaction_history(address, 100, 100)
        
        # Assert - should only return transactions involving the address
        assert len(history) == 2
        assert history[0]['hash'] == '0xhash1'
        assert history[1]['hash'] == '0xhash2'

    def test_batch_transactions(self, transaction_manager, mock_w3, mock_wallet_manager):
        """Test batch transaction sending."""
        # Setup
        from_address = "0x742d35Cc6634C0532925a3b844Bc9e7595f4b0d0"
        transactions = [
            {
                'from': from_address,
                'to': "0x742d35Cc6634C0532925a3b844Bc9e7595f4b0d1",
                'value': 1000000000000000000,
                'nonce': 10
            },
            {
                'from': from_address,
                'to': "0x742d35Cc6634C0532925a3b844Bc9e7595f4b0d2",
                'value': 2000000000000000000,
                'nonce': 11
            },
            {
                'from': from_address,
                'to': "0x742d35Cc6634C0532925a3b844Bc9e7595f4b0d3",
                'value': 3000000000000000000,
                'nonce': 12
            }
        ]
        
        mock_wallet_manager.verify_wallet.return_value = True
        mock_wallet_manager.sign_transaction.return_value = {
            'rawTransaction': HexBytes('0x1234567890abcdef')
        }
        mock_w3.eth.send_raw_transaction.side_effect = [
            HexBytes('0xhash1'),
            HexBytes('0xhash2'),
            HexBytes('0xhash3')
        ]
        
        # Execute
        tx_hashes = []
        for tx in transactions:
            tx_hash = transaction_manager.send_transaction(tx)
            tx_hashes.append(tx_hash)
        
        # Assert
        assert len(tx_hashes) == 3
        assert tx_hashes == ['0xhash1', '0xhash2', '0xhash3']
        assert mock_wallet_manager.verify_wallet.call_count == 3
        assert mock_wallet_manager.sign_transaction.call_count == 3
        assert mock_w3.eth.send_raw_transaction.call_count == 3

    @pytest.mark.asyncio
    async def test_transaction_monitoring(self, transaction_manager, mock_w3):
        """Test WebSocket transaction monitoring."""
        # Setup
        address = "0x742d35Cc6634C0532925a3b844Bc9e7595f4b0d0"
        received_transactions = []
        
        async def callback(tx):
            received_transactions.append(tx)
        
        # Mock initial block number
        mock_w3.eth.block_number = 100
        
        # Mock blocks with transactions
        block_numbers = [100, 101, 102]
        blocks = []
        for block_num in block_numbers:
            block = Mock()
            block.transactions = [
                {
                    'hash': HexBytes(f'0xhash{block_num}'),
                    'nonce': block_num,
                    'blockHash': HexBytes(f'0xblock{block_num}'),
                    'blockNumber': block_num,
                    'transactionIndex': 0,
                    'from': address,
                    'to': "0x742d35Cc6634C0532925a3b844Bc9e7595f4b0d1",
                    'value': 1000000000000000000,
                    'gasPrice': 20000000000,
                    'gas': 21000,
                    'input': '0x',
                    'v': 27,
                    'r': 123456789,
                    's': 987654321
                }
            ]
            blocks.append(block)
        
        # Mock get_block to return appropriate blocks
        def get_block_side_effect(block_number, full_transactions=False):
            if block_number in [101, 102]:
                return blocks[block_number - 100]
            return Mock(transactions=[])
        
        mock_w3.eth.get_block.side_effect = get_block_side_effect
        
        # Mock timestamp
        with patch.object(transaction_manager.w3.eth, 'get_block') as mock_get_block_ts:
            mock_get_block_ts.return_value = {'timestamp': 1640000000}
            
            # Start monitoring
            transaction_manager.start_monitoring(address, callback)
            
            # Simulate block number changes
            mock_w3.eth.block_number = 101
            await asyncio.sleep(0.1)  # Allow monitor to process
            
            mock_w3.eth.block_number = 102
            await asyncio.sleep(0.1)  # Allow monitor to process
            
            # Stop monitoring
            transaction_manager.stop_monitoring(address)
            
            # Allow final processing
            await asyncio.sleep(0.1)
        
        # Assert
        assert len(received_transactions) >= 1  # At least one transaction should be received
        assert all(tx['from'] == address for tx in received_transactions)

    def test_concurrent_transactions(self, transaction_manager, mock_w3, mock_wallet_manager):
        """Test concurrent transaction sending."""
        # Setup
        from_address = "0x742d35Cc6634C0532925a3b844Bc9e7595f4b0d0"
        
        # Mock wallet manager
        mock_wallet_manager.verify_wallet.return_value = True
        mock_wallet_manager.sign_transaction.return_value = {
            'rawTransaction': HexBytes('0x1234567890abcdef')
        }
        
        # Mock concurrent nonce management
        nonce_counter = {'value': 10}
        
        def get_nonce_side_effect(address):
            current = nonce_counter['value']
            nonce_counter['value'] += 1
            return current
        
        mock_wallet_manager.get_transaction_count.side_effect = get_nonce_side_effect
        
        # Mock send_raw_transaction to return unique hashes
        tx_counter = {'value': 0}
        
        def send_raw_tx_side_effect(raw_tx):
            tx_counter['value'] += 1
            return HexBytes(f'0xhash{tx_counter["value"]}')
        
        mock_w3.eth.send_raw_transaction.side_effect = send_raw_tx_side_effect
        
        # Execute - Send multiple transactions concurrently
        import concurrent.futures
        
        def send_tx(index):
            tx_params = {
                'from': from_address,
                'to': f"0x742d35Cc6634C0532925a3b844Bc9e7595f4b0d{index}",
                'value': 1000000000000000000 * index,
                'nonce': 10 + index
            }
            return transaction_manager.send_transaction(tx_params)
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(send_tx, i) for i in range(5)]
            tx_hashes = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # Assert
        assert len(tx_hashes) == 5
        assert len(set(tx_hashes)) == 5  # All hashes should be unique
        assert mock_wallet_manager.verify_wallet.call_count == 5
        assert mock_wallet_manager.sign_transaction.call_count == 5
        assert mock_w3.eth.send_raw_transaction.call_count == 5

    def test_eip1559_transaction(self, transaction_manager, mock_w3, mock_wallet_manager):
        """Test EIP-1559 transaction support."""
        # Setup
        from_address = "0x742d35Cc6634C0532925a3b844Bc9e7595f4b0d0"
        
        # EIP-1559 transaction parameters
        tx_params = {
            'from': from_address,
            'to': "0x742d35Cc6634C0532925a3b844Bc9e7595f4b0d1",
            'value': 1000000000000000000,
            'maxFeePerGas': 30000000000,  # 30 gwei
            'maxPriorityFeePerGas': 2000000000,  # 2 gwei
            'type': '0x2'  # EIP-1559 transaction type
        }
        
        mock_wallet_manager.verify_wallet.return_value = True
        mock_wallet_manager.sign_transaction.return_value = {
            'rawTransaction': HexBytes('0xeip1559transaction')
        }
        mock_w3.eth.send_raw_transaction.return_value = HexBytes('0xeip1559hash')
        
        # Execute
        tx_hash = transaction_manager.send_transaction(tx_params)
        
        # Assert
        assert tx_hash == '0xeip1559hash'
        mock_wallet_manager.sign_transaction.assert_called_once()
        
        # Verify EIP-1559 parameters were passed correctly
        signed_tx_params = mock_wallet_manager.sign_transaction.call_args[0][1]
        assert 'maxFeePerGas' in signed_tx_params
        assert 'maxPriorityFeePerGas' in signed_tx_params
        assert signed_tx_params['type'] == '0x2'

    def test_get_gas_price_estimate(self, transaction_manager, mock_w3):
        """Test gas price estimation for different priorities."""
        # Setup
        mock_block = {
            'baseFeePerGas': 10000000000  # 10 gwei
        }
        mock_w3.eth.get_block.return_value = mock_block
        mock_w3.eth.max_priority_fee = 1000000000  # 1 gwei
        
        # Execute
        gas_estimates = transaction_manager.get_gas_price_estimate()
        
        # Assert
        assert 'slow' in gas_estimates
        assert 'standard' in gas_estimates
        assert 'fast' in gas_estimates
        assert 'instant' in gas_estimates
        
        # Verify pricing tiers
        assert gas_estimates['slow'] == 11000000000  # 10 + 1
        assert gas_estimates['standard'] == 12000000000  # 10 + 2
        assert gas_estimates['fast'] == 13000000000  # 10 + 3
        assert gas_estimates['instant'] == 14000000000  # 10 + 4
        
        # Verify progressive pricing
        assert gas_estimates['slow'] < gas_estimates['standard']
        assert gas_estimates['standard'] < gas_estimates['fast']
        assert gas_estimates['fast'] < gas_estimates['instant']

    def test_send_transaction_no_sender(self, transaction_manager):
        """Test transaction without sender address."""
        # Setup
        tx_params = {
            'to': "0x742d35Cc6634C0532925a3b844Bc9e7595f4b0d1",
            'value': 1000000000000000000
        }
        
        # Execute & Assert
        with pytest.raises(ValueError, match="Sender address required"):
            transaction_manager.send_transaction(tx_params)

    def test_send_transaction_wallet_not_found(self, transaction_manager, mock_wallet_manager):
        """Test transaction with wallet not in manager."""
        # Setup
        from_address = "0x742d35Cc6634C0532925a3b844Bc9e7595f4b0d0"
        tx_params = {
            'from': from_address,
            'to': "0x742d35Cc6634C0532925a3b844Bc9e7595f4b0d1",
            'value': 1000000000000000000
        }
        
        mock_wallet_manager.verify_wallet.return_value = False
        
        # Execute & Assert
        with pytest.raises(ValueError, match=f"Wallet {to_checksum_address(from_address)} not found"):
            transaction_manager.send_transaction(tx_params)

    def test_format_transaction_no_block(self, transaction_manager, mock_w3):
        """Test formatting transaction without block number."""
        # Setup
        tx = {
            'hash': HexBytes('0xhash'),
            'nonce': 1,
            'blockHash': None,
            'blockNumber': None,
            'transactionIndex': None,
            'from': "0x742d35Cc6634C0532925a3b844Bc9e7595f4b0d0",
            'to': "0x742d35Cc6634C0532925a3b844Bc9e7595f4b0d1",
            'value': 1000000000000000000,
            'gasPrice': 20000000000,
            'gas': 21000,
            'input': '0x',
            'v': 27,
            'r': 123456789,
            's': 987654321
        }
        
        # Execute
        formatted = transaction_manager._format_transaction(tx)
        
        # Assert
        assert formatted['hash'] == '0xhash'
        assert formatted['blockHash'] is None
        assert formatted['timestamp'] is None