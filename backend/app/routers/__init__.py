# This file makes the routers directory a Python package
# It allows importing the router modules from other parts of the application

from .chat import router as chat_router

__all__ = ['chat_router']