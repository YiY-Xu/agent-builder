import os
import tempfile
import shutil
import logging
from typing import List, Dict, Any, Optional
import uuid
from fastapi import UploadFile
import json

# Import Llama Index components
from llama_index.core import SimpleDirectoryReader, VectorStoreIndex, StorageContext
from llama_index.indices.managed.llama_cloud import LlamaCloudIndex

from app.config.settings import settings

logger = logging.getLogger(__name__)

class KnowledgeService:
    """Service for handling document uploads and knowledge indexing."""
    
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
                "index_name": None,
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
                    "index_name": None,
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
                    "index_name": metadata.get("index_name"),
                    "project_name": metadata.get("project_name", self.project_name),
                    "storage_type": metadata.get("storage_type"),
                    "local_path": metadata.get("local_path"),
                    "has_index": metadata.get("index_name") is not None or metadata.get("local_path") is not None
                }
            else:
                # No metadata file, get files from directory
                files = [f for f in os.listdir(agent_dir) if os.path.isfile(os.path.join(agent_dir, f)) and f != "metadata.json"]
                
                return {
                    "agent_name": agent_name,
                    "files": files,
                    "index_name": None,
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
                if metadata.get("index_name"):
                    return {
                        "success": True,
                        "storage_type": "llamacloud",
                        "index_name": metadata["index_name"],
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
                    "index_name": None,
                    "project_name": self.project_name,
                    "storage_type": None,
                    "local_path": None
                }
                
                with open(metadata_path, 'w') as f:
                    json.dump(metadata, f, indent=2)
            
            # Create index name
            index_name = f"{self.index_name_prefix}-{sanitized_name}-{uuid.uuid4().hex[:8]}"
            
            logger.info(f"Creating LlamaCloud index: {index_name} with {len(metadata['files'])} documents")
            
            # Load documents from the directory
            documents = SimpleDirectoryReader(agent_dir, recursive=False).load_data()
            logger.info(f"Loaded {len(documents)} documents")
            
            # Create the index and upload documents
            index = LlamaCloudIndex.from_documents(
                documents, 
                index_name,
                project_name=self.project_name,
                api_key=self.llama_cloud_api_key
            )
            
            logger.info(f"Successfully created index {index_name}")
            
            # Update metadata with index name
            metadata["index_name"] = index_name
            metadata["project_name"] = self.project_name
            metadata["storage_type"] = "llamacloud"
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            # Return information about the upload
            return {
                "success": True,
                "storage_type": "llamacloud",
                "index_name": index_name,
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
                metadata["index_path"] = index_path
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
                    "index_path": index_path,
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
                    "index_name": None,
                    "project_name": None,
                    "index_path": index_path,
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
                    "index_path": index_path,
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
                if metadata.get("index_name") or metadata.get("local_path"):
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