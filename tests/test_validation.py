"""Comprehensive tests for validation functions in src/utils/validation.py."""
import pytest
from typing import Any, Dict, List
from src.utils.validation import (
    validate_address,
    validate_private_key,
    validate_transaction_params,
    validate_gas_params,
    validate_block_number,
    validate_hex_string,
    validate_wei_amount,
    sanitize_input,
    validate_abi,
    validate_constructor_args,
    validate_method_args,
    is_valid_bytecode,
    validate_event_filters
)


class TestValidateAddress:
    """Test cases for validate_address function."""
    
    @pytest.mark.parametrize("address", [
        "0x742d35Cc6634C0532925a3b844Bc9e7595f2bd5e",  # Mixed case
        "0x742d35cc6634c0532925a3b844bc9e7595f2bd5e",  # All lowercase
        "0x742D35CC6634C0532925A3B844BC9E7595F2BD5E",  # All uppercase
        "0x0000000000000000000000000000000000000000",  # Zero address
        "0xffffffffffffffffffffffffffffffffffffffff",  # Max address
    ])
    def test_valid_addresses(self, address):
        """Test valid Ethereum addresses."""
        validate_address(address)  # Should not raise
    
    @pytest.mark.parametrize("address,error_msg", [
        (123, "Address must be a string"),
        ("", "Address must start with '0x'"),
        ("742d35Cc6634C0532925a3b844Bc9e7595f2bd5e", "Address must start with '0x'"),
        ("0x", "Address must be 42 characters long"),
        ("0x742d35Cc6634C0532925a3b844Bc9e7595f2bd5", "Address must be 42 characters long"),
        ("0x742d35Cc6634C0532925a3b844Bc9e7595f2bd5ee", "Address must be 42 characters long"),
        ("0xGGGG35Cc6634C0532925a3b844Bc9e7595f2bd5e", "invalid hexadecimal"),
        ("0x742d35Cc6634C0532925a3b844Bc9e7595f2bd5G", "invalid hexadecimal"),
    ])
    def test_invalid_addresses(self, address, error_msg):
        """Test invalid Ethereum addresses."""
        with pytest.raises(ValueError, match=error_msg):
            validate_address(address)
    
    def test_checksum_validation(self):
        """Test EIP-55 checksum validation for mixed case addresses."""
        # This would require web3 to be installed for proper checksum validation
        # Invalid checksum (incorrect case)
        invalid_checksum = "0x742d35Cc6634C0532925a3b844Bc9e7595f2bd5E"  # Last char should be lowercase
        # Without web3, this might not raise, but with web3 it should
        try:
            from web3 import Web3
            with pytest.raises(ValueError, match="invalid EIP-55 checksum"):
                validate_address(invalid_checksum)
        except ImportError:
            # If web3 not available, just validate it passes without checksum check
            validate_address(invalid_checksum)


class TestValidatePrivateKey:
    """Test cases for validate_private_key function."""
    
    @pytest.mark.parametrize("private_key", [
        "0x" + "a" * 64,  # Valid with 0x prefix
        "a" * 64,  # Valid without prefix
        "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",  # Valid hex
        "0x0000000000000000000000000000000000000000000000000000000000000001",  # Minimum valid
        "0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364140",  # Maximum valid
    ])
    def test_valid_private_keys(self, private_key):
        """Test valid private keys."""
        validate_private_key(private_key)  # Should not raise
    
    @pytest.mark.parametrize("private_key,error_msg", [
        (123, "Private key must be a string"),
        ("", "Private key must be 64 hex characters"),
        ("0x", "Private key must be 64 hex characters"),
        ("0x123", "Private key must be 64 hex characters"),
        ("0x" + "a" * 63, "Private key must be 64 hex characters"),
        ("0x" + "a" * 65, "Private key must be 64 hex characters"),
        ("0x" + "g" * 64, "invalid hexadecimal"),
        ("0x" + "0" * 64, "Private key cannot be zero"),
        ("0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141", "outside the valid range"),
        ("0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF", "outside the valid range"),
    ])
    def test_invalid_private_keys(self, private_key, error_msg):
        """Test invalid private keys."""
        with pytest.raises(ValueError, match=error_msg):
            validate_private_key(private_key)


class TestValidateTransactionParams:
    """Test cases for validate_transaction_params function."""
    
    def test_valid_complete_params(self):
        """Test valid transaction with all parameters."""
        params = {
            'from': '0x742d35Cc6634C0532925a3b844Bc9e7595f2bd5e',
            'to': '0x742d35Cc6634C0532925a3b844Bc9e7595f2bd5e',
            'value': '1000000000000000000',
            'gas': 21000,
            'gasPrice': '20000000000',
            'nonce': 5,
            'data': '0x1234',
            'chainId': 1
        }
        validate_transaction_params(params)  # Should not raise
    
    def test_valid_minimal_params(self):
        """Test valid transaction with minimal parameters."""
        params = {
            'from': '0x742d35Cc6634C0532925a3b844Bc9e7595f2bd5e',
            'to': '0x742d35Cc6634C0532925a3b844Bc9e7595f2bd5e'
        }
        validate_transaction_params(params)  # Should not raise
    
    def test_contract_creation(self):
        """Test valid contract creation transaction (to is None)."""
        params = {
            'from': '0x742d35Cc6634C0532925a3b844Bc9e7595f2bd5e',
            'to': None,
            'data': '0x608060405234801561001057600080fd5b50'
        }
        validate_transaction_params(params)  # Should not raise
    
    def test_eip1559_params(self):
        """Test EIP-1559 transaction parameters."""
        params = {
            'from': '0x742d35Cc6634C0532925a3b844Bc9e7595f2bd5e',
            'to': '0x742d35Cc6634C0532925a3b844Bc9e7595f2bd5e',
            'maxFeePerGas': '100000000000',
            'maxPriorityFeePerGas': '2000000000'
        }
        validate_transaction_params(params)  # Should not raise
    
    @pytest.mark.parametrize("params,error_msg", [
        ("not a dict", "must be a dictionary"),
        ({'from': 'invalid'}, "Address must start with '0x'"),
        ({'to': 'invalid'}, "Address must start with '0x'"),
        ({'value': -1}, "Wei amount must be non-negative"),
        ({'gas': 20999}, "Gas limit must be at least 21000"),
        ({'nonce': -1}, "Nonce must be non-negative"),
        ({'nonce': 'invalid'}, "must be a valid integer"),
        ({'chainId': -1}, "Chain ID must be non-negative"),
        ({'data': 'invalid'}, "Hex string must start with '0x'"),
    ])
    def test_invalid_params(self, params, error_msg):
        """Test invalid transaction parameters."""
        with pytest.raises(ValueError, match=error_msg):
            validate_transaction_params(params)


class TestValidateGasParams:
    """Test cases for validate_gas_params function."""
    
    @pytest.mark.parametrize("gas_limit,gas_price", [
        (21000, None),  # Minimum valid gas
        (100000, None),  # Common gas limit
        (30000000, None),  # Maximum block gas limit
        ("0x5208", None),  # 21000 in hex
        ("100000", None),  # String decimal
        (21000, 1000000000),  # With gas price (1 Gwei)
        (21000, "0x3b9aca00"),  # With hex gas price
        (21000, "20000000000"),  # String gas price
    ])
    def test_valid_gas_params(self, gas_limit, gas_price):
        """Test valid gas parameters."""
        validate_gas_params(gas_limit, gas_price)  # Should not raise
    
    @pytest.mark.parametrize("gas_limit,gas_price,error_msg", [
        ("not a number", None, "must be a valid integer"),
        (20999, None, "Gas limit must be at least 21000"),
        (30000001, None, "exceeds typical block gas limit"),
        (-1, None, "Gas limit must be at least 21000"),
        (21000, -1, "Gas price must be non-negative"),
        (21000, "invalid", "must be a valid integer"),
    ])
    def test_invalid_gas_params(self, gas_limit, gas_price, error_msg):
        """Test invalid gas parameters."""
        with pytest.raises(ValueError, match=error_msg):
            validate_gas_params(gas_limit, gas_price)
    
    def test_high_gas_price_warning(self):
        """Test that very high gas price doesn't raise but could warn."""
        # Over 1000 Gwei
        validate_gas_params(21000, 1000000000001)  # Should not raise


class TestValidateBlockNumber:
    """Test cases for validate_block_number function."""
    
    @pytest.mark.parametrize("block_number", [
        12345,  # Integer
        0,  # Genesis block
        "0x3039",  # Hex string
        "12345",  # Decimal string
        "latest",  # Special tag
        "pending",  # Special tag
        "earliest",  # Special tag
        "safe",  # Special tag
        "finalized",  # Special tag
    ])
    def test_valid_block_numbers(self, block_number):
        """Test valid block numbers."""
        validate_block_number(block_number)  # Should not raise
    
    @pytest.mark.parametrize("block_number,error_msg", [
        (-1, "Block number must be non-negative"),
        ("-1", "Invalid block number format"),
        ("0x-1", "Invalid hexadecimal block number"),
        ("invalid", "Invalid block number format"),
        ("0xGGGG", "Invalid hexadecimal block number"),
        ([], "Block number must be an integer or string"),
        ({}, "Block number must be an integer or string"),
    ])
    def test_invalid_block_numbers(self, block_number, error_msg):
        """Test invalid block numbers."""
        with pytest.raises(ValueError, match=error_msg):
            validate_block_number(block_number)


class TestValidateHexString:
    """Test cases for validate_hex_string function."""
    
    @pytest.mark.parametrize("hex_str,expected_length", [
        ("0x", None),  # Empty is valid
        ("0x00", None),  # Single byte
        ("0x1234", None),  # Two bytes
        ("0x1234", 2),  # Exact length match
        ("0xabcdef", 3),  # Three bytes
        ("0x" + "00" * 32, 32),  # 32 bytes
    ])
    def test_valid_hex_strings(self, hex_str, expected_length):
        """Test valid hex strings."""
        validate_hex_string(hex_str, expected_length)  # Should not raise
    
    @pytest.mark.parametrize("hex_str,expected_length,error_msg", [
        (123, None, "Hex string must be a string"),
        ("", None, "Hex string must start with '0x'"),
        ("1234", None, "Hex string must start with '0x'"),
        ("0x123", None, "must have even length"),  # Odd length
        ("0xGG", None, "invalid hexadecimal"),
        ("0x1234", 3, "Expected 3 bytes, got 2"),
        ("0x", 1, "Expected 1 bytes, got 0"),
    ])
    def test_invalid_hex_strings(self, hex_str, expected_length, error_msg):
        """Test invalid hex strings."""
        with pytest.raises(ValueError, match=error_msg):
            validate_hex_string(hex_str, expected_length)


class TestValidateWeiAmount:
    """Test cases for validate_wei_amount function."""
    
    @pytest.mark.parametrize("amount", [
        0,  # Zero
        1,  # 1 Wei
        1000000000000000000,  # 1 ETH
        "0xde0b6b3a7640000",  # 1 ETH in hex
        "1000000000000000000",  # String decimal
        10**18 * 100_000_000,  # 100M ETH
    ])
    def test_valid_amounts(self, amount):
        """Test valid Wei amounts."""
        validate_wei_amount(amount)  # Should not raise
    
    @pytest.mark.parametrize("amount,error_msg", [
        (-1, "Wei amount must be non-negative"),
        ("-1000000000000000000", "Wei amount must be non-negative"),
        ("0x-1", "must be a valid integer"),
        ("invalid", "must be a valid integer"),
        ([], "Wei amount must be an integer or string"),
    ])
    def test_invalid_amounts(self, amount, error_msg):
        """Test invalid Wei amounts."""
        with pytest.raises(ValueError, match=error_msg):
            validate_wei_amount(amount)
    
    def test_very_large_amount(self):
        """Test that very large amounts don't raise errors."""
        # More than total ETH supply
        validate_wei_amount(300_000_000 * 10**18)  # Should not raise


class TestSanitizeInput:
    """Test cases for sanitize_input function."""
    
    @pytest.mark.parametrize("input_str,expected", [
        ("Hello World!", "Hello World!"),
        ("Hello\nWorld", "Hello\nWorld"),  # Newlines are kept
        ("Hello\x00World", "HelloWorld"),  # Null bytes removed
        ("<script>alert('xss')</script>", "alert('xss')"),  # HTML tags removed
        ("SELECT * FROM users -- comment", "SELECT * FROM users"),  # SQL comments removed
        ("data; rm -rf /", "data rm -rf /"),  # Shell injection chars removed
        ("test`echo hack`", "testecho hack"),  # Backticks removed
        ("$PATH | cat", "PATH  cat"),  # Shell chars removed
        ("  spaces  ", "spaces"),  # Whitespace trimmed
        ("a" * 15000, "a" * 10000),  # Length limited
    ])
    def test_sanitization(self, input_str, expected):
        """Test input sanitization."""
        assert sanitize_input(input_str) == expected
    
    def test_sql_injection_patterns(self):
        """Test SQL injection pattern removal."""
        sql_injections = [
            "'; DROP TABLE users; --",
            "1' OR '1'='1",
            "/* comment */ SELECT * FROM users",
        ]
        for injection in sql_injections:
            result = sanitize_input(injection)
            assert "--" not in result
            assert "/*" not in result
            assert "*/" not in result
    
    def test_invalid_input_type(self):
        """Test non-string input."""
        with pytest.raises(ValueError, match="Input must be a string"):
            sanitize_input(123)


class TestValidateABI:
    """Test cases for validate_abi function."""
    
    def test_valid_function_abi(self):
        """Test valid function ABI."""
        abi = [
            {
                "type": "function",
                "name": "transfer",
                "inputs": [
                    {"type": "address", "name": "to"},
                    {"type": "uint256", "name": "amount"}
                ],
                "outputs": [{"type": "bool"}]
            }
        ]
        validate_abi(abi)  # Should not raise
    
    def test_valid_event_abi(self):
        """Test valid event ABI."""
        abi = [
            {
                "type": "event",
                "name": "Transfer",
                "inputs": [
                    {"type": "address", "name": "from", "indexed": True},
                    {"type": "address", "name": "to", "indexed": True},
                    {"type": "uint256", "name": "value"}
                ]
            }
        ]
        validate_abi(abi)  # Should not raise
    
    def test_valid_constructor_abi(self):
        """Test valid constructor ABI."""
        abi = [
            {
                "type": "constructor",
                "inputs": [
                    {"type": "uint256", "name": "initialSupply"}
                ]
            }
        ]
        validate_abi(abi)  # Should not raise
    
    def test_valid_fallback_receive(self):
        """Test valid fallback and receive functions."""
        abi = [
            {"type": "fallback"},
            {"type": "receive"}
        ]
        validate_abi(abi)  # Should not raise
    
    @pytest.mark.parametrize("abi,error_msg", [
        ("not a list", "ABI must be a list"),
        ([], "ABI cannot be empty"),
        ([123], "must be a dictionary"),
        ([{"type": "function"}], "Function at index 0 must have a name"),
        ([{"type": "event"}], "Event at index 0 must have a name"),
        ([{"type": "function", "name": "test", "inputs": "not a list"}], "must be a list"),
        ([{"type": "function", "name": "test", "inputs": [123]}], "must be a dictionary"),
        ([{"type": "function", "name": "test", "inputs": [{"name": "x"}]}], "must have a type"),
        ([{"type": "function", "name": "test", "outputs": "not a list"}], "must be a list"),
        ([{"type": "event", "name": "Test", "inputs": [{"name": "x"}]}], "must have a type"),
    ])
    def test_invalid_abi(self, abi, error_msg):
        """Test invalid ABI structures."""
        with pytest.raises(ValueError, match=error_msg):
            validate_abi(abi)


class TestValidateConstructorArgs:
    """Test cases for validate_constructor_args function."""
    
    def test_no_constructor_no_args(self):
        """Test ABI without constructor and no args."""
        abi = [{"type": "function", "name": "test"}]
        validate_constructor_args(abi, None)  # Should not raise
        validate_constructor_args(abi, [])  # Should not raise
    
    def test_no_constructor_with_args(self):
        """Test ABI without constructor but args provided."""
        abi = [{"type": "function", "name": "test"}]
        with pytest.raises(ValueError, match="No constructor found in ABI"):
            validate_constructor_args(abi, ["arg"])
    
    def test_constructor_matching_args(self):
        """Test constructor with matching arguments."""
        abi = [{
            "type": "constructor",
            "inputs": [
                {"type": "uint256", "name": "supply"},
                {"type": "address", "name": "owner"},
                {"type": "bool", "name": "mintable"},
                {"type": "string", "name": "name"},
                {"type": "bytes32", "name": "hash"},
                {"type": "address[]", "name": "addresses"}
            ]
        }]
        args = [
            1000000,
            "0x742d35Cc6634C0532925a3b844Bc9e7595f2bd5e",
            True,
            "MyToken",
            "0x1234567890123456789012345678901234567890123456789012345678901234",
            ["0x742d35Cc6634C0532925a3b844Bc9e7595f2bd5e", "0x742d35Cc6634C0532925a3b844Bc9e7595f2bd5e"]
        ]
        validate_constructor_args(abi, args)  # Should not raise
    
    def test_constructor_wrong_arg_count(self):
        """Test constructor with wrong number of arguments."""
        abi = [{
            "type": "constructor",
            "inputs": [
                {"type": "uint256", "name": "supply"},
                {"type": "address", "name": "owner"}
            ]
        }]
        with pytest.raises(ValueError, match="expects 2 arguments, but 1 were provided"):
            validate_constructor_args(abi, [1000000])
    
    @pytest.mark.parametrize("arg_type,arg_value,error_msg", [
        ("uint256", [], "must be an integer or string"),
        ("int256", {}, "must be an integer or string"),
        ("address", 123, "must be a string address"),
        ("address", "0x123", "must be a valid address"),
        ("address", "not an address", "must be a valid address"),
        ("bool", "true", "must be a boolean"),
        ("string", 123, "must be a string"),
        ("bytes32", 123, "must be a string or bytes"),
        ("bytes", "no-prefix", "must start with 0x"),
        ("address[]", "not a list", "must be a list"),
    ])
    def test_constructor_invalid_arg_types(self, arg_type, arg_value, error_msg):
        """Test constructor with invalid argument types."""
        abi = [{
            "type": "constructor",
            "inputs": [{"type": arg_type, "name": "param"}]
        }]
        with pytest.raises(ValueError, match=error_msg):
            validate_constructor_args(abi, [arg_value])


class TestValidateMethodArgs:
    """Test cases for validate_method_args function."""
    
    def test_method_not_found(self):
        """Test calling non-existent method."""
        abi = [{"type": "function", "name": "transfer"}]
        with pytest.raises(ValueError, match="Method 'approve' not found in ABI"):
            validate_method_args(abi, "approve", [])
    
    def test_method_matching_args(self):
        """Test method with matching arguments."""
        abi = [{
            "type": "function",
            "name": "transfer",
            "inputs": [
                {"type": "address", "name": "to"},
                {"type": "uint256", "name": "amount"}
            ]
        }]
        args = ["0x742d35Cc6634C0532925a3b844Bc9e7595f2bd5e", 1000000]
        validate_method_args(abi, "transfer", args)  # Should not raise
    
    def test_method_no_args(self):
        """Test method with no arguments."""
        abi = [{
            "type": "function",
            "name": "totalSupply",
            "inputs": []
        }]
        validate_method_args(abi, "totalSupply", None)  # Should not raise
        validate_method_args(abi, "totalSupply", [])  # Should not raise
    
    def test_method_wrong_arg_count(self):
        """Test method with wrong number of arguments."""
        abi = [{
            "type": "function",
            "name": "transfer",
            "inputs": [
                {"type": "address", "name": "to"},
                {"type": "uint256", "name": "amount"}
            ]
        }]
        with pytest.raises(ValueError, match="expects 2 arguments, but 1 were provided"):
            validate_method_args(abi, "transfer", ["0x742d35Cc6634C0532925a3b844Bc9e7595f2bd5e"])
    
    def test_method_invalid_arg_types(self):
        """Test method with invalid argument types."""
        abi = [{
            "type": "function",
            "name": "transfer",
            "inputs": [
                {"type": "address", "name": "to"},
                {"type": "uint256", "name": "amount"}
            ]
        }]
        with pytest.raises(ValueError, match="must be a string address"):
            validate_method_args(abi, "transfer", [123, 1000])


class TestIsValidBytecode:
    """Test cases for is_valid_bytecode function."""
    
    @pytest.mark.parametrize("bytecode", [
        "0x00",  # Single zero byte
        "0x608060405234801561001057600080fd5b50",  # Contract deployment bytecode
        "0x" + "00" * 100,  # Long bytecode
        "0xabcdef1234567890",  # Mixed hex
    ])
    def test_valid_bytecode(self, bytecode):
        """Test valid bytecode."""
        assert is_valid_bytecode(bytecode) is True
    
    @pytest.mark.parametrize("bytecode", [
        123,  # Not a string
        "",  # No 0x prefix
        "608060405234801561001057600080fd5b50",  # No 0x prefix
        "0x",  # Empty bytecode
        "0x1",  # Odd length
        "0x123",  # Odd length
        "0xGGGG",  # Invalid hex
        "0x12GG",  # Invalid hex
    ])
    def test_invalid_bytecode(self, bytecode):
        """Test invalid bytecode."""
        assert is_valid_bytecode(bytecode) is False


class TestValidateEventFilters:
    """Test cases for validate_event_filters function."""
    
    def test_event_not_found(self):
        """Test filtering non-existent event."""
        abi = [{"type": "event", "name": "Transfer"}]
        with pytest.raises(ValueError, match="Event 'Approval' not found in ABI"):
            validate_event_filters(abi, "Approval", {})
    
    def test_no_filters(self):
        """Test event with no filters."""
        abi = [{
            "type": "event",
            "name": "Transfer",
            "inputs": [
                {"type": "address", "name": "from", "indexed": True},
                {"type": "address", "name": "to", "indexed": True},
                {"type": "uint256", "name": "value"}
            ]
        }]
        validate_event_filters(abi, "Transfer", None)  # Should not raise
        validate_event_filters(abi, "Transfer", {})  # Should not raise
    
    def test_valid_indexed_filters(self):
        """Test valid filters on indexed parameters."""
        abi = [{
            "type": "event",
            "name": "Transfer",
            "inputs": [
                {"type": "address", "name": "from", "indexed": True},
                {"type": "address", "name": "to", "indexed": True},
                {"type": "uint256", "name": "value"}
            ]
        }]
        filters = {
            "from": "0x742d35Cc6634C0532925a3b844Bc9e7595f2bd5e",
            "to": ["0x742d35Cc6634C0532925a3b844Bc9e7595f2bd5e", None]  # List with None
        }
        validate_event_filters(abi, "Transfer", filters)  # Should not raise
    
    def test_non_indexed_filter(self):
        """Test filtering on non-indexed parameter."""
        abi = [{
            "type": "event",
            "name": "Transfer",
            "inputs": [
                {"type": "address", "name": "from", "indexed": True},
                {"type": "address", "name": "to", "indexed": True},
                {"type": "uint256", "name": "value"}  # Not indexed
            ]
        }]
        with pytest.raises(ValueError, match="is not an indexed parameter"):
            validate_event_filters(abi, "Transfer", {"value": 1000})
    
    def test_special_filter_keys(self):
        """Test special filter keys that aren't parameters."""
        abi = [{
            "type": "event",
            "name": "Transfer",
            "inputs": []
        }]
        filters = {
            "fromBlock": 12345,
            "toBlock": "latest",
            "address": "0x742d35Cc6634C0532925a3b844Bc9e7595f2bd5e",
            "topics": ["0x123"]
        }
        validate_event_filters(abi, "Transfer", filters)  # Should not raise
    
    def test_invalid_filter_values(self):
        """Test invalid filter values."""
        abi = [{
            "type": "event",
            "name": "Transfer",
            "inputs": [
                {"type": "address", "name": "from", "indexed": True},
                {"type": "uint256", "name": "amount", "indexed": True}
            ]
        }]
        
        # Invalid address filter
        with pytest.raises(ValueError, match="must be a string address or list"):
            validate_event_filters(abi, "Transfer", {"from": 123})
        
        # Invalid address in list
        with pytest.raises(ValueError, match="must be valid addresses or None"):
            validate_event_filters(abi, "Transfer", {"from": ["invalid-address"]})
        
        # Invalid uint filter
        with pytest.raises(ValueError, match="must be an integer, string, or list"):
            validate_event_filters(abi, "Transfer", {"amount": {}})


# Security-focused edge case tests
class TestSecurityEdgeCases:
    """Security-focused tests for validation functions."""
    
    def test_address_validation_security(self):
        """Test address validation against various attack vectors."""
        # Test unicode/special characters
        with pytest.raises(ValueError):
            validate_address("0x" + "é" * 40)
        
        # Test very long input
        with pytest.raises(ValueError):
            validate_address("0x" + "a" * 1000)
    
    def test_sanitize_input_security(self):
        """Test input sanitization against various injection attacks."""
        # Test various injection patterns
        injections = [
            "'; exec(chr(99)+chr(97)+chr(116)+chr(32)+chr(47)+chr(101)+chr(116)+chr(99)+chr(47)+chr(112)+chr(97)+chr(115)+chr(115)+chr(119)+chr(100))",
            "command;rm -rf /",
            "\\x00\\x00\\x00",
            "data$PATH",
            "test`whoami`",
        ]
        
        for injection in injections:
            result = sanitize_input(injection)
            # Ensure dangerous shell characters are removed
            assert ";" not in result
            assert "$" not in result
            assert "`" not in result
            assert "\x00" not in result
            assert "\\" not in result
    
    def test_hex_string_validation_security(self):
        """Test hex string validation against malformed inputs."""
        # Test very long hex string - should still be valid if well-formed
        result = validate_hex_string("0x" + "ff" * 5000, 5000)  # Should not raise
        
        # Test length mismatch
        with pytest.raises(ValueError, match="Expected 5000 bytes, got 2"):
            validate_hex_string("0x1234", 5000)
    
    def test_transaction_params_security(self):
        """Test transaction parameter validation for security issues."""
        # Test prototype pollution attempt
        params = {
            "__proto__": {"isAdmin": True},
            "from": "0x742d35Cc6634C0532925a3b844Bc9e7595f2bd5e",
            "to": "0x742d35Cc6634C0532925a3b844Bc9e7595f2bd5e"
        }
        # Should validate without accessing __proto__
        validate_transaction_params(params)
        
        # Test recursive data structures
        recursive_params = {"from": "0x742d35Cc6634C0532925a3b844Bc9e7595f2bd5e"}
        recursive_params["data"] = recursive_params  # Circular reference
        with pytest.raises(ValueError):
            validate_transaction_params(recursive_params)