"""
Dependency injection functions for FastAPI.
"""
import asyncio
from app.services.claude_service import ClaudeService
from app.services.knowledge_service import KnowledgeService
from app.services.tools_service import ToolsService


def get_claude_service():
    """
    Dependency function to get a ClaudeService instance.
    """
    return ClaudeService()


def get_knowledge_service():
    """
    Dependency function to get a KnowledgeService instance.
    """
    return KnowledgeService()


async def get_tools_service():
    """
    Dependency function to get a ToolsService instance.
    
    Ensures the HTTP client gets closed properly when the request completes.
    """
    service = ToolsService()
    try:
        yield service
    finally:
        # Don't use create_task here as it requires a running event loop
        # Simply await the close method directly
        await service.close() 