# -*- coding: utf-8 -*-
"""
LM Studio Client for Banking Assistant
Provides 100% GPU utilization vs Ollama's 11%
"""

from llm.openai_client import OpenAIClient


class LMStudioClient(OpenAIClient):
    """
    LM Studio client wrapper
    Uses OpenAI-compatible API on port 1234
    """

    def __init__(
        self,
        model_name: str = "qwen2.5-14b-instruct-q5_k_m",
        timeout: int = 120
    ):
        """
        Initialize LM Studio client

        Args:
            model_name: Model loaded in LM Studio (default: Qwen 14B Q5_K_M)
            timeout: Request timeout in seconds
        """
        super().__init__(
            base_url="http://localhost:1234/v1",
            model_name=model_name,
            api_key="lm-studio",  # LM Studio doesn't need a real key
            timeout=timeout
        )


def get_lmstudio_client_14b():
    """Get LM Studio client for Qwen 14B"""
    return LMStudioClient(model_name="qwen2.5-14b-instruct-q5_k_m")


def get_lmstudio_client_32b():
    """Get LM Studio client for Qwen 32B (expert mode)"""
    return LMStudioClient(model_name="qwen2.5-32b-instruct-q5_k_m")


def test_lmstudio():
    """Test LM Studio connection"""
    print("Testing LM Studio connection...")
    print("Make sure LM Studio server is running on port 1234!\n")

    try:
        client = get_lmstudio_client_14b()
        prompt = "Bonjour! Dis-moi en une phrase ce que tu peux faire."

        print(f"Prompt: {prompt}")
        response = client.generate(prompt, temperature=0.7, max_tokens=100)
        print(f"\nResponse: {response}")
        print("\n✓ LM Studio connection working!")

    except Exception as e:
        print(f"\n✗ Error: {e}")
        print("\nTroubleshooting:")
        print("1. Open LM Studio application")
        print("2. Go to 'Local Server' tab")
        print("3. Select Qwen2.5-14B-Instruct-GGUF model")
        print("4. Click 'Start Server' (port 1234)")


if __name__ == "__main__":
    test_lmstudio()
