# -*- coding: utf-8 -*-
"""
Slot Filling Manager - Multi-turn conversational slot collection
Uses LLM to understand and extract slot values from natural language
"""

import re
import json
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class SlotFillingManager:
    """
    Manages conversational slot filling across multiple turns
    Uses LLM to intelligently extract and validate slot values
    """

    # Slot metadata: order, description, validation rules
    SLOT_METADATA = {
        "CALC_CAPACITE_EMPRUNT": {
            "required": ["revenu_mensuel_net", "charges_mensuelles_existantes", "taux_credit_annuel", "duree_annees"],
            "optional": ["taux_endettement_max"],
            "order": ["revenu_mensuel_net", "charges_mensuelles_existantes", "taux_credit_annuel", "duree_annees", "taux_endettement_max"],
            "defaults": {"taux_endettement_max": 0.4},
            "descriptions": {
                "revenu_mensuel_net": "votre revenu mensuel net (salaire après impôts)",
                "charges_mensuelles_existantes": "vos charges mensuelles actuelles (autres crédits, loyers, etc.)",
                "taux_credit_annuel": "le taux d'intérêt annuel proposé (en %)",
                "duree_annees": "la durée du prêt souhaitée (en années)",
                "taux_endettement_max": "le taux d'endettement maximum autorisé (généralement 40%)"
            },
            "validation": {
                "revenu_mensuel_net": {"min": 1, "max": 100_000_000, "type": "amount"},
                "charges_mensuelles_existantes": {"min": 0, "max": 100_000_000, "type": "amount"},
                "taux_credit_annuel": {"min": 0, "max": 0.5, "type": "rate"},
                "duree_annees": {"min": 1, "max": 50, "type": "duration"},
                "taux_endettement_max": {"min": 0, "max": 1, "type": "rate"}
            }
        },
        "CALC_SIMULATION_PRET": {
            "required": ["montant_pret", "taux_credit_annuel", "duree_annees"],
            "optional": ["taux_assurance_annuel", "frais_dossier"],
            "order": ["montant_pret", "taux_credit_annuel", "duree_annees", "taux_assurance_annuel", "frais_dossier"],
            "defaults": {"taux_assurance_annuel": 0, "frais_dossier": 0},
            "descriptions": {
                "montant_pret": "le montant du prêt souhaité",
                "taux_credit_annuel": "le taux d'intérêt annuel (en %)",
                "duree_annees": "la durée du prêt (en années)",
                "taux_assurance_annuel": "le taux d'assurance annuel (optionnel, en %)",
                "frais_dossier": "les frais de dossier (optionnel)"
            },
            "validation": {
                "montant_pret": {"min": 1, "max": 1_000_000_000, "type": "amount"},
                "taux_credit_annuel": {"min": 0, "max": 0.5, "type": "rate"},
                "duree_annees": {"min": 1, "max": 50, "type": "duration"},
                "taux_assurance_annuel": {"min": 0, "max": 0.1, "type": "rate"},
                "frais_dossier": {"min": 0, "max": 10_000_000, "type": "amount"}
            }
        },
        "CALC_COMPARAISON_PRETS": {
            "required": ["montant_pret_A", "taux_credit_annuel_A", "duree_annees_A",
                        "montant_pret_B", "taux_credit_annuel_B", "duree_annees_B"],
            "optional": ["taux_assurance_annuel_A", "frais_dossier_A",
                        "taux_assurance_annuel_B", "frais_dossier_B"],
            "order": ["montant_pret_A", "taux_credit_annuel_A", "duree_annees_A",
                     "montant_pret_B", "taux_credit_annuel_B", "duree_annees_B"],
            "defaults": {},
            "descriptions": {
                "montant_pret_A": "le montant de l'offre A",
                "taux_credit_annuel_A": "le taux de l'offre A (en %)",
                "duree_annees_A": "la durée de l'offre A (en années)",
                "montant_pret_B": "le montant de l'offre B",
                "taux_credit_annuel_B": "le taux de l'offre B (en %)",
                "duree_annees_B": "la durée de l'offre B (en années)"
            },
            "validation": {
                "montant_pret_A": {"min": 1, "max": 1_000_000_000, "type": "amount"},
                "taux_credit_annuel_A": {"min": 0, "max": 0.5, "type": "rate"},
                "duree_annees_A": {"min": 1, "max": 50, "type": "duration"},
                "montant_pret_B": {"min": 1, "max": 1_000_000_000, "type": "amount"},
                "taux_credit_annuel_B": {"min": 0, "max": 0.5, "type": "rate"},
                "duree_annees_B": {"min": 1, "max": 50, "type": "duration"}
            }
        },
        "CALC_EPARGNE_OBJECTIF": {
            "required": ["objectif_montant", "duree_annees", "taux_rendement_annuel"],
            "optional": [],
            "order": ["objectif_montant", "duree_annees", "taux_rendement_annuel"],
            "defaults": {},
            "descriptions": {
                "objectif_montant": "le montant que vous souhaitez atteindre",
                "duree_annees": "la durée pour atteindre cet objectif (en années)",
                "taux_rendement_annuel": "le taux de rendement annuel estimé (en %)"
            },
            "validation": {
                "objectif_montant": {"min": 1, "max": 10_000_000_000, "type": "amount"},
                "duree_annees": {"min": 1, "max": 50, "type": "duration"},
                "taux_rendement_annuel": {"min": 0, "max": 0.3, "type": "rate"}
            }
        }
    }

    def __init__(self, llm_model):
        """
        Initialize slot filling manager

        Args:
            llm_model: LLM model for understanding user input
        """
        self.llm_model = llm_model

    def extract_slot_value(self, user_message: str, slot_name: str,
                          slot_metadata: Dict, conversation_context: str = "") -> Tuple[Optional[Any], str]:
        """
        Use LLM to extract and normalize slot value from user message

        Args:
            user_message: User's natural language input
            slot_name: Name of slot to extract (e.g., "revenu_mensuel_net")
            slot_metadata: Metadata for this slot (description, validation, etc.)
            conversation_context: Recent conversation for context

        Returns:
            (extracted_value, confidence_level)
            - extracted_value: Normalized value or None if couldn't extract
            - confidence_level: "high", "medium", "low", "unclear"
        """
        slot_type = slot_metadata.get("type", "unknown")
        description = slot_metadata.get("description", slot_name)

        prompt = f"""Tu es un expert en extraction d'informations financières.

{conversation_context}

MESSAGE UTILISATEUR:
"{user_message}"

TÂCHE: Extraire la valeur pour le slot "{slot_name}".
Description: {description}
Type: {slot_type}

RÈGLES D'EXTRACTION:

1. MONTANTS (type="amount"):
   - "500000" → 500000
   - "500 000" → 500000
   - "500k" → 500000
   - "500 mille" → 500000
   - "0.5 million" → 500000
   - "un demi-million" → 500000
   - "cinq cent mille" → 500000

2. TAUX (type="rate"):
   - "8%" → 0.08
   - "8 pourcent" → 0.08
   - "huit pour cent" → 0.08
   - "0.08" → 0.08
   - "40%" → 0.4

3. DURÉES (type="duration"):
   - "20 ans" → 20
   - "vingt ans" → 20
   - "240 mois" → 20 (convertir mois en années)
   - "2 décennies" → 20

4. SI AMBIGU OU VAGUE:
   - "pas mal" → null (confidence: unclear)
   - "environ 500000" → 500000 (confidence: medium)
   - "entre 400000 et 500000" → 450000 (confidence: medium, moyenne)

Réponds UNIQUEMENT en JSON:
{{
  "extracted_value": nombre ou null,
  "confidence": "high"|"medium"|"low"|"unclear",
  "reason": "explication courte en français"
}}"""

        try:
            response = self.llm_model.generate(prompt, temperature=0.1)
            logger.info(f"[SLOT EXTRACT] LLM response: {response[:200]}...")

            # Parse JSON
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                value = result.get("extracted_value")
                confidence = result.get("confidence", "low")
                reason = result.get("reason", "")

                logger.info(f"[SLOT EXTRACT] {slot_name} = {value} (confidence: {confidence}, reason: {reason})")
                return value, confidence
            else:
                logger.warning(f"[SLOT EXTRACT] No JSON in LLM response")
                return None, "unclear"

        except Exception as e:
            logger.error(f"[SLOT EXTRACT] Error: {e}", exc_info=True)

            # Fallback: simple regex extraction
            return self._fallback_extract(user_message, slot_type), "low"

    def _fallback_extract(self, message: str, slot_type: str) -> Optional[Any]:
        """
        Fallback extraction using regex (if LLM fails)
        """
        # Remove spaces and commas
        clean = message.replace(" ", "").replace(",", "")

        # Try to find a number
        number_match = re.search(r'[\d.]+', clean)
        if not number_match:
            return None

        num = float(number_match.group())

        # Handle percentages
        if "%" in message or "pourcent" in message.lower():
            return num / 100

        # Handle "k" = thousand
        if "k" in message.lower():
            return num * 1000

        # Handle "million"
        if "million" in message.lower():
            return num * 1000000

        return num

    def validate_slot(self, slot_name: str, value: Any, validation_rules: Dict) -> Tuple[bool, str]:
        """
        Validate if slot value is within acceptable range

        Args:
            slot_name: Slot name
            value: Extracted value
            validation_rules: Min/max/type rules

        Returns:
            (is_valid, error_message)
        """
        if value is None:
            return False, "Valeur manquante"

        min_val = validation_rules.get("min", float('-inf'))
        max_val = validation_rules.get("max", float('inf'))
        slot_type = validation_rules.get("type", "unknown")

        try:
            value_float = float(value)

            if value_float < min_val or value_float > max_val:
                if slot_type == "amount":
                    return False, f"Le montant doit être entre {min_val:,.0f} et {max_val:,.0f} XOF"
                elif slot_type == "rate":
                    return False, f"Le taux doit être entre {min_val*100:.1f}% et {max_val*100:.1f}%"
                elif slot_type == "duration":
                    return False, f"La durée doit être entre {min_val:.0f} et {max_val:.0f} ans"
                else:
                    return False, f"La valeur doit être entre {min_val} et {max_val}"

            return True, ""

        except (ValueError, TypeError):
            return False, f"Format invalide pour {slot_name}"

    def get_next_slot_to_ask(self, flow_name: str, collected_slots: Dict,
                            missing_slots: List[str]) -> Optional[str]:
        """
        Determine next slot to ask for, following logical order

        Args:
            flow_name: Name of active flow
            collected_slots: Already collected slots
            missing_slots: List of missing slot names

        Returns:
            Next slot name to ask for, or None if all collected
        """
        metadata = self.SLOT_METADATA.get(flow_name)
        if not metadata:
            return missing_slots[0] if missing_slots else None

        # Follow predefined order
        for slot in metadata["order"]:
            if slot in missing_slots:
                return slot

        return None

    def generate_slot_question(self, flow_name: str, slot_name: str,
                              collected_slots: Dict, llm_model) -> str:
        """
        Generate natural question to ask for a specific slot

        Args:
            flow_name: Active flow name
            slot_name: Slot to ask about
            collected_slots: Already collected slots for context
            llm_model: LLM for generating question

        Returns:
            Natural language question
        """
        metadata = self.SLOT_METADATA.get(flow_name, {})
        description = metadata.get("descriptions", {}).get(slot_name, slot_name)

        # Build context from already collected slots
        context_parts = []
        for key, value in collected_slots.items():
            if value is not None:
                context_parts.append(f"- {key}: {value}")

        context_str = "\n".join(context_parts) if context_parts else "Aucune information collectée"

        prompt = f"""Tu es un conseiller bancaire qui collecte des informations pour un calcul financier.

FLOW ACTIF: {flow_name}
INFORMATIONS DÉJÀ COLLECTÉES:
{context_str}

PROCHAINE INFORMATION À DEMANDER:
Slot: {slot_name}
Description: {description}

TÂCHE: Génère une question naturelle, professionnelle et conviviale pour demander cette information.

RÈGLES:
- Utilise un ton chaleureux et professionnel
- Sois concis (1-2 phrases max)
- Donne un exemple si nécessaire
- Ne répète pas les informations déjà collectées

EXEMPLES DE BONNES QUESTIONS:
- "Quel est votre revenu mensuel net ?"
- "Parfait ! Quelles sont vos charges mensuelles actuelles (autres crédits, loyers, etc.) ?"
- "Merci. Quel est le taux d'intérêt annuel proposé par votre banque ?"
- "Sur combien d'années souhaitez-vous emprunter ?"

Réponds UNIQUEMENT avec la question (pas de JSON, juste le texte):"""

        try:
            question = llm_model.generate(prompt, temperature=0.7)
            # Clean up response
            question = question.strip().strip('"').strip("'")
            return question
        except Exception as e:
            logger.error(f"[SLOT QUESTION] Error: {e}")
            # Fallback to template
            return f"Pouvez-vous me donner {description} ?"

    def generate_confirmation_message(self, flow_name: str, slots: Dict, llm_model) -> str:
        """
        Generate confirmation message before executing calculation

        Args:
            flow_name: Active flow
            slots: All collected slots
            llm_model: LLM for generating message

        Returns:
            Natural confirmation message
        """
        # Format slots nicely
        slot_descriptions = self.SLOT_METADATA.get(flow_name, {}).get("descriptions", {})

        slots_summary = []
        for key, value in slots.items():
            if value is not None:
                desc = slot_descriptions.get(key, key)

                # Format based on type
                if "taux" in key and isinstance(value, float) and value < 1:
                    formatted = f"{value*100:.2f}%"
                elif "montant" in key or "revenu" in key or "charge" in key:
                    formatted = f"{value:,.0f} XOF"
                elif "duree" in key or "annees" in key:
                    formatted = f"{value:.0f} ans"
                else:
                    formatted = str(value)

                slots_summary.append(f"- {desc}: {formatted}")

        slots_text = "\n".join(slots_summary)

        prompt = f"""Tu es un conseiller bancaire qui confirme les informations avant un calcul.

FLOW: {flow_name}
INFORMATIONS COLLECTÉES:
{slots_text}

TÂCHE: Génère un message de confirmation naturel et professionnel.

RÈGLES:
- Récapitule toutes les informations de manière claire
- Demande confirmation ("Est-ce correct ?" ou "Souhaitez-vous que je calcule ?")
- Ton chaleureux et professionnel
- Concis mais complet

EXEMPLE:
"Parfait, j'ai bien noté toutes les informations :
- Votre revenu mensuel net : 500 000 XOF
- Vos charges actuelles : 100 000 XOF
- Taux d'intérêt : 8,00% par an
- Durée : 20 ans

Souhaitez-vous que je calcule votre capacité d'emprunt avec ces informations ?"

Réponds UNIQUEMENT avec le message (pas de JSON):"""

        try:
            message = llm_model.generate(prompt, temperature=0.7)
            return message.strip().strip('"').strip("'")
        except Exception as e:
            logger.error(f"[CONFIRMATION] Error: {e}")
            return f"Voici les informations que j'ai collectées :\n{slots_text}\n\nSouhaitez-vous continuer ?"


# Testing
if __name__ == "__main__":
    from llm.openai_client import OpenAIClient

    logging.basicConfig(level=logging.INFO)

    llm = OpenAIClient(base_url='http://localhost:1234/v1', model_name='qwen2.5-14b-instruct')
    manager = SlotFillingManager(llm)

    print("=== Test Slot Extraction ===\n")

    # Test 1: Extract amount
    value, conf = manager.extract_slot_value(
        "je gagne 500000 par mois",
        "revenu_mensuel_net",
        {"type": "amount", "description": "revenu mensuel net"}
    )
    print(f"Test 1: {value} (confidence: {conf})")

    # Test 2: Extract rate
    value, conf = manager.extract_slot_value(
        "le taux est de 8%",
        "taux_credit_annuel",
        {"type": "rate", "description": "taux d'intérêt"}
    )
    print(f"Test 2: {value} (confidence: {conf})")

    # Test 3: Validation
    is_valid, error = manager.validate_slot(
        "taux_credit_annuel",
        0.08,
        {"min": 0, "max": 0.5, "type": "rate"}
    )
    print(f"Test 3: Valid={is_valid}, Error={error}")
