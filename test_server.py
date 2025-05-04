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

def test_get_gas_price():
    response = requests.post(
        BASE_URL,
        json={
            "method": "eth_getGasPriceEstimate",
            "params": {}
        }
    )
    print("Gas Price Response:", response.json())

async def test_transaction_monitoring(address):
    async with websockets.connect(WS_URL.format(address)) as websocket:
        print(f"Monitoring transactions for {address}")
        while True:
            try:
                message = await websocket.recv()
                print("New Transaction:", json.loads(message))
            except websockets.exceptions.ConnectionClosed:
                break

async def main():
    # Test wallet creation
    address = test_create_wallet()
    
    # Test balance check
    test_get_balance(address)
    
    # Test gas price
    test_get_gas_price()
    
    # Test transaction monitoring
    try:
        await test_transaction_monitoring(address)
    except KeyboardInterrupt:
        print("\nStopping monitoring...")

if __name__ == "__main__":
    asyncio.run(main()) 