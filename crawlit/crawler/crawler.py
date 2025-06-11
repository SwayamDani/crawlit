class Crawler:
    """Main crawler class that orchestrates the crawling process"""
    
    def __init__(
        self, 
        start_url, 
        max_depth=2, 
        respect_robots=True,
        extract_images=False,
        extract_keywords=False,
        extract_tables=False,
        max_urls=None,
        request_delay=0,
        max_retries=3,
        timeout=30,
        custom_headers=None,
        follow_redirects=True,
        verify_ssl=True,
        allow_query_params=True,
        user_agent=None,
        cookies=None,
        same_path_only=False  # New parameter to restrict to same path
    ):
        """Initialize the crawler with the given configuration"""
        self.engine = CrawlerEngine(
            start_url=start_url,
            max_depth=max_depth,
            respect_robots=respect_robots,
            extract_images=extract_images,
            extract_keywords=extract_keywords,
            extract_tables=extract_tables,
            max_urls=max_urls,
            request_delay=request_delay,
            max_retries=max_retries,
            timeout=timeout,
            custom_headers=custom_headers,
            follow_redirects=follow_redirects,
            verify_ssl=verify_ssl,
            allow_query_params=allow_query_params,
            user_agent=user_agent,
            cookies=cookies,
            same_path_only=same_path_only  # Pass the new parameter to the engine
        )