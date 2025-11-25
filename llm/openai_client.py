# -*- coding: utf-8 -*-
"""
OpenAI-Compatible LLM Client
Works with Ollama, vLLM, LM Studio, etc.
"""

import requests
import json
from typing import Optional, Dict, Any


class OpenAIClient:
    """
    OpenAI-compatible API client
    Works with any OpenAI-compatible server (Ollama, vLLM, LM Studio, etc.)
    """

    def __init__(
        self,
        base_url: str = "http://localhost:11434/v1",
        model_name: str = "qwen2.5:14b-instruct",
        api_key: str = "ollama",  # Ollama doesn't need a real key
        timeout: int = 120
    ):
        """
        Initialize OpenAI-compatible client

        Args:
            base_url: API endpoint (default: Ollama's OpenAI-compatible endpoint)
            model_name: Model to use
            api_key: API key (not needed for Ollama)
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.model_name = model_name
        self.api_key = api_key
        self.timeout = timeout

    def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        stop: Optional[list] = None
    ) -> str:
        """
        Generate text using OpenAI-compatible API

        Args:
            prompt: Input prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            stop: Stop sequences

        Returns:
            Generated text
        """
        url = f"{self.base_url}/chat/completions"

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False
        }

        if stop:
            payload["stop"] = stop

        try:
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()

            result = response.json()
            return result["choices"][0]["message"]["content"]

        except requests.exceptions.RequestException as e:
            raise Exception(f"LLM API request failed: {e}")
        except (KeyError, IndexError) as e:
            raise Exception(f"Invalid API response format: {e}")


def test_openai_client():
    """Test the OpenAI client with Ollama"""
    print("Testing OpenAI-compatible client with Ollama...")

    client = OpenAIClient(
        base_url="http://localhost:11434/v1",
        model_name="qwen2.5:14b-instruct"
    )

    prompt = "Bonjour! Comment puis-je vous aider aujourd'hui?"
    print(f"\nPrompt: {prompt}")

    response = client.generate(prompt, temperature=0.7)
    print(f"\nResponse: {response}")


if __name__ == "__main__":
    test_openai_client()
