Quick Start
==========

This quick start guide will help you get up and running with `crawlit`.

Basic Usage
----------

Here's a simple example of how to use `crawlit` as a library:

.. code-block:: python

    from crawlit import Crawler, save_results

    # Initialize the crawler with custom parameters
    crawler = Crawler(
        start_url="https://example.com",
        max_depth=2,
        internal_only=True
    )

    # Start crawling
    crawler.crawl()

    # Get and process results
    results = crawler.get_results()
    print(f"Crawled {len(results)} URLs")

    # Save results to JSON
    save_results(results, output_format="json", output_file="results.json")

Command Line Usage
----------------

If you installed with `pip install crawlit[cli]`, you can use the command-line interface:

.. code-block:: bash

    # Basic usage
    crawlit --url https://example.com

    # Advanced options
    crawlit --url https://example.com \
            --depth 3 \
            --output-format json \
            --output results.json \
            --delay 0.5
