import re
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dateutil import parser as date_parser
import json

import sys
sys.path.append('..')
from config.config import *
from utils.text_normalizer import TextNormalizer


class SlotExtractor:
    """
    Extract slots from user messages using:
    1. Regex-based extraction (pre-extraction)
    2. LLM-based structured extraction (Qwen JSON)
    3. Validation and fusion
    """

    def __init__(self, llm_model=None):
        self.normalizer = TextNormalizer()
        self.llm_model = llm_model

        # Slot definitions per intent
        self.slot_schemas = self._define_slot_schemas()

    def _define_slot_schemas(self) -> Dict[str, Dict]:
        """Define expected slots for each intent"""
        return {
            "CONSULTER_SOLDE": {
                "required": [],
                "optional": ["compte_type", "compte_id"],
                "schema": {
                    "compte_type": {"type": "string", "values": ["courant", "epargne", "salaire", "carte"]},
                    "compte_id": {"type": "string"}
                }
            },
            "DISCUSSION_COMPTE": {
                "required": [],
                "optional": ["compte_type", "date_ou_periode", "operation_id", "sujet"],
                "schema": {
                    "compte_type": {"type": "string", "values": ["courant", "epargne", "salaire"]},
                    "date_ou_periode": {"type": "string"},
                    "operation_id": {"type": "string"},
                    "sujet": {"type": "string"}
                }
            },
            "FAIRE_VIREMENT": {
                "required": ["montant"],
                "optional": ["devise", "compte_source", "beneficiaire_nom", "beneficiaire_iban_ou_compte", "motif", "canal"],
                "schema": {
                    "montant": {"type": "number"},
                    "devise": {"type": "string", "values": SUPPORTED_CURRENCIES},
                    "compte_source": {"type": "string"},
                    "beneficiaire_nom": {"type": "string"},
                    "beneficiaire_iban_ou_compte": {"type": "string"},
                    "motif": {"type": "string"},
                    "canal": {"type": "string", "values": ["interne", "autre_banque", "mobile_money"]}
                }
            },
            "OBTENIR_RELEVE": {
                "required": [],
                "optional": ["compte_type", "date_debut", "date_fin", "format"],
                "schema": {
                    "compte_type": {"type": "string", "values": ["courant", "epargne", "salaire"]},
                    "date_debut": {"type": "date"},
                    "date_fin": {"type": "date"},
                    "format": {"type": "string", "values": ["PDF", "RESUME"]}
                }
            },
            "SIMULATION_CREDIT": {
                "required": ["montant_souhaite"],
                "optional": ["duree_mois", "revenus_mensuels", "charges_mensuelles", "taux_interet", "type_credit"],
                "schema": {
                    "montant_souhaite": {"type": "number"},
                    "duree_mois": {"type": "number"},
                    "revenus_mensuels": {"type": "number"},
                    "charges_mensuelles": {"type": "number"},
                    "taux_interet": {"type": "number"},
                    "type_credit": {"type": "string", "values": ["conso", "immo", "pro", "auto"]}
                }
            },
            "OTHER": {
                "required": [],
                "optional": [],
                "schema": {}
            }
        }

    def _regex_extract_amounts(self, text: str, text_norm: str) -> List[Dict]:
        """Extract amounts with context using regex"""
        amounts = []

        # Pattern for amounts with various formats
        patterns = [
            r'(\d+(?:\s?\d{3})*(?:[.,]\d+)?)\s*(xof|fcfa|euros?|€|\$|usd)?',
        ]

        for pattern in patterns:
            for match in re.finditer(pattern, text_norm, re.IGNORECASE):
                amount_str = match.group(1).replace(' ', '').replace(',', '.')
                currency = match.group(2) if match.group(2) else None

                try:
                    value = float(amount_str)

                    # Normalize currency
                    if currency:
                        currency = currency.lower()
                        if currency in ['fcfa', 'xof']:
                            currency = 'XOF'
                        elif currency in ['euro', 'euros', '€']:
                            currency = 'EUR'
                        elif currency in ['$', 'usd']:
                            currency = 'USD'
                        else:
                            currency = 'XOF'  # Default
                    else:
                        currency = 'XOF'  # Default for West Africa

                    # Get context around the match
                    start = max(0, match.start() - 20)
                    end = min(len(text_norm), match.end() + 20)
                    context = text_norm[start:end]

                    amounts.append({
                        'value': value,
                        'currency': currency,
                        'raw': match.group(0),
                        'context': context,
                        'position': match.start()
                    })
                except ValueError:
                    continue

        return amounts

    def _regex_extract_duration(self, text: str, text_norm: str) -> Optional[int]:
        """Extract duration in months"""
        # Pattern for duration
        patterns = [
            (r'(\d+)\s*mois', 1),
            (r'(\d+)\s*ans?', 12),
            (r'(\d+)\s*annees?', 12),
        ]

        for pattern, multiplier in patterns:
            match = re.search(pattern, text_norm)
            if match:
                try:
                    value = int(match.group(1))
                    return value * multiplier
                except ValueError:
                    continue

        return None

    def _regex_extract_dates(self, text: str) -> Dict[str, Optional[str]]:
        """Extract dates and periods"""
        result = {
            'date_debut': None,
            'date_fin': None,
            'periode': None
        }

        text_lower = text.lower()

        # Relative periods
        today = datetime.now()
        if 'hier' in text_lower:
            result['date_debut'] = (today - timedelta(days=1)).strftime('%Y-%m-%d')
            result['date_fin'] = result['date_debut']
            result['periode'] = 'hier'
        elif 'semaine derniere' in text_lower or 'la semaine derniere' in text_lower:
            result['date_debut'] = (today - timedelta(days=7)).strftime('%Y-%m-%d')
            result['date_fin'] = today.strftime('%Y-%m-%d')
            result['periode'] = 'semaine_derniere'
        elif 'mois dernier' in text_lower or 'le mois dernier' in text_lower:
            last_month = today.replace(day=1) - timedelta(days=1)
            result['date_debut'] = last_month.replace(day=1).strftime('%Y-%m-%d')
            result['date_fin'] = last_month.strftime('%Y-%m-%d')
            result['periode'] = 'mois_dernier'

        # Month names
        mois_fr = {
            'janvier': 1, 'fevrier': 2, 'mars': 3, 'avril': 4,
            'mai': 5, 'juin': 6, 'juillet': 7, 'aout': 8,
            'septembre': 9, 'octobre': 10, 'novembre': 11, 'decembre': 12
        }

        for mois_nom, mois_num in mois_fr.items():
            if mois_nom in text_lower:
                # Assume current year
                year = today.year
                result['date_debut'] = f'{year}-{mois_num:02d}-01'
                # Last day of month
                if mois_num == 12:
                    last_day = 31
                else:
                    next_month = datetime(year, mois_num + 1, 1)
                    last_day = (next_month - timedelta(days=1)).day
                result['date_fin'] = f'{year}-{mois_num:02d}-{last_day:02d}'
                result['periode'] = mois_nom
                break

        return result

    def _regex_pre_extract(self, text: str, text_norm: str, intent: str) -> Dict[str, Any]:
        """Pre-extract slots using regex before LLM"""
        slots = {}

        # Extract amounts
        amounts = self._regex_extract_amounts(text, text_norm)
        if amounts:
            # For virement, first amount is usually the montant
            if intent == "FAIRE_VIREMENT":
                slots['montant'] = amounts[0]['value']
                slots['devise'] = amounts[0]['currency']
            # For credit, first amount is montant_souhaite
            elif intent == "SIMULATION_CREDIT":
                slots['montant_souhaite'] = amounts[0]['value']

                # Try to identify revenus vs charges by context
                for amt in amounts[1:]:
                    if any(word in amt['context'] for word in ['revenu', 'salaire', 'gagne']):
                        slots['revenus_mensuels'] = amt['value']
                    elif any(word in amt['context'] for word in ['charge', 'loyer', 'depense']):
                        slots['charges_mensuelles'] = amt['value']

        # Extract duration
        duration = self._regex_extract_duration(text, text_norm)
        if duration and intent == "SIMULATION_CREDIT":
            slots['duree_mois'] = duration

        # Extract dates
        dates = self._regex_extract_dates(text)
        if intent == "OBTENIR_RELEVE":
            if dates['date_debut']:
                slots['date_debut'] = dates['date_debut']
            if dates['date_fin']:
                slots['date_fin'] = dates['date_fin']

        # Extract compte type
        compte_types = ['courant', 'epargne', 'salaire', 'carte']
        for ct in compte_types:
            if ct in text_norm:
                slots['compte_type'] = ct
                break

        return slots

    def _llm_extract_slots(self, text: str, intent: str, pre_extracted: Dict) -> Dict[str, Any]:
        """Use LLM to extract slots in JSON format"""
        if self.llm_model is None or intent == "OTHER":
            return pre_extracted

        schema = self.slot_schemas.get(intent, {}).get('schema', {})

        # Build JSON schema description
        schema_desc = json.dumps(schema, indent=2, ensure_ascii=False)

        prompt = f"""Tu es un extracteur de paramètres pour un assistant bancaire.

Intent: {intent}
Message client: "{text}"

Pré-extraction regex: {json.dumps(pre_extracted, ensure_ascii=False)}

Schema attendu:
{schema_desc}

Règles strictes:
1. Renvoie UNIQUEMENT un objet JSON valide
2. Si une information est absente ou incertaine, utilise null
3. Ne jamais inventer de valeurs
4. Utilise les valeurs pré-extraites si elles sont correctes
5. Les montants doivent être des nombres (pas de strings)
6. Les dates au format YYYY-MM-DD

Réponds uniquement avec le JSON, sans explication."""

        try:
            response = self._call_llm(prompt)
            # Parse JSON response
            slots_llm = json.loads(response)
            return slots_llm
        except Exception as e:
            print(f"LLM slot extraction error: {e}")
            return pre_extracted

    def _call_llm(self, prompt: str) -> str:
        """Call LLM - Ollama implementation"""
        if self.llm_model is None:
            return "{}"

        try:
            # Check if it's an Ollama client with JSON support
            if hasattr(self.llm_model, 'generate_json'):
                json_result = self.llm_model.generate_json(prompt)
                return json.dumps(json_result)
            elif hasattr(self.llm_model, 'generate'):
                response = self.llm_model.generate(prompt, temperature=0.3)
                return response
            else:
                return "{}"

        except Exception as e:
            print(f"LLM slot extraction error: {e}")
            return "{}"

    def _validate_slots(self, slots: Dict[str, Any], intent: str) -> Dict[str, Any]:
        """Validate extracted slots against business rules"""
        validated = {}
        schema = self.slot_schemas.get(intent, {}).get('schema', {})

        for key, value in slots.items():
            if value is None:
                validated[key] = {
                    'value': None,
                    'status': 'missing'
                }
                continue

            slot_def = schema.get(key, {})
            slot_type = slot_def.get('type')

            # Type validation
            if slot_type == 'number':
                try:
                    num_val = float(value)

                    # Range validation
                    if 'montant' in key:
                        if MONTANT_MIN <= num_val <= MONTANT_MAX:
                            validated[key] = {'value': num_val, 'status': 'ok'}
                        else:
                            validated[key] = {'value': num_val, 'status': 'invalid'}
                    elif 'duree' in key:
                        if DUREE_MIN_MOIS <= num_val <= DUREE_MAX_MOIS:
                            validated[key] = {'value': int(num_val), 'status': 'ok'}
                        else:
                            validated[key] = {'value': int(num_val), 'status': 'invalid'}
                    elif 'taux' in key:
                        if TAUX_MIN <= num_val <= TAUX_MAX:
                            validated[key] = {'value': num_val, 'status': 'ok'}
                        else:
                            validated[key] = {'value': num_val, 'status': 'invalid'}
                    else:
                        validated[key] = {'value': num_val, 'status': 'ok'}
                except ValueError:
                    validated[key] = {'value': value, 'status': 'invalid'}

            elif slot_type == 'string':
                allowed_values = slot_def.get('values')
                if allowed_values:
                    if value in allowed_values:
                        validated[key] = {'value': value, 'status': 'ok'}
                    else:
                        validated[key] = {'value': value, 'status': 'invalid'}
                else:
                    validated[key] = {'value': value, 'status': 'ok'}

            elif slot_type == 'date':
                # Validate date format
                try:
                    date_parser.parse(value)
                    validated[key] = {'value': value, 'status': 'ok'}
                except:
                    validated[key] = {'value': value, 'status': 'invalid'}

            else:
                validated[key] = {'value': value, 'status': 'ok'}

        # Check required slots
        required = self.slot_schemas.get(intent, {}).get('required', [])
        for req_slot in required:
            if req_slot not in validated or validated[req_slot]['status'] != 'ok':
                if req_slot not in validated:
                    validated[req_slot] = {'value': None, 'status': 'missing'}

        return validated

    def extract(self, text: str, intent: str) -> Dict:
        """
        Main extraction method

        Returns:
            {
                'slots': dict of validated slots,
                'missing_required': list of missing required slots,
                'invalid_slots': list of invalid slots,
                'ready_for_action': bool
            }
        """
        text_norm = self.normalizer.normalize(text)

        # Step 1: Regex pre-extraction
        pre_extracted = self._regex_pre_extract(text, text_norm, intent)

        # Step 2: LLM extraction
        llm_extracted = self._llm_extract_slots(text, intent, pre_extracted)

        # Step 3: Merge (LLM takes precedence if both exist)
        merged = {**pre_extracted, **llm_extracted}

        # Step 4: Validate
        validated = self._validate_slots(merged, intent)

        # Step 5: Analyze completeness
        required = self.slot_schemas.get(intent, {}).get('required', [])
        missing_required = [
            slot for slot in required
            if slot not in validated or validated[slot]['status'] == 'missing'
        ]

        invalid_slots = [
            slot for slot, data in validated.items()
            if data['status'] == 'invalid'
        ]

        ready_for_action = len(missing_required) == 0 and len(invalid_slots) == 0

        return {
            'slots': validated,
            'missing_required': missing_required,
            'invalid_slots': invalid_slots,
            'ready_for_action': ready_for_action,
            'pre_extracted': pre_extracted,
            'llm_extracted': llm_extracted
        }
