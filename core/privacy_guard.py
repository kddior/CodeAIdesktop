# core/privacy_guard.py

import re
from typing import Dict, List, Tuple
from enum import Enum


class DataClassification(Enum):
    """Data sensitivity levels"""
    CRITICAL = "critical"      # Never leave secure environment
    INTERNAL = "internal"      # Internal use only
    PUBLIC = "public"          # Published by AFG/DBS
    EXTERNAL = "external"      # Public domain


class PrivacyGuard:
    """
    Ensures sensitive data never leaves secure boundaries

    Usage:
        guard = PrivacyGuard()

        # Before web search
        sanitized = guard.sanitize_for_web(query, slots)

        # Check if intent can use web
        decision = guard.can_use_web_search(intent_name, message, slots)
    """

    # Sensitive patterns to detect and redact
    SENSITIVE_PATTERNS = [
        # Financial identifiers
        (r'\b[A-Z]{2}\d{2}[A-Z0-9]{10,30}\b', 'IBAN'),
        (r'\b[A-Z]{6}[A-Z0-9]{5}\b', 'BIC'),
        (r'\b\d{16}\b', 'CARD'),
        (r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b', 'CARD'),

        # Personal identifiers
        (r'\b\d{3}[-.\s]?\d{2}[-.\s]?\d{4}\b', 'SSN'),
        (r'\b[A-Z]{2}\d{6}\b', 'PASSPORT'),
        (r'\b\d{10,15}\b', 'PHONE'),

        # Account references
        (r'\bcompte[\s#-]?\d{6,}\b', 'ACCOUNT'),
        (r'\bclient[\s#-]?\d{6,}\b', 'CLIENT_ID'),

        # Email addresses (customer)
        (r'\b[a-zA-Z0-9._%+-]+@(?!afg\.com|dbs\.com)[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b', 'EMAIL'),
    ]

    # Code secrets patterns (for CODING mode)
    CODE_SENSITIVE_PATTERNS = [
        # API Keys and Secrets
        (r'api[_-]?key\s*[:=]\s*["\']([^"\']{20,})["\']', 'API_KEY'),
        (r'secret[_-]?key\s*[:=]\s*["\']([^"\']{20,})["\']', 'SECRET'),
        (r'private[_-]?key\s*[:=]\s*["\']([^"\']{20,})["\']', 'PRIVATE_KEY'),
        (r'access[_-]?token\s*[:=]\s*["\']([^"\']{20,})["\']', 'ACCESS_TOKEN'),
        (r'auth[_-]?token\s*[:=]\s*["\']([^"\']{20,})["\']', 'AUTH_TOKEN'),

        # Database credentials
        (r'password\s*[:=]\s*["\']([^"\']+)["\']', 'PASSWORD'),
        (r'db[_-]?password\s*[:=]\s*["\']([^"\']+)["\']', 'DB_PASSWORD'),
        (r'database[_-]?url\s*[:=]\s*["\']([^"\']+)["\']', 'DATABASE_URL'),
        (r'connection[_-]?string\s*[:=]\s*["\']([^"\']+)["\']', 'CONNECTION_STRING'),

        # Cloud provider credentials
        (r'AWS_SECRET_ACCESS_KEY\s*[:=]\s*["\']([^"\']+)["\']', 'AWS_SECRET'),
        (r'GOOGLE_APPLICATION_CREDENTIALS\s*[:=]\s*["\']([^"\']+)["\']', 'GOOGLE_CREDS'),
        (r'AZURE_CLIENT_SECRET\s*[:=]\s*["\']([^"\']+)["\']', 'AZURE_SECRET'),

        # OAuth and JWT
        (r'client[_-]?secret\s*[:=]\s*["\']([^"\']{20,})["\']', 'CLIENT_SECRET'),
        (r'jwt[_-]?secret\s*[:=]\s*["\']([^"\']{20,})["\']', 'JWT_SECRET'),

        # IP addresses (internal)
        (r'\b(?:10|192\.168|172\.(?:1[6-9]|2[0-9]|3[01]))\.\d{1,3}\.\d{1,3}\b', 'PRIVATE_IP'),

        # Encryption keys
        (r'encryption[_-]?key\s*[:=]\s*["\']([^"\']{20,})["\']', 'ENCRYPTION_KEY'),
        (r'cipher[_-]?key\s*[:=]\s*["\']([^"\']{20,})["\']', 'CIPHER_KEY'),

        # SSH keys (basic detection)
        (r'-----BEGIN (?:RSA |DSA |EC )?PRIVATE KEY-----', 'SSH_PRIVATE_KEY'),

        # Generic secrets in .env format
        (r'(?:^|\n)[A-Z_]+_(?:KEY|SECRET|TOKEN|PASSWORD)\s*=\s*["\']?([^"\'\n]+)', 'ENV_SECRET'),
    ]

    # Intents that must NEVER use web search
    NEVER_WEB_INTENTS = [
        'CONSULTER_SOLDE',
        'FAIRE_VIREMENT',
        'DISCUSSION_COMPTE',
        'OBTENIR_RELEVE',
        'SIMULATION_CREDIT',
    ]

    # Topics requiring user confirmation before web search
    REQUIRE_CONFIRMATION_FOR_WEB = [
        'plainte',
        'complaint',
        'litige',
        'dispute',
        'fraude',
        'fraud',
        'enquête',
        'investigation',
    ]

    # Sensitive slot names that indicate critical data
    SENSITIVE_SLOTS = [
        'account_number',
        'iban',
        'bic',
        'card_number',
        'customer_name',
        'beneficiary_name',
        'customer_email',
        'phone_number',
        'address',
        'date_of_birth',
    ]

    def sanitize_for_web(self, query: str, slots: Dict) -> Tuple[str, Dict]:
        """
        Clean query before sending to Google

        Args:
            query: Original user query
            slots: Extracted slots

        Returns:
            (sanitized_query, sanitization_report)
        """
        sanitized = query
        report = {
            'original_query': query,
            'sanitization_applied': False,
            'patterns_matched': [],
            'slots_anonymized': [],
            'safe_for_web': True
        }

        # Step 1: Remove sensitive patterns
        for pattern, name in self.SENSITIVE_PATTERNS:
            matches = re.findall(pattern, sanitized, re.IGNORECASE)
            if matches:
                sanitized = re.sub(pattern, '[REDACTED]', sanitized, flags=re.IGNORECASE)
                report['patterns_matched'].append({
                    'type': name,
                    'matches': len(matches)
                })
                report['sanitization_applied'] = True

        # Step 2: Anonymize names from slots
        if 'customer_name' in slots:
            name = slots['customer_name']
            if name and name in sanitized:
                sanitized = sanitized.replace(name, 'un client')
                report['slots_anonymized'].append('customer_name')
                report['sanitization_applied'] = True

        if 'beneficiary_name' in slots:
            name = slots['beneficiary_name']
            if name and name in sanitized:
                sanitized = sanitized.replace(name, 'un bénéficiaire')
                report['slots_anonymized'].append('beneficiary_name')
                report['sanitization_applied'] = True

        # Step 3: Generalize large amounts
        if 'amount' in slots or 'montant' in slots:
            amount = slots.get('amount') or slots.get('montant')
            if amount and isinstance(amount, (int, float)) and amount > 1_000_000:
                sanitized = re.sub(
                    r'\b' + str(int(amount)) + r'\b',
                    'un montant important',
                    sanitized
                )
                report['slots_anonymized'].append('amount')
                report['sanitization_applied'] = True

        # Step 4: Check if any critical data remains
        report['sanitized_query'] = sanitized
        report['safe_for_web'] = self._is_safe_for_web(sanitized, slots)

        return sanitized, report

    def _is_safe_for_web(self, query: str, slots: Dict) -> bool:
        """Check if query is safe to send to web"""

        # Check if any sensitive patterns still present
        for pattern, _ in self.SENSITIVE_PATTERNS:
            if re.search(pattern, query, re.IGNORECASE):
                return False

        # Check if any sensitive slots still in query
        for slot_name in self.SENSITIVE_SLOTS:
            if slot_name in slots:
                slot_value = str(slots[slot_name])
                if slot_value and slot_value.lower() in query.lower():
                    return False

        return True

    def can_use_web_search(
        self,
        intent_name: str,
        message: str,
        slots: Dict
    ) -> Dict:
        """
        Decide if web search is allowed for this request

        Returns:
        {
            'allowed': bool,
            'reason': str,
            'action': 'proceed' | 'block' | 'ask_user',
            'sanitized_query': str (if allowed)
        }
        """

        # Check 1: Intent blacklist
        if intent_name in self.NEVER_WEB_INTENTS:
            return {
                'allowed': False,
                'reason': f'Intent {intent_name} must not use web search (accesses critical data)',
                'action': 'block',
                'sanitized_query': None
            }

        # Check 2: Sensitive data in message/slots
        _, sanitization_report = self.sanitize_for_web(message, slots)

        if not sanitization_report['safe_for_web']:
            return {
                'allowed': False,
                'reason': 'Message contains sensitive data that cannot be sanitized',
                'action': 'block',
                'sanitized_query': None,
                'details': sanitization_report
            }

        # Check 3: Topics requiring confirmation
        message_lower = message.lower()
        for sensitive_topic in self.REQUIRE_CONFIRMATION_FOR_WEB:
            if sensitive_topic in message_lower:
                return {
                    'allowed': True,
                    'reason': f'Sensitive topic detected: {sensitive_topic}',
                    'action': 'ask_user',  # Ask: "Voulez-vous que je cherche sur le web ?"
                    'sanitized_query': sanitization_report['sanitized_query']
                }

        # Check 4: Check for sensitive slots
        sensitive_slot_found = any(
            slot in slots for slot in self.SENSITIVE_SLOTS
        )

        if sensitive_slot_found:
            # Try sanitization
            if sanitization_report['sanitization_applied']:
                return {
                    'allowed': True,
                    'reason': 'Sensitive data sanitized successfully',
                    'action': 'proceed',
                    'sanitized_query': sanitization_report['sanitized_query'],
                    'sanitization_report': sanitization_report
                }
            else:
                return {
                    'allowed': False,
                    'reason': 'Sensitive slots present and cannot be sanitized',
                    'action': 'block',
                    'sanitized_query': None
                }

        # Default: allow
        return {
            'allowed': True,
            'reason': 'No privacy concerns detected',
            'action': 'proceed',
            'sanitized_query': sanitization_report.get('sanitized_query', message)
        }

    def contains_sensitive_data(self, text: str, slots: Dict = None) -> bool:
        """Quick check if text contains sensitive data"""

        if slots is None:
            slots = {}

        # Check patterns
        for pattern, _ in self.SENSITIVE_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return True

        # Check sensitive slots
        for slot_name in self.SENSITIVE_SLOTS:
            if slot_name in slots:
                return True

        return False

    def sanitize_code_for_web(self, code_content: str, file_path: str = None) -> Tuple[str, Dict]:
        """
        Sanitize code content before sending to web (for CODE_ASSIST intent)

        Args:
            code_content: Source code content
            file_path: Optional file path (for context)

        Returns:
            (sanitized_code, sanitization_report)
        """
        sanitized = code_content
        report = {
            'original_length': len(code_content),
            'sanitization_applied': False,
            'secrets_found': [],
            'safe_for_web': True,
            'file_path': file_path
        }

        # Step 1: Remove code secrets
        for pattern, secret_type in self.CODE_SENSITIVE_PATTERNS:
            matches = re.findall(pattern, sanitized, re.IGNORECASE)
            if matches:
                sanitized = re.sub(pattern, f'{secret_type.lower()}="[REDACTED]"', sanitized, flags=re.IGNORECASE)
                report['secrets_found'].append({
                    'type': secret_type,
                    'count': len(matches)
                })
                report['sanitization_applied'] = True

        # Step 2: Check if sanitization was successful
        # Re-check for any remaining secrets
        for pattern, _ in self.CODE_SENSITIVE_PATTERNS:
            if re.search(pattern, sanitized, re.IGNORECASE):
                report['safe_for_web'] = False
                break

        report['sanitized_length'] = len(sanitized)
        report['reduction_percent'] = ((len(code_content) - len(sanitized)) / len(code_content) * 100) if code_content else 0

        return sanitized, report

    def contains_code_secrets(self, code_content: str) -> bool:
        """Quick check if code contains secrets"""
        for pattern, _ in self.CODE_SENSITIVE_PATTERNS:
            if re.search(pattern, code_content, re.IGNORECASE):
                return True
        return False

    def classify_data(self, intent_name: str, slots: Dict) -> DataClassification:
        """
        Classify data sensitivity level for an intent

        Returns: DataClassification enum
        """

        # CRITICAL: Transactional intents accessing account data
        if intent_name in self.NEVER_WEB_INTENTS:
            return DataClassification.CRITICAL

        # CRITICAL: Any intent with sensitive slots
        if any(slot in slots for slot in self.SENSITIVE_SLOTS):
            return DataClassification.CRITICAL

        # INTERNAL: Policy/procedure questions AND code assistance
        if intent_name in ['QUESTION_POLICY', 'CODE_ASSIST']:
            return DataClassification.INTERNAL

        # EXTERNAL: Web search intents
        if intent_name in ['QUESTION_WEB', 'EXPLAIN_TOPIC']:
            return DataClassification.EXTERNAL

        # Default: PUBLIC
        return DataClassification.PUBLIC


# Test function
if __name__ == "__main__":
    print("=" * 60)
    print("Privacy Guard - Test Suite")
    print("=" * 60)

    guard = PrivacyGuard()

    # Test 1: IBAN redaction
    print("\n[Test 1] IBAN Redaction")
    query = "cherche le taux pour IBAN FR7612345678901234567890"
    sanitized, report = guard.sanitize_for_web(query, {})
    print(f"Original:  {query}")
    print(f"Sanitized: {sanitized}")
    print(f"Safe:      {report['safe_for_web']}")
    assert "FR76" not in sanitized
    assert "[REDACTED]" in sanitized
    print("✅ PASS")

    # Test 2: Name anonymization
    print("\n[Test 2] Name Anonymization")
    query = "virement pour Jean Dupont"
    sanitized, report = guard.sanitize_for_web(query, {'beneficiary_name': 'Jean Dupont'})
    print(f"Original:  {query}")
    print(f"Sanitized: {sanitized}")
    assert "Jean Dupont" not in sanitized
    assert "bénéficiaire" in sanitized
    print("✅ PASS")

    # Test 3: Critical intent blocks web
    print("\n[Test 3] Critical Intent Blocks Web")
    decision = guard.can_use_web_search("CONSULTER_SOLDE", "mon solde", {})
    print(f"Intent:    CONSULTER_SOLDE")
    print(f"Allowed:   {decision['allowed']}")
    print(f"Action:    {decision['action']}")
    print(f"Reason:    {decision['reason']}")
    assert decision['allowed'] == False
    assert decision['action'] == 'block'
    print("✅ PASS")

    # Test 4: Safe query passes
    print("\n[Test 4] Safe Query Passes")
    query = "taux de change euro fcfa"
    sanitized, report = guard.sanitize_for_web(query, {})
    print(f"Original:  {query}")
    print(f"Sanitized: {sanitized}")
    print(f"Safe:      {report['safe_for_web']}")
    assert sanitized == query
    assert report['safe_for_web'] == True
    print("✅ PASS")

    # Test 5: Data classification
    print("\n[Test 5] Data Classification")
    classifications = [
        ('CONSULTER_SOLDE', {}, DataClassification.CRITICAL),
        ('QUESTION_POLICY', {}, DataClassification.INTERNAL),
        ('QUESTION_WEB', {}, DataClassification.EXTERNAL),
    ]

    for intent, slots, expected in classifications:
        result = guard.classify_data(intent, slots)
        print(f"{intent:20} → {result.value:10} (expected: {expected.value})")
        assert result == expected

    print("✅ PASS")

    print("✅ PASS")

    # Test 6: Code secrets detection
    print("\n[Test 6] Code Secrets Detection")
    code_with_secrets = '''
    API_KEY = "FAKE_TEST_KEY_EXAMPLE_123"
    db_password = "MySecretP@ssw0rd123"
    connection_string = "mongodb://user:pass@localhost:27017/db"
    '''

    sanitized_code, code_report = guard.sanitize_code_for_web(code_with_secrets)
    print(f"Secrets found: {len(code_report['secrets_found'])}")
    print(f"Sanitized: {code_report['sanitization_applied']}")
    assert code_report['sanitization_applied'] == True
    assert len(code_report['secrets_found']) > 0
    assert "FAKE_TEST_KEY" not in sanitized_code
    assert "[REDACTED]" in sanitized_code
    print("✅ PASS")

    # Test 7: Code secrets quick check
    print("\n[Test 7] Code Secrets Quick Check")
    assert guard.contains_code_secrets(code_with_secrets) == True
    assert guard.contains_code_secrets("def hello(): print('world')") == False
    print("✅ PASS")

    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED (including CODE protection)")
    print("=" * 60)
