#!/usr/bin/env python3
"""
Security features for crawlit

Provides CSRF token handling, security headers analysis, WAF detection,
and honeypot detection for secure web crawling.
"""

from .csrf import (
    CSRFTokenExtractor,
    CSRFTokenHandler
)

from .headers import (
    SecurityHeadersAnalyzer,
    SecurityRating,
    analyze_security_headers
)

from .waf import (
    WAFDetector,
    WAFType,
    detect_waf
)

from .honeypot import (
    HoneypotDetector,
    detect_honeypots
)

from .captcha_detector import (
    CaptchaDetector,
    CaptchaType,
    detect_captcha
)

__all__ = [
    # CSRF handling
    'CSRFTokenExtractor',
    'CSRFTokenHandler',
    
    # Security headers
    'SecurityHeadersAnalyzer',
    'SecurityRating',
    'analyze_security_headers',
    
    # WAF detection
    'WAFDetector',
    'WAFType',
    'detect_waf',
    
    # Honeypot detection
    'HoneypotDetector',
    'detect_honeypots',
    
    # CAPTCHA detection
    'CaptchaDetector',
    'CaptchaType',
    'detect_captcha',
]

