# -*- coding: utf-8 -*-
"""
Model Router for Dual-LLM Strategy (Qwen 7B + 14B)
Intelligently routes queries between:
- Qwen 2.5 7B (port 1234): Fast banking queries, greetings, simple operations
- Qwen 2.5 14B (port 1235): Complex analysis, RAG questions, multi-step reasoning
"""

from typing import Dict, Any
import re


class ModelRouter:
    """
    Routes queries to appropriate model based on complexity.

    Strategy:
    - Qwen 7B (fast): Simple banking queries, greetings, quick responses
    - Qwen 14B (quality): Complex analysis, RAG, ambiguous intents, multi-step reasoning
    """

    # ==========================================================================
    # QWEN 14B - Complex tasks requiring quality reasoning
    # ==========================================================================
    COMPLEX_INTENTS = {
        'CODE_ASSIST',           # Code assistance
        'SIMULATION_CREDIT',     # Credit simulations (calculations)
        'UNKNOWN',               # Unclear intent - needs better understanding
        'DEMANDE_AIDE',          # Help requests
        'RAG_QUESTION',          # Questions requiring document search
        'ANALYSE_JURIDIQUE',     # Legal analysis
    }

    # ==========================================================================
    # QWEN 7B - Fast simple tasks (DEFAULT)
    # ==========================================================================
    SIMPLE_INTENTS = {
        'CONSULTER_SOLDE',       # Check balance
        'FAIRE_VIREMENT',        # Make transfer
        'OBTENIR_RELEVE',        # Get statement
        'SALUTATION',            # Greetings (formal)
        'GREETING',              # Greetings (informal)
        'REMERCIEMENT',          # Thanks
        'SWITCH_MODE',           # Mode switching
        'DISCUSSION_COMPTE',     # Account discussion
        'OTHER',                 # General conversation
    }

    # Complexity indicators in query text
    COMPLEXITY_INDICATORS = [
        r'\b(pourquoi|comment|explique|analyse|compare|détaille)\b',
        r'\b(complexe|difficile|approfondi|détaillé)\b',
        r'\b(plusieurs|multiple|tous les|toutes les)\b',
        r'\b(si.*alors|dans le cas où|dépend de)\b',  # Conditional logic
    ]

    def __init__(self, fast_model: str = "qwen2.5-7b-instruct", quality_model: str = "qwen2.5-14b-instruct"):
        """
        Initialize model router.

        Args:
            fast_model: Model name for fast queries (Qwen 7B)
            quality_model: Model name for quality queries (Qwen 14B)
        """
        self.fast_model = fast_model
        self.quality_model = quality_model

    def route(self, intent: str, query: str, confidence: float, mode: str) -> Dict[str, Any]:
        """
        Determine which model to use for this query.

        Args:
            intent: Detected intent
            query: User query text
            confidence: Intent detection confidence (0-1)
            mode: Current conversation mode

        Returns:
            Dict with 'model' and 'reason'
        """
        reasons = []

        # 1. Check intent complexity
        if intent in self.COMPLEX_INTENTS:
            reasons.append(f"Complex intent: {intent}")
            return {
                'model': self.quality_model,
                'reason': ' | '.join(reasons),
                'strategy': 'intent_based'
            }

        if intent in self.SIMPLE_INTENTS:
            # Even simple intents might need quality model if confidence is low
            if confidence < 0.7:
                reasons.append(f"Low confidence ({confidence:.2f}) on simple intent")
                return {
                    'model': self.quality_model,
                    'reason': ' | '.join(reasons),
                    'strategy': 'confidence_based'
                }
            reasons.append(f"Simple intent with high confidence")
            return {
                'model': self.fast_model,
                'reason': ' | '.join(reasons),
                'strategy': 'intent_based'
            }

        # 2. Check query complexity
        query_lower = query.lower()
        complexity_score = 0

        for pattern in self.COMPLEXITY_INDICATORS:
            if re.search(pattern, query_lower, re.IGNORECASE):
                complexity_score += 1

        if complexity_score > 0:
            reasons.append(f"Complex query patterns detected ({complexity_score})")
            return {
                'model': self.quality_model,
                'reason': ' | '.join(reasons),
                'strategy': 'query_complexity'
            }

        # 3. Check query length (very long queries need more reasoning)
        if len(query.split()) > 20:
            reasons.append(f"Long query ({len(query.split())} words)")
            return {
                'model': self.quality_model,
                'reason': ' | '.join(reasons),
                'strategy': 'query_length'
            }

        # 4. Check confidence threshold
        if confidence < 0.65:
            reasons.append(f"Low confidence ({confidence:.2f})")
            return {
                'model': self.quality_model,
                'reason': ' | '.join(reasons),
                'strategy': 'confidence_based'
            }

        # 5. Mode-based routing
        if mode == 'coding':
            reasons.append(f"Coding mode requires quality model")
            return {
                'model': self.quality_model,
                'reason': ' | '.join(reasons),
                'strategy': 'mode_based'
            }

        # Default: Use fast model for banking queries
        reasons.append("Simple banking query")
        return {
            'model': self.fast_model,
            'reason': ' | '.join(reasons),
            'strategy': 'default'
        }

    def get_model_info(self, model_name: str) -> Dict[str, Any]:
        """Get information about a model."""
        if model_name == self.fast_model or 'mistral' in model_name.lower() or '7b' in model_name.lower():
            return {
                'name': model_name,
                'speed': 'Fast (~2-4s)',
                'quality': 'Good',
                'vram_gb': '4-5',
                'use_case': 'Banking queries, greetings, simple operations'
            }
        elif model_name == self.quality_model or '14b' in model_name.lower():
            return {
                'name': model_name,
                'speed': 'Moderate (~5-10s)',
                'quality': 'Excellent',
                'vram_gb': '8-10',
                'use_case': 'Complex analysis, RAG, credit simulations'
            }
        else:
            return {
                'name': model_name,
                'speed': 'Unknown',
                'quality': 'Unknown',
                'vram_gb': 'Unknown',
                'use_case': 'Unknown'
            }
