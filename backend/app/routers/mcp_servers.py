from fastapi import APIRouter, HTTPException, BackgroundTasks
import logging
import traceback
from datetime import datetime
from ..services.mcp_services import connect_sse_with_timeout, process_sse_events, load_mcp_servers, save_mcp_servers, add_mcp_server
from ..models.mcp_models import MCPServerInput

router = APIRouter(prefix="/api/mcp-servers", tags=["MCP Servers"])

# Configure logging
logger = logging.getLogger(__name__)

@router.post("/add")
async def add_mcp_server_route(server: MCPServerInput):
    """
    Add a new MCP server by connecting to its SSE endpoint and discovering services.
    """
    try:
        # Connect to the SSE endpoint
        session, response = await connect_sse_with_timeout(server.sse_url)
        
        # Process the SSE events to discover services
        services = await process_sse_events(session, response)
        
        if not services:
            raise HTTPException(status_code=400, 
                              detail="No services discovered from the MCP server")
        
        # Create the MCP server record
        new_server = await add_mcp_server(server, services)
        
        return {
            "message": "MCP server added successfully",
            "server": new_server
        }
        
    except HTTPException:
        # Re-raise FastAPI HTTP exceptions
        raise
    except Exception as e:
        logger.error(traceback.format_exc())
        logger.error(f"Error adding MCP server: {str(e)}")
        raise HTTPException(status_code=500, 
                          detail=f"Error adding MCP server: {str(e)}")

@router.get("/list")
async def list_mcp_servers():
    """
    List all registered MCP servers.
    """
    servers = await load_mcp_servers()
    print(servers)
    return {"servers": servers}

@router.get("/{server_name}")
async def get_mcp_server(server_name: str):
    """
    Get details of a specific MCP server.
    """
    servers = await load_mcp_servers()
    for server in servers:
        if server["name"] == server_name:
            return server
    
    raise HTTPException(status_code=404, detail=f"MCP server '{server_name}' not found")

@router.delete("/{server_name}")
async def delete_mcp_server(server_name: str):
    """
    Delete an MCP server.
    """
    servers = await load_mcp_servers()
    initial_count = len(servers)
    
    servers = [server for server in servers if server["name"] != server_name]
    
    if len(servers) == initial_count:
        raise HTTPException(status_code=404, detail=f"MCP server '{server_name}' not found")
    
    await save_mcp_servers(servers)
    return {"message": f"MCP server '{server_name}' deleted"}

@router.post("/refresh/{server_name}")
async def refresh_mcp_server(server_name: str):
    """
    Refresh the services for a specific MCP server.
    """
    servers = await load_mcp_servers()
    
    target_server = None
    for server in servers:
        if server["name"] == server_name:
            target_server = server
            break
    
    if not target_server:
        raise HTTPException(status_code=404, detail=f"MCP server '{server_name}' not found")
    
    try:
        # Connect to the SSE endpoint
        session, response = await connect_sse_with_timeout(target_server["sse_url"])
        
        # Process the SSE events to discover services
        services = await process_sse_events(session, response)
        
        if not services:
            raise HTTPException(status_code=400, 
                              detail="No services discovered from the MCP server")
        
        # Update the server record
        target_server["services"] = services
        target_server["last_connected"] = datetime.now().isoformat()
        
        # Save the updated servers
        await save_mcp_servers(servers)
        
        return {
            "message": f"MCP server '{server_name}' refreshed",
            "server": target_server
        }
        
    except Exception as e:
        logger.error(f"Error refreshing MCP server: {str(e)}")
        raise HTTPException(status_code=500, 
                          detail=f"Error refreshing MCP server: {str(e)}")