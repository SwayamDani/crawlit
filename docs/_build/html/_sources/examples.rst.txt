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
