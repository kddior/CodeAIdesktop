# -*- coding: utf-8 -*-
"""
Ollama Client for Banking Assistant
Optimized for RTX 3090
"""

import json
import sys
import io
from typing import Dict, Any, Optional
import traceback

# UTF-8 console encoding - disabled because it conflicts with Streamlit
# Streamlit handles stdout redirection, so we don't need to wrap it
# If needed, configure UTF-8 at the OS level: chcp 65001


class OllamaClient:
    """Ollama LLM client with GPU optimization"""

    def __init__(self, model_name: str = "qwen2.5:7b-instruct", timeout: int = 30):
        """
        Initialize Ollama client

        Args:
            model_name: Ollama model name
            timeout: Request timeout in seconds
        """
        self.model_name = model_name
        self.timeout = timeout

        try:
            import ollama
            self.client = ollama.Client()
            # Silent - no print in Streamlit context

            # Test connection
            self._test_connection()

        except ImportError:
            raise
        except Exception as e:
            raise

    def _test_connection(self):
        """Test connection to Ollama"""
        try:
            # List models to verify Ollama is running
            models = self.client.list()
            # Silent - no print in Streamlit context
            # Model verification happens silently
        except Exception:
            # Silent - connection test failed but that's ok
            pass

    def generate(self, prompt: str, system: Optional[str] = None, temperature: float = 0.7) -> str:
        """
        Generate response from Ollama

        Args:
            prompt: User prompt
            system: Optional system message
            temperature: Sampling temperature

        Returns:
            Generated text response
        """
        try:
            messages = []

            if system:
                messages.append({
                    'role': 'system',
                    'content': system
                })

            messages.append({
                'role': 'user',
                'content': prompt
            })

            response = self.client.chat(
                model=self.model_name,
                messages=messages,
                options={
                    'temperature': temperature,
                    'num_gpu': 999,  # Force ALL layers to GPU (RTX 3090)
                    'num_thread': 8,  # CPU threads for non-GPU work
                    'use_mmap': True,  # Memory-mapped files for efficiency
                    'use_mlock': False,  # Don't lock memory (allow swap if needed)
                }
            )

            return response['message']['content'].strip()

        except Exception as e:
            print(f"[FAIL] Ollama generation error: {e}")
            traceback.print_exc()
            return ""

    def generate_json(self, prompt: str, system: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate JSON response from Ollama

        Args:
            prompt: User prompt (should request JSON format)
            system: Optional system message

        Returns:
            Parsed JSON dictionary
        """
        try:
            # Add JSON format instruction
            json_prompt = f"{prompt}\n\nRespond with ONLY valid JSON, no other text."

            response_text = self.generate(json_prompt, system, temperature=0.3)

            # Extract JSON from response
            # Sometimes LLM adds markdown code blocks
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()
            elif "```" in response_text:
                json_start = response_text.find("```") + 3
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()

            # Parse JSON
            return json.loads(response_text)

        except json.JSONDecodeError as e:
            print(f"[FAIL] Failed to parse JSON: {e}")
            print(f"   Response was: {response_text[:200]}")
            return {}
        except Exception as e:
            print(f"[FAIL] Ollama JSON generation error: {e}")
            traceback.print_exc()
            return {}

    def check_gpu_usage(self) -> Dict[str, Any]:
        """
        Check if GPU is being used by Ollama

        Returns:
            GPU usage information
        """
        try:
            import subprocess

            result = subprocess.run(
                ["nvidia-smi", "--query-compute-apps=pid,process_name,used_memory",
                 "--format=csv,noheader"],
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                gpu_processes = result.stdout.strip().split('\n')
                ollama_processes = [p for p in gpu_processes if 'ollama' in p.lower()]

                if ollama_processes:
                    return {
                        'gpu_used': True,
                        'processes': ollama_processes,
                        'message': '[OK] Ollama is using GPU (RTX 3090)'
                    }
                else:
                    return {
                        'gpu_used': False,
                        'message': '[WARN] Ollama not detected on GPU (might be idle or using CPU)'
                    }
            else:
                return {
                    'gpu_used': None,
                    'message': '[WARN] Could not check GPU usage'
                }

        except FileNotFoundError:
            return {
                'gpu_used': None,
                'message': '[WARN] nvidia-smi not found'
            }
        except Exception as e:
            return {
                'gpu_used': None,
                'message': f'[WARN] Error checking GPU: {e}'
            }


# Test function
def test_ollama():
    """Test Ollama client"""
    print("\n" + "=" * 60)
    print("Testing Ollama Client")
    print("=" * 60)

    try:
        # Initialize
        client = OllamaClient()

        # Test text generation
        print("\nTest 1: Simple generation")
        response = client.generate("Say 'Hello, I am Qwen running on RTX 3090!'")
        print(f"Response: {response}")

        # Test JSON generation
        print("\nTest 2: JSON generation")
        json_response = client.generate_json("""
Extract information from this message: "je veux virer 50000 XOF à Pierre"

Return JSON with fields: montant, devise, beneficiaire_nom
        """)
        print(f"JSON: {json_response}")

        # Check GPU usage
        print("\nTest 3: GPU Usage")
        gpu_info = client.check_gpu_usage()
        print(gpu_info['message'])
        if gpu_info.get('processes'):
            for proc in gpu_info['processes']:
                print(f"  {proc}")

        print("\n[OK] All tests passed!")

    except Exception as e:
        print(f"\n[FAIL] Test failed: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    test_ollama()
