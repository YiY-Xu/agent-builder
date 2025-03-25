"""
Tests for the merged KnowledgeService class
"""
import os
import json
import shutil
import logging
import pytest
import pytest_asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi import UploadFile
import tempfile


# Set up detailed logging for debugging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Import the service
from app.services.knowledge_service import KnowledgeService, sanitize_agent_name

# Constants for testing
TEST_AGENT_NAME = "test2"
TEST_FILE_CONTENT = "This is a test document about LlamaIndex. LlamaIndex is a data framework for LLM applications to ingest, structure, and access private or domain-specific data. It helps with RAG (Retrieval Augmented Generation)."
TEST_FILE_NAME = "llamaindex_doc.txt"
TEST_QUERY = "What is Yi Xu's company?"


class TestKnowledgeService:
    """Test class for the merged KnowledgeService with all functionality"""

    @pytest.fixture
    def service(self):
        """Create a KnowledgeService instance with temporary directories."""
        # Create temporary directories
        temp_upload_dir = tempfile.mkdtemp()
        permanent_storage_dir = tempfile.mkdtemp()
        
        # Create service instance
        service = KnowledgeService()
        
        # Override paths
        service.temp_upload_dir = temp_upload_dir
        service.permanent_storage_dir = permanent_storage_dir
        
        # Clean up test agent data if it exists from a previous test
        self.cleanup_test_agent(service, TEST_AGENT_NAME)
        
        yield service
        
        # Clean up temporary directories
        shutil.rmtree(temp_upload_dir, ignore_errors=True)
        shutil.rmtree(permanent_storage_dir, ignore_errors=True)
    
    def cleanup_test_agent(self, service, agent_name):
        """Clean up index data but keep folder structure"""
        sanitized_name = sanitize_agent_name(agent_name)
        
        # Clean up metadata in temp directory
        temp_agent_dir = os.path.join(service.temp_upload_dir, sanitized_name)
        if os.path.exists(temp_agent_dir):
            # Only delete metadata.json
            metadata_path = os.path.join(temp_agent_dir, "metadata.json")
            if os.path.exists(metadata_path):
                logger.info(f"Cleaning up temporary metadata: {metadata_path}")
                os.remove(metadata_path)
        
        # Clean up index in permanent directory
        perm_agent_dir = os.path.join(service.permanent_storage_dir, sanitized_name)
        if os.path.exists(perm_agent_dir):
            # Delete index directory
            index_path = os.path.join(perm_agent_dir, "index")
            if os.path.exists(index_path):
                logger.info(f"Cleaning up index directory: {index_path}")
                shutil.rmtree(index_path, ignore_errors=True)
            
            # Delete metadata.json
            metadata_path = os.path.join(perm_agent_dir, "metadata.json")
            if os.path.exists(metadata_path):
                logger.info(f"Cleaning up permanent metadata: {metadata_path}")
                os.remove(metadata_path)
    
    async def create_fake_upload_file(self, content, filename):
        """Helper to create a UploadFile object for testing"""
        file_content = content.encode("utf-8")
        
        upload_file = MagicMock(spec=UploadFile)
        upload_file.filename = filename
        upload_file.read = AsyncMock(return_value=file_content)
        
        return upload_file
    
    async def upload_test_files(self, service):
        """Upload test files and return results"""
        test_files = [
            ("test_doc1.txt", "This is the first test document about LlamaIndex. LlamaIndex is a data framework for LLM applications."),
            ("test_doc2.txt", "LlamaIndex can be used for retrieval augmented generation and document processing."),
            ("test_doc3.txt", "With LlamaIndex, you can build RAG systems that efficiently retrieve relevant information.")
        ]
        
        results = []
        for filename, content in test_files:
            logger.info(f"Uploading test file: {filename}")
            upload_file = await self.create_fake_upload_file(content, filename)
            result = await service.upload_file(upload_file, TEST_AGENT_NAME)
            results.append(result)
            logger.info(f"Upload result: {result}")
        
        return results
    
    @pytest.mark.asyncio
    async def test_upload_file(self, service):
        """Test uploading a file to the service"""
        # Create an upload file
        upload_file = await self.create_fake_upload_file(TEST_FILE_CONTENT, TEST_FILE_NAME)
        
        # Upload the file to the service
        logger.info(f"Uploading file: {TEST_FILE_NAME}")
        result = await service.upload_file(upload_file, TEST_AGENT_NAME)
        logger.info(f"Upload result: {result}")
        
        # Check result
        assert result["success"] is True
        
        # Either the file name matches exactly or contains the base name with a unique suffix
        returned_filename = result["file_name"]
        assert TEST_FILE_NAME == returned_filename or (
            TEST_FILE_NAME.split('.')[0] in returned_filename and 
            returned_filename.endswith(TEST_FILE_NAME.split('.')[-1])
        )
        
        assert result["agent_name"] == TEST_AGENT_NAME

    @pytest.mark.asyncio
    async def test_get_uploaded_files(self, service):
        """Test retrieving the list of uploaded files"""
        # First upload some files
        await self.upload_test_files(service)
        
        # Get uploaded files
        logger.info(f"Getting uploaded files for agent: {TEST_AGENT_NAME}")
        result = service.get_uploaded_files(TEST_AGENT_NAME)
        logger.info(f"Get uploaded files result: {result}")
        
        # Check result
        assert "files" in result
        assert len(result["files"]) >= 3  # At least the 3 files we uploaded
        assert "agent_name" in result
        assert result["agent_name"] == TEST_AGENT_NAME
        
        # Check has_index status before creating index
        assert result["has_index"] is False

    @pytest.mark.asyncio
    async def test_remove_file(self, service):
        """Test removing a file"""
        # First upload some files
        await self.upload_test_files(service)
        
        # Get current files
        initial_files = service.get_uploaded_files(TEST_AGENT_NAME)
        file_to_remove = initial_files["files"][0]  # Remove the first file
        
        # Remove the file
        logger.info(f"Removing file: {file_to_remove}")
        result = service.remove_file(TEST_AGENT_NAME, file_to_remove)
        logger.info(f"Remove file result: {result}")
        
        # Check result
        assert result["success"] is True
        
        # Verify file is removed from list
        updated_files = service.get_uploaded_files(TEST_AGENT_NAME)
        assert file_to_remove not in updated_files["files"]
        assert len(updated_files["files"]) == len(initial_files["files"]) - 1

    @pytest.mark.asyncio
    async def test_create_local_index(self, service):
        """Test creating a local index with real files"""
        # Step 1: Upload test files
        upload_results = await self.upload_test_files(service)
        
        # Verify uploads were successful
        for result in upload_results:
            assert result["success"] is True
        
        # Step 2: Debug - Inspect the temp directory structure
        agent_dir = os.path.join(service.temp_upload_dir, sanitize_agent_name(TEST_AGENT_NAME))
        logger.info(f"Agent directory path: {agent_dir}")
        
        if os.path.exists(agent_dir):
            files = os.listdir(agent_dir)
            logger.info(f"Files in agent directory: {files}")
            
            # Print file sizes to ensure they're not empty
            for filename in files:
                file_path = os.path.join(agent_dir, filename)
                if os.path.isfile(file_path):
                    logger.info(f"File {filename} size: {os.path.getsize(file_path)} bytes")
                    
                    # If it's metadata.json, print the content
                    if filename == "metadata.json":
                        try:
                            with open(file_path, 'r') as f:
                                metadata = json.load(f)
                                logger.info(f"Metadata content: {json.dumps(metadata, indent=2)}")
                        except Exception as e:
                            logger.error(f"Error reading metadata file: {str(e)}")
        
        # Step 3: Create local index
        logger.info(f"Creating local index for agent: {TEST_AGENT_NAME}")
        result = await service.create_local_index(TEST_AGENT_NAME)
        logger.info(f"Create index result: {json.dumps(result, indent=2) if isinstance(result, dict) else result}")
        
        # Step 4: Check result
        assert result["success"] is True, f"Index creation failed with error: {result.get('error', 'unknown error')}"
        assert "local_path" in result
        assert "index_info" in result
        assert os.path.exists(result["local_path"])
        assert os.path.exists(result["index_info"])
        
        # Step 5: Debug - Inspect the permanent directory structure after index creation
        perm_agent_dir = result["local_path"]
        if os.path.exists(perm_agent_dir):
            perm_files = os.listdir(perm_agent_dir)
            logger.info(f"Files in permanent agent directory: {perm_files}")
            
            # Check index directory
            index_path = result["index_info"]
            if os.path.exists(index_path):
                index_files = os.listdir(index_path)
                logger.info(f"Files in index directory: {index_files}")

        # Step 6: Verify index is reflected in get_uploaded_files
        updated_files = service.get_uploaded_files(TEST_AGENT_NAME)
        assert updated_files["has_index"] is True
        assert updated_files["storage_type"] == "local"
        
        return result

    @pytest.mark.asyncio
    async def test_query_local_index(self, service):
        """Test querying a local index"""
        # First create the index
        create_result = await self.test_create_local_index(service)
        assert create_result["success"] is True
        
        # Now query the index
        logger.info(f"Querying index for: {TEST_QUERY}")
        query_result = await service.query_local_index(TEST_AGENT_NAME, TEST_QUERY)
        logger.info(f"Query result: {self.format_query_result(query_result) if isinstance(query_result, dict) else query_result}")

        print("--------------------------------")
        print(query_result)
        print("--------------------------------")
        
        # Check query result structure
        assert query_result["success"] is True
        assert query_result["agent_name"] == TEST_AGENT_NAME
        assert query_result["query"] == TEST_QUERY
        assert "response" in query_result
        assert "source_texts" in query_result
        assert "source_documents" in query_result
        
        # The response should contain information about LlamaIndex
        response_lower = query_result["response"].lower()
        assert "llamaindex" in response_lower or "rag" in response_lower or "retrieval" in response_lower
        
        # Verify source texts and documents
        assert len(query_result["source_texts"]) > 0
        assert len(query_result["source_documents"]) > 0
        
        return query_result

    @pytest.mark.asyncio
    async def test_query_agent_knowledge(self, service):
        """Test the query_agent_knowledge method that selects the appropriate index"""
        # First create the index
        create_result = await self.test_create_local_index(service)
        assert create_result["success"] is True
        
        # Now query using the agent_knowledge method
        logger.info(f"Using query_agent_knowledge for: {TEST_QUERY}")
        query_result = await service.query_agent_knowledge(TEST_AGENT_NAME, TEST_QUERY)
        logger.info(f"Query result: {self.format_query_result(query_result) if isinstance(query_result, dict) else query_result}")
        
        # Check basic response structure
        assert query_result["success"] is True
        assert query_result["agent_name"] == TEST_AGENT_NAME
        assert query_result["query"] == TEST_QUERY
        assert "response" in query_result
        
        # The response should contain information about LlamaIndex
        response_lower = query_result["response"].lower()
        assert "llamaindex" in response_lower or "rag" in response_lower or "retrieval" in response_lower

    @pytest.mark.asyncio
    async def test_query_knowledge_base(self, service):
        """Test the query_knowledge_base method with agent config"""
        # First create the index
        create_result = await self.test_create_local_index(service)
        assert create_result["success"] is True
        
        # Create agent config with knowledge base info
        agent_config = {
            "knowledge_base": {
                "agent_name": TEST_AGENT_NAME,
                "storage_type": "local"
            }
        }
        
        # Query the knowledge base
        logger.info(f"Querying knowledge base with config: {agent_config}")
        result = await service.query_knowledge_base(TEST_QUERY, agent_config)
        logger.info(f"Query knowledge base result: {result}")
        
        # Check result
        assert result is not None
        assert isinstance(result, str)
        assert "retrieved information" in result.lower()
        assert "llamaindex" in result.lower() or "rag" in result.lower() or "retrieval" in result.lower()
        assert "sources:" in result.lower()

    @pytest.mark.asyncio
    async def test_format_retrieved_context(self, service):
        """Test the _format_retrieved_context method"""
        # First get a query result
        query_result = await self.test_query_local_index(service)
        
        # Format the context
        formatted_result = service._format_retrieved_context(query_result)
        logger.info(f"Formatted context: {formatted_result}")
        
        # Check formatting
        assert "Here is the retrieved information" in formatted_result
        assert query_result["response"] in formatted_result
        assert "Sources:" in formatted_result

    def format_query_result(self, query_result):
        """Create a safe representation of query results for logging"""
        if not isinstance(query_result, dict):
            return str(query_result)
            
        # Create a copy we can modify
        result = query_result.copy()
        
        # Handle the raw_response_object specially
        if "raw_response_object" in result:
            result["raw_response_object"] = str(result["raw_response_object"])
            
        return json.dumps(result, indent=2)

def test_sanitize_name():
    """Test the name sanitization function."""
    test_cases = [
        ("Test Agent", "test-agent"),
        ("Test Agent!!!", "test-agent"),
        ("Test@Agent", "testagent"),
        ("   Test   Agent   ", "test-agent"),
        ("VeryLongAgentNameThatShouldBeTruncated", "verylongagentnameth"),
        ("-Test-Agent-", "test-agent"),
        ("", "agent"),
        ("12345", "12345")
    ]
    
    for input_name, expected in test_cases:
        sanitized_name = sanitize_agent_name(input_name)
        assert sanitized_name == expected, f"Expected {expected} for {input_name}, got {sanitized_name}"

async def test_upload_file(service, monkeypatch):
    """Test uploading a file."""
    # Mock UploadFile
    mock_file = MagicMock()
    mock_file.filename = TEST_FILE_NAME
    mock_file.read.return_value = b"test content"
    
    # Create agent directory
    agent_dir = os.path.join(service.temp_upload_dir, sanitize_agent_name(TEST_AGENT_NAME))
    os.makedirs(agent_dir, exist_ok=True)
    
    # Test uploading a file
    result = await service.upload_file(mock_file, TEST_AGENT_NAME)
    
    # Assertions
    assert result["success"] is True
    assert result["file_name"] == TEST_FILE_NAME
    assert result["agent_name"] == TEST_AGENT_NAME
    
    # Check if file exists
    file_path = os.path.join(agent_dir, TEST_FILE_NAME)
    assert os.path.exists(file_path)
    
    # Check if metadata was updated
    metadata_path = os.path.join(agent_dir, "metadata.json")
    assert os.path.exists(metadata_path)
    
    with open(metadata_path, 'r') as f:
        metadata = json.load(f)
        assert TEST_FILE_NAME in metadata["files"]