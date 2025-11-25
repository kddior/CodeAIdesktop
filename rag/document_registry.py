# -*- coding: utf-8 -*-
"""
Document Registry - SQLite database for tracking RAG documents
Manages metadata for all uploaded/processed documents
"""

import sqlite3
import os
from datetime import datetime
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class DocumentRegistry:
    """
    SQLite-based document registry for multi-document RAG system
    Tracks all documents: tariffs, procedures, regulations, websites, etc.
    """

    def __init__(self, db_path: str = "rag/registry.db"):
        """
        Initialize document registry

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._init_db()
        logger.info(f"DocumentRegistry initialized at {db_path}")

    def _init_db(self):
        """Create database schema if it doesn't exist"""
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create documents table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                doc_id TEXT PRIMARY KEY,
                doc_name TEXT NOT NULL,
                doc_type TEXT NOT NULL,
                country TEXT DEFAULT 'CI',
                bank TEXT DEFAULT 'AFG Bank CI',
                source TEXT DEFAULT 'upload',
                file_path TEXT,
                file_size INTEGER,
                num_chunks INTEGER DEFAULT 0,
                status TEXT DEFAULT 'PENDING',
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                processed_at TIMESTAMP,
                metadata TEXT,
                content_summary TEXT
            )
        """)

        # Create indexes for common queries
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_doc_type ON documents(doc_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_status ON documents(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_bank ON documents(bank)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_country ON documents(country)")

        conn.commit()
        conn.close()
        logger.info("Database schema initialized")

    def add_document(self, doc_id: str, doc_name: str, doc_type: str,
                     file_path: str, **kwargs) -> None:
        """
        Add new document to registry

        Args:
            doc_id: Unique document identifier
            doc_name: Human-readable document name
            doc_type: Type of document ('tarif', 'procedure', 'regulation', 'website')
            file_path: Path to source file
            **kwargs: Additional metadata (country, bank, source, file_size)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO documents
                (doc_id, doc_name, doc_type, file_path, country, bank, source, file_size, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'PENDING')
            """, (
                doc_id,
                doc_name,
                doc_type,
                file_path,
                kwargs.get('country', 'CI'),
                kwargs.get('bank', 'AFG Bank CI'),
                kwargs.get('source', 'upload'),
                kwargs.get('file_size', 0)
            ))
            conn.commit()
            logger.info(f"Document added: {doc_id} ({doc_name})")
        except sqlite3.IntegrityError:
            logger.error(f"Document already exists: {doc_id}")
            raise ValueError(f"Document with ID '{doc_id}' already exists")
        finally:
            conn.close()

    def update_status(self, doc_id: str, status: str,
                     num_chunks: int = None, error: str = None,
                     content_summary: str = None) -> None:
        """
        Update document processing status

        Args:
            doc_id: Document identifier
            status: New status ('PENDING', 'PROCESSING', 'READY', 'FAILED')
            num_chunks: Number of chunks created (for READY status)
            error: Error message (for FAILED status)
            content_summary: Brief summary of document content (for READY status)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if status == 'READY':
            cursor.execute("""
                UPDATE documents
                SET status = ?, processed_at = ?, num_chunks = ?, error_message = NULL, content_summary = ?
                WHERE doc_id = ?
            """, (status, datetime.now(), num_chunks or 0, content_summary, doc_id))
        elif status == 'FAILED':
            cursor.execute("""
                UPDATE documents
                SET status = ?, error_message = ?
                WHERE doc_id = ?
            """, (status, error, doc_id))
        else:
            cursor.execute("""
                UPDATE documents
                SET status = ?
                WHERE doc_id = ?
            """, (status, doc_id))

        conn.commit()
        conn.close()
        logger.info(f"Document status updated: {doc_id} -> {status}")

    def get_document(self, doc_id: str) -> Optional[Dict]:
        """
        Get single document by ID

        Args:
            doc_id: Document identifier

        Returns:
            Document dict or None if not found
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM documents WHERE doc_id = ?", (doc_id,))
        row = cursor.fetchone()
        conn.close()

        return dict(row) if row else None

    def get_all(self, status: str = None) -> List[Dict]:
        """
        Get all documents, optionally filtered by status

        Args:
            status: Filter by status ('READY', 'FAILED', etc.) or None for all

        Returns:
            List of document dicts
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        if status:
            cursor.execute(
                "SELECT * FROM documents WHERE status = ? ORDER BY created_at DESC",
                (status,)
            )
        else:
            cursor.execute("SELECT * FROM documents ORDER BY created_at DESC")

        docs = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return docs

    def get_by_type(self, doc_type: str, status: str = 'READY') -> List[Dict]:
        """
        Get documents by type

        Args:
            doc_type: Document type to filter
            status: Status filter (default: 'READY')

        Returns:
            List of document dicts
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM documents WHERE doc_type = ? AND status = ? ORDER BY created_at DESC",
            (doc_type, status)
        )

        docs = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return docs

    def get_ready_documents(self) -> List[Dict]:
        """
        Get all successfully processed documents

        Returns:
            List of READY documents
        """
        return self.get_all(status='READY')

    def delete_document(self, doc_id: str) -> bool:
        """
        Remove document from registry

        Args:
            doc_id: Document identifier

        Returns:
            True if deleted, False if not found
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("DELETE FROM documents WHERE doc_id = ?", (doc_id,))
        deleted = cursor.rowcount > 0

        conn.commit()
        conn.close()

        if deleted:
            logger.info(f"Document deleted: {doc_id}")
        else:
            logger.warning(f"Document not found for deletion: {doc_id}")

        return deleted

    def get_stats(self) -> Dict:
        """
        Get registry statistics

        Returns:
            Dict with counts by status and type
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Count by status
        cursor.execute("SELECT status, COUNT(*) FROM documents GROUP BY status")
        by_status = dict(cursor.fetchall())

        # Count by type
        cursor.execute("SELECT doc_type, COUNT(*) FROM documents WHERE status = 'READY' GROUP BY doc_type")
        by_type = dict(cursor.fetchall())

        # Total chunks
        cursor.execute("SELECT SUM(num_chunks) FROM documents WHERE status = 'READY'")
        total_chunks = cursor.fetchone()[0] or 0

        conn.close()

        return {
            'total_documents': sum(by_status.values()),
            'by_status': by_status,
            'by_type': by_type,
            'total_chunks': total_chunks
        }


# Example usage and testing
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Initialize registry
    registry = DocumentRegistry("rag/registry.db")

    # Add test document
    registry.add_document(
        doc_id="test_tariff_001",
        doc_name="AFG Bank Tariffs 2025",
        doc_type="tarif",
        file_path="rag/documents/test_tariff_001/source.txt",
        country="CI",
        bank="AFG Bank CI"
    )

    # Update status
    registry.update_status("test_tariff_001", "READY", num_chunks=50)

    # Get all documents
    print("\nAll documents:")
    for doc in registry.get_all():
        print(f"  {doc['doc_id']}: {doc['doc_name']} ({doc['status']})")

    # Get stats
    print("\nRegistry stats:")
    stats = registry.get_stats()
    print(f"  Total documents: {stats['total_documents']}")
    print(f"  Total chunks: {stats['total_chunks']}")
    print(f"  By status: {stats['by_status']}")
    print(f"  By type: {stats['by_type']}")
