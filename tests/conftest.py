"""
Pytest configuration and fixtures for crawlit tests.

This configuration automatically applies markers based on test directory:
- tests/integration/ -> @pytest.mark.integration
- tests/performance/ -> @pytest.mark.performance
- All other tests -> @pytest.mark.unit
"""

import pytest
from pathlib import Path


def pytest_collection_modifyitems(config, items):
    """
    Automatically add markers to tests based on their location.
    
    This allows running tests by category without manually adding markers:
    - pytest -m unit          # Run only unit tests
    - pytest -m integration   # Run only integration tests
    - pytest -m performance   # Run only performance tests
    """
    rootdir = Path(config.rootdir)
    
    for item in items:
        # Get the relative path of the test file
        rel_path = Path(item.fspath).relative_to(rootdir)
        
        # Apply markers based on directory
        if "integration" in rel_path.parts:
            item.add_marker(pytest.mark.integration)
        elif "performance" in rel_path.parts:
            item.add_marker(pytest.mark.performance)
        else:
            # All other tests are unit tests
            item.add_marker(pytest.mark.unit)
        
        # Add network marker to tests that aren't already marked
        # (most tests use mocked servers, but some might use real network)
        if not any(marker.name == "network" for marker in item.iter_markers()):
            # Check if test uses real network (simple heuristic)
            if "http://" in str(item.function.__doc__ or ""):
                item.add_marker(pytest.mark.network)


@pytest.fixture
def temp_dir(tmp_path):
    """Provide a temporary directory for tests."""
    return tmp_path


@pytest.fixture
def sample_html():
    """Provide sample HTML for testing."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test Page</title>
        <meta name="description" content="Test description">
    </head>
    <body>
        <h1>Test Heading</h1>
        <p>Test paragraph with some content.</p>
        <a href="/page1">Link 1</a>
        <a href="/page2">Link 2</a>
    </body>
    </html>
    """


@pytest.fixture
def sample_url():
    """Provide a sample URL for testing."""
    return "http://example.com/test"


@pytest.fixture
def mock_website():
    """Provide a mock website URL for testing."""
    return "http://example.com"
