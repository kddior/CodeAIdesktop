# -*- coding: utf-8 -*-
"""
Card Services Flow Handler - Block card, PIN change, Opposition, Limits
Handles multi-turn card service requests with slot tracking
"""

import re
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class CardServiceType(Enum):
    """Types of card service requests"""
    BLOCK = "block"           # Block/oppose card (lost/stolen)
    UNBLOCK = "unblock"       # Lift opposition
    PIN_CHANGE = "pin_change" # Request new PIN
    PIN_RESET = "pin_reset"   # Forgot PIN
    LIMIT_CHANGE = "limit"    # Change withdrawal/payment limits
    REISSUE = "reissue"       # Request new card


@dataclass
class CardServiceSlots:
    """Card service request slots"""
    service_type: Optional[CardServiceType] = None
    card_type: Optional[str] = None           # visa, mastercard, debit, etc.
    card_last_digits: Optional[str] = None    # Last 4 digits for identification
    reason: Optional[str] = None              # Why (lost, stolen, damaged, etc.)
    confirmation: Optional[bool] = None       # User confirmation

    # AFG Bank Fees (from tariff)
    FEES = {
        "block": 10000,       # Opposition sur carte: 10,000 XOF
        "unblock": 5000,      # Levee d'opposition: 5,000 XOF
        "pin_reset": 5000,    # Reedition code confidentiel: 5,000 XOF
        "reissue": 72727,     # Cout carte Visa Business
        "limit": 10000,       # Demande autorisation depassement: 10,000 XOF
    }

    def get_filled_slots(self) -> Dict[str, Any]:
        """Return only filled slots"""
        filled = {}
        if self.service_type is not None:
            filled['service_type'] = self.service_type.value
        if self.card_type is not None:
            filled['card_type'] = self.card_type
        if self.card_last_digits is not None:
            filled['card_last_digits'] = self.card_last_digits
        if self.reason is not None:
            filled['reason'] = self.reason
        if self.confirmation is not None:
            filled['confirmation'] = self.confirmation
        return filled

    def get_missing_required(self, service_type: CardServiceType = None) -> list:
        """Return list of missing required slots based on service type"""
        stype = service_type or self.service_type
        missing = []

        if self.service_type is None:
            missing.append('service_type')
            return missing  # Can't determine other requirements without service type

        # Card identification always needed
        if self.card_last_digits is None:
            missing.append('card_last_digits')

        # Reason needed for block/reissue
        if stype in [CardServiceType.BLOCK, CardServiceType.REISSUE]:
            if self.reason is None:
                missing.append('reason')

        # Confirmation needed before executing
        if self.confirmation is None:
            missing.append('confirmation')

        return missing

    def is_complete(self) -> bool:
        """Check if all required slots are filled"""
        return len(self.get_missing_required()) == 0


class CardServicesHandler:
    """
    Card Services flow handler with:
    - Service type detection
    - Slot tracking across turns
    - Fee information
    - Confirmation flow
    """

    SLOT_QUESTIONS = {
        'service_type': "Que souhaitez-vous faire avec votre carte ?\n- Bloquer (perdue/volee)\n- Debloquer\n- Changer le code PIN\n- Modifier les plafonds",
        'card_last_digits': "Quels sont les 4 derniers chiffres de votre carte ?",
        'reason': "Quelle est la raison ? (perdue, volee, endommagee, autre)",
        'confirmation': "Confirmez-vous cette operation ? (oui/non)",
    }

    SERVICE_KEYWORDS = {
        CardServiceType.BLOCK: ['bloquer', 'opposition', 'perdu', 'perdue', 'vole', 'volee', 'stolen', 'lost', 'annuler'],
        CardServiceType.UNBLOCK: ['debloquer', 'lever', 'reactiver', 'levee'],
        CardServiceType.PIN_CHANGE: ['changer', 'modifier', 'nouveau', 'pin', 'code'],
        CardServiceType.PIN_RESET: ['oublie', 'oublier', 'forgot', 'reset', 'reinitialiser'],
        CardServiceType.LIMIT_CHANGE: ['plafond', 'limite', 'augmenter', 'reduire', 'limit'],
        CardServiceType.REISSUE: ['nouvelle', 'nouveau', 'refaire', 'remplacer', 'renouveler'],
    }

    REASON_KEYWORDS = {
        'perdue': ['perdu', 'perdue', 'egare', 'lost'],
        'volee': ['vole', 'volee', 'stolen', 'vol'],
        'endommagee': ['endommage', 'casse', 'defectueuse', 'abime', 'damaged'],
        'expire': ['expire', 'expiration', 'perime'],
    }

    def __init__(self):
        """Initialize card services handler"""
        pass

    def extract_slots_from_message(self, message: str, existing_slots: CardServiceSlots) -> CardServiceSlots:
        """Extract slot values from user message"""
        msg_lower = message.lower()

        # Create copy of existing slots
        slots = CardServiceSlots(
            service_type=existing_slots.service_type,
            card_type=existing_slots.card_type,
            card_last_digits=existing_slots.card_last_digits,
            reason=existing_slots.reason,
            confirmation=existing_slots.confirmation
        )

        # Extract service type
        if slots.service_type is None:
            for stype, keywords in self.SERVICE_KEYWORDS.items():
                if any(kw in msg_lower for kw in keywords):
                    slots.service_type = stype
                    break

        # Extract card type
        if slots.card_type is None:
            if any(kw in msg_lower for kw in ['visa', 'business']):
                slots.card_type = 'visa_business'
            elif any(kw in msg_lower for kw in ['mastercard', 'master']):
                slots.card_type = 'mastercard'
            elif any(kw in msg_lower for kw in ['debit', 'retrait']):
                slots.card_type = 'debit'

        # Extract last 4 digits
        if slots.card_last_digits is None:
            digit_match = re.search(r'\b(\d{4})\b', message)
            if digit_match:
                slots.card_last_digits = digit_match.group(1)

        # Extract reason
        if slots.reason is None:
            for reason, keywords in self.REASON_KEYWORDS.items():
                if any(kw in msg_lower for kw in keywords):
                    slots.reason = reason
                    break

        # Extract confirmation
        if slots.confirmation is None:
            if any(kw in msg_lower for kw in ['oui', 'yes', 'confirme', 'ok', 'd\'accord', 'daccord']):
                slots.confirmation = True
            elif any(kw in msg_lower for kw in ['non', 'no', 'annule', 'annuler', 'cancel']):
                slots.confirmation = False

        return slots

    def get_fee(self, service_type: CardServiceType) -> int:
        """Get fee for service type"""
        return CardServiceSlots.FEES.get(service_type.value, 0)

    def process_request(self, slots: CardServiceSlots) -> Dict[str, Any]:
        """
        Process card service request (simulated backend call)
        In production, this would call the actual banking API
        """
        if not slots.is_complete():
            return {'success': False, 'error': 'Informations incompletes'}

        if not slots.confirmation:
            return {'success': False, 'cancelled': True, 'message': 'Operation annulee par le client'}

        fee = self.get_fee(slots.service_type)

        # Simulate successful processing
        result = {
            'success': True,
            'service_type': slots.service_type.value,
            'card_last_digits': slots.card_last_digits,
            'fee_charged': fee,
            'reference': f"CARD-{slots.service_type.value.upper()}-{slots.card_last_digits}",
        }

        # Add service-specific info
        if slots.service_type == CardServiceType.BLOCK:
            result['message'] = "Carte bloquee avec succes"
            result['next_steps'] = "Rendez-vous en agence pour une nouvelle carte"
        elif slots.service_type == CardServiceType.UNBLOCK:
            result['message'] = "Opposition levee avec succes"
            result['next_steps'] = "Votre carte est maintenant active"
        elif slots.service_type in [CardServiceType.PIN_CHANGE, CardServiceType.PIN_RESET]:
            result['message'] = "Demande de nouveau PIN enregistree"
            result['next_steps'] = "Nouveau code disponible en agence sous 48h"
        elif slots.service_type == CardServiceType.LIMIT_CHANGE:
            result['message'] = "Demande de modification de plafond enregistree"
            result['next_steps'] = "Modification effective sous 24h"
        elif slots.service_type == CardServiceType.REISSUE:
            result['message'] = "Demande de nouvelle carte enregistree"
            result['next_steps'] = "Retrait en agence sous 5-7 jours ouvrables"

        return result

    def get_next_response(self, slots: CardServiceSlots, is_first_message: bool = False) -> Tuple[str, bool]:
        """Generate next response based on current slot state"""
        missing = slots.get_missing_required()

        if not missing:
            # All slots filled - process and return result
            result = self.process_request(slots)
            response = self._format_result(result, slots)
            return response, True

        # Build response asking for missing info
        filled = slots.get_filled_slots()

        if is_first_message:
            response = "Je vais vous aider avec votre carte bancaire.\n\n"
            if filled:
                response += self._format_filled_slots(filled) + "\n\n"
            response += self.SLOT_QUESTIONS[missing[0]]
        else:
            if filled and missing[0] != 'confirmation':
                response = "Bien note.\n"
            else:
                response = ""

            # Show fee before confirmation
            if missing[0] == 'confirmation' and slots.service_type:
                fee = self.get_fee(slots.service_type)
                response += self._format_confirmation_request(slots, fee)
            else:
                response += self.SLOT_QUESTIONS[missing[0]]

        return response, False

    def _format_filled_slots(self, filled: Dict) -> str:
        """Format filled slots summary"""
        parts = []
        if 'service_type' in filled:
            service_labels = {
                'block': 'Blocage de carte',
                'unblock': 'Deblocage de carte',
                'pin_change': 'Changement de PIN',
                'pin_reset': 'Reinitialisation PIN',
                'limit': 'Modification plafond',
                'reissue': 'Nouvelle carte',
            }
            parts.append(f"Service: {service_labels.get(filled['service_type'], filled['service_type'])}")
        if 'card_last_digits' in filled:
            parts.append(f"Carte: ****{filled['card_last_digits']}")
        if 'reason' in filled:
            parts.append(f"Raison: {filled['reason']}")

        return "J'ai note:\n" + "\n".join(f"- {p}" for p in parts)

    def _format_confirmation_request(self, slots: CardServiceSlots, fee: int) -> str:
        """Format confirmation request with fee"""
        service_labels = {
            CardServiceType.BLOCK: 'blocage de votre carte',
            CardServiceType.UNBLOCK: 'deblocage de votre carte',
            CardServiceType.PIN_CHANGE: 'changement de PIN',
            CardServiceType.PIN_RESET: 'reinitialisation du PIN',
            CardServiceType.LIMIT_CHANGE: 'modification des plafonds',
            CardServiceType.REISSUE: 'demande de nouvelle carte',
        }

        response = f"""**Recapitulatif de votre demande:**
- Service: {service_labels.get(slots.service_type, 'Service carte')}
- Carte: ****{slots.card_last_digits}
"""
        if slots.reason:
            response += f"- Raison: {slots.reason}\n"

        response += f"\n**Frais: {fee:,} FCFA**\n\n"
        response += "Confirmez-vous cette operation ? (oui/non)"

        return response

    def _format_result(self, result: Dict, slots: CardServiceSlots) -> str:
        """Format processing result"""
        if result.get('cancelled'):
            return "Operation annulee. Comment puis-je vous aider autrement ?"

        if not result['success']:
            return f"Erreur: {result.get('error', 'Operation impossible')}"

        status_emoji = "✅"

        response = f"""{status_emoji} **OPERATION CARTE EFFECTUEE**

**{result['message']}**

- Reference: {result['reference']}
- Frais debites: {result['fee_charged']:,} FCFA
- Carte concernee: ****{slots.card_last_digits}

**Prochaines etapes:**
{result['next_steps']}

_Pour toute question, contactez le service client AFG Bank._"""

        return response


# Session helper functions
def get_card_service_slots_from_session(session) -> CardServiceSlots:
    """Get or create CardServiceSlots from session"""
    if not hasattr(session, 'card_service_slots') or session.card_service_slots is None:
        session.card_service_slots = CardServiceSlots()
    return session.card_service_slots


def clear_card_service_slots(session):
    """Clear card service slots from session"""
    if hasattr(session, 'card_service_slots'):
        session.card_service_slots = None
    if hasattr(session, 'in_card_service_flow'):
        session.in_card_service_flow = False


# Test
if __name__ == "__main__":
    print("=" * 60)
    print("CARD SERVICES FLOW TEST")
    print("=" * 60)

    handler = CardServicesHandler()
    slots = CardServiceSlots()

    # Test conversation
    messages = [
        "Je veux bloquer ma carte, elle a ete volee",
        "Les 4 derniers chiffres sont 4521",
        "oui je confirme",
    ]

    for msg in messages:
        print(f"\n[USER] {msg}")
        slots = handler.extract_slots_from_message(msg, slots)
        print(f"[SLOTS] {slots.get_filled_slots()}")
        print(f"[MISSING] {slots.get_missing_required()}")

        response, is_complete = handler.get_next_response(slots, is_first_message=(msg == messages[0]))
        print(f"[RESPONSE]\n{response}")

        if is_complete:
            print("\n[COMPLETE] Operation terminee!")
            break
