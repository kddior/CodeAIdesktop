# intents/base.py

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from enum import Enum
from dataclasses import dataclass


class IntentType(Enum):
    """Type of intent determining routing strategy"""
    TRANSACTIONAL = "transactional"        # Backend only (virement, solde)
    INFORMATIONAL_INTERNAL = "rag"         # Internal docs only (policies, procedures)
    INFORMATIONAL_EXTERNAL = "web"         # Web search only (news, rates)
    HYBRID = "hybrid"                      # Multiple sources (explain topic, compare)


@dataclass
class IntentResult:
    """Result from intent execution"""
    success: bool
    data: Dict[str, Any]
    sources: List[Dict[str, Any]] = None
    error: Optional[str] = None
    confidence: float = 1.0


class BaseIntent(ABC):
    """
    Base class for all intents - Plugin architecture

    Each intent is self-contained with:
    - Metadata (name, description, category)
    - Training examples for intent detection
    - Keyword rules
    - Slot schema
    - Intent type and routing logic
    - Execution logic
    - Response formatting
    """

    # ===== METADATA (must override) =====
    name: str = None
    description: str = None
    category: str = "general"

    # ===== TRAINING DATA =====
    examples: List[str] = []
    keywords: List[str] = []

    # ===== SLOT CONFIGURATION =====
    slots: Dict[str, Any] = {
        "required": [],
        "optional": [],
        "schema": {}
    }

    # ===== INTENT TYPE & ROUTING =====
    intent_type: IntentType = IntentType.TRANSACTIONAL
    tools: List[str] = []  # Tools this intent can use: backend, rag, web, email, calendar

    # ===== CONFIRMATION =====
    requires_confirmation: bool = False

    # ===== METHODS TO IMPLEMENT =====

    @abstractmethod
    def execute(self, slots: Dict, context: 'ExecutionContext') -> IntentResult:
        """
        Execute the intent action

        Args:
            slots: Extracted and validated slots
            context: Execution context with access to all tools
                - context.backend: Banking backend
                - context.rag_tool: RAG search
                - context.web_search_tool: Web search
                - context.email_tool: Email operations
                - context.calendar_tool: Calendar operations

        Returns:
            IntentResult with success, data, sources, error
        """
        pass

    @abstractmethod
    def format_response(self, result: IntentResult, slots: Dict) -> str:
        """
        Format the response for the user

        Args:
            result: Result from execute()
            slots: Original slots

        Returns:
            Formatted response string
        """
        pass

    # ===== OPTIONAL: CUSTOM ROUTING =====

    def route(self, message: str, slots: Dict) -> IntentType:
        """
        Optional: Dynamic routing based on message content

        Override this to implement custom routing logic.
        Default: returns self.intent_type

        Args:
            message: User message
            slots: Extracted slots

        Returns:
            IntentType indicating which sources to use

        Example:
            # Route to web if user explicitly asks
            if "google" in message.lower() or "cherche" in message.lower():
                return IntentType.INFORMATIONAL_EXTERNAL

            # Route to RAG for internal policies
            if "politique" in message.lower() or "procédure" in message.lower():
                return IntentType.INFORMATIONAL_INTERNAL

            # Default routing
            return self.intent_type
        """
        return self.intent_type

    # ===== OPTIONAL: CUSTOM SLOT EXTRACTION =====

    def extract_slots(self, text: str) -> Dict:
        """
        Optional: Custom slot extraction logic

        If not implemented, uses default regex + LLM extraction

        Returns:
            Dictionary of extracted slots
        """
        return {}

    # ===== OPTIONAL: CUSTOM VALIDATION =====

    def validate_slots(self, slots: Dict) -> Dict:
        """
        Optional: Custom slot validation

        Returns:
            Dictionary with validated slots or errors
        """
        return slots

    # ===== OPTIONAL: CONFIRMATION MESSAGE =====

    def get_confirmation_message(self, slots: Dict) -> str:
        """
        Optional: Custom confirmation message

        Only used if requires_confirmation = True
        """
        return f"Confirmez-vous cette action ?"

    # ===== OPTIONAL: PRE/POST HOOKS =====

    def pre_execute(self, slots: Dict, context: 'ExecutionContext') -> Dict:
        """
        Optional: Hook called before execution

        Can modify slots or perform validation

        Returns:
            Modified slots or original
        """
        return slots

    def post_execute(self, result: IntentResult, slots: Dict, context: 'ExecutionContext') -> IntentResult:
        """
        Optional: Hook called after execution

        Can modify result or add additional processing

        Returns:
            Modified result or original
        """
        return result


@dataclass
class ExecutionContext:
    """
    Context passed to intent execution

    Provides access to all tools and resources
    """
    user_id: str
    session_id: str
    message: str

    # Tools (optional - provided if available)
    backend: Any = None
    rag_tool: Any = None
    web_search_tool: Any = None
    email_tool: Any = None
    calendar_tool: Any = None

    # Additional context
    conversation_history: List[Dict] = None
    user_profile: Dict = None
    metadata: Dict = None

    def __post_init__(self):
        if self.conversation_history is None:
            self.conversation_history = []
        if self.user_profile is None:
            self.user_profile = {}
        if self.metadata is None:
            self.metadata = {}
