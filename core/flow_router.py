# -*- coding: utf-8 -*-
"""
Flow Router - Second Router for In-Flow Conversations
Decides: CONTINUE_FLOW, NEW_FLOW, GENERAL_CHAT, ABORT_FLOW
Exactly like GPT/Claude handle multi-turn conversations
"""

import re
import json
from typing import Dict, Any, Optional
from enum import Enum

from core.session_state import SessionState, FlowStatus
from core.flows import flow_registry


class FlowDecision(Enum):
    """Flow routing decisions"""
    CONTINUE_FLOW = "continue_flow"  # User provides info for current flow
    NEW_FLOW = "new_flow"  # User starts a completely new banking flow
    GENERAL_CHAT = "general_chat"  # Off-topic / interruption
    ABORT_FLOW = "abort_flow"  # User wants to cancel


class FlowRouter:
    """
    Second router - handles in-flow conversations

    This is what makes GPT/Claude feel natural in multi-turn conversations:
    - Detects when user provides missing information
    - Handles interruptions gracefully
    - Detects subject changes
    - Recognizes cancellation intents
    """

    def __init__(self, llm_model=None):
        self.llm_model = llm_model

    def route_in_flow(self, message: str, session: SessionState) -> Dict[str, Any]:
        """
        Main routing decision when a flow is already active

        Args:
            message: User's message
            session: Current session state with active flow

        Returns:
            {
                "decision": FlowDecision,
                "extracted_slots": dict (if CONTINUE_FLOW),
                "new_flow_name": str (if NEW_FLOW),
                "reason": str
            }
        """
        # Quick checks first (no LLM needed)

        # 1. Check for cancellation keywords
        if self._is_cancellation(message):
            return {
                "decision": FlowDecision.ABORT_FLOW,
                "reason": "User wants to cancel"
            }

        # 2. Use Qwen to make intelligent decision
        if self.llm_model:
            return self._route_with_qwen(message, session)
        else:
            # Fallback: assume user is continuing the flow
            return {
                "decision": FlowDecision.CONTINUE_FLOW,
                "extracted_slots": {},
                "reason": "No LLM, assuming continuation"
            }

    def _is_cancellation(self, message: str) -> bool:
        """Check if user wants to cancel"""
        text = message.lower()
        cancel_keywords = [
            "stop", "arrêt", "annule", "annuler", "laisse tomber",
            "abandonne", "oublie", "non merci", "pas maintenant"
        ]
        return any(keyword in text for keyword in cancel_keywords)

    def _route_with_qwen(self, message: str, session: SessionState) -> Dict[str, Any]:
        """
        Use Qwen to decide what the user is doing

        This is the HEART of GPT/Claude-like conversations
        """
        flow_name = session.active_flow
        flow = flow_registry.get_flow(flow_name)

        if not flow:
            return {
                "decision": FlowDecision.ABORT_FLOW,
                "reason": "Flow not found"
            }

        # Build prompt for Qwen
        slots_filled = json.dumps(session.flow_slots, ensure_ascii=False)
        slots_missing = ", ".join(session.flow_missing_slots) if session.flow_missing_slots else "aucun"

        prompt = f"""Tu es un routeur de conversation pour un assistant bancaire AFG/DBS.

CONTEXTE DE LA CONVERSATION :
- Flow actif : {flow_name}
- Description : {flow['description']}
- Informations déjà collectées : {slots_filled}
- Informations manquantes : {slots_missing}

MESSAGE UTILISATEUR : "{message}"

Tu dois décider parmi 4 options :

1. CONTINUE_FLOW : Le message contient des informations utiles pour le flow actif
   → Extrais les informations (slots) du message

2. NEW_FLOW : Le message demande une NOUVELLE opération bancaire complètement différente
   → Identifie le nouveau flow bancaire

3. GENERAL_CHAT : Le message est hors sujet (question, small talk, interruption)
   → Ce n'est PAS une opération bancaire, juste une discussion

4. ABORT_FLOW : Le message demande d'annuler/arrêter

Flows bancaires disponibles :
{flow_registry.format_flows_for_prompt()}

Réponds UNIQUEMENT en JSON strict :
{{
  "decision": "CONTINUE_FLOW" | "NEW_FLOW" | "GENERAL_CHAT" | "ABORT_FLOW",
  "extracted_slots": {{}},  # Si CONTINUE_FLOW
  "new_flow_name": "nom" ou null,  # Si NEW_FLOW
  "reason": "explication courte"
}}

Exemples de slots à extraire pour le flow actuel :
{json.dumps(flow.get('slots', []), ensure_ascii=False)}
"""

        try:
            response = self.llm_model.generate(prompt, temperature=0.3)

            # Extract JSON
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())

                # Convert decision string to enum
                decision_str = result.get("decision", "GENERAL_CHAT")
                try:
                    decision = FlowDecision[decision_str]
                except KeyError:
                    decision = FlowDecision.GENERAL_CHAT

                return {
                    "decision": decision,
                    "extracted_slots": result.get("extracted_slots", {}),
                    "new_flow_name": result.get("new_flow_name"),
                    "reason": result.get("reason", "")
                }
            else:
                # Fallback
                return {
                    "decision": FlowDecision.CONTINUE_FLOW,
                    "extracted_slots": {},
                    "reason": "Failed to parse Qwen response"
                }

        except Exception as e:
            print(f"⚠️  FlowRouter error: {e}")
            return {
                "decision": FlowDecision.CONTINUE_FLOW,
                "extracted_slots": {},
                "reason": f"Error: {e}"
            }

    def extract_slots_with_qwen(self, message: str, flow_name: str, missing_slots: list) -> Dict[str, Any]:
        """
        Extract specific slot values from user message

        This enables progressive slot filling across multiple messages
        """
        if not self.llm_model:
            return {}

        flow = flow_registry.get_flow(flow_name)
        if not flow:
            return {}

        prompt = f"""Extrais les informations du message utilisateur pour le flow bancaire.

Flow : {flow_name}
Informations manquantes : {', '.join(missing_slots)}

Message : "{message}"

Extrais UNIQUEMENT les informations présentes dans le message.
Réponds en JSON :
{{
  "amount": nombre ou null,
  "currency": "XOF" | "EUR" | "USD" ou null,
  "beneficiary_name": "nom" ou null,
  "duration_months": nombre ou null
}}

Si une information n'est pas dans le message, mets null.
"""

        try:
            response = self.llm_model.generate(prompt, temperature=0.3)
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                slots = json.loads(json_match.group())
                # Remove null values
                return {k: v for k, v in slots.items() if v is not None}
            else:
                return {}
        except Exception as e:
            print(f"⚠️  Slot extraction error: {e}")
            return {}

    def generate_next_question(self, session: SessionState) -> str:
        """
        Generate the next question to ask user for missing information

        Like GPT/Claude: "What about the duration?"
        """
        if not session.flow_missing_slots:
            return ""

        flow = flow_registry.get_flow(session.active_flow)
        if not flow:
            return ""

        # Map slot names to French questions
        slot_questions = {
            "amount": "Quel montant souhaitez-vous ?",
            "currency": "En quelle devise ? (XOF, EUR, USD)",
            "beneficiary_name": "À qui souhaitez-vous envoyer l'argent ?",
            "duration_months": "Sur combien de mois ? (ex: 12, 24, 36...)",
            "beneficiary_account": "Quel est le numéro de compte du bénéficiaire ?",
        }

        next_slot = session.flow_missing_slots[0]
        question = slot_questions.get(next_slot, f"Quelle est la valeur de {next_slot} ?")

        # Add collected info as context
        if session.flow_slots:
            filled = ", ".join([f"{k}: {v}" for k, v in session.flow_slots.items()])
            return f"J'ai noté : {filled}.\n{question}"
        else:
            return question

    def format_interruption_response(self, general_response: str, session: SessionState) -> str:
        """
        Format response for interruptions - respond to off-topic then remind of flow

        Exactly like GPT/Claude: answer the question, then "By the way, about your transfer..."
        """
        if not session.active_flow or session.flow_status != FlowStatus.IN_FLOW:
            return general_response

        flow = flow_registry.get_flow(session.active_flow)
        if not flow:
            return general_response

        # Get flow summary
        filled = ", ".join([f"{k}: {v}" for k, v in session.flow_slots.items()]) if session.flow_slots else "aucune"

        # Generate next question
        next_question = self.generate_next_question(session)

        return f"{general_response}\n\n" \
               f"📌 **Au fait**, nous étions en train de traiter votre {flow['description'].lower()}.\n" \
               f"Informations collectées : {filled}\n" \
               f"{next_question}"
