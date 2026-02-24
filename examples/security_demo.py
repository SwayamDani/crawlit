#!/usr/bin/env python3
"""
Security Features Demo

Demonstrates all security features in crawlit:
- CSRF token extraction and handling
- Security headers analysis
- WAF detection
- Honeypot detection
"""

from crawlit.security import (
    CSRFTokenExtractor,
    CSRFTokenHandler,
    analyze_security_headers,
    detect_waf,
    detect_honeypots
)


def demo_csrf_extraction():
    """Demonstrate CSRF token extraction"""
    print("=" * 60)
    print("CSRF TOKEN EXTRACTION DEMO")
    print("=" * 60)
    
    html = """
    <html>
        <head>
            <meta name="csrf-token" content="meta-token-abc123">
        </head>
        <body>
            <form method="post" action="/login">
                <input type="hidden" name="csrf_token" value="form-token-xyz789">
                <input type="text" name="username">
                <input type="password" name="password">
            </form>
        </body>
    </html>
    """
    
    extractor = CSRFTokenExtractor(html, url="https://example.com/login")
    tokens = extractor.extract_all_tokens()
    
    print(f"\nFound {len(tokens)} CSRF token(s):")
    for name, value in tokens.items():
        print(f"  {name}: {value}")
    
    print("\n")


def demo_csrf_handler():
    """Demonstrate CSRF token handler"""
    print("=" * 60)
    print("CSRF TOKEN HANDLER DEMO")
    print("=" * 60)
    
    handler = CSRFTokenHandler()
    
    # Extract and store tokens
    html = '<form><input type="hidden" name="csrf_token" value="token123"></form>'
    handler.extract_and_store("https://example.com", html)
    
    # Set global token
    handler.set_global_token("api_key", "global-api-key")
    
    # Add tokens to request
    form_data = {'username': 'john', 'password': 'secret'}
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    data, headers = handler.add_tokens_to_request(
        "https://example.com",
        data=form_data,
        headers=headers
    )
    
    print("\nOriginal form data: {'username': 'john', 'password': 'secret'}")
    print(f"With CSRF tokens: {data}")
    print(f"\nHeaders include: {list(headers.keys())}")
    
    stats = handler.get_statistics()
    print(f"\nStatistics: {stats}")
    
    print("\n")


def demo_security_headers():
    """Demonstrate security headers analysis"""
    print("=" * 60)
    print("SECURITY HEADERS ANALYSIS DEMO")
    print("=" * 60)
    
    # Example 1: Good security
    print("\n--- Example 1: Well-Secured Site ---")
    headers_good = {
        'Strict-Transport-Security': 'max-age=31536000; includeSubDomains; preload',
        'Content-Security-Policy': "default-src 'self'; script-src 'self' 'unsafe-inline'",
        'X-Frame-Options': 'DENY',
        'X-Content-Type-Options': 'nosniff',
        'X-XSS-Protection': '1; mode=block',
        'Referrer-Policy': 'strict-origin-when-cross-origin'
    }
    
    result = analyze_security_headers(headers_good, url="https://secure-site.example")
    print(f"Rating: {result.rating.value}")
    print(f"Score: {result.overall_score}/75")
    print(f"Missing headers: {len(result.missing_headers)}")
    if result.vulnerabilities:
        print(f"Vulnerabilities: {result.vulnerabilities}")
    
    # Example 2: Poor security
    print("\n--- Example 2: Poorly-Secured Site ---")
    headers_poor = {
        'Server': 'Apache/2.4.1'
    }
    
    result = analyze_security_headers(headers_poor, url="https://insecure-site.example")
    print(f"Rating: {result.rating.value}")
    print(f"Score: {result.overall_score}/75")
    print(f"Missing headers: {len(result.missing_headers)}")
    print("\nTop Recommendations:")
    for i, rec in enumerate(result.recommendations[:3], 1):
        print(f"  {i}. {rec}")
    
    print("\n")


def demo_waf_detection():
    """Demonstrate WAF detection"""
    print("=" * 60)
    print("WAF DETECTION DEMO")
    print("=" * 60)
    
    # Example 1: Cloudflare
    print("\n--- Example 1: Cloudflare WAF ---")
    headers_cf = {
        'cf-ray': '12345-ABC',
        'server': 'cloudflare',
        'cf-cache-status': 'HIT'
    }
    cookies_cf = {
        '__cfduid': 'd1234567890abcdef'
    }
    
    result = detect_waf(headers_cf, cookies_cf)
    if result.detected:
        print(f"WAF Detected: {result.waf_type.value}")
        print(f"Confidence: {result.confidence:.1%}")
        print(f"Indicators: {', '.join(result.indicators)}")
        print("\nRecommendations:")
        for rec in result.recommendations[:3]:
            print(f"  - {rec}")
    
    # Example 2: AWS WAF
    print("\n--- Example 2: AWS WAF ---")
    headers_aws = {
        'x-amzn-requestid': 'abc-123-def-456',
        'x-amz-cf-id': 'cloudfront-id-789'
    }
    
    result = detect_waf(headers_aws)
    if result.detected:
        print(f"WAF Detected: {result.waf_type.value}")
        print(f"Confidence: {result.confidence:.1%}")
    
    # Example 3: No WAF
    print("\n--- Example 3: No WAF ---")
    headers_none = {
        'server': 'nginx/1.18.0'
    }
    
    result = detect_waf(headers_none)
    print(f"WAF Detected: {result.detected}")
    
    print("\n")


def demo_honeypot_detection():
    """Demonstrate honeypot detection"""
    print("=" * 60)
    print("HONEYPOT DETECTION DEMO")
    print("=" * 60)
    
    html = """
    <html>
        <body>
            <nav>
                <a href="/about">About</a>
                <a href="/contact">Contact</a>
                <!-- Honeypot trap for bots -->
                <a href="/admin" style="display:none">Admin</a>
            </nav>
            
            <form action="/submit" method="post">
                <input type="text" name="name" placeholder="Your Name">
                <input type="email" name="email" placeholder="Your Email">
                
                <!-- Honeypot field -->
                <input type="text" name="website" style="position:absolute;left:-9999px">
                <input type="hidden" name="honeypot" value="">
                
                <button type="submit">Submit</button>
            </form>
            
            <a href="/spider-trap" style="opacity:0">.</a>
        </body>
    </html>
    """
    
    result = detect_honeypots(html, url="https://example.com")
    
    print(f"\nHoneypots Detected: {result.has_honeypots}")
    print(f"Count: {result.honeypot_count}")
    print(f"Risk Level: {result.risk_level.upper()}")
    
    print(f"\nDetected Honeypots:")
    for i, hp in enumerate(result.honeypots, 1):
        print(f"\n  {i}. {hp.tag_name.upper()} element")
        print(f"     Type: {hp.trap_type}")
        print(f"     Confidence: {hp.confidence:.1%}")
        print(f"     Reasons: {', '.join(hp.reasons)}")
        if hp.url:
            print(f"     URL: {hp.url}")
    
    print(f"\nRecommendations:")
    for rec in result.recommendations:
        print(f"  - {rec}")
    
    print("\n")


def demo_integrated_analysis():
    """Demonstrate integrated security analysis"""
    print("=" * 60)
    print("INTEGRATED SECURITY ANALYSIS DEMO")
    print("=" * 60)
    
    # Simulate a page with multiple security aspects
    url = "https://example.com/login"
    
    html = """
    <html>
        <head>
            <meta name="csrf-token" content="abc123">
        </head>
        <body>
            <form method="post">
                <input type="hidden" name="csrf_token" value="xyz789">
                <input type="text" name="username">
                <input type="password" name="password">
                <input type="hidden" name="trap" value="">
            </form>
            <a href="/admin-trap" style="display:none">Secret</a>
        </body>
    </html>
    """
    
    headers = {
        'cf-ray': '67890-DEF',
        'Strict-Transport-Security': 'max-age=31536000',
        'X-Frame-Options': 'SAMEORIGIN'
    }
    
    cookies = {'__cfduid': 'cookie123'}
    
    print(f"\nAnalyzing: {url}\n")
    
    # 1. CSRF Tokens
    csrf_extractor = CSRFTokenExtractor(html, url)
    csrf_tokens = csrf_extractor.extract_all_tokens()
    print(f"[CSRF] Found {len(csrf_tokens)} token(s)")
    
    # 2. Security Headers
    header_result = analyze_security_headers(headers, url)
    print(f"[HEADERS] Security Rating: {header_result.rating.value}")
    
    # 3. WAF Detection
    waf_result = detect_waf(headers, cookies)
    if waf_result.detected:
        print(f"[WAF] Detected: {waf_result.waf_type.value} ({waf_result.confidence:.0%})")
    
    # 4. Honeypots
    honeypot_result = detect_honeypots(html, url)
    print(f"[HONEYPOT] Risk: {honeypot_result.risk_level.upper()} ({honeypot_result.honeypot_count} detected)")
    
    print("\nSecurity Summary:")
    print(f"  - CSRF Protection: {'Yes' if csrf_tokens else 'No'}")
    print(f"  - Security Headers: {header_result.rating.value}")
    print(f"  - WAF Protection: {'Yes' if waf_result.detected else 'No'}")
    print(f"  - Honeypot Risk: {honeypot_result.risk_level.upper()}")
    
    print("\n")


def main():
    """Run all demos"""
    print("\n")
    print("=" * 60)
    print("CRAWLIT SECURITY FEATURES DEMONSTRATION")
    print("=" * 60)
    print("\n")
    
    demo_csrf_extraction()
    demo_csrf_handler()
    demo_security_headers()
    demo_waf_detection()
    demo_honeypot_detection()
    demo_integrated_analysis()
    
    print("=" * 60)
    print("DEMO COMPLETE")
    print("=" * 60)
    print("\nFor more information, see SECURITY_FEATURES.md")
    print("\n")


if __name__ == '__main__':
    main()




