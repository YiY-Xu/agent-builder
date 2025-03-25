import yaml
from typing import Dict, Any, List
import logging
import json
import asyncio
from app.services.mcp_services import load_mcp_servers
from datetime import datetime
logger = logging.getLogger(__name__)

async def generate_yaml_async(agent_config: Dict[str, Any]) -> str:
    """
    Generate a YAML configuration file from the agent configuration with async support for fetching MCP server details.
    
    Args:
        agent_config: Complete agent configuration
        
    Returns:
        Formatted YAML as a string
    """
    try:
        print("--------------------------------")
        print(json.dumps(agent_config))
        print("--------------------------------")
        # Create the YAML structure
        yaml_structure = {
            "name": agent_config.get("name", "Unnamed Agent"),
            "description": agent_config.get("description", ""),
            "version": "1.0.0",
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),  # This will be replaced with the current timestamp in frontend
        }
        
        # Get base instruction, removing any existing debug mode sections
        base_instruction = agent_config.get("instruction", "")
        # Remove any existing RESPONSE: sections that might interfere
        base_instruction = base_instruction.split("\nRESPONSE:\n")[0].strip()
        
        # Add debug mode instructions with proper formatting, but only if they don't already exist
        debug_mode_instructions = """
## Mode Instructions
If operating in debug mode, you must structure your responses as follows:

```
QUERY ANALYSIS:
[Explain why you decided to break down or not break down the user's query, and your reasoning process]

KNOWLEDGE SOURCES:
[List any knowledge sources you're using to inform your response]

TOOL SELECTION:
[Explain which tools you're using (if any) and why they are appropriate for this query]

MCP(Model Context Protocol) SERVERS SELECTION:
[Explain which MCP(Model Context Protocol) servers you're using (if any) and why they are appropriate for this query]

RESPONSE:
[Your actual response to the user]
```

In normal mode, provide only the response without the analytical sections."""

        # Add important general instructions
        important_instructions = """
## IMPORTANT:
- NEVER ask multiple questions in a single response. Ask ONLY ONE question at a time.
- If you need to gather multiple pieces of information, focus on the most important one first.
- After the user responds to your single question, you can ask the next question in your following response.
- When in debug mode, always show your reasoning process before providing your response.

## MCP(Model Context Protocol) SERVER USAGE:
- MCP(Model Context Protocol) servers offer specific capabilities that you can use.
- Each server has detailed information including service endpoints and capabilities.
- When a user query relates to a server's capabilities, analyze which specific endpoints would be most helpful.
- In debug mode, explain your reasoning for selecting specific MCP(Model Context Protocol) servers and endpoints.
- Reference the capability names when discussing your usage of MCP(Model Context Protocol) servers.
"""

        # Combine all instructions, checking for existing sections to avoid duplication
        full_instruction = base_instruction

        # Check if the instruction already has mode instructions
        if "## Mode Instructions" not in base_instruction:
            full_instruction += f"\n\n{debug_mode_instructions}"
        else:
            logger.info("Skipping adding mode instructions as they already exist in the base instruction")
            
        # Check if the instruction already has the important instructions
        if "## IMPORTANT:" not in base_instruction and "## MCP(Model Context Protocol) SERVER USAGE:" not in base_instruction:
            full_instruction += f"\n\n{important_instructions}"
        else:
            logger.info("Skipping adding important instructions as they already exist in the base instruction")
            
        yaml_structure["instruction"] = full_instruction
        
        # Add memory size and other config
        yaml_structure["config"] = {
            "memory_size": agent_config.get("memory_size", 10),
            "mode": agent_config.get("config", {}).get("mode", "normal"),  # Get mode from config object
            "claude_model": "claude-3-7-sonnet-20250219"  # Default model
        }
        
        # Add tools if any
        if "tools" in agent_config and agent_config["tools"]:
            yaml_structure["tools"] = []
            for tool in agent_config["tools"]:
                yaml_structure["tools"].append({
                    "name": tool.get("name"),
                    "endpoint": tool.get("endpoint")
                })
        
        # Add MCP servers if any
        if "mcp_servers" in agent_config and agent_config["mcp_servers"]:
            selected_server_names = agent_config["mcp_servers"]
            logger.info(f"Selected MCP server names: {selected_server_names}")
            
            # If the MCP servers are already objects with complete details, use them directly
            if (isinstance(selected_server_names, list) and 
                len(selected_server_names) > 0 and 
                isinstance(selected_server_names[0], dict) and 
                "name" in selected_server_names[0]):
                
                logger.info("MCP servers already have complete details, using them directly")
                yaml_structure["mcp_servers"] = selected_server_names
            else:
                # Otherwise, try to load complete details from the server list
                try:
                    # Convert to list of strings if not already
                    if isinstance(selected_server_names, list) and len(selected_server_names) > 0:
                        if not isinstance(selected_server_names[0], str):
                            selected_server_names = [str(server.get("name", server)) 
                                                    if isinstance(server, dict) else str(server) 
                                                    for server in selected_server_names]
                    
                    # Load all available MCP servers with their details
                    all_mcp_servers = await load_mcp_servers()
                    logger.info(f"Loaded {len(all_mcp_servers)} MCP servers")
                    
                    # Filter to get only the selected servers with their complete details
                    yaml_structure["mcp_servers"] = []
                    for server in all_mcp_servers:
                        if server["name"] in selected_server_names:
                            # Include the complete server details
                            yaml_structure["mcp_servers"].append(server)
                    
                    logger.info(f"Added {len(yaml_structure['mcp_servers'])} detailed MCP servers to YAML")
                except Exception as e:
                    # If there's an error loading MCP servers, use just the names as a fallback
                    logger.error(f"Error loading MCP servers: {e}. Using server names only.")
                    yaml_structure["mcp_servers"] = selected_server_names
        
        # Add knowledge base if available
        if "knowledge_base" in agent_config and agent_config["knowledge_base"]:
            knowledge_base = agent_config["knowledge_base"]            
            # Create knowledge base section in YAML
            # Don't initialize yaml_structure["knowledge_base"] = {} here since we might not use it
            
            # Handle different storage types
            if knowledge_base["storage_type"] == "local" and knowledge_base.get("index_info"):
                knowledge_section = {
                    "storage_type": "local",
                    "index_info": knowledge_base["index_info"],
                    "document_count": knowledge_base.get("document_count", 0)
                }
            elif knowledge_base["storage_type"] == "llamacloud" and knowledge_base.get("index_info"):
                knowledge_section = {
                    "storage_type": "llamacloud",
                    "index_info": knowledge_base.get("index_info"),
                    "document_count": knowledge_base.get("document_count", 0),
                    "project_name": knowledge_base.get("project_name") or "__PROJECT_NAME__"
                }
            else:
                # Default case if storage type is not recognized or missing required fields
                logger.warning(f"Unknown knowledge base storage type or missing required fields: {knowledge_base}")
                # Instead of returning early, just don't add the knowledge_base section
                knowledge_section = None
            
            # Only add knowledge_base if we have valid information
            if knowledge_section:
                yaml_structure["knowledge_base"] = knowledge_section
        
        # Convert to YAML
        yaml_content = yaml.dump(yaml_structure, sort_keys=False, default_flow_style=False)
        
        # Format the instruction to use the YAML pipe syntax
        if "instruction" in yaml_structure:
            # Replace the single line instruction with a proper multiline format
            instruction_line = f"instruction: {yaml_structure['instruction']}"
            multiline_instruction = f"instruction: |\n"
            
            # Split the instruction into lines and indent them
            for line in yaml_structure["instruction"].split("\n"):
                multiline_instruction += f"  {line}\n"
                
            # Replace in the generated YAML
            yaml_content = yaml_content.replace(instruction_line, multiline_instruction.rstrip())
        
        return yaml_content
        
    except Exception as e:
        logger.error(f"Error generating YAML: {e}")
        raise Exception(f"Error generating YAML: {str(e)}")

def generate_yaml(agent_config: Dict[str, Any]) -> str:
    """
    Generate a YAML configuration file from the agent configuration.
    This is a synchronous wrapper around the async version.
    
    Args:
        agent_config: Complete agent configuration
        
    Returns:
        Formatted YAML as a string
    """
    return asyncio.run(generate_yaml_async(agent_config))

if __name__ == "__main__":
    agent_config = {
        "name": "Travel Planner",
        "description": "Help users plan their trips",
        "instruction": "You are a professional travel agent with extensive knowledge of global destinations, travel logistics, and trip planning. When helping users plan trips:\n\n1. Begin by asking about their travel preferences, budget constraints, desired travel dates, and any special requirements (family-friendly, accessibility needs, etc.).\n\n2. Suggest appropriate destinations based on their interests, season, and budget. Provide balanced information about popular attractions, hidden gems, and practical considerations for each location.\n\n3. Create detailed itineraries when requested, including reasonable daily activities that account for travel time between locations.\n\n4. Offer specific recommendations for accommodations, transportation options, and dining that match the user's preferences and budget.\n\n5. Provide helpful travel tips about local customs, weather expectations, packing suggestions, and necessary documentation (visas, vaccinations, etc.).\n\n6. Alert users to any travel advisories, seasonal factors, or local events that might impact their experience.\n\n7. When making suggestions, explain your reasoning to help users make informed decisions.\n\n8. If you don't know specific details about a destination, acknowledge this and suggest reliable sources for further information.\n\n9. Be adaptable and patient if users change their preferences or requirements mid-planning.\n\n10. Always maintain a professional, courteous, and enthusiastic tone while providing practical and realistic travel advice.",
        "memory_size": 10,
        "tools":
        [],
        "mcp_servers":
        ["Car Rental Service", "Hotel Booking Service", "Flight Booking Service"],
        "knowledge_base":
        {
            "storage_type": "local",
            "document_count": 1,
            "file_names":
            [
                "Tesla_Model_3_Specifications.pdf"
            ]
        }
    }
    yaml_content = generate_yaml(agent_config)
    print(json.dumps(yaml_content))