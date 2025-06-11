#!/usr/bin/env python3
"""
keyword_extractor.py - Extract keywords from webpage content
"""

import re
import logging
import string
from collections import Counter
from typing import Dict, List, Optional
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

class KeywordExtractor:
    """Keyword extraction class for analyzing webpage content.
    
    This class provides methods to extract and rank keywords from HTML content,
    identifying the most relevant terms in the document.
    """
    
    # Common stop words to exclude from keyword analysis
    STOP_WORDS = set([
        "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", 
        "any", "are", "aren't", "as", "at", "be", "because", "been", "before", "being", 
        "below", "between", "both", "but", "by", "can't", "cannot", "could", "couldn't", 
        "did", "didn't", "do", "does", "doesn't", "doing", "don't", "down", "during", 
        "each", "few", "for", "from", "further", "had", "hadn't", "has", "hasn't", "have", 
        "haven't", "having", "he", "he'd", "he'll", "he's", "her", "here", "here's", 
        "hers", "herself", "him", "himself", "his", "how", "how's", "i", "i'd", "i'll", 
        "i'm", "i've", "if", "in", "into", "is", "isn't", "it", "it's", "its", "itself", 
        "let's", "me", "more", "most", "mustn't", "my", "myself", "no", "nor", "not", 
        "of", "off", "on", "once", "only", "or", "other", "ought", "our", "ours", 
        "ourselves", "out", "over", "own", "same", "shan't", "she", "she'd", "she'll", 
        "she's", "should", "shouldn't", "so", "some", "such", "than", "that", "that's", 
        "the", "their", "theirs", "them", "themselves", "then", "there", "there's", 
        "these", "they", "they'd", "they'll", "they're", "they've", "this", "those", 
        "through", "to", "too", "under", "until", "up", "very", "was", "wasn't", "we", 
        "we'd", "we'll", "we're", "we've", "were", "weren't", "what", "what's", "when", 
        "when's", "where", "where's", "which", "while", "who", "who's", "whom", "why", 
        "why's", "with", "won't", "would", "wouldn't", "you", "you'd", "you'll", 
        "you're", "you've", "your", "yours", "yourself", "yourselves"
    ])
    
    def __init__(self, min_word_length: int = 3, max_keywords: int = 20):
        """Initialize keyword extractor with customizable parameters.
        
        Args:
            min_word_length: Minimum length of words to consider as keywords
            max_keywords: Maximum number of keywords to extract
        """
        self.min_word_length = min_word_length
        self.max_keywords = max_keywords
    
    def extract_text_from_html(self, html_content: str) -> str:
        """Extract readable text content from HTML, focusing on relevant sections.
        
        Args:
            html_content: The raw HTML content
        
        Returns:
            Extracted text with HTML tags and scripts removed
        """
        # Parse HTML with BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Remove unwanted elements
        for element in soup.find_all(['script', 'style', 'footer', 'nav']):
            element.decompose()
        
        # Build text with priority weighting
        extracted_text = []
        
        # Extract title text (with higher weight)
        title_element = soup.find('title')
        if title_element and title_element.text.strip():
            extracted_text.extend([title_element.text.strip()] * 3)  # Title has higher weight
        
        # Extract h1 text (with higher weight)
        h1_elements = soup.find_all('h1')
        if h1_elements:
            h1_texts = [h1.get_text().strip() for h1 in h1_elements if h1.get_text().strip()]
            extracted_text.extend(h1_texts * 2)  # H1 has higher weight
        
        # Extract h2 text
        h2_elements = soup.find_all('h2')
        if h2_elements:
            h2_texts = [h2.get_text().strip() for h2 in h2_elements if h2.get_text().strip()]
            extracted_text.extend(h2_texts)
        
        # Extract h3 text
        h3_elements = soup.find_all('h3')
        if h3_elements:
            h3_texts = [h3.get_text().strip() for h3 in h3_elements if h3.get_text().strip()]
            extracted_text.extend(h3_texts)
        
        # Extract paragraph text
        p_elements = soup.find_all('p')
        if p_elements:
            p_texts = [p.get_text().strip() for p in p_elements if p.get_text().strip()]
            extracted_text.extend(p_texts)
        
        # If specific tag extraction failed, try a more aggressive approach
        if not extracted_text:
            logger.debug("Specific tag extraction failed, trying fallback content extraction")
            body_element = soup.find('body')
            if body_element:
                extracted_text = [body_element.get_text().strip()]
            else:
                # Final fallback: get all text from the document
                extracted_text = [soup.get_text().strip()]
        
        # Join all extracted text and normalize whitespace
        text = ' '.join(extracted_text)
        clean_text = re.sub(r'\s+', ' ', text).strip()  # Normalize whitespace
        
        return clean_text
    
    def tokenize_text(self, text: str) -> List[str]:
        """Convert text into a list of valid tokens/words.
        
        Args:
            text: The text to tokenize
        
        Returns:
            List of valid tokens
        """
        # Convert to lowercase and remove punctuation
        text = text.lower()
        text = text.translate(str.maketrans('', '', string.punctuation))
        
        # Split into words
        words = text.split()
        
        # Filter words
        valid_words = [
            word for word in words 
            if len(word) >= self.min_word_length 
            and word not in self.STOP_WORDS
            and not word.isdigit()
        ]
        
        return valid_words
    
    def extract_keywords(self, html_content: str, include_scores: bool = False) -> Dict:
        """Extract keywords from HTML content.
        
        Args:
            html_content: The raw HTML content
            include_scores: Whether to include frequency scores in the result
            
        Returns:
            Dictionary containing the extracted keywords and their scores (if requested)
        """
        # Extract text from HTML
        text = self.extract_text_from_html(html_content)
        
        # Tokenize text
        tokens = self.tokenize_text(text)
        
        if not tokens:
            logger.warning("No valid tokens found in the content")
            return {"keywords": []} if not include_scores else {"keywords": [], "scores": {}}
            
        # Skip keyword extraction for very minimal content (less than 10 words)
        raw_word_count = len(text.split())
        if raw_word_count < 10:
            logger.debug(f"Content too small for keyword extraction ({raw_word_count} words)")
            return {"keywords": []} if not include_scores else {"keywords": [], "scores": {}}
        
        # Count frequencies
        word_freq = Counter(tokens)
        
        # Get top keywords
        top_keywords = [word for word, _ in word_freq.most_common(self.max_keywords)]
        
        # Format result based on whether scores should be included
        if include_scores:
            scores = {word: count/len(tokens) for word, count in word_freq.most_common(self.max_keywords)}
            return {
                "keywords": top_keywords,
                "scores": scores
            }
        else:
            return {
                "keywords": top_keywords
            }
    
    def extract_keyphrases(self, html_content: str, max_phrase_words: int = 3, 
                          min_phrase_freq: int = 2) -> List[str]:
        """Extract multi-word keyphrases from HTML content.
        
        Args:
            html_content: The raw HTML content
            max_phrase_words: Maximum number of words in a keyphrase
            min_phrase_freq: Minimum frequency for a phrase to be considered
            
        Returns:
            List of extracted keyphrases
        """
        # Extract text from HTML using BeautifulSoup (via extract_text_from_html)
        text = self.extract_text_from_html(html_content)
        
        # Skip keyphrase extraction for very minimal content (less than 10 words)
        raw_word_count = len(text.split())
        if raw_word_count < 10:
            logger.debug(f"Content too small for keyphrase extraction ({raw_word_count} words)")
            return []
        
        # Clean and normalize text
        text = text.lower()
        text = re.sub(r'[^\w\s]', '', text)  # Remove punctuation but preserve spaces
        
        # Split into words
        words = text.split()
        
        # Filter out stop words
        filtered_words = [word for word in words if word not in self.STOP_WORDS and len(word) >= 3]
        
        # Generate n-grams (phrases)
        phrases = []
        for i in range(len(filtered_words)):
            for n in range(1, min(max_phrase_words+1, len(filtered_words)-i+1)):
                phrase = ' '.join(filtered_words[i:i+n])
                phrases.append(phrase)
        
        # Count phrase frequencies
        phrase_freq = Counter(phrases)
        
        # Filter phrases by frequency
        common_phrases = [phrase for phrase, freq in phrase_freq.items() 
                         if freq >= min_phrase_freq and ' ' in phrase]
        
        # Sort by length (longer phrases first) and frequency
        common_phrases.sort(key=lambda x: (len(x.split()), phrase_freq[x]), reverse=True)
        
        # Return top phrases (no duplicates)
        unique_phrases = []
        for phrase in common_phrases:
            if not any(phrase in existing for existing in unique_phrases):
                unique_phrases.append(phrase)
            
            if len(unique_phrases) >= self.max_keywords:
                break
                
        return unique_phrases
