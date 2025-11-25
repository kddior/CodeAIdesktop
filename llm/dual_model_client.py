# -*- coding: utf-8 -*-
"""
Dual-Model Ollama Client with Automatic Routing
Manages both DeepSeek-R1-Distill-14B (fast) and Qwen 2.5 32B (quality)
"""

from typing import Dict, Any, Optional
from .ollama_client import OllamaClient
from .model_router import ModelRouter


class DualModelClient:
    """
    Manages two Ollama models with automatic intelligent routing:
    - DeepSeek-R1-Distill-14B: Fast banking queries, calculations
    - Qwen 2.5 32B: Complex analysis, GPT-4 level reasoning

    Note: Only one model is loaded in VRAM at a time due to memory constraints.
    """

    def __init__(
        self,
        fast_model: str = "deepseek-r1:14b",
        quality_model: str = "qwen2.5:32b-instruct",
        timeout: int = 60
    ):
        """
        Initialize dual-model client.

        Args:
            fast_model: Model for fast queries (DeepSeek)
            quality_model: Model for quality queries (Qwen 32B)
            timeout: Request timeout in seconds
        """
        self.fast_model_name = fast_model
        self.quality_model_name = quality_model
        self.timeout = timeout

        # Initialize router
        self.router = ModelRouter(fast_model=fast_model, quality_model=quality_model)

        # Current loaded model (only one in VRAM at a time)
        self.current_model_name = None
        self.current_client = None

        # Statistics
        self.stats = {
            'fast_model_calls': 0,
            'quality_model_calls': 0,
            'model_switches': 0
        }

        print(f"[INFO] Dual-Model Client initialized")
        print(f"  Fast Model: {fast_model} (12-14 GB VRAM)")
        print(f"  Quality Model: {quality_model} (22-23 GB VRAM)")
        print(f"  Strategy: Automatic routing based on query complexity")

    def _load_model(self, model_name: str):
        """
        Load a specific model into VRAM.

        Note: This will unload the current model if different.
        """
        if self.current_model_name == model_name and self.current_client:
            # Model already loaded
            return

        # Model switch required
        if self.current_model_name:
            print(f"[SWITCH] Switching from {self.current_model_name} to {model_name}")
            self.stats['model_switches'] += 1
        else:
            print(f"[LOAD] Loading {model_name}")

        # Initialize new client (this will load the model)
        self.current_client = OllamaClient(model_name=model_name, timeout=self.timeout)
        self.current_model_name = model_name

    def generate(
        self,
        prompt: str,
        intent: str = "UNKNOWN",
        confidence: float = 0.5,
        mode: str = "general",
        system: Optional[str] = None,
        temperature: float = 0.7,
        force_model: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate response with automatic model routing.

        Args:
            prompt: User prompt
            intent: Detected intent
            confidence: Intent confidence
            mode: Conversation mode
            system: Optional system message
            temperature: Sampling temperature
            force_model: Force specific model (skip routing)

        Returns:
            {
                'response': str,
                'model_used': str,
                'routing_reason': str,
                'strategy': str
            }
        """
        # Determine which model to use
        if force_model:
            model_to_use = force_model
            routing_info = {
                'model': force_model,
                'reason': 'Forced by caller',
                'strategy': 'forced'
            }
        else:
            routing_info = self.router.route(
                intent=intent,
                query=prompt,
                confidence=confidence,
                mode=mode
            )
            model_to_use = routing_info['model']

        # Update statistics
        if model_to_use == self.fast_model_name:
            self.stats['fast_model_calls'] += 1
        else:
            self.stats['quality_model_calls'] += 1

        # Load model if needed
        self._load_model(model_to_use)

        # Generate response
        response_text = self.current_client.generate(
            prompt=prompt,
            system=system,
            temperature=temperature
        )

        # Get model info
        model_info = self.router.get_model_info(model_to_use)

        return {
            'response': response_text,
            'model_used': model_to_use,
            'model_name': model_info['name'],
            'routing_reason': routing_info['reason'],
            'routing_strategy': routing_info['strategy'],
            'model_info': model_info
        }

    def generate_json(
        self,
        prompt: str,
        intent: str = "UNKNOWN",
        confidence: float = 0.5,
        mode: str = "general",
        system: Optional[str] = None,
        force_model: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate JSON response with automatic model routing.

        Args:
            prompt: User prompt
            intent: Detected intent
            confidence: Intent confidence
            mode: Conversation mode
            system: Optional system message
            force_model: Force specific model (skip routing)

        Returns:
            {
                'data': dict,  # Parsed JSON
                'model_used': str,
                'routing_reason': str
            }
        """
        # Determine which model to use
        if force_model:
            model_to_use = force_model
            routing_info = {
                'model': force_model,
                'reason': 'Forced by caller',
                'strategy': 'forced'
            }
        else:
            routing_info = self.router.route(
                intent=intent,
                query=prompt,
                confidence=confidence,
                mode=mode
            )
            model_to_use = routing_info['model']

        # Update statistics
        if model_to_use == self.fast_model_name:
            self.stats['fast_model_calls'] += 1
        else:
            self.stats['quality_model_calls'] += 1

        # Load model if needed
        self._load_model(model_to_use)

        # Generate JSON response
        json_data = self.current_client.generate_json(prompt=prompt, system=system)

        return {
            'data': json_data,
            'model_used': model_to_use,
            'routing_reason': routing_info['reason'],
            'routing_strategy': routing_info['strategy']
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get usage statistics."""
        total_calls = self.stats['fast_model_calls'] + self.stats['quality_model_calls']

        return {
            'total_calls': total_calls,
            'fast_model_calls': self.stats['fast_model_calls'],
            'quality_model_calls': self.stats['quality_model_calls'],
            'model_switches': self.stats['model_switches'],
            'fast_model_percentage': (
                self.stats['fast_model_calls'] / total_calls * 100 if total_calls > 0 else 0
            ),
            'quality_model_percentage': (
                self.stats['quality_model_calls'] / total_calls * 100 if total_calls > 0 else 0
            ),
            'current_model': self.current_model_name
        }

    def print_stats(self):
        """Print usage statistics."""
        stats = self.get_stats()
        print(f"\n[STATS] Dual-Model Usage Statistics")
        print(f"  Total Calls: {stats['total_calls']}")
        print(f"  Fast Model (DeepSeek): {stats['fast_model_calls']} ({stats['fast_model_percentage']:.1f}%)")
        print(f"  Quality Model (Qwen 32B): {stats['quality_model_calls']} ({stats['quality_model_percentage']:.1f}%)")
        print(f"  Model Switches: {stats['model_switches']}")
        print(f"  Current Model in VRAM: {stats['current_model']}")


# Test function
def test_dual_model():
    """Test dual-model client"""
    print("\n" + "=" * 70)
    print("Testing Dual-Model Client with Automatic Routing")
    print("=" * 70)

    try:
        # Initialize
        client = DualModelClient()

        # Test cases
        test_cases = [
            {
                'prompt': "quel est mon solde ?",
                'intent': "CONSULTER_SOLDE",
                'confidence': 0.95,
                'mode': "banking",
                'expected': "fast"
            },
            {
                'prompt': "explique-moi comment fonctionne le crédit immobilier en détail",
                'intent': "SIMULATION_CREDIT",
                'confidence': 0.80,
                'mode': "banking",
                'expected': "quality"
            },
            {
                'prompt': "pourquoi mon virement a échoué ?",
                'intent': "UNKNOWN",
                'confidence': 0.45,
                'mode': "banking",
                'expected': "quality"
            },
            {
                'prompt': "explique ce code Python",
                'intent': "CODE_ASSIST",
                'confidence': 0.90,
                'mode': "coding",
                'expected': "quality"
            },
        ]

        for i, test in enumerate(test_cases, 1):
            print(f"\n[TEST {i}] {test['prompt']}")
            print(f"  Intent: {test['intent']} (conf: {test['confidence']:.2f}) | Mode: {test['mode']}")

            result = client.generate(
                prompt=test['prompt'],
                intent=test['intent'],
                confidence=test['confidence'],
                mode=test['mode']
            )

            print(f"  Model Used: {result['model_name']}")
            print(f"  Routing: {result['routing_reason']}")
            print(f"  Strategy: {result['routing_strategy']}")
            print(f"  Expected: {test['expected']} model")
            print(f"  Response (first 100 chars): {result['response'][:100]}...")

        # Print statistics
        client.print_stats()

        print("\n[OK] All tests completed!")

    except Exception as e:
        print(f"\n[FAIL] Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_dual_model()
