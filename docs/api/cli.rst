Command Line Interface
====================

The `crawlit` package provides a convenient command-line interface for crawling websites and extracting structured data.

CLI Usage
---------

For detailed CLI usage instructions, including all available options and examples, please see the `cli_usage.md` document in the docs directory.

CLI Module
---------

.. automodule:: crawlit
   :members: cli_main
   :undoc-members:
   :show-inheritance:

CLI Examples
-----------

Basic crawling::

    crawlit --url https://example.com

Extract tables, images, and keywords (v0.2.0+)::

    crawlit --url https://example.com --user-agent "crawlit/2.0" --extract-tables --extract-images --extract-keywords
