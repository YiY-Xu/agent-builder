from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import sys
import os
import time

# Setup logging at the very beginning
log_dir = os.path.dirname(os.path.abspath(__file__))
log_file_path = os.path.join(log_dir, "app.log")

# Configure root logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_file_path, mode='a')
    ]
)

logger = logging.getLogger(__name__)
logger.info(f"Logging to file: {log_file_path}")

# Now import the settings and routers
from app.config.settings import settings
from app.routers.chat import router as chat_router
from app.routers.test_agent import router as test_agent_router
from app.routers.knowledge import router as knowledge_router
from app.routers.logs import router as logs_router
from app.routers.mcp_servers import router as mcp_servers_router
# Log environment variables at startup
logger.info("Starting application with configuration:")
logger.info(f"CLAUDE_MODEL: {settings.CLAUDE_MODEL}")
logger.info(f"LOG_LEVEL: {settings.LOG_LEVEL}")
logger.info(f"CORS_ORIGINS: {settings.BACKEND_CORS_ORIGINS}")
# Don't log the actual API key for security reasons
logger.info(f"CLAUDE_API_KEY set: {'Yes' if settings.CLAUDE_API_KEY else 'No'}")

# Create FastAPI app
app = FastAPI(
    title="Agent Builder API",
    description="API for building agents with Claude",
    version="1.0.0",
)

# Set up CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware for logging request timing
@app.middleware("http")
async def log_requests(request: Request, call_next):
    # Skip logging for log stream requests
    if "/api/logs/current" in request.url.path:
        return await call_next(request)
    
    start_time = time.time()
    
    # Process the request
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        logger.info(f"Request to {request.url.path} completed in {process_time:.4f}s with status {response.status_code}")
        return response
    except Exception as e:
        process_time = time.time() - start_time
        logger.error(f"Request to {request.url.path} failed after {process_time:.4f}s: {str(e)}")
        return JSONResponse(status_code=500, content={"detail": str(e)})

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global exception handler caught: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {str(exc)}"}
    )

# Include routers
app.include_router(chat_router)
app.include_router(test_agent_router)
app.include_router(knowledge_router)
app.include_router(logs_router)
app.include_router(mcp_servers_router)
@app.get("/")
async def root():
    """Root endpoint to verify API is running."""
    return {"message": "Welcome to the Agent Builder API"}

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    logger.info("Health check endpoint called")
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)