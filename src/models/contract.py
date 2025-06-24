from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel
from datetime import datetime


class ContractInfo(BaseModel):
    """Store contract metadata."""
    address: str
    abi: List[Dict[str, Any]]
    name: Optional[str] = None
    deployed_at: Optional[datetime] = None


class ContractMethod(BaseModel):
    """Method details for a smart contract."""
    name: str
    inputs: List[Dict[str, Any]]
    outputs: List[Dict[str, Any]]
    stateMutability: str


class ContractEvent(BaseModel):
    """Event details for a smart contract."""
    name: str
    inputs: List[Dict[str, Any]]
    signature: str


class DeploymentResult(BaseModel):
    """Deployment response data."""
    address: str
    tx_hash: str
    gas_used: int


class ContractCallResult(BaseModel):
    """Call response data."""
    result: Any
    tx_hash: Optional[str] = None
    gas_used: Optional[int] = None


class EventLog(BaseModel):
    """Decoded event data."""
    event_name: str
    args: Dict[str, Any]
    block_number: int
    tx_hash: str
    log_index: int