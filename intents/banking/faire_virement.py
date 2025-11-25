# intents/banking/faire_virement.py

from intents.base import BaseIntent, IntentType, IntentResult, ExecutionContext
from typing import Dict


class FaireVirementIntent(BaseIntent):
    """Make a money transfer - Transactional intent with confirmation"""

    # Metadata
    name = "FAIRE_VIREMENT"
    description = "Effectuer un virement bancaire"
    category = "banking"

    # Intent type
    intent_type = IntentType.TRANSACTIONAL
    tools = ["backend"]

    # Training examples
    examples = [
        "je veux faire un virement",
        "transferer de l'argent",
        "envoyer 50000 xof a mon frere",
        "faire un transfert",
        "virement de 100000",
        "je veux payer une facture",
        "transfert vers un autre compte",
        "envoyer de l'argent",
        "virement interne",
        "payer quelqu'un",
        "transfer mobile money",
        "je veux virer 75000 fcfa",
        "faire un paiement",
        "envoyer argent a pierre",
        "virement bancaire",
        "transfert international",
        "payer fournisseur",
        "je dois envoyer 200000",
        "virer sur le compte de marie",
        "transfer vers orange money"
    ]

    # Keyword rules
    keywords = [
        r'\bvirement\b',
        r'\btransfer\w*\b',
        r'\benvoyer\b.*\bargent\b',
        r'\bpayer\b',
        r'\bvirer\b',
    ]

    # Slot schema
    slots = {
        "required": ["montant", "destinataire"],
        "optional": ["compte_source", "motif", "rib_destinataire"],
        "schema": {
            "montant": {
                "type": "number",
                "description": "Montant en XOF",
                "min": 100,
                "max": 10000000
            },
            "destinataire": {
                "type": "string",
                "description": "Nom du bénéficiaire"
            },
            "compte_source": {
                "type": "string",
                "values": ["courant", "epargne", "salaire"],
                "description": "Compte source"
            },
            "motif": {
                "type": "string",
                "description": "Motif du virement"
            },
            "rib_destinataire": {
                "type": "string",
                "description": "RIB ou numéro de compte du destinataire"
            }
        }
    }

    # Requires confirmation
    requires_confirmation = True

    def execute(self, slots: Dict, context: ExecutionContext) -> IntentResult:
        """Execute transfer"""
        montant = slots.get('montant')
        destinataire = slots.get('destinataire')
        compte_source = slots.get('compte_source', 'courant')
        motif = slots.get('motif', 'Virement')
        rib_destinataire = slots.get('rib_destinataire')

        try:
            # Call backend
            if context.backend is None:
                return IntentResult(
                    success=False,
                    data={},
                    error="Backend not available"
                )

            result = context.backend.faire_virement(
                user_id=context.user_id,
                montant=montant,
                destinataire=destinataire,
                compte_source=compte_source,
                motif=motif,
                rib_destinataire=rib_destinataire
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
        """Format transfer response"""
        if not result.success:
            return f"❌ Erreur : {result.error}"

        data = result.data

        response = f"""✅ Virement effectué avec succès !

Montant : {data.get('montant', 0):,.0f} {data.get('devise', 'XOF')}
Destinataire : {data.get('destinataire', '')}
Référence : {data.get('reference', '')}
Date : {data.get('date', '')}

Nouveau solde : {data.get('nouveau_solde', 0):,.0f} {data.get('devise', 'XOF')}"""

        return response

    def get_confirmation_message(self, slots: Dict) -> str:
        """Custom confirmation message"""
        montant = slots.get('montant', 0)
        destinataire = slots.get('destinataire', 'inconnu')

        return f"""⚠️  Confirmation requise :

Vous allez virer {montant:,.0f} XOF à {destinataire}.

Confirmez-vous cette opération ? (oui/non)"""
