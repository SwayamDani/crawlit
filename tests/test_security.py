"""Tests for crawlit.security modules."""

import pytest

from crawlit.security.csrf import (
    CSRFTokenExtractor, CSRFTokenHandler,
    extract_csrf_token, extract_all_csrf_tokens,
)
from crawlit.security.headers import (
    SecurityHeadersAnalyzer, SecurityRating,
    analyze_security_headers,
)
from crawlit.security.waf import WAFDetector, WAFType, detect_waf
from crawlit.security.honeypot import (
    HoneypotDetector, detect_honeypots,
)
from crawlit.security.captcha_detector import (
    CaptchaDetector, CaptchaType, detect_captcha,
)


# -----------------------------------------------------------------------
# CSRF
# -----------------------------------------------------------------------

class TestCSRFTokenExtractor:
    def test_extract_from_form(self):
        html = """<form action="/submit">
            <input type="hidden" name="csrf_token" value="abc123">
            <input type="text" name="data">
        </form>"""
        ext = CSRFTokenExtractor(html)
        tokens = ext.extract_all_tokens()
        assert "csrf_token" in tokens
        assert tokens["csrf_token"] == "abc123"

    def test_extract_from_meta_tag(self):
        html = '<html><head><meta name="csrf-token" content="meta_value"></head></html>'
        ext = CSRFTokenExtractor(html)
        tokens = ext.extract_all_tokens()
        assert "csrf-token" in tokens
        assert tokens["csrf-token"] == "meta_value"

    def test_extract_from_javascript(self):
        html = '<script>var csrfToken = "js_value";</script>'
        ext = CSRFTokenExtractor(html)
        tokens = ext.extract_all_tokens()
        assert len(tokens) >= 1

    def test_extract_from_data_attributes(self):
        html = '<div data-csrf-token="data_value">Content</div>'
        ext = CSRFTokenExtractor(html)
        tokens = ext.extract_all_tokens()
        assert "data-csrf-token" in tokens

    def test_get_token(self):
        html = '<form><input type="hidden" name="csrf_token" value="t1"></form>'
        ext = CSRFTokenExtractor(html)
        token = ext.get_token()
        assert token is not None

    def test_get_token_preferred(self):
        html = """<form>
            <input type="hidden" name="csrf_token" value="t1">
            <input type="hidden" name="_token" value="t2">
        </form>"""
        ext = CSRFTokenExtractor(html)
        ext.extract_all_tokens()
        token = ext.get_token("_token")
        assert token == "t2"

    def test_no_tokens(self):
        html = "<html><body><p>No tokens</p></body></html>"
        ext = CSRFTokenExtractor(html)
        tokens = ext.extract_all_tokens()
        assert len(tokens) == 0

    def test_convenience_extract_csrf_token(self):
        html = '<form><input type="hidden" name="csrf_token" value="abc"></form>'
        token = extract_csrf_token(html)
        assert token == "abc"

    def test_convenience_extract_all(self):
        html = '<form><input type="hidden" name="csrf_token" value="abc"></form>'
        tokens = extract_all_csrf_tokens(html)
        assert isinstance(tokens, dict)


class TestCSRFTokenHandler:
    def test_extract_and_store(self):
        handler = CSRFTokenHandler()
        html = '<form><input type="hidden" name="csrf_token" value="stored"></form>'
        tokens = handler.extract_and_store("https://example.com", html)
        assert "csrf_token" in tokens

    def test_get_tokens_for_url(self):
        handler = CSRFTokenHandler()
        html = '<form><input type="hidden" name="csrf_token" value="v1"></form>'
        handler.extract_and_store("https://a.com", html)
        tokens = handler.get_tokens_for_url("https://a.com")
        assert "csrf_token" in tokens

    def test_global_token(self):
        handler = CSRFTokenHandler()
        handler.set_global_token("api_token", "global_val")
        tokens = handler.get_tokens_for_url("https://any.com")
        assert tokens["api_token"] == "global_val"

    def test_clear_specific_url(self):
        handler = CSRFTokenHandler()
        html = '<form><input type="hidden" name="csrf_token" value="v1"></form>'
        handler.extract_and_store("https://a.com", html)
        handler.clear_tokens("https://a.com")
        tokens = handler.get_tokens_for_url("https://a.com")
        assert "csrf_token" not in tokens

    def test_clear_all(self):
        handler = CSRFTokenHandler()
        handler.set_global_token("g", "v")
        handler.clear_tokens()
        assert handler.get_statistics()["total_tokens"] == 0

    def test_statistics(self):
        handler = CSRFTokenHandler()
        html = '<form><input type="hidden" name="csrf_token" value="v1"></form>'
        handler.extract_and_store("https://a.com", html)
        handler.set_global_token("g", "v")
        stats = handler.get_statistics()
        assert stats["urls_with_tokens"] == 1
        assert stats["global_tokens"] == 1


# -----------------------------------------------------------------------
# Security Headers
# -----------------------------------------------------------------------

class TestSecurityHeadersAnalyzer:
    SECURE_HEADERS = {
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
        "Content-Security-Policy": "default-src 'self'; script-src 'self'",
        "X-Frame-Options": "DENY",
        "X-Content-Type-Options": "nosniff",
        "X-XSS-Protection": "1; mode=block",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": "geolocation=(), camera=()",
        "Cross-Origin-Opener-Policy": "same-origin",
        "Cross-Origin-Resource-Policy": "same-origin",
        "Cross-Origin-Embedder-Policy": "require-corp",
    }

    def test_all_headers_present(self):
        analyzer = SecurityHeadersAnalyzer()
        result = analyzer.analyze(self.SECURE_HEADERS, "https://example.com")
        assert result.rating in (SecurityRating.EXCELLENT, SecurityRating.GOOD)
        assert result.missing_headers == []

    def test_no_headers(self):
        analyzer = SecurityHeadersAnalyzer()
        result = analyzer.analyze({}, "https://example.com")
        assert result.rating == SecurityRating.CRITICAL
        assert len(result.missing_headers) == 10

    def test_hsts_analysis(self):
        analyzer = SecurityHeadersAnalyzer()
        result = analyzer.analyze(
            {"Strict-Transport-Security": "max-age=100"},
            "https://example.com",
        )
        hsts = result.headers_analyzed["Strict-Transport-Security"]
        assert hsts.present is True
        assert len(hsts.issues) > 0 or len(hsts.recommendations) > 0

    def test_csp_unsafe_inline(self):
        analyzer = SecurityHeadersAnalyzer()
        result = analyzer.analyze(
            {"Content-Security-Policy": "default-src 'self' 'unsafe-inline'"},
        )
        csp = result.headers_analyzed["Content-Security-Policy"]
        assert any("unsafe-inline" in i for i in csp.issues)

    def test_frame_options_deny(self):
        analyzer = SecurityHeadersAnalyzer()
        result = analyzer.analyze({"X-Frame-Options": "DENY"})
        fo = result.headers_analyzed["X-Frame-Options"]
        assert fo.score > 0

    def test_content_type_nosniff(self):
        analyzer = SecurityHeadersAnalyzer()
        result = analyzer.analyze({"X-Content-Type-Options": "nosniff"})
        ct = result.headers_analyzed["X-Content-Type-Options"]
        assert ct.score > 0

    def test_rating_levels(self):
        analyzer = SecurityHeadersAnalyzer()
        assert analyzer._calculate_rating(100) == SecurityRating.EXCELLENT
        assert analyzer._calculate_rating(90) == SecurityRating.GOOD
        assert analyzer._calculate_rating(75) == SecurityRating.ACCEPTABLE
        assert analyzer._calculate_rating(55) == SecurityRating.POOR
        assert analyzer._calculate_rating(35) == SecurityRating.VERY_POOR
        assert analyzer._calculate_rating(10) == SecurityRating.CRITICAL

    def test_convenience_function(self):
        result = analyze_security_headers(self.SECURE_HEADERS, "https://example.com")
        assert result.url == "https://example.com"
        assert result.overall_score > 0


# -----------------------------------------------------------------------
# WAF Detection
# -----------------------------------------------------------------------

class TestWAFDetector:
    def test_no_waf(self):
        detector = WAFDetector()
        result = detector.detect(
            headers={"Content-Type": "text/html", "Server": "Apache"},
        )
        assert result.waf_type == WAFType.NONE or result.detected is False

    def test_cloudflare_detection(self):
        detector = WAFDetector()
        result = detector.detect(
            headers={"cf-ray": "abc123", "server": "cloudflare"},
        )
        if result.detected:
            assert result.waf_type == WAFType.CLOUDFLARE
            assert result.confidence > 0

    def test_convenience_function(self):
        result = detect_waf(headers={"Content-Type": "text/html"})
        assert isinstance(result.detected, bool)

    def test_waf_type_enum(self):
        assert WAFType.CLOUDFLARE.value == "Cloudflare"
        assert WAFType.NONE.value == "No WAF Detected"

    def test_get_supported_wafs(self):
        detector = WAFDetector()
        wafs = detector.get_all_supported_wafs()
        assert isinstance(wafs, list)


# -----------------------------------------------------------------------
# Honeypot Detection
# -----------------------------------------------------------------------

class TestHoneypotDetector:
    def test_no_honeypots(self):
        html = "<html><body><p>Clean page</p></body></html>"
        result = detect_honeypots(html)
        assert result.has_honeypots is False
        assert result.honeypot_count == 0

    def test_hidden_link_detection(self):
        html = """<html><body>
            <a href="/trap" id="honeypot-link" class="bot-trap" style="display:none">Trap</a>
        </body></html>"""
        result = detect_honeypots(html)
        assert result.has_honeypots is True

    def test_invisible_element(self):
        html = """<html><body>
            <a href="/hidden" style="display:none" class="honeypot">Hidden</a>
        </body></html>"""
        detector = HoneypotDetector(html)
        result = detector.detect_all()
        assert result.has_honeypots is True

    def test_suspicious_form_field(self):
        html = """<form action="/submit">
            <input type="hidden" name="honeypot" value="">
            <input type="text" name="email">
        </form>"""
        result = detect_honeypots(html)
        assert result.has_honeypots is True

    def test_zero_dimension_element(self):
        html = '<a href="/trap" style="width:0; height:0">Trap</a>'
        result = detect_honeypots(html)
        assert result.has_honeypots is True

    def test_risk_level(self):
        html = """<html><body>
            <a href="/t1" id="honeypot" class="bot-trap" style="display:none">T1</a>
            <a href="/t2" class="honeypot" style="display:none">T2</a>
            <input type="hidden" name="honeypot" value="">
        </body></html>"""
        result = detect_honeypots(html)
        assert result.risk_level in ("low", "medium", "high")

    def test_recommendations(self):
        html = '<a href="/trap" id="honeypot" class="bot-trap" style="display:none">T</a>'
        result = detect_honeypots(html)
        if result.has_honeypots:
            assert len(result.recommendations) > 0


# -----------------------------------------------------------------------
# CAPTCHA Detection
# -----------------------------------------------------------------------

class TestCaptchaDetector:
    def test_no_captcha(self):
        html = "<html><body><p>Clean page</p></body></html>"
        result = detect_captcha(html)
        assert result["detected"] is False

    def test_recaptcha_detection(self):
        html = """<html><body>
            <div class="g-recaptcha" data-sitekey="abc123"></div>
            <script src="https://www.google.com/recaptcha/api.js"></script>
        </body></html>"""
        result = detect_captcha(html)
        assert result["detected"] is True
        assert any("reCAPTCHA" in ct for ct in result["captcha_types"])

    def test_hcaptcha_detection(self):
        html = """<html><body>
            <div class="h-captcha" data-sitekey="xyz"></div>
            <script src="https://hcaptcha.com/1/api.js"></script>
        </body></html>"""
        result = detect_captcha(html)
        assert result["detected"] is True
        assert "hCaptcha" in result["captcha_types"]

    def test_cloudflare_turnstile(self):
        html = '<div class="cf-turnstile" data-sitekey="key123"></div>'
        result = detect_captcha(html)
        assert result["detected"] is True

    def test_generic_captcha_keywords(self):
        html = "<html><body><p>Please verify you're human</p></body></html>"
        result = detect_captcha(html)
        assert result["detected"] is True

    def test_captcha_image_detection(self):
        html = '<img src="/captcha/image.png" alt="captcha" id="captcha-img">'
        result = detect_captcha(html)
        assert result["detected"] is True

    def test_callback(self):
        from unittest.mock import MagicMock
        callback = MagicMock()
        detector = CaptchaDetector(on_captcha_detected=callback)
        html = '<div class="g-recaptcha" data-sitekey="abc"></div>'
        detector.detect(html)
        assert callback.called

    def test_detection_count(self):
        detector = CaptchaDetector()
        html = '<div class="g-recaptcha" data-sitekey="abc"></div>'
        detector.detect(html)
        detector.detect(html)
        assert detector.get_detection_count() == 2

    def test_reset_count(self):
        detector = CaptchaDetector()
        detector.detect('<div class="g-recaptcha" data-sitekey="abc"></div>')
        detector.reset_count()
        assert detector.get_detection_count() == 0

    def test_empty_html(self):
        result = detect_captcha("")
        assert result["detected"] is False

    def test_captcha_type_enum(self):
        assert CaptchaType.RECAPTCHA.value == "reCAPTCHA"
        assert CaptchaType.HCAPTCHA.value == "hCaptcha"
        assert CaptchaType.CLOUDFLARE_TURNSTILE.value == "Cloudflare Turnstile"
