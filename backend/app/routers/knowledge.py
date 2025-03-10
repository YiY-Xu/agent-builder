from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Path
from typing import List, Dict, Any, Optional
import logging

from ..services.knowledge_service import KnowledgeService
from pydantic import BaseModel

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api",
    tags=["knowledge"],
    responses={404: {"description": "Not found"}},
)

# Response models
class FileUploadResponse(BaseModel):
    success: bool
    file_name: Optional[str] = None
    agent_name: Optional[str] = None
    error: Optional[str] = None

class FileListResponse(BaseModel):
    agent_name: str
    files: List[str]
    index_name: Optional[str] = None
    project_name: Optional[str] = None
    storage_type: Optional[str] = None
    local_path: Optional[str] = None
    has_index: bool
    error: Optional[str] = None

class IndexCreationResponse(BaseModel):
    success: bool
    storage_type: Optional[str] = None
    index_name: Optional[str] = None
    project_name: Optional[str] = None
    local_path: Optional[str] = None
    document_count: Optional[int] = None
    file_names: Optional[List[str]] = None
    message: Optional[str] = None
    error: Optional[str] = None

class LocalStorageResponse(BaseModel):
    success: bool
    storage_type: str = "local"
    local_path: Optional[str] = None
    document_count: Optional[int] = None
    file_names: Optional[List[str]] = None
    message: Optional[str] = None
    error: Optional[str] = None

class FileRemovalResponse(BaseModel):
    success: bool
    message: Optional[str] = None
    error: Optional[str] = None

# Dependency to get KnowledgeService instance
def get_knowledge_service():
    return KnowledgeService()

@router.post("/upload-file", response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    agent_name: str = Form(...),
    knowledge_service: KnowledgeService = Depends(get_knowledge_service)
):
    """
    Upload a single file for an agent.
    
    - Takes a single file and agent name
    - Saves the file to temporary storage
    - Returns information about the uploaded file
    """
    try:
        logger.info(f"Uploading file for agent: {agent_name}")
        logger.info(f"Received file: {file.filename}")
        
        result = await knowledge_service.upload_file(file, agent_name)
        
        if not result.get("success", False):
            raise HTTPException(status_code=500, detail=result.get("error", "Failed to upload file"))
        
        return result
    
    except Exception as e:
        logger.error(f"Error uploading file: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error uploading file: {str(e)}")

@router.get("/files/{agent_name}", response_model=FileListResponse)
async def get_files(
    agent_name: str = Path(...),
    knowledge_service: KnowledgeService = Depends(get_knowledge_service)
):
    """
    Get list of uploaded files for an agent.
    
    - Takes agent name
    - Returns list of files and index status
    """
    try:
        result = knowledge_service.get_uploaded_files(agent_name)
        
        if "error" in result:
            raise HTTPException(status_code=500, detail=result.get("error"))
        
        return result
    
    except Exception as e:
        logger.error(f"Error getting files: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error getting files: {str(e)}")

@router.post("/create-index/{agent_name}", response_model=IndexCreationResponse)
async def create_index(
    agent_name: str = Path(...),
    knowledge_service: KnowledgeService = Depends(get_knowledge_service)
):
    """
    Create a LlamaCloud index from previously uploaded files.
    
    - Takes agent name
    - Creates index from all uploaded files
    - Returns information about the created index
    """
    try:
        logger.info(f"Creating index for agent: {agent_name}")
        
        result = await knowledge_service.create_index(agent_name)
        
        if not result.get("success", False):
            raise HTTPException(status_code=500, detail=result.get("error", "Failed to create index"))
        
        return result
    
    except Exception as e:
        logger.error(f"Error creating index: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error creating index: {str(e)}")

@router.post("/save-local/{agent_name}", response_model=LocalStorageResponse)
async def save_to_local(
    agent_name: str = Path(...),
    knowledge_service: KnowledgeService = Depends(get_knowledge_service)
):
    """
    Save uploaded files to local storage.
    
    - Takes agent name
    - Copies files from temp storage to permanent local storage
    - Returns information about the local storage
    """
    try:
        logger.info(f"Saving to local storage for agent: {agent_name}")
        
        result = await knowledge_service.save_to_local(agent_name)
        
        if not result.get("success", False):
            raise HTTPException(status_code=500, detail=result.get("error", "Failed to save to local storage"))
        
        return result
    
    except Exception as e:
        logger.error(f"Error saving to local storage: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error saving to local storage: {str(e)}")

@router.delete("/files/{agent_name}/{file_name}", response_model=FileRemovalResponse)
async def remove_file(
    agent_name: str = Path(...),
    file_name: str = Path(...),
    knowledge_service: KnowledgeService = Depends(get_knowledge_service)
):
    """
    Remove a file from an agent's uploaded files.
    
    - Takes agent name and file name
    - Removes the file from temporary storage
    - Returns result of the operation
    """
    try:
        logger.info(f"Removing file {file_name} for agent: {agent_name}")
        
        result = knowledge_service.remove_file(agent_name, file_name)
        
        if not result.get("success", False):
            raise HTTPException(status_code=500, detail=result.get("error", "Failed to remove file"))
        
        return result
    
    except Exception as e:
        logger.error(f"Error removing file: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error removing file: {str(e)}")