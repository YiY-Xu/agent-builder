from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any, Optional
import logging
import re
import yaml
from pydantic import BaseModel, Field
import json

from app.services.claude_service import ClaudeService
from app.services.knowledge_service import KnowledgeService
from app.services.yaml_service import generate_yaml_async
from app.services.tools_service import ToolsService
from app.models.request_models import ChatMessage
from app.dependencies import get_claude_service, get_knowledge_service, get_tools_service
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
    knowledge_service: KnowledgeService = Depends(get_knowledge_service),
    tools_service: ToolsService = Depends(get_tools_service)
):
    """
    Test an agent with a loaded YAML configuration
    
    - Takes a user message, agent configuration, and chat history
    - Creates a custom system prompt based on the agent configuration
    - Retrieves relevant information from knowledge base if applicable
    - Sends the message to Claude with the agent-specific prompt
    - If Claude makes tool calls, executes them and sends results back to Claude
    - Returns Claude's final response
    """
    try:
        logger.info(f"--------------------------------")
        logger.info(f"Initial agent config: {request.agent_config}")
        logger.info(f"--------------------------------")
        
        # Generate the complete YAML configuration from the agent config
        yaml_content = await generate_yaml_async(request.agent_config)
        logger.debug(f"Generated YAML configuration:\n{yaml_content}")
        
        # Parse the generated YAML back to a dict
        complete_config = yaml.safe_load(yaml_content)
        
        # Determine mode (normal/debug) from final YAML
        mode = complete_config.get("config", {}).get("mode", "normal")
        logger.info(f"Current mode from YAML config: {mode}")
        
        # Basic metadata
        name = complete_config.get("name", "AI Assistant")
        description = complete_config.get("description", "")
        instruction = complete_config.get("instruction", "")
        
        # Generate tools description using the tools service
        combined_tools_info = tools_service.generate_tools_description(complete_config)
        
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
        
        logger.info(f"--------------------------------")
        logger.info(f"Generated system prompt:\n{system_prompt}")
        logger.info(f"--------------------------------")
        
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
        
        # Check if the response contains tool calls
        if '[TOOLS SELECTED]' in claude_response:
            logger.info("Tool calls detected, processing and sending back to Claude")
            
            # Extract tool calls
            tool_calls = tools_service._extract_tool_calls(claude_response)
            
            if tool_calls:
                # Store the initial response
                initial_response = claude_response
                
                # Process tool calls
                results = []
                for tool_call_json, tool_call_section in tool_calls:
                    try:
                        # Execute the tool call
                        result = await tools_service._execute_tool_call(tool_call_json)
                        
                        # Format the result for inclusion
                        action_type = tool_call_json.get("action", "unknown")
                        endpoint = tool_call_json.get("endpoint", "unknown")
                        formatted_result = json.dumps(result, indent=2)
                        
                        results.append({
                            "tool_call": tool_call_json,
                            "result": result,
                            "formatted": f"[TOOL RESULT: {action_type.upper()} call to {endpoint}]\n{formatted_result}\n[/TOOL RESULT]"
                        })
                        
                    except Exception as e:
                        logger.error(f"Error processing tool call: {str(e)}", exc_info=True)
                        error_message = f"Error: {str(e)}"
                        
                        results.append({
                            "tool_call": tool_call_json,
                            "error": str(e),
                            "formatted": f"[TOOL ERROR: {tool_call_json.get('action', 'unknown').upper()} call to {tool_call_json.get('endpoint', 'unknown')}]\n{error_message}\n[/TOOL ERROR]"
                        })
                
                # Combine the results into a message to send back to Claude
                tool_results_message = "\n\n".join([r["formatted"] for r in results])
                
                # Add a follow-up message requesting Claude to continue with the results
                follow_up = """
Based on the tool results above, please provide your final answer to the user's query. 
Incorporate the data from the API results in your response.
"""
                
                # Send the results back to Claude
                messages.append(ChatMessage(
                    role="assistant",
                    content=claude_response
                ))
                
                messages.append(ChatMessage(
                    role="user",
                    content=f"{tool_results_message}\n\n{follow_up}"
                ))
                
                # Get Claude's follow-up response
                final_response = await claude_service.send_message_with_custom_prompt(
                    messages=messages,
                    system_prompt=system_prompt
                )
                
                logger.info(f"Claude's final response with tool results:\n{final_response}")
                
                # Create a combined response showing the process
                combined_response = f"""
I needed to gather some information to answer your question.

{initial_response}

Based on the information I gathered:

{final_response}
""".strip()
                
                return TestAgentResponse(message=combined_response)
            else:
                logger.warning("Tool call tags detected but no valid tool calls found")
        
        # If no tool calls or no valid ones, just return the original response
        return TestAgentResponse(message=claude_response)
    
    except Exception as e:
        logger.error(f"Error testing agent: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error testing agent: {str(e)}")


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