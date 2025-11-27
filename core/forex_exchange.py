# -*- coding: utf-8 -*-
"""
Forex Exchange Flow Handler - Currency buying/selling operations
Handles multi-turn forex requests with slot tracking
Based on AFG Bank UEMOA tariff rates
"""

import re
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime


class ForexOperationType(Enum):
    """Types of forex operations"""
    BUY = "buy"       # Buy foreign currency (client receives EUR/USD)
    SELL = "sell"     # Sell foreign currency (client gives EUR/USD, receives XOF)
    RATE_INFO = "info"  # Just get exchange rate info


@dataclass
class ForexSlots:
    """Forex exchange slots"""
    operation_type: Optional[ForexOperationType] = None
    currency: Optional[str] = None              # EUR, USD, GBP, etc.
    amount: Optional[float] = None              # Amount to exchange
    amount_currency: Optional[str] = None       # Is amount in XOF or foreign currency
    account_number: Optional[str] = None        # Debit/credit account (optional for info)
    confirmation: Optional[bool] = None

    # AFG Bank Forex Fees (from tariff - Section 7)
    EXCHANGE_RATES = {
        # Indicative rates (real rates would come from live feed)
        "EUR": 655.957,   # Fixed FCFA/EUR rate (CFA Franc zone)
        "USD": 600.00,    # Approximate
        "GBP": 760.00,    # Approximate
        "CHF": 680.00,    # Approximate
    }

    FEES = {
        "commission_client": 0.02,      # 2% for AFG clients
        "commission_non_client": 0.025, # 2.5% for non-clients
        "frais_dossier_caisse": 0.02,   # 2% for cash operations
        "tob_rate": 0.10,               # 10% TOB on commissions
        "commission_change": 0.02,      # 2% change commission
        "min_frais_dossier": 5000,      # Max 5,000 XOF for other currencies
    }

    def get_filled_slots(self) -> Dict[str, Any]:
        """Return only filled slots"""
        filled = {}
        if self.operation_type is not None:
            filled['operation_type'] = self.operation_type.value
        if self.currency is not None:
            filled['currency'] = self.currency
        if self.amount is not None:
            filled['amount'] = self.amount
        if self.amount_currency is not None:
            filled['amount_currency'] = self.amount_currency
        if self.account_number is not None:
            filled['account_number'] = self.account_number
        if self.confirmation is not None:
            filled['confirmation'] = self.confirmation
        return filled

    def get_missing_required(self) -> list:
        """Return list of missing required slots"""
        missing = []

        if self.operation_type is None:
            missing.append('operation_type')
            return missing

        # Rate info just needs currency
        if self.operation_type == ForexOperationType.RATE_INFO:
            if self.currency is None:
                missing.append('currency')
            return missing

        # Buy/Sell needs more info
        if self.currency is None:
            missing.append('currency')
        if self.amount is None:
            missing.append('amount')
        if self.confirmation is None:
            missing.append('confirmation')

        return missing

    def is_complete(self) -> bool:
        """Check if all required slots are filled"""
        return len(self.get_missing_required()) == 0


class ForexHandler:
    """
    Forex Exchange flow handler with:
    - Operation type detection (buy/sell/info)
    - Currency and amount extraction
    - Rate calculation with fees
    - Slot tracking across turns
    """

    SLOT_QUESTIONS = {
        'operation_type': "Que souhaitez-vous faire ?\n- Acheter des devises (EUR, USD...)\n- Vendre des devises\n- Connaitre le taux de change",
        'currency': "Quelle devise ? (EUR, USD, GBP, CHF...)",
        'amount': "Quel montant souhaitez-vous echanger ?",
        'confirmation': "Confirmez-vous cette operation ? (oui/non)",
    }

    CURRENCY_KEYWORDS = {
        "EUR": ["euro", "euros", "eur", "€"],
        "USD": ["dollar", "dollars", "usd", "$", "americain"],
        "GBP": ["livre", "livres", "gbp", "sterling", "£", "anglais"],
        "CHF": ["franc suisse", "chf", "suisse"],
    }

    OPERATION_KEYWORDS = {
        ForexOperationType.BUY: ["acheter", "achat", "obtenir", "avoir", "besoin de", "je veux"],
        ForexOperationType.SELL: ["vendre", "vente", "echanger", "convertir", "changer"],
        ForexOperationType.RATE_INFO: ["taux", "cours", "combien", "quel est", "rate", "cotation"],
    }

    def __init__(self):
        """Initialize forex handler"""
        pass

    def extract_slots_from_message(self, message: str, existing_slots: ForexSlots) -> ForexSlots:
        """Extract slot values from user message"""
        msg_lower = message.lower()

        # Create copy of existing slots
        slots = ForexSlots(
            operation_type=existing_slots.operation_type,
            currency=existing_slots.currency,
            amount=existing_slots.amount,
            amount_currency=existing_slots.amount_currency,
            account_number=existing_slots.account_number,
            confirmation=existing_slots.confirmation
        )

        # Extract operation type
        if slots.operation_type is None:
            for op_type, keywords in self.OPERATION_KEYWORDS.items():
                if any(kw in msg_lower for kw in keywords):
                    slots.operation_type = op_type
                    break

        # Extract currency
        if slots.currency is None:
            for currency, keywords in self.CURRENCY_KEYWORDS.items():
                if any(kw in msg_lower for kw in keywords):
                    slots.currency = currency
                    break

        # Extract amount
        if slots.amount is None:
            # Try to extract amount with currency context
            amount, amount_currency = self._extract_amount(message, slots.currency)
            if amount:
                slots.amount = amount
                slots.amount_currency = amount_currency

        # Extract confirmation
        if slots.confirmation is None:
            if any(kw in msg_lower for kw in ['oui', 'yes', 'confirme', 'ok', 'd\'accord', 'daccord']):
                slots.confirmation = True
            elif any(kw in msg_lower for kw in ['non', 'no', 'annule', 'annuler', 'cancel']):
                slots.confirmation = False

        return slots

    def _extract_amount(self, text: str, currency: str = None) -> Tuple[Optional[float], Optional[str]]:
        """Extract amount and determine if it's in XOF or foreign currency"""
        text_lower = text.lower()

        # Pattern for amounts
        patterns = [
            (r'(\d+(?:\s?\d{3})*(?:[.,]\d+)?)\s*(?:fcfa|xof|francs?)', 'XOF'),
            (r'(\d+(?:\s?\d{3})*(?:[.,]\d+)?)\s*(?:euros?|eur|€)', 'EUR'),
            (r'(\d+(?:\s?\d{3})*(?:[.,]\d+)?)\s*(?:dollars?|usd|\$)', 'USD'),
            (r'(\d+(?:\s?\d{3})*(?:[.,]\d+)?)\s*(?:livres?|gbp|£)', 'GBP'),
            (r'(\d+(?:\s?\d{3})*(?:[.,]\d+)?)', currency or 'XOF'),  # Default
        ]

        for pattern, amt_currency in patterns:
            match = re.search(pattern, text_lower, re.IGNORECASE)
            if match:
                try:
                    amount_str = match.group(1).replace(' ', '').replace(',', '.')
                    amount = float(amount_str)
                    if amount > 0:
                        return amount, amt_currency
                except ValueError:
                    continue

        return None, None

    def get_exchange_rate(self, currency: str) -> float:
        """Get exchange rate for currency"""
        return ForexSlots.EXCHANGE_RATES.get(currency, 0)

    def calculate_exchange(self, slots: ForexSlots, is_client: bool = True) -> Dict[str, Any]:
        """
        Calculate exchange with all fees

        Based on AFG Bank tariff section 7:
        - Commission de change: 2% (client) / 2.5% (non-client)
        - TOB: 10% of commissions
        - Frais de dossier (cash): 2%
        """
        if not slots.currency or not slots.amount:
            return {'success': False, 'error': 'Informations incompletes'}

        base_rate = self.get_exchange_rate(slots.currency)
        if base_rate == 0:
            return {'success': False, 'error': f'Devise {slots.currency} non supportee'}

        amount = slots.amount
        amount_currency = slots.amount_currency or 'XOF'

        # Determine commission rate
        commission_rate = ForexSlots.FEES['commission_client'] if is_client else ForexSlots.FEES['commission_non_client']
        tob_rate = ForexSlots.FEES['tob_rate']

        if slots.operation_type == ForexOperationType.BUY:
            # Client buys foreign currency, pays in XOF
            if amount_currency == 'XOF':
                # Amount is in XOF, calculate how much foreign currency client gets
                amount_xof = amount
            else:
                # Amount is in foreign currency, calculate XOF needed
                amount_xof = amount * base_rate

            # Apply fees (deducted from XOF)
            commission = amount_xof * commission_rate
            tob = commission * tob_rate
            total_fees = commission + tob

            # Net amount in foreign currency
            net_xof = amount_xof - total_fees
            foreign_amount = net_xof / base_rate

            result = {
                'success': True,
                'operation': 'ACHAT',
                'currency': slots.currency,
                'base_rate': base_rate,
                'amount_xof': round(amount_xof),
                'commission': round(commission),
                'tob': round(tob),
                'total_fees': round(total_fees),
                'net_xof': round(net_xof),
                'foreign_amount': round(foreign_amount, 2),
                'effective_rate': round(amount_xof / foreign_amount, 3) if foreign_amount > 0 else 0,
            }

        elif slots.operation_type == ForexOperationType.SELL:
            # Client sells foreign currency, receives XOF
            if amount_currency != 'XOF' and amount_currency == slots.currency:
                # Amount is in foreign currency
                foreign_amount = amount
                gross_xof = amount * base_rate
            else:
                # Amount is in XOF (target amount)
                gross_xof = amount
                foreign_amount = amount / base_rate

            # Apply fees (deducted from XOF received)
            commission = gross_xof * commission_rate
            tob = commission * tob_rate
            total_fees = commission + tob
            net_xof = gross_xof - total_fees

            result = {
                'success': True,
                'operation': 'VENTE',
                'currency': slots.currency,
                'base_rate': base_rate,
                'foreign_amount': round(foreign_amount, 2),
                'gross_xof': round(gross_xof),
                'commission': round(commission),
                'tob': round(tob),
                'total_fees': round(total_fees),
                'net_xof': round(net_xof),
                'effective_rate': round(net_xof / foreign_amount, 3) if foreign_amount > 0 else 0,
            }

        else:
            # Rate info only
            result = {
                'success': True,
                'operation': 'INFO',
                'currency': slots.currency,
                'base_rate': base_rate,
                'commission_rate': f"{commission_rate * 100}%",
                'tob_rate': f"{tob_rate * 100}%",
            }

        return result

    def get_next_response(self, slots: ForexSlots, is_first_message: bool = False) -> Tuple[str, bool]:
        """Generate next response based on current slot state"""
        missing = slots.get_missing_required()

        # Handle rate info immediately if complete
        if slots.operation_type == ForexOperationType.RATE_INFO and not missing:
            result = self.calculate_exchange(slots)
            response = self._format_rate_info(result)
            return response, True

        if not missing:
            # All slots filled for buy/sell - process
            result = self.calculate_exchange(slots)
            response = self._format_result(result, slots)
            return response, True

        # Build response asking for missing info
        filled = slots.get_filled_slots()

        if is_first_message:
            response = "Je vais vous aider avec votre operation de change.\n\n"
            if filled:
                response += self._format_filled_slots(filled) + "\n\n"
            response += self.SLOT_QUESTIONS[missing[0]]
        else:
            if filled and missing[0] != 'confirmation':
                response = "Bien note.\n"
            else:
                response = ""

            # Show calculation before confirmation
            if missing[0] == 'confirmation':
                result = self.calculate_exchange(slots)
                response += self._format_confirmation_request(result, slots)
            else:
                response += self.SLOT_QUESTIONS[missing[0]]

        return response, False

    def _format_filled_slots(self, filled: Dict) -> str:
        """Format filled slots summary"""
        parts = []
        if 'operation_type' in filled:
            op_labels = {'buy': 'Achat', 'sell': 'Vente', 'info': 'Info taux'}
            parts.append(f"Operation: {op_labels.get(filled['operation_type'], filled['operation_type'])}")
        if 'currency' in filled:
            parts.append(f"Devise: {filled['currency']}")
        if 'amount' in filled:
            currency = filled.get('amount_currency', 'XOF')
            parts.append(f"Montant: {filled['amount']:,.0f} {currency}")

        return "J'ai note:\n" + "\n".join(f"- {p}" for p in parts)

    def _format_rate_info(self, result: Dict) -> str:
        """Format rate information response"""
        if not result['success']:
            error_msg = result.get('error', "Impossible d'obtenir le taux")
            return f"Erreur: {error_msg}"

        currency = result['currency']
        rate = result['base_rate']

        response = f"""**TAUX DE CHANGE {currency}/XOF**

- Taux de base: 1 {currency} = **{rate:,.3f} FCFA**
- Commission change: {result['commission_rate']}
- TOB (Taxe): {result['tob_rate']} sur commissions

**Exemple:**
- 100 {currency} = {100 * rate:,.0f} FCFA (avant frais)
- 1,000,000 FCFA = {1000000 / rate:,.2f} {currency} (avant frais)

_Taux indicatif au {datetime.now().strftime('%d/%m/%Y %H:%M')}. Contactez votre agence pour le taux exact._"""

        return response

    def _format_confirmation_request(self, result: Dict, slots: ForexSlots) -> str:
        """Format confirmation request with calculation details"""
        if not result['success']:
            return f"Erreur: {result.get('error')}"

        if result['operation'] == 'ACHAT':
            response = f"""**RECAPITULATIF ACHAT {slots.currency}**

Vous payez: **{result['amount_xof']:,} FCFA**
- Commission: {result['commission']:,} FCFA
- TOB: {result['tob']:,} FCFA
- Total frais: {result['total_fees']:,} FCFA

Vous recevez: **{result['foreign_amount']:,.2f} {slots.currency}**
Taux effectif: 1 {slots.currency} = {result['effective_rate']:,.3f} FCFA

Confirmez-vous cette operation ? (oui/non)"""

        else:  # VENTE
            response = f"""**RECAPITULATIF VENTE {slots.currency}**

Vous donnez: **{result['foreign_amount']:,.2f} {slots.currency}**
Equivalent brut: {result['gross_xof']:,} FCFA
- Commission: {result['commission']:,} FCFA
- TOB: {result['tob']:,} FCFA
- Total frais: {result['total_fees']:,} FCFA

Vous recevez: **{result['net_xof']:,} FCFA**
Taux effectif: 1 {slots.currency} = {result['effective_rate']:,.3f} FCFA

Confirmez-vous cette operation ? (oui/non)"""

        return response

    def _format_result(self, result: Dict, slots: ForexSlots) -> str:
        """Format final transaction result"""
        if slots.confirmation == False:
            return "Operation annulee. Comment puis-je vous aider autrement ?"

        if not result['success']:
            return f"Erreur: {result.get('error', 'Operation impossible')}"

        status_emoji = "✅"
        op_label = "ACHAT" if result['operation'] == 'ACHAT' else "VENTE"

        if result['operation'] == 'ACHAT':
            response = f"""{status_emoji} **OPERATION DE CHANGE - {op_label} {slots.currency}**

**Transaction effectuee:**
- Debite: {result['amount_xof']:,} FCFA
- Credite: {result['foreign_amount']:,.2f} {slots.currency}
- Frais totaux: {result['total_fees']:,} FCFA
- Taux applique: 1 {slots.currency} = {result['effective_rate']:,.3f} FCFA

**Reference:** FOREX-{datetime.now().strftime('%Y%m%d%H%M%S')}

_Operation soumise a validation. Delai de traitement: 24-48h ouvrables._"""

        else:  # VENTE
            response = f"""{status_emoji} **OPERATION DE CHANGE - {op_label} {slots.currency}**

**Transaction effectuee:**
- Remis: {result['foreign_amount']:,.2f} {slots.currency}
- Credite: {result['net_xof']:,} FCFA
- Frais totaux: {result['total_fees']:,} FCFA
- Taux applique: 1 {slots.currency} = {result['effective_rate']:,.3f} FCFA

**Reference:** FOREX-{datetime.now().strftime('%Y%m%d%H%M%S')}

_Operation soumise a validation. Delai de traitement: 24-48h ouvrables._"""

        return response


# Session helper functions
def get_forex_slots_from_session(session) -> ForexSlots:
    """Get or create ForexSlots from session"""
    if not hasattr(session, 'forex_slots') or session.forex_slots is None:
        session.forex_slots = ForexSlots()
    return session.forex_slots


def clear_forex_slots(session):
    """Clear forex slots from session"""
    if hasattr(session, 'forex_slots'):
        session.forex_slots = None
    if hasattr(session, 'in_forex_flow'):
        session.in_forex_flow = False


# Test
if __name__ == "__main__":
    print("=" * 60)
    print("FOREX EXCHANGE FLOW TEST")
    print("=" * 60)

    handler = ForexHandler()

    # Test 1: Rate info
    print("\n--- TEST 1: Rate Info ---")
    slots = ForexSlots()
    messages_info = [
        "Quel est le taux de change euro ?",
    ]
    for msg in messages_info:
        print(f"\n[USER] {msg}")
        slots = handler.extract_slots_from_message(msg, slots)
        print(f"[SLOTS] {slots.get_filled_slots()}")
        response, is_complete = handler.get_next_response(slots, is_first_message=True)
        print(f"[RESPONSE]\n{response}")

    # Test 2: Buy euros
    print("\n--- TEST 2: Buy Euros ---")
    slots = ForexSlots()
    messages_buy = [
        "Je veux acheter des euros",
        "500000 FCFA",
        "oui",
    ]
    for i, msg in enumerate(messages_buy):
        print(f"\n[USER] {msg}")
        slots = handler.extract_slots_from_message(msg, slots)
        print(f"[SLOTS] {slots.get_filled_slots()}")
        response, is_complete = handler.get_next_response(slots, is_first_message=(i == 0))
        print(f"[RESPONSE]\n{response}")
        if is_complete:
            print("\n[COMPLETE] Operation terminee!")
            break

    # Test 3: Sell dollars
    print("\n--- TEST 3: Sell Dollars ---")
    slots = ForexSlots()
    messages_sell = [
        "Je veux vendre 200 dollars",
        "oui confirme",
    ]
    for i, msg in enumerate(messages_sell):
        print(f"\n[USER] {msg}")
        slots = handler.extract_slots_from_message(msg, slots)
        print(f"[SLOTS] {slots.get_filled_slots()}")
        response, is_complete = handler.get_next_response(slots, is_first_message=(i == 0))
        print(f"[RESPONSE]\n{response}")
        if is_complete:
            print("\n[COMPLETE] Operation terminee!")
            break
