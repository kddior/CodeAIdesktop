# Configuration for Banking Assistant

# ============================================
# Storage Paths (Using NVMe SSDs for speed)
# ============================================
# /data  (NVMe 1) - LLM models
# /data2 (NVMe 2) - RAG, embeddings, documents
#
# IMPORTANT FOR JETSON USERS:
# Verify these paths exist on your system!
# If /data and /data2 don't exist, update to:
# MODELS_PATH = "/home/<username>/models"
# RAG_INDEX_PATH = "/home/<username>/CodeAIdesktop/rag_index"
# EMBEDDINGS_CACHE_PATH = "/home/<username>/CodeAIdesktop/embeddings"
# DOCUMENTS_PATH = "/home/<username>/CodeAIdesktop/documents"
#
MODELS_PATH = "/data/models"
RAG_INDEX_PATH = "/data2/CodeAIdesktop/rag_index"
EMBEDDINGS_CACHE_PATH = "/data2/CodeAIdesktop/embeddings"
DOCUMENTS_PATH = "/data2/CodeAIdesktop/documents"

# LLM Server Configuration
LLM_SERVER_URL = "http://localhost:1234/v1"  # llama-cpp-python server
LLM_MODEL_FILE = "/data/models/Qwen2.5-7B-Instruct-Q4_K_M.gguf"  # Using 7B (14B file corrupted, needs re-download)

# Model Configuration
# IMPORTANT FOR JETSON: Use multilingual embedding model for French banking
# Options:
# - paraphrase-multilingual-MiniLM-L12-v2 (420MB, good quality, RECOMMENDED)
# - intfloat/multilingual-e5-base (1.1GB, best quality, if RAM allows)
# - all-MiniLM-L6-v2 (80MB, English-only, NOT suitable for French)
EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"  # Multilingual for French
LLM_MODEL = "Qwen/Qwen2.5-7B-Instruct"
DEEPSEEK_MODEL = "deepseek-ai/deepseek-llm-7b-chat"  # Optional

# Intent Detection Thresholds (adjusted for multilingual model)
INTENT_THRESHOLD_HIGH = 0.65  # Direct acceptance
INTENT_THRESHOLD_LOW = 0.45   # Ambiguous zone
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
