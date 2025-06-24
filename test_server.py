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

def test_deploy_contract(address, private_key):
    # Simple storage contract bytecode
    contract_bytecode = "0x608060405234801561001057600080fd5b506040516101e83803806101e88339818101604052602081101561003357600080fd5b810190808051906020019092919050505080600081905550506101928061005b6000396000f3fe608060405234801561001057600080fd5b50600436106100365760003560e01c806360fe47b11461003b5780636d4ce63c14610069575b600080fd5b6100676004803603602081101561005157600080fd5b8101908080359060200190929190505050610087565b005b610071610091565b6040518082815260200191505060405180910390f35b8060008190555050565b6000805490509056fea2646970667358221220d6c860c2875c9f0e0d0c2c4c5c5c5c5c5c5c5c5c5c5c5c5c5c5c5c5c5c5c5c64736f6c634300060c0033"
    
    response = requests.post(
        BASE_URL,
        json={
            "method": "eth_deployContract",
            "params": {
                "from": address,
                "privateKey": private_key,
                "bytecode": contract_bytecode,
                "gas": 2000000
            }
        }
    )
    print("Deploy Contract Response:", response.json())
    return response.json()["result"]["contractAddress"]

def test_call_contract_method(contract_address, address, private_key, method_name, params=None):
    if params is None:
        params = []
        
    response = requests.post(
        BASE_URL,
        json={
            "method": "eth_callContractMethod",
            "params": {
                "contractAddress": contract_address,
                "from": address,
                "privateKey": private_key,
                "methodName": method_name,
                "params": params,
                "gas": 2000000
            }
        }
    )
    print(f"Call {method_name} Response:", response.json())
    return response.json()["result"]

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
    
    # Test contract deployment and method calls
    print("\nTesting contract deployment and method calls:")
    contract_address = test_deploy_contract(address, private_key)
    print(f"Deployed contract at: {contract_address}")
    
    # Test setting a value
    test_call_contract_method(contract_address, address, private_key, "set", [42])
    
    # Test getting the value
    result = test_call_contract_method(contract_address, address, private_key, "get")
    print(f"Contract value: {result}")
    
    # Test transaction monitoring
    try:
        print(f"\nStarting transaction monitoring for {address}")
        await test_transaction_monitoring(address)
    except KeyboardInterrupt:
        print("\nStopping monitoring...")

if __name__ == "__main__":
    asyncio.run(main()) 