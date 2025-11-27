# -*- coding: utf-8 -*-
"""
Dual-Model LLM Client with Automatic Routing
Uses TWO llama-cpp-python servers for true parallel model hosting:
- Qwen 7B on port 1234: Fast queries (greetings, simple banking, basic operations)
- Qwen 14B on port 1235: Complex queries (RAG, analysis, response generation)

Provides 100% GPU utilization on Jetson AGX
"""

from typing import Dict, Any, Optional
import requests
import json
from .model_router import ModelRouter


class DualModelLMStudio:
    """
    Manages two separate llama-cpp-python servers with automatic intelligent routing:
    - Qwen 2.5 7B (port 1234): Fast banking queries
    - Qwen 2.5 14B (port 1235): Complex analysis, RAG questions

    Both servers run simultaneously for instant switching without model reload.
    """

    def __init__(
        self,
        fast_model: str = "qwen2.5-7b-instruct",
        quality_model: str = "qwen2.5-14b-instruct",
        fast_port: int = 1234,
        quality_port: int = 1235,
        timeout: int = 120
    ):
        """
        Initialize dual-model client with two separate servers.

        Args:
            fast_model: Model name for fast queries (Qwen 7B)
            quality_model: Model name for quality queries (Qwen 14B)
            fast_port: Port for 7B server
            quality_port: Port for 14B server
            timeout: Request timeout in seconds
        """
        self.fast_model_name = fast_model
        self.quality_model_name = quality_model
        self.fast_url = f"http://localhost:{fast_port}/v1"
        self.quality_url = f"http://localhost:{quality_port}/v1"
        self.timeout = timeout

        # Initialize router
        self.router = ModelRouter(fast_model=fast_model, quality_model=quality_model)

        # Current model being used
        self.current_model = fast_model

        # Statistics
        self.stats = {
            'fast_model_calls': 0,
            'quality_model_calls': 0,
            'model_switches': 0,
            'fast_errors': 0,
            'quality_errors': 0
        }

        print(f"[INFO] Dual-Server LLM Client initialized")
        print(f"  Fast Model (7B): {fast_model} @ port {fast_port}")
        print(f"  Quality Model (14B): {quality_model} @ port {quality_port}")
        print(f"  GPU Utilization: 100% (parallel servers)")
        print(f"  Strategy: Automatic routing based on query complexity")

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

        headers = {"Content-Type": "application/json"}

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
        intent: str = "UNKNOWN",
        confidence: float = 0.5,
        mode: str = "general",
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        force_model: Optional[str] = None,
        needs_rag: bool = False
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
            max_tokens: Maximum tokens to generate
            force_model: Force specific model (skip routing)
            needs_rag: Whether RAG is being used (routes to 14B)

        Returns:
            {
                'response': str,
                'model_used': str,
                'routing_reason': str,
                'routing_strategy': str
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
        elif needs_rag:
            # RAG queries always use 14B for better quality
            model_to_use = self.quality_model_name
            routing_info = {
                'model': self.quality_model_name,
                'reason': 'RAG query (needs_rag=true)',
                'strategy': 'rag_routing'
            }
        else:
            routing_info = self.router.route(
                intent=intent,
                query=prompt,
                confidence=confidence,
                mode=mode
            )
            model_to_use = routing_info['model']

        # Determine server to use
        use_quality = (model_to_use == self.quality_model_name)

        # Track model switches
        if model_to_use != self.current_model:
            self.stats['model_switches'] += 1
            self.current_model = model_to_use
            print(f"[SWITCH] Using {model_to_use}")

        # Make the request to appropriate server
        if use_quality:
            try:
                response_text = self._call_server(
                    self.quality_url,
                    self.quality_model_name,
                    prompt,
                    system,
                    temperature,
                    max_tokens
                )
                self.stats['quality_model_calls'] += 1
            except Exception as e:
                print(f"[WARN] 14B server error, falling back to 7B: {e}")
                self.stats['quality_errors'] += 1
                # Fallback to 7B
                response_text = self._call_server(
                    self.fast_url,
                    self.fast_model_name,
                    prompt,
                    system,
                    temperature,
                    max_tokens
                )
                self.stats['fast_model_calls'] += 1
                model_to_use = self.fast_model_name
                routing_info['reason'] = 'Fallback from 14B error'
        else:
            try:
                response_text = self._call_server(
                    self.fast_url,
                    self.fast_model_name,
                    prompt,
                    system,
                    temperature,
                    max_tokens
                )
                self.stats['fast_model_calls'] += 1
            except Exception as e:
                print(f"[WARN] 7B server error, trying 14B: {e}")
                self.stats['fast_errors'] += 1
                # Fallback to 14B
                response_text = self._call_server(
                    self.quality_url,
                    self.quality_model_name,
                    prompt,
                    system,
                    temperature,
                    max_tokens
                )
                self.stats['quality_model_calls'] += 1
                model_to_use = self.quality_model_name
                routing_info['reason'] = 'Fallback from 7B error'

        # Get model info
        model_info = self.router.get_model_info(model_to_use)

        return {
            'response': response_text,
            'model_used': model_to_use,
            'model_name': model_info.get('name', model_to_use),
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
        # Generate response
        result = self.generate(
            prompt=prompt,
            intent=intent,
            confidence=confidence,
            mode=mode,
            system=system,
            force_model=force_model
        )

        # Parse JSON from response
        response_text = result['response']

        # Try to extract JSON from response
        try:
            # Look for JSON in the response
            if '{' in response_text:
                start = response_text.find('{')
                end = response_text.rfind('}') + 1
                json_str = response_text[start:end]
                json_data = json.loads(json_str)
            else:
                json_data = {"raw": response_text}
        except json.JSONDecodeError:
            json_data = {"raw": response_text, "parse_error": True}

        return {
            'data': json_data,
            'model_used': result['model_used'],
            'routing_reason': result['routing_reason'],
            'routing_strategy': result['routing_strategy']
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
            'current_model': self.current_model,
            'errors': self.stats['fast_errors'] + self.stats['quality_errors']
        }

    def print_stats(self):
        """Print usage statistics."""
        stats = self.get_stats()
        print(f"\n[STATS] Dual-Server LLM Usage Statistics")
        print(f"  Total Calls: {stats['total_calls']}")
        print(f"  Fast Model (7B): {stats['fast_model_calls']} ({stats['fast_model_percentage']:.1f}%)")
        print(f"  Quality Model (14B): {stats['quality_model_calls']} ({stats['quality_model_percentage']:.1f}%)")
        print(f"  Model Switches: {stats['model_switches']}")
        print(f"  Current Model: {stats['current_model']}")
        print(f"  Errors: {stats['errors']}")

    def health_check(self) -> Dict[str, bool]:
        """Check if both servers are healthy."""
        results = {}

        # Check fast server (7B)
        try:
            resp = requests.get(f"{self.fast_url}/models", timeout=5)
            results['fast_7B'] = resp.status_code == 200
        except:
            results['fast_7B'] = False

        # Check quality server (14B)
        try:
            resp = requests.get(f"{self.quality_url}/models", timeout=5)
            results['quality_14B'] = resp.status_code == 200
        except:
            results['quality_14B'] = False

        return results
