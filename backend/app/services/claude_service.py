import httpx
import json
from typing import List, Dict, Any, Optional, Union
import logging

from ..models.request_models import ChatMessage, AgentConfig
from ..config.settings import settings
from ..prompts.system_prompt import get_system_prompt

logger = logging.getLogger(__name__)

class ClaudeService:
    """Service for interacting with the Claude API."""
    
    def __init__(self):
        self.api_url = "https://api.anthropic.com/v1/messages"
        self.api_key = settings.CLAUDE_API_KEY
        self.model = settings.CLAUDE_MODEL
        self.headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01"
        }
    
    async def send_message(self, messages: List[ChatMessage], agent_config: Dict[str, Any]) -> str:
        """
        Send messages to Claude API and get a response.
        
        Args:
            messages: List of previous messages in the conversation
            agent_config: Current agent configuration
            
        Returns:
            Claude's response text
        """
        try:
            # Create system prompt with current agent configuration
            system_prompt = get_system_prompt(agent_config)
            
            # Log the request we're about to make
            logger.info(f"Sending request to Claude with {len(messages)} messages")
            
            # Format messages for Claude API
            formatted_messages = [
                {"role": msg.role, "content": msg.content}
                for msg in messages
            ]
            
            # Prepare request body
            request_body = {
                "model": self.model,
                "max_tokens": 4000,
                "messages": formatted_messages,
                "system": system_prompt
            }
            
            # Log the request body (but omit the full system prompt to keep logs clean)
            log_body = request_body.copy()
            log_body["system"] = "..." if system_prompt else ""
            logger.info(f"Request body: {json.dumps(log_body)}")
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.api_url,
                    headers=self.headers,
                    json=request_body,
                    timeout=30.0  # 30 second timeout
                )
                
                logger.info(f"Response status: {response.status_code}")
                
                # If we got an error response, log as much detail as possible
                if response.status_code >= 400:
                    logger.error(f"Error response: {response.text}")
                    response.raise_for_status()
                
                response_data = response.json()
                logger.info("Successfully received response from Claude")
                
                return response_data["content"][0]["text"]
                
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error occurred: {e}")
            error_detail = "Unknown error"
            try:
                error_detail = e.response.json().get("error", {}).get("message", "Unknown error")
            except:
                try:
                    error_detail = e.response.text
                except:
                    pass
            raise Exception(f"Claude API returned error: {error_detail}")
            
        except httpx.RequestError as e:
            logger.error(f"Request error occurred: {e}")
            raise Exception(f"Error communicating with Claude API: {str(e)}")
            
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            raise Exception(f"Unexpected error communicating with Claude API: {str(e)}")
    
    async def send_message_with_custom_prompt(self, messages: List[Union[ChatMessage, Dict[str, str]]], system_prompt: str) -> str:
        """
        Send messages to Claude API with a custom system prompt.
        
        Args:
            messages: List of previous messages in the conversation
            system_prompt: Custom system prompt to use
            
        Returns:
            Claude's response text
        """
        try:
            # Log the request we're about to make
            logger.info(f"Sending request to Claude with custom prompt and {len(messages)} messages")
            
            # Format messages for Claude API, handling both ChatMessage objects and dictionaries
            formatted_messages = []
            for msg in messages:
                if isinstance(msg, ChatMessage):
                    formatted_messages.append({
                        "role": msg.role,
                        "content": msg.content
                    })
                elif isinstance(msg, dict) and "role" in msg and "content" in msg:
                    formatted_messages.append({
                        "role": msg["role"],
                        "content": msg["content"]
                    })
                else:
                    logger.warning(f"Skipping malformed message: {msg}")
            
            # Prepare request body
            request_body = {
                "model": self.model,
                "max_tokens": 4000,
                "messages": formatted_messages,
                "system": system_prompt
            }
            
            logger.info(f"Using custom system prompt: {system_prompt[:100]}...")
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.api_url,
                    headers=self.headers,
                    json=request_body,
                    timeout=30.0  # 30 second timeout
                )
                
                logger.info(f"Response status: {response.status_code}")
                
                # If we got an error response, log as much detail as possible
                if response.status_code >= 400:
                    logger.error(f"Error response: {response.text}")
                    response.raise_for_status()
                
                response_data = response.json()
                logger.info("Successfully received response from Claude")
                
                return response_data["content"][0]["text"]
                
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error occurred: {e}")
            error_detail = "Unknown error"
            try:
                error_detail = e.response.json().get("error", {}).get("message", "Unknown error")
            except:
                try:
                    error_detail = e.response.text
                except:
                    pass
            raise Exception(f"Claude API returned error: {error_detail}")
            
        except httpx.RequestError as e:
            logger.error(f"Request error occurred: {e}")
            raise Exception(f"Error communicating with Claude API: {str(e)}")
            
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            raise Exception(f"Unexpected error communicating with Claude API: {str(e)}")