"""Tests for request validation middleware."""

import pytest
from pydantic import ValidationError
from src.middleware import (
    validate_request,
    validate_address_checksum,
    validate_transaction_params,
    validate_value_bounds,
    sanitize_hex_input,
    EthereumAddress,
    PrivateKey,
    HexString,
    BlockIdentifier,
    Wei,
    GasLimit,
    GasPrice,
    TransactionParams,
    ContractDeployParams,
    ContractCallParams,
    WalletImportParams,
)


class TestEthereumAddress:
    """Test Ethereum address validation."""
    
    def test_valid_address(self):
        """Test valid address validation."""
        # Valid checksummed address
        addr = "0x742d35Cc6634C0532925a3b844Bc9e7595f6AEdb"
        result = EthereumAddress.validate(addr)
        assert result == addr
    
    def test_lowercase_address(self):
        """Test lowercase address gets checksummed."""
        addr = "0x742d35cc6634c0532925a3b844bc9e7595f6aedb"
        result = EthereumAddress.validate(addr)
        # Should return checksummed version
        assert result == "0x742d35Cc6634C0532925a3b844Bc9e7595f6AEdb"
    
    def test_invalid_length(self):
        """Test address with invalid length."""
        with pytest.raises(ValueError, match="42 characters"):
            EthereumAddress.validate("0x742d35Cc")
    
    def test_invalid_hex(self):
        """Test address with invalid hex characters."""
        with pytest.raises(ValueError, match="hexadecimal"):
            EthereumAddress.validate("0xGGGG35Cc6634C0532925a3b844Bc9e7595f6AEdb")
    
    def test_no_prefix(self):
        """Test address without 0x prefix."""
        with pytest.raises(ValueError, match="start with 0x"):
            EthereumAddress.validate("742d35Cc6634C0532925a3b844Bc9e7595f6AEdb")


class TestPrivateKey:
    """Test private key validation."""
    
    def test_valid_private_key(self):
        """Test valid private key."""
        key = "0x" + "a" * 64
        result = PrivateKey.validate(key)
        assert result == key
    
    def test_invalid_length(self):
        """Test private key with wrong length."""
        with pytest.raises(ValueError, match="66 characters"):
            PrivateKey.validate("0x" + "a" * 63)
    
    def test_invalid_format(self):
        """Test private key with invalid format."""
        with pytest.raises(ValueError, match="66 characters"):
            PrivateKey.validate("not_a_private_key")


class TestHexString:
    """Test hex string validation."""
    
    def test_valid_hex(self):
        """Test valid hex strings."""
        assert HexString.validate("0x") == "0x"
        assert HexString.validate("0x1234abcd") == "0x1234abcd"
        assert HexString.validate("0xABCDEF") == "0xABCDEF"
    
    def test_invalid_hex(self):
        """Test invalid hex strings."""
        with pytest.raises(ValueError, match="Invalid hex"):
            HexString.validate("0xGHIJ")
        
        with pytest.raises(ValueError, match="Invalid hex"):
            HexString.validate("1234")  # Missing 0x


class TestBlockIdentifier:
    """Test block identifier validation."""
    
    def test_special_values(self):
        """Test special block values."""
        assert BlockIdentifier.validate("latest") == "latest"
        assert BlockIdentifier.validate("pending") == "pending"
        assert BlockIdentifier.validate("earliest") == "earliest"
    
    def test_numeric_values(self):
        """Test numeric block values."""
        assert BlockIdentifier.validate("12345") == "12345"
        assert BlockIdentifier.validate(12345) == "12345"
        assert BlockIdentifier.validate("0x1e240") == "0x1e240"
    
    def test_invalid_values(self):
        """Test invalid block identifiers."""
        with pytest.raises(ValueError, match="Invalid block"):
            BlockIdentifier.validate("invalid")


class TestWei:
    """Test Wei value validation."""
    
    def test_valid_wei(self):
        """Test valid Wei values."""
        assert Wei.validate(0) == 0
        assert Wei.validate(1000000000000000000) == 1000000000000000000
        assert Wei.validate("1000") == 1000
        assert Wei.validate("0x3e8") == 1000
    
    def test_negative_wei(self):
        """Test negative Wei values."""
        with pytest.raises(ValueError, match="cannot be negative"):
            Wei.validate(-1)
    
    def test_overflow(self):
        """Test Wei overflow."""
        max_uint256 = 2**256 - 1
        assert Wei.validate(max_uint256) == max_uint256
        
        with pytest.raises(ValueError, match="exceeds maximum"):
            Wei.validate(2**256)


class TestGasParameters:
    """Test gas parameter validation."""
    
    def test_valid_gas_limit(self):
        """Test valid gas limits."""
        assert GasLimit.validate(21000) == 21000
        assert GasLimit.validate("100000") == 100000
        assert GasLimit.validate("0x5208") == 21000
    
    def test_invalid_gas_limit(self):
        """Test invalid gas limits."""
        with pytest.raises(ValueError, match="must be positive"):
            GasLimit.validate(0)
        
        with pytest.raises(ValueError, match="exceeds maximum"):
            GasLimit.validate(30000001)
    
    def test_valid_gas_price(self):
        """Test valid gas prices."""
        assert GasPrice.validate(0) == 0
        assert GasPrice.validate(20000000000) == 20000000000  # 20 Gwei
        assert GasPrice.validate("0x4a817c800") == 20000000000
    
    def test_invalid_gas_price(self):
        """Test invalid gas prices."""
        with pytest.raises(ValueError, match="exceeds maximum"):
            GasPrice.validate(10_000_000_000_001)  # Over 10k Gwei


class TestTransactionParams:
    """Test transaction parameter validation."""
    
    def test_valid_transaction(self):
        """Test valid transaction parameters."""
        params = {
            "from": "0x742d35Cc6634C0532925a3b844Bc9e7595f6AEdb",
            "to": "0x123456789012345678901234567890123456aEdb",
            "value": 1000000000000000000,  # 1 ETH
            "gas": 21000,
            "gasPrice": 20000000000  # 20 Gwei
        }
        
        tx = TransactionParams(**params)
        assert tx.from_address == params["from"]
        assert tx.to == "0x123456789012345678901234567890123456AEdb"  # Checksummed
        assert tx.value == params["value"]
        assert tx.gas == params["gas"]
        assert tx.gasPrice == params["gasPrice"]
    
    def test_eip1559_transaction(self):
        """Test EIP-1559 transaction parameters."""
        params = {
            "from": "0x742d35Cc6634C0532925a3b844Bc9e7595f6AEdb",
            "to": "0x123456789012345678901234567890123456aEdb",
            "value": 1000000000000000000,
            "gas": 21000,
            "maxFeePerGas": 30000000000,
            "maxPriorityFeePerGas": 2000000000
        }
        
        tx = TransactionParams(**params)
        assert tx.maxFeePerGas == params["maxFeePerGas"]
        assert tx.maxPriorityFeePerGas == params["maxPriorityFeePerGas"]
        assert tx.gasPrice is None
    
    def test_invalid_eip1559_mix(self):
        """Test mixing gasPrice with EIP-1559 parameters."""
        params = {
            "from": "0x742d35Cc6634C0532925a3b844Bc9e7595f6AEdb",
            "gasPrice": 20000000000,
            "maxFeePerGas": 30000000000
        }
        
        with pytest.raises(ValidationError, match="Cannot specify both"):
            TransactionParams(**params)


class TestContractParams:
    """Test contract-related parameter validation."""
    
    def test_valid_deploy_params(self):
        """Test valid contract deployment parameters."""
        params = {
            "bytecode": "0x60606040",
            "abi": [{"type": "constructor", "inputs": []}],
            "from": "0x742d35Cc6634C0532925a3b844Bc9e7595f6AEdb",
            "gas": 1000000
        }
        
        deploy = ContractDeployParams(**params)
        assert deploy.bytecode == params["bytecode"]
        assert deploy.abi == params["abi"]
        assert deploy.from_address == params["from"]
    
    def test_empty_bytecode(self):
        """Test empty bytecode validation."""
        params = {
            "bytecode": "0x",
            "abi": [{"type": "function"}],
            "from": "0x742d35Cc6634C0532925a3b844Bc9e7595f6AEdb"
        }
        
        with pytest.raises(ValidationError, match="cannot be empty"):
            ContractDeployParams(**params)
    
    def test_valid_call_params(self):
        """Test valid contract call parameters."""
        params = {
            "contractAddress": "0x742d35Cc6634C0532925a3b844Bc9e7595f6AEdb",
            "method": "transfer",
            "args": ["0x123456789012345678901234567890123456AEdb", 1000],
            "from": "0x742d35Cc6634C0532925a3b844Bc9e7595f6AEdb"
        }
        
        call = ContractCallParams(**params)
        assert call.contractAddress == params["contractAddress"]
        assert call.method == params["method"]
        assert call.args == params["args"]


class TestValidationDecorator:
    """Test the validation decorator."""
    
    def test_sync_function_validation(self):
        """Test validation on synchronous functions."""
        @validate_request(TransactionParams)
        def send_tx(params: dict):
            return {"success": True, "from": params["from"]}
        
        # Valid params
        result = send_tx(params={
            "from": "0x742d35Cc6634C0532925a3b844Bc9e7595f6AEdb",
            "to": "0x123456789012345678901234567890123456AEdb",
            "value": 1000
        })
        assert result["success"] is True
        
        # Invalid params
        with pytest.raises(ValueError, match="Validation failed"):
            send_tx(params={"from": "invalid_address"})
    
    @pytest.mark.asyncio
    async def test_async_function_validation(self):
        """Test validation on asynchronous functions."""
        @validate_request(ContractCallParams)
        async def call_contract(params: dict):
            return {"result": f"Called {params['method']}"}
        
        # Valid params
        result = await call_contract(params={
            "contractAddress": "0x742d35Cc6634C0532925a3b844Bc9e7595f6AEdb",
            "method": "balanceOf",
            "args": ["0x123456789012345678901234567890123456AEdb"]
        })
        assert "Called balanceOf" in result["result"]
        
        # Invalid params
        with pytest.raises(ValueError, match="Validation failed"):
            await call_contract(params={"contractAddress": "not_an_address"})


class TestUtilityFunctions:
    """Test utility validation functions."""
    
    def test_sanitize_hex_input(self):
        """Test hex input sanitization."""
        assert sanitize_hex_input("0xABCD") == "0xabcd"
        assert sanitize_hex_input("0x123") == "0x0123"  # Padded
        
        with pytest.raises(ValueError, match="Invalid hex"):
            sanitize_hex_input("not_hex")
    
    def test_validate_address_checksum(self):
        """Test address checksum validation."""
        addr = validate_address_checksum("0x742d35cc6634c0532925a3b844bc9e7595f6aedb")
        assert addr == "0x742d35Cc6634C0532925a3b844Bc9e7595f6AEdb"
        
        with pytest.raises(ValueError, match="Invalid address"):
            validate_address_checksum("invalid")
    
    def test_validate_transaction_params(self):
        """Test transaction parameter validation."""
        params = {
            "from": "0x742d35Cc6634C0532925a3b844Bc9e7595f6AEdb",
            "to": "0x123456789012345678901234567890123456AEdb",
            "value": "1000000000000000000"
        }
        
        validated = validate_transaction_params(params)
        assert validated["from"] == params["from"]
        assert validated["value"] == int(params["value"])
        
        with pytest.raises(ValueError, match="Transaction validation failed"):
            validate_transaction_params({"from": "invalid"})
    
    def test_validate_value_bounds(self):
        """Test value bounds validation."""
        assert validate_value_bounds(1000, 0, 10000) == 1000
        assert validate_value_bounds("0x3e8", 0, 10000) == 1000
        
        with pytest.raises(ValueError, match="cannot be less than"):
            validate_value_bounds(-1, 0, 100)
        
        with pytest.raises(ValueError, match="cannot exceed"):
            validate_value_bounds(101, 0, 100)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])