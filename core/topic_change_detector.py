# -*- coding: utf-8 -*-
"""
Topic Change Detector - Détecte quand l'utilisateur change de sujet

Inspiré de Claude/Google Gemini:
- Détection de changement de sujet/intention
- Confirmation avant de changer de contexte
- Réinitialisation propre du contexte
"""

import logging
from typing import Dict, Optional, List, Tuple
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

logger = logging.getLogger(__name__)


class TopicChangeDetector:
    """
    Détecte les changements de sujet dans une conversation

    Utilise:
    1. Similarité sémantique entre messages
    2. Détection de mots-clés de transition ("maintenant", "plutôt", "en fait", etc.)
    3. Analyse du contexte de conversation
    """

    def __init__(self, embedding_model, similarity_threshold: float = 0.3):
        """
        Args:
            embedding_model: SentenceTransformer model for embeddings
            similarity_threshold: Si similarité < seuil → topic change (default: 0.3)
        """
        self.embedding_model = embedding_model
        self.similarity_threshold = similarity_threshold

        # Mots-clés qui indiquent un changement de sujet
        self.topic_change_keywords = [
            # Transitions explicites
            "maintenant", "plutôt", "en fait", "au fait", "sinon",
            "autre chose", "changement de sujet", "question différente",
            "nouvelle question", "oublie", "laisse tomber", "pas grave",

            # Négations du contexte précédent
            "non je voulais", "non je parle de", "non c'est pour",
            "ce n'est pas ça", "pas ça", "autre chose",

            # Redémarrage
            "recommence", "reset", "annule", "stop", "arrête",
            "nouvelle demande", "autre demande"
        ]

    def detect_topic_change(
        self,
        current_message: str,
        previous_messages: List[str],
        current_intent: str,
        previous_intent: Optional[str],
        session_active_flow: Optional[str]
    ) -> Dict:
        """
        Détecte si le message actuel représente un changement de sujet

        Args:
            current_message: Message actuel de l'utilisateur
            previous_messages: Liste des N derniers messages utilisateur
            current_intent: Intent détecté pour le message actuel
            previous_intent: Intent du message précédent
            session_active_flow: Flow actif dans la session (si existe)

        Returns:
            {
                "topic_changed": bool,
                "confidence": float (0-1),
                "reason": str,
                "should_confirm": bool,  # Si on doit confirmer avec l'utilisateur
                "suggestion": str  # Message de confirmation suggéré
            }
        """

        # Si pas de contexte précédent → pas de changement
        if not previous_messages or not previous_intent:
            return {
                "topic_changed": False,
                "confidence": 0.0,
                "reason": "Pas de contexte précédent",
                "should_confirm": False,
                "suggestion": None
            }

        message_lower = current_message.lower()

        # 1. Détection par mots-clés explicites
        explicit_change = any(keyword in message_lower for keyword in self.topic_change_keywords)

        if explicit_change:
            return {
                "topic_changed": True,
                "confidence": 0.95,
                "reason": "Mot-clé de changement de sujet détecté",
                "should_confirm": False,  # Changement explicite → pas besoin de confirmer
                "suggestion": None
            }

        # 2. Changement d'intent radical
        intent_changed_radically = self._is_radical_intent_change(
            current_intent,
            previous_intent,
            session_active_flow
        )

        if intent_changed_radically:
            # Calculer similarité sémantique pour être sûr
            semantic_similarity = self._compute_semantic_similarity(
                current_message,
                previous_messages[-1]  # Dernier message
            )

            if semantic_similarity < self.similarity_threshold:
                return {
                    "topic_changed": True,
                    "confidence": 0.85,
                    "reason": f"Intent change radical ({previous_intent} → {current_intent}) + faible similarité ({semantic_similarity:.2f})",
                    "should_confirm": True,
                    "suggestion": self._generate_confirmation_message(
                        previous_intent,
                        current_intent,
                        session_active_flow
                    )
                }

        # 3. Similarité sémantique très faible
        if previous_messages:
            # Calculer similarité avec tous les messages récents
            similarities = []
            for prev_msg in previous_messages[-3:]:  # 3 derniers messages
                sim = self._compute_semantic_similarity(current_message, prev_msg)
                similarities.append(sim)

            avg_similarity = np.mean(similarities)

            if avg_similarity < self.similarity_threshold:
                return {
                    "topic_changed": True,
                    "confidence": 0.70,
                    "reason": f"Faible similarité sémantique ({avg_similarity:.2f})",
                    "should_confirm": True,
                    "suggestion": self._generate_generic_confirmation()
                }

        # 4. Pas de changement détecté
        return {
            "topic_changed": False,
            "confidence": 0.0,
            "reason": "Continuité du sujet",
            "should_confirm": False,
            "suggestion": None
        }

    def _compute_semantic_similarity(self, text1: str, text2: str) -> float:
        """Calcule la similarité cosinus entre deux textes"""
        try:
            embeddings = self.embedding_model.encode([text1, text2], convert_to_tensor=False)
            similarity = cosine_similarity([embeddings[0]], [embeddings[1]])[0][0]
            return float(similarity)
        except Exception as e:
            logger.warning(f"Error computing similarity: {e}")
            return 0.5  # Neutral value

    def _is_radical_intent_change(
        self,
        current_intent: str,
        previous_intent: str,
        session_active_flow: Optional[str]
    ) -> bool:
        """
        Détermine si le changement d'intent est radical

        Exemples de changements radicaux:
        - CONSULTER_SOLDE → SIMULATION_CREDIT
        - FAIRE_VIREMENT → RAG_QUESTION
        - Tout → GREETING (sauf si c'est le premier message)
        """

        # Liste des intents compatibles (pas de changement radical)
        compatible_intents = {
            "CONSULTER_SOLDE": ["DISCUSSION_COMPTE", "OBTENIR_RELEVE"],
            "DISCUSSION_COMPTE": ["CONSULTER_SOLDE", "OBTENIR_RELEVE"],
            "FAIRE_VIREMENT": ["DISCUSSION_COMPTE"],
            "SIMULATION_CREDIT": ["CALC_CAPACITE_EMPRUNT", "CALC_SIMULATION_PRET", "CALC_COMPARAISON_PRETS"],
            "CALC_CAPACITE_EMPRUNT": ["SIMULATION_CREDIT", "CALC_SIMULATION_PRET"],
            "CALC_SIMULATION_PRET": ["SIMULATION_CREDIT", "CALC_CAPACITE_EMPRUNT"],
            "RAG_QUESTION": ["RAG_QUESTION"],  # RAG questions peuvent s'enchaîner
        }

        # Si même intent → pas de changement
        if current_intent == previous_intent:
            return False

        # Si l'intent actuel est compatible avec le précédent → pas radical
        if previous_intent in compatible_intents:
            if current_intent in compatible_intents[previous_intent]:
                return False

        # Si session a un flow actif et on reste dans le même flow → pas radical
        if session_active_flow and current_intent == session_active_flow:
            return False

        # Sinon → changement radical
        return True

    def _generate_confirmation_message(
        self,
        previous_intent: str,
        current_intent: str,
        session_active_flow: Optional[str]
    ) -> str:
        """Génère un message de confirmation pour le changement de sujet"""

        intent_names = {
            "CONSULTER_SOLDE": "la consultation de solde",
            "DISCUSSION_COMPTE": "la discussion sur votre compte",
            "FAIRE_VIREMENT": "le virement",
            "OBTENIR_RELEVE": "le relevé bancaire",
            "SIMULATION_CREDIT": "la simulation de crédit",
            "CALC_CAPACITE_EMPRUNT": "le calcul de capacité d'emprunt",
            "CALC_SIMULATION_PRET": "la simulation de prêt",
            "RAG_QUESTION": "votre question",
            "GREETING": "les salutations",
            "CHITCHAT": "la discussion générale"
        }

        previous_name = intent_names.get(previous_intent, "le sujet précédent")
        current_name = intent_names.get(current_intent, "ce nouveau sujet")

        return f"Je note que vous souhaitez passer de {previous_name} à {current_name}. Souhaitez-vous que j'abandonne {previous_name} et que je me concentre sur {current_name} ?"

    def _generate_generic_confirmation(self) -> str:
        """Génère un message de confirmation générique"""
        return "Je remarque que vous changez de sujet. Souhaitez-vous que j'abandonne le sujet précédent et que je me concentre sur votre nouvelle demande ?"

    def should_reset_session(
        self,
        topic_change_result: Dict,
        user_confirmed: bool
    ) -> bool:
        """
        Détermine si on doit réinitialiser la session

        Args:
            topic_change_result: Résultat de detect_topic_change()
            user_confirmed: True si l'utilisateur a confirmé le changement

        Returns:
            True si la session doit être réinitialisée
        """
        if not topic_change_result["topic_changed"]:
            return False

        # Si changement explicite (mots-clés) → reset automatique
        if topic_change_result["confidence"] >= 0.9:
            return True

        # Si changement détecté mais nécessite confirmation → attendre confirmation
        if topic_change_result["should_confirm"]:
            return user_confirmed

        # Sinon reset par défaut
        return True
