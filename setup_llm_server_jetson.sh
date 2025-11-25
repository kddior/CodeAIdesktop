#!/bin/bash
# ============================================
# LLM Server Setup for Jetson AGX
# Installs llama-cpp-python with CUDA support
# MUCH FASTER than Ollama (100% GPU utilization)
# ============================================

set -e

echo "=========================================="
echo "LLM Server Setup for Jetson AGX"
echo "=========================================="

# Check if running on ARM64
ARCH=$(uname -m)
if [[ "$ARCH" != "aarch64" ]]; then
    echo "Warning: This script is optimized for ARM64 (Jetson). Detected: $ARCH"
fi

# Activate virtual environment
if [ ! -d "venv" ]; then
    echo "[ERROR] Virtual environment not found. Run ./setup_jetson.sh first!"
    exit 1
fi

echo "[INFO] Activating virtual environment..."
source venv/bin/activate

# Install build dependencies
echo "[1/4] Installing build dependencies..."
sudo apt-get install -y build-essential cmake ninja-build

# Install llama-cpp-python with CUDA support
echo "[2/4] Installing llama-cpp-python with CUDA..."
echo "         This may take 5-10 minutes to compile..."

# Set CUDA flags for Jetson
export CUDACXX=/usr/local/cuda/bin/nvcc
export CMAKE_ARGS="-DLLAMA_CUBLAS=on -DCMAKE_CUDA_ARCHITECTURES=87"
export FORCE_CMAKE=1

pip install --no-cache-dir llama-cpp-python

# Test installation
echo "[3/4] Testing llama-cpp-python installation..."
python3 -c "from llama_cpp import Llama; print('✓ llama-cpp-python installed successfully')"

# Download a small test model (optional)
echo "[4/4] Setup complete!"
echo ""
echo "=========================================="
echo "LLM Server Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo ""
echo "1. Download a GGUF model (recommended for Jetson AGX 32GB):"
echo "   - Qwen 2.5 7B Q4: ~4.3GB VRAM"
echo "   - Qwen 2.5 14B Q4: ~8.5GB VRAM"
echo ""
echo "   Example download:"
echo "   mkdir -p models"
echo "   cd models"
echo "   wget https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-GGUF/resolve/main/qwen2.5-7b-instruct-q4_k_m.gguf"
echo ""
echo "2. Start the llama-cpp-python server:"
echo "   python -m llama_cpp.server \\"
echo "     --model models/qwen2.5-7b-instruct-q4_k_m.gguf \\"
echo "     --host 0.0.0.0 \\"
echo "     --port 8000 \\"
echo "     --n_gpu_layers -1 \\"
echo "     --n_ctx 4096"
echo ""
echo "3. Update config/config.py to use llama-cpp server"
echo ""
echo "=========================================="
echo ""
echo "Performance Comparison:"
echo "  Ollama:           11% GPU utilization  (SLOW)"
echo "  LM Studio:       100% GPU utilization  (FAST)"
echo "  llama-cpp server:100% GPU utilization  (FASTEST)"
echo ""
echo "For voice applications, use llama-cpp server!"
echo "=========================================="
