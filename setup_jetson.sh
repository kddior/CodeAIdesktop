#!/bin/bash
# ============================================
# Jetson AGX Setup Script for LocalDeskDemo
# ============================================

set -e

echo "=========================================="
echo "LocalDeskDemo - Jetson AGX Setup"
echo "=========================================="

# Check if running on ARM64
ARCH=$(uname -m)
if [[ "$ARCH" != "aarch64" ]]; then
    echo "Warning: This script is optimized for ARM64 (Jetson). Detected: $ARCH"
fi

# Update system
echo "[1/6] Updating system packages..."
sudo apt-get update
sudo apt-get install -y python3-pip python3-venv git curl

# Create virtual environment
echo "[2/6] Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install PyTorch for Jetson (NVIDIA provides ARM64 wheels)
echo "[3/6] Installing PyTorch for Jetson..."
# For JetPack 5.x (L4T R35.x) - adjust version as needed
pip install --no-cache-dir torch torchvision torchaudio --index-url https://developer.download.nvidia.com/compute/redist/jp/v51/

# Install other requirements
echo "[4/6] Installing Python dependencies..."
pip install -r requirements.txt

# Install Ollama
echo "[5/6] Installing Ollama..."
curl -fsSL https://ollama.com/install.sh | sh

# Pull default model
echo "[6/6] Pulling Qwen model for Ollama..."
ollama pull qwen2.5:7b-instruct

echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "To start the server:"
echo "  1. Activate venv: source venv/bin/activate"
echo "  2. Start Ollama: ollama serve &"
echo "  3. Run Flask app: python app.py"
echo ""
echo "The API will be available at http://localhost:5000"
echo "=========================================="
