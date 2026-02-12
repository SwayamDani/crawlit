#!/usr/bin/env python3
"""
Advanced Extraction Features Demo

Demonstrates all advanced extraction features in crawlit:
- Form detection and extraction
- Structured data extraction (JSON-LD, Microdata, RDFa, Open Graph, Twitter Cards)
- Advanced language detection
"""

from crawlit.extractors import (
    extract_forms,
    extract_structured_data,
    detect_language
)


def demo_form_extraction():
    """Demonstrate form extraction"""
    print("=" * 70)
    print("FORM EXTRACTION DEMO")
    print("=" * 70)
    
    html = '''
    <html>
    <body>
        <h2>Login Form</h2>
        <form action="/login" method="POST" id="loginForm">
            <input type="hidden" name="csrf_token" value="abc123xyz">
            
            <label for="username">Username:</label>
            <input type="text" id="username" name="username" 
                   required maxlength="50" placeholder="Enter username">
            
            <label for="password">Password:</label>
            <input type="password" id="password" name="password" required>
            
            <button type="submit">Sign In</button>
        </form>
        
        <h2>Contact Form</h2>
        <form action="/contact" method="POST" enctype="multipart/form-data">
            <label for="name">Name:</label>
            <input type="text" id="name" name="name" required>
            
            <label for="email">Email:</label>
            <input type="email" id="email" name="email" required 
                   pattern="[a-z0-9._%+-]+@[a-z0-9.-]+\\.[a-z]{2,}$">
            
            <label for="country">Country:</label>
            <select id="country" name="country">
                <option value="us">United States</option>
                <option value="uk" selected>United Kingdom</option>
                <option value="ca">Canada</option>
            </select>
            
            <label for="message">Message:</label>
            <textarea id="message" name="message" rows="5" 
                      maxlength="500" placeholder="Your message..."></textarea>
            
            <label for="attachment">Attachment:</label>
            <input type="file" id="attachment" name="attachment">
            
            <div class="g-recaptcha" data-sitekey="..."></div>
            
            <button type="submit">Send Message</button>
        </form>
    </body>
    </html>
    '''
    
    forms = extract_forms(html)
    
    print(f"\nFound {len(forms)} form(s)\n")
    
    for i, form in enumerate(forms, 1):
        print(f"--- Form {i} ---")
        print(f"Action: {form.action}")
        print(f"Method: {form.method}")
        print(f"ID: {form.form_id}")
        print(f"Fields: {len(form.fields)}")
        print(f"CSRF Token: {'Yes' if form.has_csrf_token else 'No'}")
        print(f"File Upload: {'Yes' if form.has_file_upload else 'No'}")
        print(f"CAPTCHA: {'Yes' if form.has_captcha else 'No'}")
        print(f"Submit Button: {form.submit_button_text}")
        
        print(f"\nFields:")
        for field in form.fields:
            print(f"  - {field.name} ({field.field_type})")
            if field.label:
                print(f"    Label: {field.label}")
            if field.required:
                print(f"    Required: Yes")
            if field.placeholder:
                print(f"    Placeholder: {field.placeholder}")
            if field.options:
                print(f"    Options: {', '.join(field.options[:3])}...")
        print()
    
    print("\n")


def demo_structured_data_extraction():
    """Demonstrate structured data extraction"""
    print("=" * 70)
    print("STRUCTURED DATA EXTRACTION DEMO")
    print("=" * 70)
    
    html = '''
    <html lang="en">
    <head>
        <title>Example Article</title>
        
        <!-- JSON-LD -->
        <script type="application/ld+json">
        {
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": "Advanced Web Crawling Techniques",
            "author": {
                "@type": "Person",
                "name": "John Doe"
            },
            "datePublished": "2026-02-11",
            "image": "https://example.com/article-image.jpg"
        }
        </script>
        
        <!-- Open Graph -->
        <meta property="og:title" content="Advanced Web Crawling Techniques">
        <meta property="og:type" content="article">
        <meta property="og:url" content="https://example.com/article">
        <meta property="og:image" content="https://example.com/og-image.jpg">
        <meta property="og:description" content="Learn advanced web crawling techniques">
        
        <!-- Twitter Cards -->
        <meta name="twitter:card" content="summary_large_image">
        <meta name="twitter:site" content="@example">
        <meta name="twitter:title" content="Advanced Web Crawling Techniques">
        <meta name="twitter:description" content="Learn advanced techniques">
        <meta name="twitter:image" content="https://example.com/twitter-image.jpg">
        
        <!-- Standard Meta Tags -->
        <meta name="description" content="A comprehensive guide to web crawling">
        <meta name="keywords" content="web crawling, scraping, python">
        <meta name="author" content="John Doe">
    </head>
    <body>
        <!-- Microdata -->
        <div itemscope itemtype="https://schema.org/Product">
            <span itemprop="name">Web Crawler Pro</span>
            <span itemprop="brand">CrawlTech</span>
            <span itemprop="price" content="99.99">$99.99</span>
            <div itemprop="aggregateRating" itemscope itemtype="https://schema.org/AggregateRating">
                Rating: <span itemprop="ratingValue">4.8</span> out of 
                <span itemprop="bestRating">5</span>
                based on <span itemprop="ratingCount">120</span> reviews
            </div>
        </div>
        
        <!-- RDFa -->
        <div vocab="https://schema.org/" typeof="Event">
            <span property="name">Web Crawling Conference 2026</span>
            <span property="startDate" content="2026-05-15">May 15, 2026</span>
            <span property="location" typeof="Place">
                <span property="name">Tech Center</span>
                <span property="address">San Francisco, CA</span>
            </span>
        </div>
    </body>
    </html>
    '''
    
    data = extract_structured_data(html)
    
    # JSON-LD
    print("\n--- JSON-LD ---")
    if data.json_ld:
        for item in data.json_ld:
            print(f"Type: {item.get('@type')}")
            print(f"Content: {item}")
    else:
        print("No JSON-LD found")
    
    # Microdata
    print("\n--- Microdata ---")
    if data.microdata:
        for item in data.microdata:
            print(f"Type: {item.get('@type')}")
            for key, value in item.items():
                if key not in ['@type', '@context']:
                    print(f"  {key}: {value}")
    else:
        print("No Microdata found")
    
    # RDFa
    print("\n--- RDFa ---")
    if data.rdfa:
        for item in data.rdfa:
            print(f"Type: {item.get('@type')}")
            for key, value in item.items():
                if key not in ['@type', '@context']:
                    print(f"  {key}: {value}")
    else:
        print("No RDFa found")
    
    # Open Graph
    print("\n--- Open Graph ---")
    if data.open_graph:
        for key, value in data.open_graph.items():
            print(f"  {key}: {value}")
    else:
        print("No Open Graph data found")
    
    # Twitter Cards
    print("\n--- Twitter Cards ---")
    if data.twitter_cards:
        for key, value in data.twitter_cards.items():
            print(f"  {key}: {value}")
    else:
        print("No Twitter Cards data found")
    
    # Schema Types
    print("\n--- Schema.org Types Found ---")
    extractor = data  # StructuredData object
    # Re-extract to get extractor
    from crawlit.extractors import StructuredDataExtractor
    extractor = StructuredDataExtractor(html)
    extractor.extract_all()
    types = extractor.get_schema_types()
    print(f"  {', '.join(types)}")
    
    print("\n")


def demo_language_detection():
    """Demonstrate language detection"""
    print("=" * 70)
    print("LANGUAGE DETECTION DEMO")
    print("=" * 70)
    
    # Example 1: English with explicit declaration
    print("\n--- Example 1: English (Explicit HTML lang) ---")
    html_en = '''
    <html lang="en-US">
    <head>
        <meta http-equiv="content-language" content="en">
        <title>Welcome to Our Website</title>
    </head>
    <body>
        <h1>Advanced Web Crawling</h1>
        <p>This is a comprehensive guide to web crawling and scraping. 
        The crawler can extract data from various sources and process 
        it efficiently. We provide tools for modern web development.</p>
    </body>
    </html>
    '''
    
    result = detect_language(html_en, url="https://example.com/en/page")
    print(f"Primary Language: {result.primary_language}")
    print(f"Confidence: {result.confidence:.2%}")
    print(f"Detection Methods: {', '.join(result.detection_methods.keys())}")
    print(f"All Detections: {result.detected_languages}")
    
    # Example 2: Spanish
    print("\n--- Example 2: Spanish (Content-based) ---")
    html_es = '''
    <html>
    <body>
        <h1>Guía de Rastreo Web</h1>
        <p>Esta es una guía completa para el rastreo y extracción de datos 
        web. El rastreador puede extraer datos de varias fuentes y procesarlos 
        de manera eficiente. Proporcionamos herramientas para el desarrollo 
        web moderno.</p>
    </body>
    </html>
    '''
    
    result = detect_language(html_es)
    print(f"Primary Language: {result.primary_language}")
    print(f"Confidence: {result.confidence:.2%}")
    print(f"Detection Methods: {', '.join(result.detection_methods.keys())}")
    
    # Example 3: Japanese (Character-based)
    print("\n--- Example 3: Japanese (Character-based) ---")
    html_ja = '''
    <html>
    <body>
        <h1>ウェブクローリングガイド</h1>
        <p>これはウェブクローリングとデータ抽出の包括的なガイドです。
        クローラーは様々なソースからデータを抽出し、効率的に処理できます。
        現代的なウェブ開発のためのツールを提供しています。</p>
    </body>
    </html>
    '''
    
    result = detect_language(html_ja)
    print(f"Primary Language: {result.primary_language}")
    print(f"Confidence: {result.confidence:.2%}")
    print(f"Detection Methods: {', '.join(result.detection_methods.keys())}")
    
    # Example 4: French
    print("\n--- Example 4: French (Content-based) ---")
    html_fr = '''
    <html>
    <body>
        <h1>Guide de Crawling Web</h1>
        <p>Ceci est un guide complet pour le crawling web et l'extraction de données. 
        Le crawler peut extraire des données de diverses sources et les traiter 
        efficacement. Nous fournissons des outils pour le développement web moderne.</p>
    </body>
    </html>
    '''
    
    result = detect_language(html_fr)
    print(f"Primary Language: {result.primary_language}")
    print(f"Confidence: {result.confidence:.2%}")
    print(f"Detection Methods: {', '.join(result.detection_methods.keys())}")
    
    # Example 5: Arabic (RTL script)
    print("\n--- Example 5: Arabic (RTL Character-based) ---")
    html_ar = '''
    <html>
    <body>
        <h1>دليل الزحف على الويب</h1>
        <p>هذا دليل شامل للزحف على الويب واستخراج البيانات.
        يمكن للزاحف استخراج البيانات من مصادر مختلفة ومعالجتها بكفاءة.
        نحن نقدم أدوات لتطوير الويب الحديث.</p>
    </body>
    </html>
    '''
    
    result = detect_language(html_ar)
    print(f"Primary Language: {result.primary_language}")
    print(f"Confidence: {result.confidence:.2%}")
    print(f"Detection Methods: {', '.join(result.detection_methods.keys())}")
    
    print("\n")


def demo_integrated_extraction():
    """Demonstrate integrated extraction from a complex page"""
    print("=" * 70)
    print("INTEGRATED EXTRACTION DEMO")
    print("=" * 70)
    
    html = '''
    <html lang="en">
    <head>
        <title>Product Page - Web Crawler Pro</title>
        <script type="application/ld+json">
        {
            "@context": "https://schema.org",
            "@type": "Product",
            "name": "Web Crawler Pro",
            "offers": {
                "@type": "Offer",
                "price": "99.99",
                "priceCurrency": "USD"
            }
        }
        </script>
        <meta property="og:title" content="Web Crawler Pro">
        <meta property="og:type" content="product">
    </head>
    <body>
        <h1>Web Crawler Pro</h1>
        <p>The professional web crawling solution with advanced features.</p>
        
        <form action="/purchase" method="POST">
            <input type="hidden" name="csrf_token" value="secure123">
            <input type="email" name="email" required placeholder="Your email">
            <button type="submit">Buy Now</button>
        </form>
    </body>
    </html>
    '''
    
    print("\n1. Forms:")
    forms = extract_forms(html)
    print(f"   Found {len(forms)} form(s)")
    if forms:
        print(f"   - Action: {forms[0].action}")
        print(f"   - CSRF Protected: {forms[0].has_csrf_token}")
    
    print("\n2. Structured Data:")
    data = extract_structured_data(html)
    print(f"   JSON-LD items: {len(data.json_ld)}")
    print(f"   Open Graph: {'Yes' if data.open_graph else 'No'}")
    if data.json_ld:
        print(f"   Product: {data.json_ld[0].get('name')}")
    
    print("\n3. Language:")
    lang = detect_language(html)
    print(f"   Detected: {lang.primary_language}")
    print(f"   Confidence: {lang.confidence:.2%}")
    
    print("\n")


def main():
    """Run all demos"""
    print("\n")
    print("=" * 70)
    print("CRAWLIT ADVANCED EXTRACTION FEATURES DEMONSTRATION")
    print("=" * 70)
    print("\n")
    
    demo_form_extraction()
    demo_structured_data_extraction()
    demo_language_detection()
    demo_integrated_extraction()
    
    print("=" * 70)
    print("DEMO COMPLETE")
    print("=" * 70)
    print("\nFor more information, see the documentation")
    print("\n")


if __name__ == '__main__':
    main()

