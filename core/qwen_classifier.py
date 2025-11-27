# -*- coding: utf-8 -*-
"""
QWEN #1 CLASSIFIER - Original Architecture Implementation

This module replaces embedding+rules with LLM-based classification.
Outputs: conversation_mode, flow_name, slots, needs_backend, needs_rag, needs_expert_model, reason

Architecture Flow:
User Input → Text Normalizer → Embedding Pre-Filter (top 3) → QWEN #1 CLASSIFIER → Route
"""

import json
import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass


@dataclass
class ClassificationResult:
    """Result from QWEN #1 classification"""
    conversation_mode: str  # RAG_QUESTION, BANKING_FLOW, GREETING, CHITCHAT, GENERAL_QUESTION, ASK_CAPABILITIES, UNKNOWN
    flow_name: Optional[str]  # Banking flow name if applicable
    slots: Dict[str, Any]  # Extracted slots from user message
    needs_backend: bool  # Requires backend API call
    needs_rag: bool  # Requires RAG retrieval
    needs_expert_model: bool  # Requires expert (larger) model
    reason: str  # Classification reasoning
    confidence: float  # Confidence score 0-1
    raw_response: str  # Raw LLM response for debugging


# Conversation modes
CONVERSATION_MODES = [
    "RAG_QUESTION",      # Questions requiring document lookup (tariffs, fees, policies)
    "BANKING_FLOW",      # Transactional banking operations (transfer, balance, statement)
    "GREETING",          # Greetings and salutations
    "CHITCHAT",          # Small talk, off-topic
    "GENERAL_QUESTION",  # General banking questions (no RAG needed)
    "ASK_CAPABILITIES",  # What can you do? type questions
    "UNKNOWN"           # Cannot classify
]


class QwenClassifier:
    """
    QWEN #1 CLASSIFIER

    Uses LLM to determine:
    - conversation_mode: What type of conversation this is
    - flow_name: Which banking flow to use (if applicable)
    - slots: Extracted parameters from user message
    - needs_backend: Whether backend API is required
    - needs_rag: Whether RAG retrieval is needed
    - needs_expert_model: Whether larger model is needed for response
    """

    def __init__(self, llm_client=None, text_normalizer=None, embedding_prefilter=None):
        """
        Initialize the classifier

        Args:
            llm_client: LLM client (DualModelLMStudio or OpenAIClient)
            text_normalizer: Text normalizer for preprocessing
            embedding_prefilter: Optional embedding model for pre-filtering flows
        """
        self.llm_client = llm_client
        self.text_normalizer = text_normalizer
        self.embedding_prefilter = embedding_prefilter

        # Flow definitions for context
        self.flow_definitions = self._get_flow_definitions()

    def _get_flow_definitions(self) -> str:
        """Get formatted flow definitions for prompt context"""
        try:
            from core.flows import FLOWS
            lines = []
            for flow in FLOWS:
                lines.append(f"- {flow['name']}: {flow['description']}")
                if flow.get('slots'):
                    lines.append(f"  Slots requis: {', '.join(flow['slots'])}")
            return "\n".join(lines)
        except ImportError:
            return """
- CHECK_BALANCE: Consulter le solde du compte bancaire
- TRANSFER_MONEY: Effectuer un virement (slots: amount, currency, beneficiary_name)
- CREDIT_SIMULATION: Simuler un crédit (slots: amount, duration_months)
- ACCOUNT_HISTORY: Consulter l'historique des transactions
- GET_STATEMENT: Obtenir un relevé de compte
- OPEN_ACCOUNT: Expliquer comment ouvrir un compte
"""

    def _build_classification_prompt(
        self,
        user_message: str,
        normalized_message: str,
        top_flow_candidates: List[str],
        rag_document_summaries: List[str],
        session_context: Dict
    ) -> str:
        """Build the classification prompt for QWEN #1"""

        # Format flow candidates
        candidates_str = ", ".join(top_flow_candidates) if top_flow_candidates else "aucun"

        # Format RAG document context
        rag_context = ""
        if rag_document_summaries:
            rag_context = "\n".join([f"- {doc}" for doc in rag_document_summaries[:5]])
        else:
            rag_context = "Aucun document disponible"

        # Format session context
        session_str = ""
        if session_context:
            if session_context.get('current_flow'):
                session_str += f"Flow en cours: {session_context['current_flow']}\n"
            if session_context.get('last_intent'):
                session_str += f"Dernière intention: {session_context['last_intent']}\n"
            if session_context.get('pending_slots'):
                session_str += f"Slots manquants: {session_context['pending_slots']}\n"

        prompt = f"""Tu es le CLASSIFICATEUR d'un assistant bancaire AFG/DBS pour l'Afrique de l'Ouest.

Ta tâche est d'analyser le message client et déterminer:
1. Le MODE de conversation (RAG_QUESTION, BANKING_FLOW, GREETING, CHITCHAT, GENERAL_QUESTION, ASK_CAPABILITIES, UNKNOWN)
2. Le FLOW bancaire à utiliser (si applicable)
3. Les SLOTS (paramètres) extraits du message
4. Si le BACKEND est nécessaire
5. Si la recherche RAG est nécessaire
6. Si le modèle expert est nécessaire

=== MESSAGE CLIENT ===
Original: "{user_message}"
Normalisé: "{normalized_message}"

=== FLOWS CANDIDATS (pré-filtrage embedding) ===
{candidates_str}

=== FLOWS BANCAIRES DISPONIBLES ===
{self.flow_definitions}

=== DOCUMENTS RAG DISPONIBLES ===
{rag_context}

=== CONTEXTE SESSION ===
{session_str if session_str else "Nouvelle conversation"}

=== RÈGLES DE CLASSIFICATION ===

1. RAG_QUESTION (needs_rag=true):
   - Questions sur les tarifs, frais, conditions
   - Questions sur les politiques bancaires
   - Questions sur les documents officiels
   - Exemples: "frais de carte", "taux d'intérêt", "conditions ouverture compte"

2. BANKING_FLOW (needs_backend=true selon le flow):
   - Opérations bancaires concrètes
   - Extraire les slots du message
   - CHECK_BALANCE: consultation solde
   - TRANSFER_MONEY: slots [amount, currency, beneficiary_name]
   - CREDIT_SIMULATION: slots [amount, duration_months]
   - Exemples: "mon solde", "virer 50000 à Pierre", "simuler crédit 5 millions"

3. GREETING:
   - Salutations simples
   - Exemples: "bonjour", "salut", "bonsoir"

4. CHITCHAT:
   - Discussion hors sujet bancaire
   - Exemples: "quel temps fait-il", "raconte une blague"

5. GENERAL_QUESTION:
   - Questions générales sur la banque (pas besoin de RAG)
   - Exemples: "vous êtes ouvert quand", "où est l'agence"

6. ASK_CAPABILITIES:
   - Questions sur ce que l'assistant peut faire
   - Exemples: "que peux-tu faire", "quels services"

=== FORMAT DE RÉPONSE ===
Réponds UNIQUEMENT avec un objet JSON valide:
{{
  "conversation_mode": "MODE",
  "flow_name": "NOM_FLOW ou null",
  "slots": {{}},
  "needs_backend": false,
  "needs_rag": false,
  "needs_expert_model": false,
  "reason": "Explication courte"
}}

JSON:"""

        return prompt

    def _parse_llm_response(self, response: str) -> Dict:
        """Parse LLM response to extract JSON"""
        # Clean response
        response = response.strip()

        # Try to extract JSON from response
        # Sometimes LLM adds text before/after JSON
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            json_str = json_match.group()
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                pass

        # Try direct parse
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass

        # Return default if parsing fails
        return {
            "conversation_mode": "UNKNOWN",
            "flow_name": None,
            "slots": {},
            "needs_backend": False,
            "needs_rag": False,
            "needs_expert_model": False,
            "reason": "Erreur de parsing JSON"
        }

    def _call_llm(self, prompt: str) -> str:
        """Call LLM and return response string - ALWAYS uses 7B (fast model) for classification"""
        if self.llm_client is None:
            return "{}"

        try:
            # Handle different LLM client types
            if hasattr(self.llm_client, 'generate'):
                # QWEN #1 CLASSIFIER: Always use fast 7B model for classification
                # Use force_model parameter to skip routing logic entirely
                result = self.llm_client.generate(
                    prompt,
                    force_model=self.llm_client.fast_model_name,  # Force 7B
                    temperature=0.3,
                    max_tokens=300  # Reduced for faster classification
                )

                # Handle Dict response (DualModelLMStudio returns Dict)
                if isinstance(result, dict):
                    return result.get('response', '{}')
                return result

            # Direct API call fallback
            return "{}"

        except Exception as e:
            print(f"[QwenClassifier] LLM call error: {e}")
            return "{}"

    def classify(
        self,
        user_message: str,
        top_flow_candidates: List[str] = None,
        rag_document_summaries: List[str] = None,
        session_context: Dict = None
    ) -> ClassificationResult:
        """
        Classify user message using QWEN #1

        Args:
            user_message: Raw user message
            top_flow_candidates: Top 3 flow candidates from embedding pre-filter
            rag_document_summaries: List of available RAG document summaries
            session_context: Current session state

        Returns:
            ClassificationResult with all classification outputs
        """
        # Normalize message
        normalized = user_message.lower().strip()
        if self.text_normalizer:
            try:
                normalized = self.text_normalizer.normalize(user_message)
            except Exception:
                pass

        # Default values
        if top_flow_candidates is None:
            top_flow_candidates = []
        if rag_document_summaries is None:
            rag_document_summaries = []
        if session_context is None:
            session_context = {}

        # Build prompt
        prompt = self._build_classification_prompt(
            user_message=user_message,
            normalized_message=normalized,
            top_flow_candidates=top_flow_candidates,
            rag_document_summaries=rag_document_summaries,
            session_context=session_context
        )

        # Call LLM
        raw_response = self._call_llm(prompt)

        # Parse response
        parsed = self._parse_llm_response(raw_response)

        # Build result
        result = ClassificationResult(
            conversation_mode=parsed.get('conversation_mode', 'UNKNOWN'),
            flow_name=parsed.get('flow_name'),
            slots=parsed.get('slots', {}),
            needs_backend=parsed.get('needs_backend', False),
            needs_rag=parsed.get('needs_rag', False),
            needs_expert_model=parsed.get('needs_expert_model', False),
            reason=parsed.get('reason', ''),
            confidence=0.8 if parsed.get('conversation_mode') != 'UNKNOWN' else 0.3,
            raw_response=raw_response
        )

        return result

    def classify_simple(self, user_message: str) -> Dict:
        """
        Simple classification without pre-filtering
        Returns dict instead of dataclass for easier integration
        """
        result = self.classify(
            user_message=user_message,
            top_flow_candidates=[],
            rag_document_summaries=[],
            session_context={}
        )

        return {
            'conversation_mode': result.conversation_mode,
            'flow_name': result.flow_name,
            'slots': result.slots,
            'needs_backend': result.needs_backend,
            'needs_rag': result.needs_rag,
            'needs_expert_model': result.needs_expert_model,
            'reason': result.reason,
            'confidence': result.confidence
        }


# Singleton instance
_classifier_instance = None


def get_classifier(llm_client=None) -> QwenClassifier:
    """Get or create classifier instance"""
    global _classifier_instance
    if _classifier_instance is None or llm_client is not None:
        _classifier_instance = QwenClassifier(llm_client=llm_client)
    return _classifier_instance


def test_classifier():
    """Test the classifier with sample messages"""
    print("Testing QWEN #1 Classifier...")

    # Test without LLM (rule-based fallback)
    classifier = QwenClassifier(llm_client=None)

    test_messages = [
        "bonjour",
        "quel est mon solde",
        "quels sont les frais de carte bancaire",
        "virer 50000 à Pierre",
        "simuler un crédit de 5 millions sur 20 ans"
    ]

    for msg in test_messages:
        print(f"\n--- Message: '{msg}' ---")
        result = classifier.classify_simple(msg)
        print(f"Mode: {result['conversation_mode']}")
        print(f"Flow: {result['flow_name']}")
        print(f"needs_rag: {result['needs_rag']}")
        print(f"needs_backend: {result['needs_backend']}")


if __name__ == "__main__":
    test_classifier()
