Contributing
===========

Thank you for considering contributing to `crawlit`! This document provides guidelines and instructions for contributing.

Development Setup
---------------

1. Fork the repository
2. Clone your fork:

   .. code-block:: bash

       git clone https://github.com/yourusername/crawlit.git
       cd crawlit

3. Create a virtual environment:

   .. code-block:: bash

       python -m venv venv
       source venv/bin/activate  # On Windows: venv\Scripts\activate

4. Install development dependencies:

   .. code-block:: bash

       pip install -e ".[dev,test]"

Running Tests
-----------

We use pytest for testing:

.. code-block:: bash

    # Run all tests
    pytest
    
    # Run specific test files
    pytest tests/test_engine.py
    
    # Run with coverage report
    pytest --cov=crawlit tests/

Code Style
---------

We follow PEP 8 style guidelines. Please ensure your code adheres to these standards.

You can use tools like `black`, `flake8`, and `isort` to automatically format your code:

.. code-block:: bash

    # Format your code
    black crawlit tests
    
    # Sort imports
    isort crawlit tests
    
    # Check for PEP 8 compliance
    flake8 crawlit tests

Pull Requests
-----------

1. Create a new branch for your feature or bug fix
2. Write tests that cover your changes
3. Ensure all tests pass and code style checks succeed
4. Submit a pull request with a clear description of the changes

Documentation
-----------

When adding new features, please update the documentation accordingly:

1. Update docstrings using Google-style format
2. Update the relevant RST files in the `docs/` directory
3. If adding new modules or functions, make sure they are included in the API documentation
