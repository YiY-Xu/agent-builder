import httpx
import json
import re
import logging
from typing import Dict, Any, Tuple, List, Optional
import asyncio

logger = logging.getLogger(__name__)

class ToolsService:
    """Service for processing tool calls detected in Claude responses."""
    
    TOOLS_PATTERN = r'\[TOOLS SELECTED\]\s*(.*?)\s*\[\/TOOLS SELECTED\]'
    
    def __init__(self):
        """Initialize the tools service."""
        self.http_client = httpx.AsyncClient(timeout=30.0)  # 30 second timeout
    
    async def process_tool_calls(self, claude_response: str) -> str:
        """
        Process any tool calls in the Claude response.
        
        Args:
            claude_response: The raw response from Claude
            
        Returns:
            The processed response with tool call sections replaced with results
        """
        logger.info("Processing potential tool calls in Claude response")
        
        # Check if the response contains tool calls
        if '[TOOLS SELECTED]' not in claude_response:
            logger.info("No tool calls detected in response")
            return claude_response
        
        # Extract all tool calls from the response
        tool_calls = self._extract_tool_calls(claude_response)
        if not tool_calls:
            logger.warning("Found [TOOLS SELECTED] tag but couldn't extract valid tool call data")
            return claude_response
        
        # Process each tool call and collect results
        processed_response = claude_response
        for tool_call_json, tool_call_section in tool_calls:
            try:
                # Execute the tool call
                result = await self._execute_tool_call(tool_call_json)
                
                # Replace the tool call section with the result
                result_section = self._format_tool_result(result, tool_call_json)
                processed_response = processed_response.replace(tool_call_section, result_section)
                
            except Exception as e:
                logger.error(f"Error processing tool call: {str(e)}", exc_info=True)
                error_section = self._format_tool_error(str(e), tool_call_json)
                processed_response = processed_response.replace(tool_call_section, error_section)
        
        return processed_response
    
    def _extract_tool_calls(self, response: str) -> List[Tuple[Dict[str, Any], str]]:
        """
        Extract all tool calls from the response.
        
        Args:
            response: Claude's response
            
        Returns:
            List of tuples containing (parsed tool call JSON, original tool call section)
        """
        tool_calls = []
        
        # Find all tool call sections
        matches = re.finditer(self.TOOLS_PATTERN, response, re.DOTALL)
        
        for match in matches:
            tool_call_section = match.group(0)  # The entire matched section
            tool_call_json_str = match.group(1)  # Just the JSON part
            
            try:
                # Parse the JSON
                tool_call_json = json.loads(tool_call_json_str)
                tool_calls.append((tool_call_json, tool_call_section))
                logger.info(f"Extracted tool call: {tool_call_json['action']} to {tool_call_json['endpoint']}")
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse tool call JSON: {str(e)}")
                logger.debug(f"Malformed JSON: {tool_call_json_str}")
        
        return tool_calls
    
    async def _execute_tool_call(self, tool_call: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a tool call based on the action type.
        
        Args:
            tool_call: Parsed tool call data
            
        Returns:
            The result of the tool call
        """
        action = tool_call.get("action")
        
        if action == "mcp":
            return await self._execute_mcp_call(tool_call)
        elif action == "tool":
            return await self._execute_regular_tool_call(tool_call)
        else:
            raise ValueError(f"Unknown action type: {action}")
    
    async def _execute_mcp_call(self, tool_call: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute an MCP server API call.
        
        Args:
            tool_call: Parsed tool call data
            
        Returns:
            The API response
        """
        endpoint = tool_call.get("endpoint")
        method = tool_call.get("method", "GET").upper()
        parameters = tool_call.get("parameters", {})
        
        if not endpoint:
            raise ValueError("MCP call missing required endpoint")
        
        logger.info(f"Executing MCP call: {method} {endpoint}")
        
        try:
            # Execute the appropriate HTTP method
            if method == "GET":
                response = await self.http_client.get(endpoint, params=parameters)
            elif method == "POST":
                response = await self.http_client.post(endpoint, json=parameters)
            elif method == "PUT":
                response = await self.http_client.put(endpoint, json=parameters)
            elif method == "DELETE":
                response = await self.http_client.delete(endpoint, params=parameters)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            # Handle non-2xx responses
            response.raise_for_status()
            
            # Parse and return the JSON response
            result = response.json()
            logger.info(f"MCP call successful: {endpoint}")
            return {
                "success": True,
                "status_code": response.status_code,
                "data": result
            }
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error in MCP call: {str(e)}")
            error_message = f"Error {e.response.status_code}"
            try:
                error_data = e.response.json()
                error_message = error_data.get("message", error_message)
            except:
                pass
                
            return {
                "success": False,
                "status_code": e.response.status_code,
                "error": error_message
            }
            
        except Exception as e:
            logger.error(f"Error in MCP call: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _execute_regular_tool_call(self, tool_call: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a regular tool call (non-MCP).
        
        Args:
            tool_call: Parsed tool call data
            
        Returns:
            The tool response
        """
        endpoint = tool_call.get("endpoint")
        method = tool_call.get("method", "GET").upper()
        parameters = tool_call.get("parameters", {})
        
        if not endpoint:
            raise ValueError("Tool call missing required endpoint")
        
        logger.info(f"Executing tool call: {method} {endpoint}")
        
        # This implementation is similar to MCP calls for now, but could be extended
        # to handle other types of tools in the future
        try:
            if method == "GET":
                response = await self.http_client.get(endpoint, params=parameters)
            elif method == "POST":
                response = await self.http_client.post(endpoint, json=parameters)
            else:
                raise ValueError(f"Unsupported HTTP method for tool: {method}")
            
            response.raise_for_status()
            
            # Parse and return the response
            result = response.json() if response.headers.get("content-type") == "application/json" else {"text": response.text}
            
            return {
                "success": True,
                "status_code": response.status_code,
                "data": result
            }
            
        except Exception as e:
            logger.error(f"Error in tool call: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    def _format_tool_result(self, result: Dict[str, Any], tool_call: Dict[str, Any]) -> str:
        """
        Format the tool result for inclusion in the response.
        
        Args:
            result: The result from the tool call
            tool_call: The original tool call
            
        Returns:
            Formatted tool result section
        """
        formatted_result = json.dumps(result, indent=2)
        action_type = tool_call.get("action", "unknown")
        endpoint = tool_call.get("endpoint", "unknown")
        
        return f"""[TOOL RESULT: {action_type.upper()} call to {endpoint}]
{formatted_result}
[/TOOL RESULT]"""
    
    def _format_tool_error(self, error: str, tool_call: Dict[str, Any]) -> str:
        """
        Format an error message for a failed tool call.
        
        Args:
            error: The error message
            tool_call: The original tool call
            
        Returns:
            Formatted error section
        """
        action_type = tool_call.get("action", "unknown")
        endpoint = tool_call.get("endpoint", "unknown")
        
        return f"""[TOOL ERROR: {action_type.upper()} call to {endpoint}]
The tool call failed with error: {error}
[/TOOL ERROR]"""
    
    async def close(self):
        """Close the HTTP client."""
        await self.http_client.aclose() 