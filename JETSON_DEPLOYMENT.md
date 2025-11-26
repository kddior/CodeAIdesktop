# Jetson AGX Deployment Guide
## Complete Streamlit Banking Assistant with llama.cpp

This guide helps you deploy the full 7-tab Streamlit banking assistant on your Jetson AGX.

---

## What's Included Now

After the latest updates, the repository includes:

### ✅ Complete Files
- **streamlit_app_full.py** (2,517 lines) - Full 7-tab UI interface
- **pdf_extractor.py** - PDF text extraction with 5 methods + OCR
- **tests/banking_tests.json** - 100+ test scenarios
- **requirements.txt** - All dependencies including Streamlit, PDF libs
- **config/config.py** - Updated for French multilingual support
- All backend components (banking assistant, RAG, calculators)

### 📋 7 Tabs Implemented
1. **Conversation** - Chat with banking assistant
2. **Tests Auto** - Automated testing with JSON scenarios
3. **Résultats** - Test results with metrics and export
4. **Documents** - RAG document management
5. **Calculateur** - 11 financial calculators
6. **Garantie** - Bank guarantee calculator with LLM verification
7. **Analyse Juridique** - Legal document analysis with PDF extraction

---

## Pre-Deployment Checklist

### Hardware Requirements
- [ ] **Jetson Model:** AGX Orin 32GB or 64GB
- [ ] **Storage:** 50GB+ free space (NVMe SSD recommended)
- [ ] **JetPack:** Version 5.1.x or 6.x installed
- [ ] **CUDA:** Working (`nvidia-smi` shows GPU)

### Software Requirements
- [ ] **Python:** 3.10+ (`python3 --version`)
- [ ] **Git:** Installed
- [ ] **Tesseract:** For OCR (we'll install this)

---

## Step 1: Clone Repository

```bash
cd ~
git clone https://github.com/kddior/CodeAIdesktop.git
cd CodeAIdesktop
```

---

## Step 2: Update Configuration Paths

The default config uses `/data` and `/data2` paths. **You must verify these exist or update them.**

### Check if paths exist:
```bash
ls -la /data
ls -la /data2
```

### If paths DON'T exist, update config:
```bash
nano config/config.py
```

**Change from:**
```python
MODELS_PATH = "/data/models"
RAG_INDEX_PATH = "/data2/CodeAIdesktop/rag_index"
EMBEDDINGS_CACHE_PATH = "/data2/CodeAIdesktop/embeddings"
DOCUMENTS_PATH = "/data2/CodeAIdesktop/documents"
```

**Change to:**
```python
MODELS_PATH = "/home/<your-username>/models"
RAG_INDEX_PATH = "/home/<your-username>/CodeAIdesktop/rag_index"
EMBEDDINGS_CACHE_PATH = "/home/<your-username>/CodeAIdesktop/embeddings"
DOCUMENTS_PATH = "/home/<your-username>/CodeAIdesktop/documents"
```

**Create directories:**
```bash
mkdir -p ~/models
mkdir -p ~/CodeAIdesktop/rag_index
mkdir -p ~/CodeAIdesktop/embeddings
mkdir -p ~/CodeAIdesktop/documents
```

---

## Step 3: Install System Dependencies

```bash
# Update system
sudo apt-get update

# Install Tesseract OCR (for PDF extraction)
sudo apt-get install -y tesseract-ocr tesseract-ocr-fra

# Verify installation
tesseract --version
```

---

## Step 4: Set Up Python Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip
```

---

## Step 5: Install Python Dependencies

```bash
# Install all dependencies
pip install -r requirements.txt

# This installs:
# - Streamlit (full UI)
# - PyMuPDF, pdfplumber, PyPDF2, pypdf (PDF extraction)
# - pytesseract, Pillow (OCR)
# - sentence-transformers (multilingual embeddings)
# - All other dependencies
```

**Note:** This will take 10-20 minutes on Jetson. Be patient!

---

## Step 6: Download Multilingual Embedding Model

The config now uses `paraphrase-multilingual-MiniLM-L12-v2` for French support.

```bash
# Download embedding model (first run)
python3 -c "
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
print('✅ Embedding model downloaded!')
"
```

This downloads ~420MB and caches it for future use.

---

## Step 7: Set Up LLM Server (llama.cpp)

### Option A: Using llama-cpp-python (Recommended)

```bash
# Install llama-cpp-python with CUDA
CMAKE_ARGS="-DGGML_CUDA=ON" pip install llama-cpp-python

# Verify installation
python3 -c "import llama_cpp; print('✅ llama-cpp-python installed')"
```

### Option B: Native llama.cpp (Advanced)

```bash
# Clone and build llama.cpp
cd ~
git clone https://github.com/ggerganov/llama.cpp
cd llama.cpp

# Build with CUDA for Jetson Orin (architecture 87)
cmake -B build -DGGML_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES=87
cmake --build build --config Release -j$(nproc)

# Verify
./build/bin/llama-cli --version
```

---

## Step 8: Transfer Model Files

You need GGUF model files. Choose one option:

### Option 1: 14B Model Only (Recommended for 32GB Jetson)
- **Model:** Qwen2.5-14B-Instruct (Q5_K_M quantization)
- **Size:** ~10GB
- **RAM Usage:** ~8-10GB

### Option 2: 14B + 32B Models (For 64GB Jetson)
- **14B:** General chat and intent detection
- **32B:** Expert verification (calculators, legal analysis)
- **Total Size:** ~30GB
- **RAM Usage:** ~25-30GB (when both loaded)

### Transfer from Windows PC:
```bash
# From Windows, copy via SCP:
scp C:\path\to\qwen2.5-14b-instruct-q5_k_m.gguf user@jetson-ip:~/models/

# Or use USB drive:
# 1. Copy models to USB on Windows
# 2. Plug USB into Jetson
# 3. Mount and copy:
sudo mount /dev/sda1 /mnt
cp /mnt/*.gguf ~/models/
sudo umount /mnt
```

### Or Download from HuggingFace:
```bash
cd ~/models

# Download 14B model
wget https://huggingface.co/Qwen/Qwen2.5-14B-Instruct-GGUF/resolve/main/qwen2.5-14b-instruct-q5_k_m.gguf

# Optional: Download 32B model (for expert mode)
# wget https://huggingface.co/Qwen/Qwen2.5-32B-Instruct-GGUF/resolve/main/qwen2.5-32b-instruct-q5_k_m.gguf
```

---

## Step 9: Start LLM Server

### Using llama-cpp-python:

```bash
# Terminal 1: Start LLM server
python3 -m llama_cpp.server \
  --model ~/models/qwen2.5-14b-instruct-q5_k_m.gguf \
  --host 0.0.0.0 \
  --port 1234 \
  --n_gpu_layers -1 \
  --n_ctx 8192 \
  --chat_format chatml

# Leave this running
```

### Using native llama.cpp:

```bash
# Terminal 1: Start llama-server
cd ~/llama.cpp
./build/bin/llama-server \
  -m ~/models/qwen2.5-14b-instruct-q5_k_m.gguf \
  --host 0.0.0.0 \
  --port 1234 \
  -ngl 99 \
  -c 8192 \
  --parallel 2

# Leave this running
```

### Verify server is running:
```bash
# In another terminal:
curl http://localhost:1234/v1/models

# Should return JSON with model info
```

---

## Step 10: Start Streamlit App

```bash
# Terminal 2: Start Streamlit
cd ~/CodeAIdesktop
source venv/bin/activate

# Run the FULL app (not the simple test one)
streamlit run streamlit_app_full.py --server.port 8502 --server.address 0.0.0.0
```

**Access the app:**
- **Local:** http://localhost:8502
- **Network:** http://[jetson-ip]:8502
- Find Jetson IP: `hostname -I`

---

## Step 11: Test the Application

### Test Checklist:
- [ ] **Tab 1 (Conversation):** Chat works, shows intent/confidence
- [ ] **Tab 2 (Tests Auto):** Can load and run test scenarios
- [ ] **Tab 3 (Résultats):** Test results display with metrics
- [ ] **Tab 4 (Documents):** Can upload PDF/TXT, shows in list
- [ ] **Tab 5 (Calculateur):** All 11 calculators work
- [ ] **Tab 6 (Garantie):** Guarantee calculator with LLM verification
- [ ] **Tab 7 (Juridique):** PDF upload, text extraction, analysis

### Quick Chat Tests:
```
1. "quel est mon solde ?"
   → Should detect CONSULTER_SOLDE intent

2. "je veux faire un virement de 50000 FCFA"
   → Should detect FAIRE_VIREMENT intent

3. "simulation de crédit immobilier"
   → Should detect SIMULATION_CREDIT intent
```

---

## Troubleshooting

### Issue: LLM Server Won't Start
```bash
# Check CUDA is working:
nvidia-smi

# Check model file exists:
ls -lh ~/models/*.gguf

# Try with fewer GPU layers:
python3 -m llama_cpp.server --model ~/models/qwen2.5-14b-instruct-q5_k_m.gguf --n_gpu_layers 20
```

### Issue: Streamlit Shows "Assistant Not Initialized"
```bash
# Check LLM server is running:
curl http://localhost:1234/v1/models

# Check logs in Streamlit terminal for errors
```

### Issue: PDF Extraction Fails
```bash
# Verify Tesseract is installed:
tesseract --version

# Install French language pack:
sudo apt-get install tesseract-ocr-fra

# Test PDF extraction:
python3 pdf_extractor.py /path/to/test.pdf
```

### Issue: RAG Not Working
```bash
# Create RAG directories:
mkdir -p ~/CodeAIdesktop/rag_index
mkdir -p ~/CodeAIdesktop/documents

# Check embedding model is downloaded:
python3 -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')"
```

### Issue: Out of Memory
```bash
# Check GPU memory:
nvidia-smi

# Use smaller context size:
python3 -m llama_cpp.server --model ~/models/qwen2.5-14b-instruct-q5_k_m.gguf --n_ctx 4096

# Or use CPU fallback (slower):
python3 -m llama_cpp.server --model ~/models/qwen2.5-14b-instruct-q5_k_m.gguf --n_gpu_layers 0
```

---

## Performance Optimization

### For Better Speed:
1. **Use NVMe storage** for models (not SD card)
2. **Increase GPU layers:** `-ngl 99` or `--n_gpu_layers -1`
3. **Use Q4 quantization** for 14B model (faster, less RAM)
4. **Reduce context size:** `-c 4096` instead of 8192

### For Better Quality:
1. **Use Q5 or Q6 quantization** (more accurate, slower)
2. **Increase context size:** `-c 8192` or more
3. **Use 32B expert model** for verification tasks

---

## Running as a Service (Optional)

### Create systemd service for LLM server:

```bash
sudo nano /etc/systemd/system/llm-server.service
```

**Content:**
```ini
[Unit]
Description=LLM Server (llama.cpp)
After=network.target

[Service]
Type=simple
User=<your-username>
WorkingDirectory=/home/<your-username>
ExecStart=/home/<your-username>/CodeAIdesktop/venv/bin/python3 -m llama_cpp.server \
  --model /home/<your-username>/models/qwen2.5-14b-instruct-q5_k_m.gguf \
  --host 0.0.0.0 \
  --port 1234 \
  --n_gpu_layers -1 \
  --n_ctx 8192
Restart=always

[Install]
WantedBy=multi-user.target
```

**Enable and start:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable llm-server
sudo systemctl start llm-server
sudo systemctl status llm-server
```

### Create systemd service for Streamlit:

```bash
sudo nano /etc/systemd/system/streamlit-app.service
```

**Content:**
```ini
[Unit]
Description=Streamlit Banking App
After=network.target llm-server.service

[Service]
Type=simple
User=<your-username>
WorkingDirectory=/home/<your-username>/CodeAIdesktop
ExecStart=/home/<your-username>/CodeAIdesktop/venv/bin/streamlit run streamlit_app_full.py \
  --server.port 8502 \
  --server.address 0.0.0.0
Restart=always

[Install]
WantedBy=multi-user.target
```

**Enable and start:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable streamlit-app
sudo systemctl start streamlit-app
sudo systemctl status streamlit-app
```

---

## Network Access

### Firewall Configuration (if needed):
```bash
sudo ufw allow 1234  # LLM server
sudo ufw allow 8502  # Streamlit
sudo ufw enable
```

### Access from Other Devices:
- Find Jetson IP: `hostname -I`
- Access app: `http://[jetson-ip]:8502`

### For Production (Optional):
- Set up reverse proxy with Nginx
- Enable HTTPS with Let's Encrypt
- Add authentication (Streamlit supports this)

---

## What's Different from Windows

| Component | Windows | Jetson |
|-----------|---------|--------|
| **LLM Server** | LM Studio GUI | llama-cpp-python CLI |
| **Port** | Same (1234) | Same (1234) |
| **API** | OpenAI-compatible | OpenAI-compatible |
| **Code Changes** | None needed | None needed |
| **Model Format** | GGUF | GGUF (same files) |
| **Python** | Windows | Linux ARM64 |
| **Storage Paths** | Windows paths | Linux paths (update config.py) |

---

## Additional Features

### Optional: Google Custom Search (Tab 7)
If you want web search enrichment in legal analysis:

1. Get API keys from Google Cloud Console
2. Uncomment in requirements.txt:
   ```bash
   pip install google-api-python-client
   ```
3. Add to config.py:
   ```python
   GOOGLE_API_KEY = "your-api-key"
   GOOGLE_CSE_ID = "your-cse-id"
   ```

---

## Support & Updates

### Get Latest Updates:
```bash
cd ~/CodeAIdesktop
git pull origin main
pip install -r requirements.txt  # In case new deps added
```

### Check Logs:
```bash
# LLM server logs (if using systemd):
sudo journalctl -u llm-server -f

# Streamlit logs (if using systemd):
sudo journalctl -u streamlit-app -f
```

### Report Issues:
- GitHub: https://github.com/kddior/CodeAIdesktop/issues

---

## Summary

You now have:
- ✅ Full 7-tab Streamlit UI
- ✅ PDF extraction with 5 methods + OCR
- ✅ 100+ test scenarios
- ✅ Multilingual French support
- ✅ All 11 financial calculators
- ✅ Legal document analysis
- ✅ RAG document management
- ✅ Complete banking assistant

**Next Steps:**
1. Customize for your bank's specific needs
2. Add more test scenarios
3. Upload your bank's documents to RAG
4. Train on your specific banking terminology

**Enjoy your AI banking assistant! 🏦🚀**
