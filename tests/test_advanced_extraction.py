#!/usr/bin/env python3
"""
Tests for advanced extraction features
"""

import pytest
import json
from crawlit.extractors import (
    FormExtractor, Form, FormField, extract_forms,
    StructuredDataExtractor, StructuredData, extract_structured_data,
    LanguageDetector, LanguageDetection, detect_language
)


class TestFormExtraction:
    """Test form extraction"""
    
    def test_basic_form_extraction(self):
        """Test extracting a basic form"""
        html = '''
        <form action="/submit" method="POST">
            <input type="text" name="username" placeholder="Username">
            <input type="password" name="password" required>
            <input type="submit" value="Login">
        </form>
        '''
        
        extractor = FormExtractor(html)
        forms = extractor.extract_all_forms()
        
        assert len(forms) == 1
        form = forms[0]
        assert form.action == '/submit'
        assert form.method == 'POST'
        assert len(form.fields) == 2  # submit button not included
    
    def test_form_with_labels(self):
        """Test form with field labels"""
        html = '''
        <form action="/contact">
            <label for="email">Email:</label>
            <input type="email" id="email" name="email">
            
            <label for="message">Message:</label>
            <textarea id="message" name="message"></textarea>
        </form>
        '''
        
        forms = extract_forms(html)
        
        assert len(forms) == 1
        form = forms[0]
        
        # Check that labels were associated
        email_field = next(f for f in form.fields if f.name == 'email')
        assert email_field.label == 'Email:'
        
        message_field = next(f for f in form.fields if f.name == 'message')
        assert message_field.label == 'Message:'
    
    def test_select_field_extraction(self):
        """Test extracting select fields"""
        html = '''
        <form>
            <select name="country">
                <option value="us">United States</option>
                <option value="uk" selected>United Kingdom</option>
                <option value="ca">Canada</option>
            </select>
        </form>
        '''
        
        forms = extract_forms(html)
        form = forms[0]
        
        country_field = next(f for f in form.fields if f.name == 'country')
        assert country_field.field_type == 'select'
        assert len(country_field.options) == 3
        assert country_field.value == 'uk'  # selected option
    
    def test_csrf_token_detection(self):
        """Test CSRF token detection"""
        html = '''
        <form action="/submit" method="POST">
            <input type="hidden" name="csrf_token" value="abc123">
            <input type="text" name="username">
        </form>
        '''
        
        forms = extract_forms(html)
        form = forms[0]
        
        assert form.has_csrf_token
    
    def test_file_upload_detection(self):
        """Test file upload detection"""
        html = '''
        <form enctype="multipart/form-data">
            <input type="file" name="avatar">
            <input type="text" name="description">
        </form>
        '''
        
        forms = extract_forms(html)
        form = forms[0]
        
        assert form.has_file_upload
        assert form.enctype == 'multipart/form-data'
    
    def test_captcha_detection(self):
        """Test CAPTCHA detection"""
        html = '''
        <form action="/submit">
            <input type="text" name="username">
            <div class="g-recaptcha" data-sitekey="..."></div>
        </form>
        '''
        
        forms = extract_forms(html)
        form = forms[0]
        
        assert form.has_captcha
    
    def test_login_form_detection(self):
        """Test heuristic login form detection"""
        html = '''
        <form action="/login" method="POST">
            <input type="text" name="username">
            <input type="password" name="password">
            <button type="submit">Sign In</button>
        </form>
        '''
        
        extractor = FormExtractor(html)
        extractor.extract_all_forms()
        login_forms = extractor.get_login_forms()
        
        assert len(login_forms) == 1
        assert login_forms[0].submit_button_text == 'Sign In'
    
    def test_search_form_detection(self):
        """Test heuristic search form detection"""
        html = '''
        <form action="/search" method="GET">
            <input type="text" name="q" placeholder="Search...">
            <button type="submit">Search</button>
        </form>
        '''
        
        extractor = FormExtractor(html)
        extractor.extract_all_forms()
        search_forms = extractor.get_search_forms()
        
        assert len(search_forms) == 1
    
    def test_form_field_attributes(self):
        """Test extracting field attributes"""
        html = '''
        <form>
            <input type="text" name="email" 
                   required 
                   maxlength="100" 
                   pattern="[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}$"
                   placeholder="email@example.com">
        </form>
        '''
        
        forms = extract_forms(html)
        field = forms[0].fields[0]
        
        assert field.required
        assert field.maxlength == 100
        assert field.pattern is not None
        assert field.placeholder == 'email@example.com'


class TestStructuredDataExtraction:
    """Test structured data extraction"""
    
    def test_json_ld_extraction(self):
        """Test JSON-LD extraction"""
        html = '''
        <html>
        <head>
            <script type="application/ld+json">
            {
                "@context": "https://schema.org",
                "@type": "Article",
                "headline": "Test Article",
                "author": "John Doe"
            }
            </script>
        </head>
        </html>
        '''
        
        data = extract_structured_data(html)
        
        assert len(data.json_ld) == 1
        assert data.json_ld[0]['@type'] == 'Article'
        assert data.json_ld[0]['headline'] == 'Test Article'
    
    def test_json_ld_graph(self):
        """Test JSON-LD with @graph"""
        html = '''
        <script type="application/ld+json">
        {
            "@context": "https://schema.org",
            "@graph": [
                {"@type": "Organization", "name": "Example Corp"},
                {"@type": "WebSite", "url": "https://example.com"}
            ]
        }
        </script>
        '''
        
        data = extract_structured_data(html)
        
        assert len(data.json_ld) == 2
        assert data.json_ld[0]['@type'] == 'Organization'
        assert data.json_ld[1]['@type'] == 'WebSite'
    
    def test_microdata_extraction(self):
        """Test Microdata extraction"""
        html = '''
        <div itemscope itemtype="https://schema.org/Person">
            <span itemprop="name">Jane Doe</span>
            <span itemprop="jobTitle">Professor</span>
            <img itemprop="image" src="photo.jpg">
        </div>
        '''
        
        data = extract_structured_data(html)
        
        assert len(data.microdata) == 1
        item = data.microdata[0]
        assert item['@type'] == 'Person'
        assert item['name'] == 'Jane Doe'
        assert item['jobTitle'] == 'Professor'
    
    def test_nested_microdata(self):
        """Test nested Microdata"""
        html = '''
        <div itemscope itemtype="https://schema.org/Movie">
            <span itemprop="name">Avatar</span>
            <div itemprop="director" itemscope itemtype="https://schema.org/Person">
                <span itemprop="name">James Cameron</span>
            </div>
        </div>
        '''
        
        data = extract_structured_data(html)
        
        assert len(data.microdata) == 1
        movie = data.microdata[0]
        assert movie['name'] == 'Avatar'
        assert isinstance(movie['director'], dict)
        assert movie['director']['@type'] == 'Person'
        assert movie['director']['name'] == 'James Cameron'
    
    def test_open_graph_extraction(self):
        """Test Open Graph extraction"""
        html = '''
        <html>
        <head>
            <meta property="og:title" content="Example Page">
            <meta property="og:type" content="website">
            <meta property="og:url" content="https://example.com">
            <meta property="og:image" content="https://example.com/image.jpg">
        </head>
        </html>
        '''
        
        data = extract_structured_data(html)
        
        assert data.open_graph['title'] == 'Example Page'
        assert data.open_graph['type'] == 'website'
        assert data.open_graph['url'] == 'https://example.com'
        assert data.open_graph['image'] == 'https://example.com/image.jpg'
    
    def test_twitter_cards_extraction(self):
        """Test Twitter Cards extraction"""
        html = '''
        <html>
        <head>
            <meta name="twitter:card" content="summary_large_image">
            <meta name="twitter:site" content="@example">
            <meta name="twitter:title" content="Example Page">
            <meta name="twitter:description" content="A test page">
        </head>
        </html>
        '''
        
        data = extract_structured_data(html)
        
        assert data.twitter_cards['card'] == 'summary_large_image'
        assert data.twitter_cards['site'] == '@example'
        assert data.twitter_cards['title'] == 'Example Page'
    
    def test_schema_type_detection(self):
        """Test Schema.org type detection"""
        html = '''
        <script type="application/ld+json">
        {
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": "Test"
        }
        </script>
        '''
        
        extractor = StructuredDataExtractor(html)
        extractor.extract_all()
        
        assert extractor.has_schema_type('Article')
        assert not extractor.has_schema_type('Product')
    
    def test_get_by_type(self):
        """Test getting items by type"""
        html = '''
        <script type="application/ld+json">
        [
            {"@type": "Article", "headline": "Article 1"},
            {"@type": "Product", "name": "Product 1"},
            {"@type": "Article", "headline": "Article 2"}
        ]
        </script>
        '''
        
        extractor = StructuredDataExtractor(html)
        extractor.extract_all()
        
        articles = extractor.get_by_type('Article')
        assert len(articles) == 2
        
        products = extractor.get_by_type('Product')
        assert len(products) == 1


class TestLanguageDetection:
    """Test language detection"""
    
    def test_html_lang_attribute(self):
        """Test detection from HTML lang attribute"""
        html = '<html lang="en-US"><body>Content</body></html>'
        
        result = detect_language(html)
        
        assert result.html_lang == 'en'
        assert result.primary_language == 'en'
        assert 'html_lang' in result.detection_methods
    
    def test_meta_tag_detection(self):
        """Test detection from meta tags"""
        html = '''
        <html>
        <head>
            <meta http-equiv="content-language" content="es">
        </head>
        </html>
        '''
        
        result = detect_language(html)
        
        assert result.meta_lang == 'es'
        assert 'meta_tags' in result.detection_methods
    
    def test_url_pattern_detection(self):
        """Test detection from URL patterns"""
        html = '<html><body>Test content</body></html>'
        url = 'https://example.com/fr/page'
        
        result = detect_language(html, url)
        
        assert 'url' in result.detection_methods
        assert result.detection_methods['url'] == 'fr'
    
    def test_character_pattern_detection_japanese(self):
        """Test detection of Japanese characters"""
        html = '''<html><body>
        これは日本語のテキストです。漢字もあります。日本は美しい国です。
        東京は日本の首都です。富士山は有名な山です。桜の花が綺麗です。
        日本語は難しいですが、面白い言語です。
        </body></html>'''
        
        result = detect_language(html)
        
        assert result.primary_language == 'ja'
        assert result.confidence > 0.3
    
    def test_character_pattern_detection_russian(self):
        """Test detection of Russian Cyrillic"""
        html = '''<html><body>
        Это русский текст с кириллическими буквами. Москва - столица России.
        Русский язык очень интересный. Красная площадь находится в центре Москвы.
        Зимой в России очень холодно. Русская литература знаменита во всем мире.
        </body></html>'''
        
        result = detect_language(html)
        
        assert result.primary_language == 'ru'
    
    def test_character_pattern_detection_arabic(self):
        """Test detection of Arabic script"""
        html = '''<html><body>
        هذا نص عربي مكتوب بالأحرف العربية. اللغة العربية جميلة جداً.
        العالم العربي واسع ومتنوع. القاهرة هي عاصمة مصر.
        الأهرامات من عجائب الدنيا السبع. الخط العربي فن راقي.
        </body></html>'''
        
        result = detect_language(html)
        
        assert result.primary_language == 'ar'
    
    def test_common_words_detection_english(self):
        """Test detection from English common words"""
        html = '''
        <html><body>
        The quick brown fox jumps over the lazy dog. This is a test of the 
        language detection system. It should be able to detect English.
        </body></html>
        '''
        
        result = detect_language(html)
        
        assert result.primary_language == 'en'
        assert 'common_words' in result.detection_methods
    
    def test_common_words_detection_spanish(self):
        """Test detection from Spanish common words"""
        html = '''
        <html><body>
        El rápido zorro marrón salta sobre el perro perezoso. Esta es una 
        prueba del sistema de detección de idiomas. Debería poder detectar español.
        </body></html>
        '''
        
        result = detect_language(html)
        
        assert result.primary_language == 'es'
    
    def test_common_words_detection_french(self):
        """Test detection from French common words"""
        html = '''
        <html><body>
        Le rapide renard brun saute par-dessus le chien paresseux. C'est un test 
        du système de détection de langue. Il devrait pouvoir détecter le français.
        </body></html>
        '''
        
        result = detect_language(html)
        
        assert result.primary_language == 'fr'
    
    def test_confidence_scoring(self):
        """Test confidence scoring"""
        # Multiple methods agreeing
        html = '''
        <html lang="en">
        <head><meta http-equiv="content-language" content="en"></head>
        <body>
        The quick brown fox jumps over the lazy dog. This is English content 
        with many common English words.
        </body>
        </html>
        '''
        
        result = detect_language(html, url="https://example.com/en/page")
        
        # With multiple methods agreeing, confidence should be high
        assert result.confidence > 0.7
        assert len(result.detection_methods) >= 2
    
    def test_multilingual_detection(self):
        """Test multilingual page detection"""
        html = '''
        <html><body>
        <p>English text with common words like the, and, for, with many other words</p>
        <p>Texto en español con palabras comunes como de, la, que, el, en, y otras</p>
        <p>Texte français avec des mots communs comme de, le, la, et, un, à, être</p>
        </body></html>
        '''
        
        detector = LanguageDetector(html)
        multilingual = detector.detect_multilingual()
        
        # Should detect at least one language (multilingual detection is challenging)
        assert len(multilingual) >= 1
    
    def test_unknown_language(self):
        """Test handling of unknown/undetectable language"""
        html = '<html><body>123 456 789</body></html>'
        
        result = detect_language(html)
        
        # Should handle gracefully
        assert isinstance(result, LanguageDetection)


class TestAdvancedExtractionIntegration:
    """Integration tests for advanced extraction"""
    
    def test_extract_all_from_complex_page(self):
        """Test extracting all features from a complex page"""
        html = '''
        <html lang="en">
        <head>
            <meta property="og:title" content="Test Page">
            <script type="application/ld+json">
            {
                "@type": "Article",
                "headline": "Test Article"
            }
            </script>
        </head>
        <body>
            <form action="/login" method="POST">
                <input type="text" name="username">
                <input type="password" name="password">
            </form>
            
            <p>This is English text with many common words.</p>
        </body>
        </html>
        '''
        
        # Extract forms
        forms = extract_forms(html)
        assert len(forms) >= 1
        
        # Extract structured data
        structured_data = extract_structured_data(html)
        assert len(structured_data.json_ld) >= 1
        assert structured_data.open_graph['title'] == 'Test Page'
        
        # Detect language
        lang = detect_language(html)
        assert lang.primary_language == 'en'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

