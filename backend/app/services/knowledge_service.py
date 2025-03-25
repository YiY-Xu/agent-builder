import os
import tempfile
import shutil
import logging
import json
from typing import List, Dict, Any, Optional
import uuid
from fastapi import UploadFile

# Import Llama Index components
from llama_index.core import SimpleDirectoryReader, VectorStoreIndex, StorageContext, load_index_from_storage
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.indices.managed.llama_cloud import LlamaCloudIndex
from llama_index.core.node_parser import SentenceSplitter

from app.config.settings import settings

logger = logging.getLogger(__name__)

class KnowledgeService:
    """Service for handling document uploads, knowledge indexing, and retrieval."""
    
    def __init__(self):
        self.llama_cloud_api_key = settings.LLAMA_CLOUD_API_KEY
        self.index_name_prefix = settings.LLAMA_CLOUD_INDEX_PREFIX
        self.project_name = settings.LLAMA_CLOUD_PROJECT_NAME
        
        # Paths for uploads and local storage
        self.temp_upload_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'temp_uploads')
        self.permanent_storage_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'knowledge_storage')
        
        # Create directories if they don't exist
        os.makedirs(self.temp_upload_dir, exist_ok=True)
        os.makedirs(self.permanent_storage_dir, exist_ok=True)
        
    async def upload_file(self, file: UploadFile, agent_name: str) -> Dict[str, Any]:
        """
        Upload a single file to temporary storage.
        
        Args:
            file: FastAPI UploadFile object
            agent_name: Name of the agent
            
        Returns:
            Dictionary with upload result and file information
        """
        try:
            # Create agent directory if it doesn't exist
            agent_dir = os.path.join(self.temp_upload_dir, self._sanitize_name(agent_name))
            os.makedirs(agent_dir, exist_ok=True)
            
            # Get the file content
            file_content = await file.read()
            
            # Create the file path
            file_path = os.path.join(agent_dir, file.filename)
            
            # Check if file already exists
            if os.path.exists(file_path):
                # Add timestamp to make filename unique
                filename_parts = os.path.splitext(file.filename)
                new_filename = f"{filename_parts[0]}_{uuid.uuid4().hex[:6]}{filename_parts[1]}"
                file_path = os.path.join(agent_dir, new_filename)
            else:
                new_filename = file.filename
            
            # Write the content to the file
            with open(file_path, "wb") as f:
                f.write(file_content)
                
            logger.info(f"Saved file {new_filename} for agent {agent_name}")
            
            # Update metadata file
            self._update_metadata(agent_name, new_filename)
            
            return {
                "success": True,
                "file_name": new_filename,
                "agent_name": agent_name
            }
                
        except Exception as e:
            logger.error(f"Error uploading file: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    def _update_metadata(self, agent_name: str, file_name: str) -> None:
        """
        Update the metadata file with the new uploaded file.
        
        Args:
            agent_name: Name of the agent
            file_name: Name of the uploaded file
        """
        sanitized_name = self._sanitize_name(agent_name)
        metadata_path = os.path.join(self.temp_upload_dir, sanitized_name, "metadata.json")
        
        # Initialize metadata
        if os.path.exists(metadata_path):
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
        else:
            metadata = {
                "agent_name": agent_name,
                "files": [],
                "index_info": None,
                "project_name": self.project_name,
                "storage_type": None,
                "local_path": None
            }
        
        # Add file if not already in list
        if file_name not in metadata["files"]:
            metadata["files"].append(file_name)
        
        # Write updated metadata
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
    
    def get_uploaded_files(self, agent_name: str) -> Dict[str, Any]:
        """
        Get list of uploaded files for an agent.
        
        Args:
            agent_name: Name of the agent
            
        Returns:
            Dictionary with list of files and index status
        """
        try:
            sanitized_name = self._sanitize_name(agent_name)
            agent_dir = os.path.join(self.temp_upload_dir, sanitized_name)
            
            if not os.path.exists(agent_dir):
                return {
                    "agent_name": agent_name,
                    "files": [],
                    "index_info": None,
                    "project_name": self.project_name,
                    "storage_type": None,
                    "local_path": None,
                    "has_index": False
                }
            
            metadata_path = os.path.join(agent_dir, "metadata.json")
            
            if os.path.exists(metadata_path):
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
                    
                return {
                    "agent_name": agent_name,
                    "files": metadata.get("files", []),
                    "index_info": metadata.get("index_info"),
                    "project_name": metadata.get("project_name", self.project_name),
                    "storage_type": metadata.get("storage_type"),
                    "local_path": metadata.get("local_path"),
                    "has_index": metadata.get("index_info") is not None or metadata.get("local_path") is not None
                }
            else:
                # No metadata file, get files from directory
                files = [f for f in os.listdir(agent_dir) if os.path.isfile(os.path.join(agent_dir, f)) and f != "metadata.json"]
                
                return {
                    "agent_name": agent_name,
                    "files": files,
                    "index_info": None,
                    "project_name": self.project_name,
                    "storage_type": None,
                    "local_path": None,
                    "has_index": False
                }
                
        except Exception as e:
            logger.error(f"Error getting uploaded files: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    def remove_file(self, agent_name: str, file_name: str) -> Dict[str, Any]:
        """
        Remove a file from an agent's uploaded files.
        
        Args:
            agent_name: Name of the agent
            file_name: Name of the file to remove
            
        Returns:
            Dictionary with result information
        """
        try:
            sanitized_name = self._sanitize_name(agent_name)
            agent_dir = os.path.join(self.temp_upload_dir, sanitized_name)
            file_path = os.path.join(agent_dir, file_name)
            
            if not os.path.exists(file_path):
                return {
                    "success": False,
                    "error": f"File {file_name} not found for agent {agent_name}"
                }
            
            # Remove file
            os.remove(file_path)
            
            # Update metadata
            metadata_path = os.path.join(agent_dir, "metadata.json")
            if os.path.exists(metadata_path):
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
                
                if file_name in metadata.get("files", []):
                    metadata["files"].remove(file_name)
                
                # If index or local path exists, mark it as outdated
                if metadata.get("index_info") or metadata.get("local_path"):
                    metadata["outdated"] = True
                
                with open(metadata_path, 'w') as f:
                    json.dump(metadata, f, indent=2)
            
            return {
                "success": True,
                "message": f"File {file_name} removed successfully"
            }
                
        except Exception as e:
            logger.error(f"Error removing file: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    #
    # Index Creation Methods
    #
            
    async def create_llama_index(self, agent_name: str) -> Dict[str, Any]:
        """
        Create a LlamaCloud index from previously uploaded files.
        
        Args:
            agent_name: Name of the agent
            
        Returns:
            Dictionary with index information
        """
        try:
            sanitized_name = self._sanitize_name(agent_name)
            agent_dir = os.path.join(self.temp_upload_dir, sanitized_name)
            
            if not os.path.exists(agent_dir):
                return {
                    "success": False,
                    "error": f"No files found for agent {agent_name}"
                }
            
            metadata_path = os.path.join(agent_dir, "metadata.json")
            
            if os.path.exists(metadata_path):
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
                
                # Check if index already exists
                if metadata.get("index_info") or metadata.get("index_name"):
                    index_info = metadata.get("index_info") or metadata.get("index_name")
                    return {
                        "success": True,
                        "storage_type": "llamacloud",
                        "index_info": index_info,
                        "project_name": metadata.get("project_name", self.project_name),
                        "document_count": len(metadata.get("files", [])),
                        "file_names": metadata.get("files", []),
                        "message": "Index already exists"
                    }
                
                # Check if there are files to index
                if not metadata.get("files", []):
                    return {
                        "success": False,
                        "error": f"No files uploaded for agent {agent_name}"
                    }
            else:
                # No metadata file, get files from directory
                files = [f for f in os.listdir(agent_dir) if os.path.isfile(os.path.join(agent_dir, f)) and f != "metadata.json"]
                
                if not files:
                    return {
                        "success": False,
                        "error": f"No files found for agent {agent_name}"
                    }
                    
                # Create metadata file
                metadata = {
                    "agent_name": agent_name,
                    "files": files,
                    "index_info": None,
                    "project_name": self.project_name,
                    "storage_type": None,
                    "local_path": None
                }
                
                with open(metadata_path, 'w') as f:
                    json.dump(metadata, f, indent=2)
            
            # Create index name
            index_info = f"{self.index_name_prefix}-{sanitized_name}-{uuid.uuid4().hex[:8]}"
            
            logger.info(f"Creating LlamaCloud index: {index_info} with {len(metadata['files'])} documents")
            
            # Load documents from the directory
            documents = SimpleDirectoryReader(agent_dir, recursive=False).load_data()
            logger.info(f"Loaded {len(documents)} documents")
            
            # Create the index and upload documents
            index = LlamaCloudIndex.from_documents(
                documents, 
                index_info,
                project_name=self.project_name,
                api_key=self.llama_cloud_api_key
            )
            
            logger.info(f"Successfully created index {index_info}")
            
            # Update metadata with index name
            metadata["index_info"] = index_info
            metadata["project_name"] = self.project_name
            metadata["storage_type"] = "llamacloud"
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            # Return information about the upload
            return {
                "success": True,
                "storage_type": "llamacloud",
                "index_info": index_info,
                "project_name": self.project_name,
                "document_count": len(documents),
                "file_names": metadata["files"]
            }
                
        except Exception as e:
            logger.error(f"Error creating index: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    async def create_local_index(self, agent_name: str) -> Dict[str, Any]:
        """
        Save uploaded files to a permanent local storage directory and create a LlamaIndex index.
        
        Args:
            agent_name: Name of the agent
            
        Returns:
            Dictionary with local storage and index information
        """
        try:
            sanitized_name = self._sanitize_name(agent_name)
            temp_agent_dir = os.path.join(self.temp_upload_dir, sanitized_name)
            
            if not os.path.exists(temp_agent_dir):
                return {
                    "success": False,
                    "error": f"No files found for agent {agent_name}"
                }
            
            # Create permanent storage directory for this agent
            local_path = os.path.join(self.permanent_storage_dir, sanitized_name)
            os.makedirs(local_path, exist_ok=True)
            
            # Create index directory for this agent
            index_path = os.path.join(local_path, "index")
            os.makedirs(index_path, exist_ok=True)
            
            # Get metadata
            metadata_path = os.path.join(temp_agent_dir, "metadata.json")
            
            if os.path.exists(metadata_path):
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
                
                # Check if there are files to save
                if not metadata.get("files", []):
                    return {
                        "success": False,
                        "error": f"No files uploaded for agent {agent_name}"
                    }
                
                # Copy files to permanent storage
                file_count = 0
                for file_name in metadata.get("files", []):
                    source_path = os.path.join(temp_agent_dir, file_name)
                    dest_path = os.path.join(local_path, file_name)
                    
                    if os.path.exists(source_path):
                        shutil.copy2(source_path, dest_path)
                        file_count += 1
                
                # Update metadata
                metadata["storage_type"] = "local"
                metadata["local_path"] = local_path
                
                # Create LlamaIndex index from the documents
                logger.info(f"Creating local index for agent {agent_name}")
                
                # Load documents from the permanent directory
                documents = SimpleDirectoryReader(local_path, recursive=False).load_data()
                logger.info(f"Loaded {len(documents)} documents for indexing")
                
                # Create the index 
                index = VectorStoreIndex.from_documents(documents)
                
                # Persist the index to disk
                index.storage_context.persist(persist_dir=index_path)
                
                # Update metadata with index information
                metadata["index_info"] = index_path
                metadata["has_index"] = True
                metadata["index_document_count"] = len(documents)
                
                # Save updated metadata to both temp and permanent directories
                with open(metadata_path, 'w') as f:
                    json.dump(metadata, f, indent=2)
                
                perm_metadata_path = os.path.join(local_path, "metadata.json")
                with open(perm_metadata_path, 'w') as f:
                    json.dump(metadata, f, indent=2)
                
                logger.info(f"Saved {file_count} files to local storage at {local_path}")
                logger.info(f"Created index with {len(documents)} documents at {index_path}")
                
                return {
                    "success": True,
                    "storage_type": "local",
                    "local_path": local_path,
                    "index_info": index_path,
                    "document_count": file_count,
                    "index_document_count": len(documents),
                    "file_names": metadata.get("files", []),
                    "has_index": True
                }
            else:
                # No metadata file, get files from directory
                files = [f for f in os.listdir(temp_agent_dir) if os.path.isfile(os.path.join(temp_agent_dir, f)) and f != "metadata.json"]
                
                if not files:
                    return {
                        "success": False,
                        "error": f"No files found for agent {agent_name}"
                    }
                
                # Copy files to permanent storage
                file_count = 0
                for file_name in files:
                    source_path = os.path.join(temp_agent_dir, file_name)
                    dest_path = os.path.join(local_path, file_name)
                    
                    shutil.copy2(source_path, dest_path)
                    file_count += 1
                    
                # Create LlamaIndex index from the documents
                logger.info(f"Creating local index for agent {agent_name}")
                
                # Load documents from the permanent directory
                documents = SimpleDirectoryReader(local_path, recursive=False).load_data()
                logger.info(f"Loaded {len(documents)} documents for indexing")
                
                # Create the index
                index = VectorStoreIndex.from_documents(documents)
                
                # Persist the index to disk
                index.storage_context.persist(persist_dir=index_path)
                
                # Create metadata
                metadata = {
                    "agent_name": agent_name,
                    "files": files,
                    "storage_type": "local",
                    "local_path": local_path,
                    "project_name": None,
                    "index_info": index_path,
                    "has_index": True,
                    "index_document_count": len(documents)
                }
                
                # Save metadata to both directories
                temp_metadata_path = os.path.join(temp_agent_dir, "metadata.json")
                with open(temp_metadata_path, 'w') as f:
                    json.dump(metadata, f, indent=2)
                
                perm_metadata_path = os.path.join(local_path, "metadata.json")
                with open(perm_metadata_path, 'w') as f:
                    json.dump(metadata, f, indent=2)
                
                logger.info(f"Saved {file_count} files to local storage at {local_path}")
                logger.info(f"Created index with {len(documents)} documents at {index_path}")
                
                return {
                    "success": True,
                    "storage_type": "local",
                    "local_path": local_path,
                    "index_info": index_path,
                    "document_count": file_count,
                    "index_document_count": len(documents),
                    "file_names": files,
                    "has_index": True
                }
        except Exception as e:
            logger.error(f"Error creating local index: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    #
    # Query Methods
    #

    async def query_local_index(self, agent_name: str, query_text: str, similarity_top_k: int = 3) -> Dict[str, Any]:
        """
        Query the local index for an agent.
        
        Args:
            agent_name: Name of the agent
            query_text: The query to search for
            similarity_top_k: Number of top similar results to return
            
        Returns:
            Dictionary with query results including relevant text snippets
        """
        try:
            sanitized_name = self._sanitize_name(agent_name)
            perm_agent_dir = os.path.join(self.permanent_storage_dir, sanitized_name)
            
            if not os.path.exists(perm_agent_dir):
                return {
                    "success": False,
                    "error": f"No permanent storage found for agent {agent_name}"
                }
            
            # Get metadata
            metadata_path = os.path.join(perm_agent_dir, "metadata.json")
            
            if not os.path.exists(metadata_path):
                return {
                    "success": False,
                    "error": f"No metadata found for agent {agent_name}"
                }
                
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
            
            # Check if index exists
            index_path = metadata.get("index_info")
            if not index_path or not os.path.exists(index_path):
                return {
                    "success": False,
                    "error": f"No index found for agent {agent_name}, please create an index first"
                }
            
            # Load the index from storage
            logger.info(f"Loading index for agent {agent_name} from {index_path}")
            storage_context = StorageContext.from_defaults(persist_dir=index_path)
            index = load_index_from_storage(storage_context)
            
            # Create query engine
            query_engine = index.as_query_engine(similarity_top_k=similarity_top_k)
            
            # Execute query
            logger.info(f"Executing query for agent {agent_name}: {query_text}")
            response = query_engine.query(query_text)
            
            # Extract source nodes for context
            source_texts = []
            source_documents = []
            
            if hasattr(response, 'source_nodes'):
                for node in response.source_nodes:
                    source_texts.append(node.text)
                    if hasattr(node, 'metadata') and node.metadata:
                        source_doc = {
                            "text": node.text[:200] + "..." if len(node.text) > 200 else node.text,
                            "file_name": node.metadata.get("file_name", "Unknown"),
                            "score": node.score if hasattr(node, "score") else None
                        }
                        source_documents.append(source_doc)
            
            return {
                "success": True,
                "agent_name": agent_name,
                "query": query_text,
                "response": str(response),
                "source_texts": source_texts,
                "source_documents": source_documents,
                "raw_response_object": response
            }
            
        except Exception as e:
            logger.error(f"Error querying local index: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    async def query_llama_cloud_index(self, agent_name: str, query_text: str, similarity_top_k: int = 3) -> Dict[str, Any]:
        """
        Query the LlamaCloud index for an agent.
        
        Args:
            agent_name: Name of the agent
            query_text: The query to search for
            similarity_top_k: Number of top similar results to return
            
        Returns:
            Dictionary with query results including relevant text snippets
        """
        try:
            sanitized_name = self._sanitize_name(agent_name)
            temp_agent_dir = os.path.join(self.temp_upload_dir, sanitized_name)
            
            if not os.path.exists(temp_agent_dir):
                return {
                    "success": False,
                    "error": f"No data found for agent {agent_name}"
                }
            
            # Get metadata
            metadata_path = os.path.join(temp_agent_dir, "metadata.json")
            
            if not os.path.exists(metadata_path):
                return {
                    "success": False,
                    "error": f"No metadata found for agent {agent_name}"
                }
                
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
            
            # Check if index exists
            index_info = metadata.get("index_info") or metadata.get("index_name")
            if not index_info:
                return {
                    "success": False,
                    "error": f"No LlamaCloud index found for agent {agent_name}, please create an index first"
                }
            
            # Load the index from LlamaCloud
            logger.info(f"Loading LlamaCloud index for agent {agent_name}: {index_info}")
            
            # Access the index from LlamaCloud
            index = LlamaCloudIndex(
                index_name=index_info,
                project_name=metadata.get("project_name", self.project_name),
                api_key=self.llama_cloud_api_key
            )
            
            # Create query engine
            query_engine = index.as_query_engine(
                similarity_top_k=similarity_top_k
            )
            
            # Execute query
            logger.info(f"Executing query for agent {agent_name} on LlamaCloud index: {query_text}")
            response = query_engine.query(query_text)
            
            # Extract source nodes for context
            source_texts = []
            source_documents = []
            
            if hasattr(response, 'source_nodes'):
                for node in response.source_nodes:
                    source_texts.append(node.text)
                    if hasattr(node, 'metadata') and node.metadata:
                        source_doc = {
                            "text": node.text[:200] + "..." if len(node.text) > 200 else node.text,
                            "file_name": node.metadata.get("file_name", "Unknown"),
                            "score": node.score if hasattr(node, "score") else None
                        }
                        source_documents.append(source_doc)
            
            return {
                "success": True,
                "agent_name": agent_name,
                "query": query_text,
                "response": str(response),
                "source_texts": source_texts,
                "source_documents": source_documents,
                "raw_response_object": response
            }
            
        except Exception as e:
            logger.error(f"Error querying LlamaCloud index: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    async def query_agent_knowledge(self, agent_name: str, storage_type: str, query_text: str, similarity_top_k: int = 3) -> Dict[str, Any]:
        """
        Query the appropriate index for an agent based on what's available.
        This method will automatically determine whether to use a local index or LlamaCloud index.
        
        Args:
            agent_name: Name of the agent
            query_text: The query to search for
            similarity_top_k: Number of top similar results to return
            
        Returns:
            Dictionary with query results
        """
        try:
            sanitized_name = self._sanitize_name(agent_name)
            
            # First check permanent storage for metadata
            perm_agent_dir = os.path.join(self.permanent_storage_dir, sanitized_name)
            perm_metadata_path = os.path.join(perm_agent_dir, "metadata.json")
            
            # If permanent storage exists with an index, use that first
            if storage_type == "local" and os.path.exists(perm_metadata_path):
                with open(perm_metadata_path, 'r') as f:
                    metadata = json.load(f)
                    
                if metadata.get("index_info") and os.path.exists(metadata.get("index_info")):
                    # Use local index
                    return await self.query_local_index(agent_name, query_text, similarity_top_k)
            
            else: # Otherwise check for a LlamaCloud index
                temp_agent_dir = os.path.join(self.temp_upload_dir, sanitized_name)
                temp_metadata_path = os.path.join(temp_agent_dir, "metadata.json")
                
                if os.path.exists(temp_metadata_path):
                    with open(temp_metadata_path, 'r') as f:
                        metadata = json.load(f)
                        
                    if metadata.get("index_info"):
                        # Use LlamaCloud index
                        return await self.query_llama_cloud_index(agent_name, query_text, similarity_top_k)
            
            # No index found
            return {
                "success": False,
                "error": f"No index found for agent {agent_name}, please create an index first"
            }
            
        except Exception as e:
            logger.error(f"Error querying agent knowledge: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
            
    async def query_knowledge_base(self, query: str, agent_config: Dict[str, Any], similarity_top_k: int = 1, relevance_threshold: float = 0.7) -> Optional[str]:
        """
        Query the knowledge base for relevant information.
        
        Args:
            query: User's query
            agent_config: Agent configuration including knowledge base info
            similarity_top_k: Number of top relevant documents to retrieve (default 1)
            relevance_threshold: Minimum similarity score threshold for considering a document relevant (0.0-1.0)
            
        Returns:
            Retrieved context or None if retrieval fails or no relevant documents found
        """
        try:
            # Check if knowledge base is configured
            if "knowledge_base" not in agent_config:
                logger.info("No knowledge base configured for this agent")
                return None
                
            kb = agent_config["knowledge_base"]
            storage_type = kb.get("storage_type", "llamacloud" if kb.get("index_info") else "local")
            agent_name = kb.get("agent_name")
            
            if not agent_name:
                logger.warning("Missing agent name in knowledge base configuration")
                return None
            
            logger.info(f"Querying {storage_type} knowledge base for agent {agent_name} with query: {query}")
            
            # Use the query_agent_knowledge method with the provided parameters
            query_result = await self.query_agent_knowledge(agent_name, storage_type, query, similarity_top_k)
            
            if not query_result.get("success", False):
                logger.warning(f"Query failed: {query_result.get('error', 'Unknown error')}")
                return None
            
            # Check if any of the retrieved documents meet the relevance threshold
            has_relevant_docs = False
            source_docs = query_result.get("source_documents", [])
            
            if source_docs:
                for doc in source_docs:
                    score = doc.get("score")
                    if score is not None and score >= relevance_threshold:
                        has_relevant_docs = True
                        logger.info(f"Found relevant document with score: {score}")
                        break
            
            if not has_relevant_docs:
                logger.info(f"No documents found that meet relevance threshold of {relevance_threshold}")
                return None
            
            # Format the response for the agent
            formatted_response = self._format_retrieved_context(query_result)
            return formatted_response
            
        except Exception as e:
            logger.error(f"Error querying knowledge base: {str(e)}", exc_info=True)
            return f"Error querying knowledge base: {str(e)}"
    
    def _sanitize_name(self, name: str) -> str:
        """
        Sanitize agent name for use in index name and directory names.
        
        Args:
            name: Original agent name
            
        Returns:
            Sanitized name suitable for index and filesystem
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


    def _format_retrieved_context(self, query_result: Dict[str, Any]) -> str:
        """
        Format the retrieved context for the agent, including source information.
        
        Args:
            query_result: Result from query_agent_knowledge
            
        Returns:
            Formatted context string
        """
        try:
            if not query_result.get("success", False):
                return None
                
            formatted_text = "Here is the retrieved information from the knowledge base:\n\n"
            
            # Add the response text
            response_text = query_result.get("response", "")
            formatted_text += response_text + "\n\n"
            
            # Add source information if available
            source_docs = query_result.get("source_documents", [])
            if source_docs:
                formatted_text += "Sources:\n"
                for i, doc in enumerate(source_docs):
                    file_name = doc.get("file_name", f"Source {i+1}")
                    score = doc.get("score")
                    score_text = f" (relevance: {score:.2f})" if score is not None else ""
                    
                    formatted_text += f"- {file_name}{score_text}\n"
            
            return formatted_text
            
        except Exception as e:
            logger.error(f"Error formatting retrieved context: {str(e)}", exc_info=True)
            return str(query_result.get("response", "No relevant information found."))