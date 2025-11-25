"""
Mock Banking Backend
In production, these would connect to real core banking systems
"""

from typing import Dict, Any
import random
from datetime import datetime, timedelta


class BankingBackend:
    """Mock backend for banking operations"""

    def __init__(self):
        # Mock user accounts
        self.mock_accounts = {
            "user_001": {
                "comptes": {
                    "courant": {
                        "solde": 450_000,
                        "devise": "XOF",
                        "numero": "BF1234567890123456789012"
                    },
                    "epargne": {
                        "solde": 1_200_000,
                        "devise": "XOF",
                        "numero": "BF9876543210987654321098"
                    },
                    "salaire": {
                        "solde": 850_000,
                        "devise": "XOF",
                        "numero": "BF5555555555555555555555"
                    }
                }
            }
        }

        # Mock transaction history
        self.mock_transactions = self._generate_mock_transactions()

    def _generate_mock_transactions(self):
        """Generate mock transaction history"""
        return {
            "user_001": [
                {
                    "date": (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"),
                    "type": "debit",
                    "montant": 5_000,
                    "libelle": "Retrait GAB",
                    "solde_apres": 450_000
                },
                {
                    "date": (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d"),
                    "type": "credit",
                    "montant": 200_000,
                    "libelle": "Virement salaire",
                    "solde_apres": 455_000
                },
                {
                    "date": (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d"),
                    "type": "debit",
                    "montant": 25_000,
                    "libelle": "Paiement facture électricité",
                    "solde_apres": 255_000
                },
            ]
        }

    def execute(self, intent: str, slots: Dict[str, Any]) -> Dict[str, Any]:
        """Execute backend operation based on intent"""

        if intent == "CONSULTER_SOLDE":
            return self._consulter_solde(slots)

        elif intent == "DISCUSSION_COMPTE":
            return self._discussion_compte(slots)

        elif intent == "FAIRE_VIREMENT":
            return self._faire_virement(slots)

        elif intent == "OBTENIR_RELEVE":
            return self._obtenir_releve(slots)

        elif intent == "SIMULATION_CREDIT":
            return self._simulation_credit(slots)

        else:
            return {"error": "Intent non supporté"}

    def _consulter_solde(self, slots: Dict) -> Dict:
        """Get account balance"""
        user_id = "user_001"  # Mock user
        compte_type = slots.get('compte_type', 'courant')

        compte = self.mock_accounts[user_id]["comptes"].get(compte_type)

        if not compte:
            return {
                "success": False,
                "error": f"Compte {compte_type} non trouvé"
            }

        return {
            "success": True,
            "compte_type": compte_type,
            "solde": compte["solde"],
            "devise": compte["devise"],
            "numero": compte["numero"],
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

    def _discussion_compte(self, slots: Dict) -> Dict:
        """Get account transactions/discussion"""
        user_id = "user_001"
        compte_type = slots.get('compte_type', 'courant')

        transactions = self.mock_transactions.get(user_id, [])

        # Filter by date if provided
        date_ou_periode = slots.get('date_ou_periode')

        return {
            "success": True,
            "compte_type": compte_type,
            "transactions": transactions[:5],  # Last 5 transactions
            "nb_transactions": len(transactions)
        }

    def _faire_virement(self, slots: Dict) -> Dict:
        """Execute wire transfer"""
        montant = slots.get('montant')
        devise = slots.get('devise', 'XOF')
        beneficiaire = slots.get('beneficiaire_nom', 'Bénéficiaire')
        compte_source = slots.get('compte_source', 'courant')

        # Mock validation
        user_id = "user_001"
        compte = self.mock_accounts[user_id]["comptes"].get(compte_source)

        if not compte:
            return {
                "success": False,
                "error": "Compte source non trouvé"
            }

        if montant > compte["solde"]:
            return {
                "success": False,
                "error": "Solde insuffisant",
                "solde_disponible": compte["solde"]
            }

        # Mock transfer execution
        nouveau_solde = compte["solde"] - montant
        compte["solde"] = nouveau_solde

        return {
            "success": True,
            "montant": montant,
            "devise": devise,
            "beneficiaire": beneficiaire,
            "compte_source": compte_source,
            "nouveau_solde": nouveau_solde,
            "reference": f"VIR{random.randint(100000, 999999)}",
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "frais": 0 if montant < 100_000 else 500
        }

    def _obtenir_releve(self, slots: Dict) -> Dict:
        """Generate account statement"""
        compte_type = slots.get('compte_type', 'courant')
        date_debut = slots.get('date_debut', (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"))
        date_fin = slots.get('date_fin', datetime.now().strftime("%Y-%m-%d"))
        format_type = slots.get('format', 'RESUME')

        user_id = "user_001"
        transactions = self.mock_transactions.get(user_id, [])

        return {
            "success": True,
            "compte_type": compte_type,
            "date_debut": date_debut,
            "date_fin": date_fin,
            "format": format_type,
            "transactions": transactions,
            "nb_operations": len(transactions),
            "url_pdf": f"https://bank.example.com/statements/releve_{random.randint(1000, 9999)}.pdf" if format_type == "PDF" else None
        }

    def _simulation_credit(self, slots: Dict) -> Dict:
        """Simulate credit/loan"""
        montant_souhaite = slots.get('montant_souhaite')
        duree_mois = slots.get('duree_mois', 60)
        revenus_mensuels = slots.get('revenus_mensuels', 300_000)
        charges_mensuelles = slots.get('charges_mensuelles', 100_000)
        taux_interet = slots.get('taux_interet', 12.0)  # Default 12% annual

        # Calculate mensuality
        taux_mensuel = taux_interet / 100 / 12
        nb_mois = duree_mois

        if taux_mensuel > 0:
            mensualite = montant_souhaite * (taux_mensuel * (1 + taux_mensuel) ** nb_mois) / \
                        ((1 + taux_mensuel) ** nb_mois - 1)
        else:
            mensualite = montant_souhaite / nb_mois

        # Calculate ratios
        revenu_disponible = revenus_mensuels - charges_mensuelles
        taux_endettement = (mensualite / revenus_mensuels) * 100 if revenus_mensuels > 0 else 100

        # Capacity check
        capacite_max = revenu_disponible * 0.33  # Max 33% of available income
        pret_possible = taux_endettement <= 33

        cout_total = mensualite * nb_mois
        cout_credit = cout_total - montant_souhaite

        return {
            "success": True,
            "montant_demande": montant_souhaite,
            "duree_mois": duree_mois,
            "taux_annuel": taux_interet,
            "mensualite": round(mensualite, 2),
            "cout_total": round(cout_total, 2),
            "cout_credit": round(cout_credit, 2),
            "taux_endettement": round(taux_endettement, 2),
            "pret_possible": pret_possible,
            "capacite_mensuelle_max": round(capacite_max, 2),
            "revenus_mensuels": revenus_mensuels,
            "charges_mensuelles": charges_mensuelles,
            "recommandation": "Crédit accepté" if pret_possible else "Taux d'endettement trop élevé"
        }
