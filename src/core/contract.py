from typing import Dict, List, Optional, Union, Any
from web3 import Web3
from web3.contract import Contract
from eth_typing import Address
from eth_utils import to_checksum_address
from eth_abi import encode, decode
import json
from .wallet import WalletManager

class ContractManager:
    def __init__(self, w3: Web3, wallet_manager: WalletManager):
        self.w3 = w3
        self.wallet_manager = wallet_manager
        self._contracts: Dict[str, Contract] = {}  # address -> contract instance

    def load_contract(self, address: str, abi: Union[str, List], name: Optional[str] = None) -> Contract:
        """Load a contract with its ABI and store the instance."""
        address = to_checksum_address(address)
        
        # Parse ABI if it's a string
        if isinstance(abi, str):
            try:
                abi = json.loads(abi)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid ABI JSON: {e}")
        
        # Create contract instance
        try:
            contract = self.w3.eth.contract(address=address, abi=abi)
            self._contracts[address] = contract
            
            # Store with custom name if provided
            if name:
                self._contracts[name] = contract
            
            return contract
        except Exception as e:
            raise ValueError(f"Failed to load contract: {e}")

    def deploy_contract(self, bytecode: str, abi: Union[str, List], 
                       constructor_args: Optional[List] = None,
                       from_address: str = None, 
                       gas_limit: int = 3000000) -> Dict[str, Any]:
        """Deploy a contract with ABI and constructor arguments."""
        if not from_address:
            raise ValueError("from_address is required for deployment")
            
        from_address = to_checksum_address(from_address)
        
        if not self.wallet_manager.verify_wallet(from_address):
            raise ValueError(f"Wallet {from_address} not found")
        
        # Parse ABI if it's a string
        if isinstance(abi, str):
            try:
                abi = json.loads(abi)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid ABI JSON: {e}")
        
        # Create contract factory
        try:
            contract_factory = self.w3.eth.contract(abi=abi, bytecode=bytecode)
        except Exception as e:
            raise ValueError(f"Failed to create contract factory: {e}")
        
        # Build constructor transaction
        if constructor_args is None:
            constructor_args = []
        
        try:
            # Get constructor transaction
            constructor_tx = contract_factory.constructor(*constructor_args).build_transaction({
                'from': from_address,
                'nonce': self.wallet_manager.get_transaction_count(from_address),
                'gas': gas_limit,
                'gasPrice': self.w3.eth.gas_price,
                'chainId': self.w3.eth.chain_id
            })
        except Exception as e:
            raise ValueError(f"Failed to build constructor transaction: {e}")
        
        # Sign and send transaction
        signed_tx = self.wallet_manager.sign_transaction(from_address, constructor_tx)
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx['rawTransaction'])
        
        # Wait for receipt
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        
        if receipt['status'] == 0:
            raise RuntimeError("Contract deployment failed")
        
        # Load the deployed contract
        contract_address = receipt['contractAddress']
        self.load_contract(contract_address, abi)
        
        return {
            "contractAddress": contract_address,
            "transactionHash": receipt['transactionHash'].hex(),
            "blockNumber": receipt['blockNumber'],
            "gasUsed": receipt['gasUsed'],
            "status": receipt['status']
        }

    def call_contract_method(self, address: str, method_name: str, 
                           args: Optional[List] = None,
                           from_address: str = None,
                           value: int = 0,
                           gas_limit: int = 300000) -> Dict[str, Any]:
        """Call a state-changing contract method."""
        address = to_checksum_address(address)
        
        if address not in self._contracts:
            raise ValueError(f"Contract {address} not loaded. Call load_contract first.")
        
        if not from_address:
            raise ValueError("from_address is required for state-changing calls")
            
        from_address = to_checksum_address(from_address)
        
        if not self.wallet_manager.verify_wallet(from_address):
            raise ValueError(f"Wallet {from_address} not found")
        
        contract = self._contracts[address]
        
        # Check if method exists
        if not hasattr(contract.functions, method_name):
            raise ValueError(f"Method {method_name} not found in contract ABI")
        
        # Get method
        method = getattr(contract.functions, method_name)
        
        if args is None:
            args = []
        
        try:
            # Build transaction
            tx = method(*args).build_transaction({
                'from': from_address,
                'nonce': self.wallet_manager.get_transaction_count(from_address),
                'gas': gas_limit,
                'gasPrice': self.w3.eth.gas_price,
                'value': value,
                'chainId': self.w3.eth.chain_id
            })
        except Exception as e:
            raise ValueError(f"Failed to build transaction: {e}")
        
        # Sign and send
        signed_tx = self.wallet_manager.sign_transaction(from_address, tx)
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx['rawTransaction'])
        
        # Wait for receipt
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        
        # Decode logs if any
        logs = []
        for log in receipt['logs']:
            try:
                event = contract.events[log['topics'][0]].process_log(log)
                logs.append({
                    'event': event['event'],
                    'args': dict(event['args'])
                })
            except:
                # Skip logs we can't decode
                pass
        
        return {
            "transactionHash": receipt['transactionHash'].hex(),
            "blockNumber": receipt['blockNumber'],
            "gasUsed": receipt['gasUsed'],
            "status": receipt['status'],
            "logs": logs
        }

    def read_contract(self, address: str, method_name: str, 
                     args: Optional[List] = None) -> Any:
        """Call a view/pure contract method (no state change)."""
        address = to_checksum_address(address)
        
        if address not in self._contracts:
            raise ValueError(f"Contract {address} not loaded. Call load_contract first.")
        
        contract = self._contracts[address]
        
        # Check if method exists
        if not hasattr(contract.functions, method_name):
            raise ValueError(f"Method {method_name} not found in contract ABI")
        
        # Get method
        method = getattr(contract.functions, method_name)
        
        if args is None:
            args = []
        
        try:
            # Call the method
            result = method(*args).call()
            return result
        except Exception as e:
            raise ValueError(f"Failed to call method: {e}")

    def get_contract_events(self, address: str, event_name: str,
                          from_block: Union[int, str] = 0,
                          to_block: Union[int, str] = 'latest',
                          filters: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """Get events from a contract."""
        address = to_checksum_address(address)
        
        if address not in self._contracts:
            raise ValueError(f"Contract {address} not loaded. Call load_contract first.")
        
        contract = self._contracts[address]
        
        # Check if event exists
        if not hasattr(contract.events, event_name):
            raise ValueError(f"Event {event_name} not found in contract ABI")
        
        # Get event
        event = getattr(contract.events, event_name)
        
        # Build filter
        event_filter = event.create_filter(
            fromBlock=from_block,
            toBlock=to_block,
            argument_filters=filters or {}
        )
        
        # Get events
        events = []
        for log in event_filter.get_all_entries():
            events.append({
                'event': log['event'],
                'args': dict(log['args']),
                'blockNumber': log['blockNumber'],
                'transactionHash': log['transactionHash'].hex(),
                'address': log['address'],
                'logIndex': log['logIndex']
            })
        
        return events

    def encode_function_call(self, contract_instance: Contract, 
                           method_name: str, args: List) -> str:
        """Helper to encode a function call."""
        if not hasattr(contract_instance.functions, method_name):
            raise ValueError(f"Method {method_name} not found in contract ABI")
        
        method = getattr(contract_instance.functions, method_name)
        
        try:
            # Encode the function call
            return method(*args).build_transaction({'from': '0x0000000000000000000000000000000000000000'})['data']
        except Exception as e:
            raise ValueError(f"Failed to encode function call: {e}")

    def decode_function_result(self, contract_instance: Contract,
                             method_name: str, result: str) -> Any:
        """Helper to decode a function result."""
        if not hasattr(contract_instance.functions, method_name):
            raise ValueError(f"Method {method_name} not found in contract ABI")
        
        # Get method ABI
        method_abi = None
        for item in contract_instance.abi:
            if item.get('type') == 'function' and item.get('name') == method_name:
                method_abi = item
                break
        
        if not method_abi:
            raise ValueError(f"Method {method_name} ABI not found")
        
        # Get output types
        output_types = [output['type'] for output in method_abi.get('outputs', [])]
        
        if not output_types:
            return None
        
        try:
            # Decode the result
            if result.startswith('0x'):
                result = result[2:]
            
            decoded = decode(output_types, bytes.fromhex(result))
            
            # Return single value if only one output
            if len(decoded) == 1:
                return decoded[0]
            
            return decoded
        except Exception as e:
            raise ValueError(f"Failed to decode result: {e}")

    def list_contracts(self) -> Dict[str, str]:
        """List all loaded contracts."""
        contracts = {}
        for key, contract in self._contracts.items():
            if key.startswith('0x'):  # Only include addresses, not names
                contracts[key] = {
                    'address': contract.address,
                    'functions': [item['name'] for item in contract.abi if item.get('type') == 'function'],
                    'events': [item['name'] for item in contract.abi if item.get('type') == 'event']
                }
        return contracts

    def verify_contract(self, address: str, source_code: str, 
                       compiler_version: str) -> Dict[str, Any]:
        """Placeholder for contract verification. 
        This would typically interact with Etherscan or similar service."""
        # This is a placeholder as actual verification requires external service integration
        return {
            "status": "not_implemented",
            "message": "Contract verification requires integration with Etherscan or similar service"
        }