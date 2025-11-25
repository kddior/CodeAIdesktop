# -*- coding: utf-8 -*-
"""
Simple Flask Chat Interface - Direct LLM Connection
Bypasses complex components for quick testing
"""

from flask import Flask, render_template, request, jsonify, session
from flask_cors import CORS
import os
import logging
from datetime import datetime
import uuid
import requests

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'afg-bank-demo-key-2025')
CORS(app)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# LLM Server config
LLM_URL = "http://localhost:1234/v1/chat/completions"

# Simple conversation history
conversations = {}

def call_llm(messages, temperature=0.7, max_tokens=1000):
    """Call the LLM server directly"""
    try:
        response = requests.post(
            LLM_URL,
            json={
                "model": "qwen2.5-7b-instruct",
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens
            },
            headers={"Content-Type": "application/json"},
            timeout=60
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"LLM error: {e}")
        return f"Erreur de connexion au modele: {str(e)}"


@app.route('/')
def index():
    return render_template('chat.html')


@app.route('/test')
def test():
    return render_template('test.html')


@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json()
        user_message = data.get('message', '').strip()

        if not user_message:
            return jsonify({'error': 'Empty message'}), 400

        # Get or create session
        if 'session_id' not in session:
            session['session_id'] = str(uuid.uuid4())
        session_id = session['session_id']

        # Get conversation history
        if session_id not in conversations:
            conversations[session_id] = [
                {"role": "system", "content": "Tu es un assistant bancaire AFG Bank. Tu aides les clients avec leurs questions bancaires en francais. Sois poli, professionnel et concis."}
            ]

        # Add user message
        conversations[session_id].append({"role": "user", "content": user_message})

        logger.info(f"[{session_id[:8]}] User: {user_message}")

        # Call LLM
        response_text = call_llm(conversations[session_id])

        # Add assistant response to history
        conversations[session_id].append({"role": "assistant", "content": response_text})

        # Keep history manageable (last 10 messages)
        if len(conversations[session_id]) > 12:
            conversations[session_id] = conversations[session_id][:1] + conversations[session_id][-10:]

        logger.info(f"[{session_id[:8]}] Assistant: {response_text[:100]}...")

        return jsonify({
            'response': response_text,
            'timestamp': datetime.now().isoformat(),
            'session_id': session_id
        })

    except Exception as e:
        logger.error(f"Chat error: {e}", exc_info=True)
        return jsonify({
            'error': str(e),
            'response': 'Une erreur est survenue.'
        }), 500


@app.route('/api/clear', methods=['POST'])
def clear_history():
    session_id = session.get('session_id')
    if session_id and session_id in conversations:
        del conversations[session_id]
    session['session_id'] = str(uuid.uuid4())
    return jsonify({'status': 'success'})


@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'healthy',
        'llm_url': LLM_URL,
        'timestamp': datetime.now().isoformat()
    })


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    logger.info(f"Starting Simple AFG Bank Chat on http://localhost:{port}")
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
