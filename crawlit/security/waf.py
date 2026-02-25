#!/usr/bin/env python3
"""
waf.py - Web Application Firewall detection

Detects various WAF solutions and provides evasion recommendations.
"""

import json
import re
import logging
from pathlib import Path
from typing import Dict, List, Optional, Set, Any
from enum import Enum
from dataclasses import dataclass

_SIGNATURES_FILE = Path(__file__).parent / "waf_signatures.json"

logger = logging.getLogger(__name__)


class WAFType(Enum):
    """Known WAF types"""
    CLOUDFLARE = "Cloudflare"
    AWS_WAF = "AWS WAF"
    AKAMAI = "Akamai"
    INCAPSULA = "Incapsula/Imperva"
    MODSECURITY = "ModSecurity"
    F5_BIG_IP = "F5 BIG-IP ASM"
    BARRACUDA = "Barracuda"
    FORTIWEB = "FortiWeb"
    CITRIX_NETSCALER = "Citrix NetScaler"
    RADWARE = "Radware AppWall"
    SUCURI = "Sucuri CloudProxy"
    WORDFENCE = "Wordfence"
    CLOUDFRONT = "Amazon CloudFront"
    AZURE_WAF = "Azure WAF"
    SQREEN = "Sqreen"
    REBLAZE = "Reblaze"
    WALLARM = "Wallarm"
    UNKNOWN = "Unknown WAF"
    NONE = "No WAF Detected"


@dataclass
class WAFDetectionResult:
    """Result of WAF detection"""
    detected: bool
    waf_type: WAFType
    confidence: float  # 0.0 to 1.0
    indicators: List[str]
    recommendations: List[str]
    headers: Dict[str, str]
    cookies: List[str]


class WAFDetector:
    """
    Detects Web Application Firewalls by analyzing HTTP responses.
    
    Uses multiple detection methods:
    - HTTP headers
    - Cookies
    - Response body patterns
    - Server behavior
    """
    
    # WAF signatures are loaded from waf_signatures.json at first use
    _WAF_SIGNATURES_CACHE: Optional[Dict] = None

    @classmethod
    def _load_waf_signatures(cls) -> Dict[WAFType, Dict]:
        """Load WAF signatures from the external JSON file, keyed by WAFType."""
        if cls._WAF_SIGNATURES_CACHE is not None:
            return cls._WAF_SIGNATURES_CACHE

        try:
            with open(_SIGNATURES_FILE, "r", encoding="utf-8") as fh:
                raw: Dict[str, Dict] = json.load(fh)
        except Exception as exc:
            logger.error(f"Failed to load WAF signatures from {_SIGNATURES_FILE}: {exc}")
            raw = {}

        # Build a reverse map: WAFType.value -> WAFType member
        value_to_waf = {member.value: member for member in WAFType}
        result: Dict[WAFType, Dict] = {}
        for name, sig in raw.items():
            waf = value_to_waf.get(name)
            if waf is None:
                logger.warning(f"Unknown WAF name in signatures file: {name!r}")
                continue
            result[waf] = sig

        cls._WAF_SIGNATURES_CACHE = result
        return result

    @property
    def WAF_SIGNATURES(self) -> Dict[WAFType, Dict]:
        """Signatures dict, loaded lazily from waf_signatures.json."""
        return self._load_waf_signatures()

    def __init__(self):
        """Initialize WAF detector"""
        pass
    
    def detect(self, headers: Dict[str, str], cookies: Optional[Dict[str, str]] = None,
               body: Optional[str] = None, server_header: Optional[str] = None) -> WAFDetectionResult:
        """
        Detect WAF from HTTP response.
        
        Args:
            headers: HTTP response headers
            cookies: HTTP cookies (optional)
            body: Response body (optional)
            server_header: Server header value (optional)
            
        Returns:
            WAFDetectionResult with detection information
        """
        # Normalize headers and cookies
        normalized_headers = {k.lower(): v for k, v in headers.items()}
        cookie_names = set(cookies.keys() if cookies else [])
        body_lower = body.lower() if body else ""
        server_lower = (server_header or normalized_headers.get('server', '')).lower()
        
        detection_scores = {}
        detection_indicators = {}
        
        # Check each WAF signature
        for waf_type, signatures in self.WAF_SIGNATURES.items():
            score = 0
            indicators = []
            
            # Check headers
            for header in signatures['headers']:
                if header.lower() in normalized_headers:
                    score += 3
                    indicators.append(f"Header: {header}")
            
            # Check cookies
            for cookie_pattern in signatures['cookies']:
                for cookie_name in cookie_names:
                    if cookie_pattern.lower() in cookie_name.lower():
                        score += 2
                        indicators.append(f"Cookie: {cookie_name}")
            
            # Check server header
            for server_pattern in signatures['server']:
                if server_pattern in server_lower:
                    score += 4
                    indicators.append(f"Server: {server_pattern}")
            
            # Check body patterns
            if body:
                for pattern in signatures['body_patterns']:
                    if re.search(pattern, body_lower, re.IGNORECASE):
                        score += 1
                        indicators.append(f"Body pattern: {pattern}")
            
            if score > 0:
                detection_scores[waf_type] = score
                detection_indicators[waf_type] = indicators
        
        # Determine detected WAF
        if detection_scores:
            detected_waf = max(detection_scores, key=detection_scores.get)
            max_score = detection_scores[detected_waf]
            
            # Calculate confidence (normalized to 0-1)
            confidence = min(max_score / 10.0, 1.0)
            
            # Get recommendations
            recommendations = self._get_recommendations(detected_waf)
            
            result = WAFDetectionResult(
                detected=True,
                waf_type=detected_waf,
                confidence=confidence,
                indicators=detection_indicators[detected_waf],
                recommendations=recommendations,
                headers={k: v for k, v in normalized_headers.items() if any(
                    sig in k for sig in self.WAF_SIGNATURES[detected_waf]['headers']
                )},
                cookies=[c for c in cookie_names if any(
                    pattern.lower() in c.lower() for pattern in self.WAF_SIGNATURES[detected_waf]['cookies']
                )]
            )
            
            logger.info(f"WAF detected: {detected_waf.value} (confidence: {confidence:.2f})")
            
        else:
            result = WAFDetectionResult(
                detected=False,
                waf_type=WAFType.NONE,
                confidence=0.0,
                indicators=[],
                recommendations=[],
                headers={},
                cookies=[]
            )
            
            logger.debug("No WAF detected")
        
        return result
    
    def _get_recommendations(self, waf_type: WAFType) -> List[str]:
        """Get recommendations for dealing with a specific WAF (loaded from signatures file)."""
        sig = self.WAF_SIGNATURES.get(waf_type, {})
        recs = sig.get("recommendations", [])
        if recs:
            return recs
        return [
            "Use realistic browser behavior",
            "Implement proper rate limiting",
            "Respect the website's terms of service",
            "Consider reaching out to site owners for API access"
        ]
    
    def get_all_supported_wafs(self) -> List[WAFType]:
        """Get list of all supported WAF types"""
        return list(self.WAF_SIGNATURES.keys())


def detect_waf(headers: Dict[str, str], cookies: Optional[Dict[str, str]] = None,
               body: Optional[str] = None) -> WAFDetectionResult:
    """
    Convenience function to detect WAF.
    
    Args:
        headers: HTTP response headers
        cookies: HTTP cookies (optional)
        body: Response body (optional)
        
    Returns:
        WAFDetectionResult
    """
    detector = WAFDetector()
    return detector.detect(headers, cookies, body)




