# -*- coding: utf-8 -*-
"""
FAST CLASSIFIER - Keyword-based intent detection (instant, no LLM)

Replaces slow LLM classifier (~3-4s) with instant keyword matching (~1ms)
for RAG-triggering questions. Falls back to LLM for complex cases.

Architecture:
User Input → Keyword Check → RAG Match? → Skip LLM → Go to RAG
                          → No Match? → Use LLM classifier
"""

import re
import unicodedata
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class FastClassificationResult:
    """Result from fast keyword classification"""
    intent: Optional[str]  # FEES_ACCOUNT, FEES_CARD, etc. or None
    route: str  # "RAG_TARIFS", "LLM_DIRECT", "LLM_CLASSIFY"
    needs_rag: bool
    keywords_matched: List[str]
    confidence: float  # 0.0-1.0 based on keyword match quality


# =============================================================================
# INTENT RULES - Keyword-based detection for UEMOA banking
# =============================================================================
INTENT_RULES: Dict[str, Dict] = {
    # =========================================================================
    # FEES/TARIFFS - All route to RAG
    # =========================================================================
    "FEES_ACCOUNT": {
        "any": ["frais", "tarif", "commission", "agios", "coût", "prix", "combien"],
        "must": ["compte", "tenue", "gestion", "ouverture", "clôture", "fermeture"],
        "priority": 10,
    },
    "FEES_CARD": {
        "any": ["frais", "cotisation", "tarif", "coût", "prix", "combien"],
        "must": ["carte", "visa", "mastercard", "cb", "bancaire", "débit", "crédit", "retrait"],
        "priority": 10,
    },
    "FEES_TRANSFER_UEMOA": {
        "any": ["frais", "commission", "tarif", "coût", "combien"],
        "must": ["virement", "transfert", "uemoa", "zone", "bceao", "national", "local"],
        "priority": 10,
    },
    "FEES_TRANSFER_INTL": {
        "any": ["frais", "commission", "tarif", "coût", "combien"],
        "must": ["virement", "transfert", "international", "étranger", "hors zone", "europe", "usa"],
        "priority": 10,
    },
    "FEES_CASH_WITHDRAWAL": {
        "any": ["frais", "commission", "tarif", "coût", "combien"],
        "must": ["retrait", "dab", "gab", "distributeur", "guichet", "espèces", "cash"],
        "priority": 10,
    },
    "FEES_CHEQUE": {
        "any": ["frais", "tarif", "coût", "combien"],
        "must": ["chèque", "chéquier", "carnet"],
        "priority": 10,
    },

    # =========================================================================
    # LOAN/CREDIT - Route to RAG (info questions)
    # =========================================================================
    "LOAN_FEES": {
        "any": ["frais", "commission", "coût", "combien"],
        "must": ["crédit", "prêt", "emprunt", "dossier", "financement"],
        "priority": 10,
    },
    "LOAN_RATE": {
        "any": ["taux", "intérêt", "pourcentage", "combien"],
        "must": ["crédit", "prêt", "emprunt", "financement"],
        "priority": 10,
    },
    "LOAN_CONDITIONS": {
        "any": ["condition", "critère", "éligibilité", "durée", "montant"],
        "must": ["crédit", "prêt", "emprunt", "financement"],
        "priority": 8,
    },

    # =========================================================================
    # CREDIT SIMULATION - Direct to credit flow (not RAG)
    # =========================================================================
    "SIMULATION_CREDIT": {
        "any": ["simuler", "simulation", "emprunter", "mensualité", "calcul"],
        "must": ["crédit", "prêt", "emprunt"],
        "priority": 12,
        "route": "CREDIT_FLOW",
    },
    "CREDIT_SIMULATION": {
        "any": ["je voudrais", "je veux", "besoin", "obtenir", "demande"],
        "must": ["crédit", "prêt", "emprunt", "million", "millions"],
        "priority": 11,
        "route": "CREDIT_FLOW",
    },

    # =========================================================================
    # GENERAL BANKING (may need RAG for policies)
    # =========================================================================
    "GENERAL_ACCOUNT_OPEN": {
        "any": ["ouvrir", "ouverture", "créer", "comment"],
        "must": ["compte", "bancaire", "épargne", "courant"],
        "priority": 5,
    },
    "GENERAL_MOBILE": {
        "any": ["comment", "utiliser", "application", "télécharger"],
        "must": ["mobile", "app", "smartphone", "afg mobile"],
        "priority": 5,
    },

    # =========================================================================
    # TRANSACTIONAL INTENTS (Backend, not RAG)
    # =========================================================================
    "CHECK_BALANCE": {
        "any": ["solde", "avoir", "reste", "combien"],
        "must": ["compte", "mon", "consulter", "voir"],
        "priority": 8,
        "route": "BACKEND",
    },
    "TRANSFER_MONEY": {
        "any": ["virer", "transférer", "envoyer", "faire"],
        "must": ["argent", "fcfa", "euros", "virement"],
        "priority": 8,
        "route": "BACKEND",
    },

    # =========================================================================
    # CARD SERVICES - Direct to card flow (not RAG)
    # =========================================================================
    "CARD_BLOCK": {
        "any": ["bloquer", "opposition", "perdu", "perdue", "volé", "volée", "annuler"],
        "must": ["carte", "visa", "bancaire", "cb"],
        "priority": 12,
        "route": "CARD_SERVICE_FLOW",
    },
    "CARD_UNBLOCK": {
        "any": ["débloquer", "debloquer", "lever", "réactiver", "levée"],
        "must": ["carte", "opposition", "blocage", "bancaire"],
        "priority": 13,  # Higher than CARD_BLOCK to handle "débloquer" containing "bloquer"
        "route": "CARD_SERVICE_FLOW",
    },
    "CARD_PIN": {
        "any": ["code", "pin", "confidentiel", "oublié", "changer", "nouveau"],
        "must": ["carte", "secret", "pin"],
        "priority": 11,
        "route": "CARD_SERVICE_FLOW",
    },
    "CARD_LIMIT": {
        "any": ["plafond", "limite", "augmenter", "réduire", "modifier"],
        "must": ["carte", "retrait", "paiement"],
        "priority": 10,
        "route": "CARD_SERVICE_FLOW",
    },

    # =========================================================================
    # FOREX EXCHANGE - Direct to forex flow
    # =========================================================================
    "FOREX_BUY": {
        "any": ["acheter", "achat", "obtenir", "avoir", "besoin"],
        "must": ["euro", "euros", "dollar", "dollars", "devise", "devises", "change"],
        "priority": 11,
        "route": "FOREX_FLOW",
    },
    "FOREX_SELL": {
        "any": ["vendre", "vente", "échanger", "convertir", "changer"],
        "must": ["euro", "euros", "dollar", "dollars", "devise", "devises"],
        "priority": 11,
        "route": "FOREX_FLOW",
    },
    "FOREX_RATE": {
        "any": ["taux", "cours", "combien", "quel est", "cotation"],
        "must": ["euro", "dollar", "change", "devise", "devises"],
        "priority": 10,
        "route": "FOREX_FLOW",
    },

    # =========================================================================
    # PAYMENT INCIDENTS - Direct to incident flow
    # =========================================================================
    "INCIDENT_CHEQUE": {
        "any": ["impayé", "rejeté", "refusé", "sans provision", "bounce"],
        "must": ["chèque", "cheque"],
        "priority": 11,
        "route": "INCIDENT_FLOW",
    },
    "INCIDENT_VIREMENT": {
        "any": ["rejeté", "échoué", "annulé", "refusé", "problème"],
        "must": ["virement", "transfert"],
        "priority": 10,
        "route": "INCIDENT_FLOW",
    },
    "INCIDENT_PRELEVEMENT": {
        "any": ["rejeté", "refusé", "impayé", "problème"],
        "must": ["prélèvement", "prelevement"],
        "priority": 10,
        "route": "INCIDENT_FLOW",
    },
    "INCIDENT_ATD": {
        "any": ["atd", "avis", "tiers", "détenteur", "huissier"],
        "must": ["compte", "blocage", "saisie"],
        "priority": 11,
        "route": "INCIDENT_FLOW",
    },
    "INCIDENT_SAISIE": {
        "any": ["saisie", "saisir", "bloqué", "gelé"],
        "must": ["compte", "argent", "fonds"],
        "priority": 11,
        "route": "INCIDENT_FLOW",
    },
    "CONTESTATION": {
        "any": ["contester", "contestation", "dispute", "fraude", "pas moi", "reconnais pas"],
        "must": ["transaction", "paiement", "opération", "carte", "débit"],
        "priority": 12,
        "route": "INCIDENT_FLOW",
    },

    # =========================================================================
    # GREETING/CHITCHAT (Direct LLM response)
    # =========================================================================
    "GREETING": {
        "any": ["bonjour", "salut", "bonsoir", "hello", "hi", "coucou", "bonne journée"],
        "must": [],  # No context required
        "priority": 3,
        "route": "LLM_DIRECT",
    },
    "THANKS": {
        "any": ["merci", "thanks", "remercie"],
        "must": [],
        "priority": 3,
        "route": "LLM_DIRECT",
    },
    "GOODBYE": {
        "any": ["au revoir", "bye", "à bientôt", "bonne soirée", "adieu"],
        "must": [],
        "priority": 3,
        "route": "LLM_DIRECT",
    },
}

# Quick RAG trigger keywords (instant detection)
RAG_TRIGGER_KEYWORDS = {
    "frais", "tarif", "tarifs", "coût", "coûts", "prix", "commission", "commissions",
    "taux", "intérêt", "intérêts", "cotisation", "agios",
    "combien coûte", "combien ça coûte", "quel est le prix", "quels sont les frais"
}


def normalize_text(text: str) -> str:
    """
    Normalize text for keyword matching
    - Lowercase
    - Remove accents
    - Remove extra whitespace
    """
    text = text.lower().strip()
    # Normalize unicode (NFD decomposes accents)
    text = unicodedata.normalize('NFD', text)
    # Remove accent marks
    text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text)
    return text


def normalize_with_accents(text: str) -> str:
    """Normalize but keep accents for better French matching"""
    text = text.lower().strip()
    text = re.sub(r'\s+', ' ', text)
    return text


def quick_rag_check(message: str) -> bool:
    """
    Ultra-fast check: Does message contain RAG trigger keywords?
    This is the first filter - if True, we know RAG is needed.
    """
    msg_lower = message.lower()
    for keyword in RAG_TRIGGER_KEYWORDS:
        if keyword in msg_lower:
            return True
    return False


def match_intent(message: str) -> Tuple[Optional[str], List[str], float]:
    """
    Match message against intent rules

    Returns:
        (intent_name, matched_keywords, confidence)
    """
    msg_normalized = normalize_with_accents(message)
    msg_no_accents = normalize_text(message)

    best_match = None
    best_score = 0
    best_keywords = []

    for intent_name, rules in INTENT_RULES.items():
        any_keywords = rules.get("any", [])
        must_keywords = rules.get("must", [])
        priority = rules.get("priority", 5)

        # Check "any" keywords (at least one must match)
        any_matched = []
        for kw in any_keywords:
            kw_norm = normalize_with_accents(kw)
            kw_no_acc = normalize_text(kw)
            if kw_norm in msg_normalized or kw_no_acc in msg_no_accents:
                any_matched.append(kw)

        if not any_matched and any_keywords:
            continue  # No trigger keyword found

        # Check "must" keywords (at least one must match, or empty means no constraint)
        must_matched = []
        for kw in must_keywords:
            kw_norm = normalize_with_accents(kw)
            kw_no_acc = normalize_text(kw)
            if kw_norm in msg_normalized or kw_no_acc in msg_no_accents:
                must_matched.append(kw)

        if must_keywords and not must_matched:
            continue  # Context keyword required but not found

        # Calculate score
        total_matched = len(any_matched) + len(must_matched)
        score = total_matched * priority

        if score > best_score:
            best_score = score
            best_match = intent_name
            best_keywords = any_matched + must_matched

    # Calculate confidence (0.0 - 1.0)
    if best_match:
        confidence = min(1.0, best_score / 20.0)  # Normalize to 0-1
    else:
        confidence = 0.0

    return best_match, best_keywords, confidence


def route(message: str) -> FastClassificationResult:
    """
    Main routing function - determines intent and routing path

    Returns:
        FastClassificationResult with intent, route, and metadata
    """
    # Step 1: Quick RAG check (instant)
    is_rag_question = quick_rag_check(message)

    # Step 2: Match against intent rules
    intent, keywords, confidence = match_intent(message)

    # Step 3: Determine routing
    if intent:
        # Check if intent has custom route
        intent_route = INTENT_RULES.get(intent, {}).get("route")

        if intent_route == "BACKEND":
            return FastClassificationResult(
                intent=intent,
                route="BACKEND",
                needs_rag=False,
                keywords_matched=keywords,
                confidence=confidence
            )
        elif intent_route == "LLM_DIRECT":
            return FastClassificationResult(
                intent=intent,
                route="LLM_DIRECT",
                needs_rag=False,
                keywords_matched=keywords,
                confidence=confidence
            )
        elif intent_route == "CREDIT_FLOW":
            # Credit simulation - direct to credit flow handler
            return FastClassificationResult(
                intent=intent,
                route="CREDIT_FLOW",
                needs_rag=False,
                keywords_matched=keywords,
                confidence=confidence
            )
        elif intent_route == "CARD_SERVICE_FLOW":
            # Card services - direct to card service flow handler
            return FastClassificationResult(
                intent=intent,
                route="CARD_SERVICE_FLOW",
                needs_rag=False,
                keywords_matched=keywords,
                confidence=confidence
            )
        elif intent_route == "FOREX_FLOW":
            # Forex exchange - direct to forex flow handler
            return FastClassificationResult(
                intent=intent,
                route="FOREX_FLOW",
                needs_rag=False,
                keywords_matched=keywords,
                confidence=confidence
            )
        elif intent_route == "INCIDENT_FLOW":
            # Payment incidents - direct to incident flow handler
            return FastClassificationResult(
                intent=intent,
                route="INCIDENT_FLOW",
                needs_rag=False,
                keywords_matched=keywords,
                confidence=confidence
            )
        elif intent.startswith("FEES_") or intent.startswith("LOAN_"):
            # Fee/loan questions always go to RAG
            return FastClassificationResult(
                intent=intent,
                route="RAG_TARIFS",
                needs_rag=True,
                keywords_matched=keywords,
                confidence=confidence
            )
        elif intent.startswith("GENERAL_"):
            # General questions may need RAG
            return FastClassificationResult(
                intent=intent,
                route="RAG_GENERAL",
                needs_rag=True,
                keywords_matched=keywords,
                confidence=confidence
            )

    # Step 4: Fallback based on quick RAG check
    if is_rag_question:
        return FastClassificationResult(
            intent=None,
            route="RAG_TARIFS",
            needs_rag=True,
            keywords_matched=["(rag trigger)"],
            confidence=0.6
        )

    # Step 5: No match - use LLM classifier
    return FastClassificationResult(
        intent=None,
        route="LLM_CLASSIFY",
        needs_rag=False,
        keywords_matched=[],
        confidence=0.0
    )


class FastClassifier:
    """
    Fast Classifier class for integration with Banking Assistant

    Provides instant keyword-based classification for RAG questions,
    with fallback to LLM for complex cases.
    """

    def __init__(self):
        """Initialize the fast classifier"""
        self.call_count = 0
        self.rag_detections = 0
        self.llm_fallbacks = 0

    def classify(self, message: str) -> FastClassificationResult:
        """
        Classify a message using keyword matching

        Args:
            message: User message to classify

        Returns:
            FastClassificationResult
        """
        self.call_count += 1
        result = route(message)

        if result.needs_rag:
            self.rag_detections += 1
        elif result.route == "LLM_CLASSIFY":
            self.llm_fallbacks += 1

        return result

    def needs_llm_classifier(self, message: str) -> bool:
        """
        Check if message needs LLM classifier (fast check)

        Returns:
            True if LLM classifier is needed, False if keyword detection is sufficient
        """
        result = route(message)
        return result.route == "LLM_CLASSIFY"

    def get_stats(self) -> Dict:
        """Get classifier statistics"""
        return {
            "total_calls": self.call_count,
            "rag_detections": self.rag_detections,
            "llm_fallbacks": self.llm_fallbacks,
            "rag_detection_rate": self.rag_detections / max(1, self.call_count),
            "llm_fallback_rate": self.llm_fallbacks / max(1, self.call_count)
        }


# =============================================================================
# Testing
# =============================================================================
def test_classifier():
    """Test the fast classifier with sample messages"""
    print("=" * 60)
    print("FAST CLASSIFIER TEST")
    print("=" * 60)

    test_messages = [
        # Should detect RAG (fees)
        ("Quels sont les frais de carte bancaire ?", "FEES_CARD", True),
        ("Combien coûte un virement international ?", "FEES_TRANSFER_INTL", True),
        ("Quel est le tarif de tenue de compte ?", "FEES_ACCOUNT", True),
        ("Les frais de retrait au DAB ?", "FEES_CASH_WITHDRAWAL", True),

        # Should detect RAG (loans)
        ("Quel est le taux d'intérêt pour un crédit ?", "LOAN_RATE", True),
        ("Frais de dossier pour un prêt ?", "LOAN_FEES", True),

        # Should detect GREETING (LLM_DIRECT)
        ("Bonjour", "GREETING", False),
        ("Salut comment ça va ?", "GREETING", False),

        # Should fallback to LLM
        ("Je voudrais parler à un conseiller", None, False),
        ("Pouvez-vous m'expliquer comment fonctionne votre banque ?", None, False),
    ]

    classifier = FastClassifier()

    for message, expected_intent, expected_rag in test_messages:
        result = classifier.classify(message)

        intent_ok = result.intent == expected_intent or (expected_intent is None and result.intent is None)
        rag_ok = result.needs_rag == expected_rag

        status = "OK" if (intent_ok and rag_ok) else "FAIL"

        print(f"\n[{status}] '{message}'")
        print(f"  Intent: {result.intent} (expected: {expected_intent})")
        print(f"  Route: {result.route}")
        print(f"  needs_rag: {result.needs_rag} (expected: {expected_rag})")
        print(f"  Keywords: {result.keywords_matched}")
        print(f"  Confidence: {result.confidence:.2f}")

    print("\n" + "=" * 60)
    print("STATISTICS")
    print("=" * 60)
    stats = classifier.get_stats()
    print(f"Total calls: {stats['total_calls']}")
    print(f"RAG detections: {stats['rag_detections']} ({stats['rag_detection_rate']:.1%})")
    print(f"LLM fallbacks: {stats['llm_fallbacks']} ({stats['llm_fallback_rate']:.1%})")


if __name__ == "__main__":
    test_classifier()
