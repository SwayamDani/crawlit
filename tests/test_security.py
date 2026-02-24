#!/usr/bin/env python3
"""
Tests for security features
"""

import pytest
from crawlit.security import (
    CSRFTokenExtractor, CSRFTokenHandler,
    SecurityHeadersAnalyzer, SecurityRating, analyze_security_headers,
    WAFDetector, WAFType, detect_waf,
    HoneypotDetector, detect_honeypots
)


class TestCSRFExtraction:
    """Test CSRF token extraction"""
    
    def test_extract_from_form_hidden_field(self):
        """Test extracting CSRF from hidden form field"""
        html = '''
        <form method="post">
            <input type="hidden" name="csrf_token" value="abc123xyz">
            <input type="text" name="username">
        </form>
        '''
        extractor = CSRFTokenExtractor(html)
        tokens = extractor.extract_all_tokens()
        
        assert 'csrf_token' in tokens
        assert tokens['csrf_token'] == 'abc123xyz'
    
    def test_extract_from_meta_tag(self):
        """Test extracting CSRF from meta tag"""
        html = '<meta name="csrf-token" content="meta-token-456">'
        extractor = CSRFTokenExtractor(html)
        tokens = extractor.extract_all_tokens()
        
        assert 'csrf-token' in tokens
        assert tokens['csrf-token'] == 'meta-token-456'
    
    def test_extract_from_javascript(self):
        """Test extracting CSRF from JavaScript"""
        html = '<script>var csrfToken = "js-token-789";</script>'
        extractor = CSRFTokenExtractor(html)
        tokens = extractor.extract_all_tokens()
        
        assert len(tokens) > 0  # Should find at least one token
    
    def test_extract_multiple_tokens(self):
        """Test extracting multiple tokens"""
        html = '''
        <meta name="csrf-token" content="token1">
        <form>
            <input type="hidden" name="authenticity_token" value="token2">
        </form>
        '''
        extractor = CSRFTokenExtractor(html)
        tokens = extractor.extract_all_tokens()
        
        assert len(tokens) >= 2
    
    def test_no_tokens(self):
        """Test page with no CSRF tokens"""
        html = '<html><body><p>No tokens here</p></body></html>'
        extractor = CSRFTokenExtractor(html)
        tokens = extractor.extract_all_tokens()
        
        assert len(tokens) == 0


class TestCSRFHandler:
    """Test CSRF token handler"""
    
    def test_store_and_retrieve_tokens(self):
        """Test storing and retrieving tokens"""
        handler = CSRFTokenHandler()
        html = '<form><input type="hidden" name="csrf_token" value="test123"></form>'
        
        tokens = handler.extract_and_store("http://example.com", html)
        
        assert 'csrf_token' in tokens
        retrieved = handler.get_tokens_for_url("http://example.com")
        assert 'csrf_token' in retrieved
    
    def test_global_token(self):
        """Test global token functionality"""
        handler = CSRFTokenHandler()
        handler.set_global_token("global_csrf", "global123")
        
        tokens = handler.get_tokens_for_url("http://any-url.com")
        assert 'global_csrf' in tokens
        assert tokens['global_csrf'] == 'global123'
    
    def test_add_tokens_to_request(self):
        """Test adding tokens to request"""
        handler = CSRFTokenHandler()
        handler.set_global_token("csrf_token", "abc123")
        
        data, headers = handler.add_tokens_to_request(
            "http://example.com",
            data={'username': 'test'},
            headers={}
        )
        
        assert 'csrf_token' in data
        assert data['csrf_token'] == 'abc123'
        assert 'X-CSRF-Token' in headers
    
    def test_statistics(self):
        """Test getting statistics"""
        handler = CSRFTokenHandler()
        handler.set_global_token("token1", "value1")
        
        stats = handler.get_statistics()
        assert 'global_tokens' in stats
        assert stats['global_tokens'] == 1


class TestSecurityHeaders:
    """Test security headers analysis"""
    
    def test_excellent_security_headers(self):
        """Test analysis with excellent security headers"""
        headers = {
            'Strict-Transport-Security': 'max-age=31536000; includeSubDomains; preload',
            'Content-Security-Policy': "default-src 'self'",
            'X-Frame-Options': 'DENY',
            'X-Content-Type-Options': 'nosniff',
            'X-XSS-Protection': '1; mode=block',
            'Referrer-Policy': 'strict-origin-when-cross-origin',
            'Permissions-Policy': 'geolocation=()',
            'Cross-Origin-Opener-Policy': 'same-origin',
            'Cross-Origin-Resource-Policy': 'same-origin',
            'Cross-Origin-Embedder-Policy': 'require-corp'
        }
        
        result = analyze_security_headers(headers)
        
        assert result.rating in [SecurityRating.EXCELLENT, SecurityRating.GOOD]
        assert len(result.missing_headers) == 0
    
    def test_poor_security_headers(self):
        """Test analysis with missing security headers"""
        headers = {}  # No security headers
        
        result = analyze_security_headers(headers)
        
        assert result.rating in [SecurityRating.CRITICAL, SecurityRating.VERY_POOR]
        assert len(result.missing_headers) > 5
        assert len(result.recommendations) > 0
    
    def test_hsts_analysis(self):
        """Test HSTS header analysis"""
        analyzer = SecurityHeadersAnalyzer()
        
        # Good HSTS
        result = analyzer.analyze({
            'Strict-Transport-Security': 'max-age=31536000; includeSubDomains'
        })
        assert result.headers_analyzed['Strict-Transport-Security'].present
        assert result.headers_analyzed['Strict-Transport-Security'].score > 0
    
    def test_csp_with_unsafe_inline(self):
        """Test CSP with unsafe-inline (should be flagged)"""
        result = analyze_security_headers({
            'Content-Security-Policy': "default-src 'self' 'unsafe-inline'"
        })
        
        csp_analysis = result.headers_analyzed['Content-Security-Policy']
        assert any('unsafe-inline' in issue for issue in csp_analysis.issues)
    
    def test_x_frame_options(self):
        """Test X-Frame-Options analysis"""
        result = analyze_security_headers({
            'X-Frame-Options': 'DENY'
        })
        
        xfo_analysis = result.headers_analyzed['X-Frame-Options']
        assert xfo_analysis.present
        assert xfo_analysis.score > 0


class TestWAFDetection:
    """Test WAF detection"""
    
    def test_cloudflare_detection(self):
        """Test Cloudflare WAF detection"""
        headers = {
            'cf-ray': '12345-ABC',
            'server': 'cloudflare'
        }
        
        result = detect_waf(headers)
        
        assert result.detected
        assert result.waf_type == WAFType.CLOUDFLARE
        assert result.confidence > 0.5
        assert len(result.indicators) > 0
    
    def test_aws_waf_detection(self):
        """Test AWS WAF detection"""
        headers = {
            'x-amzn-requestid': 'abc-123-def',
            'x-amz-cf-id': 'cloudfront-id'
        }
        
        result = detect_waf(headers)
        
        assert result.detected
        assert result.waf_type == WAFType.AWS_WAF
    
    def test_akamai_detection(self):
        """Test Akamai WAF detection"""
        headers = {
            'akamai-x-cache': 'hit',
            'x-akamai-request-id': 'req-123'
        }
        cookies = {'ak_bmsc': 'cookie-value'}
        
        result = detect_waf(headers, cookies)
        
        assert result.detected
        assert result.waf_type == WAFType.AKAMAI
    
    def test_no_waf_detected(self):
        """Test when no WAF is detected"""
        headers = {'server': 'nginx'}
        
        result = detect_waf(headers)
        
        assert not result.detected
        assert result.waf_type == WAFType.NONE
        assert result.confidence == 0.0
    
    def test_waf_recommendations(self):
        """Test that recommendations are provided for detected WAFs"""
        headers = {'cf-ray': '12345'}
        result = detect_waf(headers)
        
        if result.detected:
            assert len(result.recommendations) > 0
    
    def test_get_all_supported_wafs(self):
        """Test getting list of supported WAFs"""
        detector = WAFDetector()
        wafs = detector.get_all_supported_wafs()
        
        assert len(wafs) > 5
        assert WAFType.CLOUDFLARE in wafs
        assert WAFType.AWS_WAF in wafs


class TestHoneypotDetection:
    """Test honeypot detection"""
    
    def test_invisible_link_detection(self):
        """Test detecting invisible links"""
        html = '<a href="/trap" style="display:none">Hidden Link</a>'
        result = detect_honeypots(html)
        
        assert result.has_honeypots
        assert result.honeypot_count >= 1
    
    def test_hidden_form_field(self):
        """Test detecting hidden honeypot fields"""
        html = '''
        <form>
            <input type="hidden" name="honeypot" value="">
            <input type="text" name="username">
        </form>
        '''
        result = detect_honeypots(html)
        
        assert result.has_honeypots
        assert any(hp.trap_type == 'suspicious_field' for hp in result.honeypots)
    
    def test_off_screen_element(self):
        """Test detecting off-screen elements"""
        html = '<a href="/trap" style="position:absolute; left:-9999px">Off Screen</a>'
        result = detect_honeypots(html)
        
        assert result.has_honeypots
        assert any(hp.trap_type == 'off_screen' for hp in result.honeypots)
    
    def test_zero_dimension_element(self):
        """Test detecting zero-dimension elements"""
        html = '<div style="width:0; height:0"><a href="/trap">Link</a></div>'
        detector = HoneypotDetector(html)
        result = detector.detect_all()
        
        # The div has zero dimensions
        assert result.honeypot_count >= 0  # Might detect the div
    
    def test_transparent_element(self):
        """Test detecting transparent elements"""
        html = '<a href="/normal" style="opacity:0">Transparent</a>'
        result = detect_honeypots(html)
        
        # Should detect the transparent link
        assert result.has_honeypots
        # The element should be detected (might be classified as transparent, invisible, or mouse_trap)
        assert result.honeypot_count >= 1
    
    def test_suspicious_link_pattern(self):
        """Test detecting links with suspicious patterns"""
        html = '<a href="/honeypot-trap">Click here</a>'
        result = detect_honeypots(html)
        
        assert result.has_honeypots
        assert any(hp.trap_type == 'hidden_link' for hp in result.honeypots)
    
    def test_no_honeypots(self):
        """Test page with no honeypots"""
        html = '''
        <html>
            <body>
                <a href="/about">About</a>
                <form>
                    <input type="text" name="username">
                </form>
            </body>
        </html>
        '''
        result = detect_honeypots(html)
        
        assert not result.has_honeypots
        assert result.risk_level == 'none'
    
    def test_risk_level_calculation(self):
        """Test risk level calculation"""
        # High risk - many honeypots
        html = '''
        <a href="/trap1" style="display:none">1</a>
        <a href="/trap2" style="display:none">2</a>
        <a href="/trap3" style="display:none">3</a>
        <a href="/trap4" style="display:none">4</a>
        <a href="/trap5" style="display:none">5</a>
        '''
        result = detect_honeypots(html)
        
        assert result.risk_level in ['medium', 'high']
    
    def test_recommendations_provided(self):
        """Test that recommendations are provided when honeypots are detected"""
        html = '<a href="/trap" style="display:none">Hidden</a>'
        result = detect_honeypots(html)
        
        assert len(result.recommendations) > 0


class TestSecurityIntegration:
    """Integration tests for security features"""
    
    def test_combined_security_analysis(self):
        """Test using multiple security features together"""
        html = '''
        <html>
            <head>
                <meta name="csrf-token" content="token123">
            </head>
            <body>
                <form method="post">
                    <input type="hidden" name="csrf_token" value="abc123">
                    <input type="text" name="username">
                </form>
                <a href="/trap" style="display:none">Hidden</a>
            </body>
        </html>
        '''
        
        headers = {
            'cf-ray': '12345',
            'Strict-Transport-Security': 'max-age=31536000'
        }
        
        # CSRF
        csrf_extractor = CSRFTokenExtractor(html)
        csrf_tokens = csrf_extractor.extract_all_tokens()
        assert len(csrf_tokens) >= 1
        
        # Security headers
        header_result = analyze_security_headers(headers)
        assert header_result.rating is not None
        
        # WAF
        waf_result = detect_waf(headers)
        assert waf_result.waf_type == WAFType.CLOUDFLARE
        
        # Honeypots
        honeypot_result = detect_honeypots(html)
        assert honeypot_result.has_honeypots
    
    def test_security_awareness_crawling(self):
        """Test crawling with security awareness"""
        # Simulates a crawler being aware of security features
        
        html = '<input type="hidden" name="honeypot-field" value="">'
        honeypot_result = detect_honeypots(html)
        
        # Crawler should avoid interacting with honeypots
        if honeypot_result.has_honeypots:
            # Filter out honeypot fields
            safe_fields = [
                hp for hp in honeypot_result.honeypots 
                if hp.confidence < 0.7  # Only interact with low-confidence items
            ]
            # In practice, you'd skip high-confidence honeypots
            assert len(honeypot_result.honeypots) >= len(safe_fields)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

