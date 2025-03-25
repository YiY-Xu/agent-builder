from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import logging

from app.services.claude_service import ClaudeService
from app.models.request_models import ChatRequest
from app.models.response_models import ChatResponse
from app.utils.config_extractor import extract_config_updates, should_generate_yaml, clean_response
from app.services.yaml_service import generate_yaml as yaml_generator
from app.dependencies import get_claude_service

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api",
    tags=["chat"],
    responses={404: {"description": "Not found"}},
)

@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    claude_service: ClaudeService = Depends(get_claude_service)
):
    """
    Process a chat message with Claude and return the response with any configuration updates.
    
    - Takes a list of previous messages and the current agent configuration
    - Forwards to Claude API
    - Extracts configuration updates from Claude's response
    - Returns cleaned response and any extracted updates
    """
    try:
        # Debug output - log request details
        logger.info(f"Received request with {len(request.messages)} messages")
        logger.info(f"Agent config: {request.agent_config}")
        
        # Call Claude API
        claude_response = await claude_service.send_message(
            messages=request.messages,
            agent_config=request.agent_config
        )
        
        # Extract configuration updates from response
        config_updates = extract_config_updates(claude_response)
        
        # Check if YAML should be generated
        generate_yaml = should_generate_yaml(claude_response)
        
        # Clean the response (remove special tags)
        cleaned_response = clean_response(claude_response)
        
        logger.info(f"Generated response with config updates: {config_updates}")
        
        return ChatResponse(
            message=cleaned_response,
            config_updates=config_updates,
            generate_yaml=generate_yaml
        )
    
    except Exception as e:
        logger.error(f"Error processing chat request: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error communicating with Claude API: {str(e)}")

@router.post("/yaml")
async def generate_yaml(request: Dict[str, Any]):
    """
    Generate a YAML configuration file from the current agent state.
    
    - Takes the complete agent configuration
    - Returns formatted YAML as a string
    """
    try:
        yaml_content = yaml_generator(request)
        return {"yaml": yaml_content}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating YAML: {str(e)}")