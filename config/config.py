# Configuration for Banking Assistant

# ============================================
# Storage Paths (Using NVMe SSDs for speed)
# ============================================
# /data  (NVMe 1) - LLM models
# /data2 (NVMe 2) - RAG, embeddings, documents
MODELS_PATH = "/data/models"
RAG_INDEX_PATH = "/data2/CodeAIdesktop/rag_index"
EMBEDDINGS_CACHE_PATH = "/data2/CodeAIdesktop/embeddings"
DOCUMENTS_PATH = "/data2/CodeAIdesktop/documents"

# LLM Server Configuration
LLM_SERVER_URL = "http://localhost:1234/v1"  # llama-cpp-python server
LLM_MODEL_FILE = "/data/models/Qwen2.5-7B-Instruct-Q4_K_M.gguf"

# Model Configuration
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"  # Smaller, faster model (80MB vs 2GB)
LLM_MODEL = "Qwen/Qwen2.5-7B-Instruct"
DEEPSEEK_MODEL = "deepseek-ai/deepseek-llm-7b-chat"  # Optional

# Intent Detection Thresholds (adjusted for all-MiniLM-L6-v2 model)
INTENT_THRESHOLD_HIGH = 0.55  # Direct acceptance (lower for smaller model)
INTENT_THRESHOLD_LOW = 0.40   # Ambiguous zone (lower for smaller model)
INTENT_WEIGHT_EMB = 0.6       # Weight for embedding score (rely more on rules)
INTENT_WEIGHT_RULES = 0.4     # Weight for rule-based score (rely more on rules)

# Supported Intents
INTENTS = [
    "CONSULTER_SOLDE",
    "DISCUSSION_COMPTE",
    "FAIRE_VIREMENT",
    "OBTENIR_RELEVE",
    "SIMULATION_CREDIT",
    "OTHER"
]

# Supported Currencies
SUPPORTED_CURRENCIES = ["XOF", "FCFA", "EUR", "USD"]

# Device Configuration
DEVICE = "cuda"  # or "cpu"

# Slot Validation Limits
MONTANT_MIN = 1
MONTANT_MAX = 1_000_000_000  # 1 billion
DUREE_MIN_MOIS = 1
DUREE_MAX_MOIS = 360  # 30 years
TAUX_MIN = 0.0
TAUX_MAX = 100.0
