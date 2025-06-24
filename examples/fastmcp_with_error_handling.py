"""
Example of using the error handler with FastMCP.

This example shows how to integrate the comprehensive error handling
with a FastMCP server implementation.
"""

from fastmcp import FastMCP
from web3 import Web3
import os
from dotenv import load_dotenv

from src.middleware.fastmcp_error_handler import (
    fastmcp_error_handler,
    FastMCPErrorMiddleware,
    WalletNotFoundError,
    InvalidAddressError,
    InvalidParametersError,
    InsufficientFundsError,
    TransactionFailedError,
)
from src.core.wallet import WalletManager
from src.core.transaction import TransactionManager

# Load environment variables
load_dotenv()

# Initialize FastMCP server
mcp = FastMCP("Ethereum MCP Server")

# Add error handling middleware
error_middleware = FastMCPErrorMiddleware(debug=True)

# Initialize Web3 and managers
w3 = Web3(Web3.HTTPProvider(os.getenv("ETH_RPC_URL", "http://localhost:8545")))
wallet_manager = WalletManager(w3)
transaction_manager = TransactionManager(w3, wallet_manager)


@mcp.tool()
@fastmcp_error_handler
async def create_wallet(name: str) -> dict:
    """
    Create a new Ethereum wallet.
    
    Args:
        name: Name for the wallet
        
    Returns:
        Wallet information including address and chain ID
        
    Raises:
        WalletAlreadyExistsError: If wallet with name already exists
    """
    wallet = wallet_manager.create_wallet(name)
    return {
        "address": wallet["address"],
        "name": name,
        "chainId": w3.eth.chain_id
    }


@mcp.tool()
@fastmcp_error_handler
async def get_balance(address: str) -> dict:
    """
    Get ETH balance for an address.
    
    Args:
        address: Ethereum address
        
    Returns:
        Balance information
        
    Raises:
        InvalidAddressError: If address format is invalid
    """
    # Validate address format
    if not address.startswith("0x") or len(address) != 42:
        raise InvalidAddressError(address, "Invalid address format")
    
    try:
        # Check if valid checksum address
        Web3.to_checksum_address(address)
    except ValueError:
        raise InvalidAddressError(address, "Invalid address checksum")
    
    balance = wallet_manager.get_balance(address)
    return {
        "address": address,
        "balance": str(balance),
        "balance_ether": str(Web3.from_wei(balance, 'ether')),
        "chainId": w3.eth.chain_id
    }


@mcp.tool()
@fastmcp_error_handler
async def send_transaction(
    from_wallet: str,
    to_address: str,
    amount_ether: float,
    gas_price_gwei: float = None
) -> dict:
    """
    Send ETH from one address to another.
    
    Args:
        from_wallet: Name of the wallet to send from
        to_address: Recipient address
        amount_ether: Amount to send in ETH
        gas_price_gwei: Gas price in Gwei (optional)
        
    Returns:
        Transaction information
        
    Raises:
        WalletNotFoundError: If wallet not found
        InvalidAddressError: If to_address is invalid
        InsufficientFundsError: If wallet has insufficient funds
        InvalidParametersError: If parameters are invalid
    """
    # Validate parameters
    if amount_ether <= 0:
        raise InvalidParametersError("amount_ether", "Amount must be greater than 0")
    
    # Get wallet
    wallet = wallet_manager.get_wallet(from_wallet)
    if not wallet:
        raise WalletNotFoundError(from_wallet)
    
    # Validate recipient address
    try:
        to_address = Web3.to_checksum_address(to_address)
    except ValueError:
        raise InvalidAddressError(to_address, "Invalid recipient address")
    
    # Check balance
    balance = wallet_manager.get_balance(wallet["address"])
    amount_wei = Web3.to_wei(amount_ether, 'ether')
    
    if balance < amount_wei:
        raise InsufficientFundsError(
            required=str(amount_wei),
            available=str(balance),
            address=wallet["address"]
        )
    
    # Send transaction
    try:
        tx_hash = transaction_manager.send_transaction(
            from_address=wallet["address"],
            private_key=wallet["privateKey"],
            to_address=to_address,
            value=amount_wei,
            gas_price=Web3.to_wei(gas_price_gwei, 'gwei') if gas_price_gwei else None
        )
        
        return {
            "transaction_hash": tx_hash,
            "from": wallet["address"],
            "to": to_address,
            "amount": str(amount_wei),
            "amount_ether": str(amount_ether),
            "status": "pending"
        }
        
    except Exception as e:
        # Check if it's a known transaction error
        error_msg = str(e).lower()
        if "nonce too low" in error_msg:
            raise TransactionFailedError(
                tx_hash="pending",
                reason="Nonce too low - transaction already processed"
            )
        elif "gas too low" in error_msg:
            raise TransactionFailedError(
                tx_hash="pending",
                reason="Gas limit too low for transaction"
            )
        else:
            raise TransactionFailedError(
                tx_hash="pending",
                reason=str(e)
            )


@mcp.tool()
@fastmcp_error_handler
async def get_gas_estimate() -> dict:
    """
    Get current gas price estimates.
    
    Returns:
        Gas price estimates in Wei and Gwei
    """
    estimates = transaction_manager.get_gas_price_estimate()
    return {
        **estimates,
        "chainId": w3.eth.chain_id,
        "block_number": w3.eth.block_number
    }


@mcp.tool()
@fastmcp_error_handler
async def list_wallets() -> dict:
    """
    List all available wallets.
    
    Returns:
        List of wallet addresses and names
    """
    wallets = wallet_manager.list_wallets()
    return {
        "wallets": wallets,
        "count": len(wallets),
        "chainId": w3.eth.chain_id
    }


# Example of using the error handler in a custom function
@fastmcp_error_handler
async def validate_transaction_params(params: dict) -> bool:
    """
    Validate transaction parameters.
    
    This is an example of using the error handler decorator
    on a custom function that's not a tool.
    """
    required_fields = ["from", "to", "value"]
    
    for field in required_fields:
        if field not in params:
            raise InvalidParametersError(
                field,
                f"Required field '{field}' is missing"
            )
    
    # Validate addresses
    for addr_field in ["from", "to"]:
        try:
            Web3.to_checksum_address(params[addr_field])
        except ValueError:
            raise InvalidAddressError(
                params[addr_field],
                f"Invalid address in field '{addr_field}'"
            )
    
    # Validate value
    if params["value"] <= 0:
        raise InvalidParametersError(
            "value",
            "Transaction value must be greater than 0"
        )
    
    return True


if __name__ == "__main__":
    # Run the FastMCP server
    mcp.run()