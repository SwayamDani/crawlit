#!/usr/bin/env python3
"""
language.py - Advanced language detection

Detects page language using multiple methods beyond just HTML lang attribute.
"""

import re
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from collections import Counter
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


@dataclass
class LanguageDetection:
    """Result of language detection"""
    primary_language: str  # ISO 639-1 code (e.g., 'en', 'es', 'fr')
    confidence: float  # 0.0 to 1.0
    detected_languages: List[Tuple[str, float]]  # [(lang, confidence), ...]
    detection_methods: Dict[str, str]  # method_name -> detected_language
    html_lang: Optional[str] = None
    meta_lang: Optional[str] = None
    content_lang: Optional[str] = None


class LanguageDetector:
    """
    Advanced language detection for web pages.
    
    Detection methods:
    1. HTML lang attribute
    2. Meta tags (Content-Language, http-equiv)
    3. Text content analysis (character frequency)
    4. Common words detection
    5. URL patterns
    6. Title and meta description
    """
    
    # Common words in different languages (top 20 most frequent words)
    COMMON_WORDS = {
        'en': {'the', 'be', 'to', 'of', 'and', 'a', 'in', 'that', 'have', 'i',
               'it', 'for', 'not', 'on', 'with', 'he', 'as', 'you', 'do', 'at'},
        'es': {'de', 'la', 'que', 'el', 'en', 'y', 'a', 'los', 'se', 'del',
               'las', 'un', 'por', 'con', 'no', 'una', 'su', 'para', 'es', 'al'},
        'fr': {'de', 'le', 'la', 'et', 'un', 'à', 'être', 'en', 'que', 'du',
               'les', 'avoir', 'ce', 'il', 'pour', 'pas', 'vous', 'par', 'sur', 'ne'},
        'de': {'der', 'die', 'und', 'in', 'den', 'von', 'zu', 'das', 'mit', 'sich',
               'des', 'auf', 'für', 'ist', 'im', 'dem', 'nicht', 'ein', 'eine', 'als'},
        'it': {'di', 'a', 'da', 'in', 'per', 'un', 'il', 'del', 'la', 'i',
               'che', 'non', 'con', 'una', 'su', 'al', 'le', 'si', 'nel', 'della'},
        'pt': {'de', 'a', 'o', 'que', 'e', 'do', 'da', 'em', 'um', 'para',
               'é', 'com', 'não', 'uma', 'os', 'no', 'se', 'na', 'por', 'mais'},
        'nl': {'de', 'van', 'het', 'een', 'in', 'en', 'te', 'op', 'is', 'aan',
               'dat', 'die', 'voor', 'met', 'hij', 'door', 'als', 'zijn', 'er', 'naar'},
        'ru': {'и', 'в', 'не', 'на', 'я', 'что', 'он', 'с', 'как', 'а',
               'то', 'все', 'она', 'так', 'его', 'но', 'да', 'ты', 'к', 'у'},
        'ja': {'の', 'に', 'は', 'を', 'た', 'が', 'で', 'て', 'と', 'し',
               'れ', 'さ', 'ある', 'いる', 'も', 'する', 'から', 'な', 'こと', 'として'},
        'zh': {'的', '一', '是', '在', '不', '了', '有', '和', '人', '这',
               '中', '大', '为', '上', '个', '国', '我', '以', '要', '他'},
        'ar': {'في', 'من', 'على', 'أن', 'إلى', 'هذا', 'كان', 'قد', 'التي', 'أو',
               'ما', 'لا', 'عن', 'به', 'كل', 'إن', 'ولا', 'هو', 'أي', 'حتى'},
        'pl': {'i', 'w', 'na', 'z', 'do', 'się', 'nie', 'to', 'jest', 'o',
               'że', 'a', 'co', 'za', 'po', 'ze', 'przez', 'dla', 'jako', 'od'},
        'tr': {'bir', 've', 'bu', 'da', 'de', 'ile', 'için', 'daha', 'var', 'mi',
               'ne', 'gibi', 'ama', 'çok', 'hem', 'ya', 'kadar', 'sadece', 'iki', 'o'},
        'sv': {'och', 'att', 'i', 'en', 'det', 'som', 'på', 'är', 'för', 'med',
               'av', 'den', 'till', 'har', 'inte', 'ett', 'om', 'han', 'de', 'var'},
        'ko': {'의', '이', '가', '을', '는', '에', '와', '로', '으로', '에서',
               '하다', '있다', '되다', '하는', '것', '수', '등', '않다', '없다', '위해'}
    }
    
    # Character frequency patterns (unique characters for certain languages)
    CHAR_PATTERNS = {
        'ja': re.compile(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]'),  # Hiragana, Katakana, Kanji
        'ko': re.compile(r'[\uAC00-\uD7AF\u1100-\u11FF]'),  # Hangul
        'zh': re.compile(r'[\u4E00-\u9FFF]'),  # CJK Unified Ideographs
        'ar': re.compile(r'[\u0600-\u06FF]'),  # Arabic
        'he': re.compile(r'[\u0590-\u05FF]'),  # Hebrew
        'th': re.compile(r'[\u0E00-\u0E7F]'),  # Thai
        'el': re.compile(r'[\u0370-\u03FF]'),  # Greek
        'ru': re.compile(r'[\u0400-\u04FF]'),  # Cyrillic
    }
    
    def __init__(self, html_content: str, url: str = ""):
        """
        Initialize language detector.
        
        Args:
            html_content: HTML content to analyze
            url: URL of the page (for URL-based detection)
        """
        self.html_content = html_content
        self.url = url
        self.soup = BeautifulSoup(html_content, 'html.parser')
        self.detection_methods: Dict[str, str] = {}
    
    def detect(self) -> LanguageDetection:
        """
        Detect page language using multiple methods.
        
        Returns:
            LanguageDetection object with results
        """
        # Method 1: HTML lang attribute
        html_lang = self._detect_from_html_lang()
        if html_lang:
            self.detection_methods['html_lang'] = html_lang
        
        # Method 2: Meta tags
        meta_lang = self._detect_from_meta_tags()
        if meta_lang:
            self.detection_methods['meta_tags'] = meta_lang
        
        # Method 3: URL patterns
        url_lang = self._detect_from_url()
        if url_lang:
            self.detection_methods['url'] = url_lang
        
        # Method 4: Content analysis (character patterns)
        char_lang = self._detect_from_character_patterns()
        if char_lang:
            self.detection_methods['characters'] = char_lang
        
        # Method 5: Common words
        word_langs = self._detect_from_common_words()
        if word_langs:
            top_word_lang = word_langs[0][0]
            self.detection_methods['common_words'] = top_word_lang
        
        # Method 6: Title and meta description
        meta_content_lang = self._detect_from_title_meta()
        if meta_content_lang:
            self.detection_methods['title_meta'] = meta_content_lang
        
        # Combine results with weighted voting
        primary_lang, confidence, all_detections = self._combine_detections()
        
        result = LanguageDetection(
            primary_language=primary_lang,
            confidence=confidence,
            detected_languages=all_detections,
            detection_methods=self.detection_methods,
            html_lang=html_lang,
            meta_lang=meta_lang,
            content_lang=char_lang or (word_langs[0][0] if word_langs else None)
        )
        
        logger.info(f"Detected language: {primary_lang} (confidence: {confidence:.2f})")
        
        return result
    
    def _detect_from_html_lang(self) -> Optional[str]:
        """Detect from HTML lang attribute"""
        html_tag = self.soup.find('html')
        if html_tag and html_tag.has_attr('lang'):
            lang = html_tag['lang'].lower()
            # Extract primary language code (e.g., 'en' from 'en-US')
            lang_code = lang.split('-')[0][:2]
            logger.debug(f"HTML lang attribute: {lang_code}")
            return lang_code
        return None
    
    def _detect_from_meta_tags(self) -> Optional[str]:
        """Detect from meta tags"""
        # Check Content-Language meta tag
        meta_lang = self.soup.find('meta', attrs={'http-equiv': re.compile(r'content-language', re.I)})
        if meta_lang and meta_lang.has_attr('content'):
            lang = meta_lang['content'].lower()
            lang_code = lang.split('-')[0].split(',')[0].strip()[:2]
            logger.debug(f"Meta Content-Language: {lang_code}")
            return lang_code
        
        # Check name="language" meta tag
        meta_lang = self.soup.find('meta', attrs={'name': 'language'})
        if meta_lang and meta_lang.has_attr('content'):
            lang = meta_lang['content'].lower()
            lang_code = lang.split('-')[0][:2]
            logger.debug(f"Meta language: {lang_code}")
            return lang_code
        
        return None
    
    def _detect_from_url(self) -> Optional[str]:
        """Detect from URL patterns"""
        if not self.url:
            return None
        
        url_lower = self.url.lower()
        
        # Common URL patterns: /en/, /es/, ?lang=en, .es/, en.example.com
        patterns = [
            r'/([a-z]{2})/',  # /en/
            r'[?&]lang=([a-z]{2})',  # ?lang=en
            r'\.([a-z]{2})/',  # .es/
            r'//([a-z]{2})\.',  # //en.example.com
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url_lower)
            if match:
                lang_code = match.group(1)
                # Verify it's a valid language code (in our common words list or char patterns)
                if lang_code in self.COMMON_WORDS or lang_code in self.CHAR_PATTERNS:
                    logger.debug(f"URL pattern detected: {lang_code}")
                    return lang_code
        
        return None
    
    def _detect_from_character_patterns(self) -> Optional[str]:
        """Detect from character frequency patterns"""
        # Get visible text
        text = self._get_visible_text()
        
        if not text or len(text) < 50:
            return None
        
        # Check for language-specific characters
        for lang, pattern in self.CHAR_PATTERNS.items():
            matches = pattern.findall(text)
            if matches:
                ratio = len(matches) / len(text)
                if ratio > 0.05:  # At least 5% of characters are language-specific
                    logger.debug(f"Character pattern detected: {lang} (ratio: {ratio:.2%})")
                    return lang
        
        return None
    
    def _detect_from_common_words(self) -> List[Tuple[str, float]]:
        """Detect from common words frequency"""
        text = self._get_visible_text().lower()
        
        if not text or len(text) < 100:
            return []
        
        # Split into words
        words = re.findall(r'\b\w+\b', text)
        if len(words) < 20:
            return []
        
        # Count matches for each language
        lang_scores = {}
        
        for lang, common_words in self.COMMON_WORDS.items():
            matches = sum(1 for word in words if word in common_words)
            score = matches / len(words)
            if score > 0.01:  # At least 1% match
                lang_scores[lang] = score
        
        # Sort by score
        sorted_langs = sorted(lang_scores.items(), key=lambda x: x[1], reverse=True)
        
        if sorted_langs:
            logger.debug(f"Common words detected: {sorted_langs[0][0]} (score: {sorted_langs[0][1]:.2%})")
        
        return sorted_langs
    
    def _detect_from_title_meta(self) -> Optional[str]:
        """Detect from title and meta description"""
        # Get title and meta description
        title = ''
        title_tag = self.soup.find('title')
        if title_tag:
            title = title_tag.get_text(strip=True)
        
        meta_desc = ''
        meta_tag = self.soup.find('meta', attrs={'name': 'description'})
        if meta_tag and meta_tag.has_attr('content'):
            meta_desc = meta_tag['content']
        
        combined_text = (title + ' ' + meta_desc).lower()
        
        if len(combined_text) < 10:
            return None
        
        # Check for character patterns
        for lang, pattern in self.CHAR_PATTERNS.items():
            if pattern.search(combined_text):
                return lang
        
        # Check for common words
        words = re.findall(r'\b\w+\b', combined_text)
        if len(words) < 5:
            return None
        
        best_lang = None
        best_score = 0
        
        for lang, common_words in self.COMMON_WORDS.items():
            matches = sum(1 for word in words if word in common_words)
            score = matches / len(words)
            if score > best_score:
                best_score = score
                best_lang = lang
        
        if best_score > 0.1:  # At least 10% match
            return best_lang
        
        return None
    
    def _get_visible_text(self) -> str:
        """Extract visible text from HTML"""
        # Remove script and style elements
        for script in self.soup(['script', 'style', 'meta', 'noscript']):
            script.decompose()
        
        text = self.soup.get_text()
        
        # Clean up whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ' '.join(chunk for chunk in chunks if chunk)
        
        return text
    
    def _combine_detections(self) -> Tuple[str, float, List[Tuple[str, float]]]:
        """
        Combine all detection methods with weighted voting.
        
        Returns:
            (primary_language, confidence, all_detections)
        """
        if not self.detection_methods:
            return ('unknown', 0.0, [])
        
        # Weights for different methods
        weights = {
            'html_lang': 3.0,      # High weight - explicit declaration
            'meta_tags': 2.5,      # High weight - explicit declaration
            'url': 2.0,            # Medium-high weight - explicit in URL
            'characters': 2.5,     # High weight - strong indicator
            'common_words': 2.0,   # Medium-high weight - content-based
            'title_meta': 1.5      # Medium weight - important content
        }
        
        # Count votes with weights
        votes = Counter()
        total_weight = 0
        
        for method, lang in self.detection_methods.items():
            weight = weights.get(method, 1.0)
            votes[lang] += weight
            total_weight += weight
        
        if not votes:
            return ('unknown', 0.0, [])
        
        # Get primary language (most votes)
        primary_lang, primary_votes = votes.most_common(1)[0]
        
        # Calculate confidence
        confidence = primary_votes / total_weight if total_weight > 0 else 0
        
        # Boost confidence if multiple methods agree
        num_methods = len(self.detection_methods)
        if num_methods >= 3:
            confidence = min(confidence * 1.2, 1.0)
        
        # Get all detections sorted by votes
        all_detections = [
            (lang, votes_count / total_weight)
            for lang, votes_count in votes.most_common()
        ]
        
        return (primary_lang, confidence, all_detections)
    
    def detect_multilingual(self) -> Dict[str, float]:
        """
        Detect if page contains multiple languages.
        
        Returns:
            Dictionary of language codes to confidence scores
        """
        text = self._get_visible_text()
        
        if not text or len(text) < 100:
            return {}
        
        languages = {}
        
        # Check character patterns
        for lang, pattern in self.CHAR_PATTERNS.items():
            matches = pattern.findall(text)
            if matches:
                ratio = len(matches) / len(text)
                if ratio > 0.03:  # At least 3% presence
                    languages[lang] = ratio
        
        # Check common words
        words = re.findall(r'\b\w+\b', text.lower())
        if len(words) >= 20:
            for lang, common_words in self.COMMON_WORDS.items():
                if lang in languages:  # Already detected via characters
                    continue
                matches = sum(1 for word in words if word in common_words)
                ratio = matches / len(words)
                if ratio > 0.05:  # At least 5% match
                    languages[lang] = ratio
        
        return languages


def detect_language(html_content: str, url: str = "") -> LanguageDetection:
    """
    Convenience function to detect language.
    
    Args:
        html_content: HTML content
        url: URL of the page
        
    Returns:
        LanguageDetection object
    """
    detector = LanguageDetector(html_content, url)
    return detector.detect()




