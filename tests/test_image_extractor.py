import unittest
import time
import html
from io import StringIO
from contextlib import redirect_stdout
from crawlit.extractors.image_extractor import ImageTagParser, ImageExtractor

class TestImageExtractorEnhanced(unittest.TestCase):
    def setUp(self):
        self.parser = ImageTagParser()
        self.extractor = ImageExtractor()
    
    def test_extremely_large_attributes(self):
        """Test extraction of images with extremely large attribute values"""
        # Generate a large alt text
        large_alt = "a" * 10000
        large_title = "t" * 5000
        
        html_content = f"""
        <html>
            <body>
                <img src="large-attr.jpg" alt="{large_alt}" title="{large_title}">
                <img src="normal.jpg" alt="Normal image">
            </body>
        </html>
        """
        images = self.parser.extract_images(html_content)
        self.assertEqual(len(images), 2)
        
        # Check large attribute image
        large_attr_img = next(img for img in images if img['src'] == "large-attr.jpg")
        self.assertEqual(len(large_attr_img['alt']), 10000)
        self.assertEqual(len(large_attr_img['title']), 5000)
        
        # Test with extractor class too
        extractor_images = self.extractor.extract_images(html_content)
        self.assertEqual(len(extractor_images), 2)
    
    def test_unicode_and_internationalization(self):
        """Test extraction of images with international characters in attributes"""
        html_content = """
        <html>
            <body>
                <img src="international.jpg" alt="国际化测试 καλημέρα こんにちは">
                <img src="emoji.jpg" alt="Image with emoji 🌟🔥💯">
                <img src="/path/to/インターナショナル.jpg" alt="International filename">
                <img src="русский.png" alt="Russian filename">
            </body>
        </html>
        """
        images = self.parser.extract_images(html_content)
        self.assertEqual(len(images), 4)
        
        # Check international text
        int_img = next(img for img in images if img['src'] == "international.jpg")
        self.assertEqual(int_img['alt'], "国际化测试 καλημέρα こんにちは")
        
        # Check emoji
        emoji_img = next(img for img in images if img['src'] == "emoji.jpg")
        self.assertEqual(emoji_img['alt'], "Image with emoji 🌟🔥💯")
        
        # Check international filenames
        int_filename = next(img for img in images if 'インターナショナル' in img['src'])
        self.assertEqual(int_filename['src'], "/path/to/インターナショナル.jpg")
        
        rus_filename = next(img for img in images if img['src'] == "русский.png")
        self.assertEqual(rus_filename['alt'], "Russian filename")
    
    def test_deeply_nested_paths(self):
        """Test extraction with deeply nested image paths"""
        html_content = """
        <html>
            <body>
                <div>
                    <section>
                        <article>
                            <aside>
                                <figure>
                                    <div>
                                        <span>
                                            <p>
                                                <img src="deeply/nested/path/image.jpg" alt="Deeply nested">
                                            </p>
                                        </span>
                                    </div>
                                </figure>
                            </aside>
                        </article>
                    </section>
                </div>
            </body>
        </html>
        """
        images = self.parser.extract_images(html_content)
        self.assertEqual(len(images), 1)
        self.assertEqual(images[0]['src'], "deeply/nested/path/image.jpg")
        self.assertEqual(images[0]['parent_tag'], "p")
    
    def test_edge_case_attribute_values(self):
        """Test images with edge case attribute values"""
        html_content = """
        <html>
            <body>
                <!-- URL-encoded attributes -->
                <img src="encoded%20spaces.jpg" alt="Has%20encoded%20spaces">
                
                <!-- Unusual URL formats -->
                <img src="http://example.com/image.jpg?param=value&other=123#fragment" alt="URL with params">
                <img src="//cdn.example.com/image.jpg" alt="Protocol-relative URL">
                <img src="blob:http://example.com/1234-5678-90ab-cdef" alt="Blob URL">
                
                <!-- Scripts in attributes (security test) -->
                <img src="valid.jpg" alt="Alert: <script>alert('XSS');</script>">
                <img src="javascript:alert('XSS')" alt="Script URL">
                
                <!-- Extremely short and long URLs -->
                <img src="x" alt="One character URL">
                <img src="/extremely/long/path/that/is/probably/longer/than/most/reasonable/paths/would/ever/be/in/a/real/website/but/we/should/test/it/anyway/just/to/be/sure/that/our/parser/can/handle/it/properly/without/choking/on/the/length/image.jpg" alt="Extremely long path">
            </body>
        </html>
        """
        images = self.parser.extract_images(html_content)
        self.assertEqual(len(images), 8)
        
        # URL-encoded attributes
        encoded_img = next(img for img in images if img['src'] == "encoded%20spaces.jpg")
        self.assertEqual(encoded_img['alt'], "Has%20encoded%20spaces")
        
        # URL with parameters
        param_img = next(img for img in images if '?' in img['src'])
        self.assertTrue(param_img['src'].startswith("http://example.com/image.jpg?"))
        
        # Protocol-relative URL
        protocol_img = next(img for img in images if img['src'].startswith("//"))
        self.assertEqual(protocol_img['src'], "//cdn.example.com/image.jpg")
        
        # Blob URL
        blob_img = next(img for img in images if img['src'].startswith("blob:"))
        self.assertEqual(blob_img['alt'], "Blob URL")
        
        # Script in alt text shouldn't be executed but should be preserved
        script_img = next(img for img in images if "script" in img['alt'])
        self.assertTrue("<script>" in script_img['alt'])
        
        # Script URL
        js_img = next(img for img in images if img['src'].startswith("javascript:"))
        self.assertEqual(js_img['src'], "javascript:alert('XSS')")
        
        # One character URL
        short_img = next(img for img in images if img['src'] == "x")
        self.assertEqual(short_img['alt'], "One character URL")
        
        # Extremely long path
        long_img = next(img for img in images if "extremely" in img['src'])
        self.assertTrue(len(long_img['src']) > 200)
    
    def test_image_in_comments(self):
        """Test that images in HTML comments are not extracted"""
        html_content = """
        <html>
            <body>
                <img src="visible.jpg" alt="Visible image">
                <!-- 
                <img src="commented.jpg" alt="This is in a comment">
                -->
                <!--img src="another_commented.jpg" alt="Another comment style"-->
            </body>
        </html>
        """
        images = self.parser.extract_images(html_content)
        self.assertEqual(len(images), 1)
        self.assertEqual(images[0]['src'], "visible.jpg")
        
        # Also test with malformed comments
        malformed_comments = """
        <html>
            <body>
                <img src="visible1.jpg" alt="Visible 1">
                <!-- Unclosed comment
                <img src="should_not_appear1.jpg" alt="Unclosed comment">
                <img src="visible2.jpg" alt="Visible 2">
                <!- Malformed comment opener
                <img src="should_still_appear.jpg" alt="Malformed comment">
            </body>
        </html>
        """
        images2 = self.parser.extract_images(malformed_comments)
        # Depending on how HTMLParser handles malformed comments, results may vary
        # We're just checking that at least some images were extracted
        self.assertGreater(len(images2), 0)
    
    def test_partial_html_fragments(self):
        """Test with HTML fragments rather than complete documents"""
        html_content = """
        <div class="content">
            <img src="fragment1.jpg" alt="Fragment 1">
            <p>Some text</p>
            <img src="fragment2.jpg" alt="Fragment 2">
        </div>
        """
        images = self.parser.extract_images(html_content)
        self.assertEqual(len(images), 2)
        self.assertEqual(images[0]['src'], "fragment1.jpg")
        self.assertEqual(images[1]['src'], "fragment2.jpg")
        
        # Even more minimal fragment
        minimal = '<img src="minimal.jpg" alt="Minimal">'
        images2 = self.parser.extract_images(minimal)
        self.assertEqual(len(images2), 1)
        self.assertEqual(images2[0]['src'], "minimal.jpg")
    
    def test_html_entities_in_attributes(self):
        """Test with HTML entities in attributes"""
        html_content = """
        <html>
            <body>
                <img src="entities1.jpg" alt="Testing &lt;entities&gt; &amp; characters">
                <img src="entities2.jpg" alt="More entities: &quot;quoted&quot; and &apos;single&apos;">
                <img src="entities3.jpg" alt="Numeric entities: &#60;brackets&#62; and &#x3C;hex brackets&#x3E;">
                <img src="quote&amp;stuff.jpg" alt="Entities in URL">
            </body>
        </html>
        """
        images = self.parser.extract_images(html_content)
        self.assertEqual(len(images), 4)
        
        # Check decoded entities in alt text
        entity_img = images[0]
        self.assertEqual(entity_img['alt'], "Testing <entities> & characters")
        
        quote_img = images[1]
        self.assertEqual(quote_img['alt'], 'More entities: "quoted" and \'single\'')
        
        num_entity = images[2]
        self.assertEqual(num_entity['alt'], "Numeric entities: <brackets> and <hex brackets>")
        
        # Check that entities in src are decoded by HTML parser
        url_entity = next(img for img in images if "&" in img['src'])
        self.assertEqual(url_entity['src'], "quote&stuff.jpg")
    
    def test_nonstandard_image_attributes(self):
        """Test extraction of nonstandard and custom data attributes"""
        html_content = """
        <html>
            <body>
                <img src="custom.jpg" 
                     alt="Custom attributes"
                     data-id="123"
                     data-src-mobile="custom-mobile.jpg"
                     data-srcset="custom1.jpg 1x, custom2.jpg 2x"
                     data-caption="Image caption"
                     loading="lazy"
                     fetchpriority="high"
                     rel="preload"
                     importance="high"
                     decoding="async"
                     crossorigin="anonymous">
            </body>
        </html>
        """
        images = self.parser.extract_images(html_content)
        self.assertEqual(len(images), 1)
        
        img = images[0]
        self.assertEqual(img['src'], "custom.jpg")
        self.assertEqual(img['data-id'], "123")
        self.assertEqual(img['data-src-mobile'], "custom-mobile.jpg")
        self.assertEqual(img['data-srcset'], "custom1.jpg 1x, custom2.jpg 2x")
        self.assertEqual(img['loading'], "lazy")
        self.assertEqual(img['fetchpriority'], "high")
        self.assertEqual(img['decoding'], "async")
    
    def test_very_complex_nested_html(self):
        """Test extraction from very complex nested HTML with multiple contexts"""
        html_content = """
        <html>
            <head>
                <title>Complex Document</title>
            </head>
            <body>
                <header>
                    <nav>
                        <ul>
                            <li><a href="#"><img src="/nav/icon1.png" alt="Nav Icon 1" width="20" height="20"></a></li>
                            <li><a href="#"><img src="/nav/icon2.png" alt="Nav Icon 2" width="20" height="20"></a></li>
                        </ul>
                    </nav>
                    <div class="banner">
                        <img src="/banner/hero.jpg" alt="Hero Banner" class="hero" width="1200" height="400">
                    </div>
                </header>
                <main>
                    <section class="articles">
                        <article id="article1">
                            <h2>Article 1</h2>
                            <figure>
                                <img src="/articles/img1.jpg" alt="Article Image 1" class="article-img">
                                <figcaption>Figure 1: Description</figcaption>
                            </figure>
                            <p>Text with an inline <img src="/icons/info.svg" alt="Info icon" class="inline-icon" width="16" height="16"> icon.</p>
                        </article>
                        <article id="article2">
                            <h2>Article 2</h2>
                            <div class="gallery">
                                <figure>
                                    <img src="/gallery/img1.jpg" alt="Gallery Image 1" data-index="0">
                                </figure>
                                <figure>
                                    <img src="/gallery/img2.jpg" alt="Gallery Image 2" data-index="1">
                                </figure>
                            </div>
                        </article>
                    </section>
                    <aside>
                        <div class="widget">
                            <h3>Related</h3>
                            <ul>
                                <li>
                                    <img src="/widgets/thumb1.jpg" alt="Thumbnail 1" width="60" height="60">
                                </li>
                                <li>
                                    <img src="/widgets/thumb2.jpg" alt="Thumbnail 2" width="60" height="60">
                                </li>
                            </ul>
                        </div>
                    </aside>
                </main>
                <footer>
                    <div class="partners">
                        <img src="/partners/logo1.png" alt="Partner 1" class="partner-logo">
                        <img src="/partners/logo2.png" alt="Partner 2" class="partner-logo">
                    </div>
                    <div class="social">
                        <a href="#"><img src="/social/fb.svg" alt="Facebook" width="24" height="24"></a>
                        <a href="#"><img src="/social/tw.svg" alt="Twitter" width="24" height="24"></a>
                    </div>
                </footer>
            </body>
        </html>
        """
        images = self.parser.extract_images(html_content)
        self.assertEqual(len(images), 12)
        
        # Group images by their contexts
        nav_images = [img for img in images if img['src'].startswith('/nav/')]
        article_images = [img for img in images if img['src'].startswith('/articles/')]
        gallery_images = [img for img in images if img['src'].startswith('/gallery/')]
        social_images = [img for img in images if img['src'].startswith('/social/')]
        
        # Check counts by context
        self.assertEqual(len(nav_images), 2)
        self.assertEqual(len(article_images), 1)
        self.assertEqual(len(gallery_images), 2)
        self.assertEqual(len(social_images), 2)
        
        # Check parent tags
        hero_img = next(img for img in images if img['src'] == '/banner/hero.jpg')
        self.assertEqual(hero_img['parent_tag'], 'div')
        
        gallery_img = gallery_images[0]
        self.assertEqual(gallery_img['parent_tag'], 'figure')
    
    def test_overlapping_tags(self):
        """Test extraction with malformed overlapping tags"""
        html_content = """
        <html>
            <body>
                <div>
                    <p><span>Text <img src="valid1.jpg" alt="Valid 1"></span></p>
                    <p>Text <span><img src="valid2.jpg" alt="Valid 2"></p></span>
                    <p><span>Text <img src="valid3.jpg" alt="Valid 3"></p>
                    <span><img src="valid4.jpg" alt="Valid 4">
                </div>
            </body>
        </html>
        """
        # HTML parser should handle this as best it can
        images = self.parser.extract_images(html_content)
        self.assertGreaterEqual(len(images), 1)  # Should extract at least some images
        
        # Check if we found the valid images
        image_srcs = [img['src'] for img in images]
        valid_images = [src for src in image_srcs if src.startswith('valid')]
        self.assertGreaterEqual(len(valid_images), 1)
    
    def test_whitespace_behavior(self):
        """Test behavior with various whitespace patterns in HTML"""
        html_content = """
        <html>
            <body>
                <img src="normal.jpg"    alt="Normal spacing">
                <img
                    src="multiline.jpg"
                    alt="Multiline attributes"
                    width="100"
                    height="100"
                >
                <img           src          =       "weird-spacing.jpg"       alt     =     "Weird spacing"       >
                <img
                
                
                src="extra-newlines.jpg"
                
                
                alt="Extra newlines"
                
                
                >
            </body>
        </html>
        """
        images = self.parser.extract_images(html_content)
        self.assertEqual(len(images), 4)
        
        # Check all images are found despite whitespace variations
        src_list = [img['src'] for img in images]
        self.assertIn("normal.jpg", src_list)
        self.assertIn("multiline.jpg", src_list)
        self.assertIn("weird-spacing.jpg", src_list)
        self.assertIn("extra-newlines.jpg", src_list)
        
        # Verify attributes are correctly parsed
        multiline = next(img for img in images if img['src'] == "multiline.jpg")
        self.assertEqual(multiline['alt'], "Multiline attributes")
        self.assertEqual(multiline['width'], 100)
        self.assertEqual(multiline['height'], 100)
    
    def test_unusual_image_sources(self):
        """Test extraction of images with unusual source types"""
        html_content = """
        <html>
            <body>
                <!-- External domain sources -->
                <img src="https://example.com/image.jpg" alt="External domain">
                <img src="//example.org/image.png" alt="Protocol-relative URL">
                
                <!-- Various protocols -->
                <img src="ftp://example.com/image.jpg" alt="FTP protocol">
                <img src="data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='10' height='10'><circle cx='5' cy='5' r='5' fill='red'/></svg>" alt="Inline SVG data URI">
                <img src="data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7" alt="Transparent GIF">
                
                <!-- Unusual paths -->
                <img src="../relative/path.jpg" alt="Relative path with parent">
                <img src="/absolute/path.jpg" alt="Absolute path">
                <img src="?dynamic=param" alt="Query string only">
                <img src="#fragment" alt="Fragment only">
                
                <!-- Empty and nearly empty -->
                <img src=" " alt="Just whitespace">
            </body>
        </html>
        """
        images = self.parser.extract_images(html_content)
        # Should not include the image with just whitespace in src
        self.assertEqual(len(images), 9)
        
        # Check protocol sources
        https_img = next(img for img in images if img['src'].startswith('https://'))
        self.assertEqual(https_img['alt'], "External domain")
        
        protocol_rel = next(img for img in images if img['src'].startswith('//'))
        self.assertEqual(protocol_rel['alt'], "Protocol-relative URL")
        
        ftp_img = next(img for img in images if img['src'].startswith('ftp://'))
        self.assertEqual(ftp_img['alt'], "FTP protocol")
        
        # Data URIs
        data_imgs = [img for img in images if img['src'].startswith('data:')]
        self.assertEqual(len(data_imgs), 2)
        
        # Path variations
        rel_path = next(img for img in images if img['src'].startswith('../'))
        self.assertEqual(rel_path['alt'], "Relative path with parent")
        
        abs_path = next(img for img in images if img['src'].startswith('/absolute'))
        self.assertEqual(abs_path['alt'], "Absolute path")
        
        query_only = next(img for img in images if img['src'].startswith('?'))
        self.assertEqual(query_only['alt'], "Query string only")
        
        fragment_only = next(img for img in images if img['src'].startswith('#'))
        self.assertEqual(fragment_only['alt'], "Fragment only")
    
    def test_stress_test_huge_page(self):
        """Stress test with a huge HTML page containing many images"""
        # Create a really large HTML page with many images (5,000+)
        image_tags = []
        for i in range(5000):
            tag = f'<img src="image{i}.jpg" alt="Image {i}" width="{i % 100 + 50}" height="{i % 100 + 50}">'
            image_tags.append(tag)
        
        html_content = f"""
        <html>
            <body>
                {"".join(image_tags)}
            </body>
        </html>
        """
        
        # Measure performance
        start_time = time.time()
        images = self.parser.extract_images(html_content)
        end_time = time.time()
        
        # Verify all images were extracted
        self.assertEqual(len(images), 5000)
        
        # Check a sample of images
        self.assertEqual(images[0]['src'], "image0.jpg")
        self.assertEqual(images[1000]['src'], "image1000.jpg")
        self.assertEqual(images[4999]['src'], "image4999.jpg")
        
        # Log performance
        print(f"Extracted 5,000 images in {end_time - start_time:.2f} seconds")
        self.assertLess(end_time - start_time, 10.0, "Image extraction took too long")
    
    def test_identical_sources(self):
        """Test with multiple images having identical sources"""
        html_content = """
        <html>
            <body>
                <img src="repeated.jpg" alt="First instance">
                <img src="repeated.jpg" alt="Second instance">
                <img src="repeated.jpg" alt="Third instance" class="special">
                <img src="unique.jpg" alt="Unique image">
            </body>
        </html>
        """
        images = self.parser.extract_images(html_content)
        self.assertEqual(len(images), 4)
        
        # Check that all instances of the repeated image are captured
        repeated_images = [img for img in images if img['src'] == 'repeated.jpg']
        self.assertEqual(len(repeated_images), 3)
        
        # Verify the instances have different attributes
        alt_texts = [img['alt'] for img in repeated_images]
        self.assertIn("First instance", alt_texts)
        self.assertIn("Second instance", alt_texts)
        self.assertIn("Third instance", alt_texts)
        
        # Check the one with special class
        special_img = next(img for img in repeated_images if 'class' in img)
        self.assertEqual(special_img['class'], 'special')
    
    def test_image_extractor_exception_handling(self):
        """Test that the ImageExtractor class properly handles exceptions"""
        # Create an instance of the extractor
        extractor = ImageExtractor()
        
        # Test with valid HTML
        valid_html = '<img src="valid.jpg" alt="Valid">'
        valid_results = extractor.extract_images(valid_html)
        self.assertEqual(len(valid_results), 1)
        self.assertEqual(valid_results[0]['src'], 'valid.jpg')
        
        # Test with empty content
        empty_results = extractor.extract_images("")
        self.assertEqual(empty_results, [])
        
        # Test with None content
        none_results = extractor.extract_images(None)
        self.assertEqual(none_results, [])
        
        # Create pathological HTML that might cause parser errors
        pathological_html = """
        <img src="valid.jpg" alt="Valid">
        <img src=invalid"quote.jpg" alt="Invalid quotes">
        <img src="unclosed.jpg alt="Unclosed attribute
        <img src="valid2.jpg" alt="Another valid">
        """
        
        # The extractor should handle exceptions and return what it can
        path_results = extractor.extract_images(pathological_html)
        self.assertGreaterEqual(len(path_results), 1)  # Should get at least some valid images
    
    def test_cdata_sections(self):
        """Test that images inside CDATA sections are not extracted"""
        html_content = """
        <html>
            <body>
                <img src="visible.jpg" alt="Visible">
                <script type="text/javascript">
                //<![CDATA[
                    document.write('<img src="cdata1.jpg" alt="CDATA 1">');
                    // This is inside CDATA, should be treated as text
                //]]>
                </script>
                <![CDATA[
                <img src="cdata2.jpg" alt="CDATA 2">
                ]]>
                <img src="visible2.jpg" alt="Visible 2">
            </body>
        </html>
        """
        images = self.parser.extract_images(html_content)
        # Should only find the visible images, not the ones in CDATA
        self.assertEqual(len(images), 2)
        
        visible_srcs = ["visible.jpg", "visible2.jpg"]
        for img in images:
            self.assertIn(img['src'], visible_srcs)
    
    def test_document_with_frames(self):
        """Test extraction from documents with frames and iframes"""
        html_content = """
        <html>
            <head>
                <title>Framed Document</title>
            </head>
            <body>
                <img src="main.jpg" alt="Main document">
                <iframe src="iframe1.html">
                    <html>
                        <body>
                            <img src="iframe1.jpg" alt="Iframe 1">
                        </body>
                    </html>
                </iframe>
                <iframe src="iframe2.html">
                    <img src="iframe2.jpg" alt="Iframe 2">
                </iframe>
                <frameset cols="50%,50%">
                    <frame src="frame1.html">
                        <img src="frame1.jpg" alt="Frame 1">
                    </frame>
                    <frame src="frame2.html">
                        <img src="frame2.jpg" alt="Frame 2">
                    </frame>
                </frameset>
            </body>
        </html>
        """
        images = self.parser.extract_images(html_content)
        # The parser should only extract images from the main document, not from frame content
        self.assertEqual(len(images), 1)
        self.assertEqual(images[0]['src'], "main.jpg")
    
    def test_truncated_html(self):
        """Test behavior with truncated HTML"""
        html_content = """
        <html>
            <body>
                <img src="complete.jpg" alt="Complete">
                <img src="truncated.jpg" alt="Truncated
        """
        images = self.parser.extract_images(html_content)
        # Should extract the complete image, might or might not extract the truncated one
        self.assertGreaterEqual(len(images), 1)
        complete_img = next((img for img in images if img['src'] == "complete.jpg"), None)
        self.assertIsNotNone(complete_img)
    
    def test_escaped_characters_in_urls(self):
        """Test URLs with escaped characters"""
        html_content = """
        <html>
            <body>
                <img src="image%20with%20spaces.jpg" alt="URL encoded spaces">
                <img src="image+with+spaces.jpg" alt="Plus for spaces">
                <img src="special%21%40%23%24%25%5E%26%2A%28%29.jpg" alt="URL encoded special chars">
                <img src="query.jpg?name=value&amp;other=123" alt="Query params with HTML escape">
                <img src="percent%25percent.jpg" alt="Percent sign in URL">
            </body>
        </html>
        """
        images = self.parser.extract_images(html_content)
        self.assertEqual(len(images), 5)
        
        # Check all images are found with original URLs (except HTML entities which are decoded)
        src_list = [img['src'] for img in images]
        self.assertIn("image%20with%20spaces.jpg", src_list)
        self.assertIn("image+with+spaces.jpg", src_list)
        self.assertIn("special%21%40%23%24%25%5E%26%2A%28%29.jpg", src_list)
        # HTMLParser decodes &amp; to & in attribute values
        self.assertIn("query.jpg?name=value&other=123", src_list)
        self.assertIn("percent%25percent.jpg", src_list)
        
        # The HTML parser won't automatically decode these URLs
        # So they should be preserved as-is
        special_img = next(img for img in images if img['src'].startswith("special"))
        self.assertEqual(special_img['src'], "special%21%40%23%24%25%5E%26%2A%28%29.jpg")
        
    def test_html5_picture_element(self):
        """Test handling of HTML5 picture element and source tags"""
        html_content = """
        <html>
            <body>
                <picture>
                    <source media="(min-width: 1200px)" srcset="desktop.jpg">
                    <source media="(min-width: 768px)" srcset="tablet.jpg">
                    <img src="mobile.jpg" alt="Responsive image fallback">
                </picture>
                
                <picture>
                    <source media="(min-width: 800px)" srcset="large.jpg 1000w, medium.jpg 750w">
                    <source media="(min-width: 480px)" srcset="small.jpg">
                    <img src="tiny.jpg" alt="Another responsive image">
                </picture>
                
                <img src="standard.jpg" alt="Standard image">
            </body>
        </html>
        """
        images = self.parser.extract_images(html_content)
        # The parser should extract the img elements inside picture elements,
        # but not necessarily capture the source elements
        self.assertGreaterEqual(len(images), 3)
        
        # Check fallback images inside picture elements
        mobile_img = next(img for img in images if img['src'] == "mobile.jpg")
        self.assertEqual(mobile_img['alt'], "Responsive image fallback")
        
        tiny_img = next(img for img in images if img['src'] == "tiny.jpg")
        self.assertEqual(tiny_img['alt'], "Another responsive image")
        
        # Check standard image
        std_img = next(img for img in images if img['src'] == "standard.jpg")
        self.assertEqual(std_img['alt'], "Standard image")
    
    def test_self_closing_vs_normal_tags(self):
        """Test both self-closing and normal tag syntax for img elements"""
        html_content = """
        <html>
            <body>
                <!-- Self-closing with space -->
                <img src="self-close-space.jpg" alt="Self closing with space" />
                
                <!-- Self-closing without space -->
                <img src="self-close-nospace.jpg" alt="Self closing without space"/>
                
                <!-- Normal tag -->
                <img src="normal-tag.jpg" alt="Normal tag">
                
                <!-- Old-school XHTML strict -->
                <img src="xhtml-strict.jpg" alt="XHTML strict"></img>
            </body>
        </html>
        """
        images = self.parser.extract_images(html_content)
        self.assertEqual(len(images), 4)
        
        # Check all syntax variations were found
        src_list = [img['src'] for img in images]
        self.assertIn("self-close-space.jpg", src_list)
        self.assertIn("self-close-nospace.jpg", src_list)
        self.assertIn("normal-tag.jpg", src_list)
        self.assertIn("xhtml-strict.jpg", src_list)
    
    def test_invalid_attribute_syntax(self):
        """Test with invalid attribute syntax"""
        html_content = """
        <html>
            <body>
                <!-- Missing quotes around attribute value -->
                <img src=noquotes.jpg alt=No quotes here>
                
                <!-- Mismatched quotes -->
                <img src="mismatched.jpg' alt='Also mismatched">
                
                <!-- Double quoted attribute containing single quotes -->
                <img src="single'quotes.jpg" alt="Contains 'single' quotes">
                
                <!-- Single quoted attribute containing double quotes -->
                <img src='double"quotes.jpg' alt='Contains "double" quotes'>
                
                <!-- Valid for reference -->
                <img src="valid.jpg" alt="Valid attributes">
            </body>
        </html>
        """
        images = self.parser.extract_images(html_content)
        # The HTML parser should handle what it can
        self.assertGreaterEqual(len(images), 1)
        
        # Check that valid image is definitely there
        valid_img = next((img for img in images if img['src'] == "valid.jpg"), None)
        self.assertIsNotNone(valid_img)
        
        # Check if parser handled unquoted attributes
        noquotes_img = next((img for img in images if img['src'] == "noquotes.jpg"), None)
        if noquotes_img:
            self.assertEqual(noquotes_img['alt'], "No")
        
        # Check single quotes in double-quoted attributes and vice versa
        single_in_double = next((img for img in images if "single'quotes.jpg" in img['src']), None)
        if single_in_double:
            self.assertIn("'single'", single_in_double['alt'])
        
        double_in_single = next((img for img in images if 'double"quotes.jpg' in img['src']), None)
        if double_in_single:
            self.assertIn('"double"', double_in_single['alt'])
    
    def test_image_with_javascript_events(self):
        """Test images with JavaScript event handlers"""
        html_content = """
        <html>
            <body>
                <img src="events.jpg" alt="Events image" 
                     onclick="alert('clicked')" 
                     onload="this.width=200"
                     onerror="this.src='fallback.jpg'"
                     onmouseover="this.style.opacity=0.8"
                     onmouseout="this.style.opacity=1">
                <img src="normal.jpg" alt="Normal image">
            </body>
        </html>
        """
        images = self.parser.extract_images(html_content)
        self.assertEqual(len(images), 2)
        
        # Check event handlers are captured
        events_img = next(img for img in images if img['src'] == "events.jpg")
        self.assertEqual(events_img['onclick'], "alert('clicked')")
        self.assertEqual(events_img['onload'], "this.width=200")
        self.assertEqual(events_img['onerror'], "this.src='fallback.jpg'")
        self.assertEqual(events_img['onmouseover'], "this.style.opacity=0.8")
        self.assertEqual(events_img['onmouseout'], "this.style.opacity=1")
    
    def test_tag_case_sensitivity(self):
        """Test case sensitivity of img tags and attributes"""
        html_content = """
        <html>
            <body>
                <img src="lowercase.jpg" alt="Lowercase tag">
                <IMG src="uppercase-tag.jpg" alt="Uppercase tag">
                <Img src="mixedcase-tag.jpg" alt="Mixed case tag">
                <img SRC="uppercase-attr.jpg" alt="Uppercase attribute">
                <img src="lowercase.jpg" ALT="Uppercase alt attribute">
                <IMG SRC="all-uppercase.jpg" ALT="All uppercase">
            </body>
        </html>
        """
        images = self.parser.extract_images(html_content)
        self.assertEqual(len(images), 6)
        
        # HTML is case-insensitive for tags and attributes
        # Check all variations were found
        srcs = {img['src'] for img in images}
        self.assertEqual(len(srcs), 5)  # One duplicate source
        
        expected_srcs = {
            "lowercase.jpg", 
            "uppercase-tag.jpg", 
            "mixedcase-tag.jpg", 
            "uppercase-attr.jpg", 
            "all-uppercase.jpg"
        }
        self.assertEqual(srcs, expected_srcs)
        
        # Check case of attribute keys
        # HTMLParser might normalize these to lowercase
        img_attrs = list(images[0].keys())
        self.assertIn('src', img_attrs)
        self.assertIn('alt', img_attrs)
    
    def test_high_unicode_characters(self):
        """Test with high Unicode characters in attributes"""
        html_content = """
        <html>
            <body>
                <img src="unicode.jpg" alt="Unicode: 😀🌍🏆🎵🍕🚀">
                <img src="math-symbols.jpg" alt="Math: ∑∫≤≥≠∞">
                <img src="arrows.jpg" alt="Arrows: ←→↑↓⇒⇔">
                <img src="rare-chars.jpg" alt="Rare: ஜ۩۞۩ஜ">
                <img src="astral-plane.jpg" alt="Astral plane: 𐐀𐐁𐐂𐐃𐐄𐐅𐐆𐐇">
            </body>
        </html>
        """
        images = self.parser.extract_images(html_content)
        self.assertEqual(len(images), 5)
        
        # Check all Unicode characters were preserved
        emoji_img = next(img for img in images if img['src'] == "unicode.jpg")
        self.assertEqual(emoji_img['alt'], "Unicode: 😀🌍🏆🎵🍕🚀")
        
        math_img = next(img for img in images if img['src'] == "math-symbols.jpg")
        self.assertEqual(math_img['alt'], "Math: ∑∫≤≥≠∞")
        
        arrow_img = next(img for img in images if img['src'] == "arrows.jpg")
        self.assertEqual(arrow_img['alt'], "Arrows: ←→↑↓⇒⇔")
        
        rare_img = next(img for img in images if img['src'] == "rare-chars.jpg")
        self.assertEqual(rare_img['alt'], "Rare: ஜ۩۞۩ஜ")
        
        astral_img = next(img for img in images if img['src'] == "astral-plane.jpg")
        self.assertEqual(astral_img['alt'], "Astral plane: 𐐀𐐁𐐂𐐃𐐄𐐅𐐆𐐇")
    
    def test_xml_namespace_prefixes(self):
        """Test with XML namespace prefixes"""
        html_content = """
        <html xmlns="http://www.w3.org/1999/xhtml">
            <body>
                <img src="standard.jpg" alt="Standard">
                <xhtml:img src="xhtml-ns.jpg" alt="XHTML namespace">
                <svg:image href="svg-image.jpg" alt="SVG image" />
                <custom:img src="custom-ns.jpg" alt="Custom namespace">
            </body>
        </html>
        """
        images = self.parser.extract_images(html_content)
        # HTMLParser generally only handles standard img tags
        # We expect at least the standard img to be found
        self.assertGreaterEqual(len(images), 1)
        
        # Standard image should be found
        std_img = next((img for img in images if img['src'] == "standard.jpg"), None)
        self.assertIsNotNone(std_img)
    
    def test_extremely_long_document(self):
        """Test with an extremely long document with sparse images"""
        # Create a long document with a few images sprinkled throughout
        paragraphs = []
        for i in range(1000):
            if i % 100 == 0:
                # Insert an image every 100 paragraphs
                paragraphs.append(f'<img src="image{i}.jpg" alt="Image {i}">')
            paragraphs.append(f'<p>This is paragraph {i} with a lot of text that goes on and on to make this a very large document when combined with many other paragraphs. Each paragraph adds more size to the document and makes it longer and longer, simulating a real-world very long document with sparse images.</p>')
        
        html_content = f"""
        <html>
            <body>
                {''.join(paragraphs)}
            </body>
        </html>
        """
        
        # Measure performance
        start_time = time.time()
        images = self.parser.extract_images(html_content)
        end_time = time.time()
        
        # Verify all images were found (should be 10 images)
        self.assertEqual(len(images), 10)
        
        # Check specific images
        self.assertEqual(images[0]['src'], "image0.jpg")
        self.assertEqual(images[5]['src'], "image500.jpg")
        self.assertEqual(images[9]['src'], "image900.jpg")
        
        # Log performance
        print(f"Extracted 10 images from a ~1MB document in {end_time - start_time:.2f} seconds")
    
    def test_image_data_attributes(self):
        """Test images with HTML5 data-* attributes"""
        html_content = """
        <html>
            <body>
                <img src="data-attrs.jpg" alt="Data attributes"
                     data-id="123"
                     data-user="john"
                     data-timestamp="2023-05-16T14:30:00Z"
                     data-width="800"
                     data-height="600"
                     data-tags="nature,landscape,forest"
                     data-location-lat="37.7749"
                     data-location-lng="-122.4194">
                     
                <img src="minimal.jpg" alt="Minimal" data-test>
                
                <img src="empty-data.jpg" alt="Empty data" data-empty="">
            </body>
        </html>
        """
        images = self.parser.extract_images(html_content)
        self.assertEqual(len(images), 3)
        
        # Check data attributes
        data_img = next(img for img in images if img['src'] == "data-attrs.jpg")
        self.assertEqual(data_img['data-id'], "123")
        self.assertEqual(data_img['data-user'], "john")
        self.assertEqual(data_img['data-timestamp'], "2023-05-16T14:30:00Z")
        self.assertEqual(data_img['data-width'], "800")
        self.assertEqual(data_img['data-height'], "600")
        self.assertEqual(data_img['data-tags'], "nature,landscape,forest")
        self.assertEqual(data_img['data-location-lat'], "37.7749")
        self.assertEqual(data_img['data-location-lng'], "-122.4194")
        
        # Check boolean data attribute
        minimal_img = next(img for img in images if img['src'] == "minimal.jpg")
        self.assertIn('data-test', minimal_img)
        
        # Check empty data attribute
        empty_data_img = next(img for img in images if img['src'] == "empty-data.jpg")
        self.assertEqual(empty_data_img['data-empty'], "")
    
    def test_consistency_with_repeated_calls(self):
        """Test consistency of results with repeated calls to extract_images"""
        html_content = """
        <html>
            <body>
                <img src="test1.jpg" alt="Test 1">
                <img src="test2.jpg" alt="Test 2">
                <img src="test3.jpg" alt="Test 3">
            </body>
        </html>
        """
        
        # First call
        images1 = self.parser.extract_images(html_content)
        self.assertEqual(len(images1), 3)
        
        # Second call
        images2 = self.parser.extract_images(html_content)
        self.assertEqual(len(images2), 3)
        
        # Results should be identical
        for i in range(3):
            self.assertEqual(images1[i]['src'], images2[i]['src'])
            self.assertEqual(images1[i]['alt'], images2[i]['alt'])
        
        # Call with different HTML
        other_html = """
        <html>
            <body>
                <img src="other.jpg" alt="Other image">
            </body>
        </html>
        """
        other_images = self.parser.extract_images(other_html)
        self.assertEqual(len(other_images), 1)
        self.assertEqual(other_images[0]['src'], "other.jpg")
        
        # Call again with original HTML
        images3 = self.parser.extract_images(html_content)
        self.assertEqual(len(images3), 3)
        
        # Results should match the first call
        for i in range(3):
            self.assertEqual(images1[i]['src'], images3[i]['src'])
    
    def test_image_tag_with_comments_inside(self):
        """Test image tags with HTML comments inside attribute values or between attributes"""
        html_content = """
        <html>
            <body>
                <img src="normal.jpg" alt="Normal image">
                <img src="comment-between.jpg" <!-- comment between attributes --> alt="Comment between">
                <img src="comment-before-closing.jpg" alt="Comment before closing" <!-- comment before end of tag -->>
                <img src="<!-- commented attribute -->.jpg" alt="Comment in src">
            </body>
        </html>
        """
        images = self.parser.extract_images(html_content)
        
        # HTML comments should not be part of attribute values
        # Should extract what it can - at least the normal image
        self.assertGreaterEqual(len(images), 1)
        
        # Normal image should be found
        normal_img = next((img for img in images if img['src'] == "normal.jpg"), None)
        self.assertIsNotNone(normal_img)
    
    def test_image_extraction_method_directly(self):
        """Test the extract_images method directly on the ImageTagParser class"""
        # Simple HTML
        html_content = '<img src="test.jpg" alt="Test">'
        
        # First test with an instance variable
        instance_images = self.parser.extract_images(html_content)
        self.assertEqual(len(instance_images), 1)
        self.assertEqual(instance_images[0]['src'], "test.jpg")
        
        # Now test with a fresh instance
        parser = ImageTagParser()
        fresh_images = parser.extract_images(html_content)
        self.assertEqual(len(fresh_images), 1)
        self.assertEqual(fresh_images[0]['src'], "test.jpg")
        
        # Test calling multiple times with different content
        html2 = '<img src="another.jpg" alt="Another">'
        images2 = parser.extract_images(html2)
        self.assertEqual(len(images2), 1)
        self.assertEqual(images2[0]['src'], "another.jpg")
        
        def test_html_entity_handling(self):
            """Test how HTML entities in URLs and attributes are handled"""
            # Test with various HTML entities in both URLs and other attributes
            html_content = """
            <html>
                <body>
                    <!-- Entities in URLs -->
                    <img src="query.jpg?param=value&amp;other=123" alt="Ampersand entity">
                    <img src="param.jpg?key=value&#38;param=test" alt="Numeric ampersand entity">
                    <img src="quote&quot;test.jpg" alt="Quote entity in filename">
                    <img src="test&lt;&gt;.jpg" alt="Brackets in filename">
                    
                    <!-- Various entities in alt text -->
                    <img src="entities.jpg" alt="Testing &lt;entities&gt; &amp; more">
                    <img src="mixed.jpg" alt="Mixed &#x3C;hex&#x3E; and &#60;decimal&#62;">
                    
                    <!-- Nested entities -->
                    <img src="nested.jpg?p=v&amp;q=w&amp;r=z" alt="Multiple entities &amp; in &quot;text&quot;">
                </body>
            </html>
            """
            
            # Get raw HTML parsing results using a custom parser
            class EntityPreservingParser(HTMLParser):
                def __init__(self):
                    super().__init__()
                    self.raw_srcs = {}
                    self.raw_alts = {}
                    
                def handle_starttag(self, tag, attrs):
                    if tag == 'img':
                        attrs_dict = dict(attrs)
                        # Use position as a unique key
                        pos_key = str(self.getpos())
                        if 'src' in attrs_dict:
                            self.raw_srcs[pos_key] = attrs_dict['src']
                        if 'alt' in attrs_dict:
                            self.raw_alts[pos_key] = attrs_dict['alt']
            
            # Get the raw attribute values from HTML before standard parsing
            raw_parser = EntityPreservingParser()
            raw_parser.feed(html_content)
            raw_srcs = list(raw_parser.raw_srcs.values())
            
            # Test with the regular parser
            images = self.parser.extract_images(html_content)
            self.assertEqual(len(images), 7)
            
            # Test URL entity handling - note that HTMLParser decodes entities
            src_list = [img['src'] for img in images]
            
            # For ampersand in URL query strings
            self.assertTrue(any('query.jpg?param=value&amp;other=123' in raw_src for raw_src in raw_srcs))
            # Check for the decoded version in parsed results
            self.assertIn('query.jpg?param=value&other=123', src_list)
            
            # For numeric entity in URL
            self.assertTrue(any('param.jpg?key=value&#38;param=test' in raw_src for raw_src in raw_srcs))
            # Check for the decoded version
            self.assertIn('param.jpg?key=value&param=test', src_list)
            
            # For quote entity in filename
            self.assertTrue(any('quote&quot;test.jpg' in raw_src for raw_src in raw_srcs))
            # Check for the decoded version
            self.assertIn('quote"test.jpg', src_list)
            
            # Check entities in alt text are properly decoded
            alt_texts = [img['alt'] for img in images]
            self.assertIn('Testing <entities> & more', alt_texts)
            self.assertIn('Mixed <hex> and <decimal>', alt_texts)
            
            # For multiple entities in a single URL
            nested_url = next((img['src'] for img in images if img['src'].startswith('nested.jpg')), None)
            self.assertIsNotNone(nested_url)
            self.assertEqual(nested_url, 'nested.jpg?p=v&q=w&r=z')
            
            self.assertIn("percent%25percent.jpg", src_list)

        def test_html_entity_handling_in_urls(self):
            """Test specifically how HTML entities in URLs are handled"""
            html_content = """
            <html>
                <body>
                    <img src="image.jpg?param=value&amp;other=123" alt="Ampersand entity">
                    <img src="image.jpg?param=value&#38;other=123" alt="Numeric ampersand entity">
                    <img src="quote&quot;mark.jpg" alt="Quote entity in filename">
                    <img src="spaces&nbsp;test.jpg" alt="Non-breaking space entity">
                </body>
            </html>
            """
            images = self.parser.extract_images(html_content)
            self.assertEqual(len(images), 4)
            
            # The standard HTMLParser converts HTML entities in attribute values
            src_list = [img['src'] for img in images]
            
            # Note: Entities in URLs are converted by HTMLParser
            self.assertIn("image.jpg?param=value&other=123", src_list)
            
            # Document the current behavior for clarity
            # Your test can either:
            # 1. Assert the current behavior (entities decoded)
            # 2. Build in tolerance for both forms
            
            ampersand_img = next(img for img in images if "amp" in img['alt'])
            self.assertEqual(ampersand_img['src'], "image.jpg?param=value&other=123")
            
            # For non-URL attributes like 'alt', entities should be properly decoded
            for img in images:
                if "Ampersand" in img['alt']:
                    self.assertEqual(img['alt'], "Ampersand entity")
if __name__ == '__main__':
    unittest.main()