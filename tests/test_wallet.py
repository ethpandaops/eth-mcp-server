import pytest
from unittest.mock import Mock, patch, MagicMock, call
from web3 import Web3
from eth_account import Account
from eth_utils import to_checksum_address
from hexbytes import HexBytes
import threading
import concurrent.futures

from src.core.wallet import WalletManager


class TestWalletManager:
    """Comprehensive test suite for WalletManager functionality."""

    @pytest.fixture
    def mock_web3(self):
        """Create a mock Web3 instance."""
        mock = Mock(spec=Web3)
        mock.eth = Mock()
        mock.eth.chain_id = 1
        mock.eth.gas_price = 20000000000  # 20 gwei
        mock.eth.get_balance = Mock(return_value=1000000000000000000)  # 1 ETH
        mock.eth.get_transaction_count = Mock(return_value=0)
        mock.eth.estimate_gas = Mock(return_value=21000)
        mock.eth.account = Mock()
        mock.eth.account.sign_transaction = Mock()
        return mock

    @pytest.fixture
    def wallet_manager(self, mock_web3):
        """Create a WalletManager instance with mock Web3."""
        return WalletManager(mock_web3)

    @pytest.fixture
    def sample_private_key(self):
        """Provide a sample private key for testing."""
        return "0x4c0883a69102937d6231471b5dbb6204fe5129617082792ae468d01a3f362318"

    @pytest.fixture
    def sample_address(self):
        """Provide the address corresponding to sample_private_key."""
        return "0x2c7536E3605D9C16a7a3D7b1898e529396a65c23"

    def test_create_wallet(self, wallet_manager):
        """Test wallet creation."""
        with patch.object(Account, 'create') as mock_create:
            # Setup mock account
            mock_account = Mock()
            mock_account.address = "0x742d35Cc6634C0532925a3b844Bc9e7595f8b0d0"
            mock_account.key = Mock()
            mock_account.key.hex.return_value = "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
            mock_create.return_value = mock_account

            # Create wallet
            result = wallet_manager.create_wallet()

            # Verify result
            assert "address" in result
            assert "privateKey" in result
            assert result["address"] == to_checksum_address(mock_account.address)
            assert result["privateKey"] == mock_account.key.hex()
            
            # Verify wallet is stored
            assert result["address"] in wallet_manager.wallets
            assert wallet_manager.wallets[result["address"]] == result["privateKey"]

    def test_create_multiple_wallets(self, wallet_manager):
        """Test creating multiple wallets."""
        wallets = []
        
        with patch.object(Account, 'create') as mock_create:
            # Create 5 different wallets
            for i in range(5):
                mock_account = Mock()
                mock_account.address = f"0x{i:040x}"
                mock_account.key = Mock()
                mock_account.key.hex.return_value = f"0x{i:064x}"
                mock_create.return_value = mock_account
                
                wallet = wallet_manager.create_wallet()
                wallets.append(wallet)
        
        # Verify all wallets are unique
        addresses = [w["address"] for w in wallets]
        assert len(set(addresses)) == 5
        
        # Verify all wallets are stored
        assert len(wallet_manager.wallets) == 5
        for wallet in wallets:
            assert wallet["address"] in wallet_manager.wallets

    def test_import_wallet_valid(self, wallet_manager, sample_private_key, sample_address):
        """Test importing wallet with valid private key."""
        with patch.object(Account, 'from_key') as mock_from_key:
            # Setup mock account
            mock_account = Mock()
            mock_account.address = sample_address
            mock_from_key.return_value = mock_account
            
            # Import wallet
            result = wallet_manager.import_wallet(sample_private_key)
            
            # Verify result
            assert result["address"] == to_checksum_address(sample_address)
            assert result["privateKey"] == sample_private_key
            
            # Verify wallet is stored
            assert to_checksum_address(sample_address) in wallet_manager.wallets
            assert wallet_manager.wallets[to_checksum_address(sample_address)] == sample_private_key

    def test_import_wallet_invalid(self, wallet_manager):
        """Test importing wallet with invalid private key."""
        with patch.object(Account, 'from_key') as mock_from_key:
            mock_from_key.side_effect = ValueError("Invalid private key")
            
            with pytest.raises(ValueError):
                wallet_manager.import_wallet("invalid_key")

    def test_import_duplicate_wallet(self, wallet_manager, sample_private_key, sample_address):
        """Test importing already existing wallet."""
        with patch.object(Account, 'from_key') as mock_from_key:
            # Setup mock account
            mock_account = Mock()
            mock_account.address = sample_address
            mock_from_key.return_value = mock_account
            
            # Import wallet twice
            wallet_manager.import_wallet(sample_private_key)
            result = wallet_manager.import_wallet(sample_private_key)
            
            # Should succeed and return same wallet
            assert result["address"] == to_checksum_address(sample_address)
            assert len(wallet_manager.wallets) == 1

    def test_list_wallets_empty(self, wallet_manager):
        """Test listing wallets when no wallets exist."""
        wallets = wallet_manager.list_wallets()
        assert wallets == []

    def test_list_wallets_multiple(self, wallet_manager):
        """Test listing multiple wallets."""
        # Add wallets directly
        addresses = [
            "0x742d35Cc6634C0532925a3b844Bc9e7595f8b0d0",
            "0x2c7536E3605D9C16a7a3D7b1898e529396a65c23",
            "0x4E83362442E3c13144C29d98C20d26Be54d2b999"
        ]
        
        for addr in addresses:
            wallet_manager.wallets[to_checksum_address(addr)] = f"0x{'0' * 64}"
        
        # List wallets
        result = wallet_manager.list_wallets()
        
        # Verify all addresses are returned
        assert len(result) == 3
        for addr in addresses:
            assert to_checksum_address(addr) in result

    def test_get_balance(self, wallet_manager, mock_web3):
        """Test balance retrieval."""
        address = "0x742d35Cc6634C0532925a3b844Bc9e7595f8b0d0"
        expected_balance = 2500000000000000000  # 2.5 ETH
        
        mock_web3.eth.get_balance.return_value = expected_balance
        
        balance = wallet_manager.get_balance(address)
        
        assert balance == expected_balance
        mock_web3.eth.get_balance.assert_called_once_with(to_checksum_address(address))

    def test_get_balance_wallet_not_found(self, wallet_manager, mock_web3):
        """Test balance retrieval for non-existent wallet (should still work)."""
        address = "0x742d35Cc6634C0532925a3b844Bc9e7595f8b0d0"
        expected_balance = 1000000000000000000  # 1 ETH
        
        mock_web3.eth.get_balance.return_value = expected_balance
        
        # Should work even if wallet is not managed
        balance = wallet_manager.get_balance(address)
        
        assert balance == expected_balance
        mock_web3.eth.get_balance.assert_called_once_with(to_checksum_address(address))

    def test_sign_message(self, wallet_manager, mock_web3):
        """Test message signing (via sign_transaction with message data)."""
        # Add a wallet
        address = to_checksum_address("0x742d35Cc6634C0532925a3b844Bc9e7595f8b0d0")
        private_key = "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        wallet_manager.wallets[address] = private_key
        
        # Create a message transaction
        transaction = {
            "to": address,
            "value": 0,
            "data": "0x48656c6c6f20576f726c64"  # "Hello World" in hex
        }
        
        # Mock signing
        mock_signed = Mock()
        mock_signed.rawTransaction = HexBytes("0x1234")
        mock_signed.hash = HexBytes("0x5678")
        mock_signed.r = 12345
        mock_signed.s = 67890
        mock_signed.v = 27
        
        mock_web3.eth.account.sign_transaction.return_value = mock_signed
        mock_web3.eth.get_transaction_count.return_value = 5
        
        # Sign transaction
        result = wallet_manager.sign_transaction(address, transaction)
        
        # Verify result
        assert result["rawTransaction"] == "0x1234"
        assert result["hash"] == "0x5678"
        assert result["r"] == hex(12345)
        assert result["s"] == hex(67890)
        assert result["v"] == hex(27)

    def test_sign_transaction(self, wallet_manager, mock_web3):
        """Test transaction signing."""
        # Add a wallet
        address = to_checksum_address("0x742d35Cc6634C0532925a3b844Bc9e7595f8b0d0")
        private_key = "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        wallet_manager.wallets[address] = private_key
        
        # Create a transaction
        transaction = {
            "to": "0x2c7536E3605D9C16a7a3D7b1898e529396a65c23",
            "value": 1000000000000000000,  # 1 ETH
            "gas": 21000,
            "gasPrice": 20000000000,
            "nonce": 10
        }
        
        # Mock signing
        mock_signed = Mock()
        mock_signed.rawTransaction = HexBytes("0xf86c0a85048...")
        mock_signed.hash = HexBytes("0x7f9fade1c0d57a...")
        mock_signed.r = 99999
        mock_signed.s = 88888
        mock_signed.v = 28
        
        mock_web3.eth.account.sign_transaction.return_value = mock_signed
        
        # Sign transaction
        result = wallet_manager.sign_transaction(address, transaction)
        
        # Verify the transaction was signed with correct parameters
        mock_web3.eth.account.sign_transaction.assert_called_once_with(
            transaction, private_key
        )
        
        # Verify result format
        assert "rawTransaction" in result
        assert "hash" in result
        assert "r" in result
        assert "s" in result
        assert "v" in result

    def test_sign_transaction_wallet_not_found(self, wallet_manager):
        """Test signing transaction with non-existent wallet."""
        address = "0x742d35Cc6634C0532925a3b844Bc9e7595f8b0d0"
        transaction = {"to": address, "value": 1000}
        
        with pytest.raises(ValueError, match=f"Wallet {address} not found"):
            wallet_manager.sign_transaction(address, transaction)

    def test_sign_transaction_auto_fill_fields(self, wallet_manager, mock_web3):
        """Test transaction signing with auto-filled fields."""
        # Add a wallet
        address = to_checksum_address("0x742d35Cc6634C0532925a3b844Bc9e7595f8b0d0")
        private_key = "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        wallet_manager.wallets[address] = private_key
        
        # Create a minimal transaction
        transaction = {
            "to": "0x2c7536E3605D9C16a7a3D7b1898e529396a65c23",
            "value": 1000000000000000000
        }
        
        # Mock values
        mock_web3.eth.get_transaction_count.return_value = 15
        mock_web3.eth.gas_price = 25000000000
        mock_web3.eth.estimate_gas.return_value = 21000
        
        # Mock signing
        mock_signed = Mock()
        mock_signed.rawTransaction = HexBytes("0xabc")
        mock_signed.hash = HexBytes("0xdef")
        mock_signed.r = 111
        mock_signed.s = 222
        mock_signed.v = 27
        
        mock_web3.eth.account.sign_transaction.return_value = mock_signed
        
        # Sign transaction
        result = wallet_manager.sign_transaction(address, transaction)
        
        # Verify auto-filled fields were added
        call_args = mock_web3.eth.account.sign_transaction.call_args[0][0]
        assert call_args["nonce"] == 15
        assert call_args["gasPrice"] == 25000000000
        assert call_args["gas"] == 21000

    def test_wallet_persistence(self, wallet_manager):
        """Test wallet storage in memory."""
        # Add multiple wallets
        wallets_data = [
            ("0x742d35Cc6634C0532925a3b844Bc9e7595f8b0d0", "0x1111111111111111111111111111111111111111111111111111111111111111"),
            ("0x2c7536E3605D9C16a7a3D7b1898e529396a65c23", "0x2222222222222222222222222222222222222222222222222222222222222222"),
            ("0x4E83362442E3c13144C29d98C20d26Be54d2b999", "0x3333333333333333333333333333333333333333333333333333333333333333")
        ]
        
        for address, private_key in wallets_data:
            wallet_manager.wallets[to_checksum_address(address)] = private_key
        
        # Verify all wallets are stored
        assert len(wallet_manager.wallets) == 3
        
        # Verify each wallet
        for address, private_key in wallets_data:
            checksummed = to_checksum_address(address)
            assert checksummed in wallet_manager.wallets
            assert wallet_manager.wallets[checksummed] == private_key
        
        # Verify list_wallets returns all
        listed = wallet_manager.list_wallets()
        assert len(listed) == 3

    def test_concurrent_wallet_operations(self, wallet_manager):
        """Test thread safety of wallet operations."""
        num_threads = 10
        wallets_per_thread = 5
        
        def create_wallets(thread_id):
            """Create wallets in a thread."""
            created = []
            for i in range(wallets_per_thread):
                with patch.object(Account, 'create') as mock_create:
                    mock_account = Mock()
                    # Create unique address for each wallet
                    mock_account.address = f"0x{thread_id:02d}{i:038x}"
                    mock_account.key = Mock()
                    mock_account.key.hex.return_value = f"0x{thread_id:02d}{i:062x}"
                    mock_create.return_value = mock_account
                    
                    wallet = wallet_manager.create_wallet()
                    created.append(wallet["address"])
            return created
        
        # Run concurrent wallet creation
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(create_wallets, i) for i in range(num_threads)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # Verify all wallets were created
        total_wallets = sum(len(result) for result in results)
        assert total_wallets == num_threads * wallets_per_thread
        
        # Verify all wallets are in manager
        assert len(wallet_manager.wallets) == num_threads * wallets_per_thread
        
        # Verify no duplicates
        all_addresses = [addr for result in results for addr in result]
        assert len(set(all_addresses)) == len(all_addresses)

    def test_verify_wallet(self, wallet_manager):
        """Test wallet verification."""
        # Add a wallet
        address = to_checksum_address("0x742d35Cc6634C0532925a3b844Bc9e7595f8b0d0")
        wallet_manager.wallets[address] = "0x1234567890abcdef"
        
        # Verify existing wallet
        assert wallet_manager.verify_wallet(address) is True
        
        # Verify non-existing wallet
        other_address = "0x2c7536E3605D9C16a7a3D7b1898e529396a65c23"
        assert wallet_manager.verify_wallet(other_address) is False

    def test_get_transaction_count(self, wallet_manager, mock_web3):
        """Test getting transaction count (nonce)."""
        address = "0x742d35Cc6634C0532925a3b844Bc9e7595f8b0d0"
        expected_nonce = 42
        
        mock_web3.eth.get_transaction_count.return_value = expected_nonce
        
        nonce = wallet_manager.get_transaction_count(address)
        
        assert nonce == expected_nonce
        mock_web3.eth.get_transaction_count.assert_called_once_with(to_checksum_address(address))

    def test_import_wallet_without_0x_prefix(self, wallet_manager, sample_address):
        """Test importing wallet with private key without 0x prefix."""
        private_key_no_prefix = "4c0883a69102937d6231471b5dbb6204fe5129617082792ae468d01a3f362318"
        
        with patch.object(Account, 'from_key') as mock_from_key:
            # Setup mock account
            mock_account = Mock()
            mock_account.address = sample_address
            mock_from_key.return_value = mock_account
            
            # Import wallet
            result = wallet_manager.import_wallet(private_key_no_prefix)
            
            # Verify 0x was added
            assert result["privateKey"] == "0x" + private_key_no_prefix
            mock_from_key.assert_called_once_with("0x" + private_key_no_prefix)

    def test_case_insensitive_address_handling(self, wallet_manager, mock_web3):
        """Test that addresses are handled case-insensitively."""
        # Test with mixed case address
        mixed_case_address = "0x742d35cc6634c0532925a3b844bc9e7595f8b0d0"
        checksum_address = to_checksum_address(mixed_case_address)
        
        # Add wallet with mixed case
        wallet_manager.wallets[checksum_address] = "0x1234"
        
        # Test various operations with different case
        assert wallet_manager.verify_wallet(mixed_case_address.upper()) is False  # Different checksum
        assert wallet_manager.verify_wallet(checksum_address) is True
        
        # get_balance should work with any case
        wallet_manager.get_balance(mixed_case_address)
        mock_web3.eth.get_balance.assert_called_with(checksum_address)