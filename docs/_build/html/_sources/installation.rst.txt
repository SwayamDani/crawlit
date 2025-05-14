Installation
============

Requirements
-----------

* Python 3.8+
* Dependencies (listed in ``requirements.txt``)

From PyPI (recommended)
----------------------

.. code-block:: bash

    # Install the core library
    pip install crawlit

    # Install with CLI tool support
    pip install crawlit[cli]

From Source
----------

.. code-block:: bash

    # Clone the repository
    git clone https://github.com/SwayamDani/crawlit.git
    cd crawlit

    # Create a virtual environment (recommended)
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate

    # Install dependencies
    pip install -r requirements.txt

    # Install in development mode
    pip install -e .
