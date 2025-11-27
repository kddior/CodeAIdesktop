# -*- coding: utf-8 -*-
"""
Payment Incidents Flow Handler - ATD, Saisies, Impayes, Rejets
Handles payment incident reporting and dispute flows
Based on AFG Bank tariff section 5 (Gestion des incidents de paiements)
"""

import re
from typing import Dict, Any, Optional, Tuple, List
from dataclasses import dataclass
from enum import Enum
from datetime import datetime


class IncidentType(Enum):
    """Types of payment incidents"""
    CHEQUE_IMPAYE = "cheque_impaye"         # Bounced cheque
    VIREMENT_REJETE = "virement_rejete"     # Rejected transfer
    PRELEVEMENT_REJETE = "prelevement_rejete"  # Rejected direct debit
    CARTE_REJETEE = "carte_rejetee"         # Card transaction rejected
    ATD = "atd"                              # Avis a Tiers Detenteur
    SAISIE = "saisie"                        # Saisie attribution
    OPPOSITION = "opposition"               # Payment opposition
    CONTESTATION = "contestation"           # Dispute a transaction


class IncidentStatus(Enum):
    """Status of incident resolution"""
    DECLARED = "declared"         # Just reported
    IN_REVIEW = "in_review"       # Under investigation
    RESOLVED = "resolved"         # Resolved
    ESCALATED = "escalated"       # Escalated to legal


@dataclass
class PaymentIncidentSlots:
    """Payment incident slots"""
    incident_type: Optional[IncidentType] = None
    transaction_ref: Optional[str] = None      # Reference number
    transaction_date: Optional[str] = None     # Date of incident
    amount: Optional[float] = None             # Amount involved
    description: Optional[str] = None          # User description
    account_number: Optional[str] = None       # Affected account
    contact_phone: Optional[str] = None        # Contact phone (optional)
    confirmation: Optional[bool] = None

    # AFG Bank Fees (from tariff - Section 5)
    FEES = {
        "cheque_impaye": 35000,           # Frais d'impaye cheque: 35,000 XOF
        "frais_impaye_general": 30000,    # Frais d'impayes: 30,000 XOF
        "atd": 50000,                     # Avis a Tiers Detenteur: 50,000 XOF
        "saisie_conservatoire": 50000,    # Frais saisie conservatoire: 50,000 XOF
        "saisie_attribution": 50000,      # Frais saisie attribution: 50,000 XOF
        "injonction": 7510,               # Frais d'injonction: 7,510 XOF
        "relance_pli_simple": 5000,       # Lettre de relance simple: 5,000 XOF
        "relance_recommande": 5000,       # Lettre de relance recommande: 5,000 XOF
        "duplicata_lettre": 5000,         # Duplicata lettre incident: 5,000 XOF
        "declaration_cip": 10000,         # Lettre declaration CIP: 10,000 XOF
        "prelevement_impaye": 2000,       # Frais prelevement impaye: 2,000 XOF
        "rejet_prelevement": 2500,        # Rejet prelevement client: 2,500 XOF
    }

    def get_filled_slots(self) -> Dict[str, Any]:
        """Return only filled slots"""
        filled = {}
        if self.incident_type is not None:
            filled['incident_type'] = self.incident_type.value
        if self.transaction_ref is not None:
            filled['transaction_ref'] = self.transaction_ref
        if self.transaction_date is not None:
            filled['transaction_date'] = self.transaction_date
        if self.amount is not None:
            filled['amount'] = self.amount
        if self.description is not None:
            filled['description'] = self.description
        if self.account_number is not None:
            filled['account_number'] = self.account_number
        if self.confirmation is not None:
            filled['confirmation'] = self.confirmation
        return filled

    def get_missing_required(self) -> list:
        """Return list of missing required slots"""
        missing = []

        if self.incident_type is None:
            missing.append('incident_type')
            return missing

        # Different requirements based on incident type
        if self.incident_type == IncidentType.CONTESTATION:
            # Contestation needs transaction ref and date
            if self.transaction_ref is None:
                missing.append('transaction_ref')
            if self.amount is None:
                missing.append('amount')
            if self.description is None:
                missing.append('description')
        elif self.incident_type in [IncidentType.CHEQUE_IMPAYE, IncidentType.VIREMENT_REJETE,
                                     IncidentType.PRELEVEMENT_REJETE]:
            # Incident reporting needs basic info
            if self.amount is None:
                missing.append('amount')
            if self.transaction_date is None:
                missing.append('transaction_date')
        elif self.incident_type in [IncidentType.ATD, IncidentType.SAISIE]:
            # Legal incidents - info only, no slot collection
            pass

        if self.confirmation is None:
            missing.append('confirmation')

        return missing

    def is_complete(self) -> bool:
        """Check if all required slots are filled"""
        return len(self.get_missing_required()) == 0


class PaymentIncidentsHandler:
    """
    Payment Incidents flow handler with:
    - Incident type detection
    - Transaction detail collection
    - Status tracking
    - Resolution guidance
    """

    SLOT_QUESTIONS = {
        'incident_type': "Quel type d'incident souhaitez-vous signaler ?\n- Cheque impaye\n- Virement rejete\n- Prelevement rejete\n- Transaction carte rejetee\n- Contestation de transaction\n- Information ATD/Saisie",
        'transaction_ref': "Quelle est la reference de la transaction ? (si disponible)",
        'transaction_date': "A quelle date a eu lieu l'incident ?",
        'amount': "Quel est le montant concerne ?",
        'description': "Decrivez brievement le probleme:",
        'confirmation': "Confirmez-vous cette declaration ? (oui/non)",
    }

    INCIDENT_KEYWORDS = {
        IncidentType.CHEQUE_IMPAYE: ['cheque impaye', 'cheque rejete', 'cheque refuse', 'cheque sans provision', 'bounce'],
        IncidentType.VIREMENT_REJETE: ['virement rejete', 'transfert echoue', 'virement annule', 'virement refuse'],
        IncidentType.PRELEVEMENT_REJETE: ['prelevement rejete', 'prelevement refuse', 'prelevement impaye'],
        IncidentType.CARTE_REJETEE: ['carte rejetee', 'carte refusee', 'paiement refuse', 'transaction echouee'],
        IncidentType.ATD: ['atd', 'avis tiers', 'detenteur', 'huissier'],
        IncidentType.SAISIE: ['saisie', 'saisir', 'bloquer compte', 'gele'],
        IncidentType.OPPOSITION: ['opposition', 'bloquer paiement', 'arreter paiement'],
        IncidentType.CONTESTATION: ['contester', 'contestation', 'dispute', 'erreur', 'fraude', 'pas moi', 'reconnais pas'],
    }

    def __init__(self):
        """Initialize payment incidents handler"""
        pass

    def extract_slots_from_message(self, message: str, existing_slots: PaymentIncidentSlots) -> PaymentIncidentSlots:
        """Extract slot values from user message"""
        msg_lower = message.lower()

        # Create copy of existing slots
        slots = PaymentIncidentSlots(
            incident_type=existing_slots.incident_type,
            transaction_ref=existing_slots.transaction_ref,
            transaction_date=existing_slots.transaction_date,
            amount=existing_slots.amount,
            description=existing_slots.description,
            account_number=existing_slots.account_number,
            contact_phone=existing_slots.contact_phone,
            confirmation=existing_slots.confirmation
        )

        # Extract incident type
        if slots.incident_type is None:
            for itype, keywords in self.INCIDENT_KEYWORDS.items():
                if any(kw in msg_lower for kw in keywords):
                    slots.incident_type = itype
                    break

        # Extract transaction reference
        if slots.transaction_ref is None:
            # Look for reference patterns
            ref_patterns = [
                r'ref[:\s]*([A-Z0-9\-]+)',
                r'reference[:\s]*([A-Z0-9\-]+)',
                r'\b([A-Z]{2,4}[0-9]{6,12})\b',  # Common ref format
            ]
            for pattern in ref_patterns:
                match = re.search(pattern, message, re.IGNORECASE)
                if match:
                    slots.transaction_ref = match.group(1)
                    break

        # Extract date
        if slots.transaction_date is None:
            date_patterns = [
                r'(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})',  # DD/MM/YYYY or DD-MM-YYYY
                r'(\d{1,2}\s+(?:janvier|fevrier|mars|avril|mai|juin|juillet|aout|septembre|octobre|novembre|decembre)\s+\d{4})',
                r'(hier|aujourd\'?hui|avant-?hier)',
            ]
            for pattern in date_patterns:
                match = re.search(pattern, msg_lower)
                if match:
                    slots.transaction_date = match.group(1)
                    break

        # Extract amount
        if slots.amount is None:
            amount_match = re.search(r'(\d+(?:\s?\d{3})*(?:[.,]\d+)?)\s*(?:fcfa|xof|francs?)?', msg_lower)
            if amount_match:
                try:
                    amount_str = amount_match.group(1).replace(' ', '').replace(',', '.')
                    slots.amount = float(amount_str)
                except ValueError:
                    pass

        # Extract description (if message is long enough and not just keywords)
        if slots.description is None and len(message) > 30:
            # Use the full message as description if it looks like a description
            if not any(kw in msg_lower for kw in ['oui', 'non', 'confirme', 'annule']):
                slots.description = message[:200]  # Limit to 200 chars

        # Extract account number
        if slots.account_number is None:
            acc_match = re.search(r'\b(\d{10,16})\b', message)
            if acc_match:
                slots.account_number = acc_match.group(1)

        # Extract confirmation
        if slots.confirmation is None:
            if any(kw in msg_lower for kw in ['oui', 'yes', 'confirme', 'ok', 'd\'accord']):
                slots.confirmation = True
            elif any(kw in msg_lower for kw in ['non', 'no', 'annule', 'annuler', 'cancel']):
                slots.confirmation = False

        return slots

    def get_fee(self, incident_type: IncidentType) -> int:
        """Get processing fee for incident type"""
        fee_map = {
            IncidentType.CHEQUE_IMPAYE: PaymentIncidentSlots.FEES['cheque_impaye'],
            IncidentType.VIREMENT_REJETE: PaymentIncidentSlots.FEES['frais_impaye_general'],
            IncidentType.PRELEVEMENT_REJETE: PaymentIncidentSlots.FEES['prelevement_impaye'],
            IncidentType.CARTE_REJETEE: 0,  # No specific fee for card rejection query
            IncidentType.ATD: PaymentIncidentSlots.FEES['atd'],
            IncidentType.SAISIE: PaymentIncidentSlots.FEES['saisie_attribution'],
            IncidentType.OPPOSITION: 10000,  # Opposition fee
            IncidentType.CONTESTATION: 0,    # No fee for disputes
        }
        return fee_map.get(incident_type, 0)

    def process_incident(self, slots: PaymentIncidentSlots) -> Dict[str, Any]:
        """
        Process payment incident (generate reference and next steps)
        In production, this would create a ticket in the banking system
        """
        if not slots.is_complete():
            return {'success': False, 'error': 'Informations incompletes'}

        if not slots.confirmation:
            return {'success': False, 'cancelled': True, 'message': 'Declaration annulee'}

        fee = self.get_fee(slots.incident_type)
        reference = f"INC-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        result = {
            'success': True,
            'incident_type': slots.incident_type.value,
            'reference': reference,
            'fee': fee,
            'status': IncidentStatus.DECLARED.value,
        }

        # Add type-specific guidance
        if slots.incident_type == IncidentType.CHEQUE_IMPAYE:
            result['message'] = "Incident cheque enregistre"
            result['next_steps'] = [
                "Un conseiller vous contactera sous 24h",
                "Frais d'impaye appliques au compte",
                "Lettre d'information sera envoyee a l'emetteur"
            ]
            result['resolution_time'] = "3-5 jours ouvrables"

        elif slots.incident_type == IncidentType.VIREMENT_REJETE:
            result['message'] = "Incident virement enregistre"
            result['next_steps'] = [
                "Verification des coordonnees bancaires",
                "Le montant sera recredite sous 2-3 jours",
                "Veuillez verifier les informations du beneficiaire"
            ]
            result['resolution_time'] = "2-3 jours ouvrables"

        elif slots.incident_type == IncidentType.PRELEVEMENT_REJETE:
            result['message'] = "Incident prelevement enregistre"
            result['next_steps'] = [
                "Contactez l'organisme emetteur",
                "Regularisez votre situation si necessaire",
                "Une relance peut etre effectuee"
            ]
            result['resolution_time'] = "1-2 jours ouvrables"

        elif slots.incident_type == IncidentType.CONTESTATION:
            result['message'] = "Contestation enregistree"
            result['next_steps'] = [
                "Dossier transmis au service contentieux",
                "Investigation en cours (delai: 10-15 jours)",
                "Conservez tous les justificatifs",
                "Un conseiller vous contactera"
            ]
            result['resolution_time'] = "10-15 jours ouvrables"

        elif slots.incident_type in [IncidentType.ATD, IncidentType.SAISIE]:
            result['message'] = "Information ATD/Saisie"
            result['next_steps'] = [
                "Contactez votre conseiller pour details",
                "Consultez un avocat si necessaire",
                "Les frais seront debites du compte"
            ]
            result['resolution_time'] = "Selon procedure legale"

        else:
            result['message'] = "Incident enregistre"
            result['next_steps'] = ["Un conseiller vous contactera"]
            result['resolution_time'] = "Variable"

        return result

    def get_next_response(self, slots: PaymentIncidentSlots, is_first_message: bool = False) -> Tuple[str, bool]:
        """Generate next response based on current slot state"""
        missing = slots.get_missing_required()

        # Special handling for ATD/Saisie - info only
        if slots.incident_type in [IncidentType.ATD, IncidentType.SAISIE]:
            response = self._format_atd_saisie_info(slots.incident_type)
            return response, True

        if not missing:
            # All slots filled - process
            result = self.process_incident(slots)
            response = self._format_result(result, slots)
            return response, True

        # Build response asking for missing info
        filled = slots.get_filled_slots()

        if is_first_message:
            response = "Je vais vous aider a signaler cet incident.\n\n"
            if filled:
                response += self._format_filled_slots(filled) + "\n\n"
            response += self.SLOT_QUESTIONS[missing[0]]
        else:
            if filled and missing[0] != 'confirmation':
                response = "Bien note.\n"
            else:
                response = ""

            # Show summary before confirmation
            if missing[0] == 'confirmation':
                response += self._format_confirmation_request(slots)
            else:
                response += self.SLOT_QUESTIONS[missing[0]]

        return response, False

    def _format_filled_slots(self, filled: Dict) -> str:
        """Format filled slots summary"""
        parts = []
        type_labels = {
            'cheque_impaye': 'Cheque impaye',
            'virement_rejete': 'Virement rejete',
            'prelevement_rejete': 'Prelevement rejete',
            'carte_rejetee': 'Transaction carte rejetee',
            'atd': 'ATD',
            'saisie': 'Saisie',
            'opposition': 'Opposition',
            'contestation': 'Contestation',
        }

        if 'incident_type' in filled:
            parts.append(f"Type: {type_labels.get(filled['incident_type'], filled['incident_type'])}")
        if 'amount' in filled:
            parts.append(f"Montant: {filled['amount']:,.0f} FCFA")
        if 'transaction_date' in filled:
            parts.append(f"Date: {filled['transaction_date']}")
        if 'transaction_ref' in filled:
            parts.append(f"Reference: {filled['transaction_ref']}")

        return "J'ai note:\n" + "\n".join(f"- {p}" for p in parts)

    def _format_atd_saisie_info(self, incident_type: IncidentType) -> str:
        """Format ATD/Saisie information response"""
        if incident_type == IncidentType.ATD:
            fee = PaymentIncidentSlots.FEES['atd']
            response = f"""**INFORMATION - AVIS A TIERS DETENTEUR (ATD)**

Un ATD est une procedure de recouvrement forcee initiee par l'administration fiscale.

**Ce que cela implique:**
- Blocage temporaire du compte
- Prelevement des sommes dues
- Frais ATD: **{fee:,} FCFA**

**Vos options:**
1. Regulariser la dette aupres du Tresor Public
2. Contester l'ATD (delai: 2 mois)
3. Demander un echeancier

**Important:**
- Le solde bancaire insaisissable (SBI) est preserve
- Contactez votre conseiller pour plus de details

_Pour toute contestation, consultez un avocat ou huissier._"""

        else:  # SAISIE
            fee = PaymentIncidentSlots.FEES['saisie_attribution']
            response = f"""**INFORMATION - SAISIE ATTRIBUTION**

Une saisie attribution est une procedure judiciaire de recouvrement de creance.

**Ce que cela implique:**
- Blocage des sommes sur le compte
- Attribution au creancier apres delai legal
- Frais de saisie: **{fee:,} FCFA**

**Vos options:**
1. Contester devant le juge (delai: 1 mois)
2. Negocier avec le creancier
3. Demander la mainlevee

**Montants proteges:**
- Solde bancaire insaisissable (SBI): ~150,000 FCFA
- Prestations familiales non saisissables

_Recommandation: Consultez un avocat pour vos droits._"""

        return response

    def _format_confirmation_request(self, slots: PaymentIncidentSlots) -> str:
        """Format confirmation request"""
        type_labels = {
            IncidentType.CHEQUE_IMPAYE: 'Cheque impaye',
            IncidentType.VIREMENT_REJETE: 'Virement rejete',
            IncidentType.PRELEVEMENT_REJETE: 'Prelevement rejete',
            IncidentType.CARTE_REJETEE: 'Transaction carte rejetee',
            IncidentType.CONTESTATION: 'Contestation de transaction',
            IncidentType.OPPOSITION: 'Opposition de paiement',
        }

        fee = self.get_fee(slots.incident_type)

        response = f"""**RECAPITULATIF DE L'INCIDENT**

- Type: {type_labels.get(slots.incident_type, 'Incident')}
"""
        if slots.amount:
            response += f"- Montant: {slots.amount:,} FCFA\n"
        if slots.transaction_date:
            response += f"- Date: {slots.transaction_date}\n"
        if slots.transaction_ref:
            response += f"- Reference: {slots.transaction_ref}\n"
        if slots.description:
            response += f"- Description: {slots.description[:100]}...\n"

        if fee > 0:
            response += f"\n**Frais de traitement: {fee:,} FCFA**\n"

        response += "\nConfirmez-vous cette declaration ? (oui/non)"

        return response

    def _format_result(self, result: Dict, slots: PaymentIncidentSlots) -> str:
        """Format processing result"""
        if result.get('cancelled'):
            return "Declaration annulee. Comment puis-je vous aider autrement ?"

        if not result['success']:
            error_msg = result.get('error', "Impossible de traiter l'incident")
            return f"Erreur: {error_msg}"

        status_emoji = "📋"

        next_steps = "\n".join(f"• {step}" for step in result.get('next_steps', []))

        response = f"""{status_emoji} **INCIDENT ENREGISTRE**

**{result['message']}**

- Reference dossier: **{result['reference']}**
- Statut: En cours de traitement
"""
        if result.get('fee', 0) > 0:
            response += f"- Frais: {result['fee']:,} FCFA\n"

        response += f"""- Delai estime: {result.get('resolution_time', 'Variable')}

**Prochaines etapes:**
{next_steps}

**Suivi:**
Vous pouvez suivre votre dossier avec la reference **{result['reference']}** ou contacter le service client.

_Conservez cette reference pour tout suivi._"""

        return response


# Session helper functions
def get_payment_incident_slots_from_session(session) -> PaymentIncidentSlots:
    """Get or create PaymentIncidentSlots from session"""
    if not hasattr(session, 'payment_incident_slots') or session.payment_incident_slots is None:
        session.payment_incident_slots = PaymentIncidentSlots()
    return session.payment_incident_slots


def clear_payment_incident_slots(session):
    """Clear payment incident slots from session"""
    if hasattr(session, 'payment_incident_slots'):
        session.payment_incident_slots = None
    if hasattr(session, 'in_payment_incident_flow'):
        session.in_payment_incident_flow = False


# Test
if __name__ == "__main__":
    print("=" * 60)
    print("PAYMENT INCIDENTS FLOW TEST")
    print("=" * 60)

    handler = PaymentIncidentsHandler()

    # Test 1: Bounced cheque
    print("\n--- TEST 1: Bounced Cheque ---")
    slots = PaymentIncidentSlots()
    messages = [
        "J'ai recu un cheque impaye de 500000 FCFA",
        "C'etait le 15/11/2024",
        "oui je confirme",
    ]
    for i, msg in enumerate(messages):
        print(f"\n[USER] {msg}")
        slots = handler.extract_slots_from_message(msg, slots)
        print(f"[SLOTS] {slots.get_filled_slots()}")
        response, is_complete = handler.get_next_response(slots, is_first_message=(i == 0))
        print(f"[RESPONSE]\n{response}")
        if is_complete:
            print("\n[COMPLETE]")
            break

    # Test 2: ATD info
    print("\n--- TEST 2: ATD Information ---")
    slots = PaymentIncidentSlots()
    msg = "Je veux des informations sur un ATD sur mon compte"
    print(f"\n[USER] {msg}")
    slots = handler.extract_slots_from_message(msg, slots)
    response, is_complete = handler.get_next_response(slots, is_first_message=True)
    print(f"[RESPONSE]\n{response}")

    # Test 3: Contestation
    print("\n--- TEST 3: Transaction Dispute ---")
    slots = PaymentIncidentSlots()
    messages = [
        "Je conteste une transaction de 150000 FCFA que je ne reconnais pas",
        "Je n'ai jamais fait cet achat, c'est peut-etre une fraude",
        "oui",
    ]
    for i, msg in enumerate(messages):
        print(f"\n[USER] {msg}")
        slots = handler.extract_slots_from_message(msg, slots)
        print(f"[SLOTS] {slots.get_filled_slots()}")
        response, is_complete = handler.get_next_response(slots, is_first_message=(i == 0))
        print(f"[RESPONSE]\n{response}")
        if is_complete:
            print("\n[COMPLETE]")
            break
