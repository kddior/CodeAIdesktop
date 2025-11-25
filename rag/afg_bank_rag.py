# -*- coding: utf-8 -*-
"""
AFG Bank RAG System
Vector embeddings with FAISS for fast document retrieval
"""

import os
import json
import pickle
from typing import List, Dict, Tuple
import numpy as np

# PDF parsing
try:
    import pdfplumber
except ImportError:
    pdfplumber = None
    print("[WARNING] pdfplumber not installed. Install with: pip install pdfplumber")

# Embeddings
from sentence_transformers import SentenceTransformer
import faiss

# BM25 for hybrid search
from rank_bm25 import BM25Okapi


class AFGBankRAG:
    """
    RAG system for AFG Bank documents
    - Indexes AFG Bank tariff PDF
    - Fast retrieval with FAISS
    - Returns relevant passages for banking questions
    """

    def __init__(
        self,
        document_path: str = "afg_bank_tariff.txt",
        index_path: str = "rag/afg_bank_index",
        embedding_model: str = "BAAI/bge-m3",
        chunk_size: int = 800,
        chunk_overlap: int = 160,
        top_k: int = 5
    ):
        """
        Args:
            document_path: Path to AFG Bank document (PDF or TXT)
            index_path: Path to save/load FAISS index
            embedding_model: Sentence transformer model name
            chunk_size: Characters per chunk
            chunk_overlap: Overlap between chunks
            top_k: Number of top results to return
        """
        self.document_path = document_path
        self.index_path = index_path
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.top_k = top_k

        # Initialize embedding model
        print(f"[RAG] Loading embedding model: {embedding_model}")
        self.embedding_model = SentenceTransformer(embedding_model)
        self.embedding_dim = self.embedding_model.get_sentence_embedding_dimension()

        # Initialize FAISS index (semantic search)
        self.index = None
        self.chunks = []  # Store text chunks
        self.metadata = []  # Store metadata for each chunk

        # Initialize BM25 index (keyword search)
        self.bm25 = None
        self.tokenized_chunks = []  # Tokenized chunks for BM25

        # Load or create index
        if os.path.exists(f"{index_path}.faiss"):
            self.load_index()
        else:
            print(f"[RAG] Index not found. Creating new index from {document_path}")
            self.create_index()

    def extract_text(self) -> str:
        """Extract text from AFG Bank document (PDF or TXT)"""
        if not os.path.exists(self.document_path):
            raise FileNotFoundError(f"Document not found: {self.document_path}")

        # Check file extension
        ext = os.path.splitext(self.document_path)[1].lower()

        if ext == '.txt':
            print(f"[RAG] Reading text file: {self.document_path}")
            with open(self.document_path, 'r', encoding='utf-8') as f:
                return f.read()

        elif ext == '.pdf':
            return self.extract_text_from_pdf()

        else:
            raise ValueError(f"Unsupported file format: {ext}. Use .txt or .pdf")

    def extract_text_from_pdf(self) -> str:
        """Extract text from AFG Bank PDF"""
        if not pdfplumber:
            raise ImportError("pdfplumber not installed. Install with: pip install pdfplumber")

        if not os.path.exists(self.document_path):
            raise FileNotFoundError(f"PDF not found: {self.document_path}")

        print(f"[RAG] Extracting text from {self.document_path}")
        full_text = ""

        with pdfplumber.open(self.document_path) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                text = page.extract_text()
                if text:
                    full_text += f"\n\n[Page {page_num}]\n{text}"

        print(f"[RAG] Extracted {len(full_text)} characters from {len(pdf.pages)} pages")
        return full_text

    def _extract_section_name(self, text: str) -> str:
        """Extract section name from text if present"""
        # Look for section headers like "=== SECTION NAME ==="
        lines = text.split('\n')
        for i, line in enumerate(lines[:5]):  # Check first 5 lines
            if '===' in line:
                # Next line might be the section name
                if i + 1 < len(lines):
                    section = lines[i + 1].strip()
                    if section and not '===' in section:
                        return section
            # Or the line itself might be the section
            stripped = line.strip('= \n')
            if stripped and len(stripped) < 100:  # Section names are typically short
                return stripped
        return "UNKNOWN"

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract key banking terms from text"""
        keywords = []
        text_lower = text.lower()

        # Banking keywords to extract
        key_terms = [
            'frais', 'tenue', 'compte', 'carte', 'visa', 'virement',
            'cheque', 'credit', 'taux', 'commission', 'gratuit',
            'xof', 'eur', 'usd', 'sica', 'uemoa', 'rtgs',
            'entreprise', 'pme', 'association', 'ong',
            'ouverture', 'cloture', 'depot', 'retrait'
        ]

        for term in key_terms:
            if term in text_lower:
                keywords.append(term)

        return keywords

    def chunk_text(self, text: str) -> List[Dict]:
        """
        Split text into semantic chunks with section awareness
        Returns list of dicts with 'text' and 'metadata'
        """
        chunks = []
        chunk_id = 0

        # Clean text: remove excessive decoration but preserve structure
        cleaned_text = text
        # Replace multiple equals signs with double newline for section breaks
        import re
        cleaned_text = re.sub(r'={50,}', '\n\n', cleaned_text)

        # Split by double newlines to identify sections
        sections = cleaned_text.split('\n\n')

        current_chunk = ""
        current_section = "UNKNOWN"
        start_pos = 0

        for section in sections:
            section = section.strip()
            if not section:
                continue

            # Check if this is a section header
            is_header = (
                len(section) < 100 and
                section.isupper() and
                '\n' not in section
            )

            if is_header:
                # Save current chunk if it exists
                if current_chunk.strip():
                    chunk_text = current_chunk.strip()
                    chunks.append({
                        'text': chunk_text,
                        'metadata': {
                            'chunk_id': chunk_id,
                            'start_pos': start_pos,
                            'end_pos': start_pos + len(chunk_text),
                            'section_name': current_section,
                            'keywords': self._extract_keywords(chunk_text),
                            'page_num': None
                        }
                    })
                    chunk_id += 1
                    start_pos += len(chunk_text)

                # Start new section
                current_section = section
                current_chunk = f"{section}\n\n"
            else:
                # Add to current chunk
                current_chunk += section + "\n\n"

                # If chunk gets too large, split it
                if len(current_chunk) > self.chunk_size:
                    # Find good break point
                    break_point = self.chunk_size

                    # Try to break at paragraph boundary
                    last_para = current_chunk[:break_point].rfind('\n\n')
                    if last_para > self.chunk_size // 2:
                        break_point = last_para
                    else:
                        # Try sentence boundary
                        last_period = current_chunk[:break_point].rfind('.')
                        if last_period > self.chunk_size // 2:
                            break_point = last_period + 1

                    # Save chunk
                    chunk_text = current_chunk[:break_point].strip()
                    chunks.append({
                        'text': chunk_text,
                        'metadata': {
                            'chunk_id': chunk_id,
                            'start_pos': start_pos,
                            'end_pos': start_pos + len(chunk_text),
                            'section_name': current_section,
                            'keywords': self._extract_keywords(chunk_text),
                            'page_num': None
                        }
                    })
                    chunk_id += 1
                    start_pos += break_point

                    # Keep overlap
                    overlap_start = max(0, break_point - self.chunk_overlap)
                    current_chunk = current_chunk[overlap_start:]

        # Don't forget the last chunk
        if current_chunk.strip():
            chunk_text = current_chunk.strip()
            chunks.append({
                'text': chunk_text,
                'metadata': {
                    'chunk_id': chunk_id,
                    'start_pos': start_pos,
                    'end_pos': start_pos + len(chunk_text),
                    'section_name': current_section,
                    'keywords': self._extract_keywords(chunk_text),
                    'page_num': None
                }
            })

        print(f"[RAG] Created {len(chunks)} semantic chunks (size={self.chunk_size}, overlap={self.chunk_overlap})")
        return chunks

    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenizer for BM25"""
        # Convert to lowercase and split on whitespace and punctuation
        import re
        # Keep numbers and letters, split on other chars
        tokens = re.findall(r'\w+', text.lower())
        return tokens

    def _normalize_query(self, query: str) -> str:
        """
        Normalize query for better matching
        Handles common synonyms and accent variations
        """
        import unicodedata

        # Normalize to lowercase first
        normalized = query.lower()

        # Common synonym mapping for AFG Bank queries
        synonyms = {
            'fermeture': 'cloture',
            'clôture': 'cloture',  # Normalize to unaccented version for consistency
            'carte gold': 'carte visa',
            'cloture': 'cloture',  # Keep unaccented
        }

        # Apply synonym replacements
        for old, new in synonyms.items():
            normalized = normalized.replace(old, new)

        # Remove accents for better matching (optional, but helps with variations)
        # This ensures 'clôture', 'cloture' both match the same way
        normalized_nfd = unicodedata.normalize('NFD', normalized)
        normalized = ''.join(char for char in normalized_nfd if unicodedata.category(char) != 'Mn')

        return normalized

    def create_embeddings(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings for list of texts"""
        print(f"[RAG] Generating embeddings for {len(texts)} chunks...")
        embeddings = self.embedding_model.encode(
            texts,
            show_progress_bar=False,
            normalize_embeddings=True
        )
        return embeddings

    def create_index(self):
        """Create FAISS and BM25 indices from document"""
        # Extract text
        full_text = self.extract_text()

        # Chunk text
        chunked_docs = self.chunk_text(full_text)
        self.chunks = [doc['text'] for doc in chunked_docs]
        self.metadata = [doc['metadata'] for doc in chunked_docs]

        # Generate embeddings for FAISS
        embeddings = self.create_embeddings(self.chunks)

        # Create FAISS index (semantic search)
        print(f"[RAG] Creating FAISS index (dimension={self.embedding_dim})")
        self.index = faiss.IndexFlatIP(self.embedding_dim)  # Inner product (cosine similarity)
        self.index.add(embeddings.astype('float32'))

        # Create BM25 index (keyword search)
        print(f"[RAG] Creating BM25 index for keyword search")
        self.tokenized_chunks = [self._tokenize(chunk) for chunk in self.chunks]
        self.bm25 = BM25Okapi(self.tokenized_chunks)

        # Save index
        self.save_index()
        print(f"[RAG] Hybrid index created with {self.index.ntotal} vectors (FAISS + BM25)")

    def save_index(self):
        """Save FAISS, BM25 indices and metadata to disk"""
        os.makedirs(os.path.dirname(self.index_path), exist_ok=True)

        # Save FAISS index
        faiss.write_index(self.index, f"{self.index_path}.faiss")

        # Save chunks, metadata, and BM25 index
        with open(f"{self.index_path}.pkl", 'wb') as f:
            pickle.dump({
                'chunks': self.chunks,
                'metadata': self.metadata,
                'tokenized_chunks': self.tokenized_chunks,
                'bm25': self.bm25
            }, f)

        print(f"[RAG] Hybrid index saved to {self.index_path}")

    def load_index(self):
        """Load FAISS, BM25 indices and metadata from disk"""
        print(f"[RAG] Loading hybrid index from {self.index_path}")

        # Load FAISS index
        self.index = faiss.read_index(f"{self.index_path}.faiss")

        # Load chunks, metadata, and BM25 index
        with open(f"{self.index_path}.pkl", 'rb') as f:
            data = pickle.load(f)
            self.chunks = data['chunks']
            self.metadata = data['metadata']
            self.tokenized_chunks = data.get('tokenized_chunks', [])
            self.bm25 = data.get('bm25', None)

        # If BM25 not in saved data (old index), create it
        if not self.bm25 and self.chunks:
            print(f"[RAG] BM25 index not found, creating from loaded chunks...")
            self.tokenized_chunks = [self._tokenize(chunk) for chunk in self.chunks]
            self.bm25 = BM25Okapi(self.tokenized_chunks)

        print(f"[RAG] Hybrid index loaded with {self.index.ntotal} vectors (FAISS + BM25)")

    def retrieve(self, query: str, top_k: int = None, use_hybrid: bool = True) -> List[Dict]:
        """
        Retrieve top-k most relevant chunks using hybrid search (semantic + keyword)

        Args:
            query: User query
            top_k: Number of results (default: self.top_k)
            use_hybrid: If True, use hybrid search (semantic + BM25). If False, semantic only.

        Returns:
            List of dicts with 'text', 'score', 'metadata'
        """
        if top_k is None:
            top_k = self.top_k

        # Apply synonym normalization to query
        normalized_query = self._normalize_query(query)

        if not use_hybrid or not self.bm25:
            # Fall back to semantic-only search
            return self._retrieve_semantic(normalized_query, top_k)

        # HYBRID SEARCH: Combine semantic (FAISS) and keyword (BM25)

        # 1. Semantic search (FAISS) - get top 2*top_k candidates
        semantic_results = self._retrieve_semantic(normalized_query, top_k * 2)

        # 2. Keyword search (BM25) - get top 2*top_k candidates
        bm25_results = self._retrieve_bm25(normalized_query, top_k * 2)

        # 3. Merge and rerank using score fusion
        hybrid_results = self._fuse_results(semantic_results, bm25_results, top_k)

        return hybrid_results

    def _retrieve_semantic(self, query: str, top_k: int) -> List[Dict]:
        """Semantic search using FAISS"""
        # Generate query embedding
        query_embedding = self.embedding_model.encode(
            [query],
            normalize_embeddings=True,
            show_progress_bar=False
        ).astype('float32')

        # Search FAISS index
        scores, indices = self.index.search(query_embedding, min(top_k, self.index.ntotal))

        # Format results
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < len(self.chunks):
                results.append({
                    'text': self.chunks[idx],
                    'score': float(score),
                    'metadata': self.metadata[idx],
                    'source': 'semantic'
                })

        return results

    def _retrieve_bm25(self, query: str, top_k: int) -> List[Dict]:
        """Keyword search using BM25"""
        # Tokenize query
        query_tokens = self._tokenize(query)

        # Get BM25 scores for all documents
        bm25_scores = self.bm25.get_scores(query_tokens)

        # Get top-k indices
        top_indices = np.argsort(bm25_scores)[::-1][:top_k]

        # Format results
        results = []
        for idx in top_indices:
            if idx < len(self.chunks):
                results.append({
                    'text': self.chunks[idx],
                    'score': float(bm25_scores[idx]),
                    'metadata': self.metadata[idx],
                    'source': 'bm25'
                })

        return results

    def _fuse_results(self, semantic_results: List[Dict], bm25_results: List[Dict], top_k: int) -> List[Dict]:
        """
        Fuse semantic and BM25 results using Reciprocal Rank Fusion (RRF)
        RRF is robust and doesn't require score normalization
        """
        k = 60  # RRF constant (standard value)

        # Build rank dictionaries
        chunk_scores = {}

        # Add semantic results
        for rank, result in enumerate(semantic_results):
            chunk_id = result['metadata']['chunk_id']
            rrf_score = 1.0 / (k + rank + 1)
            if chunk_id not in chunk_scores:
                chunk_scores[chunk_id] = {
                    'text': result['text'],
                    'metadata': result['metadata'],
                    'semantic_score': result['score'],
                    'bm25_score': 0.0,
                    'rrf_score': 0.0,
                    'semantic_rank': rank + 1,
                    'bm25_rank': None
                }
            chunk_scores[chunk_id]['rrf_score'] += rrf_score * 0.6  # 60% weight for semantic

        # Add BM25 results
        for rank, result in enumerate(bm25_results):
            chunk_id = result['metadata']['chunk_id']
            rrf_score = 1.0 / (k + rank + 1)
            if chunk_id not in chunk_scores:
                chunk_scores[chunk_id] = {
                    'text': result['text'],
                    'metadata': result['metadata'],
                    'semantic_score': 0.0,
                    'bm25_score': result['score'],
                    'rrf_score': 0.0,
                    'semantic_rank': None,
                    'bm25_rank': rank + 1
                }
            else:
                chunk_scores[chunk_id]['bm25_score'] = result['score']
                chunk_scores[chunk_id]['bm25_rank'] = rank + 1

            chunk_scores[chunk_id]['rrf_score'] += rrf_score * 0.4  # 40% weight for BM25

        # Sort by RRF score and return top-k
        sorted_chunks = sorted(chunk_scores.items(), key=lambda x: x[1]['rrf_score'], reverse=True)

        results = []
        for chunk_id, data in sorted_chunks[:top_k]:
            results.append({
                'text': data['text'],
                'score': data['rrf_score'],  # Combined RRF score
                'metadata': data['metadata'],
                'semantic_score': data['semantic_score'],
                'bm25_score': data['bm25_score'],
                'source': 'hybrid'
            })

        return results

    def format_results_for_llm(self, results: List[Dict]) -> str:
        """
        Format retrieval results for LLM context

        Args:
            results: List of retrieval results

        Returns:
            Formatted string for LLM prompt
        """
        if not results:
            return "[Aucune information trouvée dans la documentation AFG Bank]"

        formatted = "=== DOCUMENTATION AFG BANK (passages pertinents) ===\n\n"

        for i, result in enumerate(results, 1):
            score = result['score']
            text = result['text']
            metadata = result['metadata']

            formatted += f"[Passage {i} - Score: {score:.3f}"
            if metadata.get('section_name'):
                formatted += f" - Section: {metadata['section_name']}"
            if metadata.get('page_num'):
                formatted += f" - Page {metadata['page_num']}"
            formatted += "]\n"
            formatted += f"{text}\n\n"

        formatted += "=== FIN DOCUMENTATION ===\n"
        return formatted

    def answer_question(self, question: str, top_k: int = None) -> Dict:
        """
        Answer banking question using RAG

        Args:
            question: User question
            top_k: Number of results to retrieve

        Returns:
            Dict with 'question', 'results', 'formatted_context'
        """
        results = self.retrieve(question, top_k)
        formatted_context = self.format_results_for_llm(results)

        return {
            'question': question,
            'results': results,
            'formatted_context': formatted_context
        }


def test_rag():
    """Test RAG system with sample questions"""
    print("\n" + "="*80)
    print("  AFG BANK RAG SYSTEM - TEST")
    print("="*80 + "\n")

    # Initialize RAG
    rag = AFGBankRAG(
        document_path="afg_bank_tariff.txt",
        index_path="rag/afg_bank_index",
        top_k=3
    )

    # Test questions
    test_questions = [
        "C'est quoi les frais de tenue de compte ?",
        "Combien coûte un chèque de banque ?",
        "Quel est le taux d'intérêt pour un crédit ?",
        "Frais de virement SICA UEMOA",
        "Carte Visa Business tarif"
    ]

    for question in test_questions:
        print(f"\n{'='*80}")
        print(f"Question: {question}")
        print('='*80)

        result = rag.answer_question(question)

        print(f"\nTop {len(result['results'])} résultats:\n")
        for i, res in enumerate(result['results'], 1):
            print(f"{i}. [Score: {res['score']:.3f}]")
            print(f"   {res['text'][:150]}...")
            print()


if __name__ == "__main__":
    test_rag()
