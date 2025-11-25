# -*- coding: utf-8 -*-
"""
Session State Management - Multi-turn Conversation Memory
Like GPT/Claude: tracks active flows, slots, and conversation context
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum


class FlowStatus(Enum):
    """Flow execution status"""
    IDLE = "idle"  # No active flow
    IN_FLOW = "in_flow"  # Currently collecting information
    COMPLETED = "completed"  # Flow finished
    ABORTED = "aborted"  # User cancelled


class SessionState:
    """
    Conversation session state - THE MISSING PIECE

    This is what GPT/Claude use server-side to remember:
    - What flow is active
    - What information has been collected
    - What's still missing
    - Last question asked
    """

    def __init__(self, user_id: str, session_id: str = "default"):
        self.user_id = user_id
        self.session_id = session_id

        # Active flow tracking
        self.active_flow: Optional[str] = None
        self.flow_status: FlowStatus = FlowStatus.IDLE
        self.flow_slots: Dict[str, Any] = {}
        self.flow_missing_slots: List[str] = []
        self.last_question: Optional[str] = None

        # Slot filling tracking
        self.slot_filling_mode: bool = False  # True when actively collecting slots
        self.current_slot_being_asked: Optional[str] = None  # Which slot we're currently asking for
        self.slot_extraction_attempts: Dict[str, int] = {}  # Track retry attempts per slot
        self.awaiting_confirmation: bool = False  # True when waiting for user to confirm all slots

        # Topic change tracking (like Claude/GPT)
        self.topic_boundaries: List[int] = []  # Indices where topics changed
        self.current_topic_start_index: int = 0  # Where current topic started
        self.awaiting_topic_change_confirmation: bool = False  # Waiting for user to confirm topic change
        self.pending_topic_change_message: Optional[str] = None  # Store new topic message
        self.topic_change_suggestion: Optional[str] = None  # Confirmation message to show
        self.previous_intent: Optional[str] = None  # Track last intent for comparison

        # Conversation history
        self.history: List[Dict] = []
        self.created_at = datetime.now()
        self.updated_at = datetime.now()

    def start_flow(self, flow_name: str, required_slots: List[str], initial_slots: Dict = None):
        """
        Start a new flow

        Args:
            flow_name: Name of the flow (e.g., "TRANSFER_MONEY")
            required_slots: List of required slot names
            initial_slots: Any slots already extracted from the initial message
        """
        self.active_flow = flow_name
        self.flow_status = FlowStatus.IN_FLOW
        self.flow_slots = initial_slots or {}
        self.flow_missing_slots = [
            slot for slot in required_slots if slot not in self.flow_slots
        ]
        self.updated_at = datetime.now()

    def update_slots(self, new_slots: Dict[str, Any]):
        """
        Update flow slots with new information

        Args:
            new_slots: Dictionary of slot_name -> value
        """
        self.flow_slots.update(new_slots)
        # Update missing slots list
        self.flow_missing_slots = [
            slot for slot in self.flow_missing_slots if slot not in new_slots
        ]
        self.updated_at = datetime.now()

    def is_flow_complete(self) -> bool:
        """Check if all required slots are filled"""
        return len(self.flow_missing_slots) == 0

    def complete_flow(self):
        """Mark flow as completed"""
        self.flow_status = FlowStatus.COMPLETED
        self.updated_at = datetime.now()

    def abort_flow(self):
        """Cancel current flow"""
        self.flow_status = FlowStatus.ABORTED
        self.updated_at = datetime.now()

    def reset_flow(self):
        """Clear flow state"""
        self.active_flow = None
        self.flow_status = FlowStatus.IDLE
        self.flow_slots = {}
        self.flow_missing_slots = []
        self.last_question = None
        self.updated_at = datetime.now()

    def reset_flow_keep_history(self):
        """
        Reset flow state but keep conversation history
        Used when topic changes - like Claude/GPT behavior
        """
        self.active_flow = None
        self.flow_status = FlowStatus.IDLE
        self.flow_slots = {}
        self.flow_missing_slots = []
        self.last_question = None
        self.slot_filling_mode = False
        self.current_slot_being_asked = None
        self.awaiting_confirmation = False
        self.slot_extraction_attempts = {}
        self.updated_at = datetime.now()

    def mark_topic_boundary(self):
        """
        Add a topic boundary marker to conversation history
        Like Claude's implicit topic tracking
        """
        boundary_index = len(self.history)
        self.topic_boundaries.append(boundary_index)
        self.current_topic_start_index = boundary_index

        # Add system marker to history
        self.history.append({
            "timestamp": datetime.now().isoformat(),
            "system": "--- CHANGEMENT DE SUJET ---",
            "type": "topic_boundary"
        })
        self.updated_at = datetime.now()

    def get_current_topic_history(self) -> List[Dict]:
        """Get only messages from current topic"""
        return self.history[self.current_topic_start_index:]

    def get_previous_user_messages(self, n: int = 3) -> List[str]:
        """
        Get last N user messages (excluding system messages)

        Args:
            n: Number of recent user messages to retrieve

        Returns:
            List of user message strings
        """
        user_messages = [
            turn['user'] for turn in self.history
            if 'user' in turn and turn['user']
        ]
        return user_messages[-n:] if len(user_messages) > n else user_messages

    def add_to_history(self, message: str, response: str, intent: str, metadata: Dict = None):
        """Add message to conversation history"""
        self.history.append({
            "timestamp": datetime.now().isoformat(),
            "user": message,
            "assistant": response,
            "intent": intent,
            "metadata": metadata or {}
        })
        self.updated_at = datetime.now()

    def get_recent_conversation_context(self, num_turns: int = 3, focus_current_topic: bool = True) -> str:
        """
        Get recent conversation history as context for LLM
        With smart topic focusing (like Claude/GPT)

        Args:
            num_turns: Number of recent conversation turns to include (default: 3)
            focus_current_topic: If True, prioritize current topic over old context

        Returns:
            Formatted conversation history string
        """
        if not self.history:
            return ""

        if focus_current_topic and self.current_topic_start_index > 0:
            # Split history into previous topics and current topic
            previous_history = self.history[:self.current_topic_start_index]
            current_history = self.history[self.current_topic_start_index:]

            context_lines = []

            # Add brief summary of previous context (if exists)
            if previous_history:
                # Count only user/assistant messages (exclude system markers)
                prev_message_count = sum(1 for turn in previous_history if 'user' in turn or 'assistant' in turn)
                context_lines.append("=== CONTEXTE PRÉCÉDENT (résumé) ===")
                context_lines.append(f"[{prev_message_count} messages sur sujet antérieur - disponible si référencé explicitement]")
                context_lines.append("")

            # Add full current topic with all details
            context_lines.append("=== CONVERSATION ACTUELLE ===")
            for turn in current_history:
                if 'user' in turn:
                    context_lines.append(f"User: {turn['user']}")
                if 'assistant' in turn:
                    context_lines.append(f"Assistant: {turn['assistant']}")
                if 'system' in turn and turn.get('type') == 'topic_boundary':
                    context_lines.append(f"[{turn['system']}]")
                context_lines.append("")

            context_lines.append("=== FIN CONVERSATION ACTUELLE ===")

            return "\n".join(context_lines)

        else:
            # Normal behavior - recent N turns (backward compatibility)
            recent = self.history[-num_turns:] if len(self.history) > num_turns else self.history

            if not recent:
                return ""

            # Format for LLM context
            context_lines = ["=== HISTORIQUE RÉCENT DE CONVERSATION ===\n"]
            for turn in recent:
                if 'user' in turn:
                    context_lines.append(f"User: {turn['user']}")
                if 'assistant' in turn:
                    context_lines.append(f"Assistant: {turn['assistant']}\n")

            context_lines.append("=== FIN HISTORIQUE ===")
            return "\n".join(context_lines)

    def get_flow_summary(self) -> str:
        """Get human-readable flow summary"""
        if not self.active_flow:
            return "Aucun flow actif"

        filled = ", ".join([f"{k}: {v}" for k, v in self.flow_slots.items()])
        missing = ", ".join(self.flow_missing_slots) if self.flow_missing_slots else "aucun"

        return f"Flow actif: {self.active_flow}\n" \
               f"Informations collectées: {filled or 'aucune'}\n" \
               f"Informations manquantes: {missing}"

    def to_dict(self) -> Dict:
        """Serialize to dictionary"""
        return {
            "user_id": self.user_id,
            "session_id": self.session_id,
            "active_flow": self.active_flow,
            "flow_status": self.flow_status.value if self.flow_status else None,
            "flow_slots": self.flow_slots,
            "flow_missing_slots": self.flow_missing_slots,
            "last_question": self.last_question,
            "history_count": len(self.history),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }

    def __repr__(self):
        return f"SessionState(user={self.user_id}, flow={self.active_flow}, status={self.flow_status.value})"


class SessionManager:
    """
    Manages multiple user sessions
    """

    def __init__(self):
        self.sessions: Dict[str, SessionState] = {}

    def get_session(self, user_id: str, session_id: str = "default") -> SessionState:
        """Get or create session"""
        key = f"{user_id}:{session_id}"
        if key not in self.sessions:
            self.sessions[key] = SessionState(user_id, session_id)
        return self.sessions[key]

    def clear_session(self, user_id: str, session_id: str = "default"):
        """Clear session"""
        key = f"{user_id}:{session_id}"
        if key in self.sessions:
            del self.sessions[key]

    def get_all_sessions(self) -> List[SessionState]:
        """Get all active sessions"""
        return list(self.sessions.values())
