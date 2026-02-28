# Security Analysis with Crawlit

Crawlit provides comprehensive security analysis capabilities for web crawling, helping you assess website security posture, detect protection mechanisms, and handle security tokens appropriately. This guide covers all security-related features available in the crawlit framework.

## Table of Contents

1. [Security Analysis Overview](#security-analysis-overview)
2. [HTTP Security Headers Analysis](#http-security-headers-analysis)
3. [WAF (Web Application Firewall) Detection](#waf-detection)
4. [CAPTCHA Detection](#captcha-detection)
5. [Honeypot Detection](#honeypot-detection)
6. [CSRF Token Handling](#csrf-token-handling)
7. [Security Reporting](#security-reporting)
8. [Integration with Crawling Workflows](#integration-with-crawling-workflows)
9. [Security Best Practices](#security-best-practices)
10. [Examples and Use Cases](#examples-and-use-cases)

## Security Analysis Overview

Crawlit's security module (`crawlit.security`) provides five main security analysis components:

- **Headers Analysis**: Evaluates HTTP security headers and provides security ratings
- **WAF Detection**: Identifies Web Application Firewalls and provides evasion recommendations
- **CAPTCHA Detection**: Detects various CAPTCHA challenges to avoid wasting resources
- **Honeypot Detection**: Identifies honeypot traps designed to catch scrapers
- **CSRF Handling**: Automatically extracts and manages CSRF tokens

### Basic Usage

```python
from crawlit.security import (
    SecurityHeadersAnalyzer,
    WAFDetector, 
    CaptchaDetector,
    HoneypotDetector,
    CSRFTokenHandler
)

# Initialize security analyzers
headers_analyzer = SecurityHeadersAnalyzer()
waf_detector = WAFDetector()
captcha_detector = CaptchaDetector()
honeypot_detector = HoneypotDetector(html_content, url)
csrf_handler = CSRFTokenHandler()
```

## HTTP Security Headers Analysis

The `SecurityHeadersAnalyzer` evaluates HTTP response headers for security best practices and provides comprehensive security ratings.

### Analyzed Headers

The analyzer checks for the following security headers:

| Header | Score Weight | Purpose |
|--------|--------------|---------|
| `Strict-Transport-Security` | 10 | Enforces HTTPS connections |
| `Content-Security-Policy` | 15 | Prevents XSS and injection attacks |
| `X-Frame-Options` | 8 | Prevents clickjacking attacks |
| `X-Content-Type-Options` | 5 | Prevents MIME-sniffing |
| `X-XSS-Protection` | 3 | Legacy XSS protection |
| `Referrer-Policy` | 5 | Controls referrer information |
| `Permissions-Policy` | 8 | Controls browser features and APIs |
| `Cross-Origin-Opener-Policy` | 5 | Isolates browsing context |
| `Cross-Origin-Resource-Policy` | 5 | Controls cross-origin resource loading |
| `Cross-Origin-Embedder-Policy` | 5 | Prevents loading cross-origin resources |

### Security Ratings

- **A+** (Excellent): 90-100% of maximum score
- **A** (Good): 80-89% of maximum score  
- **B** (Acceptable): 70-79% of maximum score
- **C** (Poor): 60-69% of maximum score
- **D** (Very Poor): 40-59% of maximum score
- **F** (Critical): Below 40% of maximum score

### Usage Example

```python
from crawlit.security import SecurityHeadersAnalyzer

analyzer = SecurityHeadersAnalyzer()

# Analyze headers from HTTP response
headers = {
    'Strict-Transport-Security': 'max-age=31536000; includeSubDomains; preload',
    'Content-Security-Policy': "default-src 'self'; script-src 'self'",
    'X-Frame-Options': 'DENY',
    'X-Content-Type-Options': 'nosniff'
}

result = analyzer.analyze(headers, "https://example.com")

print(f"Security Rating: {result.rating.value}")
print(f"Score: {result.overall_score}/{analyzer.max_score}")
print(f"Missing Headers: {result.missing_headers}")
print(f"Vulnerabilities: {result.vulnerabilities}")
print(f"Recommendations: {result.recommendations}")
```

### Header-Specific Analysis

#### HSTS (Strict-Transport-Security)
- Checks for `max-age` directive and duration
- Validates presence of `includeSubDomains`
- Recommends `preload` directive
- Flags short max-age values

#### Content Security Policy (CSP)
- Detects unsafe directives (`unsafe-inline`, `unsafe-eval`)
- Identifies overly permissive wildcards
- Validates presence of important directives
- Provides specific CSP improvement recommendations

#### X-Frame-Options
- Validates acceptable values (`DENY`, `SAMEORIGIN`, `ALLOW-FROM`)
- Flags missing or invalid configurations

## WAF Detection

The `WAFDetector` identifies Web Application Firewalls by analyzing HTTP responses, headers, cookies, and response body patterns.

### Supported WAF Types

- **Cloudflare**: Most common CDN/WAF
- **AWS WAF**: Amazon's Web Application Firewall
- **Akamai**: Enterprise CDN/security platform
- **Incapsula/Imperva**: Cloud security platform
- **ModSecurity**: Open-source WAF
- **F5 BIG-IP ASM**: Enterprise application security
- **Barracuda**: Web application firewall
- **FortiWeb**: Fortinet web application firewall
- **Citrix NetScaler**: Application delivery controller
- **And many more...**

### Detection Methods

The detector uses multiple techniques:

1. **HTTP Headers**: Analyzes response headers for WAF signatures
2. **Cookies**: Identifies WAF-specific cookies
3. **Server Headers**: Checks server identification strings
4. **Response Body**: Scans for WAF-specific error pages and patterns

### Usage Example

```python
from crawlit.security import WAFDetector, detect_waf

detector = WAFDetector()

# Detect WAF from response
result = detector.detect(
    headers={'cf-ray': '6d2a1b2c3d4e5f6g-ORD', 'server': 'cloudflare'},
    cookies=['__cfduid=abc123'],
    response_body="<html>Cloudflare protection...</html>",
    url="https://example.com"
)

print(f"WAF Detected: {result.detected}")
print(f"WAF Type: {result.waf_type.value}")
print(f"Confidence: {result.confidence:.2f}")
print(f"Indicators: {result.indicators}")
print(f"Recommendations: {result.recommendations}")

# Convenience function
waf_result = detect_waf(headers, cookies, response_body)
```

### WAF-Specific Recommendations

Each detected WAF includes specific recommendations for handling:

**Cloudflare:**
- Respect rate limits to avoid challenges
- Use real browser User-Agent headers
- Maintain consistent request patterns
- Handle JavaScript challenges appropriately

**AWS WAF:**
- Distribute requests across different IP addresses
- Use authentic browser headers
- Avoid triggering rate limit rules
- Respect robots.txt directives

## CAPTCHA Detection

The `CaptchaDetector` identifies various CAPTCHA challenges in web pages to help avoid wasting crawler resources on unsolvable challenges.

### Supported CAPTCHA Types

- **reCAPTCHA v2/v3**: Google's CAPTCHA system
- **hCaptcha**: Privacy-focused alternative to reCAPTCHA
- **Cloudflare Turnstile**: Cloudflare's CAPTCHA replacement
- **FunCaptcha**: Arkose Labs interactive challenges
- **GeeTest**: Popular CAPTCHA in Asia
- **Simple Image CAPTCHAs**: Basic image-based challenges
- **Custom CAPTCHAs**: Site-specific implementations

### Detection Patterns

The detector searches for:
- CAPTCHA provider scripts and APIs
- CAPTCHA-specific HTML elements and attributes
- JavaScript initialization code
- Generic CAPTCHA keywords and phrases

### Usage Example

```python
from crawlit.security import CaptchaDetector, CaptchaType

html_content = """
<html>
<script src="https://www.google.com/recaptcha/api.js"></script>
<div class="g-recaptcha" data-sitekey="6LdRcP4oAAAAAOcHcMYtZ..."></div>
</html>
"""

detector = CaptchaDetector()
result = detector.detect(html_content, "https://example.com")

print(f"CAPTCHA Detected: {result['detected']}")
print(f"CAPTCHA Types: {[t.value for t in result['types']]}")
print(f"Confidence: {result['confidence']:.2f}")
print(f"Elements: {result['elements']}")

# Handle CAPTCHA detection in crawler
def on_captcha_detected(detection_result):
    print(f"CAPTCHA found at {detection_result['url']}")
    # Skip or handle appropriately

detector_with_callback = CaptchaDetector(on_captcha_detected)
```

### CAPTCHA Handling Strategies

When CAPTCHAs are detected:

1. **Skip the Page**: Mark as unable to process
2. **Retry Later**: Attempt again with different parameters
3. **Use Alternative Routes**: Find other ways to access content
4. **Manual Intervention**: Queue for human review
5. **CAPTCHA Solving Services**: Integrate with solving APIs (if legally permitted)

## Honeypot Detection

The `HoneypotDetector` identifies honeypot traps designed to catch automated scrapers and bots.

### Types of Honeypots Detected

1. **Invisible Elements**: CSS-hidden form fields and links
2. **Off-screen Elements**: Elements positioned outside visible area
3. **Zero-dimension Elements**: Elements with zero width/height
4. **Transparent Elements**: Fully transparent or nearly invisible
5. **Hidden Form Fields**: Suspicious hidden inputs
6. **Mouse Traps**: Links designed to catch non-human interaction

### Detection Methods

```python
from crawlit.security import HoneypotDetector, detect_honeypots

html_content = """
<form>
    <input type="hidden" name="honeypot" value="" style="display:none">
    <input type="text" name="email" placeholder="Your email">
    <a href="/trap-link" style="position:absolute;left:-9999px">Hidden Link</a>
</form>
"""

detector = HoneypotDetector(html_content, "https://example.com")
result = detector.detect_all()

print(f"Honeypots Found: {result.has_honeypots}")
print(f"Count: {result.honeypot_count}")
print(f"Risk Level: {result.risk_level}")

for honeypot in result.honeypots:
    print(f"Type: {honeypot.trap_type}, Confidence: {honeypot.confidence}")
    print(f"Element: {honeypot.tag_name}, Reasons: {honeypot.reasons}")
```

### Honeypot Avoidance

When honeypots are detected:

1. **Never Interact**: Do not click links or fill forms identified as honeypots
2. **Selective Processing**: Only interact with legitimate elements
3. **CSS Analysis**: Parse CSS to identify truly hidden elements
4. **Behavioral Mimicking**: Follow human-like interaction patterns

### Risk Assessment

- **High Risk**: Multiple honeypots with high confidence scores
- **Medium Risk**: Few honeypots or lower confidence
- **Low Risk**: Questionable detections or edge cases

## CSRF Token Handling

The CSRF (Cross-Site Request Forgery) token system automatically extracts and manages CSRF tokens from web pages.

### Token Extraction Sources

1. **Hidden Form Fields**: `<input type="hidden" name="csrf_token">`
2. **Meta Tags**: `<meta name="csrf-token" content="...">`
3. **JavaScript Variables**: `var csrfToken = "..."`
4. **Data Attributes**: `data-csrf-token="..."`

### Common Token Names

The extractor recognizes various naming conventions:
- `csrf_token`, `csrftoken`, `_csrf`, `csrf`
- `authenticity_token`, `_token`, `token`
- `xsrf_token`, `xsrftoken`, `_xsrf`
- `__RequestVerificationToken` (ASP.NET)
- `form_build_id` (Drupal)
- `_wpnonce` (WordPress)

### Usage Example

```python
from crawlit.security import CSRFTokenExtractor, CSRFTokenHandler

# Extract tokens from HTML
html = """
<form method="post">
    <meta name="csrf-token" content="abc123xyz">
    <input type="hidden" name="authenticity_token" value="def456uvw">
    <input type="text" name="username">
</form>
"""

extractor = CSRFTokenExtractor(html, "https://example.com")
tokens = extractor.extract_all_tokens()

print(f"Found tokens: {tokens}")

# Use token handler for automatic management
handler = CSRFTokenHandler()

# Extract and store tokens
tokens = handler.extract_and_store("https://example.com", html)

# Add tokens to subsequent requests
data = {"username": "user", "password": "pass"}
headers = {"Content-Type": "application/x-www-form-urlencoded"}

data_with_tokens, updated_headers = handler.add_tokens_to_request(
    "https://example.com", data, headers
)

print(f"Updated data: {data_with_tokens}")
```

### Global Token Management

```python
# Set global tokens that apply to all requests
handler.set_global_token("api_key", "secret123")

# Get global tokens
global_tokens = handler.get_global_tokens()

# Clear all tokens for a URL
handler.clear_tokens_for_url("https://example.com")
```

## Security Reporting

### Consolidated Security Report

Generate comprehensive security reports combining all analysis results:

```python
from crawlit.security import (
    SecurityHeadersAnalyzer, WAFDetector, 
    CaptchaDetector, HoneypotDetector
)

def generate_security_report(response, html_content, url):
    """Generate comprehensive security report"""
    
    # Initialize analyzers
    headers_analyzer = SecurityHeadersAnalyzer()
    waf_detector = WAFDetector()
    captcha_detector = CaptchaDetector()
    honeypot_detector = HoneypotDetector(html_content, url)
    
    # Perform analysis
    headers_result = headers_analyzer.analyze(response.headers, url)
    waf_result = waf_detector.detect(
        response.headers, response.cookies, html_content, url
    )
    captcha_result = captcha_detector.detect(html_content, url)
    honeypot_result = honeypot_detector.detect_all()
    
    # Compile report
    security_report = {
        "url": url,
        "timestamp": headers_result.timestamp,
        "security_headers": {
            "rating": headers_result.rating.value,
            "score": f"{headers_result.overall_score}/{headers_analyzer.max_score}",
            "missing_headers": headers_result.missing_headers,
            "vulnerabilities": headers_result.vulnerabilities,
            "recommendations": headers_result.recommendations
        },
        "waf_detection": {
            "detected": waf_result.detected,
            "type": waf_result.waf_type.value,
            "confidence": waf_result.confidence,
            "recommendations": waf_result.recommendations
        },
        "captcha_detection": {
            "detected": captcha_result["detected"],
            "types": [t.value for t in captcha_result["types"]],
            "confidence": captcha_result["confidence"]
        },
        "honeypot_detection": {
            "detected": honeypot_result.has_honeypots,
            "count": honeypot_result.honeypot_count,
            "risk_level": honeypot_result.risk_level,
            "recommendations": honeypot_result.recommendations
        }
    }
    
    return security_report

# Usage
report = generate_security_report(response, html_content, url)
print(json.dumps(report, indent=2))
```

### Export Formats

Security reports can be exported in various formats:

```python
import json
import csv
from datetime import datetime

def export_security_report(report, format="json"):
    """Export security report in specified format"""
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if format == "json":
        filename = f"security_report_{timestamp}.json"
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2)
    
    elif format == "csv":
        filename = f"security_report_{timestamp}.csv"
        with open(filename, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["URL", "Security Rating", "WAF Detected", "CAPTCHA Detected", "Honeypots"])
            writer.writerow([
                report["url"],
                report["security_headers"]["rating"],
                report["waf_detection"]["detected"],
                report["captcha_detection"]["detected"],
                report["honeypot_detection"]["detected"]
            ])
    
    return filename
```

## Integration with Crawling Workflows

### Custom Security Middleware

Create middleware to automatically perform security analysis during crawling:

```python
class SecurityAnalysisMiddleware:
    """Middleware for automatic security analysis"""
    
    def __init__(self):
        self.headers_analyzer = SecurityHeadersAnalyzer()
        self.waf_detector = WAFDetector()
        self.captcha_detector = CaptchaDetector()
        self.csrf_handler = CSRFTokenHandler()
    
    def process_request(self, request):
        """Process outgoing request"""
        # Add CSRF tokens if available
        if hasattr(request, 'data'):
            request.data, request.headers = self.csrf_handler.add_tokens_to_request(
                request.url, request.data, request.headers
            )
        return request
    
    def process_response(self, request, response):
        """Process incoming response"""
        
        # Analyze security headers
        security_analysis = self.headers_analyzer.analyze(
            response.headers, request.url
        )
        
        # Detect WAF
        waf_result = self.waf_detector.detect(
            response.headers, response.cookies, 
            response.content, request.url
        )
        
        # Check for CAPTCHA
        captcha_result = self.captcha_detector.detect(
            response.content, request.url
        )
        
        # Extract CSRF tokens for future requests
        if response.content:
            self.csrf_handler.extract_and_store(
                request.url, response.content
            )
        
        # Add security metadata to response
        response.security_analysis = {
            "headers": security_analysis,
            "waf": waf_result,
            "captcha": captcha_result
        }
        
        return response
```

### Conditional Processing

Make crawling decisions based on security analysis:

```python
def should_continue_crawling(response):
    """Determine if crawling should continue based on security analysis"""
    
    if hasattr(response, 'security_analysis'):
        security = response.security_analysis
        
        # Skip if CAPTCHA detected
        if security["captcha"]["detected"]:
            print(f"CAPTCHA detected at {response.url}, skipping...")
            return False
        
        # Be cautious with aggressive WAF
        if security["waf"]["detected"] and security["waf"]["confidence"] > 0.8:
            print(f"High-confidence WAF detected: {security['waf']['type']}")
            # Implement backoff or different strategy
            return False
        
        # Check for honeypots
        if hasattr(response, 'honeypot_analysis'):
            if response.honeypot_analysis.risk_level == "high":
                print("High honeypot risk detected, proceeding carefully...")
                # Use selective element interaction
    
    return True
```

## Security Best Practices

### 1. Respectful Crawling

- **Rate Limiting**: Implement appropriate delays between requests
- **robots.txt Compliance**: Respect robots.txt directives
- **User-Agent Transparency**: Use descriptive, honest User-Agent strings
- **Resource Conservation**: Avoid unnecessary resource consumption

### 2. WAF and CAPTCHA Handling

- **Detection Response**: Adapt behavior when security measures are detected
- **Backoff Strategies**: Implement exponential backoff for rate-limited requests
- **Header Rotation**: Use realistic browser headers when appropriate
- **Session Management**: Maintain consistent session behavior

### 3. Token Management

- **Automatic Extraction**: Always extract and use CSRF tokens when present
- **Token Freshness**: Refresh tokens periodically for long-running crawls
- **Session Persistence**: Maintain sessions properly for multi-step processes
- **Error Handling**: Handle token validation errors gracefully

### 4. Honeypot Avoidance

- **Element Analysis**: Analyze CSS and visibility before interaction
- **Selective Processing**: Only interact with legitimate, visible elements
- **Pattern Recognition**: Learn site-specific honeypot patterns
- **Human Behavior**: Mimic natural user interaction patterns

### 5. Security Header Compliance

- **HSTS Respect**: Always use HTTPS when HSTS headers are present
- **CSP Awareness**: Be aware of Content Security Policy restrictions
- **Cookie Security**: Handle secure and SameSite cookie attributes properly
- **Header Analysis**: Use security header analysis to understand site security posture

## Examples and Use Cases

### Example 1: E-commerce Security Assessment

```python
import requests
from crawlit.security import SecurityHeadersAnalyzer, WAFDetector

def assess_ecommerce_security(urls):
    """Assess security of e-commerce sites"""
    
    analyzer = SecurityHeadersAnalyzer()
    waf_detector = WAFDetector()
    results = {}
    
    for url in urls:
        try:
            response = requests.get(url, timeout=10)
            
            # Analyze security headers
            headers_result = analyzer.analyze(response.headers, url)
            
            # Detect WAF
            waf_result = waf_detector.detect(
                response.headers, 
                [cookie.name for cookie in response.cookies],
                response.text, url
            )
            
            results[url] = {
                "security_rating": headers_result.rating.value,
                "score": headers_result.overall_score,
                "waf_protected": waf_result.detected,
                "waf_type": waf_result.waf_type.value if waf_result.detected else None,
                "critical_issues": [
                    issue for issue in headers_result.vulnerabilities 
                    if "XSS" in issue or "injection" in issue
                ]
            }
            
        except Exception as e:
            results[url] = {"error": str(e)}
    
    return results

# Usage
ecommerce_sites = [
    "https://shop.example.com",
    "https://store.example.org"
]

security_assessment = assess_ecommerce_security(ecommerce_sites)
for site, assessment in security_assessment.items():
    print(f"\n{site}:")
    print(f"Security Rating: {assessment.get('security_rating', 'Error')}")
    if assessment.get('waf_protected'):
        print(f"WAF Protection: {assessment['waf_type']}")
```

### Example 2: Form Interaction with CSRF Protection

```python
from crawlit.security import CSRFTokenHandler, HoneypotDetector
import requests

def safe_form_submission(form_url, form_data):
    """Safely submit forms with CSRF protection and honeypot avoidance"""
    
    csrf_handler = CSRFTokenHandler()
    
    # Get the form page first
    response = requests.get(form_url)
    
    # Check for honeypots
    honeypot_detector = HoneypotDetector(response.text, form_url)
    honeypot_result = honeypot_detector.detect_all()
    
    if honeypot_result.has_honeypots and honeypot_result.risk_level == "high":
        print("High honeypot risk detected, aborting form submission")
        return None
    
    # Extract CSRF tokens
    tokens = csrf_handler.extract_and_store(form_url, response.text)
    print(f"Found CSRF tokens: {list(tokens.keys())}")
    
    # Add tokens to form data
    enhanced_data, headers = csrf_handler.add_tokens_to_request(
        form_url, form_data, {"Content-Type": "application/x-www-form-urlencoded"}
    )
    
    # Submit form
    submit_response = requests.post(form_url, data=enhanced_data, headers=headers)
    
    return submit_response

# Usage
form_data = {
    "username": "testuser",
    "email": "test@example.com",
    "message": "Hello world"
}

result = safe_form_submission("https://example.com/contact", form_data)
```

### Example 3: Comprehensive Security Scanner

```python
import asyncio
import aiohttp
from crawlit.security import *

class SecurityScanner:
    """Comprehensive security scanner for websites"""
    
    def __init__(self):
        self.headers_analyzer = SecurityHeadersAnalyzer()
        self.waf_detector = WAFDetector()
        self.captcha_detector = CaptchaDetector()
        
    async def scan_url(self, session, url):
        """Scan a single URL for security issues"""
        try:
            async with session.get(url) as response:
                html = await response.text()
                
                # Perform all security checks
                security_headers = self.headers_analyzer.analyze(
                    dict(response.headers), url
                )
                
                waf_result = self.waf_detector.detect(
                    dict(response.headers),
                    [cookie.name for cookie in response.cookies],
                    html, url
                )
                
                captcha_result = self.captcha_detector.detect(html, url)
                
                honeypot_detector = HoneypotDetector(html, url)
                honeypot_result = honeypot_detector.detect_all()
                
                return {
                    "url": url,
                    "status": response.status,
                    "security_rating": security_headers.rating.value,
                    "security_score": security_headers.overall_score,
                    "waf_detected": waf_result.detected,
                    "waf_type": waf_result.waf_type.value,
                    "captcha_detected": captcha_result["detected"],
                    "honeypots_detected": honeypot_result.has_honeypots,
                    "honeypot_risk": honeypot_result.risk_level,
                    "vulnerabilities": security_headers.vulnerabilities,
                    "recommendations": security_headers.recommendations[:5]  # Top 5
                }
                
        except Exception as e:
            return {"url": url, "error": str(e)}
    
    async def scan_multiple_urls(self, urls):
        """Scan multiple URLs concurrently"""
        async with aiohttp.ClientSession() as session:
            tasks = [self.scan_url(session, url) for url in urls]
            results = await asyncio.gather(*tasks)
            return results
    
    def generate_report(self, results):
        """Generate security report from scan results"""
        total_sites = len(results)
        high_security = sum(1 for r in results if r.get("security_rating") in ["A+", "A"])
        waf_protected = sum(1 for r in results if r.get("waf_detected"))
        captcha_protected = sum(1 for r in results if r.get("captcha_detected"))
        
        print(f"\n=== Security Scan Report ===")
        print(f"Total Sites Scanned: {total_sites}")
        print(f"High Security Rating (A+/A): {high_security} ({high_security/total_sites*100:.1f}%)")
        print(f"WAF Protected: {waf_protected} ({waf_protected/total_sites*100:.1f}%)")
        print(f"CAPTCHA Protected: {captcha_protected} ({captcha_protected/total_sites*100:.1f}%)")
        
        print(f"\n=== Individual Results ===")
        for result in results:
            if 'error' in result:
                print(f"{result['url']}: ERROR - {result['error']}")
            else:
                print(f"{result['url']}: {result['security_rating']} "
                      f"(WAF: {'Yes' if result['waf_detected'] else 'No'})")

# Usage
async def main():
    scanner = SecurityScanner()
    
    urls_to_scan = [
        "https://example.com",
        "https://google.com",
        "https://github.com",
        # Add more URLs as needed
    ]
    
    results = await scanner.scan_multiple_urls(urls_to_scan)
    scanner.generate_report(results)

# Run the scanner
# asyncio.run(main())
```

### Example 4: Security-Aware Web Crawler

```python
import time
from crawlit.security import *

class SecurityAwareCrawler:
    """A web crawler that adapts behavior based on security detection"""
    
    def __init__(self):
        self.waf_detector = WAFDetector()
        self.captcha_detector = CaptchaDetector()
        self.csrf_handler = CSRFTokenHandler()
        self.request_delays = {}  # URL domain -> delay mapping
        
    def get_adaptive_delay(self, url, waf_result):
        """Calculate appropriate delay based on WAF detection"""
        from urllib.parse import urlparse
        domain = urlparse(url).netloc
        
        base_delay = 1.0  # seconds
        
        if waf_result.detected:
            if waf_result.waf_type == WAFType.CLOUDFLARE:
                base_delay = 2.0
            elif waf_result.waf_type == WAFType.AKAMAI:
                base_delay = 3.0
            elif waf_result.confidence > 0.8:
                base_delay = 4.0
        
        # Increase delay if we've been rate limited
        current_delay = self.request_delays.get(domain, base_delay)
        return current_delay
    
    def crawl_page(self, url):
        """Crawl a single page with security awareness"""
        import requests
        
        try:
            # Get initial page
            response = requests.get(url, timeout=10)
            
            # Detect WAF
            waf_result = self.waf_detector.detect(
                response.headers, 
                [cookie.name for cookie in response.cookies],
                response.text, url
            )
            
            # Check for CAPTCHA
            captcha_result = self.captcha_detector.detect(response.text, url)
            
            if captcha_result["detected"]:
                print(f"CAPTCHA detected at {url}, skipping page")
                return {"url": url, "status": "captcha_blocked"}
            
            # Extract CSRF tokens for future use
            csrf_tokens = self.csrf_handler.extract_and_store(url, response.text)
            
            # Adapt crawling behavior based on WAF
            if waf_result.detected:
                delay = self.get_adaptive_delay(url, waf_result)
                print(f"WAF detected ({waf_result.waf_type.value}), using {delay}s delay")
                time.sleep(delay)
            
            return {
                "url": url,
                "status": "success",
                "content_length": len(response.text),
                "waf_detected": waf_result.detected,
                "waf_type": waf_result.waf_type.value if waf_result.detected else None,
                "csrf_tokens": len(csrf_tokens)
            }
            
        except requests.exceptions.Timeout:
            return {"url": url, "status": "timeout"}
        except requests.exceptions.RequestException as e:
            return {"url": url, "status": "error", "error": str(e)}

# Usage
crawler = SecurityAwareCrawler()
urls = ["https://example.com", "https://httpbin.org"]

for url in urls:
    result = crawler.crawl_page(url)
    print(f"Crawled {url}: {result['status']}")
    if result.get('waf_detected'):
        print(f"  WAF detected: {result['waf_type']}")
```

---

This comprehensive security documentation covers all aspects of crawlit's security analysis capabilities. The security module provides essential tools for responsible web crawling while respecting website security measures and avoiding common anti-bot traps.

For additional examples and advanced usage patterns, refer to the test files in the `tests/` directory and the security module source code in `crawlit/security/`.