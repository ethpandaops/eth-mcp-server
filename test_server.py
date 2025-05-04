import requests
import json
import asyncio
import websockets
import sys

BASE_URL = "http://localhost:8000/mcp"
WS_URL = "ws://localhost:8000/ws/transactions/{}"

def test_create_wallet():
    response = requests.post(
        BASE_URL,
        json={
            "method": "eth_createWallet",
            "params": {}
        }
    )
    print("Create Wallet Response:", response.json())
    return response.json()["result"]["address"]

def test_import_wallet(private_key: str):
    response = requests.post(
        BASE_URL,
        json={
            "method": "eth_importWallet",
            "params": {
                "privateKey": private_key
            }
        }
    )
    print("Import Wallet Response:", response.json())
    return response.json()["result"]["address"]

def test_list_wallets():
    response = requests.post(
        BASE_URL,
        json={
            "method": "eth_listWallets",
            "params": {}
        }
    )
    print("List Wallets Response:", response.json())
    return response.json()["result"]["addresses"]

def test_get_balance(address):
    response = requests.post(
        BASE_URL,
        json={
            "method": "eth_getBalance",
            "params": {
                "address": address
            }
        }
    )
    print("Get Balance Response:", response.json())
    return int(response.json()["result"]["balance"])

def test_get_nonce(address):
    response = requests.post(
        BASE_URL,
        json={
            "method": "eth_getTransactionCount",
            "params": {
                "address": address
            }
        }
    )
    print("Get Nonce Response:", response.json())
    return int(response.json()["result"]["count"])

def test_get_gas_price():
    response = requests.post(
        BASE_URL,
        json={
            "method": "eth_getGasPriceEstimate",
            "params": {}
        }
    )
    print("Gas Price Response:", response.json())
    return response.json()["result"]

async def test_transaction_monitoring(address):
    async with websockets.connect(WS_URL.format(address)) as websocket:
        print(f"Monitoring transactions for {address}")
        while True:
            try:
                message = await websocket.recv()
                print("New Transaction:", json.loads(message))
            except websockets.exceptions.ConnectionClosed:
                break

def test_get_all_wallet_balances():
    """Get balances for all managed wallets"""
    wallets = test_list_wallets()
    balances = {}
    
    for address in wallets:
        balance = test_get_balance(address)
        balances[address] = balance
        print(f"Wallet {address}: {balance} wei")
    
    return balances

async def main():
    # Test wallet creation
    address = test_create_wallet()
    
    # Test importing the same wallet
    private_key = "0x4312ca863dc5c824f1355814f1560ab9b5fddbd656c559654865f1629936e02f"  # Example private key
    imported_address = test_import_wallet(private_key)
    
    # Test listing wallets
    wallets = test_list_wallets()
    print(f"Managed wallets: {wallets}")
    
    # Test balances for all wallets
    print("\nChecking balances for all wallets:")
    balances = test_get_all_wallet_balances()
    
    # Test nonce for first wallet
    nonce = test_get_nonce(address)
    print(f"\nNonce for {address}: {nonce}")
    
    # Test gas price
    print("\nGas price estimates:")
    gas_prices = test_get_gas_price()
    
    # Test transaction monitoring
    try:
        print(f"\nStarting transaction monitoring for {address}")
        await test_transaction_monitoring(address)
    except KeyboardInterrupt:
        print("\nStopping monitoring...")

if __name__ == "__main__":
    asyncio.run(main()) 