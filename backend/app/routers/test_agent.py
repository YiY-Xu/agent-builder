from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any, Optional
import logging
import re
import yaml
from pydantic import BaseModel, Field

from app.services.claude_service import ClaudeService
from app.services.knowledge_retrieval import KnowledgeRetrievalService
from app.services.yaml_service import generate_yaml
from app.models.request_models import ChatMessage
from app.models.response_models import ChatResponse

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


# Dependency to get ClaudeService instance
def get_claude_service():
    return ClaudeService()

# Dependency to get KnowledgeRetrievalService instance
def get_knowledge_service():
    return KnowledgeRetrievalService()


@router.post("/test-agent", response_model=TestAgentResponse)
async def test_agent(
    request: TestAgentRequest,
    claude_service: ClaudeService = Depends(get_claude_service),
    knowledge_service: KnowledgeRetrievalService = Depends(get_knowledge_service)
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
        
        # Get the mode directly from the request config first
        mode = request.agent_config.get("config", {}).get("mode", "normal")
        logger.info(f"Initial mode from request: {mode}")
        
        # Generate the complete YAML configuration
        yaml_content = generate_yaml(request.agent_config)
        logger.info(f"Generated YAML configuration:\n{yaml_content}")
        
        # Parse the generated YAML back to a dict to ensure we have all instructions
        complete_config = yaml.safe_load(yaml_content)
        
        # Get the mode from the complete config, as it may have been updated by the YAML service
        mode = complete_config.get("config", {}).get("mode", "normal")
        logger.info(f"Final mode from YAML config: {mode}")
        
        # Create system prompt using the complete configuration
        name = complete_config.get("name", "AI Assistant")
        description = complete_config.get("description", "")
        instruction = complete_config.get("instruction", "")
        
        # Extract tools
        tools = complete_config.get("tools", [])
        tools_description = ""
        if tools:
            tools_description = "You have access to the following tools:\n\n"
            for tool in tools:
                tools_description += f"- {tool.get('name', 'Unknown Tool')}: {tool.get('endpoint', 'No endpoint')}\n"
        
        # Create the system prompt with explicit mode reminder
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

{tools_description}

Remember to act consistently with your configuration and purpose.
"""
        system_prompt = system_prompt.strip()
        logger.info(f"Generated system prompt:\n{system_prompt}")
        
        # Format chat history
        messages = []
        for msg in request.history:
            messages.append(ChatMessage(
                role=msg["role"],
                content=msg["content"]
            ))
        
        # Add the user's message
        user_message = ChatMessage(
            role="user",
            content=request.message
        )
        messages.append(user_message)
        
        # Check if knowledge retrieval is needed
        has_knowledge_base = "knowledge_base" in complete_config and (
            complete_config["knowledge_base"].get("index_name") or 
            complete_config["knowledge_base"].get("local_path")
        )
        
        might_need_knowledge = has_knowledge_base and any(
            keyword in request.message.lower() 
            for keyword in ["what", "who", "when", "where", "why", "how", "explain", "tell me about", "information"]
        )
        
        # Retrieve knowledge if needed
        if might_need_knowledge:
            logger.info("Query might need knowledge, attempting retrieval")
            retrieved_context = await knowledge_service.query_knowledge_base(
                request.message, 
                complete_config
            )
            if retrieved_context:
                logger.info("Adding retrieved knowledge to user message")
                augmented_message = f"""
{request.message}

[Retrieved Knowledge]
{retrieved_context}
[End Retrieved Knowledge]

Please use the retrieved knowledge above to help answer my question, and cite the sources if appropriate.
"""
                messages[-1] = ChatMessage(
                    role="user",
                    content=augmented_message
                )
        
        # Call Claude with the custom system prompt
        claude_response = await claude_service.send_message_with_custom_prompt(
            messages=messages,
            system_prompt=system_prompt
        )
        logger.info(f"Claude's raw response:\n{claude_response}")
        
        # No need for response reformatting since the instruction specifies the format
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
    current_mode: str = Field(default="normal", description="Current mode (normal or debug)")

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