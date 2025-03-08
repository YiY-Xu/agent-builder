from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
import logging
import os

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/logs",
    tags=["logs"],
    responses={404: {"description": "Not found"}},
)

# Configuration for log file
LOG_FILE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "app.log")

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