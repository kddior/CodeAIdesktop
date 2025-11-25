# intents/banking/obtenir_releve.py

from intents.base import BaseIntent, IntentType, IntentResult, ExecutionContext
from typing import Dict


class ObtenirReleveIntent(BaseIntent):
    """Get account statement - Transactional intent"""

    # Metadata
    name = "OBTENIR_RELEVE"
    description = "Obtenir un relevé de compte"
    category = "banking"

    # Intent type
    intent_type = IntentType.TRANSACTIONAL
    tools = ["backend"]

    # Training examples
    examples = [
        "je veux mon releve",
        "releve de compte",
        "extrait de compte",
        "envoie moi mon releve",
        "releve du mois dernier",
        "je veux un pdf de mes operations",
        "releve bancaire",
        "historique complet",
        "releve de janvier",
        "mes operations du mois",
        "extrait de mes mouvements",
        "je veux voir toutes mes transactions",
        "releve de compte courant",
        "document de mes operations",
        "releve sur 3 mois",
        "historique des transactions",
        "besoin de mon releve",
        "releve annuel",
        "releve de l'annee",
        "extrait compte epargne"
    ]

    # Keyword rules
    keywords = [
        r'\breleve\b',
        r'\bextrait\b.*\bcompte\b',
        r'\bhistorique\b.*\b(complet|transactions)\b',
        r'\bpdf\b.*\b(operations|transactions)\b',
    ]

    # Slot schema
    slots = {
        "required": [],
        "optional": ["periode", "compte_type", "format"],
        "schema": {
            "periode": {
                "type": "string",
                "description": "Période du relevé (mois, année, dates)",
                "examples": ["janvier", "mois dernier", "2024", "3 mois"]
            },
            "compte_type": {
                "type": "string",
                "values": ["courant", "epargne", "salaire"],
                "description": "Type de compte"
            },
            "format": {
                "type": "string",
                "values": ["pdf", "excel", "email"],
                "description": "Format du relevé"
            }
        }
    }

    # No confirmation needed
    requires_confirmation = False

    def execute(self, slots: Dict, context: ExecutionContext) -> IntentResult:
        """Execute statement request"""
        periode = slots.get('periode', 'mois en cours')
        compte_type = slots.get('compte_type', 'courant')
        format_releve = slots.get('format', 'pdf')

        try:
            # Call backend
            if context.backend is None:
                return IntentResult(
                    success=False,
                    data={},
                    error="Backend not available"
                )

            result = context.backend.obtenir_releve(
                user_id=context.user_id,
                periode=periode,
                compte_type=compte_type,
                format_releve=format_releve
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
        """Format statement response"""
        if not result.success:
            return f"❌ Erreur : {result.error}"

        data = result.data

        response = f"""📄 Relevé de compte généré

Compte : {data.get('compte_type', 'courant')}
Période : {data.get('periode', '')}
Format : {data.get('format', 'PDF')}"""

        if data.get('url'):
            response += f"\n\n🔗 Télécharger : {data['url']}"

        if data.get('email_sent'):
            response += f"\n\n📧 Le relevé a été envoyé à {data.get('email', 'votre adresse email')}"

        return response
