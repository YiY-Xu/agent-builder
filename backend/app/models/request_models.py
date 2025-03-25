from pydantic import BaseModel, Field, validator, field_validator
from typing import List, Dict, Any, Optional, Union


class ChatMessage(BaseModel):
    """Model representing a single message in a chat conversation."""
    role: str = Field(..., description="Role of the message sender (user or assistant)")
    content: str = Field(..., description="Content of the message")


class AgentTool(BaseModel):
    """Model representing a tool/API that the agent can use."""
    name: str = Field(..., description="Name of the tool")
    endpoint: str = Field(..., description="Endpoint URL for the tool")


class AgentConfig(BaseModel):
    """Model representing the configuration of an agent."""
    name: Optional[str] = Field(None, description="Name of the agent")
    description: Optional[str] = Field(None, description="Description of the agent's purpose")
    instruction: Optional[str] = Field(None, description="Detailed instructions for the agent")
    memory_size: int = Field(10, description="Number of messages to remember in conversation history")
    mode: str = Field("debug", description="Agent operating mode (normal or debug)")
    tools: List[AgentTool] = Field(default_factory=list, description="List of tools/APIs the agent can use")
    
    class Config:
        """Pydantic config"""
        extra = "ignore"  # Allow extra fields


class ChatRequest(BaseModel):
    """
    Model for chat request containing messages and current agent configuration.
    Used when sending messages to the chat endpoint.
    """
    messages: List[ChatMessage] = Field(..., description="List of previous messages in the conversation")
    agent_config: AgentConfig = Field(..., description="Current agent configuration")
    
    @field_validator('messages')
    @classmethod
    def validate_messages(cls, v):
        """Validate that there is at least one message"""
        if not v:
            raise ValueError('messages cannot be empty')
        return v

    class Config:
        """Pydantic config"""
        extra = "ignore"  # Allow extra fields