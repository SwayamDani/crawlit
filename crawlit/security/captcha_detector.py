#!/usr/bin/env python3
"""
captcha_detector.py - CAPTCHA detection to avoid wasting resources

Detects common CAPTCHA providers and challenges in web pages.
"""

import logging
import re
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class CaptchaType(Enum):
    """Types of CAPTCHA challenges detected."""
    RECAPTCHA = "reCAPTCHA"
    RECAPTCHA_V2 = "reCAPTCHA v2"
    RECAPTCHA_V3 = "reCAPTCHA v3"
    HCAPTCHA = "hCaptcha"
    CLOUDFLARE_TURNSTILE = "Cloudflare Turnstile"
    CLOUDFLARE_CHALLENGE = "Cloudflare Challenge"
    FUNCAPTCHA = "FunCaptcha"
    GEETEST = "GeeTest"
    SIMPLE_CAPTCHA = "Simple CAPTCHA"
    CUSTOM_CAPTCHA = "Custom CAPTCHA"
    UNKNOWN = "Unknown"


class CaptchaDetector:
    """
    Detector for CAPTCHA challenges in web pages.
    
    Identifies common CAPTCHA providers and challenge types.
    """
    
    # Patterns to detect CAPTCHA providers
    RECAPTCHA_PATTERNS = [
        r'google\.com/recaptcha',
        r'recaptcha',
        r'g-recaptcha',
        r'grecaptcha',
        r'data-sitekey'
    ]
    
    HCAPTCHA_PATTERNS = [
        r'hcaptcha\.com',
        r'h-captcha',
        r'hcaptcha',
        r'data-sitekey.*hcaptcha'
    ]
    
    CLOUDFLARE_PATTERNS = [
        r'challenges\.cloudflare\.com',
        r'cf-turnstile',
        r'cloudflare.*challenge',
        r'ray\s+id',
        r'cf-chl-'
    ]
    
    FUNCAPTCHA_PATTERNS = [
        r'arkoselabs\.com',
        r'funcaptcha',
        r'arkose',
        r'enforcement\.arkoselabs'
    ]
    
    GEETEST_PATTERNS = [
        r'geetest\.com',
        r'gt-captcha',
        r'geetest'
    ]
    
    GENERIC_CAPTCHA_KEYWORDS = [
        'captcha',
        'verify you\'re human',
        'verify you are human',
        'prove you\'re not a robot',
        'security check',
        'bot detection',
        'human verification',
        'complete the challenge',
        'access denied'
    ]
    
    def __init__(self, on_captcha_detected: Optional[Callable[[Dict[str, Any]], None]] = None):
        """
        Initialize the CAPTCHA detector.
        
        Args:
            on_captcha_detected: Optional callback when CAPTCHA is detected
                                Receives detection results as parameter
        """
        self.on_captcha_detected = on_captcha_detected
        self._detection_count = 0
    
    def detect(self, html_content: str, url: str = "") -> Dict[str, Any]:
        """
        Detect CAPTCHAs in HTML content.
        
        Args:
            html_content: HTML content to analyze
            url: URL of the page (for logging)
            
        Returns:
            Dictionary with detection results:
                - detected: Boolean indicating if CAPTCHA was detected
                - captcha_types: List of detected CAPTCHA types
                - confidence: Detection confidence (0.0-1.0)
                - indicators: List of specific indicators found
                - url: The URL analyzed
        """
        result = {
            'detected': False,
            'captcha_types': [],
            'confidence': 0.0,
            'indicators': [],
            'url': url
        }
        
        if not html_content:
            return result
        
        # Convert to lowercase for case-insensitive matching
        html_lower = html_content.lower()
        
        # Parse HTML for more detailed analysis
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
        except Exception as e:
            logger.warning(f"Failed to parse HTML for CAPTCHA detection: {e}")
            soup = None
        
        indicators = []
        captcha_types = set()
        
        # Check for reCAPTCHA
        if self._check_patterns(html_lower, self.RECAPTCHA_PATTERNS):
            if 'recaptcha/api.js' in html_lower or 'recaptcha/enterprise.js' in html_lower:
                captcha_types.add(CaptchaType.RECAPTCHA_V2)
                indicators.append("reCAPTCHA v2 script detected")
            elif 'grecaptcha.execute' in html_lower:
                captcha_types.add(CaptchaType.RECAPTCHA_V3)
                indicators.append("reCAPTCHA v3 detected")
            else:
                captcha_types.add(CaptchaType.RECAPTCHA)
                indicators.append("reCAPTCHA detected")
        
        # Check for hCaptcha
        if self._check_patterns(html_lower, self.HCAPTCHA_PATTERNS):
            captcha_types.add(CaptchaType.HCAPTCHA)
            indicators.append("hCaptcha detected")
        
        # Check for Cloudflare
        if self._check_patterns(html_lower, self.CLOUDFLARE_PATTERNS):
            if 'cf-turnstile' in html_lower:
                captcha_types.add(CaptchaType.CLOUDFLARE_TURNSTILE)
                indicators.append("Cloudflare Turnstile detected")
            else:
                captcha_types.add(CaptchaType.CLOUDFLARE_CHALLENGE)
                indicators.append("Cloudflare Challenge detected")
        
        # Check for FunCaptcha
        if self._check_patterns(html_lower, self.FUNCAPTCHA_PATTERNS):
            captcha_types.add(CaptchaType.FUNCAPTCHA)
            indicators.append("FunCaptcha detected")
        
        # Check for GeeTest
        if self._check_patterns(html_lower, self.GEETEST_PATTERNS):
            captcha_types.add(CaptchaType.GEETEST)
            indicators.append("GeeTest CAPTCHA detected")
        
        # Check for CAPTCHA images
        if soup:
            captcha_images = self._detect_captcha_images(soup)
            if captcha_images:
                captcha_types.add(CaptchaType.SIMPLE_CAPTCHA)
                indicators.append(f"CAPTCHA image(s) detected: {len(captcha_images)}")
        
        # Check for generic CAPTCHA keywords
        keyword_matches = []
        for keyword in self.GENERIC_CAPTCHA_KEYWORDS:
            if keyword in html_lower:
                keyword_matches.append(keyword)
        
        if keyword_matches:
            indicators.append(f"CAPTCHA keywords detected: {', '.join(keyword_matches[:3])}")
            if not captcha_types:
                captcha_types.add(CaptchaType.CUSTOM_CAPTCHA)
        
        # Check for CAPTCHA iframes
        if soup:
            captcha_iframes = self._detect_captcha_iframes(soup)
            if captcha_iframes:
                indicators.append(f"CAPTCHA iframe(s) detected: {len(captcha_iframes)}")
        
        # Calculate confidence based on number of indicators
        if captcha_types:
            result['detected'] = True
            result['captcha_types'] = [ct.value for ct in captcha_types]
            result['indicators'] = indicators
            
            # Higher confidence with more indicators
            result['confidence'] = min(1.0, len(indicators) * 0.25)
            
            logger.info(f"CAPTCHA detected on {url}: {result['captcha_types']}")
            self._detection_count += 1
            
            # Trigger callback if provided
            if self.on_captcha_detected:
                try:
                    self.on_captcha_detected(result)
                except Exception as e:
                    logger.error(f"Error in CAPTCHA callback: {e}")
        
        return result
    
    def _check_patterns(self, text: str, patterns: List[str]) -> bool:
        """
        Check if any pattern matches the text.
        
        Args:
            text: Text to search
            patterns: List of regex patterns
            
        Returns:
            True if any pattern matches
        """
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False
    
    def _detect_captcha_images(self, soup: BeautifulSoup) -> List[str]:
        """
        Detect CAPTCHA-related images in HTML.
        
        Args:
            soup: BeautifulSoup object
            
        Returns:
            List of image URLs
        """
        captcha_images = []
        
        # Look for images with CAPTCHA-related attributes
        for img in soup.find_all('img'):
            src = img.get('src', '').lower()
            alt = img.get('alt', '').lower()
            img_id = img.get('id', '').lower()
            img_class = ' '.join(img.get('class', [])).lower()
            
            if any(keyword in src or keyword in alt or keyword in img_id or keyword in img_class 
                   for keyword in ['captcha', 'challenge', 'verify']):
                captcha_images.append(img.get('src', ''))
        
        return captcha_images
    
    def _detect_captcha_iframes(self, soup: BeautifulSoup) -> List[str]:
        """
        Detect CAPTCHA-related iframes in HTML.
        
        Args:
            soup: BeautifulSoup object
            
        Returns:
            List of iframe sources
        """
        captcha_iframes = []
        
        # Look for iframes with CAPTCHA-related attributes
        for iframe in soup.find_all('iframe'):
            src = iframe.get('src', '').lower()
            iframe_id = iframe.get('id', '').lower()
            iframe_class = ' '.join(iframe.get('class', [])).lower()
            title = iframe.get('title', '').lower()
            
            if any(keyword in src or keyword in iframe_id or keyword in iframe_class or keyword in title
                   for keyword in ['captcha', 'recaptcha', 'hcaptcha', 'challenge', 'verify']):
                captcha_iframes.append(iframe.get('src', ''))
        
        return captcha_iframes
    
    def get_detection_count(self) -> int:
        """
        Get the total number of CAPTCHAs detected.
        
        Returns:
            Number of CAPTCHAs detected
        """
        return self._detection_count
    
    def reset_count(self) -> None:
        """Reset the detection counter."""
        self._detection_count = 0


def detect_captcha(html_content: str, url: str = "") -> Dict[str, Any]:
    """
    Convenience function to detect CAPTCHA in HTML content.
    
    Args:
        html_content: HTML content to analyze
        url: URL of the page (for logging)
        
    Returns:
        Dictionary with detection results
    """
    detector = CaptchaDetector()
    return detector.detect(html_content, url)

