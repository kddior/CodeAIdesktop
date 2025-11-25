# intents/general/other.py

from intents.base import BaseIntent, IntentType, IntentResult, ExecutionContext
from typing import Dict


class OtherIntent(BaseIntent):
    """General conversational intent - Handles greetings, thanks, etc."""

    # Metadata
    name = "OTHER"
    description = "Conversations générales (salutations, remerciements, etc.)"
    category = "general"

    # Intent type
    intent_type = IntentType.TRANSACTIONAL  # Uses backend for simple responses
    tools = ["backend"]

    # Training examples
    examples = [
        "bonjour",
        "salut",
        "merci",
        "ok",
        "d'accord",
        "au revoir",
        "bye",
        "comment ca va",
        "qui es-tu",
        "aide moi",
        "je comprends pas",
        "c'est quoi ca",
        "pardon",
        "excusez moi",
        "comment faire",
        "allo",
        "vous etes la",
        "ok merci",
        "non",
        "oui"
    ]

    # Keyword rules
    keywords = [
        r'\b(bonjour|salut|hello|coucou)\b',
        r'\b(merci|thanks)\b',
        r'\b(au\s+revoir|bye|adieu)\b',
        r'\b(aide|help)\b',
    ]

    # No slots needed
    slots = {
        "required": [],
        "optional": [],
        "schema": {}
    }

    # No confirmation needed
    requires_confirmation = False

    def execute(self, slots: Dict, context: ExecutionContext) -> IntentResult:
        """Execute general conversation"""
        message = context.message.lower()

        # Simple pattern matching for responses
        if any(word in message for word in ['bonjour', 'salut', 'hello', 'coucou', 'allo']):
            response_text = "Bonjour ! Comment puis-je vous aider aujourd'hui ?"
        elif any(word in message for word in ['merci', 'thanks']):
            response_text = "De rien ! N'hésitez pas si vous avez d'autres questions."
        elif any(word in message for word in ['au revoir', 'bye', 'adieu']):
            response_text = "Au revoir ! À bientôt !"
        elif any(word in message for word in ['qui es-tu', 'qui êtes-vous']):
            response_text = "Je suis votre assistant bancaire virtuel. Je peux vous aider avec vos comptes, virements, relevés et simulations de crédit."
        elif any(word in message for word in ['aide', 'help']):
            response_text = """Je peux vous aider avec :
• Consulter votre solde
• Effectuer des virements
• Obtenir des relevés de compte
• Simuler un crédit
• Discuter de vos opérations

Comment puis-je vous aider ?"""
        else:
            response_text = "Je comprends. Comment puis-je vous aider ?"

        return IntentResult(
            success=True,
            data={'response': response_text},
            sources=[]
        )

    def format_response(self, result: IntentResult, slots: Dict) -> str:
        """Format general response"""
        if not result.success:
            return "Désolé, je n'ai pas compris. Pouvez-vous reformuler ?"

        return result.data.get('response', 'Comment puis-je vous aider ?')
