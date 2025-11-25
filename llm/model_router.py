# -*- coding: utf-8 -*-
"""
Model Router for Dual-LLM Strategy
Intelligently routes queries between:
- DeepSeek-R1-Distill-14B: Fast banking queries, calculations
- Qwen 2.5 32B: Complex analysis, GPT-4 level reasoning
"""

from typing import Dict, Any
import re


class ModelRouter:
    """
    Routes queries to appropriate model based on complexity.

    Strategy:
    - DeepSeek (fast): Simple banking queries, calculations, quick responses
    - Qwen 32B (quality): Complex analysis, ambiguous intents, multi-step reasoning
    """

    # Intents that require high-quality reasoning (use Qwen 32B)
    COMPLEX_INTENTS = {
        'CODE_ASSIST',
        'SIMULATION_CREDIT',
        'UNKNOWN',
        'DEMANDE_AIDE',
    }

    # Intents that are fast and simple (use DeepSeek)
    SIMPLE_INTENTS = {
        'CONSULTER_SOLDE',
        'FAIRE_VIREMENT',
        'OBTENIR_RELEVE',
        'SALUTATION',
        'REMERCIEMENT',
        'SWITCH_MODE',
    }

    # Complexity indicators in query text
    COMPLEXITY_INDICATORS = [
        r'\b(pourquoi|comment|explique|analyse|compare|détaille)\b',
        r'\b(complexe|difficile|approfondi|détaillé)\b',
        r'\b(plusieurs|multiple|tous les|toutes les)\b',
        r'\b(si.*alors|dans le cas où|dépend de)\b',  # Conditional logic
    ]

    def __init__(self, fast_model: str = "deepseek-r1:14b", quality_model: str = "qwen2.5:32b-instruct"):
        """
        Initialize model router.

        Args:
            fast_model: Model name for fast queries (DeepSeek)
            quality_model: Model name for quality queries (Qwen 32B)
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
        if model_name == self.fast_model:
            return {
                'name': 'DeepSeek-R1-Distill-14B',
                'speed': 'Fast',
                'quality': 'Good',
                'vram_gb': '12-14',
                'use_case': 'Banking queries, calculations'
            }
        elif model_name == self.quality_model:
            return {
                'name': 'Qwen 2.5 32B',
                'speed': 'Moderate',
                'quality': 'Excellent (GPT-4 level)',
                'vram_gb': '22-23',
                'use_case': 'Complex analysis, reasoning'
            }
        else:
            return {
                'name': model_name,
                'speed': 'Unknown',
                'quality': 'Unknown',
                'vram_gb': 'Unknown',
                'use_case': 'Unknown'
            }
