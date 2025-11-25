# -*- coding: utf-8 -*-
"""
Flask Web Interface for AFG Bank Assistant
ChatGPT-style modern interface + Document management
"""

from flask import Flask, render_template, request, jsonify, session
from flask_cors import CORS
from werkzeug.utils import secure_filename
import os
import sys
import logging
from datetime import datetime
import uuid

# Import banking assistant
from banking_assistant_v4_dual_qwen import BankingAssistantV4

# Import RAG Manager for document management
from rag.rag_manager import RAGManager

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'afg-bank-demo-key-2025')
CORS(app)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global instances (initialized on first request)
assistant = None
rag_manager = None

# Upload configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'txt', 'pdf'}
MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB max

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_assistant():
    """Get or create banking assistant instance"""
    global assistant
    if assistant is None:
        logger.info("Initializing Banking Assistant...")
        assistant = BankingAssistantV4(
            enable_rag=True
        )
        logger.info("Banking Assistant initialized successfully")
    return assistant

def get_rag_manager():
    """Get or create RAG manager instance"""
    global rag_manager
    if rag_manager is None:
        logger.info("Initializing RAG Manager...")
        rag_manager = RAGManager()
        logger.info("RAG Manager initialized successfully")
    return rag_manager


@app.route('/')
def index():
    """Main chat interface"""
    return render_template('chat.html')


@app.route('/documents')
def documents():
    """Document management interface"""
    return render_template('documents.html')


@app.route('/test')
def test():
    """Simple test page for debugging"""
    return render_template('test.html')


@app.route('/api/chat', methods=['POST'])
def chat():
    """Handle chat messages"""
    try:
        data = request.get_json()
        user_message = data.get('message', '').strip()

        if not user_message:
            return jsonify({'error': 'Empty message'}), 400

        # Get or create session ID
        if 'session_id' not in session:
            session['session_id'] = str(uuid.uuid4())

        session_id = session['session_id']
        logger.info(f"[{session_id}] User: {user_message}")

        # Get assistant and generate response
        asst = get_assistant()
        result = asst.chat(session_id, user_message)

        # Extract response text from result dict
        if isinstance(result, dict):
            response = result.get('response', str(result))
        else:
            response = str(result)

        logger.info(f"[{session_id}] Assistant: {response[:100]}...")

        return jsonify({
            'response': response,
            'timestamp': datetime.now().isoformat(),
            'session_id': session_id
        })

    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}", exc_info=True)
        return jsonify({
            'error': 'Une erreur est survenue. Veuillez réessayer.',
            'details': str(e)
        }), 500


@app.route('/api/clear', methods=['POST'])
def clear_history():
    """Clear conversation history"""
    try:
        session_id = session.get('session_id')
        if session_id:
            asst = get_assistant()
            if hasattr(asst, 'clear_history'):
                asst.clear_history(session_id)
            logger.info(f"[{session_id}] Conversation history cleared")

        # Create new session
        session['session_id'] = str(uuid.uuid4())

        return jsonify({
            'status': 'success',
            'message': 'Conversation réinitialisée'
        })

    except Exception as e:
        logger.error(f"Error clearing history: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'assistant_initialized': assistant is not None,
        'rag_manager_initialized': rag_manager is not None,
        'timestamp': datetime.now().isoformat()
    })


# ========== DOCUMENT MANAGEMENT ENDPOINTS ==========

@app.route('/api/documents', methods=['GET'])
def list_documents():
    """List all documents"""
    try:
        manager = get_rag_manager()
        docs = manager.registry.get_all()

        # Format for frontend
        documents = []
        for doc in docs:
            documents.append({
                'doc_id': doc['doc_id'],
                'doc_name': doc['doc_name'],
                'doc_type': doc['doc_type'],
                'country': doc['country'],
                'bank': doc['bank'],
                'status': doc['status'],
                'num_chunks': doc['num_chunks'],
                'created_at': doc['created_at'],
                'file_size': doc['file_size'],
                'error_message': doc['error_message']
            })

        return jsonify({
            'documents': documents,
            'stats': manager.get_stats()
        })

    except Exception as e:
        logger.error(f"Error listing documents: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/documents/upload', methods=['POST'])
def upload_document():
    """Upload and process a new document"""
    try:
        # Check if file is present
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400

        file = request.files['file']

        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        if not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file type. Only PDF and TXT allowed.'}), 400

        # Get metadata from form
        doc_name = request.form.get('doc_name', file.filename)
        doc_type = request.form.get('doc_type', 'tarif')
        country = request.form.get('country', 'CI')
        bank = request.form.get('bank', 'AFG Bank CI')

        # Save uploaded file
        filename = secure_filename(file.filename)
        timestamp = int(datetime.now().timestamp())
        unique_filename = f"{timestamp}_{filename}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)

        file.save(file_path)
        logger.info(f"File uploaded: {file_path}")

        # Process document
        manager = get_rag_manager()
        doc_id = manager.upload_and_ingest(
            file_path=file_path,
            doc_name=doc_name,
            doc_type=doc_type,
            country=country,
            bank=bank,
            source='upload'
        )

        # Clean up uploaded file (already copied to documents dir)
        os.remove(file_path)

        return jsonify({
            'status': 'success',
            'doc_id': doc_id,
            'message': f'Document "{doc_name}" uploaded and processed successfully'
        })

    except Exception as e:
        logger.error(f"Error uploading document: {e}", exc_info=True)
        return jsonify({
            'error': 'Failed to process document',
            'details': str(e)
        }), 500


@app.route('/api/documents/<doc_id>', methods=['DELETE'])
def delete_document(doc_id):
    """Delete a document"""
    try:
        manager = get_rag_manager()
        success = manager.delete_document(doc_id)

        if success:
            return jsonify({
                'status': 'success',
                'message': f'Document {doc_id} deleted'
            })
        else:
            return jsonify({'error': 'Document not found'}), 404

    except Exception as e:
        logger.error(f"Error deleting document {doc_id}: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/documents/stats', methods=['GET'])
def get_document_stats():
    """Get document statistics"""
    try:
        manager = get_rag_manager()
        stats = manager.get_stats()
        return jsonify(stats)

    except Exception as e:
        logger.error(f"Error getting stats: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    # Run Flask app
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'False').lower() == 'true'

    logger.info(f"Starting AFG Bank Assistant on http://localhost:{port}")
    logger.info("Press Ctrl+C to stop")

    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug,
        threaded=True  # Important for concurrent requests
    )
