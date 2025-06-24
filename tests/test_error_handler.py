"""Test script to demonstrate error handling functionality."""

import requests
import json
from typing import Dict, Any

# Test server URL
BASE_URL = "http://localhost:8000"


def make_request(method: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
    """Make a request to the MCP server."""
    payload = {
        "id": 1,
        "method": method,
        "params": params or {}
    }
    
    response = requests.post(f"{BASE_URL}/mcp", json=payload)
    return response.json()


def test_invalid_parameters():
    """Test invalid parameter errors."""
    print("\n=== Testing Invalid Parameters ===")
    
    # Missing required parameter
    result = make_request("eth_getBalance", {})
    print(f"Missing address parameter: {json.dumps(result, indent=2)}")
    
    # Invalid method
    result = make_request("invalid_method", {})
    print(f"Invalid method: {json.dumps(result, indent=2)}")


def test_invalid_address():
    """Test invalid address errors."""
    print("\n=== Testing Invalid Address ===")
    
    # Invalid address format
    result = make_request("eth_getBalance", {
        "address": "invalid_address"
    })
    print(f"Invalid address format: {json.dumps(result, indent=2)}")


def test_wallet_errors():
    """Test wallet-related errors."""
    print("\n=== Testing Wallet Errors ===")
    
    # Import invalid private key
    result = make_request("eth_importWallet", {
        "privateKey": "invalid_key"
    })
    print(f"Invalid private key: {json.dumps(result, indent=2)}")


def test_contract_errors():
    """Test contract-related errors."""
    print("\n=== Testing Contract Errors ===")
    
    # Missing required parameters
    result = make_request("contract_deploy", {
        "bytecode": "0x123"
        # Missing abi and from_address
    })
    print(f"Missing contract parameters: {json.dumps(result, indent=2)}")
    
    # Invalid ABI
    result = make_request("contract_load", {
        "address": "0x742d35Cc6634C0532925a3b844Bc9e7595f8B92E",
        "abi": "invalid_abi"
    })
    print(f"Invalid ABI: {json.dumps(result, indent=2)}")


def test_transaction_errors():
    """Test transaction-related errors."""
    print("\n=== Testing Transaction Errors ===")
    
    # Transaction history with invalid block numbers
    result = make_request("eth_getTransactionHistory", {
        "address": "0x742d35Cc6634C0532925a3b844Bc9e7595f8B92E",
        "startBlock": "invalid",
        "endBlock": "100"
    })
    print(f"Invalid block number: {json.dumps(result, indent=2)}")


def main():
    """Run all error handling tests."""
    print("Error Handling Test Suite")
    print("========================")
    
    try:
        test_invalid_parameters()
        test_invalid_address()
        test_wallet_errors()
        test_contract_errors()
        test_transaction_errors()
    except requests.ConnectionError:
        print("\nError: Could not connect to server at", BASE_URL)
        print("Make sure the server is running with: python src/server.py")


if __name__ == "__main__":
    main()