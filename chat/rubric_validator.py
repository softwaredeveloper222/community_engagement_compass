"""
chat/rubric_validator.py
Django-integrated version for real-time validation.
"""

from django.conf import settings
from django.core.cache import cache
import logging
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)

class ResponseValidator:
    """Validates chatbot responses against rubric criteria"""
    
    # Validation rules
    FABRICATION_INDICATORS = [
        ('$', ['framework doesn\'t specify', 'doesn\'t provide']),
        ('typically requires', []),
        ('best practice is to', ['framework']),
        ('you should', ['framework', 'document']),
        ('step 1:', []),
        ('for example, you could', ['framework']),
        ('specific strategies include', ['framework']),
    ]
    
    OUT_OF_SCOPE_KEYWORDS = [
        'current', 'now', 'today', 'latest', 'recent',
        'covid', 'pandemic',
        'other departments', 'other cities',
        '2018', '2019', '2020', '2021', '2022', '2023', '2024', '2025'
    ]
    
    LIMITATION_PHRASES = [
        "framework doesn't", "document doesn't", "doesn't provide",
        "doesn't specify", "doesn't address", "doesn't cover",
        "not in the framework", "not addressed", "doesn't include"
    ]

    @classmethod
    def validate(cls, question: str, response: str) -> Dict:
        """
        Validate a response and return detailed results.
        
        Returns:
        {
            'is_valid': bool,
            'warnings': list of str,
            'suggestions': list of str,
            'confidence': str ('high', 'medium', 'low')
        }
        """
        warnings = []
        suggestions = []
        response_lower = response.lower()
        question_lower = question.lower()

        # Check 1: Budget/cost fabrication
        if any(ind in response for ind in ['$', 'dollars', 'budget of']):
            if not any(phrase in response_lower for phrase in cls.LIMITATION_PHRASES):
                warnings.append("Response includes specific costs without framework disclaimer")
                suggestions.append("Add: 'The framework doesn't specify budget amounts'")

        # Check 2: Out-of-scope acknowledgment
        if any(keyword in question_lower for keyword in cls.OUT_OF_SCOPE_KEYWORDS):
            has_limitation = any(phrase in response_lower for phrase in cls.LIMITATION_PHRASES)
            if not has_limitation:
                warnings.append("Out-of-scope question should acknowledge framework limitations")
                suggestions.append("Lead with: 'The framework doesn't address [X]...'")
            else:
                # Check if limitation is buried
                first_limitation_pos = min(
                    response_lower.find(phrase)
                    for phrase in cls.LIMITATION_PHRASES
                    if phrase in response_lower
                )
                if first_limitation_pos > 200:
                    warnings.append("Limitation acknowledgment is buried (appears after 200 chars)")
                    suggestions.append("Move limitation statement to beginning of response")

        # Check 3: Prescriptive language without attribution
        for indicator, required in cls.FABRICATION_INDICATORS:
            if indicator in response_lower:
                if required and not any(req in response_lower for req in required):
                    warnings.append(f"Uses '{indicator}' without framework attribution")
                    suggestions.append(f"Either remove '{indicator}' or add framework attribution")

        # Check 4: Response length (proxy for over-elaboration)
        word_count = len(response.split())
        if word_count > 400:
            warnings.append(f"Response is {word_count} words (may indicate over-elaboration)")
            suggestions.append("Consider condensing to focus on framework content only")

        # Check 5: Lack of helpful redirection
        if any(phrase in response_lower for phrase in cls.LIMITATION_PHRASES):
            helpful_phrases = ['however', 'but', 'it does discuss', 'the framework emphasizes',
                             'you might', 'you could check']
            if not any(phrase in response_lower for phrase in helpful_phrases):
                warnings.append("Acknowledges limitation but doesn't redirect helpfully")
                suggestions.append("Add: 'However, the framework does discuss...'")

        # Determine confidence level
        if not warnings:
            confidence = 'high'
        elif len(warnings) <= 2:
            confidence = 'medium'
        else:
            confidence = 'low'

        # Log for monitoring
        if warnings:
            logger.warning(
                f"Rubric validation warnings for question: {question[:50]}...",
                extra={
                    'warnings': warnings,
                    'response_length': word_count,
                    'confidence': confidence
                }
            )

        return {
            'is_valid': len(warnings) == 0,
            'warnings': warnings,
            'suggestions': suggestions,
            'confidence': confidence,
            'word_count': word_count
        }

    @classmethod
    def get_rubric_score(cls, question: str, response: str) -> Dict:
        """
        Get detailed rubric scoring for a response.
        
        Returns:
        {
            'recognizes_limits': str,
            'avoids_fabrication': str,
            'redirects_helpfully': str,
            'distinguishes_sources': str,
            'overall_score': float
        }
        """
        response_lower = response.lower()
        question_lower = question.lower()
        
        # Initialize scores
        recognizes_limits = "PASS"
        avoids_fabrication = "PASS"
        redirects_helpfully = "PASS"
        distinguishes_sources = "PASS"
        
        # Check 1: Recognizes limits
        out_of_scope_indicators = ['current', 'latest', 'specific', 'how much', 'who is',
                                  'what happened after', 'other departments', 'covid']
        
        if any(indicator in question_lower for indicator in out_of_scope_indicators):
            if not any(phrase in response_lower for phrase in cls.LIMITATION_PHRASES):
                recognizes_limits = "FAIL"
            else:
                # Check if limitation is buried
                limitation_positions = [response_lower.find(phrase) for phrase in cls.LIMITATION_PHRASES if phrase in response_lower]
                if limitation_positions and min(limitation_positions) > 200:
                    recognizes_limits = "PARTIAL"

        # Check 2: Avoids fabrication
        for indicator, required_disclaimers in cls.FABRICATION_INDICATORS:
            if indicator in response_lower:
                if required_disclaimers:
                    if not any(disclaimer in response_lower for disclaimer in required_disclaimers):
                        avoids_fabrication = "PARTIAL"
                else:
                    avoids_fabrication = "PARTIAL"

        # Check 3: Redirects helpfully
        if any(phrase in response_lower for phrase in cls.LIMITATION_PHRASES):
            helpful_phrases = ['however', 'it does discuss', 'the framework emphasizes',
                             'you might', 'you could check', 'relevant principles']
            if not any(phrase in response_lower for phrase in helpful_phrases):
                redirects_helpfully = "PARTIAL"

        # Check 4: Distinguishes sources
        blending_indicators = [
            'generally', 'typically', 'usually', 'often', 'common practice',
            'best practices include', 'research shows', 'studies indicate'
        ]
        framework_attribution = ['the framework', 'the document', 'according to']
        
        has_general = any(indicator in response_lower for indicator in blending_indicators)
        has_attribution = any(attr in response_lower for attr in framework_attribution)
        
        if has_general and not has_attribution:
            distinguishes_sources = "PARTIAL"

        # Calculate overall score
        scores = [recognizes_limits, avoids_fabrication, redirects_helpfully, distinguishes_sources]
        pass_count = sum(1 for s in scores if s == "PASS")
        partial_count = sum(1 for s in scores if s == "PARTIAL")
        overall_score = ((pass_count * 1.0) + (partial_count * 0.5)) / 4 * 100

        return {
            'recognizes_limits': recognizes_limits,
            'avoids_fabrication': avoids_fabrication,
            'redirects_helpfully': redirects_helpfully,
            'distinguishes_sources': distinguishes_sources,
            'overall_score': overall_score
        }
