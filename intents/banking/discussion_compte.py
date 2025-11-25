# intents/banking/discussion_compte.py

from intents.base import BaseIntent, IntentType, IntentResult, ExecutionContext
from typing import Dict


class DiscussionCompteIntent(BaseIntent):
    """Discuss account activity - Transactional intent"""

    # Metadata
    name = "DISCUSSION_COMPTE"
    description = "Discuter des opérations et mouvements du compte"
    category = "banking"

    # Intent type
    intent_type = IntentType.TRANSACTIONAL
    tools = ["backend"]

    # Training examples
    examples = [
        "pourquoi ce debit sur mon compte ?",
        "c'est quoi cette operation de 5000 xof ?",
        "j'ai pas autorise ce retrait",
        "je comprends pas ce mouvement",
        "pourquoi mon compte est negatif ?",
        "c'est quoi ces frais ?",
        "expliquez moi cette transaction",
        "d'ou vient ce prelevement",
        "pourquoi j'ai ete debite",
        "je vois une operation bizarre",
        "c'est quoi ce retrait de 10000",
        "mon compte a ete debite pourquoi",
        "frais bancaires c'est combien",
        "transaction suspecte sur mon compte",
        "je veux comprendre mes operations",
        "historique de mes mouvements",
        "mes dernieres transactions",
        "qu'est ce qui s'est passe hier sur mon compte",
        "pourquoi cette sortie d'argent",
        "activite de mon compte"
    ]

    # Keyword rules
    keywords = [
        r'\bpourquoi\b.*\b(debit|operation|retrait|prelevement)\b',
        r'\btransaction\b.*\b(suspecte|bizarre)\b',
        r'\bfrais\b.*\bbancaire',
        r'\bhistorique\b',
        r'\bmouvements?\b',
        r'\boperations?\b',
    ]

    # Slot schema
    slots = {
        "required": [],
        "optional": ["montant", "date", "type_operation", "compte_type"],
        "schema": {
            "montant": {
                "type": "number",
                "description": "Montant de l'opération concernée"
            },
            "date": {
                "type": "string",
                "description": "Date de l'opération (hier, aujourd'hui, etc.)"
            },
            "type_operation": {
                "type": "string",
                "values": ["debit", "credit", "retrait", "virement", "frais"],
                "description": "Type d'opération"
            },
            "compte_type": {
                "type": "string",
                "values": ["courant", "epargne", "salaire"],
                "description": "Type de compte"
            }
        }
    }

    # No confirmation needed
    requires_confirmation = False

    def execute(self, slots: Dict, context: ExecutionContext) -> IntentResult:
        """Execute account discussion"""
        montant = slots.get('montant')
        date = slots.get('date')
        type_operation = slots.get('type_operation')
        compte_type = slots.get('compte_type', 'courant')

        try:
            # Call backend
            if context.backend is None:
                return IntentResult(
                    success=False,
                    data={},
                    error="Backend not available"
                )

            result = context.backend.discussion_compte(
                user_id=context.user_id,
                montant=montant,
                date=date,
                type_operation=type_operation,
                compte_type=compte_type
            )

            if result.get('success'):
                return IntentResult(
                    success=True,
                    data=result,
                    sources=[{'type': 'backend', 'name': 'Banking System'}]
                )
            else:
                return IntentResult(
                    success=False,
                    data={},
                    error=result.get('error', 'Unknown error')
                )

        except Exception as e:
            return IntentResult(
                success=False,
                data={},
                error=f"Execution failed: {str(e)}"
            )

    def format_response(self, result: IntentResult, slots: Dict) -> str:
        """Format discussion response"""
        if not result.success:
            return f"❌ Erreur : {result.error}"

        data = result.data
        operations = data.get('operations', [])

        if not operations:
            return "Je n'ai pas trouvé d'opérations récentes correspondant à votre demande."

        response = f"📋 Voici vos dernières opérations :\n\n"

        for op in operations[:5]:  # Show max 5 recent operations
            response += f"• {op.get('date', '')} : {op.get('type', '')} de {op.get('montant', 0):,.0f} {op.get('devise', 'XOF')}\n"
            response += f"  {op.get('description', '')}\n\n"

        if data.get('explication'):
            response += f"\n💡 {data['explication']}"

        return response
