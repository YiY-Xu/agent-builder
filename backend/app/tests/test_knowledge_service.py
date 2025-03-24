import os
import sys
import shutil
import pytest
import tempfile
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi import UploadFile
import io
import json

# Add parent directory to Python path to allow importing app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import the service to test - use absolute imports
from app.services.knowledge_service import KnowledgeService

# Mock the settings for testing
class MockSettings:
    LLAMA_CLOUD_API_KEY = "test_api_key"
    LLAMA_CLOUD_INDEX_PREFIX = "test-index"
    LLAMA_CLOUD_PROJECT_NAME = "test-project"

# Constants for testing
TEST_AGENT_NAME = "test-agent"
TEST_FILE_CONTENT = "This is a test document about LlamaIndex. LlamaIndex is a data framework for LLM applications to ingest, structure, and access private or domain-specific data. It helps with RAG (Retrieval Augmented Generation)."
TEST_FILE_NAME = "llamaindex_doc.txt"
TEST_QUERY = "What is LlamaIndex used for?"


class TestKnowledgeService:
    """Test class for KnowledgeService with real file operations"""

    @pytest.fixture(scope="function", autouse=True)
    def patch_settings(self):
        """Patch the settings import in the knowledge service"""
        with patch('app.services.knowledge_service.settings', MockSettings()):
            yield

    @pytest.fixture
    def test_dirs(self):
        """Create test directories for the service"""
        # Create temporary directories for testing
        temp_dir = tempfile.mkdtemp()
        perm_dir = tempfile.mkdtemp()
        
        yield temp_dir, perm_dir
        
        # Cleanup after tests
        shutil.rmtree(temp_dir, ignore_errors=True)
        shutil.rmtree(perm_dir, ignore_errors=True)
    
    @pytest.fixture
    def service(self, test_dirs):
        """Create a KnowledgeService instance for testing with real files"""
        temp_dir, perm_dir = test_dirs
        
        # Create instance with test directories
        service = KnowledgeService()
        
        # Override the directories for testing
        service.temp_upload_dir = temp_dir
        service.permanent_storage_dir = perm_dir
        
        # Ensure directories exist
        os.makedirs(service.temp_upload_dir, exist_ok=True)
        os.makedirs(service.permanent_storage_dir, exist_ok=True)
        
        return service
    
    async def create_fake_upload_file(self, content, filename):
        """Helper to create a UploadFile object for testing"""
        file_content = content.encode("utf-8")
        file_obj = io.BytesIO(file_content)
        
        upload_file = MagicMock(spec=UploadFile)
        upload_file.filename = filename
        upload_file.read = AsyncMock(return_value=file_content)
        
        return upload_file
    
    @pytest.fixture
    async def setup_test_files(self, service):
        """Set up test files in the temporary upload directory"""
        test_files = [
            ("document1.txt", "This is the first test document about LlamaIndex."),
            ("document2.txt", "LlamaIndex can be used for retrieval augmented generation."),
            ("document3.txt", "Document retrieval systems help with finding relevant information.")
        ]
        
        upload_results = []
        for filename, content in test_files:
            upload_file = await self.create_fake_upload_file(content, filename)
            result = await service.upload_file(upload_file, TEST_AGENT_NAME)
            upload_results.append(result)
            assert result["success"] is True
        
        return upload_results
    
    @pytest.mark.asyncio
    async def test_upload_file(self, service):
        """Test uploading a real file to the service"""
        # Create an upload file
        upload_file = await self.create_fake_upload_file(TEST_FILE_CONTENT, TEST_FILE_NAME)
        
        # Upload the file to the service
        result = await service.upload_file(upload_file, TEST_AGENT_NAME)
        
        # Check result
        assert result["success"] is True
        assert result["file_name"] == TEST_FILE_NAME
        assert result["agent_name"] == TEST_AGENT_NAME
        
        # Check if file exists in the temporary directory
        agent_dir = os.path.join(service.temp_upload_dir, service._sanitize_name(TEST_AGENT_NAME))
        file_path = os.path.join(agent_dir, TEST_FILE_NAME)
        assert os.path.exists(file_path)
        
        # Verify file content
        with open(file_path, 'r') as f:
            content = f.read()
            assert content == TEST_FILE_CONTENT

    @pytest.mark.asyncio
    async def test_create_local_index(self, service, setup_test_files):
        """Test creating a local index with real files"""
        # Create local index
        result = await service.create_local_index(TEST_AGENT_NAME)
        
        # Check result
        assert result["success"] is True
        assert result["storage_type"] == "local"
        assert "local_path" in result
        assert "index_path" in result
        assert os.path.exists(result["local_path"])
        assert os.path.exists(result["index_path"])
        assert result["has_index"] is True
        
        # Check that files were copied to permanent storage
        sanitized_name = service._sanitize_name(TEST_AGENT_NAME)
        perm_agent_dir = os.path.join(service.permanent_storage_dir, sanitized_name)
        assert os.path.exists(perm_agent_dir)
        
        # Verify metadata file exists
        metadata_path = os.path.join(perm_agent_dir, "metadata.json")
        assert os.path.exists(metadata_path)
        
        # Verify index directory exists with files
        index_path = os.path.join(perm_agent_dir, "index")
        assert os.path.exists(index_path)
        assert len(os.listdir(index_path)) > 0  # Should have some index files
        
        return result

    @pytest.mark.asyncio
    async def test_query_local_index(self, service, setup_test_files):
        """Test querying a local index with real files"""
        # First create the index
        create_result = await service.create_local_index(TEST_AGENT_NAME)
        assert create_result["success"] is True
        
        # Now query the index
        query_result = await service.query_local_index(TEST_AGENT_NAME, TEST_QUERY)
        
        # Check query result structure
        assert query_result["success"] is True
        assert query_result["agent_name"] == TEST_AGENT_NAME
        assert query_result["query"] == TEST_QUERY
        assert "response" in query_result
        assert "source_texts" in query_result
        assert isinstance(query_result["source_texts"], list)
        assert "source_documents" in query_result
        assert isinstance(query_result["source_documents"], list)
        
        # The response should contain some information about LlamaIndex
        response_lower = query_result["response"].lower()
        assert "llamaindex" in response_lower or "retrieval" in response_lower
        
        return query_result

    @pytest.mark.asyncio
    async def test_query_agent_knowledge(self, service, setup_test_files):
        """Test the query_agent_knowledge method which selects the appropriate index"""
        # First create the index
        create_result = await service.create_local_index(TEST_AGENT_NAME)
        assert create_result["success"] is True
        
        # Now query using the agent_knowledge method
        query_result = await service.query_agent_knowledge(TEST_AGENT_NAME, TEST_QUERY)
        
        # Check basic response structure
        assert query_result["success"] is True
        assert query_result["agent_name"] == TEST_AGENT_NAME
        assert query_result["query"] == TEST_QUERY
        assert "response" in query_result
        
        # The response should contain some information about LlamaIndex
        response_lower = query_result["response"].lower()
        assert "llamaindex" in response_lower or "retrieval" in response_lower

    @pytest.mark.asyncio
    async def test_multiple_document_types(self, service):
        """Test indexing and querying with multiple document types"""
        # Create and upload different types of test files
        test_files = [
            ("text_doc.txt", "LlamaIndex helps with document retrieval for LLMs."),
            ("info_doc.md", "# LlamaIndex\n\nA data framework for LLM applications."),
            ("data_doc.csv", "feature,description\nretrieval,finding relevant info\nindexing,organizing documents")
        ]
        
        for filename, content in test_files:
            upload_file = await self.create_fake_upload_file(content, filename)
            result = await service.upload_file(upload_file, TEST_AGENT_NAME)
            assert result["success"] is True
        
        # Create local index with these files
        create_result = await service.create_local_index(TEST_AGENT_NAME)
        assert create_result["success"] is True
        
        # Query about a specific topic that should be found in the documents
        query_result = await service.query_local_index(TEST_AGENT_NAME, "What does LlamaIndex do with documents?")
        
        # Verify we get a response with relevant information
        assert query_result["success"] is True
        assert "response" in query_result
        response_lower = query_result["response"].lower()
        
        # The response should have relevant content
        relevant_terms = ["retrieval", "document", "llm", "llamaindex"]
        assert any(term in response_lower for term in relevant_terms)

if __name__ == "__main__":
    pytest.main(["-v"])