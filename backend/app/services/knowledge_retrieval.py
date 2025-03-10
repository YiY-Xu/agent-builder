import os
import logging
from typing import Dict, Any, List, Optional
import tempfile
import shutil

from llama_index.core import SimpleDirectoryReader, VectorStoreIndex, Document
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.indices.managed.llama_cloud import LlamaCloudIndex
from llama_index.core.node_parser import SentenceSplitter

from ..config.settings import settings

logger = logging.getLogger(__name__)

class KnowledgeRetrievalService:
    """Service for retrieving information from knowledge bases."""
    
    def __init__(self):
        self.llama_cloud_api_key = settings.LLAMA_CLOUD_API_KEY
        self.storage_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'knowledge_storage')
        
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
            storage_type = kb.get("storage_type", "llamacloud" if kb.get("index_name") else "local")
            
            logger.info(f"Querying {storage_type} knowledge base with query: {query}")
            
            if storage_type == "llamacloud" and kb.get("index_name"):
                # LlamaCloud retrieval
                return await self._query_llamacloud(query, kb)
            elif storage_type == "local" and kb.get("local_path"):
                # Local storage retrieval
                return await self._query_local_storage(query, kb)
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
            index_name = kb.get("index_name")
            project_name = kb.get("project_name", settings.LLAMA_CLOUD_PROJECT_NAME)
            
            if not index_name:
                logger.warning("Missing index name for LlamaCloud query")
                return None
                
            # Initialize LlamaCloud index
            index = LlamaCloudIndex(
                index_name=index_name,
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
    
    async def _query_local_storage(self, query: str, kb: Dict[str, Any]) -> Optional[str]:
        """
        Query local document storage for information.
        
        Args:
            query: User's query
            kb: Knowledge base configuration
            
        Returns:
            Retrieved context or None if retrieval fails
        """
        try:
            local_path = kb.get("local_path")
            
            if not local_path:
                logger.warning("Missing local path for local storage query")
                return None
            
            # Make sure the path exists
            agent_name = local_path.split('/')[-1]
            sanitized_name = agent_name.lower().replace(' ', '-')
            actual_path = os.path.join(self.storage_dir, sanitized_name)
            
            if not os.path.exists(actual_path):
                logger.warning(f"Local storage path doesn't exist: {actual_path}")
                return None
            
            # Load documents
            documents = SimpleDirectoryReader(actual_path).load_data()
            
            if not documents:
                logger.warning(f"No documents found in {actual_path}")
                return None
                
            # Create index
            index = VectorStoreIndex.from_documents(documents)
            
            # Create query engine and query
            query_engine = index.as_query_engine(similarity_top_k=5)
            response = query_engine.query(query)
            
            # Log and return response
            logger.info(f"Retrieved information from local storage: {str(response)[:200]}...")
            
            # Format the response and source nodes for Claude
            formatted_response = self._format_retrieved_context(response)
            return formatted_response
            
        except Exception as e:
            logger.error(f"Error querying local storage: {str(e)}", exc_info=True)
            return None
    
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
                    if hasattr(node, 'node') and hasattr(node.node, 'metadata'):
                        source = node.node.metadata.get('file_name', f"Source {i+1}")
                        formatted_text += f"- {source}\n"
            
            return formatted_text
            
        except Exception as e:
            logger.error(f"Error formatting retrieved context: {str(e)}", exc_info=True)
            return str(response)