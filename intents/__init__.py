# intents/__init__.py
# -*- coding: utf-8 -*-

import sys
import io
from pathlib import Path
import importlib
import inspect
from typing import Dict, List, Optional
from .base import BaseIntent, IntentType, IntentResult, ExecutionContext

# Fix Windows console encoding
if sys.platform == 'win32' and hasattr(sys.stdout, 'buffer'):
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    except:
        pass


class IntentRegistry:
    """
    Auto-discovers and registers all intent plugins

    Scans the intents/ directory and loads all classes that inherit from BaseIntent.
    This allows adding new intents by simply creating a new file - no core changes needed.
    """

    def __init__(self):
        self.intents: Dict[str, BaseIntent] = {}
        self._discover_intents()

    def _discover_intents(self):
        """Scan intents/ directory and load all intent classes"""
        intents_dir = Path(__file__).parent
        loaded_count = 0

        # Find all .py files (except __init__ and base)
        for py_file in intents_dir.rglob("*.py"):
            if py_file.name in ["__init__.py", "base.py"]:
                continue

            try:
                # Convert file path to module path
                # e.g., intents/banking/consulter_solde.py -> intents.banking.consulter_solde
                relative_path = py_file.relative_to(intents_dir.parent)
                module_path = str(relative_path).replace("\\", ".").replace("/", ".")[:-3]

                # Import module
                module = importlib.import_module(module_path)

                # Find Intent classes (subclasses of BaseIntent)
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)

                    # Check if it's a class that inherits from BaseIntent
                    if (inspect.isclass(attr) and
                        issubclass(attr, BaseIntent) and
                        attr != BaseIntent and
                        attr.name is not None):  # Must have name defined

                        # Instantiate intent
                        intent = attr()

                        # Register by name
                        self.intents[intent.name] = intent
                        loaded_count += 1

                        try:
                            print(f"[OK] Loaded intent: {intent.name:25} | {intent.category:12} | {len(intent.examples):3} examples | type={intent.intent_type.value}")
                        except (ValueError, OSError):
                            pass  # Ignore stdout errors in Streamlit

            except Exception as e:
                try:
                    print(f"[WARN] Failed to load {py_file.name}: {e}")
                except (ValueError, OSError):
                    pass  # Ignore stdout errors in Streamlit

        try:
            print(f"\n[INFO] Total intents loaded: {loaded_count}")
        except (ValueError, OSError):
            pass  # Ignore stdout errors in Streamlit

    # ===== PUBLIC API =====

    def get_all_intents(self) -> List[str]:
        """Get list of all intent names"""
        return list(self.intents.keys())

    def get_intent(self, intent_name: str) -> Optional[BaseIntent]:
        """Get intent instance by name"""
        return self.intents.get(intent_name)

    def get_examples(self) -> Dict[str, List[str]]:
        """Get all examples for all intents"""
        return {name: intent.examples for name, intent in self.intents.items()}

    def get_keywords(self) -> Dict[str, List[str]]:
        """Get all keyword rules"""
        return {name: intent.keywords for name, intent in self.intents.items()}

    def get_slot_schema(self, intent_name: str) -> Dict:
        """Get slot schema for an intent"""
        intent = self.intents.get(intent_name)
        return intent.slots if intent else {}

    def get_intent_type(self, intent_name: str) -> Optional[IntentType]:
        """Get intent type for routing"""
        intent = self.intents.get(intent_name)
        return intent.intent_type if intent else None

    def get_tools(self, intent_name: str) -> List[str]:
        """Get tools required by intent"""
        intent = self.intents.get(intent_name)
        return intent.tools if intent else []

    def execute(self, intent_name: str, slots: Dict, context: ExecutionContext) -> IntentResult:
        """
        Execute an intent

        Args:
            intent_name: Name of intent to execute
            slots: Extracted slots
            context: Execution context with tools

        Returns:
            IntentResult
        """
        intent = self.intents.get(intent_name)
        if not intent:
            return IntentResult(
                success=False,
                data={},
                error=f"Intent '{intent_name}' not found"
            )

        try:
            # Pre-execution hook
            slots = intent.pre_execute(slots, context)

            # Execute
            result = intent.execute(slots, context)

            # Post-execution hook
            result = intent.post_execute(result, slots, context)

            return result

        except Exception as e:
            return IntentResult(
                success=False,
                data={},
                error=f"Execution failed: {str(e)}"
            )

    def format_response(self, intent_name: str, result: IntentResult, slots: Dict) -> str:
        """Format response for an intent"""
        intent = self.intents.get(intent_name)
        if not intent:
            return f"❌ Intent '{intent_name}' not found"

        try:
            return intent.format_response(result, slots)
        except Exception as e:
            return f"❌ Failed to format response: {str(e)}"

    def route(self, intent_name: str, message: str, slots: Dict) -> IntentType:
        """
        Get routing strategy for an intent

        Args:
            intent_name: Name of intent
            message: User message
            slots: Extracted slots

        Returns:
            IntentType for routing
        """
        intent = self.intents.get(intent_name)
        if not intent:
            return IntentType.TRANSACTIONAL

        return intent.route(message, slots)

    # ===== UTILITY METHODS =====

    def get_intents_by_category(self, category: str) -> List[str]:
        """Get all intents in a category"""
        return [
            name for name, intent in self.intents.items()
            if intent.category == category
        ]

    def get_intents_by_type(self, intent_type: IntentType) -> List[str]:
        """Get all intents of a specific type"""
        return [
            name for name, intent in self.intents.items()
            if intent.intent_type == intent_type
        ]

    def get_stats(self) -> Dict:
        """Get registry statistics"""
        categories = {}
        types = {}

        for intent in self.intents.values():
            # Count by category
            categories[intent.category] = categories.get(intent.category, 0) + 1

            # Count by type
            type_name = intent.intent_type.value
            types[type_name] = types.get(type_name, 0) + 1

        return {
            'total_intents': len(self.intents),
            'categories': categories,
            'types': types,
            'total_examples': sum(len(i.examples) for i in self.intents.values())
        }

    def print_stats(self):
        """Print registry statistics"""
        stats = self.get_stats()

        print("\n" + "="*60)
        print("📊 INTENT REGISTRY STATISTICS")
        print("="*60)
        print(f"Total Intents: {stats['total_intents']}")
        print(f"Total Examples: {stats['total_examples']}")

        print("\nBy Category:")
        for cat, count in sorted(stats['categories'].items()):
            print(f"  {cat:15} : {count:2} intents")

        print("\nBy Type:")
        for typ, count in sorted(stats['types'].items()):
            print(f"  {typ:25} : {count:2} intents")
        print("="*60 + "\n")


# Global registry instance
# This is auto-populated when the module is imported
registry = IntentRegistry()


# Export public API
__all__ = [
    'BaseIntent',
    'IntentType',
    'IntentResult',
    'ExecutionContext',
    'IntentRegistry',
    'registry'
]
