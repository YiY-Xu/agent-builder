from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Union


class ConfigUpdate(BaseModel):
    """Model representing a single update to the agent configuration."""
    field: str = Field(..., description="Field to update in the agent configuration")
    value: Any = Field(..., description="New value for the field")


class ChatResponse(BaseModel):
    """
    Model for chat response containing Claude's message and any configuration updates.
    Used when returning responses from the chat endpoint.
    """
    message: str = Field(..., description="Claude's response message")
    config_updates: Optional[Union[ConfigUpdate, List[ConfigUpdate]]] = Field(
        None, 
        description="Configuration updates extracted from Claude's response"
    )
    generate_yaml: bool = Field(
        False, 
        description="Flag indicating whether YAML should be generated"
    )


class YamlResponse(BaseModel):
    """
    Model for YAML generation response.
    Used when returning responses from the YAML generation endpoint.
    """
    yaml: str = Field(..., description="Generated YAML configuration")