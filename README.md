# LocalDeskDemo - Jetson AGX Deployment

Banking AI Assistant core logic for NVIDIA Jetson AGX (Linux ARM64).

## Architecture

```
┌─────────────────────────────────────┐
│          Flask API (app.py)         │
│            Port 5000                │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│         Core Pipeline               │
│  ├── Intent Detection               │
│  ├── Slot Extraction                │
│  ├── Dialogue Manager               │
│  └── Response Generator             │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│         LLM Layer                   │
│  └── Ollama (qwen2.5)               │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│         Knowledge                   │
│  ├── RAG (FAISS + BM25)             │
│  ├── Financial Calculator           │
│  └── Banking Backend                │
└─────────────────────────────────────┘
```

## Quick Start (Jetson AGX)

### Option 1: LM Studio (Recommended - 100% GPU)

```bash
# 1. Clone repository
git clone git@github.com:kddior/CodeAIdesktop.git
cd CodeAIdesktop

# 2. Run setup script
chmod +x setup_jetson.sh
./setup_jetson.sh

# 3. Activate environment
source venv/bin/activate

# 4. Download and start LM Studio
# - Download from: https://lmstudio.ai
# - Load Qwen 2.5 7B Instruct GGUF
# - Start server on port 1234

# 5. Start Flask API
python app.py
```

### Option 2: llama-cpp-python Server (Fastest - 100% GPU)

```bash
# 1-3. Same as above

# 4. Install llama-cpp-python with CUDA
chmod +x setup_llm_server_jetson.sh
./setup_llm_server_jetson.sh

# 5. Download model
mkdir -p models
cd models
wget https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-GGUF/resolve/main/qwen2.5-7b-instruct-q4_k_m.gguf
cd ..

# 6. Start llama-cpp server
python -m llama_cpp.server \
  --model models/qwen2.5-7b-instruct-q4_k_m.gguf \
  --host 0.0.0.0 \
  --port 8000 \
  --n_gpu_layers -1 \
  --n_ctx 4096 &

# 7. Start Flask API
python app.py
```

### Performance Comparison

| Backend | GPU Utilization | Speed | Best For |
|---------|----------------|-------|----------|
| Ollama | 11% | Slow ❌ | Not recommended |
| LM Studio | 100% | Fast ✅ | Easy setup |
| llama-cpp | 100% | Fastest 🚀 | Voice + Production |

## API Endpoints

- `POST /api/chat` - Send message, get AI response
- `GET /api/documents` - List RAG documents
- `POST /api/documents/upload` - Upload new document

## Project Structure

```
├── app.py                 # Flask API entry point
├── core/                  # Intent, slot, dialogue, flow logic
├── llm/                   # LLM clients (Ollama, OpenAI)
├── rag/                   # RAG system (FAISS indexing)
├── tools/                 # Financial calculators
├── intents/               # Intent handlers
├── backends/              # Banking backend (mock)
├── config/                # Configuration
├── setup_jetson.sh        # Jetson setup script
└── requirements.txt       # Python dependencies
```

## Configuration

Edit `config/config.py` to adjust:
- Embedding model
- Intent thresholds
- Device (cuda/cpu)

## LLM Server Options

### LM Studio (Recommended)
- **GPU Utilization:** 100%
- **Setup:** Download from https://lmstudio.ai
- **Models:** Qwen 2.5 7B or 14B Instruct GGUF
- **Port:** 1234 (OpenAI-compatible API)

### llama-cpp-python Server (Fastest)
- **GPU Utilization:** 100%
- **Setup:** Run `./setup_llm_server_jetson.sh`
- **Best for:** Voice applications, production deployments
- **Memory:** Q4 models use ~4-8GB VRAM

### Ollama (Not Recommended)
- **GPU Utilization:** Only 11% ❌
- **Issue:** Poor GPU utilization on Jetson
- **Use:** Only for testing/development
