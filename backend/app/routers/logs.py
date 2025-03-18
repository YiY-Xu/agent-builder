from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from typing import List, Dict, Any
import logging
import os
import json
import asyncio
from datetime import datetime

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/logs",
    tags=["logs"],
    responses={404: {"description": "Not found"}},
)

# Configuration for log file
LOG_FILE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "app.log")

async def log_stream_generator():
    """Generator function to stream log updates."""
    last_position = 0
    
    while True:
        try:
            if not os.path.exists(LOG_FILE_PATH):
                await asyncio.sleep(1)
                continue
                
            with open(LOG_FILE_PATH, 'r') as file:
                # Move to last known position
                file.seek(last_position)
                
                # Read new lines
                new_lines = file.readlines()
                
                if new_lines:
                    # Update last position
                    last_position = file.tell()
                    
                    # Process and send new lines
                    for line in new_lines:
                        if line.strip():
                            yield f"data: {json.dumps({'logs': [line.rstrip()]})}\n\n"
            
            # Wait before checking for new logs
            await asyncio.sleep(0.1)
            
        except Exception as e:
            logger.error(f"Error in log stream: {str(e)}")
            await asyncio.sleep(1)

@router.get("/stream")
async def stream_logs():
    """
    Stream system logs using Server-Sent Events (SSE).
    
    Returns:
        StreamingResponse: SSE stream of log updates
    """
    return StreamingResponse(
        log_stream_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )

@router.get("/current")
async def get_current_logs():
    """
    Get the current system logs from the log file.
    
    Returns:
        dict: Dictionary containing log lines
    """
    try:
        if not os.path.exists(LOG_FILE_PATH):
            logger.warning(f"Log file not found at {LOG_FILE_PATH}")
            # Create an empty log file if it doesn't exist
            with open(LOG_FILE_PATH, 'w') as f:
                f.write("Log file initialized\n")
            return {"logs": ["Log file initialized"]}
        
        # Read the last 500 lines of the log file
        with open(LOG_FILE_PATH, 'r') as file:
            # Read all lines and reverse them
            all_lines = file.readlines()
            
            # Take the last 500 lines
            lines = all_lines[-500:] if len(all_lines) > 500 else all_lines
            
            # Strip newlines
            lines = [line.rstrip() for line in lines]
        
        logger.info(f"Returning {len(lines)} log lines")
        return {"logs": lines}
    
    except Exception as e:
        logger.error(f"Error reading log file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error reading log file: {str(e)}")