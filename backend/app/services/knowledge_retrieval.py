import os
import json
import logging
from typing import Dict, Any, List, Optional
import tempfile
import shutil

from llama_index.core import SimpleDirectoryReader, VectorStoreIndex, Document, StorageContext
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.indices.managed.llama_cloud import LlamaCloudIndex
from llama_index.core.node_parser import SentenceSplitter

from app.config.settings import settings

logger = logging.getLogger(__name__)

class KnowledgeRetrievalService:
    """Service for retrieving information from knowledge bases."""
    
    def __init__(self):
        self.llama_cloud_api_key = settings.LLAMA_CLOUD_API_KEY
        self.storage_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'knowledge_storage')
        self.permanent_storage_dir = self.storage_dir  # Alias for compatibility with query methods
        
    async def query_knowledge_base(self, query: str, agent_config: Dict[str, Any]) -> Optional[str]:
        """
        Query the knowledge base for relevant information.
        
        Args:
            query: User's query
            agent_config: Agent configuration including knowledge base info
            
        Returns:
            Retrieved context or None if retrieval fails
        """
        try:
            # Check if knowledge base is configured
            if "knowledge_base" not in agent_config:
                logger.info("No knowledge base configured for this agent")
                return None
                
            kb = agent_config["knowledge_base"]
            storage_type = kb.get("storage_type", "llamacloud" if kb.get("index_info") else "local")
            
            logger.info(f"Querying {storage_type} knowledge base with query: {query}")
            
            if storage_type == "llamacloud" and kb.get("index_info"):
                # LlamaCloud retrieval
                return await self._query_llamacloud(query, kb)
            elif storage_type == "local" and kb.get("local_path"):
                # Local storage retrieval
                return await self._query_local_index(query, kb)
            else:
                logger.warning(f"Unknown knowledge base configuration: {kb}")
                return None
                
        except Exception as e:
            logger.error(f"Error querying knowledge base: {str(e)}", exc_info=True)
            return f"Error querying knowledge base: {str(e)}"
    
    async def _query_llamacloud(self, query: str, kb: Dict[str, Any]) -> Optional[str]:
        """
        Query LlamaCloud index for information.
        
        Args:
            query: User's query
            kb: Knowledge base configuration
            
        Returns:
            Retrieved context or None if retrieval fails
        """
        try:
            index_info = kb.get("index_info")
            project_name = kb.get("project_name", settings.LLAMA_CLOUD_PROJECT_NAME)
            
            if not index_info:
                logger.warning("Missing index info for LlamaCloud query")
                return None
                
            # Initialize LlamaCloud index
            index = LlamaCloudIndex(
                index_name=index_info,
                project_name=project_name,
                api_key=self.llama_cloud_api_key
            )
            
            # Create query engine and query
            query_engine = index.as_query_engine(similarity_top_k=5)
            response = query_engine.query(query)
            
            # Log and return response
            logger.info(f"Retrieved information from LlamaCloud: {str(response)[:200]}...")
            
            # Format the response and source nodes for Claude
            formatted_response = self._format_retrieved_context(response)
            return formatted_response
            
        except Exception as e:
            logger.error(f"Error querying LlamaCloud: {str(e)}", exc_info=True)
            return None
    
    async def _query_local_index(self, query: str, kb: Dict[str, Any]) -> Optional[str]:
        """
        Query the local index for information.
        
        Args:
            query: User's query
            kb: Knowledge base configuration
            
        Returns:
            Retrieved context or None if retrieval fails
        """
        try:
            local_path = kb.get("local_path")
            
            if not local_path:
                logger.warning("Missing local path for local index query")
                return None
            
            # Get agent name from path
            agent_name = os.path.basename(local_path)
            
            # Check if index exists
            index_path = os.path.join(local_path, "index")
            if not os.path.exists(index_path):
                logger.warning(f"No index found at {index_path}")
                return None
            
            # Load the index from storage
            logger.info(f"Loading index for agent {agent_name} from {index_path}")
            storage_context = StorageContext.from_defaults(persist_dir=index_path)
            index = VectorStoreIndex.from_storage(storage_context)
            
            # Create query engine
            query_engine = index.as_query_engine(similarity_top_k=5)
            
            # Execute query
            logger.info(f"Executing query for agent {agent_name}: {query}")
            response = query_engine.query(query)
            
            # Format and return response
            logger.info(f"Retrieved information from local index: {str(response)[:200]}...")
            formatted_response = self._format_retrieved_context(response)
            return formatted_response
            
        except Exception as e:
            logger.error(f"Error querying local index: {str(e)}", exc_info=True)
            return None
    
    def _sanitize_name(self, name: str) -> str:
        """
        Sanitize agent name for use in index name and directory names.
        
        Args:
            name: Original agent name
            
        Returns:
            Sanitized name suitable for index
        """
        # Replace spaces with hyphens and remove special characters
        sanitized = name.lower().replace(" ", "-")
        sanitized = ''.join(c for c in sanitized if c.isalnum() or c == '-')
        
        # Limit length
        if len(sanitized) > 20:
            sanitized = sanitized[:20]
            
        # Ensure it doesn't start or end with hyphen
        sanitized = sanitized.strip('-')
        
        # If empty after sanitization, use default
        if not sanitized:
            sanitized = "agent"
            
        return sanitized
    
    def _format_retrieved_context(self, response) -> str:
        """
        Format the retrieved context for Claude, including source information.
        
        Args:
            response: Response from the query engine
            
        Returns:
            Formatted context string
        """
        try:
            formatted_text = "Here is the retrieved information from the knowledge base:\n\n"
            
            # Add the response text
            formatted_text += str(response) + "\n\n"
            
            # Add source information if available
            if hasattr(response, 'source_nodes') and response.source_nodes:
                formatted_text += "Sources:\n"
                for i, node in enumerate(response.source_nodes):
                    source = f"Source {i+1}"
                    
                    # Try different ways to access metadata
                    if hasattr(node, 'metadata') and node.metadata:
                        source = node.metadata.get('file_name', source)
                    elif hasattr(node, 'node') and hasattr(node.node, 'metadata'):
                        source = node.node.metadata.get('file_name', source)
                    
                    formatted_text += f"- {source}\n"
            
            return formatted_text
            
        except Exception as e:
            logger.error(f"Error formatting retrieved context: {str(e)}", exc_info=True)
            return str(response)