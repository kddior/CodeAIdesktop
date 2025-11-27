# -*- coding: utf-8 -*-
"""
Dual-Server LLM Client
Uses two llama-cpp-python servers for optimal routing:
- 7B model (port 1234): Fast queries (greetings, simple banking)
- 14B model (port 1235): Complex queries (RAG, response generation)
"""

import requests
import json
from typing import Optional, Dict, Any


class DualServerClient:
    """
    Routes requests between 7B and 14B models based on query complexity.
    Both servers use llama-cpp-python with OpenAI-compatible API.
    """

    def __init__(
        self,
        fast_url: str = "http://localhost:1234/v1",
        quality_url: str = "http://localhost:1235/v1",
        fast_model: str = "qwen2.5-7b-instruct",
        quality_model: str = "qwen2.5-14b-instruct",
        timeout: int = 120
    ):
        """
        Initialize dual-server client.

        Args:
            fast_url: URL for fast 7B model server
            quality_url: URL for quality 14B model server
            fast_model: Model name for fast queries
            quality_model: Model name for quality queries
            timeout: Request timeout in seconds
        """
        self.fast_url = fast_url.rstrip('/')
        self.quality_url = quality_url.rstrip('/')
        self.fast_model = fast_model
        self.quality_model = quality_model
        self.timeout = timeout

        # Statistics
        self.stats = {
            'fast_calls': 0,
            'quality_calls': 0,
            'fast_errors': 0,
            'quality_errors': 0
        }

        print(f"[DualServer] Initialized with:")
        print(f"  Fast (7B): {fast_url}")
        print(f"  Quality (14B): {quality_url}")

    def _call_server(
        self,
        base_url: str,
        model_name: str,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> str:
        """Make a request to the specified server."""
        url = f"{base_url}/chat/completions"

        headers = {
            "Content-Type": "application/json"
        }

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": model_name,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False
        }

        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=self.timeout
        )
        response.raise_for_status()

        result = response.json()
        return result["choices"][0]["message"]["content"]

    def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        mode: str = "auto",
        intent: str = "",
        needs_rag: bool = False
    ) -> Dict[str, Any]:
        """
        Generate response with automatic model routing.

        Args:
            prompt: User prompt
            system: Optional system message
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            mode: Routing mode ("auto", "fast", "quality")
            intent: Detected intent (for routing decisions)
            needs_rag: Whether RAG is being used

        Returns:
            Dict with 'response', 'model_used', 'routing_reason'
        """
        # Determine which model to use
        use_quality = False
        routing_reason = "default"

        if mode == "quality":
            use_quality = True
            routing_reason = "forced_quality"
        elif mode == "fast":
            use_quality = False
            routing_reason = "forced_fast"
        elif mode == "auto":
            # Auto routing based on context
            if needs_rag:
                use_quality = True
                routing_reason = "rag_query"
            elif intent in ["RAG_QUESTION", "SIMULATION_CREDIT", "COMPLEX"]:
                use_quality = True
                routing_reason = f"intent_{intent}"
            elif len(prompt) > 500:
                use_quality = True
                routing_reason = "long_prompt"
            else:
                use_quality = False
                routing_reason = "simple_query"

        # Make the request
        if use_quality:
            try:
                response = self._call_server(
                    self.quality_url,
                    self.quality_model,
                    prompt,
                    system,
                    temperature,
                    max_tokens
                )
                self.stats['quality_calls'] += 1
                return {
                    'response': response,
                    'model_used': self.quality_model,
                    'routing_reason': routing_reason,
                    'server': '14B'
                }
            except Exception as e:
                print(f"[DualServer] 14B error, falling back to 7B: {e}")
                self.stats['quality_errors'] += 1
                # Fallback to fast model
                use_quality = False
                routing_reason = "fallback_from_14B"

        # Use fast model
        try:
            response = self._call_server(
                self.fast_url,
                self.fast_model,
                prompt,
                system,
                temperature,
                max_tokens
            )
            self.stats['fast_calls'] += 1
            return {
                'response': response,
                'model_used': self.fast_model,
                'routing_reason': routing_reason,
                'server': '7B'
            }
        except Exception as e:
            self.stats['fast_errors'] += 1
            raise Exception(f"Both servers failed: {e}")

    def generate_simple(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> str:
        """Simple generate that returns just the response text."""
        result = self.generate(prompt, system, temperature, max_tokens, mode="auto")
        return result['response']

    def get_stats(self) -> Dict[str, Any]:
        """Get usage statistics."""
        total = self.stats['fast_calls'] + self.stats['quality_calls']
        return {
            'total_calls': total,
            'fast_calls': self.stats['fast_calls'],
            'quality_calls': self.stats['quality_calls'],
            'fast_percentage': (self.stats['fast_calls'] / total * 100) if total > 0 else 0,
            'quality_percentage': (self.stats['quality_calls'] / total * 100) if total > 0 else 0,
            'errors': self.stats['fast_errors'] + self.stats['quality_errors']
        }

    def health_check(self) -> Dict[str, bool]:
        """Check if both servers are healthy."""
        results = {}

        # Check fast server
        try:
            resp = requests.get(f"{self.fast_url}/models", timeout=5)
            results['fast_7B'] = resp.status_code == 200
        except:
            results['fast_7B'] = False

        # Check quality server
        try:
            resp = requests.get(f"{self.quality_url}/models", timeout=5)
            results['quality_14B'] = resp.status_code == 200
        except:
            results['quality_14B'] = False

        return results


# Test function
def test_dual_server():
    """Test the dual server client."""
    print("Testing Dual Server Client...")

    client = DualServerClient()

    # Health check
    health = client.health_check()
    print(f"\nHealth Check: {health}")

    if not all(health.values()):
        print("Not all servers are healthy!")
        return

    # Test fast query
    print("\n--- Testing Fast Query (Greeting) ---")
    result = client.generate(
        "Bonjour!",
        mode="auto",
        intent="GREETING"
    )
    print(f"Model: {result['model_used']}")
    print(f"Reason: {result['routing_reason']}")
    print(f"Response: {result['response'][:100]}...")

    # Test quality query
    print("\n--- Testing Quality Query (RAG) ---")
    result = client.generate(
        "Quels sont les frais de carte bancaire?",
        mode="auto",
        needs_rag=True
    )
    print(f"Model: {result['model_used']}")
    print(f"Reason: {result['routing_reason']}")
    print(f"Response: {result['response'][:100]}...")

    # Stats
    print(f"\nStats: {client.get_stats()}")


if __name__ == "__main__":
    test_dual_server()
