# intents/banking/consulter_solde.py

from intents.base import BaseIntent, IntentType, IntentResult, ExecutionContext
from typing import Dict


class ConsulterSoldeIntent(BaseIntent):
    """Check account balance - Transactional intent"""

    # Metadata
    name = "CONSULTER_SOLDE"
    description = "Consulter le solde d'un compte bancaire"
    category = "banking"

    # Intent type
    intent_type = IntentType.TRANSACTIONAL
    tools = ["backend"]

    # Training examples
    examples = [
        "c'est quoi mon solde ?",
        "je veux voir ce qu'il me reste sur mon compte",
        "solde compte courant stp",
        "combien j'ai sur mon compte ?",
        "mon solde actuel",
        "quel est mon solde",
        "affiche moi mon solde",
        "je veux connaitre mon solde",
        "solde de mon compte epargne",
        "combien il me reste",
        "balance de mon compte",
        "j'ai combien sur mon compte",
        "montre moi mon solde",
        "solde disponible",
        "consultation de solde",
        "je veux voir mon argent",
        "combien d'argent j'ai",
        "solde compte salaire",
        "mon compte c'est combien",
        "afficher le solde"
    ]

    # Keyword rules
    keywords = [
        r'\bsolde\b',
        r'\bbalance\b',
        r'\bcombien\b.*\b(j\'?ai|reste|argent)\b',
        r'\baffich\w+.*\bsolde\b',
        r'\bconsult\w+.*\bsolde\b',
    ]

    # Slot schema
    slots = {
        "required": [],
        "optional": ["compte_type", "compte_id"],
        "schema": {
            "compte_type": {
                "type": "string",
                "values": ["courant", "epargne", "salaire", "carte"],
                "description": "Type de compte"
            },
            "compte_id": {
                "type": "string",
                "description": "ID du compte"
            }
        }
    }

    # No confirmation needed
    requires_confirmation = False

    def execute(self, slots: Dict, context: ExecutionContext) -> IntentResult:
        """Execute balance check"""
        compte_type = slots.get('compte_type', 'courant')
        compte_id = slots.get('compte_id')

        try:
            # Call backend
            if context.backend is None:
                return IntentResult(
                    success=False,
                    data={},
                    error="Backend not available"
                )

            result = context.backend.consulter_solde(
                user_id=context.user_id,
                compte_type=compte_type,
                compte_id=compte_id
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
        """Format balance response"""
        if not result.success:
            return f"❌ Erreur : {result.error}"

        data = result.data

        # Format currency amount
        solde = data.get('solde', 0)
        devise = data.get('devise', 'XOF')
        compte_type = data.get('compte_type', 'courant')
        date = data.get('date', '')

        response = f"""Votre solde sur le compte {compte_type} :
💰 {solde:,.0f} {devise}

Mis à jour le {date}"""

        return response
