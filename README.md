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

```bash
# 1. Clone repository
git clone git@github.com:kddior/CodeAIdesktop.git
cd CodeAIdesktop

# 2. Run setup script
chmod +x setup_jetson.sh
./setup_jetson.sh

# 3. Activate environment
source venv/bin/activate

# 4. Start Ollama server (background)
ollama serve &

# 5. Start Flask API
python app.py
```

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

## LLM Server

Default: Ollama with `qwen2.5:7b-instruct`

For larger models on Jetson AGX (32GB):
```bash
ollama pull qwen2.5:14b-instruct
```
