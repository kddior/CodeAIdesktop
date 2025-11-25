# -*- coding: utf-8 -*-
"""
Calculator Formulas and Expert Prompts
Provides detailed formula explanations and LLM verification prompts for each calculator
"""

from typing import Dict, Any


class CalculatorFormulas:
    """Formulas and expert prompts for financial calculators"""

    @staticmethod
    def get_formula_explanation(calc_type: str, inputs: Dict[str, Any], result: Dict[str, Any]) -> str:
        """
        Get detailed formula explanation for display

        Args:
            calc_type: Type of calculation
            inputs: Input parameters
            result: Calculation result

        Returns:
            Markdown formatted formula explanation
        """
        formulas = {
            'capacite_emprunt': CalculatorFormulas._formula_capacite_emprunt,
            'simulation_pret': CalculatorFormulas._formula_simulation_pret,
            'commission_garantie': CalculatorFormulas._formula_commission_garantie,
            'dscr_entreprise': CalculatorFormulas._formula_dscr,
            'ltv_garantie': CalculatorFormulas._formula_ltv,
            'epargne_objectif': CalculatorFormulas._formula_epargne,
        }

        formula_func = formulas.get(calc_type)
        if formula_func:
            return formula_func(inputs, result)
        else:
            return "Formule non disponible pour ce type de calcul."

    @staticmethod
    def _formula_capacite_emprunt(inputs: Dict, result: Dict) -> str:
        revenu = inputs.get('revenu_mensuel_net', 0)
        charges = inputs.get('charges_mensuelles_existantes', 0)
        taux_max = inputs.get('taux_endettement_max', 0.4)
        taux = inputs.get('taux_credit_annuel', 0)
        duree = inputs.get('duree_annees', 0)

        i = taux / 12
        n = duree * 12
        mensualite_dispo = revenu * taux_max - charges

        return f"""
### 📐 Formule: Capacité d'Emprunt (Annuités Constantes)

**Étape 1:** Calcul de la mensualité disponible
```
Mensualité maximale = Revenu net × Taux endettement max
                    = {revenu:,.0f} × {taux_max*100:.0f}%
                    = {revenu * taux_max:,.0f} FCFA

Mensualité disponible = Mensualité max - Charges actuelles
                      = {revenu * taux_max:,.0f} - {charges:,.0f}
                      = {mensualite_dispo:,.0f} FCFA
```

**Étape 2:** Calcul du montant empruntable
```
Variables:
  i = Taux annuel ÷ 12 = {taux*100:.2f}% ÷ 12 = {i*100:.4f}% (taux mensuel)
  n = Durée × 12 = {duree} × 12 = {n} mois

Formule d'annuité:
  Montant = Mensualité × [(1 - (1 + i)^(-n)) ÷ i]

Calcul:
  Montant = {mensualite_dispo:,.0f} × [(1 - (1 + {i:.6f})^(-{n})) ÷ {i:.6f}]
          = {mensualite_dispo:,.0f} × {(1 - (1 + i)**(-n)) / i:.6f}
          = {result.get('montant_max_pret', 0):,.0f} FCFA
```

**📊 Résultat:**
- **Montant maximum empruntable:** {result.get('montant_max_pret', 0):,.0f} FCFA
- **Mensualité du nouveau crédit:** {mensualite_dispo:,.0f} FCFA
- **Taux d'endettement actuel:** {result.get('taux_endettement_actuel', 0)*100:.1f}%
- **Taux d'endettement projeté:** {(charges + mensualite_dispo)/revenu*100:.1f}%

**💡 Note:** Cette formule suppose des mensualités constantes (amortissement dégressif du capital, intérêts constants).
"""

    @staticmethod
    def _formula_simulation_pret(inputs: Dict, result: Dict) -> str:
        montant = inputs.get('montant_pret', 0)
        taux = inputs.get('taux_credit_annuel', 0)
        duree = inputs.get('duree_annees', 0)
        taux_assurance = inputs.get('taux_assurance_annuel', 0)
        frais = inputs.get('frais_dossier', 0)

        i = taux / 12
        n = duree * 12

        return f"""
### 📐 Formule: Simulation de Prêt (Annuités Constantes)

**Étape 1:** Calcul de la mensualité (capital + intérêts)
```
Variables:
  i = Taux annuel ÷ 12 = {taux*100:.2f}% ÷ 12 = {i*100:.4f}%
  n = Durée × 12 = {duree} × 12 = {n} mois

Formule:
  Mensualité = Montant × [i ÷ (1 - (1 + i)^(-n))]

Calcul:
  Mensualité = {montant:,.0f} × [{i:.6f} ÷ (1 - (1 + {i:.6f})^(-{n}))]
             = {montant:,.0f} × {i / (1 - (1 + i)**(-n)):.6f}
             = {result.get('mensualite_hors_assurance', 0):,.0f} FCFA
```

**Étape 2:** Assurance (si applicable)
```
Mensualité assurance = Montant × (Taux assurance annuel ÷ 12)
                     = {montant:,.0f} × ({taux_assurance*100:.2f}% ÷ 12)
                     = {result.get('mensualite_assurance', 0):,.0f} FCFA
```

**Étape 3:** Coût total du crédit
```
Mensualité totale = {result.get('mensualite_hors_assurance', 0):,.0f} + {result.get('mensualite_assurance', 0):,.0f}
                  = {result.get('mensualite_totale', 0):,.0f} FCFA

Coût des intérêts = (Mensualité × n mois) - Capital
                  = ({result.get('mensualite_hors_assurance', 0):,.0f} × {n}) - {montant:,.0f}
                  = {result.get('cout_interets_total', 0):,.0f} FCFA

Coût assurance = {result.get('mensualite_assurance', 0):,.0f} × {n}
               = {result.get('cout_assurance_total', 0):,.0f} FCFA

Coût total = Intérêts + Assurance + Frais
           = {result.get('cout_interets_total', 0):,.0f} + {result.get('cout_assurance_total', 0):,.0f} + {frais:,.0f}
           = {result.get('cout_total_global', 0):,.0f} FCFA
```

**📊 Résultat:**
- **Mensualité totale:** {result.get('mensualite_totale', 0):,.0f} FCFA/mois
- **Coût total du crédit:** {result.get('cout_total_global', 0):,.0f} FCFA
- **TAEG effectif:** {(result.get('cout_total_global', 0) / montant - 1) / duree * 100:.2f}% par an
"""

    @staticmethod
    def _formula_commission_garantie(inputs: Dict, result: Dict) -> str:
        montant_marche = inputs.get('montant_marche', 0)
        taux_garantie = inputs.get('taux_garantie', 0)
        duree = inputs.get('duree_mois', 0)
        taux_comm = inputs.get('taux_commission_annuel', 0)
        minimum = inputs.get('minimum_forfaitaire', 0)
        frais = inputs.get('frais_dossier', 0)
        taux_couv = inputs.get('taux_couverture', 0)
        type_gar = inputs.get('type_garantie', 'N/A')

        return f"""
### 📐 Formule: Commission de Garantie Bancaire

**Type de garantie:** {type_gar.replace('_', ' ').title()}

**Étape 1:** Montant garanti
```
Montant garanti = Montant marché × Taux garantie
                = {montant_marche:,.0f} × {taux_garantie*100:.1f}%
                = {result.get('montant_garantie', 0):,.0f} FCFA
```

**Étape 2:** Commission théorique
```
Commission théorique = Montant garanti × Taux commission × (Durée ÷ 12)
                     = {result.get('montant_garantie', 0):,.0f} × {taux_comm*100:.2f}% × ({duree} ÷ 12)
                     = {result.get('montant_garantie', 0):,.0f} × {taux_comm * duree / 12:.6f}
                     = {result.get('commission_theorique', 0):,.0f} FCFA
```

**Étape 3:** Commission facturée (avec minimum)
```
Commission facturée = MAX(Commission théorique, Minimum forfaitaire)
                    = MAX({result.get('commission_theorique', 0):,.0f}, {minimum:,.0f})
                    = {result.get('commission_facturee', 0):,.0f} FCFA
{"                    ⚠️ Minimum forfaitaire appliqué" if result.get('commission_facturee', 0) > result.get('commission_theorique', 0) else "                    ✅ Commission théorique suffisante"}
```

**Étape 4:** Total des frais
```
Total frais = Commission + Frais dossier
            = {result.get('commission_facturee', 0):,.0f} + {frais:,.0f}
            = {result.get('total_frais', 0):,.0f} FCFA
```

**Étape 5:** Couverture exigée (blocage de fonds)
```
Couverture = Montant garanti × Taux couverture
           = {result.get('montant_garantie', 0):,.0f} × {taux_couv*100:.0f}%
           = {result.get('couverture_exigee', 0):,.0f} FCFA
```

**📊 Résultat:**
- **Coût de la garantie:** {result.get('total_frais', 0):,.0f} FCFA ({result.get('total_frais', 0)/montant_marche*100:.3f}% du marché)
- **Blocage de trésorerie:** {result.get('couverture_exigee', 0):,.0f} FCFA pendant {duree} mois

**📚 Fourchettes standard (UEMOA):**
- Soumission: 1-3%, durée 3-6 mois
- Bonne Exécution: 5-10%, durée = contrat + 6-12 mois
- Acompte: 20-30%, durée 6-12 mois
- Retenue: 5-10%, durée 12-24 mois
"""

    @staticmethod
    def _formula_dscr(inputs: Dict, result: Dict) -> str:
        if 'ebitda' in inputs:
            # Via EBITDA
            ebitda = inputs.get('ebitda', 0)
            impots = inputs.get('impots', 0)
            capex = inputs.get('investissements_recurrents', 0)
            service = inputs.get('service_dette_annuel', 0)
            cash_flow = result.get('cash_flow_disponible', ebitda - impots - capex)

            return f"""
### 📐 Formule: DSCR (Debt Service Coverage Ratio)

**Méthode:** Via EBITDA

**Étape 1:** Calcul du cash flow disponible
```
Cash Flow Disponible = EBITDA - Impôts - Investissements Récurrents
                     = {ebitda:,.0f} - {impots:,.0f} - {capex:,.0f}
                     = {cash_flow:,.0f} FCFA
```

**Étape 2:** Calcul du DSCR
```
DSCR = Cash Flow Disponible ÷ Service de Dette Annuel
     = {cash_flow:,.0f} ÷ {service:,.0f}
     = {result.get('dscr', 0):.2f}
```

**📊 Interprétation:**
- **DSCR = {result.get('dscr', 0):.2f}**
- **Signification:** {"❌ Cash flow insuffisant (< 1.0)" if result.get('dscr', 0) < 1.0 else "⚠️ Marge faible (1.0-1.25)" if result.get('dscr', 0) < 1.25 else "✅ Couverture saine (1.25-1.5)" if result.get('dscr', 0) < 1.5 else "✅✅ Excellente couverture (≥ 1.5)"}

**💡 Benchmarks:**
- DSCR < 1.0: Risque élevé, cash insuffisant
- DSCR 1.0-1.25: Acceptable mais serré
- DSCR 1.25-1.5: Confortable
- DSCR > 1.5: Très bon
"""
        else:
            # Direct
            cash_flow = inputs.get('cash_flow_disponible', 0)
            service = inputs.get('service_dette_annuel', 0)

            return f"""
### 📐 Formule: DSCR (Debt Service Coverage Ratio)

**Méthode:** Calcul direct

```
DSCR = Cash Flow Disponible ÷ Service de Dette Annuel
     = {cash_flow:,.0f} ÷ {service:,.0f}
     = {result.get('dscr', 0):.2f}
```

**📊 Interprétation:**
- **DSCR = {result.get('dscr', 0):.2f}**
- **Signification:** {"❌ Cash flow insuffisant (< 1.0)" if result.get('dscr', 0) < 1.0 else "⚠️ Marge faible (1.0-1.25)" if result.get('dscr', 0) < 1.25 else "✅ Couverture saine (1.25-1.5)" if result.get('dscr', 0) < 1.5 else "✅✅ Excellente couverture (≥ 1.5)"}

**💡 Benchmarks:**
- DSCR < 1.0: Risque élevé
- DSCR 1.0-1.25: Acceptable
- DSCR 1.25-1.5: Confortable
- DSCR > 1.5: Excellent
"""

    @staticmethod
    def _formula_ltv(inputs: Dict, result: Dict) -> str:
        valeur = inputs.get('valeur_garantie', 0)
        montant = inputs.get('montant_pret', 0)
        ltv_max = inputs.get('ltv_max_autorisee', 0)

        return f"""
### 📐 Formule: LTV (Loan-to-Value)

**Formule simple:**
```
LTV = Montant du Prêt ÷ Valeur de la Garantie
    = {montant:,.0f} ÷ {valeur:,.0f}
    = {result.get('ltv', 0)*100:.1f}%
```

**Conformité à la politique:**
```
LTV calculé: {result.get('ltv', 0)*100:.1f}%
LTV maximum autorisé: {ltv_max*100:.0f}%
{"✅ Conforme" if result.get('conforme_politique') else "❌ Non conforme - LTV trop élevé"}
Marge: {(ltv_max - result.get('ltv', 0))*100:.1f}%
```

**📊 Interprétation:**
- **LTV ≤ 50%:** Très sûr
- **LTV 50-70%:** Standard immobilier
- **LTV 70-80%:** Acceptable avec garanties
- **LTV > 80%:** Risqué, nécessite assurances
"""

    @staticmethod
    def _formula_epargne(inputs: Dict, result: Dict) -> str:
        objectif = inputs.get('objectif_montant', 0)
        duree = inputs.get('duree_annees', 0)
        taux = inputs.get('taux_rendement_annuel', 0)

        i = taux / 12
        n = duree * 12

        return f"""
### 📐 Formule: Plan d'Épargne (Versements Constants)

**Objectif:** Atteindre {objectif:,.0f} FCFA en {duree} ans

**Variables:**
```
i = Taux annuel ÷ 12 = {taux*100:.2f}% ÷ 12 = {i*100:.4f}%
n = Durée × 12 = {duree} × 12 = {n} mois
```

**Formule (valeur future d'annuités):**
```
Versement mensuel = Objectif ÷ [((1 + i)^n - 1) ÷ i]

Calcul:
  Versement = {objectif:,.0f} ÷ [((1 + {i:.6f})^{n} - 1) ÷ {i:.6f}]
            = {objectif:,.0f} ÷ {((1 + i)**n - 1) / i:.4f}
            = {result.get('versement_mensuel_necessaire', 0):,.0f} FCFA
```

**📊 Résultat:**
- **Versement mensuel:** {result.get('versement_mensuel_necessaire', 0):,.0f} FCFA
- **Total versé:** {result.get('versement_mensuel_necessaire', 0) * n:,.0f} FCFA
- **Intérêts gagnés:** {objectif - result.get('versement_mensuel_necessaire', 0) * n:,.0f} FCFA
- **Rendement effectif:** {(objectif / (result.get('versement_mensuel_necessaire', 0) * n) - 1)*100:.2f}%
"""

    # ============================================================
    # EXPERT LLM VERIFICATION PROMPTS
    # ============================================================

    @staticmethod
    def get_expert_prompt(calc_type: str, inputs: Dict[str, Any], result: Dict[str, Any]) -> str:
        """
        Get expert LLM verification prompt for a calculation

        Args:
            calc_type: Type of calculation
            inputs: Input parameters
            result: Calculation result

        Returns:
            Structured prompt for expert LLM verification (Qwen 32B)
        """
        prompts = {
            'capacite_emprunt': CalculatorFormulas._expert_capacite_emprunt,
            'simulation_pret': CalculatorFormulas._expert_simulation_pret,
            'commission_garantie': CalculatorFormulas._expert_commission_garantie,
            'dscr_entreprise': CalculatorFormulas._expert_dscr,
            'ltv_garantie': CalculatorFormulas._expert_ltv,
            'epargne_objectif': CalculatorFormulas._expert_epargne,
        }

        prompt_func = prompts.get(calc_type)
        if prompt_func:
            return prompt_func(inputs, result)
        else:
            return CalculatorFormulas._generic_expert_prompt(calc_type, inputs, result)

    @staticmethod
    def _expert_capacite_emprunt(inputs: Dict, result: Dict) -> str:
        return f"""Tu es un expert en crédit bancaire dans la zone UEMOA. Analyse ce calcul de capacité d'emprunt:

**PARAMÈTRES DU CLIENT:**
- Revenu mensuel net: {inputs.get('revenu_mensuel_net', 0):,.0f} FCFA
- Charges mensuelles existantes: {inputs.get('charges_mensuelles_existantes', 0):,.0f} FCFA
- Taux d'endettement maximum: {inputs.get('taux_endettement_max', 0.4)*100:.0f}%
- Durée souhaitée: {inputs.get('duree_annees', 0)} ans
- Taux du crédit: {inputs.get('taux_credit_annuel', 0)*100:.2f}%

**RÉSULTATS CALCULÉS:**
- Montant maximum empruntable: {result.get('montant_max_pret', 0):,.0f} FCFA
- Mensualité du nouveau crédit: {result.get('mensualite_nouveau_credit', 0):,.0f} FCFA
- Taux d'endettement actuel: {result.get('taux_endettement_actuel', 0)*100:.1f}%
- Taux d'endettement projeté: {result.get('taux_endettement_projete', 0)*100:.1f}%

**TES TÂCHES:**
1. **VALIDATION MATHÉMATIQUE:** Vérifie la cohérence des calculs (formule d'annuité constante, taux d'endettement).

2. **ANALYSE DE FAISABILITÉ:** Évalue si ce montant est réaliste pour ce profil de client:
   - Le reste à vivre est-il suffisant?
   - Le taux d'endettement projeté est-il acceptable?
   - La durée est-elle adaptée au profil?

3. **RISQUES IDENTIFIÉS:** Liste les risques potentiels (ex: faible marge, durée longue, charges élevées).

4. **RECOMMANDATIONS STRATÉGIQUES:** Propose des conseils concrets:
   - Ajustements possibles (durée, montant)
   - Documents à préparer
   - Points d'attention pour la banque

**FORMAT DE RÉPONSE:**
Utilise des sections claires (✅ Validation, ⚠️ Risques, 💡 Recommandations).
Sois concis, précis et professionnel. Maximum 1500 tokens."""

    @staticmethod
    def _expert_simulation_pret(inputs: Dict, result: Dict) -> str:
        return f"""Tu es un expert en financement bancaire. Analyse cette simulation de prêt:

**PARAMÈTRES DU PRÊT:**
- Montant emprunté: {inputs.get('montant_pret', 0):,.0f} FCFA
- Durée: {inputs.get('duree_annees', 0)} ans ({inputs.get('duree_annees', 0)*12} mois)
- Taux nominal annuel: {inputs.get('taux_credit_annuel', 0)*100:.2f}%
- Taux assurance: {inputs.get('taux_assurance_annuel', 0)*100:.2f}%
- Frais de dossier: {inputs.get('frais_dossier', 0):,.0f} FCFA

**RÉSULTATS:**
- Mensualité (hors assurance): {result.get('mensualite_hors_assurance', 0):,.0f} FCFA
- Mensualité assurance: {result.get('mensualite_assurance', 0):,.0f} FCFA
- Mensualité totale: {result.get('mensualite_totale', 0):,.0f} FCFA
- Coût total des intérêts: {result.get('cout_interets_total', 0):,.0f} FCFA
- Coût total global: {result.get('cout_total_global', 0):,.0f} FCFA
- TAEG effectif: {result.get('taeg', 0)*100:.2f}%

**TES TÂCHES:**
1. **VALIDATION MATHÉMATIQUE:** Vérifie la formule d'annuité, le TAEG, et le coût total.

2. **ANALYSE ÉCONOMIQUE:**
   - Le coût du crédit est-il compétitif pour ce type de prêt?
   - Le TAEG est-il dans les normes BCEAO?
   - Les frais sont-ils proportionnés?

3. **COMPARAISON MARCHÉ:** Compare avec les standards du marché UEMOA pour cette durée et ce montant.

4. **RECOMMANDATIONS FINANCIÈRES:**
   - Opportunités de renégociation
   - Arbitrage durée vs mensualité
   - Optimisations possibles

**FORMAT:** Sections structurées (✅ Validation, 📊 Analyse, 💡 Recommandations). Maximum 1500 tokens."""

    @staticmethod
    def _expert_commission_garantie(inputs: Dict, result: Dict) -> str:
        type_gar = inputs.get('type_garantie', 'N/A')
        return f"""Tu es un expert en garanties bancaires (normes UEMOA). Analyse ce calcul:

**TYPE DE GARANTIE:** {type_gar.replace('_', ' ').title()}

**PARAMÈTRES:**
- Montant du marché: {inputs.get('montant_marche', 0):,.0f} FCFA
- Taux de garantie: {inputs.get('taux_garantie', 0)*100:.1f}%
- Durée: {inputs.get('duree_mois', 0)} mois
- Taux de commission annuel: {inputs.get('taux_commission_annuel', 0)*100:.2f}%
- Minimum forfaitaire: {inputs.get('minimum_forfaitaire', 0):,.0f} FCFA
- Taux de couverture (blocage): {inputs.get('taux_couverture', 0)*100:.0f}%

**RÉSULTATS:**
- Montant garanti: {result.get('montant_garantie', 0):,.0f} FCFA
- Commission théorique: {result.get('commission_theorique', 0):,.0f} FCFA
- Commission facturée: {result.get('commission_facturee', 0):,.0f} FCFA
- Total frais: {result.get('total_frais', 0):,.0f} FCFA
- Couverture exigée: {result.get('couverture_exigee', 0):,.0f} FCFA

**TES TÂCHES:**
1. **VALIDATION CONFORMITÉ:** Vérifie que les paramètres respectent les standards UEMOA pour ce type de garantie.

2. **ANALYSE FINANCIÈRE:**
   - Le taux de garantie est-il approprié pour ce type?
   - La commission est-elle dans les fourchettes standards?
   - Le blocage de trésorerie est-il justifié?

3. **IMPACT TRÉSORERIE:** Évalue l'impact du blocage de fonds sur la trésorerie du client.

4. **RECOMMANDATIONS:**
   - Négociation possible (taux, durée, couverture)
   - Alternatives (caution bancaire vs garantie à première demande)
   - Optimisation du coût

**STANDARDS UEMOA:**
- Soumission: 1-3%, 3-6 mois
- Bonne Exécution: 5-10%, durée contrat + 6-12 mois
- Acompte: 20-30%, 6-12 mois
- Retenue: 5-10%, 12-24 mois

**FORMAT:** Sections claires. Maximum 1500 tokens."""

    @staticmethod
    def _expert_dscr(inputs: Dict, result: Dict) -> str:
        if 'ebitda' in inputs:
            method = "Via EBITDA"
            params = f"""- EBITDA: {inputs.get('ebitda', 0):,.0f} FCFA
- Impôts: {inputs.get('impots', 0):,.0f} FCFA
- Investissements récurrents: {inputs.get('investissements_recurrents', 0):,.0f} FCFA
- Cash flow disponible: {result.get('cash_flow_disponible', 0):,.0f} FCFA"""
        else:
            method = "Direct"
            params = f"- Cash flow disponible: {inputs.get('cash_flow_disponible', 0):,.0f} FCFA"

        return f"""Tu es un analyste crédit expert pour entreprises. Analyse ce DSCR:

**MÉTHODE:** {method}

**PARAMÈTRES:**
{params}
- Service de dette annuel: {inputs.get('service_dette_annuel', 0):,.0f} FCFA

**RÉSULTAT:**
- **DSCR = {result.get('dscr', 0):.2f}**

**TES TÂCHES:**
1. **VALIDATION CALCUL:** Vérifie la cohérence du DSCR avec les flux de trésorerie.

2. **ANALYSE DE SOLVABILITÉ:**
   - L'entreprise peut-elle honorer sa dette?
   - Quelle est la marge de sécurité?
   - Benchmark vs normes bancaires (DSCR min: 1.25)

3. **RISQUES:**
   - Sensibilité aux variations de revenus
   - Robustesse face aux chocs économiques
   - Points de vigilance

4. **RECOMMANDATIONS:**
   - Niveau d'endettement supplémentaire possible
   - Mesures d'amélioration du DSCR
   - Covenants à mettre en place

**BENCHMARKS:**
- < 1.0: Risque élevé, défaut probable
- 1.0-1.25: Acceptable, marge faible
- 1.25-1.5: Confortable
- > 1.5: Excellent

**FORMAT:** Analyse structurée. Maximum 1500 tokens."""

    @staticmethod
    def _expert_ltv(inputs: Dict, result: Dict) -> str:
        return f"""Tu es un expert en gestion des garanties bancaires. Analyse ce LTV:

**PARAMÈTRES:**
- Valeur de la garantie: {inputs.get('valeur_garantie', 0):,.0f} FCFA
- Montant du prêt: {inputs.get('montant_pret', 0):,.0f} FCFA
- LTV maximum autorisé: {inputs.get('ltv_max_autorisee', 0)*100:.0f}%

**RÉSULTATS:**
- **LTV calculé: {result.get('ltv', 0)*100:.1f}%**
- **Conformité: {"✅ Conforme" if result.get('conforme_politique') else "❌ Non conforme"}**
- **Marge de sécurité: {(inputs.get('ltv_max_autorisee', 0) - result.get('ltv', 0))*100:.1f}%**

**TES TÂCHES:**
1. **VALIDATION:** Vérifie le calcul et la conformité à la politique de crédit.

2. **ANALYSE DU RISQUE:**
   - Niveau de couverture de la garantie
   - Risque de dépréciation
   - Coussin de sécurité suffisant?

3. **TYPE DE GARANTIE:** Évalue si le type de garantie est approprié:
   - Immobilier: LTV standard 70-80%
   - Véhicules: LTV max 70% (dépréciation rapide)
   - Équipements: LTV max 60%
   - Titres financiers: LTV 50-70% selon liquidité

4. **RECOMMANDATIONS:**
   - Ajustements possibles (montant, garantie complémentaire)
   - Assurances recommandées
   - Réévaluation périodique

**FORMAT:** Sections claires. Maximum 1500 tokens."""

    @staticmethod
    def _expert_epargne(inputs: Dict, result: Dict) -> str:
        return f"""Tu es un conseiller en gestion de patrimoine. Analyse ce plan d'épargne:

**OBJECTIF:**
- Montant cible: {inputs.get('objectif_montant', 0):,.0f} FCFA
- Durée: {inputs.get('duree_annees', 0)} ans
- Taux de rendement annuel: {inputs.get('taux_rendement_annuel', 0)*100:.2f}%

**RÉSULTATS:**
- Versement mensuel nécessaire: {result.get('versement_mensuel_necessaire', 0):,.0f} FCFA
- Total versé: {result.get('versement_mensuel_necessaire', 0) * inputs.get('duree_annees', 0) * 12:,.0f} FCFA
- Intérêts gagnés: {inputs.get('objectif_montant', 0) - result.get('versement_mensuel_necessaire', 0) * inputs.get('duree_annees', 0) * 12:,.0f} FCFA

**TES TÂCHES:**
1. **VALIDATION:** Vérifie le calcul de valeur future d'annuités constantes.

2. **FAISABILITÉ:**
   - Le versement mensuel est-il réaliste pour un revenu moyen?
   - L'objectif est-il atteignable avec ce taux?
   - La durée est-elle optimale?

3. **ANALYSE DU TAUX:**
   - Le taux de {inputs.get('taux_rendement_annuel', 0)*100:.2f}% est-il réaliste?
   - Produits d'épargne UEMOA offrant ce rendement
   - Risques associés

4. **RECOMMANDATIONS:**
   - Produits adaptés (DAT, OPCVM, obligations)
   - Diversification
   - Optimisation fiscale
   - Flexibilité vs rigidité

**PRODUITS UEMOA:**
- Compte épargne: 2-3.5%
- DAT: 4-6%
- Obligations: 5-7%
- OPCVM: 3-8% (risque variable)

**FORMAT:** Analyse structurée. Maximum 1500 tokens."""

    @staticmethod
    def _generic_expert_prompt(calc_type: str, inputs: Dict, result: Dict) -> str:
        """Fallback prompt for unknown calculator types"""
        return f"""Tu es un expert financier. Analyse ce calcul ({calc_type}):

**PARAMÈTRES:**
{inputs}

**RÉSULTATS:**
{result}

**TES TÂCHES:**
1. Valide la cohérence mathématique
2. Analyse la pertinence économique
3. Identifie les risques
4. Propose des recommandations

**FORMAT:** Réponse structurée et professionnelle. Maximum 1500 tokens."""


# End of file
