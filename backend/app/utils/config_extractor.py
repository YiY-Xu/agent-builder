import re
import json
import logging
from typing import Union, List, Dict, Any, Optional

from app.models.response_models import ConfigUpdate

logger = logging.getLogger(__name__)

def extract_config_updates(response: str) -> Optional[Union[ConfigUpdate, List[ConfigUpdate]]]:
    """
    Extract configuration updates from Claude's response.
    
    Args:
        response: Claude's raw response text
        
    Returns:
        Either a single ConfigUpdate, a list of ConfigUpdate objects, or None if no updates found
    """
    # Pattern to match CONFIG_UPDATE blocks
    config_update_pattern = r'\[CONFIG_UPDATE\]([\s\S]*?)\[\/CONFIG_UPDATE\]'
    matches = re.findall(config_update_pattern, response)
    
    if not matches:
        return None
    
    try:
        # Parse the first match
        update_data = json.loads(matches[0].strip())
        
        # Check if it's a list or single object
        if isinstance(update_data, list):
            # Multiple updates
            updates = []
            for item in update_data:
                updates.append(ConfigUpdate(field=item["field"], value=item["value"]))
            return updates
        else:
            # Single update
            return ConfigUpdate(field=update_data["field"], value=update_data["value"])
            
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing CONFIG_UPDATE JSON: {e}")
        logger.error(f"Raw content: {matches[0]}")
        return None
        
    except KeyError as e:
        logger.error(f"Missing key in CONFIG_UPDATE: {e}")
        return None

def should_generate_yaml(response: str) -> bool:
    """
    Check if YAML should be generated based on Claude's response.
    
    Args:
        response: Claude's raw response text
        
    Returns:
        True if YAML should be generated, False otherwise
    """
    yaml_pattern = r'\[GENERATE_YAML\]([\s\S]*?)\[\/GENERATE_YAML\]'
    match = re.search(yaml_pattern, response)
    
    if match:
        value = match.group(1).strip().lower()
        return value in ['true', '1', 'yes']
        
    return False

def clean_response(response: str) -> str:
    """
    Remove special tags from Claude's response before sending to the client.
    
    Args:
        response: Claude's raw response text
        
    Returns:
        Cleaned response with special tags removed
    """
    # Remove CONFIG_UPDATE blocks
    cleaned = re.sub(r'\[CONFIG_UPDATE\][\s\S]*?\[\/CONFIG_UPDATE\]', '', response)
    
    # Remove GENERATE_YAML blocks
    cleaned = re.sub(r'\[GENERATE_YAML\][\s\S]*?\[\/GENERATE_YAML\]', '', cleaned)
    
    return cleaned.strip()