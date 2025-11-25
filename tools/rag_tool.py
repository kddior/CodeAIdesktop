# tools/rag_tool.py

import numpy as np
from typing import List, Dict, Optional, Literal
from sentence_transformers import SentenceTransformer
import json
from pathlib import Path
from datetime import datetime


class RAGTool:
    """
    RAG (Retrieval Augmented Generation) Tool

    Searches internal documents using semantic similarity.

    Supports multiple vector database backends:
    - In-memory (for development/testing)
    - Oracle AI Vector Search 23ai (production - recommended)
    - pgvector (PostgreSQL extension)
    - Qdrant (vector database)

    For production, use Oracle AI Vector Search with the embedding model.
    """

    def __init__(
        self,
        vector_db: Literal["memory", "oracle", "pgvector", "qdrant"] = "memory",
        embedding_model: str = "BAAI/bge-m3",
        db_config: Optional[Dict] = None,
        docs_path: Optional[str] = None
    ):
        """
        Initialize RAG tool

        Args:
            vector_db: Vector database backend
            embedding_model: Embedding model name
            db_config: Database configuration
            docs_path: Path to documents directory (for memory backend)
        """
        self.vector_db = vector_db
        self.embedding_model_name = embedding_model
        self.db_config = db_config or {}
        self.docs_path = docs_path

        # Load embedding model
        print(f"📥 Loading embedding model: {embedding_model}...")
        self.embedding_model = SentenceTransformer(embedding_model)
        print(f"✅ Embedding model loaded")

        # Initialize vector DB
        if vector_db == "memory":
            self._init_memory_db()
        elif vector_db == "oracle":
            self._init_oracle_db()
        elif vector_db == "pgvector":
            self._init_pgvector_db()
        elif vector_db == "qdrant":
            self._init_qdrant_db()

        print(f"✅ RAG Tool initialized with {vector_db} backend")

    def _init_memory_db(self):
        """Initialize in-memory vector database"""
        self.documents = []
        self.embeddings = []

        # Load documents from directory if provided
        if self.docs_path:
            self._load_documents_from_directory(self.docs_path)

    def _init_oracle_db(self):
        """Initialize Oracle AI Vector Search connection"""
        try:
            import oracledb

            connection_params = {
                'user': self.db_config.get('user', 'admin'),
                'password': self.db_config.get('password'),
                'dsn': self.db_config.get('dsn', 'localhost:1521/FREEPDB1')
            }

            self.db_connection = oracledb.connect(**connection_params)
            print(f"✅ Connected to Oracle AI Vector Search")

        except ImportError:
            print("⚠️  oracledb not installed. Install with: pip install oracledb")
            print("⚠️  Falling back to in-memory database")
            self._init_memory_db()
        except Exception as e:
            print(f"⚠️  Oracle connection failed: {e}")
            print("⚠️  Falling back to in-memory database")
            self._init_memory_db()

    def _init_pgvector_db(self):
        """Initialize pgvector (PostgreSQL) connection"""
        try:
            import psycopg2

            connection_params = {
                'host': self.db_config.get('host', 'localhost'),
                'port': self.db_config.get('port', 5432),
                'database': self.db_config.get('database', 'banking'),
                'user': self.db_config.get('user', 'postgres'),
                'password': self.db_config.get('password')
            }

            self.db_connection = psycopg2.connect(**connection_params)
            print(f"✅ Connected to pgvector")

        except ImportError:
            print("⚠️  psycopg2 not installed. Install with: pip install psycopg2-binary")
            print("⚠️  Falling back to in-memory database")
            self._init_memory_db()
        except Exception as e:
            print(f"⚠️  pgvector connection failed: {e}")
            print("⚠️  Falling back to in-memory database")
            self._init_memory_db()

    def _init_qdrant_db(self):
        """Initialize Qdrant connection"""
        try:
            from qdrant_client import QdrantClient

            host = self.db_config.get('host', 'localhost')
            port = self.db_config.get('port', 6333)

            self.db_connection = QdrantClient(host=host, port=port)
            print(f"✅ Connected to Qdrant at {host}:{port}")

        except ImportError:
            print("⚠️  qdrant-client not installed. Install with: pip install qdrant-client")
            print("⚠️  Falling back to in-memory database")
            self._init_memory_db()
        except Exception as e:
            print(f"⚠️  Qdrant connection failed: {e}")
            print("⚠️  Falling back to in-memory database")
            self._init_memory_db()

    def _load_documents_from_directory(self, docs_path: str):
        """Load documents from directory (for memory backend)"""
        docs_dir = Path(docs_path)
        if not docs_dir.exists():
            print(f"⚠️  Documents directory not found: {docs_path}")
            return

        # Load all JSON/TXT files
        for file_path in docs_dir.rglob("*"):
            if file_path.suffix in ['.json', '.txt', '.md']:
                try:
                    if file_path.suffix == '.json':
                        with open(file_path, 'r', encoding='utf-8') as f:
                            docs = json.load(f)
                            if isinstance(docs, list):
                                for doc in docs:
                                    self.add_document(doc)
                            else:
                                self.add_document(docs)
                    else:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            self.add_document({
                                'content': content,
                                'source': str(file_path),
                                'doc_type': 'text'
                            })
                except Exception as e:
                    print(f"⚠️  Failed to load {file_path}: {e}")

        print(f"✅ Loaded {len(self.documents)} documents")

    def add_document(self, doc: Dict):
        """
        Add document to vector database

        Args:
            doc: Document with fields:
                - content: str (required) - document text
                - doc_id: str (optional) - unique ID
                - doc_type: str (optional) - type (policy, faq, guide, etc.)
                - category: str (optional) - category
                - metadata: dict (optional) - additional metadata
        """
        if self.vector_db == "memory":
            # Generate embedding
            content = doc['content']
            embedding = self.embedding_model.encode(content, normalize_embeddings=True)

            # Add to memory
            self.documents.append(doc)
            self.embeddings.append(embedding)

        elif self.vector_db == "oracle":
            # Insert into Oracle
            self._add_to_oracle(doc)

        elif self.vector_db == "pgvector":
            # Insert into pgvector
            self._add_to_pgvector(doc)

        elif self.vector_db == "qdrant":
            # Insert into Qdrant
            self._add_to_qdrant(doc)

    def search(
        self,
        query: str,
        doc_types: Optional[List[str]] = None,
        categories: Optional[List[str]] = None,
        top_k: int = 5,
        min_score: float = 0.3
    ) -> List[Dict]:
        """
        Search documents

        Args:
            query: Search query
            doc_types: Filter by document types
            categories: Filter by categories
            top_k: Number of results
            min_score: Minimum similarity score (0-1)

        Returns:
            List of results with:
            - content: Document content
            - score: Similarity score
            - doc_id: Document ID
            - doc_type: Document type
            - category: Category
            - metadata: Additional metadata
        """
        # Generate query embedding
        query_embedding = self.embedding_model.encode(query, normalize_embeddings=True)

        if self.vector_db == "memory":
            return self._search_memory(query_embedding, doc_types, categories, top_k, min_score)
        elif self.vector_db == "oracle":
            return self._search_oracle(query_embedding, doc_types, categories, top_k, min_score)
        elif self.vector_db == "pgvector":
            return self._search_pgvector(query_embedding, doc_types, categories, top_k, min_score)
        elif self.vector_db == "qdrant":
            return self._search_qdrant(query_embedding, doc_types, categories, top_k, min_score)

    def _search_memory(
        self,
        query_embedding: np.ndarray,
        doc_types: Optional[List[str]],
        categories: Optional[List[str]],
        top_k: int,
        min_score: float
    ) -> List[Dict]:
        """Search in-memory database"""
        if not self.documents:
            return []

        # Compute similarities
        embeddings_matrix = np.array(self.embeddings)
        similarities = np.dot(embeddings_matrix, query_embedding)

        # Get top-k indices
        top_indices = np.argsort(similarities)[::-1]

        results = []
        for idx in top_indices:
            score = float(similarities[idx])

            # Check minimum score
            if score < min_score:
                break

            doc = self.documents[idx]

            # Apply filters
            if doc_types and doc.get('doc_type') not in doc_types:
                continue
            if categories and doc.get('category') not in categories:
                continue

            results.append({
                'content': doc.get('content', ''),
                'score': score,
                'doc_id': doc.get('doc_id', f'doc_{idx}'),
                'doc_type': doc.get('doc_type', 'unknown'),
                'category': doc.get('category', 'general'),
                'source': doc.get('source', 'unknown'),
                'metadata': doc.get('metadata', {})
            })

            if len(results) >= top_k:
                break

        return results

    def _search_oracle(self, query_embedding, doc_types, categories, top_k, min_score):
        """Search Oracle AI Vector Search"""
        # Placeholder - implement Oracle vector search SQL
        # See RAG_ARCHITECTURE.md for SQL examples
        return []

    def _search_pgvector(self, query_embedding, doc_types, categories, top_k, min_score):
        """Search pgvector"""
        # Placeholder - implement pgvector search
        return []

    def _search_qdrant(self, query_embedding, doc_types, categories, top_k, min_score):
        """Search Qdrant"""
        # Placeholder - implement Qdrant search
        return []

    def _add_to_oracle(self, doc):
        """Add document to Oracle (placeholder)"""
        pass

    def _add_to_pgvector(self, doc):
        """Add document to pgvector (placeholder)"""
        pass

    def _add_to_qdrant(self, doc):
        """Add document to Qdrant (placeholder)"""
        pass

    def format_results(self, results: List[Dict], max_content_length: int = 300) -> str:
        """Format search results for display"""
        if not results:
            return "Aucun document trouvé."

        output = []
        for i, result in enumerate(results, 1):
            content = result['content']
            if len(content) > max_content_length:
                content = content[:max_content_length] + "..."

            output.append(f"{i}. [{result['doc_type']}] {result.get('title', 'Document')} (score: {result['score']:.2f})")
            output.append(f"   {content}")
            output.append(f"   📁 {result.get('source', 'N/A')}")
            output.append("")

        return "\n".join(output)


# Test function
if __name__ == "__main__":
    # Initialize RAG tool with in-memory database
    rag = RAGTool(vector_db="memory")

    # Add sample documents
    sample_docs = [
        {
            'content': "La politique de crédit de la banque AFG stipule qu'un emprunteur ne peut pas avoir un taux d'endettement (DTI) supérieur à 40%. Les crédits immobiliers sont plafonnés à 25 ans.",
            'doc_id': 'policy_credit_001',
            'doc_type': 'policy',
            'category': 'crédit',
            'source': 'politique_credit_2025.pdf'
        },
        {
            'content': "Procédure KYC : Tous les clients doivent fournir une pièce d'identité valide, un justificatif de domicile de moins de 3 mois, et un justificatif de revenus. La vérification doit être effectuée dans les 48h.",
            'doc_id': 'proc_kyc_001',
            'doc_type': 'procedure',
            'category': 'compliance',
            'source': 'procedures_kyc.pdf'
        },
        {
            'content': "FAQ Virement : Les virements SEPA sont gratuits et prennent 1-2 jours ouvrés. Les virements internationaux coûtent 15€ et prennent 3-5 jours. Le montant maximum par virement est de 50,000 XOF.",
            'doc_id': 'faq_virement_001',
            'doc_type': 'faq',
            'category': 'virement',
            'source': 'faq_virements.md'
        }
    ]

    print("📥 Adding sample documents...")
    for doc in sample_docs:
        rag.add_document(doc)

    print("\n" + "="*60)
    print("🔍 Testing RAG search...\n")

    # Test search
    query = "quelle est la procédure KYC ?"
    results = rag.search(query, top_k=3)

    print(f"Query: {query}")
    print(f"\n✅ Found {len(results)} results\n")
    print(rag.format_results(results))

    # Test filtered search
    print("\n" + "="*60)
    print("🔍 Testing filtered search (doc_type=policy)...\n")

    results = rag.search("crédit immobilier", doc_types=['policy'], top_k=2)
    print(f"✅ Found {len(results)} results\n")
    print(rag.format_results(results))
