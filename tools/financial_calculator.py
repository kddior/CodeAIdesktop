# -*- coding: utf-8 -*-
"""
Financial Calculator - Accurate mathematical calculations for banking
Uses numpy for numerical precision (no LLM calculations!)

Implements 11 calculation types:
1. capacite_emprunt - Borrowing capacity
2. simulation_pret - Loan simulation
3. comparaison_prets - Compare 2 loans
4. rachat_credits - Refinancing/consolidation
5. cout_decouvert_vs_credit - Overdraft vs small loan
6. epargne_objectif - Savings plan
7. dscr_entreprise - Debt Service Coverage Ratio
8. leverage_entreprise - Financial leverage
9. ltv_garantie_reelle - Loan-to-Value
10. commission_garantie_bancaire - Guarantee commissions
11. fx_conversion - FX conversion with margin
"""

import numpy as np
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class FinancialCalculator:
    """
    Mathematical financial calculator

    IMPORTANT: All calculations done in code, NEVER by LLM!
    LLM only extracts inputs and explains results.
    """

    @staticmethod
    def calculate(type_calcul: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main entry point for financial calculations

        Args:
            type_calcul: Type of calculation (see list above)
            inputs: Dictionary of input parameters

        Returns:
            Dictionary with type_calcul, inputs, and resultat
        """
        calculators = {
            'capacite_emprunt': FinancialCalculator._capacite_emprunt,
            'simulation_pret': FinancialCalculator._simulation_pret,
            'comparaison_prets': FinancialCalculator._comparaison_prets,
            'rachat_credits': FinancialCalculator._rachat_credits,
            'cout_decouvert_vs_credit': FinancialCalculator._cout_decouvert_vs_credit,
            'epargne_objectif': FinancialCalculator._epargne_objectif,
            'dscr_entreprise': FinancialCalculator._dscr_entreprise,
            'leverage_entreprise': FinancialCalculator._leverage_entreprise,
            'ltv_garantie_reelle': FinancialCalculator._ltv_garantie_reelle,
            'commission_garantie_bancaire': FinancialCalculator._commission_garantie_bancaire,
            'commission_garantie': FinancialCalculator._commission_garantie_bancaire,  # Alias
            'fx_conversion': FinancialCalculator._fx_conversion,
        }

        if type_calcul not in calculators:
            raise ValueError(f"Unknown calculation type: {type_calcul}")

        logger.info(f"[CALC] Executing {type_calcul} with inputs: {inputs}")

        try:
            resultat = calculators[type_calcul](inputs)
            response = {
                "type_calcul": type_calcul,
                "inputs": inputs,
                "resultat": resultat
            }
            logger.info(f"[CALC] Success: {resultat}")
            return response
        except Exception as e:
            logger.error(f"[CALC] Error in {type_calcul}: {e}", exc_info=True)
            raise

    @staticmethod
    def _capacite_emprunt(inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        1. Borrowing capacity calculation

        Inputs:
            - revenu_mensuel_net: net monthly income
            - charges_mensuelles_existantes: existing monthly debt payments
            - taux_endettement_max: max debt ratio (e.g. 0.4 for 40%)
            - taux_credit_annuel: annual interest rate (e.g. 0.08 for 8%)
            - duree_annees: loan duration in years

        Returns:
            - taux_endettement_actuel
            - taux_endettement_max
            - mensualite_totale_max
            - mensualite_disponible_nouveau_credit
            - montant_max_pret
        """
        revenu = float(inputs['revenu_mensuel_net'])
        charges = float(inputs['charges_mensuelles_existantes'])
        taux_end_max = float(inputs['taux_endettement_max'])
        taux_annuel = float(inputs['taux_credit_annuel'])
        duree_ans = float(inputs['duree_annees'])

        # Current debt ratio
        taux_end_actuel = charges / revenu if revenu > 0 else 0

        # Max total monthly payment
        mensualite_max = revenu * taux_end_max

        # Available for new credit
        mensualite_dispo = max(0, mensualite_max - charges)

        # Max loan amount calculation
        i = taux_annuel / 12  # monthly rate
        n = duree_ans * 12    # months

        if i > 0:
            # Standard annuity formula: PV = PMT * (1 - (1+i)^-n) / i
            montant_max = mensualite_dispo * (1 - np.power(1 + i, -n)) / i
        else:
            # Zero interest
            montant_max = mensualite_dispo * n

        return {
            'taux_endettement_actuel': round(taux_end_actuel, 4),
            'taux_endettement_max': taux_end_max,
            'mensualite_totale_max': round(mensualite_max, 2),
            'mensualite_disponible_nouveau_credit': round(mensualite_dispo, 2),
            'montant_max_pret': round(montant_max, 2)
        }

    @staticmethod
    def _simulation_pret(inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        2. Loan simulation (monthly payment & total cost)

        Inputs:
            - montant_pret
            - taux_credit_annuel
            - duree_annees
            - taux_assurance_annuel (optional)
            - frais_dossier (optional)

        Returns:
            - mensualite_hors_assurance
            - mensualite_assurance
            - mensualite_totale
            - cout_interets_total
            - cout_assurance_total
            - cout_total_global
        """
        montant = float(inputs['montant_pret'])
        taux_annuel = float(inputs['taux_credit_annuel'])
        duree_ans = float(inputs['duree_annees'])
        taux_ass = float(inputs.get('taux_assurance_annuel', 0))
        frais = float(inputs.get('frais_dossier', 0))

        i = taux_annuel / 12
        n = duree_ans * 12

        # Monthly payment (principal + interest)
        if i > 0:
            mensualite_base = montant * i / (1 - np.power(1 + i, -n))
        else:
            mensualite_base = montant / n

        # Insurance payment (on initial capital)
        i_ass = taux_ass / 12
        mensualite_ass = montant * i_ass

        # Total monthly payment
        mensualite_totale = mensualite_base + mensualite_ass

        # Total costs
        cout_interets = mensualite_base * n - montant
        cout_assurance = mensualite_ass * n
        cout_total = cout_interets + cout_assurance + frais

        return {
            'mensualite_hors_assurance': round(mensualite_base, 2),
            'mensualite_assurance': round(mensualite_ass, 2),
            'mensualite_totale': round(mensualite_totale, 2),
            'cout_interets_total': round(cout_interets, 2),
            'cout_assurance_total': round(cout_assurance, 2),
            'cout_total_global': round(cout_total, 2)
        }

    @staticmethod
    def _comparaison_prets(inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        3. Compare 2 loan offers

        Inputs: All inputs for offer A and B (suffixed with _A and _B)

        Returns:
            - offer_A: simulation results for A
            - offer_B: simulation results for B
            - delta_mensualite: B - A
            - delta_cout_total: B - A
        """
        # Extract inputs for each offer
        inputs_A = {
            'montant_pret': inputs['montant_pret_A'],
            'taux_credit_annuel': inputs['taux_credit_annuel_A'],
            'duree_annees': inputs['duree_annees_A'],
            'taux_assurance_annuel': inputs.get('taux_assurance_annuel_A', 0),
            'frais_dossier': inputs.get('frais_dossier_A', 0)
        }

        inputs_B = {
            'montant_pret': inputs['montant_pret_B'],
            'taux_credit_annuel': inputs['taux_credit_annuel_B'],
            'duree_annees': inputs['duree_annees_B'],
            'taux_assurance_annuel': inputs.get('taux_assurance_annuel_B', 0),
            'frais_dossier': inputs.get('frais_dossier_B', 0)
        }

        # Calculate each offer
        offer_A = FinancialCalculator._simulation_pret(inputs_A)
        offer_B = FinancialCalculator._simulation_pret(inputs_B)

        # Deltas
        delta_mens = offer_B['mensualite_totale'] - offer_A['mensualite_totale']
        delta_cout = offer_B['cout_total_global'] - offer_A['cout_total_global']

        return {
            'offer_A': offer_A,
            'offer_B': offer_B,
            'delta_mensualite': round(delta_mens, 2),
            'delta_cout_total': round(delta_cout, 2)
        }

    @staticmethod
    def _rachat_credits(inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        4. Refinancing / consolidation

        Inputs:
            - mensualite_actuelle_totale
            - capital_restant_du_total
            - frais_rachats (optional)
            - taux_credit_annuel_nouveau
            - duree_annees_nouveau

        Returns:
            - nouveau_montant_pret
            - nouvelle_mensualite
            - gain_mensuel (positive = savings)
        """
        mens_actuelle = float(inputs['mensualite_actuelle_totale'])
        capital_restant = float(inputs['capital_restant_du_total'])
        frais_rachat = float(inputs.get('frais_rachats', 0))
        taux_nouveau = float(inputs['taux_credit_annuel_nouveau'])
        duree_nouveau = float(inputs['duree_annees_nouveau'])

        # New loan amount = outstanding + fees
        nouveau_montant = capital_restant + frais_rachat

        # Calculate new monthly payment
        i = taux_nouveau / 12
        n = duree_nouveau * 12

        if i > 0:
            nouvelle_mens = nouveau_montant * i / (1 - np.power(1 + i, -n))
        else:
            nouvelle_mens = nouveau_montant / n

        # Monthly gain (positive = client pays less per month)
        gain = mens_actuelle - nouvelle_mens

        return {
            'nouveau_montant_pret': round(nouveau_montant, 2),
            'nouvelle_mensualite': round(nouvelle_mens, 2),
            'gain_mensuel': round(gain, 2)
        }

    @staticmethod
    def _cout_decouvert_vs_credit(inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        5. Overdraft vs small loan comparison

        Inputs:
            - montant_decouvert_moyen
            - taux_decouvert_annuel
            - jours_decouvert_par_an
            - montant_credit
            - taux_credit_annuel
            - duree_annees

        Returns:
            - cout_decouvert_annuel
            - mensualite_credit
            - cout_interets_credit_total
        """
        montant_dec = float(inputs['montant_decouvert_moyen'])
        taux_dec = float(inputs['taux_decouvert_annuel'])
        jours_dec = float(inputs['jours_decouvert_par_an'])

        montant_cred = float(inputs['montant_credit'])
        taux_cred = float(inputs['taux_credit_annuel'])
        duree = float(inputs['duree_annees'])

        # Overdraft cost (360-day convention)
        cout_decouvert = montant_dec * taux_dec * (jours_dec / 360)

        # Loan simulation
        i = taux_cred / 12
        n = duree * 12

        if i > 0:
            mens_credit = montant_cred * i / (1 - np.power(1 + i, -n))
        else:
            mens_credit = montant_cred / n

        cout_interets = mens_credit * n - montant_cred

        return {
            'cout_decouvert_annuel': round(cout_decouvert, 2),
            'mensualite_credit': round(mens_credit, 2),
            'cout_interets_credit_total': round(cout_interets, 2)
        }

    @staticmethod
    def _epargne_objectif(inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        6. Savings plan for target amount

        Inputs:
            - objectif_montant
            - duree_annees
            - taux_rendement_annuel

        Returns:
            - versement_mensuel_necessaire
            - nombre_versements
        """
        objectif = float(inputs['objectif_montant'])
        duree = float(inputs['duree_annees'])
        taux = float(inputs['taux_rendement_annuel'])

        i = taux / 12
        n = duree * 12

        # Future value of annuity: FV = PMT * ((1+i)^n - 1) / i
        # Solve for PMT: PMT = FV * i / ((1+i)^n - 1)
        if i > 0:
            versement = objectif * i / (np.power(1 + i, n) - 1)
        else:
            versement = objectif / n

        return {
            'versement_mensuel_necessaire': round(versement, 2),
            'nombre_versements': int(n)
        }

    @staticmethod
    def _dscr_entreprise(inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        7. Debt Service Coverage Ratio

        Inputs (Option A):
            - cash_flow_disponible
            - service_dette_annuel

        OR (Option B):
            - ebitda
            - impots
            - investissements_recurrents
            - service_dette_annuel

        Returns:
            - cash_flow_disponible
            - service_dette_annuel
            - dscr
        """
        service_dette = float(inputs['service_dette_annuel'])

        # Check which option
        if 'cash_flow_disponible' in inputs:
            # Option A - direct
            cash_flow = float(inputs['cash_flow_disponible'])
        else:
            # Option B - calculate from EBITDA
            ebitda = float(inputs['ebitda'])
            impots = float(inputs['impots'])
            capex = float(inputs['investissements_recurrents'])
            cash_flow = ebitda - impots - capex

        # DSCR calculation
        if service_dette > 0:
            dscr = cash_flow / service_dette
        else:
            dscr = float('inf')  # No debt = infinite coverage

        return {
            'cash_flow_disponible': round(cash_flow, 2),
            'service_dette_annuel': round(service_dette, 2),
            'dscr': round(dscr, 2)
        }

    @staticmethod
    def _leverage_entreprise(inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        8. Financial leverage ratio

        Inputs:
            - dettes_financieres_totales
            - fonds_propres

        Returns:
            - ratio_endettement (debt-to-equity)
        """
        dettes = float(inputs['dettes_financieres_totales'])
        fonds_propres = float(inputs['fonds_propres'])

        if fonds_propres > 0:
            ratio = dettes / fonds_propres
        else:
            ratio = float('inf') if dettes > 0 else 0

        return {
            'ratio_endettement': round(ratio, 2)
        }

    @staticmethod
    def _ltv_garantie_reelle(inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        9. Loan-to-Value on collateral

        Inputs:
            - valeur_garantie
            - montant_pret
            - ltv_max_autorisee (optional)

        Returns:
            - ltv
            - conforme_politique (if max provided)
            - marge_sur_ltv (if max provided)
        """
        valeur = float(inputs['valeur_garantie'])
        montant = float(inputs['montant_pret'])
        ltv_max = inputs.get('ltv_max_autorisee')

        # LTV calculation
        if valeur > 0:
            ltv = montant / valeur
        else:
            ltv = float('inf')

        result = {
            'ltv': round(ltv, 4)
        }

        # Check against max if provided
        if ltv_max is not None:
            ltv_max = float(ltv_max)
            result['ltv_max_autorisee'] = ltv_max
            result['conforme_politique'] = ltv <= ltv_max
            result['marge_sur_ltv'] = round(ltv_max - ltv, 4)

        return result

    @staticmethod
    def _commission_garantie_bancaire(inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        10. Guarantee commissions

        Inputs (Option A - Direct):
            - montant_garantie
            - taux_commission_annuel
            - duree_mois
            - minimum_forfaitaire (optional)
            - frais_dossier (optional)
            - type_garantie (optional, for display)

        Inputs (Option B - From market):
            - montant_marche
            - taux_garantie
            - taux_commission_annuel
            - duree_mois
            - minimum_forfaitaire (optional)
            - frais_dossier (optional)
            - type_garantie (optional)
            - taux_couverture (optional)

        Returns:
            - montant_garantie
            - commission_theorique
            - commission_facturee
            - frais_dossier
            - total_frais
            - couverture_exigee (if taux_couverture provided)
        """
        # Calculate guaranteed amount
        if 'montant_garantie' in inputs:
            montant = float(inputs['montant_garantie'])
        elif 'montant_marche' in inputs and 'taux_garantie' in inputs:
            montant_marche = float(inputs['montant_marche'])
            taux_gar = float(inputs['taux_garantie'])
            montant = montant_marche * taux_gar
        else:
            raise ValueError("Must provide either 'montant_garantie' or ('montant_marche' + 'taux_garantie')")

        taux = float(inputs['taux_commission_annuel'])
        duree_mois = float(inputs['duree_mois'])
        minimum = float(inputs.get('minimum_forfaitaire', 0))
        frais = float(inputs.get('frais_dossier', 0))

        # Theoretical commission
        commission_theo = montant * taux * (duree_mois / 12)

        # Apply minimum
        commission_fact = max(commission_theo, minimum)

        # Total with fees
        total = commission_fact + frais

        result = {
            'montant_garantie': round(montant, 2),
            'commission_theorique': round(commission_theo, 2),
            'commission_facturee': round(commission_fact, 2),
            'frais_dossier': frais,
            'total_frais': round(total, 2)
        }

        # Coverage required (optional)
        if 'taux_couverture' in inputs:
            taux_couv = float(inputs['taux_couverture'])
            result['couverture_exigee'] = round(montant * taux_couv, 2)

        if 'type_garantie' in inputs:
            result['type_garantie'] = inputs['type_garantie']

        return result

    @staticmethod
    def _fx_conversion(inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        11. FX conversion with margin

        Inputs:
            - montant_devise
            - taux_marche (interbank rate)
            - marge_taux (percentage margin on rate, e.g. 0.01 = +1%)

        Returns:
            - taux_client
            - montant_devise_locale
            - marge_banque_estimee
        """
        montant = float(inputs['montant_devise'])
        taux_marche = float(inputs['taux_marche'])
        marge = float(inputs['marge_taux'])

        # Client rate with margin
        taux_client = taux_marche * (1 + marge)

        # Converted amount
        montant_local = montant * taux_client

        # Bank margin in local currency
        marge_banque = montant * (taux_client - taux_marche)

        return {
            'taux_marche': round(taux_marche, 6),
            'taux_client': round(taux_client, 6),
            'montant_devise_locale': round(montant_local, 2),
            'marge_banque_estimee': round(marge_banque, 2)
        }


# Testing
if __name__ == "__main__":
    import json

    print("=== Financial Calculator Tests ===\n")

    # Test 1: Borrowing capacity
    print("[Test 1] Borrowing Capacity")
    result1 = FinancialCalculator.calculate('capacite_emprunt', {
        'revenu_mensuel_net': 500000,
        'charges_mensuelles_existantes': 100000,
        'taux_endettement_max': 0.4,
        'taux_credit_annuel': 0.08,
        'duree_annees': 20
    })
    print(json.dumps(result1, indent=2, ensure_ascii=False))

    # Test 2: Loan simulation
    print("\n[Test 2] Loan Simulation")
    result2 = FinancialCalculator.calculate('simulation_pret', {
        'montant_pret': 10000000,
        'taux_credit_annuel': 0.08,
        'duree_annees': 20,
        'taux_assurance_annuel': 0.003,
        'frais_dossier': 50000
    })
    print(json.dumps(result2, indent=2, ensure_ascii=False))

    # Test 3: DSCR
    print("\n[Test 3] DSCR")
    result3 = FinancialCalculator.calculate('dscr_entreprise', {
        'ebitda': 500000000,
        'impots': 50000000,
        'investissements_recurrents': 100000000,
        'service_dette_annuel': 200000000
    })
    print(json.dumps(result3, indent=2, ensure_ascii=False))
