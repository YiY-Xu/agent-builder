"""
Dependency injection functions for FastAPI.
"""
from app.services.claude_service import ClaudeService
from app.services.knowledge_service import KnowledgeService


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