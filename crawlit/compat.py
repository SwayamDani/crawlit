#!/usr/bin/env python3
"""
compat.py - Compatibility utilities for crawlit

This module provides utility functions to ensure compatibility between
different versions of crawlit and its dependencies.
"""

import inspect
from typing import Any, Callable

def ensure_response_compatibility(response_obj: Any) -> Any:
    """
    Ensures compatibility between sync and async response objects.
    
    This function will detect whether we're dealing with a requests.Response,
    aiohttp.ClientResponse, or our custom ResponseLike class, and adapt it to
    ensure consistent interface for the rest of the library.
    
    Args:
        response_obj: A response object from either requests or aiohttp
        
    Returns:
        The response object, possibly wrapped for compatibility
    """
    from .crawler.async_fetcher import ResponseLike
    import inspect
    
    # If it's already our wrapped class, return it
    if isinstance(response_obj, ResponseLike):
        return response_obj
    
    # Check if it's a requests.Response by looking for common attributes
    if hasattr(response_obj, 'text') and not inspect.iscoroutinefunction(response_obj.text):
        # It's likely a requests.Response, no need to convert
        return response_obj
        
    # Check if it's an aiohttp.ClientResponse by looking for async text() method
    if hasattr(response_obj, 'text') and inspect.iscoroutinefunction(response_obj.text):
        # Need to convert to ResponseLike
        # But we can't do it here because text() is async
        # So we return the original for now
        return response_obj
    
    # For unknown objects, return as-is
    return response_obj

def is_async_context() -> bool:
    """
    Determine if the current function is being called in an async context.
    
    Returns:
        bool: True if the current function is called from an async context
    """
    try:
        # Check the call stack to see if there's an async frame
        for frame_info in inspect.stack():
            if inspect.iscoroutinefunction(frame_info.frame.f_code):
                return True
        return False
    except Exception:
        # If we can't determine, assume not async
        return False
