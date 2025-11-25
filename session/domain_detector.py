# session/domain_detector.py

from typing import Optional, Dict, List
from .unified_session import DomainType


class DomainDetector:
    """
    Detects which domain/mode the user is currently in based on:
    1. Explicit commands (e.g., "mode banking", "switch to coding")
    2. Intent classification
    3. Keywords in message
    4. Context (stay in current mode if ambiguous)
    """

    def __init__(self):
        # Map intent names to domains
        self.intent_to_domain = {
            # Banking intents
            'CONSULTER_SOLDE': DomainType.BANKING,
            'FAIRE_VIREMENT': DomainType.BANKING,
            'OBTENIR_RELEVE': DomainType.BANKING,
            'SIMULATION_CREDIT': DomainType.BANKING,
            'DISCUSSION_COMPTE': DomainType.BANKING,
            'QUESTION_POLICY': DomainType.BANKING,

            # Coding intents
            'CODE_ASSIST': DomainType.CODING,
            'EXPLAIN_CODE': DomainType.CODING,
            'DEBUG_CODE': DomainType.CODING,
            'REFACTOR_CODE': DomainType.CODING,

            # Personal intents (future)
            'READ_EMAIL': DomainType.PERSONAL,
            'WRITE_EMAIL': DomainType.PERSONAL,
            'CHECK_CALENDAR': DomainType.PERSONAL,
            'CREATE_NOTE': DomainType.PERSONAL,

            # General
            'QUESTION_WEB': DomainType.GENERAL,
            'EXPLAIN_TOPIC': DomainType.GENERAL,
            'OTHER': DomainType.GENERAL,
        }

        # Keywords for each domain
        self.domain_keywords = {
            DomainType.BANKING: [
                'solde', 'virement', 'compte', 'crédit', 'fcfa', 'xof',
                'balance', 'transfer', 'account', 'bank', 'transaction',
                'releve', 'historique', 'carte', 'iban', 'rib'
            ],
            DomainType.CODING: [
                'code', 'fichier', 'fonction', 'classe', 'python', 'dart',
                'debug', 'bug', 'error', 'function', 'class', 'file',
                'repository', 'repo', 'git', 'commit', 'branch',
                'javascript', 'typescript', 'java', 'csharp', 'go',
                'implementation', 'refactor', 'test', 'api', 'endpoint'
            ],
            DomainType.PERSONAL: [
                'email', 'mail', 'calendrier', 'calendar', 'rendez-vous',
                'meeting', 'appointment', 'note', 'reminder', 'task',
                'todo', 'agenda', 'schedule'
            ],
        }

    def detect_domain(
        self,
        message: str,
        intent_name: str,
        current_domain: Optional[DomainType],
        session_history: List[Dict]
    ) -> tuple[DomainType, str]:
        """
        Detect domain with priority:
        1. Explicit commands (highest priority)
        2. Intent classification
        3. Keywords in message
        4. Context (stay in current domain)
        5. Default to GENERAL

        Returns:
            (DomainType, reason: str)
        """

        # 1. Check for explicit mode switching
        explicit = self._check_explicit_switch(message)
        if explicit:
            return explicit, "explicit command"

        # 2. Use intent classification
        domain_from_intent = self.intent_to_domain.get(intent_name)
        if domain_from_intent:
            return domain_from_intent, f"intent: {intent_name}"

        # 3. Check keywords
        domain_from_keywords = self._domain_from_keywords(message)
        if domain_from_keywords:
            return domain_from_keywords, "keywords detected"

        # 4. Stay in current domain if set
        if current_domain:
            return current_domain, "context continuation"

        # 5. Default
        return DomainType.GENERAL, "default"

    def _check_explicit_switch(self, message: str) -> Optional[DomainType]:
        """Check for explicit mode switching commands"""
        m = message.lower()

        # Banking mode switches
        if any(kw in m for kw in ['mode banking', 'mode banque', 'retour au banking',
                                    'banking mode', 'switch to banking', 'banque mode']):
            return DomainType.BANKING

        # Coding mode switches
        if any(kw in m for kw in ['mode coding', 'mode code', 'retour au code',
                                    'coding mode', 'switch to coding', 'dev mode',
                                    'mode développement', 'mode dev']):
            return DomainType.CODING

        # Personal mode switches
        if any(kw in m for kw in ['mode personnel', 'mode perso', 'personal mode',
                                    'switch to personal', 'retour au perso']):
            return DomainType.PERSONAL

        # General mode
        if any(kw in m for kw in ['mode general', 'mode général', 'general mode']):
            return DomainType.GENERAL

        return None

    def _domain_from_keywords(self, message: str) -> Optional[DomainType]:
        """Detect domain from keywords in message"""
        m = message.lower()

        # Count keyword matches for each domain
        scores = {}
        for domain, keywords in self.domain_keywords.items():
            score = sum(1 for kw in keywords if kw in m)
            if score > 0:
                scores[domain] = score

        # Return domain with highest score
        if scores:
            return max(scores, key=scores.get)

        return None

    def get_mode_display(self, domain: Optional[DomainType]) -> str:
        """Get emoji display for current mode"""
        if not domain:
            return "💬 GENERAL"

        mode_emoji = {
            DomainType.BANKING: "🏦 BANKING",
            DomainType.CODING: "💻 CODING",
            DomainType.PERSONAL: "📧 PERSONAL",
            DomainType.GENERAL: "💬 GENERAL",
        }

        return mode_emoji.get(domain, "💬 GENERAL")
