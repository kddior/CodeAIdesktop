# -*- coding: utf-8 -*-
"""
Banking Flows Definition - V3 "Flow-First" Architecture
Declarative flow definitions with embeddings + Qwen
"""

from typing import Dict, List, Optional, Any

# =======================
# FLOW DEFINITIONS
# =======================

FLOWS = [
    {
        "name": "CHECK_BALANCE",
        "description": "Consulter le solde du compte bancaire de l'utilisateur",
        "type": "transactional",
        "slots": [],
        "tool": "get_balance",
        "llm_answer_style": "banking_short",
        "examples": [
            "quel est mon solde",
            "combien j'ai sur mon compte",
            "je veux savoir mon solde",
            "affiche mon solde",
            "mon compte c'est combien",
            "balance de mon compte"
        ]
    },
    {
        "name": "OPEN_ACCOUNT",
        "description": "Expliquer comment ouvrir un compte bancaire chez AFG/DBS",
        "type": "informational",
        "slots": [],
        "tool": None,
        "llm_answer_style": "banking_explainer",
        "examples": [
            "comment ouvrir un compte",
            "je veux ouvrir un compte",
            "ouvrir un compte bancaire",
            "créer un compte",
            "procédure ouverture compte",
            "comment faire pour ouvrir un compte"
        ]
    },
    {
        "name": "TRANSFER_MONEY",
        "description": "Effectuer un virement d'un montant vers un bénéficiaire",
        "type": "transactional",
        "slots": ["amount", "currency", "beneficiary_name"],
        "tool": "execute_transfer",
        "llm_answer_style": "banking_transaction",
        "examples": [
            "virer 50000 à Pierre",
            "envoyer de l'argent",
            "faire un virement",
            "transférer 100000 XOF",
            "je veux payer Jean",
            "envoyer 500000 à Marie"
        ]
    },
    {
        "name": "CREDIT_SIMULATION",
        "description": "Simuler un crédit avec montant, durée et mensualité approximative",
        "type": "informational",
        "slots": ["amount", "duration_months"],
        "tool": None,
        "llm_answer_style": "banking_simulation",
        "examples": [
            "simuler un crédit",
            "emprunter 5 millions",
            "prêt de 10 millions",
            "je veux un crédit",
            "combien je peux emprunter",
            "capacité d'emprunt"
        ]
    },
    {
        "name": "ACCOUNT_HISTORY",
        "description": "Consulter l'historique des transactions du compte",
        "type": "transactional",
        "slots": [],
        "tool": "get_transactions",
        "llm_answer_style": "banking_short",
        "examples": [
            "mes dernières transactions",
            "historique de mon compte",
            "voir mes opérations",
            "liste des transactions",
            "mouvements de compte"
        ]
    },
    {
        "name": "GET_STATEMENT",
        "description": "Obtenir un relevé de compte en PDF",
        "type": "transactional",
        "slots": [],
        "tool": "generate_statement",
        "llm_answer_style": "banking_short",
        "examples": [
            "relevé de compte",
            "je veux un relevé",
            "document PDF",
            "extrait de compte",
            "envoyer mon relevé"
        ]
    },
    # ========================================
    # FINANCIAL CALCULATION FLOWS
    # ========================================
    {
        "name": "CALC_CAPACITE_EMPRUNT",
        "description": "Calculer la capacité d'emprunt en fonction du revenu, charges existantes et taux d'endettement",
        "type": "calculation",
        "slots": ["revenu_mensuel_net", "charges_mensuelles_existantes", "taux_endettement_max", "taux_credit_annuel", "duree_annees"],
        "tool": "financial_calculator",
        "calc_type": "capacite_emprunt",
        "llm_answer_style": "financial_explanation",
        "examples": [
            "quelle est ma capacité d'emprunt",
            "combien je peux emprunter avec un salaire de 500000",
            "calculer capacité emprunt",
            "montant maximum empruntable",
            "je gagne 700000 combien je peux emprunter"
        ]
    },
    {
        "name": "CALC_SIMULATION_PRET",
        "description": "Simuler un prêt : mensualité, coût total des intérêts et assurance",
        "type": "calculation",
        "slots": ["montant_pret", "taux_credit_annuel", "duree_annees", "taux_assurance_annuel", "frais_dossier"],
        "tool": "financial_calculator",
        "calc_type": "simulation_pret",
        "llm_answer_style": "financial_explanation",
        "examples": [
            "simuler un prêt de 10 millions sur 20 ans",
            "calculer mensualité crédit immobilier",
            "combien je vais payer par mois pour un crédit de 5 millions",
            "simulation crédit",
            "coût total d'un prêt"
        ]
    },
    {
        "name": "CALC_COMPARAISON_PRETS",
        "description": "Comparer deux offres de prêt (taux, durée, coût total)",
        "type": "calculation",
        "slots": ["montant_pret_A", "taux_credit_annuel_A", "duree_annees_A", "montant_pret_B", "taux_credit_annuel_B", "duree_annees_B"],
        "tool": "financial_calculator",
        "calc_type": "comparaison_prets",
        "llm_answer_style": "financial_explanation",
        "examples": [
            "comparer deux offres de crédit",
            "quelle offre est la plus avantageuse",
            "banque A vs banque B",
            "comparer 8% sur 20 ans vs 7.5% sur 25 ans",
            "meilleure offre entre deux prêts"
        ]
    },
    {
        "name": "CALC_RACHAT_CREDITS",
        "description": "Calculer l'intérêt d'un rachat de crédits (refinancement)",
        "type": "calculation",
        "slots": ["mensualite_actuelle_totale", "capital_restant_du_total", "frais_rachats", "taux_credit_annuel_nouveau", "duree_annees_nouveau"],
        "tool": "financial_calculator",
        "calc_type": "rachat_credits",
        "llm_answer_style": "financial_explanation",
        "examples": [
            "rachat de crédit",
            "regrouper mes crédits",
            "consolidation de dettes",
            "refinancement crédits",
            "réduire mes mensualités"
        ]
    },
    {
        "name": "CALC_DECOUVERT_VS_CREDIT",
        "description": "Comparer le coût d'un découvert récurrent vs un petit crédit",
        "type": "calculation",
        "slots": ["montant_decouvert_moyen", "taux_decouvert_annuel", "jours_decouvert_par_an", "montant_credit", "taux_credit_annuel", "duree_annees"],
        "tool": "financial_calculator",
        "calc_type": "cout_decouvert_vs_credit",
        "llm_answer_style": "financial_explanation",
        "examples": [
            "découvert ou crédit",
            "mieux vaut un crédit ou rester à découvert",
            "coût découvert vs prêt",
            "comparer découvert et crédit"
        ]
    },
    {
        "name": "CALC_EPARGNE_OBJECTIF",
        "description": "Calculer le versement mensuel nécessaire pour atteindre un objectif d'épargne",
        "type": "calculation",
        "slots": ["objectif_montant", "duree_annees", "taux_rendement_annuel"],
        "tool": "financial_calculator",
        "calc_type": "epargne_objectif",
        "llm_answer_style": "financial_explanation",
        "examples": [
            "combien épargner par mois",
            "plan d'épargne pour 20 millions",
            "économiser pour un projet",
            "atteindre 10 millions en 5 ans",
            "épargne mensuelle nécessaire"
        ]
    },
    {
        "name": "CALC_DSCR_ENTREPRISE",
        "description": "Calculer le ratio de couverture du service de la dette (DSCR) pour une entreprise",
        "type": "calculation",
        "slots": ["cash_flow_disponible", "service_dette_annuel", "ebitda", "impots", "investissements_recurrents"],
        "tool": "financial_calculator",
        "calc_type": "dscr_entreprise",
        "llm_answer_style": "financial_explanation",
        "examples": [
            "calculer DSCR",
            "ratio couverture dette",
            "mon entreprise peut-elle supporter la dette",
            "debt service coverage ratio",
            "capacité remboursement entreprise"
        ]
    },
    {
        "name": "CALC_LEVERAGE_ENTREPRISE",
        "description": "Calculer le ratio d'endettement d'une entreprise (dettes / fonds propres)",
        "type": "calculation",
        "slots": ["dettes_financieres_totales", "fonds_propres"],
        "tool": "financial_calculator",
        "calc_type": "leverage_entreprise",
        "llm_answer_style": "financial_explanation",
        "examples": [
            "ratio endettement entreprise",
            "leverage financier",
            "dette sur fonds propres",
            "gearing ratio",
            "niveau d'endettement société"
        ]
    },
    {
        "name": "CALC_LTV_GARANTIE",
        "description": "Calculer le Loan-to-Value (LTV) d'une garantie réelle",
        "type": "calculation",
        "slots": ["valeur_garantie", "montant_pret", "ltv_max_autorisee"],
        "tool": "financial_calculator",
        "calc_type": "ltv_garantie_reelle",
        "llm_answer_style": "financial_explanation",
        "examples": [
            "calculer LTV",
            "loan to value",
            "ratio prêt valeur",
            "garantie suffisante",
            "couverture par la garantie"
        ]
    },
    {
        "name": "CALC_COMMISSION_GARANTIE",
        "description": "Calculer les commissions sur garanties bancaires (caution, aval, etc.)",
        "type": "calculation",
        "slots": ["montant_garantie", "taux_commission_annuel", "duree_mois", "minimum_forfaitaire", "frais_dossier", "type_garantie"],
        "tool": "financial_calculator",
        "calc_type": "commission_garantie_bancaire",
        "llm_answer_style": "financial_explanation",
        "examples": [
            "coût garantie bancaire",
            "commission caution",
            "prix aval bancaire",
            "frais garantie",
            "calculer commission garantie"
        ]
    },
    {
        "name": "CALC_FX_CONVERSION",
        "description": "Convertir devises avec marge bancaire",
        "type": "calculation",
        "slots": ["montant_devise", "taux_marche", "marge_taux"],
        "tool": "financial_calculator",
        "calc_type": "fx_conversion",
        "llm_answer_style": "financial_explanation",
        "examples": [
            "convertir EUR en XOF",
            "taux de change",
            "conversion devise",
            "combien ça fait en francs CFA",
            "change EUR USD"
        ]
    }
]

# =======================
# FLOW REGISTRY
# =======================

class FlowRegistry:
    """Registry for banking flows"""

    def __init__(self):
        self.flows = {flow["name"]: flow for flow in FLOWS}

    def get_flow(self, name: str) -> Optional[Dict]:
        """Get flow by name"""
        return self.flows.get(name)

    def get_all_flows(self) -> List[Dict]:
        """Get all flows"""
        return FLOWS

    def get_flow_descriptions(self) -> List[str]:
        """Get all flow descriptions for embedding"""
        descriptions = []
        for flow in FLOWS:
            # Add description
            descriptions.append(f"{flow['name']}: {flow['description']}")
            # Add examples
            for example in flow.get("examples", []):
                descriptions.append(f"{flow['name']}: {example}")
        return descriptions

    def format_flows_for_prompt(self) -> str:
        """Format flows for Qwen prompt"""
        lines = []
        for i, flow in enumerate(FLOWS, 1):
            lines.append(f"{i}. {flow['name']}: {flow['description']}")
        return "\n".join(lines)


# Global registry instance
flow_registry = FlowRegistry()
