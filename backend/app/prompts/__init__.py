# This file makes the prompts directory a Python package
# It allows importing the prompt modules from other parts of the application

from .system_prompt import get_system_prompt

__all__ = ['get_system_prompt']