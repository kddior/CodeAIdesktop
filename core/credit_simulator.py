# -*- coding: utf-8 -*-
"""
Credit Simulator - Complete flow with slot tracking and calculation
Handles multi-turn credit simulation with persistent slot collection
"""

import re
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass, field


@dataclass
class CreditSlots:
    """Credit simulation slots with validation"""
    montant: Optional[float] = None          # Loan amount in FCFA
    duree_mois: Optional[int] = None         # Duration in months
    revenus: Optional[float] = None          # Monthly income
    charges: Optional[float] = None          # Monthly expenses (optional)
    type_credit: Optional[str] = None        # Credit type (optional)

    # Default values for UEMOA banking
    TAUX_ANNUEL_DEFAULT = 8.5                # 8.5% annual rate (UEMOA standard)
    TAUX_ENDETTEMENT_MAX = 33.0              # 33% max debt ratio

    def get_filled_slots(self) -> Dict[str, Any]:
        """Return only filled slots"""
        filled = {}
        if self.montant is not None:
            filled['montant'] = self.montant
        if self.duree_mois is not None:
            filled['duree_mois'] = self.duree_mois
        if self.revenus is not None:
            filled['revenus'] = self.revenus
        if self.charges is not None:
            filled['charges'] = self.charges
        if self.type_credit is not None:
            filled['type_credit'] = self.type_credit
        return filled

    def get_missing_required(self) -> list:
        """Return list of missing required slots"""
        missing = []
        if self.montant is None:
            missing.append('montant')
        if self.duree_mois is None:
            missing.append('duree_mois')
        if self.revenus is None:
            missing.append('revenus')
        return missing

    def is_complete(self) -> bool:
        """Check if all required slots are filled"""
        return (self.montant is not None and
                self.duree_mois is not None and
                self.revenus is not None)


class CreditSimulator:
    """
    Complete credit simulation flow with:
    - Persistent slot tracking across turns
    - Progressive information collection
    - Calculation when complete
    - Short, direct responses
    """

    # Questions for missing slots (short and direct)
    SLOT_QUESTIONS = {
        'montant': "Quel montant souhaitez-vous emprunter (en FCFA) ?",
        'duree_mois': "Sur combien de mois souhaitez-vous rembourser ?",
        'revenus': "Quels sont vos revenus mensuels (en FCFA) ?",
        'charges': "Avez-vous des charges mensuelles (loyer, autres credits) ?",
    }

    # Slot labels for display
    SLOT_LABELS = {
        'montant': 'Montant',
        'duree_mois': 'Duree',
        'revenus': 'Revenus',
        'charges': 'Charges',
        'type_credit': 'Type',
    }

    def __init__(self):
        """Initialize credit simulator"""
        pass

    def extract_slots_from_message(self, message: str, existing_slots: CreditSlots) -> CreditSlots:
        """
        Extract slot values from user message using regex.
        Merges with existing slots (existing values are NOT overwritten unless new value found).

        Args:
            message: User message to parse
            existing_slots: Existing CreditSlots to merge with

        Returns:
            Updated CreditSlots
        """
        msg_lower = message.lower()
        msg_normalized = self._normalize_numbers(message)

        # Create copy of existing slots
        slots = CreditSlots(
            montant=existing_slots.montant,
            duree_mois=existing_slots.duree_mois,
            revenus=existing_slots.revenus,
            charges=existing_slots.charges,
            type_credit=existing_slots.type_credit
        )

        # Extract amounts with context
        amounts = self._extract_amounts(msg_normalized)

        # Classify amounts by context
        for amount, context in amounts:
            context_lower = context.lower()

            # Check for income/salary keywords
            if any(kw in context_lower for kw in ['revenu', 'salaire', 'gagne', 'touche', 'mensuel']):
                if 'charge' not in context_lower and 'loyer' not in context_lower:
                    slots.revenus = amount
                    continue

            # Check for expense/charge keywords
            if any(kw in context_lower for kw in ['charge', 'loyer', 'depense', 'paye', 'credit']):
                slots.charges = amount
                continue

            # Check for loan amount keywords
            if any(kw in context_lower for kw in ['emprunter', 'pret', 'credit', 'besoin', 'montant', 'million']):
                slots.montant = amount
                continue

            # If no context and no montant yet, assume it's the loan amount
            if slots.montant is None and amount >= 100000:  # Min loan 100K
                slots.montant = amount
            # If montant filled but not revenus, might be revenus
            elif slots.revenus is None and amount >= 50000:  # Min salary 50K
                # Only if it looks like a salary range
                if amount <= 20000000:  # Max salary 20M
                    slots.revenus = amount

        # Extract duration
        duration = self._extract_duration(msg_normalized)
        if duration:
            slots.duree_mois = duration

        # Extract credit type
        credit_type = self._extract_credit_type(msg_lower)
        if credit_type:
            slots.type_credit = credit_type

        return slots

    def _normalize_numbers(self, text: str) -> str:
        """Normalize number formats in text"""
        # Replace common number words
        replacements = [
            (r'(\d+)\s*millions?', lambda m: str(int(m.group(1)) * 1000000)),
            (r'(\d+)\s*million', lambda m: str(int(m.group(1)) * 1000000)),
            (r'(\d+)\s*m(?:\s|$)', lambda m: str(int(m.group(1)) * 1000000) + ' '),
        ]

        result = text
        for pattern, replacement in replacements:
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)

        return result

    def _extract_amounts(self, text: str) -> list:
        """Extract amounts with surrounding context"""
        amounts = []

        # Pattern for numbers with optional currency
        pattern = r'(\d+(?:\s?\d{3})*(?:[.,]\d+)?)\s*(fcfa|xof|f|francs?)?'

        # Patterns that indicate duration (to exclude)
        duration_patterns = [
            r'\d+\s*ans?',
            r'\d+\s*annees?',
            r'\d+\s*mois',
            r'sur\s*\d+',
            r'pendant\s*\d+',
        ]

        for match in re.finditer(pattern, text, re.IGNORECASE):
            try:
                amount_str = match.group(1).replace(' ', '').replace(',', '.')
                value = float(amount_str)

                # Get context (50 chars before and after)
                start = max(0, match.start() - 50)
                end = min(len(text), match.end() + 50)
                context = text[start:end]

                # Skip if this number is part of a duration expression
                is_duration = False
                for dp in duration_patterns:
                    if re.search(dp, context, re.IGNORECASE):
                        # Check if the number we found IS the duration number
                        dur_match = re.search(dp, context, re.IGNORECASE)
                        if dur_match:
                            dur_num = re.search(r'\d+', dur_match.group())
                            if dur_num and dur_num.group() == match.group(1):
                                is_duration = True
                                break

                if is_duration:
                    continue

                amounts.append((value, context))
            except ValueError:
                continue

        return amounts

    def _extract_duration(self, text: str) -> Optional[int]:
        """Extract duration in months"""
        patterns = [
            (r'(\d+)\s*mois', 1),          # X mois
            (r'(\d+)\s*ans?', 12),          # X ans
            (r'(\d+)\s*annees?', 12),       # X annees
            (r'sur\s*(\d+)\s*mois', 1),     # sur X mois
            (r'sur\s*(\d+)\s*ans?', 12),    # sur X ans
            (r'pendant\s*(\d+)\s*mois', 1), # pendant X mois
            (r'pendant\s*(\d+)\s*ans?', 12),# pendant X ans
        ]

        for pattern, multiplier in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    value = int(match.group(1))
                    months = value * multiplier
                    # Validate range (6 months to 30 years)
                    if 6 <= months <= 360:
                        return months
                except ValueError:
                    continue

        return None

    def _extract_credit_type(self, text: str) -> Optional[str]:
        """Extract credit type from text"""
        type_keywords = {
            'immo': ['immobilier', 'maison', 'appartement', 'terrain', 'immo'],
            'auto': ['voiture', 'auto', 'vehicule', 'automobile'],
            'conso': ['consommation', 'personnel', 'conso'],
            'pro': ['professionnel', 'entreprise', 'business', 'commerce'],
        }

        for credit_type, keywords in type_keywords.items():
            if any(kw in text for kw in keywords):
                return credit_type

        return None

    def calculate(self, slots: CreditSlots) -> Dict[str, Any]:
        """
        Calculate credit simulation results.

        Args:
            slots: Filled CreditSlots

        Returns:
            Calculation results
        """
        if not slots.is_complete():
            return {'success': False, 'error': 'Slots incomplets'}

        montant = slots.montant
        duree_mois = slots.duree_mois
        revenus = slots.revenus
        charges = slots.charges or 0
        taux_annuel = CreditSlots.TAUX_ANNUEL_DEFAULT

        # Calculate monthly rate
        taux_mensuel = taux_annuel / 100 / 12

        # Calculate monthly payment using amortization formula
        # M = P * [r(1+r)^n] / [(1+r)^n - 1]
        if taux_mensuel > 0:
            factor = (1 + taux_mensuel) ** duree_mois
            mensualite = montant * (taux_mensuel * factor) / (factor - 1)
        else:
            mensualite = montant / duree_mois

        # Calculate total cost
        cout_total = mensualite * duree_mois
        cout_credit = cout_total - montant

        # Calculate debt ratio
        revenu_disponible = revenus - charges
        taux_endettement = (mensualite / revenus) * 100

        # Determine eligibility
        eligible = taux_endettement <= CreditSlots.TAUX_ENDETTEMENT_MAX

        # Generate recommendation
        if eligible:
            if taux_endettement <= 25:
                recommandation = "Excellent ! Votre capacite d'emprunt est tres bonne."
            elif taux_endettement <= 30:
                recommandation = "Bon profil. Ce credit est accessible pour vous."
            else:
                recommandation = "Acceptable. Attention a ne pas depasser ce montant."
        else:
            # Calculate max affordable loan
            max_mensualite = revenus * 0.33 - charges * 0.5
            if max_mensualite > 0:
                factor = (1 + taux_mensuel) ** duree_mois
                max_montant = max_mensualite * (factor - 1) / (taux_mensuel * factor)
                recommandation = f"Taux d'endettement trop eleve. Montant max conseille: {max_montant:,.0f} FCFA"
            else:
                recommandation = "Vos charges actuelles ne permettent pas ce credit."

        return {
            'success': True,
            'montant_demande': montant,
            'duree_mois': duree_mois,
            'taux_annuel': taux_annuel,
            'mensualite': round(mensualite),
            'cout_total': round(cout_total),
            'cout_credit': round(cout_credit),
            'revenus': revenus,
            'charges': charges,
            'taux_endettement': round(taux_endettement, 1),
            'pret_possible': eligible,
            'recommandation': recommandation
        }

    def get_next_response(self, slots: CreditSlots, is_first_message: bool = False) -> Tuple[str, bool]:
        """
        Generate next response based on current slot state.

        Args:
            slots: Current CreditSlots state
            is_first_message: True if this is the first message in the flow

        Returns:
            (response_text, is_complete)
        """
        missing = slots.get_missing_required()

        if not missing:
            # All slots filled - calculate and return result
            result = self.calculate(slots)
            response = self._format_calculation_result(result)
            return response, True

        # Build response asking for missing info
        filled = slots.get_filled_slots()

        if is_first_message:
            # First response - acknowledge and ask for first missing slot
            response = "Je vais simuler votre credit.\n\n"
            if filled:
                response += self._format_filled_slots(filled) + "\n"
            response += self.SLOT_QUESTIONS[missing[0]]
        else:
            # Subsequent response - acknowledge what was provided, ask for next
            if filled:
                response = "Bien note.\n"
            else:
                response = ""
            response += self.SLOT_QUESTIONS[missing[0]]

        return response, False

    def _format_filled_slots(self, filled: Dict) -> str:
        """Format filled slots summary"""
        parts = []
        if 'montant' in filled:
            parts.append(f"Montant: {filled['montant']:,.0f} FCFA")
        if 'duree_mois' in filled:
            years = filled['duree_mois'] // 12
            months = filled['duree_mois'] % 12
            if years > 0 and months > 0:
                parts.append(f"Duree: {years} an(s) et {months} mois")
            elif years > 0:
                parts.append(f"Duree: {years} an(s)")
            else:
                parts.append(f"Duree: {months} mois")
        if 'revenus' in filled:
            parts.append(f"Revenus: {filled['revenus']:,.0f} FCFA/mois")
        if 'charges' in filled:
            parts.append(f"Charges: {filled['charges']:,.0f} FCFA/mois")

        return "J'ai note:\n" + "\n".join(f"- {p}" for p in parts)

    def _format_calculation_result(self, result: Dict) -> str:
        """Format calculation result as short, clear response"""
        if not result['success']:
            return f"Erreur: {result.get('error', 'Calcul impossible')}"

        status = "ELIGIBLE" if result['pret_possible'] else "NON ELIGIBLE"
        status_emoji = "✅" if result['pret_possible'] else "⚠️"

        # Format duration nicely
        duree = result['duree_mois']
        years = duree // 12
        months = duree % 12
        if years > 0 and months > 0:
            duree_str = f"{years} an(s) et {months} mois"
        elif years > 0:
            duree_str = f"{years} an(s)"
        else:
            duree_str = f"{months} mois"

        response = f"""{status_emoji} **SIMULATION DE CREDIT** - {status}

**Votre demande:**
- Montant: {result['montant_demande']:,.0f} FCFA
- Duree: {duree_str}
- Taux: {result['taux_annuel']}% annuel

**Resultat:**
- Mensualite: **{result['mensualite']:,.0f} FCFA/mois**
- Cout du credit: {result['cout_credit']:,.0f} FCFA
- Total a rembourser: {result['cout_total']:,.0f} FCFA
- Taux d'endettement: **{result['taux_endettement']:.1f}%**

{result['recommandation']}

_Simulation indicative. Contactez un conseiller pour une offre personnalisee._"""

        return response


# Session helper functions
def get_credit_slots_from_session(session) -> CreditSlots:
    """Get or create CreditSlots from session"""
    if not hasattr(session, 'credit_slots') or session.credit_slots is None:
        session.credit_slots = CreditSlots()
    return session.credit_slots


def clear_credit_slots(session):
    """Clear credit slots from session"""
    if hasattr(session, 'credit_slots'):
        session.credit_slots = None


# Test
if __name__ == "__main__":
    print("=" * 60)
    print("CREDIT SIMULATOR TEST")
    print("=" * 60)

    sim = CreditSimulator()
    slots = CreditSlots()

    # Test messages simulating conversation
    messages = [
        "Je voudrais emprunter 10 millions",
        "Sur 4 ans",
        "Je gagne 4 millions par mois",
    ]

    for msg in messages:
        print(f"\n[USER] {msg}")
        slots = sim.extract_slots_from_message(msg, slots)
        print(f"[SLOTS] {slots.get_filled_slots()}")
        print(f"[MISSING] {slots.get_missing_required()}")

        response, is_complete = sim.get_next_response(slots, is_first_message=(msg == messages[0]))
        print(f"[RESPONSE]\n{response}")

        if is_complete:
            print("\n[COMPLETE] Simulation terminee!")
            break
