# -*- coding: utf-8 -*-
"""
RAG Manager - Multi-document RAG orchestration
Manages multiple document indexes and provides unified retrieval
"""

import os
import time
import shutil
from typing import List, Dict, Optional
import logging
import numpy as np

from rag.document_registry import DocumentRegistry
from rag.afg_bank_rag import AFGBankRAG

logger = logging.getLogger(__name__)


class RAGManager:
    """
    Multi-document RAG manager
    - Manages document registry (SQLite)
    - Creates per-document FAISS+BM25 indexes
    - Queries all indexes in parallel
    - Merges results using RRF (Reciprocal Rank Fusion)
    """

    def __init__(self,
                 registry_path: str = "rag/registry.db",
                 documents_dir: str = "rag/documents",
                 embedding_model: str = "BAAI/bge-m3"):
        """
        Initialize RAG Manager

        Args:
            registry_path: Path to SQLite registry database
            documents_dir: Directory containing per-document folders
            embedding_model: Embedding model name
        """
        self.registry = DocumentRegistry(registry_path)
        self.documents_dir = documents_dir
        self.embedding_model = embedding_model

        # Cache of loaded RAG indexes {doc_id: AFGBankRAG}
        self.rag_indexes = {}

        # Ensure documents directory exists
        os.makedirs(documents_dir, exist_ok=True)

        logger.info(f"RAGManager initialized (documents_dir={documents_dir})")

    def upload_and_ingest(self,
                         file_path: str,
                         doc_name: str,
                         doc_type: str,
                         country: str = "CI",
                         bank: str = "AFG Bank CI",
                         source: str = "upload") -> str:
        """
        Upload and process a document

        Args:
            file_path: Path to uploaded file (PDF or TXT)
            doc_name: Human-readable document name
            doc_type: Type ('tarif', 'procedure', 'regulation', 'website')
            country: Country code (CI, SN, BJ, etc.)
            bank: Bank name
            source: Source type ('upload', 'website', 'manual')

        Returns:
            doc_id: Generated document ID

        Raises:
            Exception: If processing fails
        """
        # Generate unique doc_id
        timestamp = int(time.time())
        doc_id = f"{doc_type}_{timestamp}"

        # Get file size
        file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0

        logger.info(f"Starting ingestion: {doc_id} ({doc_name})")

        try:
            # 1. Add to registry
            self.registry.add_document(
                doc_id=doc_id,
                doc_name=doc_name,
                doc_type=doc_type,
                file_path=file_path,
                country=country,
                bank=bank,
                source=source,
                file_size=file_size
            )

            # 2. Create document directory
            doc_dir = os.path.join(self.documents_dir, doc_id)
            os.makedirs(doc_dir, exist_ok=True)

            # 3. Copy source file to document directory
            source_file = os.path.join(doc_dir, "source" + os.path.splitext(file_path)[1])
            shutil.copy2(file_path, source_file)

            # 4. Update status to PROCESSING
            self.registry.update_status(doc_id, "PROCESSING")

            # 5. Create RAG index for this document
            index_path = os.path.join(doc_dir, "index")

            rag = AFGBankRAG(
                document_path=source_file,
                index_path=index_path,
                embedding_model=self.embedding_model,
                chunk_size=800,
                chunk_overlap=160,
                top_k=5
            )

            # Count chunks created
            num_chunks = len(rag.chunks) if hasattr(rag, 'chunks') else 0

            # 5.5 Generate content summary (extractive: first 3 chunks)
            content_summary = self._generate_content_summary(rag, doc_name, doc_type)

            # 6. Update status to READY
            self.registry.update_status(doc_id, "READY", num_chunks=num_chunks,
                                      content_summary=content_summary)

            # 7. Cache the RAG index
            self.rag_indexes[doc_id] = rag

            logger.info(f"Document ingested successfully: {doc_id} ({num_chunks} chunks)")
            return doc_id

        except Exception as e:
            logger.error(f"Ingestion failed for {doc_id}: {e}", exc_info=True)
            self.registry.update_status(doc_id, "FAILED", error=str(e))
            raise

    def load_document_index(self, doc_id: str) -> Optional[AFGBankRAG]:
        """
        Load a document's RAG index into memory

        Args:
            doc_id: Document identifier

        Returns:
            AFGBankRAG instance or None if failed
        """
        # Check cache first
        if doc_id in self.rag_indexes:
            return self.rag_indexes[doc_id]

        # Get document metadata
        doc = self.registry.get_document(doc_id)
        if not doc or doc['status'] != 'READY':
            logger.warning(f"Document not ready: {doc_id}")
            return None

        # Load index from disk
        doc_dir = os.path.join(self.documents_dir, doc_id)
        index_path = os.path.join(doc_dir, "index")
        source_file = os.path.join(doc_dir, "source" + os.path.splitext(doc['file_path'])[1])

        if not os.path.exists(f"{index_path}.faiss"):
            logger.error(f"Index not found for {doc_id}")
            return None

        try:
            rag = AFGBankRAG(
                document_path=source_file,
                index_path=index_path,
                embedding_model=self.embedding_model
            )
            self.rag_indexes[doc_id] = rag
            logger.info(f"Loaded index for {doc_id}")
            return rag

        except Exception as e:
            logger.error(f"Failed to load index for {doc_id}: {e}")
            return None

    def retrieve_multi_document(self,
                                query: str,
                                top_k: int = 5,
                                doc_filter: Dict = None) -> List[Dict]:
        """
        Retrieve from multiple documents using hybrid search + cross-document RRF

        Args:
            query: User query
            top_k: Number of final results to return
            doc_filter: Optional filters {'doc_type': ['tarif'], 'country': ['CI']}

        Returns:
            List of ranked chunks with metadata from all matching documents
        """
        # Get all ready documents
        ready_docs = self.registry.get_ready_documents()

        # Apply filters
        if doc_filter:
            filtered_docs = []
            for doc in ready_docs:
                match = True
                for key, allowed_values in doc_filter.items():
                    if doc.get(key) not in allowed_values:
                        match = False
                        break
                if match:
                    filtered_docs.append(doc)
            ready_docs = filtered_docs

        if not ready_docs:
            logger.warning("No documents available for retrieval")
            return []

        logger.info(f"Querying {len(ready_docs)} documents: {query}")

        # Retrieve from each document
        all_results = []
        for doc in ready_docs:
            doc_id = doc['doc_id']

            # Load index
            rag = self.load_document_index(doc_id)
            if not rag:
                continue

            # Retrieve from this document
            try:
                doc_results = rag.retrieve(query, top_k=top_k * 2)

                # Add document metadata to each chunk
                for result in doc_results:
                    result['metadata']['doc_id'] = doc_id
                    result['metadata']['doc_name'] = doc['doc_name']
                    result['metadata']['doc_type'] = doc['doc_type']
                    result['metadata']['country'] = doc['country']
                    result['metadata']['bank'] = doc['bank']

                all_results.extend(doc_results)

            except Exception as e:
                logger.error(f"Retrieval failed for {doc_id}: {e}")
                continue

        # Merge results using RRF (cross-document ranking)
        merged_results = self._rrf_fusion_cross_document(all_results, top_k)

        logger.info(f"Retrieved {len(merged_results)} results from {len(ready_docs)} documents")
        return merged_results

    def _rrf_fusion_cross_document(self, results: List[Dict], top_k: int) -> List[Dict]:
        """
        Reciprocal Rank Fusion across multiple documents
        Ensures fair ranking even if documents have different score scales

        Args:
            results: All results from all documents
            top_k: Number of results to return

        Returns:
            Top-k re-ranked results
        """
        if not results:
            return []

        # Group by document
        by_doc = {}
        for result in results:
            doc_id = result['metadata']['doc_id']
            if doc_id not in by_doc:
                by_doc[doc_id] = []
            by_doc[doc_id].append(result)

        # Sort each document's results by score
        for doc_id in by_doc:
            by_doc[doc_id].sort(key=lambda x: x['score'], reverse=True)

        # RRF constant
        k = 60

        # Compute RRF scores
        rrf_scores = {}
        for doc_id, doc_results in by_doc.items():
            for rank, result in enumerate(doc_results):
                chunk_key = (doc_id, result['metadata']['chunk_id'])
                rrf_score = 1.0 / (k + rank + 1)

                if chunk_key not in rrf_scores:
                    rrf_scores[chunk_key] = {
                        'result': result,
                        'rrf_score': 0.0
                    }
                rrf_scores[chunk_key]['rrf_score'] += rrf_score

        # Sort by RRF score
        ranked = sorted(rrf_scores.values(), key=lambda x: x['rrf_score'], reverse=True)

        # Return top-k with updated scores
        final_results = []
        for item in ranked[:top_k]:
            result = item['result'].copy()
            result['score'] = item['rrf_score']  # Replace with RRF score
            result['original_score'] = item['result']['score']  # Keep original
            final_results.append(result)

        return final_results

    def format_results_for_llm(self, results: List[Dict]) -> str:
        """
        Format multi-document results for LLM prompt

        Args:
            results: Retrieval results with metadata

        Returns:
            Formatted context string
        """
        if not results:
            return "[Aucune information trouvée dans la documentation]"

        formatted = "=== DOCUMENTATION BANCAIRE (passages pertinents de plusieurs documents) ===\n\n"

        for i, result in enumerate(results, 1):
            score = result['score']
            text = result['text']
            meta = result['metadata']

            formatted += f"[Passage {i} - Score: {score:.3f}]\n"
            formatted += f"Source: {meta.get('doc_name', 'N/A')} ({meta.get('doc_type', 'N/A')})\n"

            if meta.get('section_name'):
                formatted += f"Section: {meta['section_name']}\n"

            formatted += f"Contenu:\n{text}\n\n"
            formatted += "-" * 80 + "\n\n"

        formatted += "=== FIN DOCUMENTATION ===\n"
        return formatted

    def delete_document(self, doc_id: str) -> bool:
        """
        Delete a document and its index

        Args:
            doc_id: Document identifier

        Returns:
            True if deleted, False if not found
        """
        # Get document info
        doc = self.registry.get_document(doc_id)
        if not doc:
            return False

        logger.info(f"Deleting document: {doc_id}")

        try:
            # Remove from cache
            if doc_id in self.rag_indexes:
                del self.rag_indexes[doc_id]

            # Delete files
            doc_dir = os.path.join(self.documents_dir, doc_id)
            if os.path.exists(doc_dir):
                shutil.rmtree(doc_dir)

            # Remove from registry
            self.registry.delete_document(doc_id)

            logger.info(f"Document deleted: {doc_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete document {doc_id}: {e}")
            return False

    def get_stats(self) -> Dict:
        """Get system statistics"""
        return self.registry.get_stats()

    def _generate_content_summary(self, rag: AFGBankRAG, doc_name: str, doc_type: str) -> str:
        """
        Generate a brief content summary for LLM context
        Uses extractive summarization: samples first 3-5 chunks

        Args:
            rag: RAG instance with loaded chunks
            doc_name: Document name
            doc_type: Document type

        Returns:
            Brief summary string
        """
        if not hasattr(rag, 'chunks') or not rag.chunks:
            return f"Document {doc_type}: {doc_name}"

        # Sample first 3 chunks (or fewer if document is small)
        sample_size = min(3, len(rag.chunks))
        sample_chunks = rag.chunks[:sample_size]

        # Extract key topics (simple keyword extraction)
        all_text = " ".join(sample_chunks).lower()

        # Type-specific keywords to look for
        keywords_by_type = {
            'tarif': ['frais', 'tarif', 'prix', 'coût', 'montant', 'commission', 'carte', 'virement', 'crédit'],
            'procedure': ['procédure', 'étapes', 'comment', 'guide', 'mode d\'emploi', 'tutoriel'],
            'general': ['règlement', 'condition', 'modalité', 'service', 'banque'],
            'mobile': ['mobile', 'application', 'app', 'smartphone', 'connexion'],
            'credit': ['crédit', 'prêt', 'emprunt', 'financement', 'taux', 'durée']
        }

        # Find matching keywords
        relevant_keywords = keywords_by_type.get(doc_type, [])
        found_topics = [kw for kw in relevant_keywords if kw in all_text]

        # Build summary
        if found_topics:
            topics_str = ", ".join(found_topics[:5])  # Top 5 topics
            summary = f"Contient: {topics_str}"
        else:
            # Fallback: use first 150 chars of first chunk
            preview = sample_chunks[0][:150].replace('\n', ' ')
            summary = f"Aperçu: {preview}..."

        return summary


# Testing
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    manager = RAGManager()

    print("RAG Manager initialized")
    print(f"Stats: {manager.get_stats()}")
