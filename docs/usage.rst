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
    
    # Save results in different formats
    save_results(results, "json", "crawl_results.json", pretty=True)
    save_results(results, "csv", "crawl_results.csv")
    save_results(results, "txt", "crawl_results.txt")
    

New Features in v0.2.0
---------------------

Table Extraction
^^^^^^^^^^^^^^^

Extract structured table data from HTML content with support for complex tables:

.. code-block:: python

    from crawlit import Crawler
    from crawlit.extractors.tables import extract_tables, tables_to_csv, tables_to_json, tables_to_dict

    # Option 1: Use the crawler
    crawler = Crawler(
        start_url="https://example.com",
        max_depth=2,
    )
    crawler.crawl()
    results = crawler.get_results()
    
    # Tables are automatically extracted and available in results
    for url, data in results.items():
        if 'tables' in data:
            print(f"Found {len(data['tables'])} tables on {url}")
    
    # Option 2: Extract tables directly from HTML content
    html_content = "<html>...</html>"  # Your HTML content here
    tables = extract_tables(html_content, min_rows=2, min_columns=2)
    
    # Convert tables to various formats
    tables_to_csv(tables, base_filename="extracted_tables", output_dir="output")
    tables_to_json(tables, base_filename="extracted_tables", output_dir="output")
    
    # Convert to dictionaries with headers
    table_dicts = tables_to_dict(tables)
    for table in table_dicts:
        print(table)  # List of dictionaries, one per row

Image Extraction
^^^^^^^^^^^^^^^

Extract and analyze images from web pages:

.. code-block:: python

    from crawlit import Crawler
    from crawlit.extractors.image_extractor import ImageTagParser
    
    # Option 1: Use the crawler
    crawler = Crawler(
        start_url="https://example.com",
        max_depth=2,
    )
    crawler.crawl()
    results = crawler.get_results()
    
    # Access extracted images
    for url, data in results.items():
        if 'images' in data:
            for img in data['images']:
                print(f"Image source: {img.get('src')}")
                print(f"Alt text: {img.get('alt', 'None')}")
                print(f"Dimensions: {img.get('width', 'N/A')}x{img.get('height', 'N/A')}")
                print(f"Decorative: {img.get('decorative', False)}")
    
    # Option 2: Extract images directly from HTML content
    parser = ImageTagParser()
    html_content = "<html><body><img src='example.jpg' alt='Example'></body></html>"
    parser.feed(html_content)
    images = parser.images
    
    for img in images:
        print(f"Image source: {img.get('src')}")

Keyword Extraction
^^^^^^^^^^^^^^^^

Extract and rank important keywords and phrases from web content:

.. code-block:: python

    from crawlit import Crawler
    from crawlit.extractors.keyword_extractor import KeywordExtractor
    
    # Option 1: Use the crawler
    crawler = Crawler(
        start_url="https://example.com",
        user_agent="crawlit/2.0",  # Using version 2.0 enables keyword extraction
        max_depth=2,
    )
    crawler.crawl()
    results = crawler.get_results()
    
    # Access extracted keywords
    for url, data in results.items():
        if 'keywords' in data:
            print(f"Keywords for {url}: {data['keywords']}")
        if 'keyphrases' in data:
            print(f"Key phrases: {data['keyphrases']}")
    
    # Option 2: Use the keyword extractor directly
    extractor = KeywordExtractor(min_word_length=4, max_keywords=10)
    html_content = "<html><body><h1>Example Page</h1><p>This is sample content for keyword extraction.</p></body></html>"
    
    # Extract keywords with scores
    keywords_data = extractor.extract_keywords(html_content, include_scores=True)
    print(f"Keywords: {keywords_data['keywords']}")
    print(f"Scores: {keywords_data['scores']}")
    
    # Extract keyphrases
    keyphrases = extractor.extract_keyphrases(html_content)
    print(f"Key phrases: {keyphrases}")

Command Line Interface
--------------------

Basic Usage
^^^^^^^^^^

The command-line interface provides access to all Crawlit features:

.. code-block:: bash

    # Basic usage
    crawlit --url https://example.com
    
    # Advanced options
    crawlit --url https://example.com \
            --depth 3 \
            --output-format json \
            --output results.json \
            --delay 0.5 \
            --user-agent "crawlit/1.0" \
            --ignore-robots

CLI for v0.2.0 Features
^^^^^^^^^^^^^^^^^^^^^

Table Extraction via CLI:

.. code-block:: bash

    # Extract tables from a website
    crawlit --url https://example.com \
            --user-agent "crawlit/2.0" \
            --extract-tables \
            --tables-output "./tables" \
            --tables-format csv \
            --min-rows 2 \
            --min-columns 2

Image Extraction via CLI:

.. code-block:: bash

    # Extract images from a website
    crawlit --url https://example.com \
            --user-agent "crawlit/2.0" \
            --extract-images \
            --images-output "./images"

Keyword Extraction via CLI:

.. code-block:: bash

    # Extract keywords from a website
    crawlit --url https://example.com \
            --user-agent "crawlit/2.0" \
            --extract-keywords \
            --keywords-output keywords.json \
            --max-keywords 30 \
            --min-word-length 4

Combined Features via CLI:

.. code-block:: bash

    # Use all extraction features together
    crawlit --url https://example.com \
            --user-agent "crawlit/2.0" \
            --depth 2 \
            --extract-tables \
            --tables-output "./tables" \
            --extract-images \
            --images-output "./images" \
            --extract-keywords \
            --keywords-output keywords.json
    
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
