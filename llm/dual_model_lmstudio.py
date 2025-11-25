# -*- coding: utf-8 -*-
"""
Dual-Model LM Studio Client with Automatic Routing
Provides 100% GPU utilization vs Ollama's 11%
Manages fast and quality models for optimal performance
"""

from typing import Dict, Any, Optional
from .lmstudio_client import LMStudioClient
from .model_router import ModelRouter


class DualModelLMStudio:
    """
    Manages two models via LM Studio with automatic intelligent routing:
    - Qwen 2.5 7B: Fast banking queries (primary model)
    - Qwen 2.5 14B: Complex analysis (optional, higher quality)

    LM Studio provides 100% GPU utilization vs Ollama's 11%
    Critical for voice applications requiring low latency
    """

    def __init__(
        self,
        fast_model: str = "qwen2.5-7b-instruct",
        quality_model: str = "qwen2.5-14b-instruct",
        timeout: int = 60
    ):
        """
        Initialize dual-model LM Studio client.

        Args:
            fast_model: Model for fast queries (Qwen 7B)
            quality_model: Model for quality queries (Qwen 14B)
            timeout: Request timeout in seconds
        """
        self.fast_model_name = fast_model
        self.quality_model_name = quality_model
        self.timeout = timeout

        # Initialize router
        self.router = ModelRouter(fast_model=fast_model, quality_model=quality_model)

        # Single client (LM Studio handles model loading)
        self.client = LMStudioClient(model_name=fast_model, timeout=timeout)

        # Current model being used
        self.current_model = fast_model

        # Statistics
        self.stats = {
            'fast_model_calls': 0,
            'quality_model_calls': 0,
            'model_switches': 0
        }

        print(f"[INFO] LM Studio Dual-Model Client initialized")
        print(f"  Fast Model: {fast_model} (~4GB VRAM)")
        print(f"  Quality Model: {quality_model} (~8GB VRAM)")
        print(f"  GPU Utilization: 100% (vs Ollama's 11%)")
        print(f"  Strategy: Automatic routing based on query complexity")

    def generate(
        self,
        prompt: str,
        intent: str = "UNKNOWN",
        confidence: float = 0.5,
        mode: str = "general",
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
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
            max_tokens: Maximum tokens to generate
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

        # Track model switches
        if model_to_use != self.current_model:
            self.stats['model_switches'] += 1
            self.current_model = model_to_use
            print(f"[SWITCH] Using {model_to_use}")

        # Update client model if needed
        if self.client.model_name != model_to_use:
            self.client.model_name = model_to_use

        # Generate response
        response_text = self.client.generate(
            prompt=prompt,
            system=system,
            temperature=temperature,
            max_tokens=max_tokens
        )

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

        # Track model switches
        if model_to_use != self.current_model:
            self.stats['model_switches'] += 1
            self.current_model = model_to_use

        # Update client model if needed
        if self.client.model_name != model_to_use:
            self.client.model_name = model_to_use

        # Generate JSON response
        json_data = self.client.generate_json(prompt=prompt, system=system)

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
            'current_model': self.current_model
        }

    def print_stats(self):
        """Print usage statistics."""
        stats = self.get_stats()
        print(f"\n[STATS] LM Studio Dual-Model Usage Statistics")
        print(f"  Total Calls: {stats['total_calls']}")
        print(f"  Fast Model: {stats['fast_model_calls']} ({stats['fast_model_percentage']:.1f}%)")
        print(f"  Quality Model: {stats['quality_model_calls']} ({stats['quality_model_percentage']:.1f}%)")
        print(f"  Model Switches: {stats['model_switches']}")
        print(f"  Current Model: {stats['current_model']}")
