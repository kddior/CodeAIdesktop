# intents/banking/simulation_credit.py

from intents.base import BaseIntent, IntentType, IntentResult, ExecutionContext
from typing import Dict


class SimulationCreditIntent(BaseIntent):
    """Simulate loan/credit - Transactional intent"""

    # Metadata
    name = "SIMULATION_CREDIT"
    description = "Simuler un crédit ou prêt bancaire"
    category = "banking"

    # Intent type
    intent_type = IntentType.TRANSACTIONAL
    tools = ["backend"]

    # Training examples
    examples = [
        "je veux emprunter",
        "simulation de pret",
        "je peux emprunter combien",
        "credit immobilier",
        "pret personnel",
        "capacite d'emprunt",
        "simuler un credit",
        "mensualite pour 5000000",
        "je veux un pret de 10 millions",
        "credit a la consommation",
        "calculer ma capacite de remboursement",
        "pret sur 5 ans",
        "combien je peux emprunter",
        "simulation mensualite",
        "taux d'interet pret",
        "je gagne 200000 par mois je peux emprunter combien",
        "credit auto",
        "pret entreprise",
        "financement projet",
        "demande de credit"
    ]

    # Keyword rules
    keywords = [
        r'\b(credit|pret)\b',
        r'\bemprunter\b',
        r'\bsimulation\b.*\b(credit|pret)\b',
        r'\bmensualite\b',
        r'\bcapacite\b.*\b(emprunt|remboursement)\b',
    ]

    # Slot schema
    slots = {
        "required": [],
        "optional": ["montant", "duree", "type_credit", "revenus"],
        "schema": {
            "montant": {
                "type": "number",
                "description": "Montant du crédit souhaité en XOF",
                "min": 100000,
                "max": 100000000
            },
            "duree": {
                "type": "number",
                "description": "Durée du prêt en années",
                "min": 1,
                "max": 30
            },
            "type_credit": {
                "type": "string",
                "values": ["immobilier", "personnel", "auto", "consommation", "entreprise"],
                "description": "Type de crédit"
            },
            "revenus": {
                "type": "number",
                "description": "Revenus mensuels en XOF",
                "min": 0
            }
        }
    }

    # No confirmation needed (it's just a simulation)
    requires_confirmation = False

    def execute(self, slots: Dict, context: ExecutionContext) -> IntentResult:
        """Execute credit simulation"""
        montant = slots.get('montant')
        duree = slots.get('duree', 10)
        type_credit = slots.get('type_credit', 'personnel')
        revenus = slots.get('revenus')

        try:
            # Call backend
            if context.backend is None:
                return IntentResult(
                    success=False,
                    data={},
                    error="Backend not available"
                )

            result = context.backend.simulation_credit(
                user_id=context.user_id,
                montant=montant,
                duree=duree,
                type_credit=type_credit,
                revenus=revenus
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
        """Format simulation response"""
        if not result.success:
            return f"❌ Erreur : {result.error}"

        data = result.data

        response = f"""💰 Simulation de crédit

Type : {data.get('type_credit', 'personnel').capitalize()}
Montant : {data.get('montant', 0):,.0f} XOF
Durée : {data.get('duree', 0)} ans
Taux : {data.get('taux', 0):.2f}%

Mensualité : {data.get('mensualite', 0):,.0f} XOF/mois
Coût total : {data.get('cout_total', 0):,.0f} XOF"""

        if data.get('dti'):
            response += f"\n\nTaux d'endettement : {data['dti']:.1f}%"

            if data['dti'] > 40:
                response += "\n⚠️  Attention : Votre taux d'endettement dépasse 40%"
            else:
                response += "\n✅ Votre taux d'endettement est acceptable"

        if data.get('eligible'):
            response += "\n\n✅ Vous êtes éligible pour ce crédit"
        elif data.get('eligible') is False:
            response += "\n\n❌ Vous n'êtes pas éligible pour ce crédit"
            if data.get('raison'):
                response += f"\nRaison : {data['raison']}"

        return response
