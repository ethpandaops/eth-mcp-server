from typing import Dict, List, Optional
from eth_account import Account
from web3 import Web3
from eth_typing import Address
from eth_utils import to_checksum_address

class WalletManager:
    def __init__(self, w3: Web3):
        self.w3 = w3
        self.wallets: Dict[str, str] = {}  # address -> private_key mapping

    def create_wallet(self) -> Dict[str, str]:
        """Create a new wallet and return address and private key."""
        account = Account.create()
        address = to_checksum_address(account.address)
        self.wallets[address] = account.key.hex()
        return {
            "address": address,
            "privateKey": account.key.hex()
        }

    def import_wallet(self, private_key: str) -> Dict[str, str]:
        """Import a wallet from private key."""
        if not private_key.startswith('0x'):
            private_key = '0x' + private_key
        account = Account.from_key(private_key)
        address = to_checksum_address(account.address)
        self.wallets[address] = private_key
        return {
            "address": address,
            "privateKey": private_key
        }

    def list_wallets(self) -> List[str]:
        """List all managed wallet addresses."""
        return list(self.wallets.keys())

    def get_balance(self, address: str) -> int:
        """Get ETH balance for an address."""
        address = to_checksum_address(address)
        return self.w3.eth.get_balance(address)

    def get_transaction_count(self, address: str) -> int:
        """Get transaction count (nonce) for an address."""
        address = to_checksum_address(address)
        return self.w3.eth.get_transaction_count(address)

    def sign_transaction(self, address: str, transaction: Dict) -> Dict:
        """Sign a transaction with the wallet's private key."""
        if address not in self.wallets:
            raise ValueError(f"Wallet {address} not found")
        
        # Ensure transaction has required fields
        if 'nonce' not in transaction:
            transaction['nonce'] = self.get_transaction_count(address)
        if 'gasPrice' not in transaction:
            transaction['gasPrice'] = self.w3.eth.gas_price
        if 'gas' not in transaction:
            transaction['gas'] = self.w3.eth.estimate_gas(transaction)
            
        signed_tx = self.w3.eth.account.sign_transaction(
            transaction,
            self.wallets[address]
        )
        return {
            "rawTransaction": signed_tx.rawTransaction.hex(),
            "hash": signed_tx.hash.hex(),
            "r": hex(signed_tx.r),
            "s": hex(signed_tx.s),
            "v": hex(signed_tx.v)
        }

    def verify_wallet(self, address: str) -> bool:
        """Verify if a wallet is managed by this manager."""
        return address in self.wallets 