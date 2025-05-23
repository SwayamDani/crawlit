# Crawlit Response Interface Standardization

## Background

In Crawlit v0.2.0, we've standardized the response interfaces between the synchronous (`requests`-based) and asynchronous (`aiohttp`-based) fetchers. This document explains the changes and how to handle response objects in your code.

## The Problem

Prior to v0.2.0, Crawlit had inconsistent interfaces for HTTP responses:

- Synchronous fetcher: Used `requests.Response` objects with properties like `.text`, `.status_code`, etc.
- Asynchronous fetcher: Used a custom `ResponseLike` wrapper that had an async `.text()` method and different property names

This inconsistency made it difficult for users to write code that worked with both sync and async crawlers, requiring special handling for each implementation.

## The Solution

We've enhanced the `ResponseLike` class to better match the `requests.Response` API while maintaining async compatibility:

### Standardized Properties

Both sync and async responses now support:

- `.status_code`: HTTP status code (200, 404, etc.)
- `.headers`: HTTP response headers
- `.content`: Binary content of the response
- `.url`: URL of the response
- `.ok`: Boolean indicating if status code is 2xx

### Text Content Access

- **Synchronous context**: Use `response.text_content` to get the text content as a string
- **Asynchronous context**: Use `await response.text()` for async access

### Response Error Handling

Both interfaces now support:

- `.raise_for_status()`: Raises an appropriate exception for 4xx/5xx status codes

### New Helper Functions

- `fetch_url_async()`: Mirrors the functionality of `fetch_url()` but for async contexts

## Migration Guide

If you were previously working with both sync and async interfaces and writing special handling for each:

1. **Use the standardized properties**: `.status_code`, `.headers`, `.url`, etc. work the same way in both interfaces

2. **For text content access**:
   - In async code, continue using `await response.text()`
   - In sync code with async responses, use `response.text_content` instead of `response.text_sync()`

3. **For error handling**:
   - In both interfaces, you can use `.raise_for_status()` the same way

## Example Usage

```python
# Works with both sync and async responses
def process_response(response):
    if not response.ok:
        print(f"Error {response.status_code}")
        return
    
    print(f"URL: {response.url}")
    print(f"Headers: {response.headers}")
    
    # For text access, need to handle differently
    if hasattr(response, 'text') and isinstance(response.text, str):
        # It's a sync response
        content = response.text
    elif hasattr(response, 'text_content'):
        # It's our ResponseLike wrapper
        content = response.text_content
    else:
        # It's an async response that needs await
        print("Can't access text content synchronously")
        return
        
    print(f"Content length: {len(content)}")
```

This standardization makes it easier to write code that works with both the synchronous and asynchronous crawlers without needing to handle the differences manually.
