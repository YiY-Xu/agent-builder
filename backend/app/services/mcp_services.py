import json
import os
import aiohttp
import asyncio
import time
from datetime import datetime
import logging
from fastapi import HTTPException

logger = logging.getLogger(__name__)

# Path to the JSON file for storing MCP server data
MCP_SERVERS_FILE = "mcp_servers.json"

async def process_sse_events(session, response, timeout: int = 30):
    """
    Process SSE events from a connected endpoint.
    
    Args:
        session: aiohttp ClientSession
        response: aiohttp ClientResponse
        timeout: How long to wait for the initial catalog in seconds
        
    Returns:
        Dictionary of discovered services
    """
    discovered_services = {}
    start_time = time.time()
    
    try:
        # Set up processing of the SSE stream
        async for line in response.content:
            line = line.decode('utf-8').strip()
            
            # Check for timeout while waiting for initial catalog
            if time.time() - start_time > timeout and not discovered_services:
                raise HTTPException(status_code=408, 
                                  detail="Timeout waiting for initial service catalog")
            
            # Skip empty lines or comments
            if not line or line.startswith(':'):
                continue
            
            # Parse SSE event
            if line.startswith('event:'):
                event_type = line[6:].strip()
            elif line.startswith('data:'):
                data = json.loads(line[5:].strip())
                print(data)
                
                # Process initial catalog
                if event_type == "INITIAL_CATALOG":
                    services_data = data.get("data", [])
                    print(services_data)
                    for service_data in services_data:
                        service_id = service_data.get("id")
                        service_name = service_data.get("name")
                        
                        if service_id and service_name:
                            discovered_services[service_id] = {
                                "id": service_id,
                                "name": service_name,
                                "capabilities": service_data.get("capabilities", []),
                                "endpoints": service_data.get("endpoints", [])
                            }
                    
                    # Once we have the initial catalog, we can disconnect
                    if discovered_services:
                        break
                        
                # Process individual service registrations
                elif event_type in ["SERVICE_REGISTERED", "SERVICE_UPDATED"]:
                    service_data = data.get("data", {})
                    service_id = service_data.get("id")
                    service_name = service_data.get("name")
                    
                    if service_id and service_name:
                        discovered_services[service_id] = {
                            "id": service_id,
                            "name": service_name,
                            "capabilities": service_data.get("capabilities", []),
                            "endpoints": service_data.get("endpoints", [])
                        }
    finally:
        # Ensure we close the session
        await session.close()
    
    return list(discovered_services.values())

async def load_mcp_servers():
    """Load MCP servers from the JSON file."""
    try:
        if os.path.exists(MCP_SERVERS_FILE):
            with open(MCP_SERVERS_FILE, 'r') as f:
                return json.load(f)
        else:
            return []
    except Exception as e:
        logger.error(f"Error loading MCP servers: {str(e)}")
        return []

async def save_mcp_servers(servers):
    """Save MCP servers to the JSON file."""
    try:
        with open(MCP_SERVERS_FILE, 'w') as f:
            json.dump(servers, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving MCP servers: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error saving MCP servers: {str(e)}")

async def connect_sse_with_timeout(url: str, timeout: int = 10):
    """
    Connect to an SSE endpoint with a timeout.
    
    Args:
        url: SSE endpoint URL
        timeout: Connection timeout in seconds
        
    Returns:
        ClientResponse object or raises an exception
    """
    try:
        # Create a ClientTimeout with the specified timeout
        timeout_obj = aiohttp.ClientTimeout(total=timeout)
        
        # Connect to the SSE endpoint
        session = aiohttp.ClientSession(timeout=timeout_obj)
        response = await session.get(url, headers={'Accept': 'text/event-stream'})
        
        if response.status != 200:
            error_text = await response.text()
            await session.close()
            raise HTTPException(status_code=response.status, 
                              detail=f"Failed to connect to SSE endpoint: {error_text}")
        
        return session, response
    except asyncio.TimeoutError:
        logger.error(f"Timeout connecting to SSE endpoint: {url}")
        raise HTTPException(status_code=408, 
                          detail=f"Timeout connecting to SSE endpoint: {url}")
    except Exception as e:
        logger.error(f"Error connecting to SSE endpoint: {str(e)}")
        raise HTTPException(status_code=500, 
                          detail=f"Error connecting to SSE endpoint: {str(e)}")
    
async def add_mcp_server(server, services):
    new_server = {
            "name": server.name,
            "sse_url": server.sse_url,
            "last_connected": datetime.now().isoformat(),
            "services": services
        }
        
        # Load existing servers
    servers = await load_mcp_servers()
    
    # Check if this server already exists
    for i, existing_server in enumerate(servers):
        if existing_server["sse_url"] == server.sse_url:
            # Update existing server
            servers[i] = new_server
            await save_mcp_servers(servers)
            return {"message": "MCP server updated", "server": new_server}
    
    # Add new server
    servers.append(new_server)
    await save_mcp_servers(servers)

    return new_server