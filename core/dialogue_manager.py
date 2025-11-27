from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime

import sys
sys.path.append('..')
from config.config import *


class DialogueState(Enum):
    """States of the conversation"""
    START = "start"
    INTENT_SELECTED = "intent_selected"
    SLOT_FILLING = "slot_filling"
    ACTION = "action"
    CONFIRM = "confirm"
    DONE = "done"
    LLM_CHAT = "llm_chat"


@dataclass
class ConversationContext:
    """Context for a single conversation session"""
    user_id: str
    session_id: str
    state: DialogueState = DialogueState.START
    intent: Optional[str] = None
    slots: Dict[str, Any] = field(default_factory=dict)
    missing_slots: List[str] = field(default_factory=list)
    current_slot_to_fill: Optional[str] = None
    action_result: Optional[Dict] = None
    confirmation_pending: bool = False
    history: List[Dict] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)

    def add_to_history(self, user_msg: str, bot_msg: str, intent: str = None, slots: Dict = None):
        """Add interaction to history"""
        self.history.append({
            'timestamp': datetime.now().isoformat(),
            'user': user_msg,
            'bot': bot_msg,
            'intent': intent,
            'slots': slots,
            'state': self.state.value
        })
        self.last_updated = datetime.now()


class DialogueManager:
    """
    Manages conversation flow and state transitions

    State machine:
    START → INTENT_SELECTED → SLOT_FILLING → ACTION → CONFIRM → DONE
                         ↘ (if OTHER) → LLM_CHAT
    """

    def __init__(self, intent_detector, slot_extractor, backend, response_generator):
        self.intent_detector = intent_detector
        self.slot_extractor = slot_extractor
        self.backend = backend
        self.response_generator = response_generator

        # Store active conversations
        self.conversations: Dict[str, ConversationContext] = {}

        # Define which intents require confirmation
        self.confirmation_required = {
            "FAIRE_VIREMENT": True,
            "SIMULATION_CREDIT": False,  # Just simulation, no action
            "CONSULTER_SOLDE": False,
            "DISCUSSION_COMPTE": False,
            "OBTENIR_RELEVE": False,
        }

    def get_or_create_context(self, user_id: str, session_id: str = None) -> ConversationContext:
        """Get existing context or create new one"""
        if session_id is None:
            session_id = f"{user_id}_{datetime.now().timestamp()}"

        key = f"{user_id}_{session_id}"

        if key not in self.conversations:
            self.conversations[key] = ConversationContext(
                user_id=user_id,
                session_id=session_id
            )

        return self.conversations[key]

    def process_message(self, user_id: str, message: str, session_id: str = None) -> Dict:
        """
        Main entry point - process a user message

        Returns:
            {
                'response': str,
                'state': str,
                'intent': str,
                'slots': dict,
                'action_result': dict (if action was performed),
                'needs_confirmation': bool
            }
        """
        context = self.get_or_create_context(user_id, session_id)

        # Handle based on current state
        if context.state == DialogueState.START:
            return self._handle_start(context, message)

        elif context.state == DialogueState.SLOT_FILLING:
            return self._handle_slot_filling(context, message)

        elif context.state == DialogueState.CONFIRM:
            return self._handle_confirmation(context, message)

        elif context.state == DialogueState.LLM_CHAT:
            return self._handle_llm_chat(context, message)

        else:
            # Default: restart
            return self._handle_start(context, message)

    def _handle_start(self, context: ConversationContext, message: str) -> Dict:
        """Handle new message - detect intent and extract slots"""

        # Step 1: Detect intent
        intent_result = self.intent_detector.detect(message)
        intent = intent_result['intent']
        confidence = intent_result['confidence']

        context.intent = intent

        # Step 2: If OTHER, go to LLM chat
        if intent == "OTHER":
            context.state = DialogueState.LLM_CHAT
            response = self.response_generator.generate_other_response(message)
            context.add_to_history(message, response, intent)
            return {
                'response': response,
                'state': context.state.value,
                'intent': intent,
                'confidence': confidence
            }

        # Step 3: Extract slots
        slot_result = self.slot_extractor.extract(message, intent)
        context.slots = {k: v['value'] for k, v in slot_result['slots'].items()}
        context.missing_slots = slot_result['missing_required']

        # Step 4: Determine next state
        if slot_result['ready_for_action']:
            # All required slots filled - go to action
            return self._execute_action(context, message)
        else:
            # Need more slots - go to slot filling
            context.state = DialogueState.SLOT_FILLING
            context.current_slot_to_fill = context.missing_slots[0] if context.missing_slots else None

            response = self.response_generator.generate_slot_question(
                intent, context.current_slot_to_fill, context.slots
            )

            context.add_to_history(message, response, intent, context.slots)

            return {
                'response': response,
                'state': context.state.value,
                'intent': intent,
                'slots': context.slots,
                'missing_slots': context.missing_slots
            }

    def _handle_slot_filling(self, context: ConversationContext, message: str) -> Dict:
        """Handle slot filling - user is providing missing information"""

        # Extract slots from this message
        slot_result = self.slot_extractor.extract(message, context.intent)

        # Update context slots
        for key, data in slot_result['slots'].items():
            if data['value'] is not None and data['status'] == 'ok':
                context.slots[key] = data['value']

        # Re-check if ready for action
        slot_result_full = self.slot_extractor.extract(
            " ".join([str(v) for v in context.slots.values()]),
            context.intent
        )

        # Update missing slots
        context.missing_slots = slot_result['missing_required']

        if slot_result['ready_for_action'] or len(context.missing_slots) == 0:
            # All slots filled - execute action
            return self._execute_action(context, message)
        else:
            # Still missing slots - ask for next one
            context.current_slot_to_fill = context.missing_slots[0]

            response = self.response_generator.generate_slot_question(
                context.intent, context.current_slot_to_fill, context.slots
            )

            context.add_to_history(message, response, context.intent, context.slots)

            return {
                'response': response,
                'state': context.state.value,
                'intent': context.intent,
                'slots': context.slots,
                'missing_slots': context.missing_slots
            }

    def _execute_action(self, context: ConversationContext, message: str) -> Dict:
        """Execute the backend action"""

        # Check if confirmation is needed
        if self.confirmation_required.get(context.intent, False):
            if not context.confirmation_pending:
                # Ask for confirmation first
                context.state = DialogueState.CONFIRM
                context.confirmation_pending = True

                response = self.response_generator.generate_confirmation_request(
                    context.intent, context.slots
                )

                context.add_to_history(message, response, context.intent, context.slots)

                return {
                    'response': response,
                    'state': context.state.value,
                    'intent': context.intent,
                    'slots': context.slots,
                    'needs_confirmation': True
                }

        # Execute action
        context.state = DialogueState.ACTION

        try:
            action_result = self.backend.execute(context.intent, context.slots)
            context.action_result = action_result

            # Generate response
            response = self.response_generator.generate_action_response(
                context.intent, context.slots, action_result
            )

            # Mark as done
            context.state = DialogueState.DONE

            context.add_to_history(message, response, context.intent, context.slots)

            return {
                'response': response,
                'state': context.state.value,
                'intent': context.intent,
                'slots': context.slots,
                'action_result': action_result
            }

        except Exception as e:
            response = f"Désolé, une erreur s'est produite: {str(e)}"
            context.add_to_history(message, response, context.intent, context.slots)
            return {
                'response': response,
                'state': 'error',
                'intent': context.intent,
                'error': str(e)
            }

    def _handle_confirmation(self, context: ConversationContext, message: str) -> Dict:
        """Handle confirmation response"""

        message_lower = message.lower()

        # Check for positive confirmation
        confirmations = ['oui', 'yes', 'ok', 'confirme', 'valide', 'd\'accord', 'daccord']
        rejections = ['non', 'no', 'annule', 'stop', 'pas']

        if any(word in message_lower for word in confirmations):
            # User confirmed - execute action
            context.confirmation_pending = False
            return self._execute_action(context, message)

        elif any(word in message_lower for word in rejections):
            # User rejected - cancel
            context.state = DialogueState.DONE
            response = "D'accord, opération annulée. Puis-je vous aider avec autre chose ?"

            context.add_to_history(message, response, context.intent, context.slots)

            return {
                'response': response,
                'state': context.state.value,
                'intent': context.intent,
                'action': 'cancelled'
            }

        else:
            # Unclear - ask again
            response = "Je n'ai pas bien compris. Souhaitez-vous confirmer cette opération ? Répondez par 'oui' ou 'non'."

            context.add_to_history(message, response, context.intent, context.slots)

            return {
                'response': response,
                'state': context.state.value,
                'intent': context.intent,
                'needs_confirmation': True
            }

    def _handle_llm_chat(self, context: ConversationContext, message: str) -> Dict:
        """Handle general chat (OTHER intent)"""

        response = self.response_generator.generate_other_response(message)

        context.add_to_history(message, response, "OTHER")

        return {
            'response': response,
            'state': context.state.value,
            'intent': 'OTHER'
        }

    def reset_context(self, user_id: str, session_id: str = None):
        """Reset conversation context"""
        key = f"{user_id}_{session_id}" if session_id else None

        if key and key in self.conversations:
            del self.conversations[key]
        elif not session_id:
            # Delete all sessions for this user
            keys_to_delete = [k for k in self.conversations.keys() if k.startswith(f"{user_id}_")]
            for k in keys_to_delete:
                del self.conversations[k]

    def update(self, session, intent: str, slots: Dict, user_message: str) -> Dict:
        """
        Update dialogue state based on new message

        Args:
            session: SessionState object
            intent: Detected intent
            slots: Extracted slots dict
            user_message: Original user message

        Returns:
            Dictionary with dialogue state info
        """
        # Get or create conversation context
        context = self.get_or_create_context(session.user_id, session.session_id)

        # Update context with new intent and slots
        context.intent = intent
        if isinstance(slots, dict) and 'slots' in slots:
            # Handle nested slots structure
            extracted_slots = slots.get('slots', {})
            for k, v in extracted_slots.items():
                if isinstance(v, dict) and 'value' in v:
                    context.slots[k] = v['value']
                else:
                    context.slots[k] = v
        elif isinstance(slots, dict):
            context.slots.update(slots)

        # Return dialogue state
        return {
            'state': context.state.value,
            'intent': intent,
            'slots': context.slots,
            'missing_slots': context.missing_slots,
            'needs_confirmation': context.confirmation_pending
        }
