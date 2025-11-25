# session/unified_session.py

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime
from enum import Enum


class DomainType(Enum):
    """Domain types for multi-mode assistant"""
    BANKING = "banking"
    PERSONAL = "personal"
    CODING = "coding"
    GENERAL = "general"


@dataclass
class UnifiedSession:
    """
    Unified session supporting 3 main modes: Banking, Personal, Coding

    User can switch between modes seamlessly in same conversation
    """
    user_id: str
    session_id: str
    created_at: datetime = field(default_factory=datetime.now)

    # Conversation history (all modes mixed)
    history: List[Dict] = field(default_factory=list)

    # Mode-specific contexts
    banking_context: Dict = field(default_factory=lambda: {
        'current_account': 'courant',
        'pending_transfer': None,
        'last_balance': None,
        'transaction_in_progress': False,
    })

    coding_context: Dict = field(default_factory=lambda: {
        'current_file': None,
        'current_language': None,
        'last_function': None,
        'repo_path': None,
        'editing_mode': False,
    })

    personal_context: Dict = field(default_factory=lambda: {
        'last_email_thread': None,
        'calendar_view': 'week',
        'last_note_id': None,
    })

    # Current state
    current_mode: Optional[DomainType] = None
    last_mode: Optional[DomainType] = None

    # User preferences
    preferences: Dict = field(default_factory=dict)

    def switch_mode(self, new_mode: DomainType, reason: str = "auto-detected"):
        """Switch to a new mode"""
        if new_mode != self.current_mode:
            self.last_mode = self.current_mode
            self.current_mode = new_mode
            print(f"\n🔄 Mode switched: {self.last_mode or 'START'} → {new_mode.value} ({reason})")

    def get_context(self, mode: DomainType = None) -> Dict:
        """Get context for specific mode"""
        target_mode = mode or self.current_mode

        context_map = {
            DomainType.BANKING: self.banking_context,
            DomainType.CODING: self.coding_context,
            DomainType.PERSONAL: self.personal_context,
        }

        return context_map.get(target_mode, {})

    def update_context(self, updates: Dict, mode: DomainType = None):
        """Update mode-specific context"""
        context = self.get_context(mode)
        context.update(updates)

    def add_to_history(self, message: str, response: str, intent: str, mode: DomainType):
        """Add interaction to history"""
        self.history.append({
            'timestamp': datetime.now().isoformat(),
            'mode': mode.value,
            'intent': intent,
            'user': message,
            'assistant': response,
        })

    def get_mode_display(self) -> str:
        """Get current mode for display"""
        if not self.current_mode:
            return "GENERAL"

        mode_emoji = {
            DomainType.BANKING: "🏦 BANKING",
            DomainType.CODING: "💻 CODING",
            DomainType.PERSONAL: "📧 PERSONAL",
            DomainType.GENERAL: "💬 GENERAL",
        }

        return mode_emoji.get(self.current_mode, "💬 GENERAL")
