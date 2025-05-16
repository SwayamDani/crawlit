Examples
========

This section provides real-world examples of using `crawlit`.

Basic Link Extraction
-------------------

.. code-block:: python

    from crawlit import Crawler, save_results

    # Create a crawler focused on link extraction
    crawler = Crawler(
        start_url="https://example.com",
        max_depth=2,
        internal_only=True
    )
    
    # Start crawling
    crawler.crawl()
    
    # Get the results
    results = crawler.get_results()
    
    # Extract all links from the crawled pages
    all_links = set()
    for url, data in results.items():
        if 'links' in data:
            all_links.update(data['links'])
    
    print(f"Found {len(all_links)} unique links")
    for link in sorted(all_links):
        print(f"- {link}")

Site Map Generation
-----------------

.. code-block:: python

    import json
    from crawlit import Crawler
    
    # Create a crawler for site mapping
    crawler = Crawler(
        start_url="https://example.com",
        max_depth=3,
        internal_only=True,
        delay=0.5
    )
    
Table Extraction (v0.2.0+)
------------------------

.. code-block:: python

    from crawlit import Crawler
    from crawlit.extractors.tables import extract_tables, tables_to_csv
    
    # Example 1: Extract tables directly from HTML
    html_content = """
    <html>
    <body>
        <table>
            <tr><th>Name</th><th>Age</th><th>City</th></tr>
            <tr><td>John</td><td>30</td><td>New York</td></tr>
            <tr><td>Alice</td><td>25</td><td>Los Angeles</td></tr>
        </table>
    </body>
    </html>
    """
    
    tables = extract_tables(html_content, min_rows=2, min_columns=2)
    print(f"Extracted {len(tables)} tables")
    
    # Save to CSV
    tables_to_csv(tables, base_filename="example_table", output_dir="output")
    
    # Example 2: Extract tables from crawled pages
    crawler = Crawler(
        start_url="https://example.com",
        max_depth=2,
    )
    crawler.crawl()
    results = crawler.get_results()
    
    for url, data in results.items():
        if 'tables' in data:
            print(f"Found {len(data['tables'])} tables on {url}")
    
Image Extraction (v0.2.0+)
-----------------------

.. code-block:: python

    from crawlit import Crawler
    from crawlit.extractors.image_extractor import ImageTagParser
    
    # Example 1: Analyze images on a website
    crawler = Crawler(
        start_url="https://example.com",
        max_depth=1
    )
    crawler.crawl()
    results = crawler.get_results()
    
    # Count images without alt text (accessibility issues)
    missing_alt = 0
    total_images = 0
    
    for url, data in results.items():
        if 'images' in data:
            page_images = data['images']
            total_images += len(page_images)
            
            for img in page_images:
                if img.get('decorative', False):
                    missing_alt += 1
                    
    print(f"Found {total_images} images, {missing_alt} missing alt text")
    
    # Example 2: Extract images from HTML
    parser = ImageTagParser()
    html_content = "<html><body><img src='logo.png' alt='Company Logo'></body></html>"
    parser.feed(html_content)
    
    for img in parser.images:
        print(f"Image URL: {img.get('src')}")
        print(f"Alt text: {img.get('alt', 'None')}")
        
Keyword Extraction (v0.2.0+)
-------------------------

.. code-block:: python

    from crawlit import Crawler
    from crawlit.extractors.keyword_extractor import KeywordExtractor
    
    # Example 1: Extract keywords from website pages
    crawler = Crawler(
        start_url="https://example.com",
        max_depth=1,
        user_agent="crawlit/2.0"  # Required for keyword extraction
    )
    crawler.crawl()
    results = crawler.get_results()
    
    # Analyze keywords across all pages
    all_keywords = {}
    
    for url, data in results.items():
        if 'keywords' in data:
            print(f"\nKeywords for {url}:")
            for keyword in data['keywords'][:5]:  # Show top 5
                print(f"- {keyword}")
                
            # Aggregate keywords
            for keyword in data['keywords']:
                if keyword not in all_keywords:
                    all_keywords[keyword] = 0
                all_keywords[keyword] += 1
    
    # Print most common keywords across site
    print("\nMost common keywords across site:")
    for keyword, count in sorted(all_keywords.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"- {keyword}: {count}")
        
    # Example 2: Direct keyword extraction
    extractor = KeywordExtractor(min_word_length=4, max_keywords=10)
    html_content = "<html><body><h1>Keyword Extraction</h1><p>This is an example of keyword extraction.</p></body></html>"
    
    keywords = extractor.extract_keywords(html_content, include_scores=True)
    print(f"\nExtracted keywords: {keywords['keywords']}")
    print(f"Keyword scores: {keywords['scores']}")
    
    # Start crawling
    crawler.crawl()
    
    # Get the results
    results = crawler.get_results()
    
    # Create a site map structure
    site_map = {}
    for url, data in results.items():
        site_map[url] = {
            'title': data.get('title', 'No title'),
            'outgoing_links': data.get('links', [])
        }
    
    # Save the site map to a JSON file
    with open('sitemap.json', 'w') as f:
        json.dump(site_map, f, indent=2)
    
    print(f"Site map saved to sitemap.json with {len(site_map)} pages")

See more examples in the ``examples/`` directory.
