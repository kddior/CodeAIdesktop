# -*- coding: utf-8 -*-
"""
Calculation Verifier - Uses expert LLM to verify financial calculations
Uses Qwen 32B or DeepSeek to double-check calculation logic
"""

import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class CalculationVerifier:
    """
    Verification layer for financial calculations

    Uses expert LLM (Qwen 32B or DeepSeek) to:
    1. Verify that the correct formula was used
    2. Check if inputs make sense
    3. Validate that result is reasonable

    IMPORTANT: Does NOT recalculate (math done by Python/Numpy)
    Only verifies LOGIC and REASONABLENESS
    """

    def __init__(self, expert_llm_model):
        """
        Initialize verifier

        Args:
            expert_llm_model: Expert LLM (Qwen 32B or DeepSeek)
        """
        self.expert_llm = expert_llm_model

    def verify_calculation(self, calc_type: str, inputs: Dict[str, Any],
                          result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Verify a financial calculation using expert LLM

        Args:
            calc_type: Type of calculation (e.g., "capacite_emprunt")
            inputs: Input parameters used
            result: Calculation result from FinancialCalculator

        Returns:
            {
                "is_valid": bool,
                "confidence": "high"|"medium"|"low",
                "issues": List[str],  # Any concerns found
                "recommendations": List[str],  # Suggestions for user
                "verification_summary": str
            }
        """
        if not self.expert_llm:
            # No expert LLM available - skip verification
            return {
                "is_valid": True,
                "confidence": "medium",
                "issues": [],
                "recommendations": [],
                "verification_summary": "Verification skipped (no expert LLM)"
            }

        prompt = self._build_verification_prompt(calc_type, inputs, result)

        try:
            response = self.expert_llm.generate(prompt, temperature=0.1)
            logger.info(f"[VERIFY] Expert LLM response: {response[:200]}...")

            # Parse JSON response
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                verification = json.loads(json_match.group())
                logger.info(f"[VERIFY] Result: {verification.get('is_valid')} "
                          f"(confidence: {verification.get('confidence')})")
                return verification
            else:
                logger.warning("[VERIFY] No JSON in expert response")
                return self._fallback_verification()

        except Exception as e:
            logger.error(f"[VERIFY] Error: {e}", exc_info=True)
            return self._fallback_verification()

    def _build_verification_prompt(self, calc_type: str, inputs: Dict, result: Dict) -> str:
        """Build verification prompt for expert LLM"""

        # Format inputs nicely
        inputs_str = json.dumps(inputs, indent=2, ensure_ascii=False)
        result_str = json.dumps(result.get("resultat", {}), indent=2, ensure_ascii=False)

        # Calculation-specific verification rules
        verification_rules = {
            "capacite_emprunt": """
FORMULE ATTENDUE:
1. Taux d'endettement actuel = charges / revenu
2. Mensualité max = revenu × taux_endettement_max
3. Mensualité disponible = max(0, mensualité_max - charges)
4. Montant max prêt = mensualité_dispo × (1 - (1+i)^-n) / i
   où i = taux_annuel/12, n = durée_ans×12

VÉRIFICATIONS:
- Taux d'endettement actuel < taux max ? (sinon warning)
- Mensualité disponible > 0 ? (sinon montant_max = 0)
- Montant max cohérent avec mensualité et durée ?
- Résultat raisonnable (pas trop élevé/bas) ?
""",
            "simulation_pret": """
FORMULE ATTENDUE:
1. Mensualité = montant × i / (1 - (1+i)^-n)
   où i = taux_annuel/12, n = durée_ans×12
2. Assurance = montant × taux_assurance/12
3. Coût total = (mensualité × n - montant) + assurance×n + frais

VÉRIFICATIONS:
- Mensualité cohérente avec montant/durée/taux ?
- Coût total > montant initial ?
- Assurance raisonnable (< 10% du total) ?
""",
            "dscr_entreprise": """
FORMULE ATTENDUE:
DSCR = cash_flow_disponible / service_dette_annuel

INTERPRÉTATION:
- DSCR < 1.0 : Insuffisant (warning)
- DSCR ≥ 1.0 et < 1.25 : Faible couverture
- DSCR ≥ 1.25 : Bonne couverture

VÉRIFICATIONS:
- DSCR cohérent avec cash flow et dette ?
- Niveau de risque approprié ?
"""
        }

        rules = verification_rules.get(calc_type, "Vérification générale de cohérence")

        prompt = f"""Tu es un expert financier senior qui vérifie des calculs bancaires.

TYPE DE CALCUL: {calc_type}

INPUTS (fournis par l'utilisateur):
{inputs_str}

RÉSULTAT (calculé par le système):
{result_str}

{rules}

TA TÂCHE:
Vérifier si le calcul est LOGIQUEMENT CORRECT et RAISONNABLE.

⚠️ IMPORTANT:
- NE RECALCULE PAS (le calcul est fait par du code précis)
- Vérifie seulement la LOGIQUE et la COHÉRENCE
- Détecte les inputs aberrants (ex: taux 80%, durée 200 ans)
- Détecte les résultats incohérents (ex: emprunt 1 milliard avec salaire 100k)

ANALYSE À FAIRE:

1. **Cohérence des inputs**:
   - Les valeurs sont-elles dans des plages normales ?
   - Y a-t-il des aberrations (taux trop élevé, durée trop longue) ?

2. **Cohérence du résultat**:
   - Le résultat est-il proportionnel aux inputs ?
   - Est-il dans une fourchette raisonnable ?

3. **Formule utilisée**:
   - La formule mathématique semble-t-elle correcte pour ce type de calcul ?

4. **Warnings pour l'utilisateur**:
   - Y a-t-il des risques à signaler ? (endettement élevé, durée longue, etc.)

Réponds UNIQUEMENT en JSON:
{{
  "is_valid": true|false,
  "confidence": "high"|"medium"|"low",
  "issues": [
    "Liste des problèmes détectés (si aucun: [])"
  ],
  "recommendations": [
    "Recommandations pour l'utilisateur (si applicable)"
  ],
  "verification_summary": "Résumé court en français (1-2 phrases)"
}}

EXEMPLES DE RÉPONSES:

Exemple 1 (tout va bien):
{{
  "is_valid": true,
  "confidence": "high",
  "issues": [],
  "recommendations": [],
  "verification_summary": "Calcul cohérent. La capacité d'emprunt de 11,9M XOF correspond bien aux revenus de 500k XOF avec 40% d'endettement max."
}}

Exemple 2 (warning taux élevé):
{{
  "is_valid": true,
  "confidence": "medium",
  "issues": ["Taux d'endettement actuel à 35% (proche de la limite)"],
  "recommendations": ["Attention: vous êtes proche du taux max. Évitez de nouveaux crédits."],
  "verification_summary": "Calcul correct mais taux d'endettement élevé."
}}

Exemple 3 (aberration détectée):
{{
  "is_valid": false,
  "confidence": "low",
  "issues": ["Durée de 100 ans est irréaliste", "Taux de 80% est anormalement élevé"],
  "recommendations": ["Vérifiez vos données. Les prêts bancaires standard sont sur 5-30 ans avec taux 5-15%."],
  "verification_summary": "Inputs aberrants détectés. Vérifiez les valeurs saisies."
}}"""

        return prompt

    def _fallback_verification(self) -> Dict[str, Any]:
        """Fallback when expert LLM fails"""
        return {
            "is_valid": True,
            "confidence": "low",
            "issues": [],
            "recommendations": [],
            "verification_summary": "Verification failed - using calculation result as-is"
        }

    def format_verification_for_user(self, verification: Dict[str, Any]) -> Optional[str]:
        """
        Format verification result as user-friendly message

        Args:
            verification: Verification result dict

        Returns:
            User message or None if no warnings
        """
        if not verification.get("issues") and not verification.get("recommendations"):
            return None  # No warnings

        parts = []

        if verification.get("issues"):
            parts.append("⚠️ **Points d'attention** :")
            for issue in verification["issues"]:
                parts.append(f"  • {issue}")

        if verification.get("recommendations"):
            parts.append("\n💡 **Recommandations** :")
            for rec in verification["recommendations"]:
                parts.append(f"  • {rec}")

        return "\n".join(parts)


# Testing
if __name__ == "__main__":
    from llm.openai_client import OpenAIClient

    logging.basicConfig(level=logging.INFO)

    # Use Qwen 14B for testing (in production, use 32B or DeepSeek)
    llm = OpenAIClient(base_url='http://localhost:1234/v1', model_name='qwen2.5-14b-instruct')
    verifier = CalculationVerifier(llm)

    print("=== Test Calculation Verification ===\n")

    # Test 1: Normal borrowing capacity
    print("[Test 1] Normal Borrowing Capacity")
    verification = verifier.verify_calculation(
        calc_type="capacite_emprunt",
        inputs={
            "revenu_mensuel_net": 500000,
            "charges_mensuelles_existantes": 100000,
            "taux_endettement_max": 0.4,
            "taux_credit_annuel": 0.08,
            "duree_annees": 20
        },
        result={
            "resultat": {
                "taux_endettement_actuel": 0.2,
                "montant_max_pret": 11955429.17,
                "mensualite_disponible_nouveau_credit": 100000
            }
        }
    )
    print(json.dumps(verification, indent=2, ensure_ascii=False))

    # Test 2: High debt ratio (warning expected)
    print("\n[Test 2] High Debt Ratio")
    verification = verifier.verify_calculation(
        calc_type="capacite_emprunt",
        inputs={
            "revenu_mensuel_net": 500000,
            "charges_mensuelles_existantes": 180000,  # 36% already
            "taux_endettement_max": 0.4,
            "taux_credit_annuel": 0.08,
            "duree_annees": 20
        },
        result={
            "resultat": {
                "taux_endettement_actuel": 0.36,
                "montant_max_pret": 4782171.67,
                "mensualite_disponible_nouveau_credit": 20000
            }
        }
    )
    print(json.dumps(verification, indent=2, ensure_ascii=False))
