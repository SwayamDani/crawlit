Usage Guide
===========

This guide shows you how to use `crawlit` in more advanced scenarios.

Library Usage
------------

Using the Crawler Class
^^^^^^^^^^^^^^^^^^^^^

The ``Crawler`` class is the main entry point for programmatic use:

.. code-block:: python

    from crawlit import Crawler
    
    # Initialize with all available parameters
    crawler = Crawler(
        start_url="https://example.com",
        max_depth=3,               # Maximum crawling depth
        internal_only=True,        # Restrict to the same domain
        user_agent="Custom/1.0",   # Custom User-Agent
        max_retries=3,             # Maximum retry attempts
        timeout=10,                # Request timeout in seconds
        delay=0.5,                 # Delay between requests
        respect_robots=True        # Respect robots.txt rules
    )
    
    # Start the crawling process
    crawler.crawl()
    
    # Get the results
    results = crawler.get_results()
    
    # Access information about each crawled page
    for url, data in results.items():
        print(f"URL: {url}")
        print(f"Status: {data['status']}")
        print(f"Title: {data.get('title', 'No title')}")
        print(f"Links found: {len(data.get('links', []))}")

Working with Results
^^^^^^^^^^^^^^^^^^

The ``save_results`` function helps you save the crawler results:

.. code-block:: python

    from crawlit import save_results
    
    # Save as JSON
    save_results(results, output_format="json", output_file="results.json", pretty_json=True)
    
    # Save as CSV
    save_results(results, output_format="csv", output_file="results.csv")
    
    # Save as plain text
    save_results(results, output_format="txt", output_file="results.txt")
    
    # Generate a summary report
    from crawlit import generate_summary_report
    summary = generate_summary_report(results)
    print(summary)

Extracting Data from Pages
^^^^^^^^^^^^^^^^^^^^^^^^^^

Crawlit provides built-in extractors for common data types:

Image Extraction
"""""""""""""""

Extract images and their attributes from web pages:

.. code-block:: python

    from crawlit import Crawler
    
    crawler = Crawler("https://example.com")
    crawler.crawl()
    results = crawler.get_results()
    
    # Process extracted images
    for url, page_data in results.items():
        if 'images' in page_data and page_data['images']:
            print(f"\nImages on {url}: {len(page_data['images'])}")
            
            for img in page_data['images']:
                print(f"- Source: {img['src']}")
                print(f"  Alt text: {img.get('alt', 'None')}")
                
                # Check if image has dimensions
                if 'width' in img and 'height' in img:
                    print(f"  Dimensions: {img['width']}x{img['height']}")
                
                # Check if image is likely decorative (missing alt text)
                if img.get('decorative', False):
                    print("  Warning: Missing alt text (accessibility issue)")

Each image is returned as a dictionary containing:

- ``src``: The image source URL
- ``alt``: Alternative text for the image (if any)
- ``title``: Title attribute (if any) 
- ``width`` and ``height``: Dimensions (if specified)
- ``class``: CSS class attributes
- ``decorative``: Boolean flag indicating if the image lacks alt text
- ``parent_tag``: The HTML tag containing the image

Table Extraction
"""""""""""""""

Command Line Interface
--------------------

Basic Examples
^^^^^^^^^^^

.. code-block:: bash

    # Basic crawling
    crawlit --url https://example.com
    
    # Set crawling depth
    crawlit --url https://example.com --depth 2
    
    # Save results to a specific file
    crawlit --url https://example.com --output myresults.json

Advanced Options
^^^^^^^^^^^^^

.. code-block:: bash

    # Full example with all options
    crawlit --url https://example.com \
            --depth 3 \
            --output-format json \
            --output results.json \
            --pretty-json \
            --delay 0.5 \
            --user-agent "MyCustomBot/1.0" \
            --allow-external \
            --ignore-robots \
            --verbose \
            --summary
