# -*- coding: utf-8 -*-
"""
AFG Bank Assistant - Streamlit Testing Interface
Test banking logic, intents, and LLM responses
"""

import streamlit as st
import requests
import json
from datetime import datetime

# Page configuration
st.set_page_config(
    page_title="AFG Bank Assistant - Test",
    page_icon="🏦",
    layout="wide"
)

# LLM Server configuration
LLM_URL = "http://localhost:1234/v1/chat/completions"
MODEL_NAME = "qwen2.5-7b-instruct"

# Banking system prompt
SYSTEM_PROMPT = """Tu es un assistant bancaire AFG Bank professionnel. Tu aides les clients avec:
- Consultation de solde (CONSULTER_SOLDE)
- Virements (FAIRE_VIREMENT)
- Simulation de credit (SIMULATION_CREDIT)
- Releves de compte (OBTENIR_RELEVE)
- Discussion generale sur les comptes (DISCUSSION_COMPTE)

Reponds en francais, sois poli et professionnel. Pour les operations bancaires, demande les informations necessaires:
- Virement: montant, devise (XOF/EUR/USD), beneficiaire, motif
- Credit: montant, duree en mois, taux d'interet
"""

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "test_results" not in st.session_state:
    st.session_state.test_results = []


def call_llm(messages, temperature=0.7, max_tokens=1000):
    """Call the LLM server"""
    try:
        full_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + messages

        response = requests.post(
            LLM_URL,
            json={
                "model": MODEL_NAME,
                "messages": full_messages,
                "temperature": temperature,
                "max_tokens": max_tokens
            },
            headers={"Content-Type": "application/json"},
            timeout=60
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"], None
    except requests.exceptions.ConnectionError:
        return None, "Erreur: Impossible de se connecter au serveur LLM (port 1234)"
    except Exception as e:
        return None, f"Erreur: {str(e)}"


def check_llm_status():
    """Check if LLM server is running"""
    try:
        response = requests.get("http://localhost:1234/v1/models", timeout=5)
        if response.status_code == 200:
            models = response.json()
            return True, models.get("data", [{}])[0].get("id", "Unknown")
        return False, "Server responded but no models"
    except:
        return False, "Server not running"


# Sidebar - Server Status & Test Cases
with st.sidebar:
    st.title("🏦 AFG Bank Test")

    # Server status
    st.subheader("Status du serveur")
    status, model = check_llm_status()
    if status:
        st.success(f"✅ LLM: {model}")
    else:
        st.error(f"❌ LLM: {model}")

    st.divider()

    # Quick test cases
    st.subheader("🧪 Cas de test rapides")

    test_cases = {
        "Salutation": "Bonjour!",
        "Consulter solde": "Quel est mon solde?",
        "Virement simple": "Je veux faire un virement de 50000 FCFA",
        "Virement complet": "Je veux transferer 100000 XOF a Mamadou Diallo pour paiement facture",
        "Simulation credit": "Je voudrais simuler un credit de 5 millions sur 24 mois",
        "Releve compte": "Je veux mon releve de compte du mois dernier",
        "Question tarifs": "Combien coute une attestation de cloture?",
        "Question generale": "Comment ouvrir un compte?",
    }

    st.caption("Cliquez pour tester:")
    for name, msg in test_cases.items():
        if st.button(name, key=f"test_{name}", use_container_width=True):
            st.session_state.messages.append({"role": "user", "content": msg})
            st.rerun()

    st.divider()

    # Clear chat
    if st.button("🗑️ Effacer conversation", use_container_width=True):
        st.session_state.messages = []
        st.rerun()


# Main chat area
st.title("🏦 AFG Bank Assistant")
st.caption("Interface de test pour l'assistant bancaire")

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("Posez votre question..."):
    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

# Generate response if last message is from user
if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    with st.chat_message("assistant"):
        with st.spinner("Reflexion en cours..."):
            response, error = call_llm(st.session_state.messages)

            if error:
                st.error(error)
                response = "Desole, une erreur est survenue."

            st.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})


# Bottom section - Test scenarios
st.divider()

col1, col2 = st.columns(2)

with col1:
    st.subheader("📋 Scenarios de test complets")

    scenarios = {
        "Virement avec slot filling": [
            "Je veux faire un virement",
            "50000 FCFA",
            "A Fatou Diop",
            "Compte 123456789",
            "Paiement loyer"
        ],
        "Simulation credit immobilier": [
            "Je voudrais un credit immobilier",
            "15 millions XOF",
            "Sur 10 ans",
            "Quel serait le taux?"
        ],
        "Multi-question": [
            "Bonjour, quel est mon solde et quels sont vos tarifs?"
        ]
    }

    selected_scenario = st.selectbox("Choisir un scenario:", list(scenarios.keys()))

    if st.button("▶️ Executer scenario"):
        st.session_state.messages = []
        for msg in scenarios[selected_scenario]:
            st.session_state.messages.append({"role": "user", "content": msg})
            response, _ = call_llm(st.session_state.messages)
            if response:
                st.session_state.messages.append({"role": "assistant", "content": response})
        st.rerun()

with col2:
    st.subheader("📊 Statistiques")

    total_messages = len(st.session_state.messages)
    user_messages = len([m for m in st.session_state.messages if m["role"] == "user"])

    st.metric("Total messages", total_messages)
    st.metric("Questions posees", user_messages)

    # Model info
    st.caption(f"Modele: {MODEL_NAME}")
    st.caption(f"Serveur: {LLM_URL}")
