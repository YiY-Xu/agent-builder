from pydantic import BaseModel# Model for adding a new MCP server
from typing import List, Dict, Any, Optional

class MCPServerInput(BaseModel):
    name: str
    sse_url: str

# Model for discovered service
class DiscoveredService(BaseModel):
    id: str
    name: str
    capabilities: List[str] = []
    endpoints: List[Dict[str, Any]] = []

# Model for stored MCP server
class MCPServer(BaseModel):
    name: str
    sse_url: str
    last_connected: Optional[str] = None
    services: List[Dict[str, Any]] = []