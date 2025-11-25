# core/knowledge_router.py

import re
from typing import Dict, List, Optional
from intents import BaseIntent, IntentType


class KnowledgeRouter:
    """
    Routes requests to appropriate knowledge sources

    Decides which sources to use based on:
    1. Intent type (transactional/informational)
    2. Explicit user requests ("cherche sur Google", "dans nos docs")
    3. Message content analysis
    4. Intent-specific routing logic

    Routing strategies:
    - transactional: Backend only (virement, solde, relevé)
    - rag: Internal docs only (policies, procedures, FAQ)
    - web: Web search only (news, rates, public info)
    - hybrid: Multiple sources (complex questions, comparisons)
    """

    def __init__(self, enable_rag: bool = True, enable_web: bool = True):
        """
        Initialize router

        Args:
            enable_rag: Enable RAG (internal docs) routing
            enable_web: Enable web search routing
        """
        self.enable_rag = enable_rag
        self.enable_web = enable_web

        # Explicit web request patterns
        self.web_request_patterns = [
            r'\b(cherche|recherche|google|trouve)\b.*\b(sur|dans|via)\b.*\b(web|internet|google)\b',
            r'\b(google|internet)\b',
            r'\brecherche\s+(web|internet)\b',
            r'\bsur\s+(google|le\s+web|internet)\b',
        ]

        # Explicit internal docs request patterns
        self.rag_request_patterns = [
            r'\b(dans|selon)\b.*\b(nos|vos)\b.*\b(docs|documents|politiques|procédures)\b',
            r'\bpolitique\s+(interne|de\s+la\s+banque)\b',
            r'\bprocédure\s+(interne|AFG|DBS)\b',
            r'\brèglement\s+interne\b',
            r'\bdocumentation\s+interne\b',
        ]

        # Keywords suggesting web search
        self.web_keywords = [
            'actualité', 'news', 'nouveau', 'récent', 'aujourd\'hui',
            'taux de change', 'cours', 'marché', 'bourse',
            'crypto', 'bitcoin', 'blockchain',
            'comparaison', 'meilleur', 'top', 'classement',
        ]

        # Keywords suggesting internal docs
        self.rag_keywords = [
            'politique', 'procédure', 'règlement', 'norme',
            'guide', 'manuel', 'documentation',
            'afg', 'dbs', 'interne', 'banque',
            'conformité', 'compliance', 'audit',
        ]

    def route(
        self,
        intent: BaseIntent,
        message: str,
        slots: Dict
    ) -> Dict[str, any]:
        """
        Route request to appropriate sources

        Args:
            intent: Intent instance
            message: User message
            slots: Extracted slots

        Returns:
            Dict with:
            - strategy: str (transactional|rag|web|hybrid)
            - tools_to_use: List[str] (backend, rag, web_search, etc.)
            - reasoning: str (explanation of routing decision)
        """
        message_lower = message.lower()

        # Step 1: Check for explicit user requests
        explicit_web = self._is_explicit_web_request(message_lower)
        explicit_rag = self._is_explicit_rag_request(message_lower)

        if explicit_web and self.enable_web:
            return {
                'strategy': 'web',
                'tools_to_use': ['web_search'],
                'reasoning': 'User explicitly requested web search'
            }

        if explicit_rag and self.enable_rag:
            return {
                'strategy': 'rag',
                'tools_to_use': ['rag_search'],
                'reasoning': 'User explicitly requested internal documentation'
            }

        # Step 2: Use intent-specific routing if defined
        intent_type = intent.route(message, slots)

        # Step 3: Route based on intent type
        if intent_type == IntentType.TRANSACTIONAL:
            return {
                'strategy': 'transactional',
                'tools_to_use': ['backend'],
                'reasoning': 'Transactional intent - backend only'
            }

        elif intent_type == IntentType.INFORMATIONAL_INTERNAL:
            if self.enable_rag:
                return {
                    'strategy': 'rag',
                    'tools_to_use': ['rag_search'],
                    'reasoning': 'Informational intent - internal docs'
                }
            else:
                # Fallback to web if RAG disabled
                return {
                    'strategy': 'web',
                    'tools_to_use': ['web_search'],
                    'reasoning': 'RAG disabled - fallback to web'
                }

        elif intent_type == IntentType.INFORMATIONAL_EXTERNAL:
            if self.enable_web:
                return {
                    'strategy': 'web',
                    'tools_to_use': ['web_search'],
                    'reasoning': 'Informational intent - external sources'
                }
            else:
                # Fallback to RAG if web disabled
                return {
                    'strategy': 'rag',
                    'tools_to_use': ['rag_search'],
                    'reasoning': 'Web disabled - fallback to RAG'
                }

        elif intent_type == IntentType.HYBRID:
            # Hybrid: use multiple sources
            tools = []

            # Always include backend if intent has backend tools
            if 'backend' in intent.tools:
                tools.append('backend')

            # Add RAG if enabled and relevant
            if self.enable_rag and self._is_rag_relevant(message_lower):
                tools.append('rag_search')

            # Add web if enabled and relevant
            if self.enable_web and self._is_web_relevant(message_lower):
                tools.append('web_search')

            # If no tools selected, use default based on keywords
            if not tools:
                if self._count_keywords(message_lower, self.rag_keywords) > self._count_keywords(message_lower, self.web_keywords):
                    tools = ['rag_search']
                else:
                    tools = ['web_search']

            return {
                'strategy': 'hybrid',
                'tools_to_use': tools,
                'reasoning': f'Hybrid intent - using {len(tools)} source(s)'
            }

        # Default: transactional
        return {
            'strategy': 'transactional',
            'tools_to_use': ['backend'],
            'reasoning': 'Default routing - backend'
        }

    def _is_explicit_web_request(self, message_lower: str) -> bool:
        """Check if user explicitly requested web search"""
        for pattern in self.web_request_patterns:
            if re.search(pattern, message_lower):
                return True
        return False

    def _is_explicit_rag_request(self, message_lower: str) -> bool:
        """Check if user explicitly requested internal docs"""
        for pattern in self.rag_request_patterns:
            if re.search(pattern, message_lower):
                return True
        return False

    def _is_web_relevant(self, message_lower: str) -> bool:
        """Check if web search is relevant for this message"""
        return self._count_keywords(message_lower, self.web_keywords) > 0

    def _is_rag_relevant(self, message_lower: str) -> bool:
        """Check if RAG is relevant for this message"""
        return self._count_keywords(message_lower, self.rag_keywords) > 0

    def _count_keywords(self, text: str, keywords: List[str]) -> int:
        """Count how many keywords appear in text"""
        count = 0
        for keyword in keywords:
            if keyword in text:
                count += 1
        return count

    def should_use_rag(self, routing: Dict) -> bool:
        """Check if RAG should be used based on routing decision"""
        return 'rag_search' in routing['tools_to_use']

    def should_use_web(self, routing: Dict) -> bool:
        """Check if web search should be used"""
        return 'web_search' in routing['tools_to_use']

    def should_use_backend(self, routing: Dict) -> bool:
        """Check if backend should be used"""
        return 'backend' in routing['tools_to_use']

    def format_routing_info(self, routing: Dict) -> str:
        """Format routing information for debugging"""
        return f"""
🎯 Routing Decision:
   Strategy: {routing['strategy']}
   Tools: {', '.join(routing['tools_to_use'])}
   Reason: {routing['reasoning']}
"""


# Test function
if __name__ == "__main__":
    from intents import IntentType

    # Mock intent for testing
    class MockIntent(BaseIntent):
        name = "TEST"
        description = "Test intent"
        intent_type = IntentType.HYBRID
        tools = ["backend", "rag_search", "web_search"]
        examples = []
        keywords = []
        slots = {}

        def execute(self, slots, context):
            pass

        def format_response(self, result, slots):
            pass

    router = KnowledgeRouter()
    intent = MockIntent()

    # Test cases
    test_cases = [
        "quel est mon solde ?",  # Transactional
        "cherche sur Google le taux de change",  # Explicit web
        "quelle est notre politique de crédit ?",  # RAG
        "compare les taux d'intérêt actuels",  # Hybrid
        "dans nos documents, quelle est la procédure KYC ?",  # Explicit RAG
    ]

    for message in test_cases:
        print(f"\n{'='*60}")
        print(f"Message: {message}")
        routing = router.route(intent, message, {})
        print(router.format_routing_info(routing))
