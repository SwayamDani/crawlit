#!/usr/bin/env python3
"""
headers.py - Security headers analysis

Analyzes HTTP security headers and provides security ratings.
"""

import logging
from typing import Dict, List, Optional, Any
from enum import Enum
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


class SecurityRating(Enum):
    """Security rating levels"""
    EXCELLENT = "A+"
    GOOD = "A"
    ACCEPTABLE = "B"
    POOR = "C"
    VERY_POOR = "D"
    CRITICAL = "F"


@dataclass
class HeaderAnalysis:
    """Analysis result for a single security header"""
    name: str
    present: bool
    value: Optional[str] = None
    score: int = 0
    issues: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


@dataclass
class SecurityAnalysisResult:
    """Complete security analysis result"""
    url: str
    overall_score: int
    rating: SecurityRating
    headers_analyzed: Dict[str, HeaderAnalysis]
    missing_headers: List[str]
    vulnerabilities: List[str]
    recommendations: List[str]
    timestamp: str


class SecurityHeadersAnalyzer:
    """
    Analyzes HTTP security headers and provides comprehensive security assessment.
    
    Checks for:
    - Content Security Policy (CSP)
    - HTTP Strict Transport Security (HSTS)
    - X-Frame-Options
    - X-Content-Type-Options
    - X-XSS-Protection
    - Referrer-Policy
    - Permissions-Policy
    - And more...
    """
    
    # Security headers to check
    SECURITY_HEADERS = {
        'Strict-Transport-Security': {
            'score': 10,
            'description': 'Enforces HTTPS connections',
            'recommendation': 'Add with max-age=31536000; includeSubDomains; preload'
        },
        'Content-Security-Policy': {
            'score': 15,
            'description': 'Prevents XSS and injection attacks',
            'recommendation': 'Implement a strict CSP policy'
        },
        'X-Frame-Options': {
            'score': 8,
            'description': 'Prevents clickjacking attacks',
            'recommendation': 'Set to DENY or SAMEORIGIN'
        },
        'X-Content-Type-Options': {
            'score': 5,
            'description': 'Prevents MIME-sniffing',
            'recommendation': 'Set to nosniff'
        },
        'X-XSS-Protection': {
            'score': 3,
            'description': 'Legacy XSS protection (deprecated but still useful)',
            'recommendation': 'Set to 1; mode=block'
        },
        'Referrer-Policy': {
            'score': 5,
            'description': 'Controls referrer information',
            'recommendation': 'Set to strict-origin-when-cross-origin or no-referrer'
        },
        'Permissions-Policy': {
            'score': 8,
            'description': 'Controls browser features and APIs',
            'recommendation': 'Define restrictive permissions'
        },
        'Cross-Origin-Opener-Policy': {
            'score': 5,
            'description': 'Isolates browsing context',
            'recommendation': 'Set to same-origin'
        },
        'Cross-Origin-Resource-Policy': {
            'score': 5,
            'description': 'Controls cross-origin resource loading',
            'recommendation': 'Set to same-origin or cross-origin as needed'
        },
        'Cross-Origin-Embedder-Policy': {
            'score': 5,
            'description': 'Prevents loading of cross-origin resources',
            'recommendation': 'Set to require-corp'
        }
    }
    
    def __init__(self):
        """Initialize security headers analyzer"""
        self.max_score = sum(header['score'] for header in self.SECURITY_HEADERS.values())
    
    def analyze(self, headers: Dict[str, str], url: str = "") -> SecurityAnalysisResult:
        """
        Analyze security headers.
        
        Args:
            headers: HTTP response headers (case-insensitive dict)
            url: URL being analyzed
            
        Returns:
            SecurityAnalysisResult with comprehensive analysis
        """
        # Normalize header names (case-insensitive)
        normalized_headers = {k.lower(): v for k, v in headers.items()}
        
        analyzed_headers = {}
        current_score = 0
        missing_headers = []
        vulnerabilities = []
        recommendations = []
        
        # Analyze each security header
        for header_name, header_info in self.SECURITY_HEADERS.items():
            header_lower = header_name.lower()
            
            if header_lower in normalized_headers:
                analysis = self._analyze_header(
                    header_name,
                    normalized_headers[header_lower],
                    header_info
                )
                analyzed_headers[header_name] = analysis
                current_score += analysis.score
                
                if analysis.issues:
                    vulnerabilities.extend(analysis.issues)
                if analysis.recommendations:
                    recommendations.extend(analysis.recommendations)
            else:
                # Header is missing
                analyzed_headers[header_name] = HeaderAnalysis(
                    name=header_name,
                    present=False,
                    score=0,
                    recommendations=[header_info['recommendation']]
                )
                missing_headers.append(header_name)
                recommendations.append(f"Add {header_name}: {header_info['recommendation']}")
        
        # Calculate rating
        percentage = (current_score / self.max_score) * 100
        rating = self._calculate_rating(percentage)
        
        from datetime import datetime
        result = SecurityAnalysisResult(
            url=url,
            overall_score=current_score,
            rating=rating,
            headers_analyzed=analyzed_headers,
            missing_headers=missing_headers,
            vulnerabilities=vulnerabilities,
            recommendations=recommendations,
            timestamp=datetime.now().isoformat()
        )
        
        logger.info(f"Security analysis for {url}: {rating.value} ({current_score}/{self.max_score})")
        
        return result
    
    def _analyze_header(self, name: str, value: str, info: Dict[str, Any]) -> HeaderAnalysis:
        """Analyze a specific header"""
        analysis = HeaderAnalysis(
            name=name,
            present=True,
            value=value,
            score=0
        )
        
        # Header-specific analysis
        if name == 'Strict-Transport-Security':
            analysis.score, analysis.issues, analysis.recommendations = self._analyze_hsts(value, info['score'])
        
        elif name == 'Content-Security-Policy':
            analysis.score, analysis.issues, analysis.recommendations = self._analyze_csp(value, info['score'])
        
        elif name == 'X-Frame-Options':
            analysis.score, analysis.issues, analysis.recommendations = self._analyze_frame_options(value, info['score'])
        
        elif name == 'X-Content-Type-Options':
            analysis.score, analysis.issues, analysis.recommendations = self._analyze_content_type_options(value, info['score'])
        
        elif name == 'X-XSS-Protection':
            analysis.score, analysis.issues, analysis.recommendations = self._analyze_xss_protection(value, info['score'])
        
        elif name == 'Referrer-Policy':
            analysis.score, analysis.issues, analysis.recommendations = self._analyze_referrer_policy(value, info['score'])
        
        else:
            # Generic analysis - header is present
            analysis.score = info['score']
        
        return analysis
    
    def _analyze_hsts(self, value: str, max_score: int) -> tuple:
        """Analyze HSTS header"""
        issues = []
        recommendations = []
        score = 0
        
        value_lower = value.lower()
        
        # Check for max-age
        if 'max-age=' in value_lower:
            import re
            match = re.search(r'max-age=(\d+)', value_lower)
            if match:
                max_age = int(match.group(1))
                if max_age >= 31536000:  # 1 year
                    score += max_score * 0.5
                elif max_age >= 15768000:  # 6 months
                    score += max_score * 0.3
                    recommendations.append("Increase max-age to at least 31536000 (1 year)")
                else:
                    score += max_score * 0.1
                    issues.append("HSTS max-age is too short")
        else:
            issues.append("HSTS missing max-age directive")
        
        # Check for includeSubDomains
        if 'includesubdomains' in value_lower:
            score += max_score * 0.3
        else:
            recommendations.append("Add includeSubDomains directive")
        
        # Check for preload
        if 'preload' in value_lower:
            score += max_score * 0.2
        else:
            recommendations.append("Consider adding preload directive")
        
        return int(score), issues, recommendations
    
    def _analyze_csp(self, value: str, max_score: int) -> tuple:
        """Analyze Content Security Policy"""
        issues = []
        recommendations = []
        score = max_score  # Start with full score, deduct for issues
        
        value_lower = value.lower()
        
        # Check for unsafe directives
        if "'unsafe-inline'" in value_lower:
            issues.append("CSP allows unsafe-inline which can enable XSS attacks")
            score -= max_score * 0.3
        
        if "'unsafe-eval'" in value_lower:
            issues.append("CSP allows unsafe-eval which is dangerous")
            score -= max_score * 0.2
        
        # Check for wildcard sources
        if "* " in value or value.endswith("*"):
            issues.append("CSP uses wildcard (*) which is too permissive")
            score -= max_score * 0.2
        
        # Check for important directives
        if 'default-src' not in value_lower:
            recommendations.append("Add default-src directive")
        
        if 'script-src' not in value_lower:
            recommendations.append("Add script-src directive")
        
        return max(0, int(score)), issues, recommendations
    
    def _analyze_frame_options(self, value: str, max_score: int) -> tuple:
        """Analyze X-Frame-Options"""
        issues = []
        recommendations = []
        
        value_upper = value.upper()
        
        if value_upper in ['DENY', 'SAMEORIGIN']:
            score = max_score
        elif value_upper.startswith('ALLOW-FROM'):
            score = max_score * 0.7
            recommendations.append("ALLOW-FROM is deprecated, use CSP frame-ancestors instead")
        else:
            score = 0
            issues.append(f"Invalid X-Frame-Options value: {value}")
        
        return int(score), issues, recommendations
    
    def _analyze_content_type_options(self, value: str, max_score: int) -> tuple:
        """Analyze X-Content-Type-Options"""
        if value.lower() == 'nosniff':
            return max_score, [], []
        else:
            return 0, [f"Invalid X-Content-Type-Options value: {value}"], ["Set to 'nosniff'"]
    
    def _analyze_xss_protection(self, value: str, max_score: int) -> tuple:
        """Analyze X-XSS-Protection"""
        value_lower = value.lower()
        
        if '1' in value and 'mode=block' in value_lower:
            return max_score, [], []
        elif '1' in value:
            return int(max_score * 0.7), [], ["Add mode=block"]
        elif '0' in value:
            return 0, ["XSS Protection is disabled"], ["Enable XSS Protection with 1; mode=block"]
        else:
            return 0, [f"Invalid X-XSS-Protection value: {value}"], []
    
    def _analyze_referrer_policy(self, value: str, max_score: int) -> tuple:
        """Analyze Referrer-Policy"""
        value_lower = value.lower()
        
        strict_policies = ['no-referrer', 'same-origin', 'strict-origin', 'strict-origin-when-cross-origin']
        
        if value_lower in strict_policies:
            return max_score, [], []
        elif value_lower in ['origin', 'origin-when-cross-origin']:
            return int(max_score * 0.6), [], ["Consider using a stricter policy"]
        else:
            return int(max_score * 0.3), ["Referrer policy is permissive"], ["Use strict-origin-when-cross-origin"]
    
    def _calculate_rating(self, percentage: float) -> SecurityRating:
        """Calculate security rating from percentage score"""
        if percentage >= 95:
            return SecurityRating.EXCELLENT
        elif percentage >= 85:
            return SecurityRating.GOOD
        elif percentage >= 70:
            return SecurityRating.ACCEPTABLE
        elif percentage >= 50:
            return SecurityRating.POOR
        elif percentage >= 30:
            return SecurityRating.VERY_POOR
        else:
            return SecurityRating.CRITICAL


def analyze_security_headers(headers: Dict[str, str], url: str = "") -> SecurityAnalysisResult:
    """
    Convenience function to analyze security headers.
    
    Args:
        headers: HTTP response headers
        url: URL being analyzed
        
    Returns:
        SecurityAnalysisResult
    """
    analyzer = SecurityHeadersAnalyzer()
    return analyzer.analyze(headers, url)




