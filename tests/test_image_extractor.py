#!/usr/bin/env python3
"""
test_image_extractor.py - Tests for the image extraction functionality
"""

import unittest
from crawlit.extractors.image_extractor import ImageTagParser

class TestImageExtractor(unittest.TestCase):
    def setUp(self):
        self.extractor = ImageTagParser()
        
    def test_extract_basic_image(self):
        html = """
        <html>
            <body>
                <img src="image.jpg" alt="Test image">
            </body>
        </html>
        """
        images = self.extractor.extract_images(html)
        self.assertEqual(len(images), 1)
        self.assertEqual(images[0]["src"], "image.jpg")
        self.assertEqual(images[0]["alt"], "Test image")
        self.assertFalse(images[0]["decorative"])
        self.assertEqual(images[0]["parent_tag"], "body")
        
    def test_extract_multiple_images(self):
        html = """
        <html>
            <body>
                <div>
                    <img src="image1.jpg" alt="First image" width="100" height="100">
                    <p>Some text</p>
                    <img src="image2.jpg" class="hero">
                    <img src="image3.jpg" alt="" title="Decorative element">
                </div>
            </body>
        </html>
        """
        images = self.extractor.extract_images(html)
        self.assertEqual(len(images), 3)
        
        # Check first image
        self.assertEqual(images[0]["src"], "image1.jpg")
        self.assertEqual(images[0]["alt"], "First image")
        self.assertEqual(images[0]["width"], 100)
        self.assertEqual(images[0]["height"], 100)
        
        # Check second image
        self.assertEqual(images[1]["src"], "image2.jpg")
        self.assertEqual(images[1]["class"], "hero")
        self.assertTrue(images[1]["decorative"])  # No alt text
        
        # Check third image
        self.assertEqual(images[2]["src"], "image3.jpg")
        self.assertEqual(images[2]["alt"], "")
        self.assertEqual(images[2]["title"], "Decorative element")
        self.assertTrue(images[2]["decorative"])  # Empty alt text
        
    def test_empty_html(self):
        images = self.extractor.extract_images("")
        self.assertEqual(images, [])
        
    def test_no_images(self):
        html = """
        <html>
            <body>
                <p>This is a page with no images</p>
                <div>Just some text content</div>
            </body>
        </html>
        """
        images = self.extractor.extract_images(html)
        self.assertEqual(images, [])
        
    def test_malformed_images(self):
        html = """
        <html>
            <body>
                <img>  <!-- No src attribute -->
                <img src="">  <!-- Empty src attribute -->
                <img src="valid.jpg">  <!-- Valid image -->
            </body>
        </html>
        """
        images = self.extractor.extract_images(html)
        self.assertEqual(len(images), 1)
        self.assertEqual(images[0]["src"], "valid.jpg")
        
    def test_nested_images(self):
        html = """
        <html>
            <body>
                <div>
                    <section>
                        <article>
                            <img src="deeply/nested/image.png" alt="Nested image">
                        </article>
                    </section>
                </div>
            </body>
        </html>
        """
        images = self.extractor.extract_images(html)
        self.assertEqual(len(images), 1)
        self.assertEqual(images[0]["src"], "deeply/nested/image.png")
        self.assertEqual(images[0]["parent_tag"], "article")

    def test_special_characters(self):
        html = """
        <html>
            <body>
                <img src="image.jpg" alt="Test with &lt;special&gt; &amp; characters">
            </body>
        </html>
        """
        images = self.extractor.extract_images(html)
        self.assertEqual(len(images), 1)
        self.assertEqual(images[0]["alt"], "Test with <special> & characters")

if __name__ == '__main__':
    unittest.main()