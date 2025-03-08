from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any, Optional
import logging
import re

from ..services.claude_service import ClaudeService
from ..services.knowledge_retrieval import KnowledgeRetrievalService
from ..models.request_models import ChatMessage
from ..models.response_models import ChatResponse
from pydantic import BaseModel, Field

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
        logger.info(f"Agent config: {request.agent_config}")
        
        # Check if the message is asking for a cat image
        cat_image_requested = bool(re.search(r'\b(cat|kitten|cats|kittens)\b', request.message.lower()))
        
        # Check if the agent has a knowledge base and if the query might need knowledge
        has_knowledge_base = "knowledge_base" in request.agent_config and (
            request.agent_config["knowledge_base"].get("index_name") or 
            request.agent_config["knowledge_base"].get("local_path")
        )
        
        # Determine if query might need knowledge (simple heuristic)
        might_need_knowledge = has_knowledge_base and any(
            keyword in request.message.lower() 
            for keyword in ["what", "who", "when", "where", "why", "how", "explain", "tell me about", "information"]
        )
        
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
        
        # Create a custom system prompt for the agent
        system_prompt = create_agent_prompt(request.agent_config)
        
        # Retrieve knowledge if needed
        retrieved_context = None
        if might_need_knowledge:
            logger.info("Query might need knowledge, attempting retrieval")
            retrieved_context = await knowledge_service.query_knowledge_base(
                request.message, 
                request.agent_config
            )
        
        # Add special instruction for image support if needed
        if 'cat' in request.message.lower():
            system_prompt += "\n\nThe user seems interested in cats. If appropriate in your response, you can include a link to a cat image using https://cataas.com/cat without any Markdown formatting - just include the URL directly."
        
        # If knowledge was retrieved, augment the user's message with it
        if retrieved_context:
            logger.info("Adding retrieved knowledge to user message")
            augmented_message = f"""
{request.message}

[Retrieved Knowledge]
{retrieved_context}
[End Retrieved Knowledge]

Please use the retrieved knowledge above to help answer my question, and cite the sources if appropriate.
"""
            # Replace the last message (user's question) with the augmented version
            messages[-1] = ChatMessage(
                role="user",
                content=augmented_message
            )
        
        # Call Claude with the custom system prompt
        claude_response = await claude_service.send_message_with_custom_prompt(
            messages=messages,
            system_prompt=system_prompt
        )
        
        # Fix markdown image syntax if present
        claude_response = claude_response.replace('![A cute cat](https://cataas.com/cat)', 'https://cataas.com/cat')
        claude_response = claude_response.replace('![A cute cat]', '')
        
        # If cats were mentioned but no cat image URL was included, add one if appropriate
        if cat_image_requested and "cataas.com/cat" not in claude_response:
            if "cat" in request.message.lower() and len(claude_response) > 0 and not claude_response.startswith("I don't"):
                claude_response += "\n\nHere's a cat image for you:\nhttps://cataas.com/cat"
        
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
    
    # Extract memory size from config
    memory_size = 10  # Default
    if "config" in agent_config and "memory_size" in agent_config["config"]:
        memory_size = agent_config["config"]["memory_size"]
    elif "memory_size" in agent_config:
        memory_size = agent_config["memory_size"]
    
    # Extract tools
    tools = agent_config.get("tools", [])
    tools_description = ""
    if tools:
        tools_description = "You have access to the following tools:\n\n"
        for tool in tools:
            tools_description += f"- {tool.get('name', 'Unknown Tool')}: {tool.get('endpoint', 'No endpoint')}\n"
    
    # Extract knowledge base information if available
    knowledge_base_instructions = ""
    
    if "knowledge_base" in agent_config:
        kb = agent_config["knowledge_base"]
        storage_type = kb.get("storage_type", "llamacloud" if kb.get("index_name") else "local")
        
        # Include knowledge base details
        if storage_type == "llamacloud" and kb.get("index_name"):
            knowledge_base_instructions = f"""
You have access to a knowledge base with document storage on LlamaCloud.
Index name: {kb.get("index_name")}
Document count: {kb.get("document_count", "Unknown")}

When users ask questions that require information from these documents, the system will automatically retrieve relevant information and provide it to you as part of the user's message in a section labeled [Retrieved Knowledge].

If you see retrieved knowledge:
1. Use this information to answer the user's question
2. Cite sources when appropriate
3. Make sure your response is accurate and based on the retrieved information

If no knowledge is retrieved or if the question doesn't require specialized knowledge, answer based on your general knowledge.
"""
        elif storage_type == "local" and kb.get("local_path"):
            knowledge_base_instructions = f"""
You have access to a knowledge base with document storage on the local filesystem.
Document path: {kb.get("local_path")}
Document count: {kb.get("document_count", "Unknown")}

When users ask questions that require information from these documents, the system will automatically retrieve relevant information and provide it to you as part of the user's message in a section labeled [Retrieved Knowledge].

If you see retrieved knowledge:
1. Use this information to answer the user's question
2. Cite sources when appropriate
3. Make sure your response is accurate and based on the retrieved information

If no knowledge is retrieved or if the question doesn't require specialized knowledge, answer based on your general knowledge.
"""
    
    # Create the agent prompt
    prompt = f"""
You are {name}, an AI assistant.

{description}

{instruction}

{tools_description}

{knowledge_base_instructions}

Remember to act consistently with your configuration and purpose.

You can display images in the chat by including direct image URLs (e.g., https://cataas.com/cat) in your response. Do not use Markdown syntax for images, just include the URL directly.
"""
    
    return prompt.strip()