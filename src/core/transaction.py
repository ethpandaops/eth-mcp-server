from typing import Dict, List, Optional, Union
from web3 import Web3
from eth_typing import Address, BlockNumber
from eth_utils import to_checksum_address
from .wallet import WalletManager
import asyncio
from datetime import datetime

class TransactionManager:
    def __init__(self, w3: Web3, wallet_manager: WalletManager):
        self.w3 = w3
        self.wallet_manager = wallet_manager
        self.transaction_history: Dict[str, List[Dict]] = {}  # address -> list of transactions
        self.monitoring_tasks: Dict[str, asyncio.Task] = {}  # address -> monitoring task

    def send_transaction(self, tx_params: Dict) -> str:
        """Send a transaction and return the transaction hash."""
        if 'from' not in tx_params:
            raise ValueError("Sender address required")
        
        from_address = to_checksum_address(tx_params['from'])
        if not self.wallet_manager.verify_wallet(from_address):
            raise ValueError(f"Wallet {from_address} not found")

        # Sign and send transaction
        signed_tx = self.wallet_manager.sign_transaction(from_address, tx_params)
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx['rawTransaction'])
        return tx_hash.hex()

    def get_transaction(self, tx_hash: str) -> Dict:
        """Get transaction details by hash."""
        tx = self.w3.eth.get_transaction(tx_hash)
        return {
            "hash": tx['hash'].hex(),
            "nonce": tx['nonce'],
            "blockHash": tx['blockHash'].hex() if tx['blockHash'] else None,
            "blockNumber": tx['blockNumber'],
            "transactionIndex": tx['transactionIndex'],
            "from": tx['from'],
            "to": tx['to'],
            "value": str(tx['value']),
            "gasPrice": str(tx['gasPrice']),
            "gas": tx['gas'],
            "input": tx['input'],
            "v": hex(tx['v']),
            "r": hex(tx['r']),
            "s": hex(tx['s'])
        }

    def get_transaction_receipt(self, tx_hash: str) -> Dict:
        """Get transaction receipt by hash."""
        receipt = self.w3.eth.get_transaction_receipt(tx_hash)
        return {
            "transactionHash": receipt['transactionHash'].hex(),
            "blockHash": receipt['blockHash'].hex(),
            "blockNumber": receipt['blockNumber'],
            "from": receipt['from'],
            "to": receipt['to'],
            "contractAddress": receipt['contractAddress'],
            "cumulativeGasUsed": receipt['cumulativeGasUsed'],
            "gasUsed": receipt['gasUsed'],
            "effectiveGasPrice": str(receipt['effectiveGasPrice']),
            "status": receipt['status'],
            "logs": [
                {
                    "address": log['address'],
                    "topics": [topic.hex() for topic in log['topics']],
                    "data": log['data'],
                    "blockNumber": log['blockNumber'],
                    "transactionHash": log['transactionHash'].hex(),
                    "logIndex": log['logIndex'],
                    "blockHash": log['blockHash'].hex()
                }
                for log in receipt['logs']
            ]
        }

    def get_transaction_count(self, address: str, block: Optional[Union[str, int]] = 'latest') -> int:
        """Get transaction count (nonce) for an address at a specific block."""
        return self.w3.eth.get_transaction_count(to_checksum_address(address), block)

    def estimate_gas(self, tx_params: Dict) -> int:
        """Estimate gas for a transaction."""
        return self.w3.eth.estimate_gas(tx_params)

    def get_gas_price(self) -> int:
        """Get current gas price."""
        return self.w3.eth.gas_price

    def get_transaction_history(self, address: str, start_block: Optional[int] = None, end_block: Optional[int] = None) -> List[Dict]:
        """Get transaction history for an address."""
        address = to_checksum_address(address)
        
        # Get current block if end_block not specified
        if end_block is None:
            end_block = self.w3.eth.block_number
            
        # Get genesis block if start_block not specified
        if start_block is None:
            start_block = 0
            
        # Get all transactions in range
        transactions = []
        for block_number in range(start_block, end_block + 1):
            block = self.w3.eth.get_block(block_number, full_transactions=True)
            for tx in block.transactions:
                if tx['from'].lower() == address.lower() or (tx['to'] and tx['to'].lower() == address.lower()):
                    transactions.append(self._format_transaction(tx))
                    
        # Sort by block number and transaction index
        transactions.sort(key=lambda x: (x['blockNumber'], x['transactionIndex']))
        return transactions

    def start_monitoring(self, address: str, callback) -> None:
        """Start monitoring transactions for an address."""
        address = to_checksum_address(address)
        if address in self.monitoring_tasks:
            return
            
        async def monitor():
            last_block = self.w3.eth.block_number
            while True:
                try:
                    current_block = self.w3.eth.block_number
                    if current_block > last_block:
                        for block_number in range(last_block + 1, current_block + 1):
                            block = self.w3.eth.get_block(block_number, full_transactions=True)
                            for tx in block.transactions:
                                if tx['from'].lower() == address.lower() or (tx['to'] and tx['to'].lower() == address.lower()):
                                    formatted_tx = self._format_transaction(tx)
                                    await callback(formatted_tx)
                        last_block = current_block
                    await asyncio.sleep(1)  # Poll every second
                except Exception as e:
                    print(f"Error monitoring transactions: {e}")
                    await asyncio.sleep(5)  # Wait longer on error
                    
        self.monitoring_tasks[address] = asyncio.create_task(monitor())

    def stop_monitoring(self, address: str) -> None:
        """Stop monitoring transactions for an address."""
        address = to_checksum_address(address)
        if address in self.monitoring_tasks:
            self.monitoring_tasks[address].cancel()
            del self.monitoring_tasks[address]

    def _format_transaction(self, tx: Dict) -> Dict:
        """Format a transaction for consistent output."""
        return {
            "hash": tx['hash'].hex(),
            "nonce": tx['nonce'],
            "blockHash": tx['blockHash'].hex() if tx['blockHash'] else None,
            "blockNumber": tx['blockNumber'],
            "transactionIndex": tx['transactionIndex'],
            "from": tx['from'],
            "to": tx['to'],
            "value": str(tx['value']),
            "gasPrice": str(tx['gasPrice']),
            "gas": tx['gas'],
            "input": tx['input'],
            "v": hex(tx['v']),
            "r": hex(tx['r']),
            "s": hex(tx['s']),
            "timestamp": datetime.fromtimestamp(
                self.w3.eth.get_block(tx['blockNumber'])['timestamp']
            ).isoformat() if tx['blockNumber'] else None
        }

    def get_gas_price_estimate(self) -> Dict[str, int]:
        """Get gas price estimates for different priorities."""
        base_fee = self.w3.eth.get_block('latest')['baseFeePerGas']
        max_priority_fee = self.w3.eth.max_priority_fee
        
        return {
            "slow": base_fee + max_priority_fee,  # 1 gwei priority
            "standard": base_fee + (max_priority_fee * 2),  # 2 gwei priority
            "fast": base_fee + (max_priority_fee * 3),  # 3 gwei priority
            "instant": base_fee + (max_priority_fee * 4)  # 4 gwei priority
        } 