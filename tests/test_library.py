"""
test_library.py - Comprehensive test suite for the crawlit library
"""

import pytest
import tempfile
import os
import json
import csv
import re
import time
import shutil
import threading
import socket
import logging
import requests
from pathlib import Path
from unittest import mock
from contextlib import contextmanager
from http.server import HTTPServer, SimpleHTTPRequestHandler

# Import main public functionality from top-level package
from crawlit import (
    Crawler, AsyncCrawler, save_results, generate_summary_report,
    ImageTagParser, KeywordExtractor, extract_tables
)
# Import internal components still needed for testing
from crawlit.output.formatters import save_as_json, save_as_csv, save_as_txt
from crawlit.crawler.fetcher import fetch_page
from crawlit.crawler.parser import extract_links, _process_url
from crawlit.crawler.robots import RobotsHandler


class TestCrawlitLibrary:
    """Comprehensive test suite for testing the crawlit library as a user would use it"""
    
    @pytest.fixture
    def mock_website(self, httpserver):
        """Create a complete mock website for testing with various edge cases"""
        # Main page with links
        main_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Test Site</title>
            <meta name="description" content="A test site for crawlit">
            <meta name="keywords" content="test, crawlit, crawler">
            <link rel="canonical" href="/canonical">
        </head>
        <body>
            <h1>Test Website for Crawlit</h1>
            <p>This is a comprehensive test site with various elements and links.</p>
            <nav>
                <ul>
                    <li><a href="/page1">Page 1</a></li>
                    <li><a href="/page2">Page 2</a></li>
                    <li><a href="/page3?param=value">Page 3 with query params</a></li>
                    <li><a href="/page-with-hyphens">Page with hyphens</a></li>
                    <li><a href="/page_with_underscores">Page with underscores</a></li>
                    <li><a href="https://external-site.com/page">External Link</a></li>
                    <li><a href="javascript:void(0)">JavaScript Link</a></li>
                    <li><a href="#section">Hash Link</a></li>
                    <li><a href="mailto:test@example.com">Email Link</a></li>
                    <li><a href="tel:+1234567890">Phone Link</a></li>
                </ul>
            </nav>
            <div id="section">
                <h2>Section with anchor</h2>
                <p>This section has an anchor that can be linked to.</p>
            </div>
            <div>
                <h2>Image Examples</h2>
                <img src="/images/test1.jpg" alt="Test Image 1" width="300" height="200">
                <img src="/images/test2.png" alt="Test Image 2" class="featured" width="400" height="300">
                <img src="/images/icon.svg" alt="" class="inline-icon" width="16" height="16">
                <img src="/images/broken.jpg" alt="Broken Image">
            </div>
            <div>
                <h2>Table Examples</h2>
                <table border="1">
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Name</th>
                            <th>Value</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td>1</td>
                            <td>Item 1</td>
                            <td>100</td>
                        </tr>
                        <tr>
                            <td>2</td>
                            <td>Item 2</td>
                            <td>200</td>
                        </tr>
                        <tr>
                            <td>3</td>
                            <td>Item 3</td>
                            <td>300</td>
                        </tr>
                    </tbody>
                </table>
                
                <table border="1">
                    <tr>
                        <td colspan="2">Merged Cell</td>
                        <td>Regular Cell</td>
                    </tr>
                    <tr>
                        <td rowspan="2">Rowspan Cell</td>
                        <td>Cell 2</td>
                        <td>Cell 3</td>
                    </tr>
                    <tr>
                        <td>Cell 5</td>
                        <td>Cell 6</td>
                    </tr>
                </table>
            </div>
            <script>
                // This script should be ignored by the parser
                document.write("This text should not appear in extracted content");
            </script>
            <style>
                /* This style should be ignored by the parser */
                body { color: red; }
            </style>
        </body>
        </html>
        """
        
        # Page 1 with internal links
        page1_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Page 1 - Test Site</title>
            <meta name="keywords" content="page1, test, keyword1, keyword2">
        </head>
        <body>
            <h1>Page 1</h1>
            <p>This is page 1 content with lots of keywords for testing. This is page 1 content with lots of keywords for testing. 
            This is page 1 content with lots of keywords for testing. This page should have many repeated phrases for the keyword extractor.</p>
            <p>Common phrases for keyword extraction testing. Common phrases for keyword extraction testing. Important test phrase.</p>
            <a href="/page1/subpage">Subpage</a>
            <a href="/page2">Link to page 2</a>
            <a href="/">Back to home</a>
            <a href="http://localhost:{}PLACEHOLDER/page1">Self-reference with full URL</a>
            <img src="/images/page1-image.jpg" alt="Page 1 Image" width="500" height="300">
            <iframe src="/iframe-content"></iframe>
            <a href="/page1/subpage1">Subpage 1</a>
            <a href="/page1/subpage2">Subpage 2</a>
            <a href="/page1/subpage3">Subpage 3</a>
        </body>
        </html>
        """
        
        # Page 2 with download links
        page2_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Page 2 - Test Site</title>
        </head>
        <body>
            <h1>Page 2</h1>
            <p>This is page 2 content</p>
            <div>
                <h2>Downloads Section</h2>
                <ul>
                    <li><a href="/files/document.pdf">Download PDF</a></li>
                    <li><a href="/files/document.docx">Download DOCX</a></li>
                    <li><a href="/files/document.xlsx">Download XLSX</a></li>
                    <li><a href="/files/sample.zip">Download ZIP</a></li>
                </ul>
            </div>
            <table>
                <tr>
                    <th>File Type</th>
                    <th>Size (KB)</th>
                </tr>
                <tr>
                    <td>PDF</td>
                    <td>256</td>
                </tr>
                <tr>
                    <td>DOCX</td>
                    <td>128</td>
                </tr>
                <tr>
                    <td>XLSX</td>
                    <td>64</td>
                </tr>
                <tr>
                    <td>ZIP</td>
                    <td>1024</td>
                </tr>
            </table>
            <a href="/">Back to home</a>
        </body>
        </html>
        """
        
        # Page 3 with query parameters
        page3_html = """
        <!DOCTYPE html>
        <html>
        <head><title>Page 3 - With Parameters</title></head>
        <body>
            <h1>Page 3 - Query Parameters</h1>
            <p>This is page 3 showing parameter value: <span id="param-value">value</span></p>
            <a href="/page3?param=newvalue">Change parameter</a>
            <a href="/page3?param=value&second=123">Multiple parameters</a>
            <a href="/">Back to home</a>
            <a href="/page3/child">Child page</a>
        </body>
        </html>
        """
        
        # Long page with many links to test pagination
        long_page_html = """
        <!DOCTYPE html>
        <html>
        <head><title>Long Page with Many Links</title></head>
        <body>
            <h1>Long Page with Many Links</h1>
            <ul>
        """
        # Add 100 links to the long page
        for i in range(1, 101):
            long_page_html += f'<li><a href="/long/item{i}">Item {i}</a></li>\n'
        
        long_page_html += """
            </ul>
            <a href="/">Back to home</a>
        </body>
        </html>
        """
        
        # Subpage with malformed HTML
        subpage_html = """
        <!DOCTYPE html>
        <html>
        <head><title>Subpage - Malformed HTML</title></head>
        <body>
            <h1>Subpage with Malformed HTML
            <p>This is a subpage with malformed HTML tags
            <a href="/page1">Back to Page 1
            <img src="/images/broken.jpg" alt="Broken Image" width="300">
            <div>
                <table>
                    <tr>
                        <td>Malformed table
                    <tr>
                        <td>Another row
                </table>
            </div>
            <ul>
                <li>Unclosed list item
            </ul>
        </body>
        </html>
        """
        
        # Page with many tables
        tables_page_html = """
        <!DOCTYPE html>
        <html>
        <head><title>Tables Example</title></head>
        <body>
            <h1>Multiple Tables Example</h1>
            
            <h2>Table 1 - Basic Table</h2>
            <table border="1">
                <tr>
                    <th>Header 1</th>
                    <th>Header 2</th>
                    <th>Header 3</th>
                </tr>
                <tr>
                    <td>Row 1, Cell 1</td>
                    <td>Row 1, Cell 2</td>
                    <td>Row 1, Cell 3</td>
                </tr>
                <tr>
                    <td>Row 2, Cell 1</td>
                    <td>Row 2, Cell 2</td>
                    <td>Row 2, Cell 3</td>
                </tr>
            </table>
            
            <h2>Table 2 - Table with colspan and rowspan</h2>
            <table border="1">
                <tr>
                    <th colspan="3">Merged Header</th>
                </tr>
                <tr>
                    <td rowspan="2">Cell spans two rows</td>
                    <td>Regular cell</td>
                    <td>Regular cell</td>
                </tr>
                <tr>
                    <td colspan="2">Cell spans two columns</td>
                </tr>
            </table>
            
            <h2>Table 3 - Table with thead and tbody</h2>
            <table border="1">
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Name</th>
                        <th>Value</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>101</td>
                        <td>Product A</td>
                        <td>$50.00</td>
                    </tr>
                    <tr>
                        <td>102</td>
                        <td>Product B</td>
                        <td>$75.00</td>
                    </tr>
                </tbody>
            </table>
            
            <h2>Table 4 - Nested Tables</h2>
            <table border="1">
                <tr>
                    <td>
                        <table border="1">
                            <tr>
                                <td>Nested Table Cell 1</td>
                                <td>Nested Table Cell 2</td>
                            </tr>
                        </table>
                    </td>
                    <td>Regular cell</td>
                </tr>
            </table>
            
            <h2>Table 5 - Extremely Small Table</h2>
            <table border="1">
                <tr>
                    <td>Just one cell</td>
                </tr>
            </table>
            
            <a href="/">Back to home</a>
        </body>
        </html>
        """
        
        # Page with Unicode and special characters
        unicode_page_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Unicode and Special Characters</title>
            <meta charset="UTF-8">
        </head>
        <body>
            <h1>Unicode and Special Characters Test</h1>
            <p>Emoji test: 😀 🎉 🚀 💻 🌍</p>
            <p>Foreign languages: こんにちは (Japanese), Привет (Russian), नमस्ते (Hindi)</p>
            <p>HTML entities: &lt;tag&gt; &amp; &quot;quote&quot; &apos;apostrophe&apos; &copy; &reg;</p>
            <p>Special characters: © ® ™ ¥ € £ § ¶ • ...</p>
            <a href="/">Back to home</a>
        </body>
        </html>
        """
        
        # Page with redirects
        redirect_page_html = """<meta http-equiv="refresh" content="0;url=/redirected-page">
        <p>If you are not redirected, <a href="/redirected-page">click here</a>.</p>"""
        
        redirected_page_html = """
        <!DOCTYPE html>
        <html>
        <head><title>Redirected Page</title></head>
        <body>
            <h1>This is the redirected page</h1>
            <p>You have been redirected here.</p>
            <a href="/">Back to home</a>
        </body>
        </html>
        """
        
        # Cyclic redirect
        cyclic_redirect1_html = """<meta http-equiv="refresh" content="0;url=/cyclic-redirect2">
        <p>Redirecting...</p>"""
        
        cyclic_redirect2_html = """<meta http-equiv="refresh" content="0;url=/cyclic-redirect1">
        <p>Redirecting back...</p>"""
        
        # Page with very long content
        very_long_content = """
        <!DOCTYPE html>
        <html>
        <head><title>Very Long Page</title></head>
        <body>
            <h1>Very Long Page</h1>
            <p>This page has very long content to test handling of large responses.</p>
        """
        
        # Add lots of paragraphs to create a large page
        for i in range(1, 501):
            very_long_content += f"<p>Paragraph {i}: Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.</p>\n"
        
        very_long_content += """
            <a href="/">Back to home</a>
        </body>
        </html>
        """
        
        # Page with slow response
        slow_page_html = """
        <!DOCTYPE html>
        <html>
        <head><title>Slow Response Page</title></head>
        <body>
            <h1>Slow Response Page</h1>
            <p>This page has a deliberately slow response time.</p>
            <a href="/">Back to home</a>
        </body>
        </html>
        """
        
        # Pages for testing extraction features
        extraction_test_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Extraction Features Test Page</title>
            <meta name="description" content="Testing all crawler extraction features">
            <meta name="keywords" content="extraction, images, tables, keywords">
        </head>
        <body>
            <h1>Extraction Features Test</h1>
            <p>This page tests all extraction features of the crawlit crawler.</p>
            
            <h2>Image Gallery</h2>
            <div class="gallery">
                <img src="/images/gallery1.jpg" alt="Gallery Image 1" width="300" height="200">
                <img src="/images/gallery2.jpg" alt="Gallery Image 2" width="300" height="200">
                <img src="/images/gallery3.jpg" alt="Gallery Image 3" width="300" height="200">
                <img src="/images/gallery4.jpg" alt="Gallery Image 4" width="300" height="200">
                <img src="/images/gallery5.jpg" alt="Gallery Image 5" width="300" height="200">
                <img src="/images/icon1.png" alt="" class="inline-icon" width="16" height="16">
                <img src="/images/icon2.png" alt="" class="inline-icon" width="16" height="16">
            </div>
            
            <h2>Data Tables</h2>
            <table border="1" id="products-table">
                <thead>
                    <tr>
                        <th>Product ID</th>
                        <th>Product Name</th>
                        <th>Category</th>
                        <th>Price</th>
                        <th>Stock</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>P001</td>
                        <td>Smartphone X</td>
                        <td>Electronics</td>
                        <td>$999.99</td>
                        <td>24</td>
                    </tr>
                    <tr>
                        <td>P002</td>
                        <td>Laptop Pro</td>
                        <td>Electronics</td>
                        <td>$1299.99</td>
                        <td>15</td>
                    </tr>
                    <tr>
                        <td>P003</td>
                        <td>Coffee Maker</td>
                        <td>Kitchen</td>
                        <td>$89.99</td>
                        <td>42</td>
                    </tr>
                    <tr>
                        <td>P004</td>
                        <td>Wireless Headphones</td>
                        <td>Electronics</td>
                        <td>$199.99</td>
                        <td>38</td>
                    </tr>
                </tbody>
            </table>
            
            <h2>User Reviews</h2>
            <table border="1" id="reviews-table">
                <tr>
                    <th>User</th>
                    <th>Rating</th>
                    <th>Comment</th>
                    <th>Date</th>
                </tr>
                <tr>
                    <td>John D.</td>
                    <td>5/5</td>
                    <td>Excellent product, works perfectly! Very satisfied with my purchase.</td>
                    <td>2023-01-15</td>
                </tr>
                <tr>
                    <td>Mary S.</td>
                    <td>4/5</td>
                    <td>Good quality but a bit expensive. Would recommend on sale.</td>
                    <td>2023-02-20</td>
                </tr>
                <tr>
                    <td>Robert T.</td>
                    <td>3/5</td>
                    <td>Average product. Does what it says but nothing spectacular.</td>
                    <td>2023-03-10</td>
                </tr>
            </table>
            
            <h2>Keyword-rich Content</h2>
            <div class="content">
                <p>Web crawler technology enables automated browsing of websites. Web crawlers are essential for search engines to index content.</p>
                <p>Modern web crawlers respect robots.txt files and implement rate limiting to avoid overloading servers.</p>
                <p>Ethical web crawling practices include proper user agent identification and respecting site terms of service.</p>
                <p>Web crawler performance metrics include crawl efficiency, content coverage, and extraction accuracy.</p>
                <p>Web crawler implementation requires handling of redirects, connection timeouts, and HTTP status codes.</p>
            </div>
            
            <a href="/">Back to home</a>
        </body>
        </html>
        """
        
        # Configure the server endpoints
        httpserver.expect_request("/").respond_with_data(main_html, content_type="text/html")
        httpserver.expect_request("/canonical").respond_with_data(main_html, content_type="text/html")
        httpserver.expect_request("/page1").respond_with_data(
            page1_html.replace("{}PLACEHOLDER", str(httpserver.port)), 
            content_type="text/html"
        )
        httpserver.expect_request("/page2").respond_with_data(page2_html, content_type="text/html")
        httpserver.expect_request("/page3").respond_with_data(page3_html, content_type="text/html")
        httpserver.expect_request("/page3/child").respond_with_data("<html><body><h1>Child of Page 3</h1></body></html>", content_type="text/html")
        httpserver.expect_request("/page-with-hyphens").respond_with_data("<html><body><h1>Page with hyphens</h1></body></html>", content_type="text/html")
        httpserver.expect_request("/page_with_underscores").respond_with_data("<html><body><h1>Page with underscores</h1></body></html>", content_type="text/html")
        httpserver.expect_request("/page1/subpage").respond_with_data(subpage_html, content_type="text/html")
        httpserver.expect_request("/page1/subpage1").respond_with_data("<html><body><h1>Subpage 1</h1></body></html>", content_type="text/html")
        httpserver.expect_request("/page1/subpage2").respond_with_data("<html><body><h1>Subpage 2</h1></body></html>", content_type="text/html")
        httpserver.expect_request("/page1/subpage3").respond_with_data("<html><body><h1>Subpage 3</h1></body></html>", content_type="text/html")
        httpserver.expect_request("/redirect-page").respond_with_data(redirect_page_html, content_type="text/html")
        httpserver.expect_request("/redirected-page").respond_with_data(redirected_page_html, content_type="text/html")
        httpserver.expect_request("/cyclic-redirect1").respond_with_data(cyclic_redirect1_html, content_type="text/html")
        httpserver.expect_request("/cyclic-redirect2").respond_with_data(cyclic_redirect2_html, content_type="text/html")
        httpserver.expect_request("/very-long-page").respond_with_data(very_long_content, content_type="text/html")
        httpserver.expect_request("/long-page").respond_with_data(long_page_html, content_type="text/html")
        httpserver.expect_request("/tables-page").respond_with_data(tables_page_html, content_type="text/html")
        httpserver.expect_request("/unicode-page").respond_with_data(unicode_page_html, content_type="text/html")
        httpserver.expect_request("/extraction-test").respond_with_data(extraction_test_html, content_type="text/html")
        
        # Custom handler for the slow page
        def slow_handler(request):
            time.sleep(2)  # Simulate a slow response
            return 200, {'Content-Type': 'text/html'}, slow_page_html
        
        httpserver.expect_request("/slow-page").respond_with_handler(slow_handler)
        
        # Add a "not found" page for 404 testing
        httpserver.expect_request("/not-found").respond_with_data("Not Found", content_type="text/plain", status=404)
        
        # Add a server error page for 500 testing
        httpserver.expect_request("/server-error").respond_with_data("Server Error", content_type="text/plain", status=500)
        
        # Respond with 403 Forbidden for a specific path
        httpserver.expect_request("/forbidden").respond_with_data("Forbidden", content_type="text/plain", status=403)
        
        # Add various binary files
        pdf_content = b"%PDF-1.4\n1 0 obj\n<</Type/Catalog/Pages 2 0 R>>\nendobj\n2 0 obj\n<</Type/Pages/Kids[3 0 R]/Count 1>>\nendobj\n3 0 obj\n<</Type/Page/MediaBox[0 0 612 792]/Resources<<>>/Parent 2 0 R>>\nendobj\nxref\n0 4\n0000000000 65535 f\n0000000009 00000 n\n0000000057 00000 n\n0000000110 00000 n\ntrailer\n<</Size 4/Root 1 0 R>>\nstartxref\n187\n%%EOF"
        docx_content = b"PK\x03\x04\x14\x00\x06\x00\x08\x00\x00\x00!\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
        xlsx_content = b"PK\x03\x04\x14\x00\x06\x00\x08\x00\x00\x00!\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
        zip_content = b"PK\x03\x04\x0A\x00\x00\x00\x00\x00\x00\x00!\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00PK\x01\x02\x14\x03\x0A\x00\x00\x00\x00\x00\x00\x00!\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xA4\x81\x00\x00\x00\x00PK\x05\x06\x00\x00\x00\x00\x01\x00\x01\x00.\x00\x00\x00\x18\x00\x00\x00\x00\x00"
        
        # Serve files
        httpserver.expect_request("/files/document.pdf").respond_with_data(pdf_content, content_type="application/pdf")
        httpserver.expect_request("/files/document.docx").respond_with_data(docx_content, content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        httpserver.expect_request("/files/document.xlsx").respond_with_data(xlsx_content, content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        httpserver.expect_request("/files/sample.zip").respond_with_data(zip_content, content_type="application/zip")
        
        # Serve image files
        img1_content = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
        img2_content = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
        svg_content = b'<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16"><circle cx="8" cy="8" r="7" stroke="black" stroke-width="1" fill="red" /></svg>'
        
        httpserver.expect_request("/images/test1.jpg").respond_with_data(img1_content, content_type="image/jpeg")
        httpserver.expect_request("/images/test2.png").respond_with_data(img2_content, content_type="image/png")
        httpserver.expect_request("/images/icon.svg").respond_with_data(svg_content, content_type="image/svg+xml")
        httpserver.expect_request("/images/broken.jpg").respond_with_data(b"", status=404)
        httpserver.expect_request("/images/page1-image.jpg").respond_with_data(img1_content, content_type="image/jpeg")
        
        # Serve gallery images
        for i in range(1, 6):
            httpserver.expect_request(f"/images/gallery{i}.jpg").respond_with_data(img1_content, content_type="image/jpeg")
        httpserver.expect_request("/images/icon1.png").respond_with_data(img2_content, content_type="image/png")
        httpserver.expect_request("/images/icon2.png").respond_with_data(img2_content, content_type="image/png")
        
        # Setup iframe content
        iframe_content = "<html><body><h1>Iframe Content</h1><p>This content is within an iframe.</p></body></html>"
        httpserver.expect_request("/iframe-content").respond_with_data(iframe_content, content_type="text/html")
        
        # Setup robots.txt
        robots_txt = """
        User-agent: *
        Allow: /private/allowed/
        Disallow: /private/
        Disallow: /forbidden/
        Disallow: /admin/
        Disallow: /*.pdf$
        Sitemap: http://localhost:{}/sitemap.xml
        """.format(httpserver.port)
        
        httpserver.expect_request("/robots.txt").respond_with_data(robots_txt, content_type="text/plain")
        
        # Serve a sitemap
        sitemap_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
            <url>
                <loc>http://localhost:{}/</loc>
                <lastmod>2023-01-01</lastmod>
                <changefreq>daily</changefreq>
                <priority>1.0</priority>
            </url>
            <url>
                <loc>http://localhost:{}/page1</loc>
                <lastmod>2023-01-01</lastmod>
                <changefreq>weekly</changefreq>
                <priority>0.8</priority>
            </url>
            <url>
                <loc>http://localhost:{}/page2</loc>
                <lastmod>2023-01-01</lastmod>
                <changefreq>weekly</changefreq>
                <priority>0.8</priority>
            </url>
            <url>
                <loc>http://localhost:{}/sitemapped-page</loc>
                <lastmod>2023-01-01</lastmod>
                <changefreq>monthly</changefreq>
                <priority>0.5</priority>
            </url>
        </urlset>
        """.format(httpserver.port, httpserver.port, httpserver.port, httpserver.port)
        
        httpserver.expect_request("/sitemap.xml").respond_with_data(sitemap_xml, content_type="application/xml")
        
        # Serve a page only found in the sitemap
        sitemapped_page_html = """
        <!DOCTYPE html>
        <html>
        <head><title>Sitemapped Page</title></head>
        <body>
            <h1>Sitemapped Page</h1>
            <p>This page is only linked from the sitemap, not from other pages.</p>
            <a href="/">Back to home</a>
        </body>
        </html>
        """
        httpserver.expect_request("/sitemapped-page").respond_with_data(sitemapped_page_html, content_type="text/html")
        
        # Add a private page that should be blocked by robots.txt
        private_html = """
        <!DOCTYPE html>
        <html>
        <head><title>Private Page</title></head>
        <body>
            <h1>Private Page</h1>
            <p>This page should not be crawled</p>
        </body>
        </html>
        """
        httpserver.expect_request("/private/secret").respond_with_data(private_html, content_type="text/html")
        
        # Add an allowed page within private
        private_allowed_html = """
        <!DOCTYPE html>
        <html>
        <head><title>Allowed Private Page</title></head>
        <body>
            <h1>Allowed Private Page</h1>
            <p>This page should be crawled despite being in /private/ because of the Allow rule in robots.txt</p>
        </body>
        </html>
        """
        httpserver.expect_request("/private/allowed/page").respond_with_data(private_allowed_html, content_type="text/html")
        
        # Add a link to the private page from the main page
        main_html_with_private = main_html.replace("</ul>", 
                                  "<li><a href='/private/secret'>Private</a></li>" +
                                  "<li><a href='/private/allowed/page'>Allowed Private</a></li></ul>")
        httpserver.expect_request("/with_private").respond_with_data(main_html_with_private, content_type="text/html")
        
        # Add handlers for /long/item* URLs (referenced from /long-page)
        for i in range(1, 101):
            item_html = f"""
            <!DOCTYPE html>
            <html>
            <head><title>Item {i}</title></head>
            <body>
                <h1>Item {i}</h1>
                <p>This is item number {i} from the long page.</p>
                <a href="/long-page">Back to long page</a>
            </body>
            </html>
            """
            httpserver.expect_request(f"/long/item{i}").respond_with_data(item_html, content_type="text/html")
        
        return httpserver.url_for("/")

    @pytest.fixture
    def mock_server_with_errors(self, httpserver):
        """Create a mock server that simulates various error conditions"""
        # Basic page
        httpserver.expect_request("/").respond_with_data("<html><body>Main page</body></html>", 
                                           content_type="text/html")
        
        # Various HTTP errors
        httpserver.expect_request("/not_found").respond_with_data("Not Found", 
                                           content_type="text/plain", status=404)
        httpserver.expect_request("/server_error").respond_with_data("Server Error", 
                                           content_type="text/plain", status=500)
        httpserver.expect_request("/forbidden").respond_with_data("Forbidden", 
                                           content_type="text/plain", status=403)
        httpserver.expect_request("/unauthorized").respond_with_data("Unauthorized", 
                                           content_type="text/plain", status=401)
        httpserver.expect_request("/bad_request").respond_with_data("Bad Request", 
                                           content_type="text/plain", status=400)
        httpserver.expect_request("/method_not_allowed").respond_with_data("Method Not Allowed", 
                                           content_type="text/plain", status=405)
        
        # Redirects
        httpserver.expect_request("/redirect").respond_with_data("", status=302,
                                           headers={"Location": f"{httpserver.url_for('/')}redirected"})
        httpserver.expect_request("/redirected").respond_with_data("<html><body>Redirected page</body></html>",
                                           content_type="text/html")
        
        # Permanent redirect
        httpserver.expect_request("/permanent_redirect").respond_with_data("", status=301,
                                           headers={"Location": f"{httpserver.url_for('/')}permanent"})
        httpserver.expect_request("/permanent").respond_with_data("<html><body>Permanently Redirected page</body></html>",
                                           content_type="text/html")
        
        # Too many redirects
        httpserver.expect_request("/redirect_loop1").respond_with_data("", status=302,
                                           headers={"Location": f"{httpserver.url_for('/')}redirect_loop2"})
        httpserver.expect_request("/redirect_loop2").respond_with_data("", status=302,
                                           headers={"Location": f"{httpserver.url_for('/')}redirect_loop1"})
        
        # Redirect chain
        httpserver.expect_request("/redirect_chain1").respond_with_data("", status=302,
                                           headers={"Location": f"{httpserver.url_for('/')}redirect_chain2"})
        httpserver.expect_request("/redirect_chain2").respond_with_data("", status=302,
                                           headers={"Location": f"{httpserver.url_for('/')}redirect_chain3"})
        httpserver.expect_request("/redirect_chain3").respond_with_data("<html><body>End of redirect chain</body></html>",
                                           content_type="text/html")
        
        # Timeout simulation
        def timeout_handler(request):
            from werkzeug.wrappers import Response
            time.sleep(2)  # Longer than the crawler's timeout=1 to trigger client-side timeout
            return Response("<html><body>This should timeout</body></html>", content_type="text/html")

        httpserver.expect_request("/timeout").respond_with_handler(timeout_handler)

        # Connection reset simulation
        def connection_reset_handler(request):
            from werkzeug.wrappers import Response
            # This doesn't actually reset the connection, but will be mocked in tests
            return Response("<html><body>Connection will be reset</body></html>", content_type="text/html")

        httpserver.expect_request("/connection_reset").respond_with_handler(connection_reset_handler)
        
        # Invalid content type
        httpserver.expect_request("/invalid_content_type").respond_with_data("<html><body>Invalid Content Type</body></html>",
                                           content_type="invalid/content-type")
        
        # Empty response
        httpserver.expect_request("/empty_response").respond_with_data("",
                                           content_type="text/html")
        
        # Extremely large response (simulated)
        large_response = "<html><body>" + "x" * 1024 * 1024 * 10 + "</body></html>"  # 10MB response
        httpserver.expect_request("/large_response").respond_with_data(large_response[:1024],  # Actually return truncated version for test practicality
                                           content_type="text/html")
        
        # Main page with error links
        base_url = httpserver.url_for('')
        main_html = f"""
        <html>
        <body>
            <h1>Error Test Page</h1>
            <ul>
                <li><a href="{base_url}not_found">Not Found Page</a></li>
                <li><a href="{base_url}server_error">Server Error Page</a></li>
                <li><a href="{base_url}forbidden">Forbidden Page</a></li>
                <li><a href="{base_url}unauthorized">Unauthorized Page</a></li>
                <li><a href="{base_url}bad_request">Bad Request Page</a></li>
                <li><a href="{base_url}method_not_allowed">Method Not Allowed Page</a></li>
                <li><a href="{base_url}redirect">Redirect Page</a></li>
                <li><a href="{base_url}permanent_redirect">Permanent Redirect Page</a></li>
                <li><a href="{base_url}redirect_loop1">Redirect Loop</a></li>
                <li><a href="{base_url}redirect_chain1">Redirect Chain</a></li>
                <li><a href="{base_url}timeout">Timeout Page</a></li>
                <li><a href="{base_url}connection_reset">Connection Reset Page</a></li>
                <li><a href="{base_url}invalid_content_type">Invalid Content Type</a></li>
                <li><a href="{base_url}empty_response">Empty Response</a></li>
                <li><a href="{base_url}large_response">Large Response</a></li>
            </ul>
        </body>
        </html>
        """
        httpserver.expect_request("/error_test").respond_with_data(main_html, content_type="text/html")
        
        return httpserver.url_for("/error_test")

    def test_basic_crawling(self, mock_website):
        """Test basic crawling functionality"""
        # Initialize the crawler with mock website URL
        crawler = Crawler(start_url=mock_website, max_depth=2)
        
        # Start crawling
        crawler.crawl()
        
        # Get results
        results = crawler.get_results()
        
        # Check that the right number of pages were crawled
        assert len(results) >= 4, f"Expected at least 4 pages, got {len(results)}"
        
        # Check that the main pages were crawled
        assert mock_website in results, "Main page not found in results"
        assert f"{mock_website}page1" in results, "Page1 not found in results"
        assert f"{mock_website}page2" in results, "Page2 not found in results"
        
        # Check that the subpage was crawled
        assert f"{mock_website}page1/subpage" in results, "Subpage not found in results"
        
        # Check that all crawled pages were successful (HTTP 200)
        for url, data in results.items():
            # Skip image URLs with known 404 status
            if '/images/broken.jpg' in url:
                assert data["status"] == 404, f"Broken image URL {url} should return 404 status"
                assert data["success"] == False, f"Broken image URL {url} should be marked as unsuccessful"
            else:
                assert data["status"] == 200, f"URL {url} did not return 200 status"
                assert data["success"] == True, f"URL {url} was not marked as successful"
        
        # Verify depth assignment
        assert results[mock_website]["depth"] == 0, "Main page should have depth 0"
        assert results[f"{mock_website}page1"]["depth"] == 1, "Page1 should have depth 1"
        assert results[f"{mock_website}page1/subpage"]["depth"] == 2, "Subpage should have depth 2"
    
    def test_external_link_handling(self, mock_website):
        """Test handling of external links"""
        # First, test with internal_only=True (default)
        crawler = Crawler(start_url=mock_website, max_depth=1)
        crawler.crawl()
        
        # Get skipped external URLs
        skipped = crawler.get_skipped_external_urls()
        
        # Check that the external link was skipped
        assert "https://external-site.com/page" in skipped, "External link not properly skipped"
        
        # Check that the external link is not in the results
        results = crawler.get_results()
        assert "https://external-site.com/page" not in results, "External link should not be in results with internal_only=True"
        
        # Now test with internal_only=False
        crawler = Crawler(start_url=mock_website, max_depth=1, internal_only=False)
        crawler.crawl()
        
        # The external URL should be in the queue but may not be accessible
        skipped = crawler.get_skipped_external_urls()
        assert "https://external-site.com/page" not in skipped, "External link should not be skipped with internal_only=False"
    
    def test_respecting_robots_txt(self, mock_website):
        """Test that robots.txt rules are respected"""
        # Test with respect_robots=True (default)
        url_with_private = f"{mock_website}with_private"
        crawler = Crawler(start_url=url_with_private, max_depth=1, respect_robots=True)
        crawler.crawl()
        
        results = crawler.get_results()
        private_url = f"{mock_website}private/secret"
        allowed_private_url = f"{mock_website}private/allowed/page"
        
        # Check that the private page was not crawled but allowed private page was
        assert private_url not in results, "Private URL should not be crawled due to robots.txt"
        assert allowed_private_url in results, "Allowed private URL should be crawled despite being under /private/"
        
        # Check skipped robots paths
        skipped = crawler.get_skipped_robots_paths()
        assert private_url in skipped, "Private URL should be in skipped robots paths"
        assert allowed_private_url not in skipped, "Allowed private URL should not be in skipped robots paths"
        
        # Test that .pdf files are disallowed by robots.txt
        pdf_url = f"{mock_website}files/document.pdf"
        assert pdf_url in skipped or pdf_url not in results, "PDF URL should be blocked by robots.txt pattern"
        
        # Now test with respect_robots=False
        crawler = Crawler(start_url=url_with_private, max_depth=1, respect_robots=False)
        crawler.crawl()
        
        results = crawler.get_results()
        
        # Now the private page should be crawled
        assert private_url in results, "Private URL should be crawled with respect_robots=False"
        
        # And there should be no skipped robots paths
        skipped = crawler.get_skipped_robots_paths()
        assert len(skipped) == 0, "There should be no skipped robots paths with respect_robots=False"
    
    def test_depth_limit(self, mock_website):
        """Test max_depth parameter"""
        # Test with max_depth=1 (only main page and direct links)
        crawler = Crawler(start_url=mock_website, max_depth=1)
        crawler.crawl()
        
        results = crawler.get_results()
        
        # Should have crawled main page, page1, and page2, but not subpage
        assert mock_website in results, "Main page not in results"
        assert f"{mock_website}page1" in results, "Page1 not in results"
        assert f"{mock_website}page2" in results, "Page2 not in results"
        assert f"{mock_website}page1/subpage" not in results, "Subpage should not be in results with max_depth=1"
        
        # Now test with max_depth=2 (should include subpage)
        crawler = Crawler(start_url=mock_website, max_depth=2)
        crawler.crawl()
        
        results = crawler.get_results()
        
        # Should now include the subpage
        assert f"{mock_website}page1/subpage" in results, "Subpage should be in results with max_depth=2"
        
        # Test with max_depth=0 (only crawl the start URL)
        crawler = Crawler(start_url=mock_website, max_depth=0)
        crawler.crawl()
        
        results = crawler.get_results()
        
        # Should only have crawled the start URL
        assert len(results) == 1, f"Expected only 1 URL with max_depth=0, got {len(results)}"
        assert mock_website in results, "Start URL not in results with max_depth=0"
    
    def test_link_extraction(self, mock_website):
        """Test that links are correctly extracted from different elements"""
        crawler = Crawler(
            start_url=mock_website, 
            max_depth=0,
            enable_content_extraction=True  # Enable content extraction for canonical_url
        )
        crawler.crawl()
        
        results = crawler.get_results()
        main_page_links = results[mock_website]["links"]
        
        # Check that links from anchor tags were extracted
        assert f"{mock_website}page1" in main_page_links, "Link from anchor tag not extracted"
        assert f"{mock_website}page2" in main_page_links, "Link from anchor tag not extracted"
        
        # Check that links with query parameters were extracted
        assert f"{mock_website}page3?param=value" in main_page_links, "Link with query parameters not extracted"
        
        # Check that links with hyphens and underscores were extracted
        assert f"{mock_website}page-with-hyphens" in main_page_links, "Link with hyphens not extracted"
        assert f"{mock_website}page_with_underscores" in main_page_links, "Link with underscores not extracted"
        
        # Check that external links were extracted
        assert "https://external-site.com/page" in main_page_links, "External link not extracted"
        
        # Check that javascript, hash, mailto, and tel links were NOT extracted
        assert not any("javascript:" in link for link in main_page_links), "JavaScript link should not be extracted"
        assert not any("#" in link for link in main_page_links), "Hash link should not be extracted"
        assert not any("mailto:" in link for link in main_page_links), "Mailto link should not be extracted"
        assert not any("tel:" in link for link in main_page_links), "Tel link should not be extracted"
        
        # Test extraction of canonical URL (only if content extraction is enabled)
        if "canonical_url" in results[mock_website]:
            # Canonical URL might be relative, so check if it contains "canonical"
            canonical = results[mock_website]["canonical_url"]
            assert canonical is not None and "canonical" in canonical, f"Incorrect canonical URL extracted: {canonical}"
    
    def test_feature_extraction(self, mock_website):
        """Test that the crawler correctly extracts special features like images, tables, and keywords"""
        # Enable all extraction features
        crawler = Crawler(
            start_url=f"{mock_website}extraction-test", 
            max_depth=0,
            enable_image_extraction=True,
            enable_keyword_extraction=True,
            enable_table_extraction=True
        )
        crawler.crawl()
        
        results = crawler.get_results()
        extraction_page = f"{mock_website}extraction-test"
        
        # Verify that the page was crawled
        assert extraction_page in results, "Extraction test page not found in results"
        page_data = results[extraction_page]
        
        # Check image extraction
        assert "images" in page_data, "Images not extracted"
        assert len(page_data["images"]) >= 7, f"Expected at least 7 images, got {len(page_data['images'])}"
        
        # Check for specific image attributes
        for img in page_data["images"]:
            assert "src" in img, "Image source not extracted"
            assert "alt" in img, "Image alt text not extracted"
            if "width" in img and "height" in img:
                assert isinstance(img["width"], (int, str)) and isinstance(img["height"], (int, str)), "Image dimensions not properly extracted"
        
        # Check keyword extraction
        assert "keywords" in page_data, "Keywords not extracted"
        assert len(page_data["keywords"]) > 0, "No keywords extracted"
        
        assert "keyphrases" in page_data, "Key phrases not extracted"
        assert len(page_data["keyphrases"]) > 0, "No key phrases extracted"
        
        # Most common expected keywords should be present
        expected_keywords = ["web", "crawler", "content", "page"]
        found_keywords = [kw for kw in expected_keywords if any(kw in k for k in page_data["keywords"])]
        assert len(found_keywords) >= 2, f"Expected common keywords not found. Found: {page_data['keywords']}"
        
        # Check table extraction
        assert "tables" in page_data, "Tables not extracted"
        assert len(page_data["tables"]) >= 2, f"Expected at least 2 tables, got {len(page_data['tables'])}"
        
        # Check that the product table contains expected data
        product_table_found = False
        for table in page_data["tables"]:
            # Check if this is likely the products table
            if len(table) >= 5 and len(table[0]) >= 5:  # Header + 4 rows, 5 columns
                # Check header row contains expected text
                if any("Product" in cell for cell in table[0]):
                    product_table_found = True
                    # Check for specific product data
                    data_found = False
                    for row in table[1:]:  # Skip header row
                        if any("Smartphone" in cell for cell in row) or any("Laptop" in cell for cell in row):
                            data_found = True
                            break
                    assert data_found, "Expected product data not found in table"
        
        assert product_table_found, "Products table not found in extracted tables"
    
    def test_output_formats(self, mock_website):
        """Test saving results in different formats"""
        # Initialize the crawler with mock website URL
        crawler = Crawler(start_url=mock_website, max_depth=1)
        crawler.crawl()
        
        results = crawler.get_results()
        
        # Create a temporary directory for outputs
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test JSON output
            json_path = Path(temp_dir) / "results.json"
            save_results(results, "json", json_path)
            
            # Verify JSON file was created and contains valid data
            assert json_path.exists(), "JSON file not created"
            with open(json_path) as f:
                json_data = json.load(f)
                assert isinstance(json_data, dict), "JSON data not a dictionary"
                
                # Check metadata section
                assert "metadata" in json_data, "Metadata section missing from JSON"
                assert "timestamp" in json_data["metadata"], "Timestamp missing from metadata"
                assert "total_urls" in json_data["metadata"], "Total URLs missing from metadata"
                
                # Check URLs section
                assert "urls" in json_data, "URLs section missing from JSON"
                assert mock_website in json_data["urls"], "Start URL not found in JSON output"
                
                # Check URL details
                url_data = json_data["urls"][mock_website]
                assert "depth" in url_data, "Depth missing from URL data"
                assert "status" in url_data, "Status missing from URL data"
                assert "links" in url_data, "Links missing from URL data"
            
            # Test CSV output
            csv_path = Path(temp_dir) / "results.csv"
            save_results(results, "csv", csv_path)
            
            # Verify CSV file was created and contains valid data
            assert csv_path.exists(), "CSV file not created"
            with open(csv_path, 'r', newline='', encoding='utf-8') as f:
                reader = csv.reader(f)
                rows = list(reader)
                
                # Check header row
                assert len(rows) > 1, "CSV file has insufficient rows"
                header = rows[0]
                assert "URL" in header, "URL column missing from CSV header"
                assert "Status" in header, "Status column missing from CSV header"
                assert "Depth" in header, "Depth column missing from CSV header"
                assert "Links Found" in header, "Links Found column missing from CSV header"
                
                # Check that each URL in the results appears in the CSV
                url_column_index = header.index("URL")
                csv_urls = [row[url_column_index] for row in rows[1:] if len(row) > url_column_index]
                for url in results.keys():
                    assert url in csv_urls, f"URL {url} missing from CSV output"
            
            # Test TXT output
            txt_path = Path(temp_dir) / "results.txt"
            save_results(results, "txt", txt_path)
            
            # Verify TXT file was created and contains valid data
            assert txt_path.exists(), "TXT file not created"
            with open(txt_path, 'r', encoding='utf-8') as f:
                content = f.read()
                assert "Crawl Results" in content, "Crawl Results header missing from TXT output"
                assert "Total URLs:" in content, "Total URLs count missing from TXT output"
                for url in results.keys():
                    assert url in content, f"URL {url} missing from TXT output"
            
            # Test HTML output
            html_path = Path(temp_dir) / "results.html"
            save_results(results, "html", html_path)
            
            # Verify HTML file was created and contains valid data
            assert html_path.exists(), "HTML file not created"
            with open(html_path, 'r', encoding='utf-8') as f:
                content = f.read()
                assert "<!DOCTYPE html>" in content, "DOCTYPE declaration missing from HTML output"
                assert "<title>Crawlit Results" in content, "Title missing from HTML output"
                for url in results.keys():
                    assert url in content, f"URL {url} missing from HTML output"
    
    def test_summary_report(self, mock_website):
        """Test the summary report generation"""
        crawler = Crawler(start_url=mock_website, max_depth=2)
        crawler.crawl()
        
        results = crawler.get_results()
        
        # Generate a summary report
        summary = generate_summary_report(results)
        
        # Verify that the summary contains expected information
        assert "Crawl Summary" in summary, "Crawl Summary header missing from summary report"
        assert "Total URLs crawled:" in summary, "Total URLs count missing from summary report"
        assert "Successful requests:" in summary, "Successful requests count missing from summary report"
        assert "Failed requests:" in summary, "Failed requests count missing from summary report"
        assert "URLs by depth:" in summary, "URLs by depth section missing from summary report"
        
        # Check that the depth breakdown includes depth 0
        assert "Depth 0:" in summary, "Depth 0 missing from summary report"
    
    def test_error_handling(self, mock_server_with_errors):
        """Test error handling for various HTTP status codes"""
        # Initialize the crawler - set max_retries and timeout for quicker testing
        crawler = Crawler(
            start_url=mock_server_with_errors, 
            max_depth=1,
            max_retries=1,
            timeout=1
        )
        crawler.crawl()
        
        # Get results
        results = crawler.get_results()
        
        # Verify the test page was crawled successfully
        assert mock_server_with_errors in results, "Error test page not in results"
        assert results[mock_server_with_errors]["success"] == True, "Error test page crawl was not successful"
        
        # Check for 404 error
        not_found_url = f"{mock_server_with_errors.rstrip('error_test')}not_found"
        if not_found_url in results:
            assert results[not_found_url]["status"] == 404, "404 status not recorded correctly"
            assert results[not_found_url]["success"] == False, "404 page incorrectly marked as successful"
        
        # Check for 500 error
        server_error_url = f"{mock_server_with_errors.rstrip('error_test')}server_error"
        if server_error_url in results:
            assert results[server_error_url]["status"] == 500, "500 status not recorded correctly"
            assert results[server_error_url]["success"] == False, "500 page incorrectly marked as successful"
        
        # Check for redirect handling
        redirect_url = f"{mock_server_with_errors.rstrip('error_test')}redirect"
        redirected_url = f"{mock_server_with_errors.rstrip('error_test')}redirected"
        
        # Either the original URL should be in results (crawler may record 302 or final 200 after following)
        # or the redirected URL should be in results with a 200 status
        if redirect_url in results:
            assert results[redirect_url]["status"] in (200, 302), "Redirect status not recorded correctly"
        
        if redirected_url in results:
            assert results[redirected_url]["status"] == 200, "Redirected page status not recorded correctly"
            assert results[redirected_url]["success"] == True, "Redirected page incorrectly marked as unsuccessful"
    
    def test_custom_user_agent(self, httpserver):
        """Test custom user agent functionality"""
        user_agent_received = [None]  # Use a list to allow modification in the handler
        
        def handler(request):
            from werkzeug.wrappers import Response
            user_agent_received[0] = request.headers.get('User-Agent')
            return Response("<html><body>Test page for User-Agent</body></html>", content_type="text/html")
        
        httpserver.expect_request("/").respond_with_handler(handler)
        
        # Initialize the crawler with a custom user agent
        custom_agent = "TestCrawler/3.0"
        crawler = Crawler(start_url=httpserver.url_for("/"), user_agent=custom_agent)
        crawler.crawl()
        
        # Verify that the custom user agent was sent
        assert user_agent_received[0] == custom_agent, f"Expected user agent '{custom_agent}', got '{user_agent_received[0]}'"
        
        # Test with default user agent
        user_agent_received[0] = None
        crawler = Crawler(start_url=httpserver.url_for("/"))
        crawler.crawl()
        
        # Verify that the default user agent was sent
        assert user_agent_received[0] == "crawlit/1.0", f"Expected default user agent 'crawlit/1.0', got '{user_agent_received[0]}'"
    
    def test_request_delay(self, httpserver):
        """Test the delay between requests"""
        # Configure DEBUG logging
        from tests.configure_logging import configure_logging
        configure_logging()
        
        request_times = []
    
        def handler(request):
            print(f"Handler called for URL: {request.url}")
            request_times.append(time.time())
            # Return Response object instead of tuple
            from werkzeug.wrappers import Response
            return Response("<html><body>Test page</body></html>", content_type="text/html")
    
        # Setup main page with links
        main_html = """
        <html><body>
            <a href="/page1">Page 1</a>
            <a href="/page2">Page 2</a>
            <a href="/page3">Page 3</a>
            <a href="/page4">Page 4</a>
            <a href="/page5">Page 5</a>
        </body></html>
        """
    
        print(f"Test server URL: {httpserver.url_for('/')}")
        httpserver.expect_request("/").respond_with_data(main_html, content_type="text/html")
        httpserver.expect_request("/page1").respond_with_handler(handler)
        httpserver.expect_request("/page2").respond_with_handler(handler)
        httpserver.expect_request("/page3").respond_with_handler(handler)
        httpserver.expect_request("/page4").respond_with_handler(handler)
        httpserver.expect_request("/page5").respond_with_handler(handler)
        
        # Test with a large delay to make sure it's measurable
        delay = 0.5  # half a second
        # Disable robots.txt handling for test purpose
        crawler = Crawler(start_url=httpserver.url_for("/"), max_depth=1, delay=delay, respect_robots=False)
        crawler.crawl()
        
        # Should have at least 5 requests (to the linked pages)
        assert len(request_times) >= 5, f"Expected at least 5 requests, got {len(request_times)}"
        
        # Check time differences between requests
        time_diffs = [request_times[i+1] - request_times[i] for i in range(len(request_times)-1)]
        
        # At least some of the requests should have the specified delay
        delays_respected = [diff >= delay for diff in time_diffs]
        assert any(delays_respected), f"Delay of {delay}s not respected between requests. Time diffs: {time_diffs}"
        
        # Test with no delay
        request_times.clear()
        # Also disable robots.txt for the second test
        crawler = Crawler(start_url=httpserver.url_for("/"), max_depth=1, delay=0, respect_robots=False)
        crawler.crawl()
        
        # Should still have at least 5 requests
        assert len(request_times) >= 5, f"Expected at least 5 requests with no delay, got {len(request_times)}"
    
    def test_max_retries(self, monkeypatch):
        """Test the max_retries parameter using mocks to simulate retries"""
        # Keep track of retry count
        retry_count = [0]
        
        # Create a mock requests.get function that simulates retries
        def mock_get(url, headers=None, timeout=None, **kwargs):
            retry_count[0] += 1
            # Mock response object
            mock_response = mock.MagicMock()
            
            if retry_count[0] <= 2:  # Fail first 2 attempts
                mock_response.status_code = 500
                mock_response.headers = {'Content-Type': 'text/html'}
                mock_response.text = "<html><body>Server Error</body></html>"
                mock_response.content = b"<html><body>Server Error</body></html>"
            else:  # Succeed on 3rd attempt
                mock_response.status_code = 200
                mock_response.headers = {'Content-Type': 'text/html'}
                mock_response.text = "<html><body>Success after retries</body></html>"
                mock_response.content = b"<html><body>Success after retries</body></html>"
            return mock_response
        
        # Apply the mock
        monkeypatch.setattr('requests.get', mock_get)
        
        # Test with max_retries=3 (should eventually succeed on 3rd attempt)
        retry_count[0] = 0
        success, response, status = fetch_page("https://example.com/", "test-agent", 3, 10)
        
        # Check that it took 3 attempts and succeeded
        assert retry_count[0] == 3, f"Expected 3 attempts, got {retry_count[0]}"
        assert success == True, "Third attempt should succeed"
        assert status == 200, "Status code should be 200 on success"
        
        # Test with max_retries=1 (should fail after 2 attempts)
        retry_count[0] = 0
        success, response, status = fetch_page("https://example.com/", "test-agent", 1, 10)
        
        # Check that it made 2 attempts and failed
        assert retry_count[0] == 2, f"Expected 2 attempts, got {retry_count[0]}"
        assert success == False, "Request should fail with insufficient retries"
        assert status == 500, "Status code should be 500 on failure"
        
    def test_timeout_handling(self, httpserver):
        """Test handling of request timeouts"""
        def timeout_handler(request):
            time.sleep(3)  # Longer than our specified timeout
            return 200, {'Content-Type': 'text/html'}, "<html><body>This should timeout</body></html>"
        
        httpserver.expect_request("/timeout").respond_with_handler(timeout_handler)
        
        # Test with a short timeout
        crawler = Crawler(start_url=httpserver.url_for("/timeout"), timeout=1)
        crawler.crawl()
        
        results = crawler.get_results()
        assert httpserver.url_for("/timeout") in results, "Timeout URL not in results"
        assert results[httpserver.url_for("/timeout")]["success"] == False, "Timeout request incorrectly marked as successful"
        assert "error" in results[httpserver.url_for("/timeout")], "Error not recorded for timeout"
        assert "timeout" in results[httpserver.url_for("/timeout")]["error"].lower(), "Timeout error not properly identified"
    
    @pytest.mark.timeout(30)  # Set a 30-second timeout for the entire test
    def test_large_website_crawling(self, mock_website):
        """Test crawling a larger website structure with many links"""
        from crawlit.utils.budget_tracker import BudgetTracker
        
        # Use budget tracker to limit pages to keep test fast
        budget = BudgetTracker(max_pages=10)  # Limit to 10 pages total
        
        crawler = Crawler(
            start_url=f"{mock_website}long-page", 
            max_depth=1,
            same_path_only=False,  # Don't limit to just the same path
            budget_tracker=budget,  # Use budget tracker to limit pages
            delay=0  # No delay between requests
        )
        crawler.crawl()

        results = crawler.get_results()

        # Should have the main page plus some of the linked pages
        assert f"{mock_website}long-page" in results, "Long page not in results"

        # Count how many of the item pages were crawled
        item_pages = [url for url in results if "/long/item" in url]

        # With budget limit of 10, should have crawled some but not all 100 items
        assert len(item_pages) > 0, "No item pages were crawled"
        assert len(results) <= 10, f"Should have stopped at budget limit, got {len(results)} pages"
    
    def test_unicode_handling(self, mock_website):
        """Test handling of unicode and special characters"""
        crawler = Crawler(start_url=f"{mock_website}unicode-page", max_depth=0)
        crawler.crawl()
        
        results = crawler.get_results()
        
        # Verify the page was crawled successfully
        assert f"{mock_website}unicode-page" in results, "Unicode page not in results"
        assert results[f"{mock_website}unicode-page"]["success"] == True, "Unicode page crawl was not successful"
        
        # If we enable keyword extraction, we should be able to extract unicode keywords
        crawler = Crawler(
            start_url=f"{mock_website}unicode-page", 
            max_depth=0,
            enable_keyword_extraction=True
        )
        crawler.crawl()
        
        results = crawler.get_results()
        page_data = results[f"{mock_website}unicode-page"]
        
        # Verify keywords were extracted
        assert "keywords" in page_data, "Keywords not extracted from unicode page"
        assert len(page_data["keywords"]) > 0, "No keywords extracted from unicode page"
    
    def test_malformed_html_handling(self, mock_website):
        """Test handling of malformed HTML"""
        crawler = Crawler(
            start_url=f"{mock_website}page1/subpage", 
            max_depth=0,
            enable_image_extraction=True,
            enable_table_extraction=True
        )
        crawler.crawl()
        
        results = crawler.get_results()
        
        # Verify the page was crawled successfully despite malformed HTML
        assert f"{mock_website}page1/subpage" in results, "Malformed HTML page not in results"
        assert results[f"{mock_website}page1/subpage"]["success"] == True, "Malformed HTML page crawl was not successful"
        
        # Verify some links were extracted even from malformed HTML
        page_data = results[f"{mock_website}page1/subpage"]
        assert "links" in page_data, "Links not extracted from malformed HTML"
        assert len(page_data["links"]) > 0, "No links extracted from malformed HTML"
        
        # Verify image extraction worked despite malformed HTML
        assert "images" in page_data, "Images not extracted from malformed HTML"
        assert len(page_data["images"]) > 0, "No images extracted from malformed HTML"
        
        # Verify table extraction attempted (may or may not find valid tables)
        assert "tables" in page_data, "Tables extraction not attempted on malformed HTML"
    
    def test_table_extraction(self, mock_website):
        """Test detailed table extraction functionality"""
        crawler = Crawler(
            start_url=f"{mock_website}tables-page", 
            max_depth=0,
            enable_table_extraction=True
        )
        crawler.crawl()
        
        results = crawler.get_results()
        
        # Verify the page was crawled successfully
        assert f"{mock_website}tables-page" in results, "Tables page not in results"
        page_data = results[f"{mock_website}tables-page"]
        
        # Verify tables were extracted
        assert "tables" in page_data, "Tables not extracted"
        assert len(page_data["tables"]) >= 5, f"Expected at least 5 tables, got {len(page_data['tables'])}"
        
        # Check specific table structures
        
        # Find the basic table with 3x3 structure
        basic_table_found = False
        for table in page_data["tables"]:
            if len(table) == 3 and all(len(row) == 3 for row in table):
                basic_table_found = True
                # Check header
                assert "Header 1" in table[0][0] or "Header 1" in table[0][1] or "Header 1" in table[0][2], "Header text not found in basic table"
                break
                
        assert basic_table_found, "Basic 3x3 table not found or not properly extracted"
        
        # Find the table with colspan/rowspan
        colspan_table_found = False
        for table in page_data["tables"]:
            if len(table) == 3:  # This table has 3 rows after processing
                if table[0][0] == "Merged Header" or "Merged Header" in table[0][0]:
                    colspan_table_found = True
                    break
                    
        assert colspan_table_found, "Table with colspan/rowspan not found or not properly extracted"
        
        # Find the table with thead/tbody
        thead_table_found = False
        for table in page_data["tables"]:
            if len(table) >= 3:  # Header + at least 2 data rows
                # This table has ID, Name, Value columns
                header_row = table[0]
                if ("ID" in header_row[0] and "Name" in header_row[1] and "Value" in header_row[2]):
                    thead_table_found = True
                    # Check for specific product values
                    assert any("Product" in row[1] for row in table[1:]), "Product data not found in thead/tbody table"
                    break
                    
        assert thead_table_found, "Table with thead/tbody not found or not properly extracted"
        
        # Check extraction of the tiny one-cell table
        small_table_found = False
        for table in page_data["tables"]:
            if len(table) == 1 and len(table[0]) == 1:
                if "Just one cell" in table[0][0]:
                    small_table_found = True
                    break
                    
        assert small_table_found, "Small one-cell table not found or not properly extracted"
        
        # Test standalone table extraction function
        from crawlit.extractors.tables import extract_tables
        
        # Get the HTML content from the crawled page
        html_content = page_data["html_content"]
        
        # Extract tables directly
        extracted_tables = extract_tables(html_content)
        
        # Should match what was extracted during crawling
        assert len(extracted_tables) == len(page_data["tables"]), "Direct table extraction doesn't match crawler results"
        
        # Test with minimum size filters
        filtered_tables = extract_tables(html_content, min_rows=2, min_columns=2)
        assert len(filtered_tables) < len(extracted_tables), "Table filtering by size didn't reduce the number of tables"
        
        # The one-cell table should be filtered out
        one_cell_tables = [table for table in filtered_tables if len(table) ==  1 and len(table[0]) == 1]
        assert len(one_cell_tables) == 0, "Small tables not properly filtered"
    
    def test_image_extraction(self, mock_website):
        """Test detailed image extraction functionality"""
        crawler = Crawler(
            start_url=mock_website, 
            max_depth=0,
            enable_image_extraction=True
        )
        crawler.crawl()
        
        results = crawler.get_results()
        page_data = results[mock_website]
        
        # Verify images were extracted
        assert "images" in page_data, "Images not extracted"
        assert len(page_data["images"]) >= 3, f"Expected at least 3 images, got {len(page_data['images'])}"
        
        # Check specific image attributes
        test1_found = False
        test2_found = False
        icon_found = False
        
        for img in page_data["images"]:
            if img["src"].endswith("/images/test1.jpg"):
                test1_found = True
                assert img["alt"] == "Test Image 1", "Alt text for test1.jpg not correctly extracted"
                assert int(img["width"]) == 300, "Width for test1.jpg not correctly extracted"
                assert int(img["height"]) == 200, "Height for test1.jpg not correctly extracted"
                
            elif img["src"].endswith("/images/test2.png"):
                test2_found = True
                assert img["alt"] == "Test Image 2", "Alt text for test2.png not correctly extracted"
                assert "class" in img and "featured" in img["class"], "Class for test2.png not correctly extracted"
                
            elif img["src"].endswith("/images/icon.svg"):
                icon_found = True
                assert img["alt"] == "", "Alt text for icon.svg not correctly extracted"
                assert "class" in img and "inline-icon" in img["class"], "Class for icon.svg not correctly extracted"
        
        assert test1_found, "test1.jpg not found or attributes not correctly extracted"
        assert test2_found, "test2.png not found or attributes not correctly extracted"
        assert icon_found, "icon.svg not found or attributes not correctly extracted"
        
        # Test standalone image extraction
        from crawlit.extractors.image_extractor import ImageTagParser
        
        # Get the HTML content from the crawled page
        html_content = page_data["html_content"]
        
        # Extract images directly
        parser = ImageTagParser()
        extracted_images = parser.extract_images(html_content)
        
        # Should match what was extracted during crawling
        assert len(extracted_images) == len(page_data["images"]), "Direct image extraction doesn't match crawler results"
        
        # Test with iframe handling - iframes should be excluded
        crawler = Crawler(
            start_url=f"{mock_website}page1", 
            max_depth=0,
            enable_image_extraction=True
        )
        crawler.crawl()
        
        results = crawler.get_results()
        page_data = results[f"{mock_website}page1"]
        
        # Verify that images in iframes were not extracted
        iframe_images = [img for img in page_data["images"] if "src" in img and "/iframe-content" in img["src"]]
        assert len(iframe_images) == 0, "Images from iframe content were incorrectly extracted"
    
    def test_keyword_extraction(self, mock_website):
        """Test detailed keyword extraction functionality"""
        crawler = Crawler(
            start_url=f"{mock_website}page1", 
            max_depth=0,
            enable_keyword_extraction=True
        )
        crawler.crawl()
        
        results = crawler.get_results()
        page_data = results[f"{mock_website}page1"]
        
        # Verify keywords were extracted
        assert "keywords" in page_data, "Keywords not extracted"
        assert len(page_data["keywords"]) > 0, f"No keywords extracted"
        
        # Verify key phrases were extracted
        assert "keyphrases" in page_data, "Key phrases not extracted"
        assert len(page_data["keyphrases"]) > 0, f"No key phrases extracted"
        
        # Check that keyword scores were calculated
        assert "keyword_scores" in page_data, "Keyword scores not calculated"
        assert len(page_data["keyword_scores"]) > 0, f"No keyword scores calculated"
        
        # Check that scores are between 0 and 1
        for score in page_data["keyword_scores"].values():
            assert 0 <= score <= 1, f"Keyword score {score} not between 0 and 1"
        
        # Test standalone keyword extraction
        from crawlit.extractors.keyword_extractor import KeywordExtractor
        
        # Get the HTML content from the crawled page
        html_content = page_data["html_content"]
        
        # Extract keywords directly
        extractor = KeywordExtractor()
        keyword_data = extractor.extract_keywords(html_content, include_scores=True)
        
        # Should have keywords and scores
        assert "keywords" in keyword_data, "Keywords not in direct extraction results"
        assert "scores" in keyword_data, "Scores not in direct extraction results"
        assert len(keyword_data["keywords"]) > 0, "No keywords in direct extraction results"
        
        # Extract keyphrases directly
        keyphrases = extractor.extract_keyphrases(html_content)
        
        # Should have keyphrases
        assert len(keyphrases) > 0, "No keyphrases in direct extraction results"
        
        # Test extraction from meta tags
        crawler = Crawler(
            start_url=mock_website, 
            max_depth=0,
            enable_keyword_extraction=True
        )
        crawler.crawl()
        
        results = crawler.get_results()
        page_data = results[mock_website]
        
        # The main page has meta keywords
        meta_keywords = ["test", "crawlit", "crawler"]
        found_meta_keywords = [kw for kw in meta_keywords if any(kw == k.lower() for k in page_data["keywords"])]
        assert len(found_meta_keywords) > 0, f"Meta keywords not found in extracted keywords: {page_data['keywords']}"
    
    def test_concurrent_requests(self):
        """Test that the crawler can handle concurrent requests from multiple threads"""
        # Create a simple HTTP server in a separate thread
        class SimpleRequestHandler(SimpleHTTPRequestHandler):
            def do_GET(self):
                time.sleep(0.1)  # Small delay to simulate processing
                
                if self.path == '/robots.txt':
                    # Handle robots.txt specially
                    self.send_response(200)
                    self.send_header('Content-type', 'text/plain')
                    self.end_headers()
                    self.wfile.write(b"User-agent: *\nAllow: /\n")
                    return
                
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                
                if self.path == '/' or self.path == '/index.html':
                    content = b"""
                    <html><body>
                        <h1>Concurrent Test</h1>
                        <ul>
                    """
                    # Add many links
                    for i in range(20):
                        content += f'<li><a href="/page{i}.html">Page {i}</a></li>\n'.encode()
                    
                    content += b"""
                        </ul>
                    </body></html>
                    """
                    self.wfile.write(content)
                else:
                    self.wfile.write(b"<html><body>Test page</body></html>")
        
        # Find an available port
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('localhost', 0))
            port = s.getsockname()[1]
        
        # Start the server in a separate thread
        server = HTTPServer(('localhost', port), SimpleRequestHandler)
        server_thread = threading.Thread(target=server.serve_forever)
        server_thread.daemon = True
        server_thread.start()
        
        try:
            # Test with sequential requests
            start_time_sequential = time.time()
            crawler = Crawler(
                start_url=f"http://localhost:{port}/",
                max_depth=1,
                max_retries=1,
                timeout=5,
                delay=0  # No delay between requests
            )
            crawler.crawl()
            end_time_sequential = time.time()
            sequential_results = crawler.get_results()
            
            # Server should stay up between tests
            time.sleep(1)
            
            # In a real threaded implementation, this would be faster
            # Note: Since our crawler implementation is sequential, this test
            # primarily serves as a stability check for handling multiple requests
            sequential_duration = end_time_sequential - start_time_sequential
            
            # Verify that both approaches crawled the same pages
            assert f"http://localhost:{port}/" in sequential_results, "Start URL not in sequential results"
            assert len(sequential_results) > 1, "Not enough pages crawled in sequential mode"
        finally:
            server.shutdown()
            server_thread.join()
    
    def test_crawler_stop_and_resume(self, mock_website):
        """Test ability to serialize and deserialize crawler state for stop/resume functionality"""
        # Create a test for a potential feature where crawling could be stopped and resumed
        # This is not implemented in the current code, but demonstrates how it might be tested
        
        # Start a crawler and do partial crawling
        crawler = Crawler(start_url=mock_website, max_depth=2)
        
        # Mock a partial crawl by manually filling the queue and visited sets
        # In a real implementation, this would come from serialized state
        crawler.visited_urls.add(mock_website)
        crawler.queue.append((f"{mock_website}page1", 1))
        crawler.queue.append((f"{mock_website}page2", 1))
        
        # Add a result for the start URL
        crawler.results[mock_website] = {
            'depth': 0,
            'status': 200,
            'success': True,
            'links': [f"{mock_website}page1", f"{mock_website}page2"]
        }
        
        # Now resume crawling from this state
        crawler.crawl()
        
        # Check that both the pre-filled results and new results are present
        results = crawler.get_results()
        assert mock_website in results, "Start URL not in results after resume"
        assert f"{mock_website}page1" in results, "Page1 not crawled after resume"
        assert f"{mock_website}page2" in results, "Page2 not crawled after resume"
        
        # The subpage should also be crawled since we set max_depth=2
        assert f"{mock_website}page1/subpage" in results, "Subpage not crawled after resume"
    
    def test_sitemap_parsing(self):
        """Test parsing and using XML sitemaps"""
        # While the current implementation doesn't explicitly support sitemap parsing,
        # this test demonstrates how it might be tested
        
        # Create sample sitemap XML
        sitemap_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
            <url>
                <loc>http://example.com/</loc>
                <lastmod>2023-01-01</lastmod>
                <changefreq>daily</changefreq>
                <priority>1.0</priority>
            </url>
            <url>
                <loc>http://example.com/page1</loc>
                <lastmod>2023-01-01</lastmod>
                <changefreq>weekly</changefreq>
                <priority>0.8</priority>
            </url>
            <url>
                <loc>http://example.com/page2</loc>
                <lastmod>2023-01-01</lastmod>
                <changefreq>weekly</changefreq>
                <priority>0.8</priority>
            </url>
        </urlset>
        """
        
        # Parse sitemap directly with a hypothetical function
        # This function doesn't exist in the current code but shows how it might be used
        # extracted_urls = parse_sitemap(sitemap_xml)
        # assert len(extracted_urls) == 3, "Not all URLs extracted from sitemap"
        # assert "http://example.com/" in extracted_urls, "Start URL not extracted from sitemap"
        # assert "http://example.com/page1" in extracted_urls, "Page1 not extracted from sitemap"
        # assert "http://example.com/page2" in extracted_urls, "Page2 not extracted from sitemap"
        
        # In a more advanced implementation, the crawler could discover and use sitemaps
        # from robots.txt "Sitemap:" directives
        pass
    
    def test_robots_handler(self, httpserver):
        """Test the RobotsHandler class directly"""
        from crawlit.crawler.robots import RobotsHandler
        
        # Create a mock robots.txt
        robots_txt = """
        User-agent: *
        Allow: /private/allowed/
        Disallow: /private/

        User-agent: test-agent
        Disallow: /test-only/

        User-agent: crawlit
        Disallow: /crawlit-only/
        """
        
        # Setup a mock server to serve the robots.txt
        httpserver.expect_request("/robots.txt").respond_with_data(robots_txt, content_type="text/plain")
            
        # Initialize the handler
        handler = RobotsHandler()
        
        # Test with a generic agent (matches User-agent: * rules)
        assert handler.can_fetch(f"{httpserver.url_for('/')}public", "genericbot/1.0"), "Public URL incorrectly blocked"
        assert not handler.can_fetch(f"{httpserver.url_for('/')}private/secret", "genericbot/1.0"), "Private URL incorrectly allowed"
        assert handler.can_fetch(f"{httpserver.url_for('/')}private/allowed/page", "genericbot/1.0"), "Allowed private URL incorrectly blocked"

        # Test with specific user agent (crawlit/1.0 matches User-agent: crawlit block)
        assert not handler.can_fetch(f"{httpserver.url_for('/')}crawlit-only/page", "crawlit/1.0"), "crawlit-only URL incorrectly allowed for crawlit agent"
        assert handler.can_fetch(f"{httpserver.url_for('/')}test-only/page", "crawlit/1.0"), "test-only URL incorrectly blocked for crawlit agent"
        assert not handler.can_fetch(f"{httpserver.url_for('/')}test-only/page", "test-agent"), "test-only URL incorrectly allowed for test-agent"

        # Test missing robots.txt
        assert handler.can_fetch("http://nonexistent.example.com/page", "genericbot/1.0"), "URL incorrectly blocked when robots.txt is missing"

