import re
from unidecode import unidecode

class TextNormalizer:
    """Normalize text for better intent detection and slot extraction"""

    @staticmethod
    def normalize(text: str) -> str:
        """
        Normalize text:
        - Lowercase
        - Remove accents
        - Normalize numbers
        - Remove extra punctuation
        - Remove extra spaces
        """
        if not text:
            return ""

        # Lowercase
        text = text.lower()

        # Remove accents
        text = unidecode(text)

        # Normalize common number formats
        # "50 000", "50.000", "50k" -> "50000"
        text = re.sub(r'(\d+)\s+(\d{3})', r'\1\2', text)  # "50 000" -> "50000"
        text = re.sub(r'(\d+)\.(\d{3})', r'\1\2', text)   # "50.000" -> "50000"
        text = re.sub(r'(\d+)k', lambda m: str(int(m.group(1)) * 1000), text, flags=re.IGNORECASE)
        text = re.sub(r'(\d+)m', lambda m: str(int(m.group(1)) * 1000000), text, flags=re.IGNORECASE)

        # Normalize common banking terms
        replacements = {
            'fcfa': 'xof',
            'compte courant': 'courant',
            'compte epargne': 'epargne',
            'compte salaire': 'salaire',
        }

        for old, new in replacements.items():
            text = text.replace(old, new)

        # Remove extra punctuation (keep only useful ones)
        text = re.sub(r'[^\w\s€$%,.-]', ' ', text)

        # Remove extra spaces
        text = re.sub(r'\s+', ' ', text).strip()

        return text

    @staticmethod
    def extract_numbers(text: str) -> list:
        """Extract all numbers from text with their context"""
        pattern = r'(\d+(?:[.,]\d+)?)\s*(%|€|\$|xof|fcfa|mois|ans)?'
        matches = re.finditer(pattern, text.lower())

        numbers = []
        for match in matches:
            value_str = match.group(1).replace(',', '.')
            unit = match.group(2) or ""

            try:
                value = float(value_str)
                numbers.append({
                    'value': value,
                    'raw': match.group(0),
                    'unit': unit,
                    'position': match.start()
                })
            except ValueError:
                continue

        return numbers
