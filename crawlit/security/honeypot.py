#!/usr/bin/env python3
"""
honeypot.py - Honeypot trap detection

Detects honeypot traps designed to catch web scrapers and bots.
"""

import re
import logging
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass, field
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


@dataclass
class HoneypotElement:
    """Represents a detected honeypot element"""
    element_type: str  # 'link', 'form', 'input'
    tag_name: str
    element_id: Optional[str] = None
    element_class: Optional[str] = None
    url: Optional[str] = None
    trap_type: str = ""  # 'invisible', 'hidden', 'off-screen', etc.
    confidence: float = 0.0  # 0.0 to 1.0
    reasons: List[str] = field(default_factory=list)


@dataclass
class HoneypotDetectionResult:
    """Result of honeypot detection"""
    has_honeypots: bool
    honeypot_count: int
    honeypots: List[HoneypotElement]
    risk_level: str  # 'low', 'medium', 'high'
    recommendations: List[str]


class HoneypotDetector:
    """
    Detects honeypot traps in HTML pages.
    
    Honeypots are invisible or hidden elements designed to catch bots.
    A legitimate user would never interact with them, so any interaction
    indicates automated behavior.
    
    Detection methods:
    - CSS-based hiding (display:none, visibility:hidden)
    - Off-screen positioning
    - Zero dimensions
    - Transparent elements
    - Hidden form fields with suspicious names
    - Links with suspicious patterns
    """
    
    # Suspicious patterns that might indicate honeypots
    HONEYPOT_PATTERNS = [
        'honeypot', 'hp-', 'hpot', 'trap', 'bot-trap',
        'spider-trap', 'crawler-trap', 'decoy',
        'fake-field', 'hidden-field', 'invisible',
        'do-not-fill', 'leave-empty', 'bot-field'
    ]
    
    def __init__(self, html_content: str, url: str = ""):
        """
        Initialize honeypot detector.
        
        Args:
            html_content: HTML content to analyze
            url: URL of the page
        """
        self.html_content = html_content
        self.url = url
        self.soup = BeautifulSoup(html_content, 'html.parser')
        self.honeypots: List[HoneypotElement] = []
    
    def detect_all(self) -> HoneypotDetectionResult:
        """
        Detect all honeypots in the page.
        
        Returns:
            HoneypotDetectionResult with all detected honeypots
        """
        # Clear previous results
        self.honeypots = []
        
        # Run all detection methods
        self._detect_invisible_elements()
        self._detect_hidden_links()
        self._detect_off_screen_elements()
        self._detect_zero_dimension_elements()
        self._detect_transparent_elements()
        self._detect_suspicious_form_fields()
        self._detect_mouse_traps()
        
        # Calculate risk level
        risk_level = self._calculate_risk_level()
        
        # Get recommendations
        recommendations = self._get_recommendations()
        
        result = HoneypotDetectionResult(
            has_honeypots=len(self.honeypots) > 0,
            honeypot_count=len(self.honeypots),
            honeypots=self.honeypots,
            risk_level=risk_level,
            recommendations=recommendations
        )
        
        if result.has_honeypots:
            logger.warning(f"Detected {result.honeypot_count} honeypot(s) on {self.url} (risk: {risk_level})")
        
        return result
    
    def _detect_invisible_elements(self):
        """Detect elements hidden with CSS display:none or visibility:hidden"""
        # Find elements with inline styles
        for element in self.soup.find_all(style=True):
            style = element.get('style', '').lower()
            
            reasons = []
            confidence = 0.0
            
            if 'display:none' in style.replace(' ', '') or 'display: none' in style:
                reasons.append("CSS display:none")
                confidence += 0.4
            
            if 'visibility:hidden' in style.replace(' ', '') or 'visibility: hidden' in style:
                reasons.append("CSS visibility:hidden")
                confidence += 0.3
            
            if reasons:
                # Check if it's a link or form element
                if element.name in ['a', 'form', 'input', 'button']:
                    # Check for suspicious names
                    elem_id = element.get('id', '').lower()
                    elem_class = ' '.join(element.get('class', [])).lower()
                    elem_name = element.get('name', '').lower()
                    
                    # Increase confidence if names are suspicious
                    if any(pattern in elem_id or pattern in elem_class or pattern in elem_name
                           for pattern in self.HONEYPOT_PATTERNS):
                        confidence += 0.3
                        reasons.append("Suspicious naming pattern")
                    
                    # For legitimate sites, some elements might be hidden for UI reasons
                    # So we only flag high confidence ones
                    if confidence >= 0.5:
                        self.honeypots.append(HoneypotElement(
                            element_type=element.name,
                            tag_name=element.name,
                            element_id=element.get('id'),
                            element_class=' '.join(element.get('class', [])),
                            url=element.get('href') if element.name == 'a' else None,
                            trap_type='invisible',
                            confidence=min(confidence, 1.0),
                            reasons=reasons
                        ))
    
    def _detect_hidden_links(self):
        """Detect links that are likely honeypots"""
        for link in self.soup.find_all('a', href=True):
            reasons = []
            confidence = 0.0
            
            href = link.get('href', '')
            link_text = link.get_text().strip().lower()
            link_id = link.get('id', '').lower()
            link_class = ' '.join(link.get('class', [])).lower()
            
            # Check for suspicious patterns in href
            if any(pattern in href.lower() for pattern in ['trap', 'honeypot', 'bot', 'crawler']):
                reasons.append("Suspicious URL pattern")
                confidence += 0.5
            
            # Check for suspicious IDs or classes
            if any(pattern in link_id or pattern in link_class for pattern in self.HONEYPOT_PATTERNS):
                reasons.append("Suspicious ID/class")
                confidence += 0.4
            
            # Check for empty or suspicious link text
            if link_text in ['', 'do not follow', 'bot trap', 'hidden']:
                reasons.append("Suspicious or empty link text")
                confidence += 0.3
            
            # Check if link has aria-hidden attribute
            if link.get('aria-hidden') == 'true':
                reasons.append("aria-hidden=true")
                confidence += 0.2
            
            if confidence >= 0.5:
                self.honeypots.append(HoneypotElement(
                    element_type='link',
                    tag_name='a',
                    element_id=link.get('id'),
                    element_class=' '.join(link.get('class', [])),
                    url=href,
                    trap_type='hidden_link',
                    confidence=min(confidence, 1.0),
                    reasons=reasons
                ))
    
    def _detect_off_screen_elements(self):
        """Detect elements positioned off-screen"""
        for element in self.soup.find_all(style=True):
            style = element.get('style', '').lower()
            
            reasons = []
            confidence = 0.0
            
            # Check for negative positioning
            if re.search(r'(left|top|margin-left|margin-top):\s*-\d+', style):
                reasons.append("Negative positioning (off-screen)")
                confidence += 0.4
            
            # Check for position:absolute with large negative values
            if 'position:absolute' in style.replace(' ', '') or 'position: absolute' in style:
                if re.search(r'-\d{3,}px', style):  # -100px or more
                    reasons.append("Absolute positioning far off-screen")
                    confidence += 0.3
            
            if confidence >= 0.5 and element.name in ['a', 'form', 'input', 'button']:
                self.honeypots.append(HoneypotElement(
                    element_type=element.name,
                    tag_name=element.name,
                    element_id=element.get('id'),
                    element_class=' '.join(element.get('class', [])),
                    url=element.get('href') if element.name == 'a' else None,
                    trap_type='off_screen',
                    confidence=min(confidence, 1.0),
                    reasons=reasons
                ))
    
    def _detect_zero_dimension_elements(self):
        """Detect elements with zero or near-zero dimensions"""
        for element in self.soup.find_all(style=True):
            style = element.get('style', '').lower()
            
            reasons = []
            confidence = 0.0
            
            # Check for width/height: 0
            if re.search(r'(width|height):\s*0(px)?', style):
                reasons.append("Zero dimensions")
                confidence += 0.5
            
            # Check for very small dimensions (< 3px)
            if re.search(r'(width|height):\s*[12]px', style):
                reasons.append("Extremely small dimensions")
                confidence += 0.3
            
            if confidence >= 0.5 and element.name in ['a', 'form', 'input', 'div']:
                self.honeypots.append(HoneypotElement(
                    element_type=element.name,
                    tag_name=element.name,
                    element_id=element.get('id'),
                    element_class=' '.join(element.get('class', [])),
                    url=element.get('href') if element.name == 'a' else None,
                    trap_type='zero_dimension',
                    confidence=min(confidence, 1.0),
                    reasons=reasons
                ))
    
    def _detect_transparent_elements(self):
        """Detect transparent elements"""
        for element in self.soup.find_all(style=True):
            style = element.get('style', '').lower()
            
            reasons = []
            confidence = 0.0
            
            # Check for opacity: 0
            if 'opacity:0' in style.replace(' ', '') or 'opacity: 0' in style:
                reasons.append("Fully transparent (opacity:0)")
                confidence += 0.5  # Increased from 0.4 to meet threshold
            
            # Check for rgba with alpha = 0
            if re.search(r'rgba?\([^)]*,\s*0\)', style):
                reasons.append("Transparent color")
                confidence += 0.4  # Increased from 0.3
            
            if confidence >= 0.5 and element.name in ['a', 'form', 'input', 'button']:
                self.honeypots.append(HoneypotElement(
                    element_type=element.name,
                    tag_name=element.name,
                    element_id=element.get('id'),
                    element_class=' '.join(element.get('class', [])),
                    url=element.get('href') if element.name == 'a' else None,
                    trap_type='transparent',
                    confidence=min(confidence, 1.0),
                    reasons=reasons
                ))
    
    def _detect_suspicious_form_fields(self):
        """Detect hidden form fields that might be honeypots"""
        # Look for hidden input fields
        for input_field in self.soup.find_all('input'):
            input_type = input_field.get('type', '').lower()
            input_name = input_field.get('name', '').lower()
            input_id = input_field.get('id', '').lower()
            input_class = ' '.join(input_field.get('class', [])).lower()
            
            reasons = []
            confidence = 0.0
            
            # Type="hidden" can be legitimate, check for suspicious patterns
            if input_type == 'hidden':
                if any(pattern in input_name or pattern in input_id or pattern in input_class
                       for pattern in self.HONEYPOT_PATTERNS):
                    reasons.append("Hidden field with suspicious name")
                    confidence += 0.6
                
                # Check for fields with instructions not to fill
                placeholder = input_field.get('placeholder', '').lower()
                if any(phrase in placeholder for phrase in ['leave empty', 'do not fill', 'for bots']):
                    reasons.append("Instructions to leave empty")
                    confidence += 0.4
            
            # Fields with type="text" but hidden via CSS or suspicious names
            elif input_type in ['text', 'email', 'tel']:
                if any(pattern in input_name for pattern in self.HONEYPOT_PATTERNS):
                    reasons.append("Visible field with honeypot name")
                    confidence += 0.5
                
                # Check for tabindex=-1 (not keyboard accessible)
                if input_field.get('tabindex') == '-1':
                    reasons.append("Not keyboard accessible (tabindex=-1)")
                    confidence += 0.2
            
            if confidence >= 0.5:
                self.honeypots.append(HoneypotElement(
                    element_type='form_field',
                    tag_name='input',
                    element_id=input_field.get('id'),
                    element_class=' '.join(input_field.get('class', [])),
                    trap_type='suspicious_field',
                    confidence=min(confidence, 1.0),
                    reasons=reasons
                ))
    
    def _detect_mouse_traps(self):
        """Detect elements designed to catch mouse interactions"""
        # Look for elements with JavaScript mousedown/mouseup but no visible content
        for element in self.soup.find_all(['a', 'button', 'div']):
            reasons = []
            confidence = 0.0
            
            # Has JavaScript event handlers
            has_onclick = element.get('onclick') is not None
            has_onmousedown = element.get('onmousedown') is not None
            
            if has_onclick or has_onmousedown:
                # Check if element has no visible text
                text = element.get_text().strip()
                if not text:
                    reasons.append("Interactive element with no visible text")
                    confidence += 0.3
                
                # Check if element is tiny
                style = element.get('style', '').lower()
                if re.search(r'(width|height):\s*[12]px', style):
                    reasons.append("Interactive element with minimal size")
                    confidence += 0.3
            
            if confidence >= 0.5:
                self.honeypots.append(HoneypotElement(
                    element_type='mouse_trap',
                    tag_name=element.name,
                    element_id=element.get('id'),
                    element_class=' '.join(element.get('class', [])),
                    trap_type='mouse_trap',
                    confidence=min(confidence, 1.0),
                    reasons=reasons
                ))
    
    def _calculate_risk_level(self) -> str:
        """Calculate overall risk level based on detected honeypots"""
        if not self.honeypots:
            return 'none'
        
        # Calculate average confidence
        avg_confidence = sum(hp.confidence for hp in self.honeypots) / len(self.honeypots)
        
        # Consider both count and confidence
        if len(self.honeypots) >= 5 or avg_confidence >= 0.8:
            return 'high'
        elif len(self.honeypots) >= 2 or avg_confidence >= 0.6:
            return 'medium'
        else:
            return 'low'
    
    def _get_recommendations(self) -> List[str]:
        """Get recommendations based on detected honeypots"""
        if not self.honeypots:
            return []
        
        recommendations = [
            "Avoid interacting with invisible or hidden elements",
            "Do not follow links with suspicious patterns",
            "Skip form fields marked as honeypots",
            "Implement visibility checking before element interaction",
            "Respect robots.txt and site terms of service"
        ]
        
        # Add specific recommendations based on trap types
        trap_types = set(hp.trap_type for hp in self.honeypots)
        
        if 'hidden_link' in trap_types:
            recommendations.append("Filter out links with 'trap', 'honeypot', or 'bot' in URL")
        
        if 'suspicious_field' in trap_types:
            recommendations.append("Do not fill form fields with honeypot-indicating names")
        
        if 'mouse_trap' in trap_types:
            recommendations.append("Avoid random mouse movements or clicks")
        
        return recommendations


def detect_honeypots(html_content: str, url: str = "") -> HoneypotDetectionResult:
    """
    Convenience function to detect honeypots.
    
    Args:
        html_content: HTML content to analyze
        url: URL of the page
        
    Returns:
        HoneypotDetectionResult
    """
    detector = HoneypotDetector(html_content, url)
    return detector.detect_all()

