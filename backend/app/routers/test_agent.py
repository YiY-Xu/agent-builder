from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any, Optional
import logging
import re
import yaml
from pydantic import BaseModel, Field

from app.services.claude_service import ClaudeService
from app.services.knowledge_service import KnowledgeService
from app.services.yaml_service import generate_yaml_async
from app.models.request_models import ChatMessage
from app.dependencies import get_claude_service, get_knowledge_service
from app.config.settings import settings

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api",
    tags=["test-agent"],
    responses={404: {"description": "Not found"}},
)

# Request model for testing an agent
class TestAgentRequest(BaseModel):
    message: str = Field(..., description="User message to send to the agent")
    agent_config: Dict[str, Any] = Field(..., description="Agent configuration from YAML")
    history: List[Dict[str, str]] = Field(default_factory=list, description="Chat history")


# Response model for test agent
class TestAgentResponse(BaseModel):
    message: str = Field(..., description="Agent's response message")

# Use dependencies from app.dependencies instead of local definitions

@router.post("/test-agent", response_model=TestAgentResponse)
async def test_agent(
    request: TestAgentRequest,
    claude_service: ClaudeService = Depends(get_claude_service),
    knowledge_service: KnowledgeService = Depends(get_knowledge_service)
):
    """
    Test an agent with a loaded YAML configuration
    
    - Takes a user message, agent configuration, and chat history
    - Creates a custom system prompt based on the agent configuration
    - Retrieves relevant information from knowledge base if applicable
    - Sends the message to Claude with the agent-specific prompt
    - Returns Claude's response
    """
    try:
        logger.info(f"Testing agent with message: {request.message}")
        logger.info(f"Initial agent config: {request.agent_config}")
        
        # Log MCP servers specifically for debugging
        if "mcp_servers" in request.agent_config:
            logger.info(f"MCP servers in request: {request.agent_config['mcp_servers']}")
        
        # Generate the complete YAML configuration from the agent config
        yaml_content = await generate_yaml_async(request.agent_config)
        logger.info(f"Generated YAML configuration:\n{yaml_content}")
        
        # Parse the generated YAML back to a dict
        complete_config = yaml.safe_load(yaml_content)

        # Log MCP servers after YAML generation
        if "mcp_servers" in complete_config:
            logger.info(f"MCP servers after YAML generation: {complete_config['mcp_servers']}")
        
        # Determine mode (normal/debug) from final YAML
        mode = complete_config.get("config", {}).get("mode", "normal")
        logger.info(f"Final mode from YAML config: {mode}")
        
        # Basic metadata
        name = complete_config.get("name", "AI Assistant")
        description = complete_config.get("description", "")
        instruction = complete_config.get("instruction", "")
        
        # Extract normal tools, if any
        tools = complete_config.get("tools", [])
        tools_description = ""
        if tools:
            tools_description = "You have access to the following tools:\n\n"
            for tool in tools:
                tool_name = tool.get('name', 'Unknown Tool')
                tool_endpoint = tool.get('endpoint', 'No endpoint')
                tools_description += f"- {tool_name}: {tool_endpoint}\n"
        
        # Extract MCP servers, if any, and build a description block
        mcp_servers = complete_config.get("mcp_servers", [])
        mcp_servers_description = ""
        if mcp_servers:
            mcp_servers_description = "You also have access to the following MCP servers:\n\n"
            for server in mcp_servers:
                server_name = server.get("name", "Unnamed Server")
                sse_url = server.get("sse_url", "No SSE URL Provided")
                mcp_servers_description += f"- **{server_name}** (SSE URL: {sse_url})\n"
                
                services = server.get("services", [])
                for svc in services:
                    svc_name = svc.get("name", "Unnamed Service")
                    capabilities = svc.get("capabilities", [])
                    mcp_servers_description += f"  - Service **{svc_name}** with capabilities: {', '.join(capabilities)}\n"
                    
                    endpoints = svc.get("endpoints", [])
                    for ep in endpoints:
                        path = ep.get("path", "")
                        methods = ep.get("methods", [])
                        desc = ep.get("description", "")
                        capability = ep.get("capability", "")
                        mcp_servers_description += (
                            f"    - Endpoint: `{path}` (methods: {', '.join(methods)})\n"
                            f"      Description: {desc}\n"
                            f"      Capability: {capability}\n"
                        )
                
                mcp_servers_description += "\n"
        
        # Combine both types of tool information
        combined_tools_info = (tools_description + "\n" + mcp_servers_description).strip()
        
        # Create the system prompt
        system_prompt = f"""
You are {name}, an AI assistant.

{description}

CURRENT MODE: {mode.upper()}

When in debug mode, you must structure your response in exactly this format:
```
QUERY ANALYSIS:
[Your analysis of the user's query]

KNOWLEDGE SOURCES:
[List of knowledge sources used]

TOOL SELECTION:
[Your tool selection reasoning]
```

[Your actual response to the user in plain text, not in a code block]

{instruction}

{combined_tools_info}

Remember to act consistently with your configuration and purpose.
""".strip()
        
        logger.info(f"Generated system prompt:\n{system_prompt}")
        
        # Construct chat messages
        messages = []
        for msg in request.history:
            messages.append(ChatMessage(
                role=msg["role"],
                content=msg["content"]
            ))
        
        # User message appended at the end
        user_message = ChatMessage(
            role="user",
            content=request.message
        )
        messages.append(user_message)
        
        # Check if knowledge retrieval is needed
        has_knowledge_base = "knowledge_base" in complete_config and (
            complete_config["knowledge_base"].get("index_info")
        )
        
        if has_knowledge_base:
            logger.info("Knowledge base exists, attempting retrieval")
            
            # Relevance threshold for knowledge retrieval
            relevance_threshold = settings.KNOWLEDGE_RELEVANCE_THRESHOLD
            logger.info(f"Using relevance threshold: {relevance_threshold}")
            
            # Query the knowledge base
            retrieved_context = await knowledge_service.query_knowledge_base(
                request.message, 
                complete_config,
                similarity_top_k=1,  # Only get the most relevant document
                relevance_threshold=relevance_threshold
            )
            
            if retrieved_context:
                logger.info("Retrieved relevant document - augmenting user query")
                print("--------------------------------")
                print(retrieved_context)
                print("--------------------------------")
                augmented_message = f"""
{request.message}

[Retrieved Knowledge]
{retrieved_context}
[End Retrieved Knowledge]

Please use the retrieved knowledge above to help answer my question, and cite the sources if appropriate.
"""
                # Replace the last message with augmented version
                messages[-1] = ChatMessage(
                    role="user",
                    content=augmented_message
                )
            else:
                logger.info(f"No relevant documents found above threshold: {relevance_threshold}")
                logger.info("Proceeding with regular query without knowledge augmentation")
        
        # Call Claude with the custom system prompt
        claude_response = await claude_service.send_message_with_custom_prompt(
            messages=messages,
            system_prompt=system_prompt
        )
        
        logger.info(f"Claude's raw response:\n{claude_response}")
        
        # Return the final response
        return TestAgentResponse(message=claude_response)
    
    except Exception as e:
        logger.error(f"Error testing agent: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error testing agent: {str(e)}")


def create_agent_prompt(agent_config: Dict[str, Any]) -> str:
    """
    Create a system prompt based on the agent configuration
    
    Args:
        agent_config: Agent configuration from YAML
        
    Returns:
        System prompt for Claude
    """
    # Extract configuration values
    name = agent_config.get("name", "AI Assistant")
    description = agent_config.get("description", "")
    instruction = agent_config.get("instruction", "")
    
    # Extract memory size and mode from config
    memory_size = 10  # Default
    mode = "normal"   # Default
    if "config" in agent_config:
        memory_size = agent_config["config"].get("memory_size", memory_size)
        mode = agent_config["config"].get("mode", mode)
    elif "memory_size" in agent_config:
        memory_size = agent_config["memory_size"]
    
    # Extract tools
    tools = agent_config.get("tools", [])
    tools_description = ""
    if tools:
        tools_description = "You have access to the following tools:\n\n"
        for tool in tools:
            tools_description += f"- {tool.get('name', 'Unknown Tool')}: {tool.get('endpoint', 'No endpoint')}\n"
    
    # Create the agent prompt
    prompt = f"""
You are {name}, an AI assistant.

{description}

{instruction}

{tools_description}

Remember to act consistently with your configuration and purpose.
"""
    
    return prompt.strip()

class AgentConfig(BaseModel):
    config: Dict[str, Any] = Field(..., description="Agent configuration")

class ToggleModeRequest(BaseModel):
    current_mode: str = Field(default="debug", description="Current mode (normal or debug)")

class ToggleModeResponse(BaseModel):
    new_mode: str = Field(..., description="New mode after toggle")

@router.post("/toggle-mode", response_model=ToggleModeResponse)
async def toggle_mode(request: ToggleModeRequest):
    """
    Toggle the agent's mode between 'normal' and 'debug'
    
    Args:
        request: Current mode to toggle
        
    Returns:
        New mode after toggle
    """
    try:
        logger.info(f"Current mode: {request.current_mode}")
        new_mode = "debug" if request.current_mode == "normal" else "normal"
        logger.info(f"New mode: {new_mode}")
        return ToggleModeResponse(new_mode=new_mode)
        
    except Exception as e:
        logger.error(f"Error toggling mode: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error toggling mode: {str(e)}")