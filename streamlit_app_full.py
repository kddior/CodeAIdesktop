# -*- coding: utf-8 -*-
"""
AFG Bank Assistant - Complete Streamlit Interface
7-tab comprehensive banking assistant with RAG, calculators, and legal analysis
Optimized for Jetson AGX with llama.cpp server
"""

import streamlit as st
import json
import time
from datetime import datetime
from pathlib import Path
import tempfile
import os
from typing import Dict, Any, List, Optional

# Banking Assistant
from banking_assistant_v4_dual_qwen import BankingAssistantV4

# LLM Clients
from llm.lmstudio_client import LMStudioClient

# Tools
from tools.calculator_formulas import CalculatorFormulas
from tools.financial_calculator import FinancialCalculator
from tools.calculation_verifier import CalculationVerifier

# RAG
from rag.rag_manager import RAGManager

# PDF Extraction
try:
    from pdf_extractor import extract_pdf_text, chunk_text_for_analysis
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    st.warning("PDF extraction not available - install PyMuPDF, pdfplumber, PyPDF2, pypdf, pytesseract")

# =============================================================================
# PAGE CONFIGURATION
# =============================================================================

st.set_page_config(
    page_title="AFG Bank Assistant",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =============================================================================
# AFG BRAND CSS STYLING
# =============================================================================

st.markdown("""
<style>
    :root {
        --afg-navy: #002855;
        --afg-green: #00B140;
        --afg-red: #E30613;
        --afg-white: #FFFFFF;
    }

    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #002855 0%, #001a3d 100%);
    }

    [data-testid="stSidebar"] * {
        color: white !important;
    }

    /* Primary buttons */
    .stButton > button[kind="primary"] {
        background-color: #00B140;
        color: white;
        border: none;
        font-weight: 600;
    }

    .stButton > button[kind="primary"]:hover {
        background-color: #008f33;
    }

    /* Secondary buttons */
    .stButton > button {
        border: 2px solid #002855;
        color: #002855;
        font-weight: 600;
    }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }

    .stTabs [data-baseweb="tab"] {
        height: 50px;
        background-color: #f0f2f6;
        border-radius: 4px 4px 0 0;
        color: #002855;
        font-weight: 600;
    }

    .stTabs [aria-selected="true"] {
        background-color: #002855;
        color: white !important;
    }

    /* Metrics */
    [data-testid="stMetricValue"] {
        color: #002855;
        font-size: 2rem;
        font-weight: 700;
    }

    /* Success/Error messages */
    .element-container .stSuccess {
        background-color: #00B14010;
        border-left: 4px solid #00B140;
    }

    .element-container .stError {
        background-color: #E3061310;
        border-left: 4px solid #E30613;
    }

    /* Chat messages */
    [data-testid="stChatMessageContent"] {
        background-color: #f8f9fa;
        border-radius: 8px;
        padding: 12px;
    }

    /* Headers */
    h1, h2, h3 {
        color: #002855;
        font-weight: 700;
    }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# SESSION STATE INITIALIZATION
# =============================================================================

def init_session_state():
    """Initialize all session state variables"""

    # Assistant initialization
    if "initialized" not in st.session_state:
        st.session_state.initialized = False

    # Chat history
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # Test results
    if "test_results" not in st.session_state:
        st.session_state.test_results = []

    # Current model
    if "current_model" not in st.session_state:
        st.session_state.current_model = "qwen2.5-14b-instruct"

    # User ID
    if "user_id" not in st.session_state:
        st.session_state.user_id = "user_001"

    # Model stats
    if "model_stats" not in st.session_state:
        st.session_state.model_stats = {}

    # Use LM Studio/llama.cpp
    if "use_lm_studio" not in st.session_state:
        st.session_state.use_lm_studio = True

    # Legal analysis
    if "juridique_analysis" not in st.session_state:
        st.session_state.juridique_analysis = None

    if "juridique_document_text" not in st.session_state:
        st.session_state.juridique_document_text = ""

    if "juridique_chat_history" not in st.session_state:
        st.session_state.juridique_chat_history = []

    if "juridique_user_context" not in st.session_state:
        st.session_state.juridique_user_context = ""

    # RAG Manager
    if "rag_manager" not in st.session_state:
        try:
            st.session_state.rag_manager = RAGManager()
        except Exception as e:
            st.session_state.rag_manager = None
            st.error(f"RAG initialization error: {e}")

    # Banking Assistant
    if "assistant" not in st.session_state and not st.session_state.initialized:
        with st.spinner("Initializing Banking Assistant..."):
            try:
                st.session_state.assistant = BankingAssistantV4(
                    enable_rag=True,
                    fast_model="mistral-7b-instruct",
                    quality_model="qwen2.5-14b-instruct"
                )
                st.session_state.initialized = True
                st.success("Assistant initialized successfully!")
            except Exception as e:
                st.error(f"Failed to initialize assistant: {e}")
                st.session_state.initialized = False

init_session_state()

# =============================================================================
# SIDEBAR
# =============================================================================

with st.sidebar:
    st.title("🏦 AFG Bank")
    st.markdown("---")

    # Server status
    st.subheader("🔌 Statut Serveur")

    try:
        import requests
        response = requests.get("http://localhost:1234/v1/models", timeout=5)
        if response.status_code == 200:
            models = response.json()
            model_name = models.get("data", [{}])[0].get("id", "Unknown")
            st.success(f"✅ LLM: {model_name}")
        else:
            st.error("❌ LLM: Server error")
    except:
        st.error("❌ LLM: Not running")

    # Assistant status
    if st.session_state.initialized:
        st.success("✅ Assistant: Ready")
    else:
        st.warning("⚠️ Assistant: Not initialized")

    # RAG status
    if st.session_state.rag_manager:
        st.success("✅ RAG: Ready")
    else:
        st.warning("⚠️ RAG: Not available")

    st.markdown("---")

    # User info
    st.subheader("👤 Utilisateur")
    st.session_state.user_id = st.text_input("User ID", value=st.session_state.user_id)

    st.markdown("---")

    # Settings
    st.subheader("⚙️ Paramètres")
    st.session_state.use_lm_studio = st.checkbox(
        "Utiliser LM Studio/llama.cpp",
        value=st.session_state.use_lm_studio
    )

    # Clear all data
    if st.button("🗑️ Effacer toutes les données", use_container_width=True):
        st.session_state.chat_history = []
        st.session_state.test_results = []
        st.session_state.juridique_analysis = None
        st.session_state.juridique_document_text = ""
        st.session_state.juridique_chat_history = []
        st.rerun()

    st.markdown("---")
    st.caption(f"Version: 4.0 | Model: {st.session_state.current_model}")

# =============================================================================
# MAIN CONTENT - TABS
# =============================================================================

st.title("🏦 AFG Bank Assistant")
st.caption("Assistant bancaire intelligent avec IA")

tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "💬 Conversation",
    "🧪 Tests Auto",
    "📊 Résultats",
    "📄 Documents",
    "🧮 Calculateur",
    "🛡️ Garantie",
    "⚖️ Analyse Juridique"
])

# =============================================================================
# TAB 1: CONVERSATION
# =============================================================================

with tab1:
    st.header("💬 Conversation avec l'Assistant")

    if not st.session_state.initialized:
        st.warning("⚠️ L'assistant n'est pas initialisé. Vérifiez que le serveur LLM est en cours d'exécution.")
    else:
        # Display chat history
        for message in st.session_state.chat_history:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

                # Show metadata for assistant messages
                if message["role"] == "assistant" and "metadata" in message:
                    meta = message["metadata"]
                    mode = meta.get('mode', meta.get('intent', 'N/A'))
                    flow_name = meta.get('flow_name', '')
                    display_mode = f"{mode}" + (f"/{flow_name}" if flow_name else "")
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.caption(f"🎯 Mode: **{display_mode}**")
                    with col2:
                        confidence = meta.get('confidence', 0)
                        st.caption(f"📊 Confidence: **{confidence:.2%}**")
                    with col3:
                        if meta.get('rag_used'):
                            st.caption(f"📚 RAG: **{meta.get('rag_count', 0)} docs**")
                        else:
                            st.caption(f"📚 RAG: **non**")
                    with col4:
                        response_time = meta.get('response_time_ms', 0)
                        if response_time:
                            if response_time < 1000:
                                time_display = f"{response_time}ms"
                            else:
                                time_display = f"{response_time/1000:.1f}s"
                            st.caption(f"⏱️ Temps: **{time_display}**")
                    # Show model used
                    model_used = meta.get('model_used', '')
                    if model_used and model_used != 'N/A':
                        model_short = model_used.split('/')[-1] if '/' in model_used else model_used
                        st.caption(f"🤖 Modèle: **{model_short}**")

        # Chat input
        if prompt := st.chat_input("Saisissez votre message..."):
            # Add user message
            st.session_state.chat_history.append({"role": "user", "content": prompt})

            with st.chat_message("user"):
                st.markdown(prompt)

            # Get assistant response
            with st.chat_message("assistant"):
                with st.spinner("Réflexion en cours..."):
                    try:
                        # Start timing
                        start_time = time.time()

                        result = st.session_state.assistant.chat(
                            st.session_state.user_id,
                            prompt
                        )

                        # Calculate elapsed time
                        elapsed_time = time.time() - start_time
                        elapsed_ms = int(elapsed_time * 1000)

                        response = result.get('response', 'Désolé, une erreur est survenue.')
                        # Use conversation_mode instead of legacy intent
                        mode = result.get('conversation_mode', result.get('intent', 'UNKNOWN'))
                        flow_name = result.get('flow_name', '')
                        confidence = result.get('confidence', 0.0)
                        rag_used = result.get('rag_used', False)
                        rag_count = result.get('rag_results_count', 0)
                        model_used = result.get('model_used', 'N/A')

                        st.markdown(response)

                        # Display metrics with timing
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            display_mode = f"{mode}"
                            if flow_name:
                                display_mode += f"/{flow_name}"
                            st.caption(f"🎯 Mode: **{display_mode}**")
                        with col2:
                            st.caption(f"📊 Confidence: **{confidence:.2%}**")
                        with col3:
                            if rag_used:
                                st.caption(f"📚 RAG: **{rag_count} docs**")
                            else:
                                st.caption(f"📚 RAG: **non**")
                        with col4:
                            # Format timing display
                            if elapsed_time < 1:
                                time_display = f"{elapsed_ms}ms"
                            else:
                                time_display = f"{elapsed_time:.1f}s"
                            st.caption(f"⏱️ Temps: **{time_display}**")

                        # Show model used in a separate line
                        if model_used and model_used != 'N/A':
                            model_short = model_used.split('/')[-1] if '/' in model_used else model_used
                            st.caption(f"🤖 Modèle: **{model_short}**")

                        # Save to history
                        st.session_state.chat_history.append({
                            "role": "assistant",
                            "content": response,
                            "metadata": {
                                "mode": mode,
                                "flow_name": flow_name,
                                "confidence": confidence,
                                "rag_used": rag_used,
                                "rag_count": rag_count,
                                "model_used": model_used,
                                "response_time_ms": elapsed_ms,
                                "timestamp": datetime.now().isoformat()
                            }
                        })

                    except Exception as e:
                        st.error(f"Erreur: {str(e)}")
                        st.session_state.chat_history.append({
                            "role": "assistant",
                            "content": f"Erreur: {str(e)}"
                        })

            st.rerun()

        # Quick actions
        st.markdown("---")
        st.subheader("Actions Rapides")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            if st.button("💰 Consulter solde", use_container_width=True):
                st.session_state.chat_history.append({"role": "user", "content": "Quel est mon solde?"})
                st.rerun()

        with col2:
            if st.button("💸 Faire virement", use_container_width=True):
                st.session_state.chat_history.append({"role": "user", "content": "Je veux faire un virement"})
                st.rerun()

        with col3:
            if st.button("📄 Obtenir relevé", use_container_width=True):
                st.session_state.chat_history.append({"role": "user", "content": "Je veux mon relevé de compte"})
                st.rerun()

        with col4:
            if st.button("🔄 Simulation crédit", use_container_width=True):
                st.session_state.chat_history.append({"role": "user", "content": "Je voudrais simuler un crédit"})
                st.rerun()

# =============================================================================
# TAB 2: AUTOMATED TESTS
# =============================================================================

with tab2:
    st.header("🧪 Tests Automatiques")
    st.caption("Exécuter des scénarios de test prédéfinis")

    if not st.session_state.initialized:
        st.warning("⚠️ L'assistant n'est pas initialisé.")
    else:
        # Load test scenarios
        test_file_path = Path("tests/banking_tests.json")

        if test_file_path.exists():
            with open(test_file_path, 'r', encoding='utf-8') as f:
                test_scenarios = json.load(f)

            # Test category selection
            col1, col2 = st.columns([2, 1])

            with col1:
                categories = list(test_scenarios.keys())
                selected_categories = st.multiselect(
                    "Catégories de tests à exécuter",
                    categories,
                    default=categories
                )

            with col2:
                max_tests = st.number_input(
                    "Nombre max de tests par catégorie",
                    min_value=1,
                    max_value=100,
                    value=20
                )

            # Run tests button
            if st.button("▶️ Exécuter les tests", type="primary", use_container_width=True):
                results = []
                progress_bar = st.progress(0)
                status_text = st.empty()

                total_tests = sum(
                    min(len(test_scenarios[cat]), max_tests)
                    for cat in selected_categories
                )
                test_count = 0

                for category in selected_categories:
                    tests = test_scenarios[category][:max_tests]

                    for test in tests:
                        test_count += 1
                        progress = test_count / total_tests
                        progress_bar.progress(progress)
                        status_text.text(f"Test {test_count}/{total_tests}: {test['input'][:50]}...")

                        start_time = time.time()

                        try:
                            result = st.session_state.assistant.chat(
                                st.session_state.user_id,
                                test["input"]
                            )

                            elapsed_ms = int((time.time() - start_time) * 1000)

                            actual_intent = result.get('intent', 'UNKNOWN')
                            expected_intent = test.get('expected_intent', 'N/A')
                            passed = actual_intent == expected_intent

                            results.append({
                                'category': category,
                                'input': test['input'],
                                'expected_intent': expected_intent,
                                'actual_intent': actual_intent,
                                'confidence': result.get('confidence', 0.0),
                                'passed': passed,
                                'time_ms': elapsed_ms,
                                'description': test.get('description', ''),
                                'timestamp': datetime.now().isoformat()
                            })

                        except Exception as e:
                            results.append({
                                'category': category,
                                'input': test['input'],
                                'expected_intent': test.get('expected_intent', 'N/A'),
                                'actual_intent': 'ERROR',
                                'confidence': 0.0,
                                'passed': False,
                                'time_ms': 0,
                                'error': str(e),
                                'timestamp': datetime.now().isoformat()
                            })

                progress_bar.progress(1.0)
                status_text.text(f"✅ Tests terminés: {test_count}/{total_tests}")

                # Save results
                st.session_state.test_results = results

                st.success(f"✅ {test_count} tests exécutés avec succès!")

                # Quick summary
                passed_count = sum(1 for r in results if r['passed'])
                pass_rate = passed_count / len(results) * 100 if results else 0

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Tests", len(results))
                with col2:
                    st.metric("Tests Réussis", passed_count)
                with col3:
                    st.metric("Taux de Réussite", f"{pass_rate:.1f}%")

        else:
            st.error(f"❌ Fichier de tests non trouvé: {test_file_path}")
            st.info("Créez un fichier `tests/banking_tests.json` avec les scénarios de test.")

            # Show example structure
            with st.expander("📝 Voir exemple de structure"):
                st.code('''
{
  "banking_tests": [
    {
      "input": "quel est mon solde ?",
      "expected_intent": "CONSULTER_SOLDE",
      "description": "Basic balance inquiry"
    },
    {
      "input": "virement de 50000 FCFA à Pierre",
      "expected_intent": "FAIRE_VIREMENT",
      "description": "Transfer with amount and recipient"
    }
  ],
  "general_tests": [
    {
      "input": "quelle heure est-il ?",
      "expected_intent": "OTHER",
      "description": "General conversation"
    }
  ]
}
                ''', language='json')

# =============================================================================
# TAB 3: TEST RESULTS
# =============================================================================

with tab3:
    st.header("📊 Résultats des Tests")
    st.caption("Analyse détaillée des résultats de tests")

    if not st.session_state.test_results:
        st.info("ℹ️ Aucun résultat de test disponible. Exécutez des tests dans l'onglet 'Tests Auto'.")
    else:
        results = st.session_state.test_results

        # Overall metrics
        st.subheader("📈 Métriques Globales")

        passed_count = sum(1 for r in results if r['passed'])
        failed_count = len(results) - passed_count
        pass_rate = passed_count / len(results) * 100 if results else 0
        avg_time = sum(r['time_ms'] for r in results) / len(results) if results else 0

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Total Tests", len(results))
        with col2:
            st.metric("✅ Réussis", passed_count)
        with col3:
            st.metric("❌ Échoués", failed_count)
        with col4:
            st.metric("Taux Réussite", f"{pass_rate:.1f}%")

        col1, col2 = st.columns(2)
        with col1:
            st.metric("⏱️ Temps Moyen", f"{avg_time:.0f} ms")
        with col2:
            st.metric("📊 Confiance Moy.", f"{sum(r.get('confidence', 0) for r in results) / len(results):.2%}")

        st.markdown("---")

        # Results by category
        st.subheader("📁 Résultats par Catégorie")

        categories = {}
        for r in results:
            cat = r.get('category', 'unknown')
            if cat not in categories:
                categories[cat] = {'passed': 0, 'failed': 0, 'total': 0}
            categories[cat]['total'] += 1
            if r['passed']:
                categories[cat]['passed'] += 1
            else:
                categories[cat]['failed'] += 1

        for cat, stats in categories.items():
            col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
            with col1:
                st.write(f"**{cat}**")
            with col2:
                st.write(f"Total: {stats['total']}")
            with col3:
                st.write(f"✅ {stats['passed']}")
            with col4:
                st.write(f"❌ {stats['failed']}")

        st.markdown("---")

        # Detailed results table
        st.subheader("📋 Résultats Détaillés")

        # Filter options
        col1, col2 = st.columns(2)
        with col1:
            filter_status = st.selectbox(
                "Filtrer par statut",
                ["Tous", "✅ Réussis", "❌ Échoués"]
            )
        with col2:
            filter_category = st.selectbox(
                "Filtrer par catégorie",
                ["Toutes"] + list(categories.keys())
            )

        # Apply filters
        filtered_results = results
        if filter_status == "✅ Réussis":
            filtered_results = [r for r in filtered_results if r['passed']]
        elif filter_status == "❌ Échoués":
            filtered_results = [r for r in filtered_results if not r['passed']]

        if filter_category != "Toutes":
            filtered_results = [r for r in filtered_results if r.get('category') == filter_category]

        # Display results
        for i, result in enumerate(filtered_results):
            status_icon = "✅" if result['passed'] else "❌"

            with st.expander(f"{status_icon} Test {i+1}: {result['input'][:60]}..."):
                col1, col2 = st.columns(2)

                with col1:
                    st.write(f"**Input:** {result['input']}")
                    st.write(f"**Expected Intent:** {result['expected_intent']}")
                    st.write(f"**Actual Intent:** {result['actual_intent']}")

                with col2:
                    st.write(f"**Category:** {result.get('category', 'N/A')}")
                    st.write(f"**Confidence:** {result.get('confidence', 0):.2%}")
                    st.write(f"**Time:** {result['time_ms']} ms")

                if 'error' in result:
                    st.error(f"Error: {result['error']}")

        st.markdown("---")

        # Export results
        st.subheader("💾 Exporter les Résultats")

        col1, col2 = st.columns(2)

        with col1:
            if st.button("📥 Télécharger JSON", use_container_width=True):
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"test_results_{timestamp}.json"

                json_str = json.dumps(results, indent=2, ensure_ascii=False)
                st.download_button(
                    label="💾 Télécharger",
                    data=json_str,
                    file_name=filename,
                    mime="application/json"
                )

        with col2:
            if st.button("🗑️ Effacer les résultats", use_container_width=True):
                st.session_state.test_results = []
                st.rerun()

# =============================================================================
# TAB 4: DOCUMENTS (RAG MANAGEMENT)
# =============================================================================

with tab4:
    st.header("📄 Gestion des Documents")
    st.caption("Upload et gestion des documents pour le système RAG")

    if not st.session_state.rag_manager:
        st.error("❌ RAG Manager non disponible")
    else:
        rag = st.session_state.rag_manager

        # Upload section
        st.subheader("📤 Upload de Document")

        col1, col2 = st.columns([2, 1])

        with col1:
            uploaded_file = st.file_uploader(
                "Choisir un fichier PDF ou TXT",
                type=['pdf', 'txt'],
                help="Formats supportés: PDF, TXT"
            )

        with col2:
            st.info("💡 Les documents sont indexés pour la recherche sémantique")

        if uploaded_file:
            # Document metadata form
            st.subheader("📝 Métadonnées du Document")

            col1, col2 = st.columns(2)

            with col1:
                doc_name = st.text_input("Nom du document", value=uploaded_file.name)
                doc_type = st.selectbox(
                    "Type de document",
                    ["tarifs", "procedures", "reglementations", "contrats", "autres"]
                )

            with col2:
                doc_country = st.selectbox("Pays", ["Senegal", "Mali", "Côte d'Ivoire", "Autre"])
                doc_bank = st.text_input("Banque", value="AFG Bank")

            if st.button("✅ Upload et Indexer", type="primary", use_container_width=True):
                with st.spinner("Upload et indexation en cours..."):
                    try:
                        # Save uploaded file temporarily
                        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(uploaded_file.name).suffix) as tmp_file:
                            tmp_file.write(uploaded_file.getvalue())
                            tmp_path = tmp_file.name

                        # Upload and ingest
                        doc_id = rag.upload_and_ingest(
                            file_path=tmp_path,
                            doc_name=doc_name,
                            doc_type=doc_type,
                            metadata={
                                'country': doc_country,
                                'bank': doc_bank,
                                'upload_date': datetime.now().isoformat()
                            }
                        )

                        # Clean up temp file
                        os.unlink(tmp_path)

                        st.success(f"✅ Document indexé avec succès! ID: {doc_id}")
                        st.rerun()

                    except Exception as e:
                        st.error(f"❌ Erreur lors de l'upload: {str(e)}")

        st.markdown("---")

        # Document list
        st.subheader("📚 Documents Indexés")

        try:
            all_docs = rag.registry.get_all()

            if all_docs:
                st.write(f"**Total: {len(all_docs)} documents**")

                for doc in all_docs:
                    with st.expander(f"📄 {doc.get('doc_name', 'Unnamed')}"):
                        col1, col2, col3 = st.columns([2, 1, 1])

                        # Parse metadata if it's a JSON string
                        metadata = doc.get('metadata', {})
                        if isinstance(metadata, str):
                            try:
                                metadata = json.loads(metadata)
                            except:
                                metadata = {}

                        with col1:
                            st.write(f"**ID:** {doc.get('doc_id', 'N/A')}")
                            st.write(f"**Type:** {doc.get('doc_type', 'N/A')}")
                            st.write(f"**Pays:** {doc.get('country', metadata.get('country', 'N/A') if metadata else 'N/A')}")

                        with col2:
                            st.write(f"**Chunks:** {doc.get('num_chunks', 0)}")
                            created_at = doc.get('created_at', 'N/A')
                            if created_at != 'N/A' and created_at:
                                try:
                                    created_at = datetime.fromisoformat(str(created_at)).strftime("%Y-%m-%d %H:%M")
                                except:
                                    pass
                            st.write(f"**Upload:** {created_at}")

                        with col3:
                            if st.button(f"🗑️ Supprimer", key=f"del_{doc.get('doc_id')}", use_container_width=True):
                                try:
                                    rag.registry.delete_document(doc.get('doc_id'))
                                    st.success("Document supprimé")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Erreur: {e}")
            else:
                st.info("ℹ️ Aucun document indexé")

        except Exception as e:
            st.error(f"❌ Erreur lors de la récupération des documents: {str(e)}")

        st.markdown("---")

        # RAG Statistics
        st.subheader("📊 Statistiques RAG")

        try:
            stats = rag.get_stats()

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Documents", stats.get('total_documents', 0))
            with col2:
                st.metric("Chunks Totaux", stats.get('total_chunks', 0))
            with col3:
                st.metric("Index Size", f"{stats.get('index_size_kb', 0):.1f} KB")

        except:
            st.info("Statistiques non disponibles")

# =============================================================================
# TAB 5: FINANCIAL CALCULATORS
# =============================================================================

with tab5:
    st.header("🧮 Calculateurs Financiers")
    st.caption("11 calculateurs financiers professionnels")

    # Calculator selection
    calculators = {
        "capacite_emprunt": "💰 Capacité d'Emprunt",
        "simulation_pret": "🏦 Simulation de Prêt",
        "comparaison_prets": "⚖️ Comparaison de 2 Prêts",
        "rachat_credits": "🔄 Rachat de Crédits",
        "decouvert_vs_credit": "💳 Découvert vs Crédit",
        "epargne_objectif": "🎯 Plan d'Épargne",
        "dscr_entreprise": "🏢 DSCR Entreprise",
        "leverage_entreprise": "📊 Ratio d'Endettement",
        "ltv_garantie": "🏠 Loan-to-Value",
        "commission_garantie": "🛡️ Commissions de Garantie",
        "fx_conversion": "💱 Conversion FX"
    }

    selected_calc = st.selectbox(
        "Choisir un calculateur",
        list(calculators.keys()),
        format_func=lambda x: calculators[x]
    )

    st.markdown("---")

    # Calculator forms
    if selected_calc == "capacite_emprunt":
        st.subheader("💰 Capacité d'Emprunt")

        col1, col2 = st.columns(2)

        with col1:
            revenu_mensuel = st.number_input("Revenu mensuel net (XOF)", min_value=0, value=500000, step=10000)
            charges_mensuelles = st.number_input("Charges mensuelles (XOF)", min_value=0, value=100000, step=10000)

        with col2:
            taux_annuel = st.number_input("Taux annuel (%)", min_value=0.0, value=8.0, step=0.1)
            duree_mois = st.number_input("Durée (mois)", min_value=1, value=240, step=12)

        if st.button("🔢 Calculer", type="primary", use_container_width=True, key="calc_capacite"):
            inputs = {
                'revenu_mensuel_net': revenu_mensuel,
                'charges_mensuelles_existantes': charges_mensuelles,
                'taux_endettement_max': 0.33,  # 33% standard
                'taux_credit_annuel': taux_annuel / 100,  # Convert % to decimal
                'duree_annees': duree_mois / 12  # Convert months to years
            }

            result = FinancialCalculator.calculate("capacite_emprunt", inputs)

            if result.get('ok'):
                res = result['resultat']

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Capacité d'Emprunt", f"{res['montant_max_pret']:,.0f} XOF")
                with col2:
                    st.metric("Mensualité Disponible", f"{res['mensualite_disponible_nouveau_credit']:,.0f} XOF")
                with col3:
                    st.metric("Taux Endettement Actuel", f"{res['taux_endettement_actuel']*100:.1f}%")

                # Formula explanation
                formula = CalculatorFormulas.get_formula_explanation("capacite_emprunt", inputs, res)
                with st.expander("📐 Voir les détails du calcul"):
                    st.write(formula)
            else:
                st.error(f"❌ {result.get('error', 'Erreur de calcul')}")

    elif selected_calc == "simulation_pret":
        st.subheader("🏦 Simulation de Prêt")

        col1, col2 = st.columns(2)

        with col1:
            montant = st.number_input("Montant du prêt (XOF)", min_value=0, value=10000000, step=100000)
            duree_mois = st.number_input("Durée (mois)", min_value=1, value=120, step=12)

        with col2:
            taux_annuel = st.number_input("Taux annuel (%)", min_value=0.0, value=8.5, step=0.1)
            frais_dossier_pct = st.number_input("Frais de dossier (%)", min_value=0.0, value=1.0, step=0.1)

        if st.button("🔢 Calculer", type="primary", use_container_width=True, key="calc_simulation"):
            inputs = {
                'montant': montant,
                'taux_annuel': taux_annuel,
                'duree_mois': duree_mois,
                'frais_dossier_pct': frais_dossier_pct
            }

            result = FinancialCalculator.calculate("simulation_pret", inputs)

            if result.get('ok'):
                res = result['resultat']

                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Mensualité", f"{res['mensualite']:,.0f} XOF")
                with col2:
                    st.metric("Coût Total", f"{res['cout_total']:,.0f} XOF")
                with col3:
                    st.metric("Intérêts Totaux", f"{res['interets_totaux']:,.0f} XOF")
                with col4:
                    st.metric("TAEG", f"{res['taeg']:.2f}%")

                # Formula explanation
                formula = CalculatorFormulas.get_formula_explanation("simulation_pret", inputs, res)
                with st.expander("📐 Voir les détails du calcul"):
                    st.write(formula)
            else:
                st.error(f"❌ {result.get('error', 'Erreur de calcul')}")

    elif selected_calc == "fx_conversion":
        st.subheader("💱 Conversion FX")

        col1, col2 = st.columns(2)

        with col1:
            montant = st.number_input("Montant", min_value=0.0, value=1000.0, step=100.0)
            devise_source = st.selectbox("De", ["XOF", "EUR", "USD"])

        with col2:
            taux_change = st.number_input("Taux de change", min_value=0.0, value=655.957, step=0.001)
            devise_cible = st.selectbox("Vers", ["EUR", "USD", "XOF"])

        marge_banque_pct = st.slider("Marge banque (%)", min_value=0.0, max_value=5.0, value=1.5, step=0.1)

        if st.button("🔢 Calculer", type="primary", use_container_width=True, key="calc_fx"):
            inputs = {
                'montant': montant,
                'taux_change': taux_change,
                'marge_banque_pct': marge_banque_pct,
                'devise_source': devise_source,
                'devise_cible': devise_cible
            }

            result = FinancialCalculator.calculate("fx_conversion", inputs)

            if result.get('ok'):
                res = result['resultat']

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Montant Converti", f"{res['montant_converti']:,.2f} {devise_cible}")
                with col2:
                    st.metric("Taux Client", f"{res['taux_client']:.4f}")
                with col3:
                    st.metric("Commission", f"{res['commission_banque']:,.2f} {devise_cible}")
            else:
                st.error(f"❌ {result.get('error', 'Erreur de calcul')}")

    else:
        st.info(f"ℹ️ Interface pour {calculators[selected_calc]} - À implémenter")
        st.write("Les calculateurs suivants sont disponibles via l'API:")
        for key, name in calculators.items():
            st.write(f"- {name}")

# =============================================================================
# TAB 6: GUARANTEE CALCULATOR
# =============================================================================

with tab6:
    st.header("🛡️ Calculateur de Garantie Bancaire")
    st.caption("Calcul des commissions de garanties bancaires")

    # Guarantee types
    guarantee_types = {
        "soumission": "Garantie de Soumission (Bid Bond)",
        "bonne_execution": "Garantie de Bonne Exécution (Performance Bond)",
        "acompte": "Garantie d'Acompte (Advance Payment)",
        "retenue": "Garantie de Retenue de Garantie (Retention)"
    }

    selected_guarantee = st.selectbox(
        "Type de garantie",
        list(guarantee_types.keys()),
        format_func=lambda x: guarantee_types[x]
    )

    st.markdown("---")

    col1, col2 = st.columns(2)

    with col1:
        montant_marche = st.number_input(
            "Montant du marché (XOF)",
            min_value=0,
            value=50000000,
            step=1000000,
            help="Montant total du contrat ou marché"
        )

        taux_garantie = st.number_input(
            "Taux de garantie (%)",
            min_value=0.0,
            max_value=100.0,
            value=10.0,
            step=0.5,
            help="Pourcentage du marché à garantir"
        )

    with col2:
        duree_mois = st.number_input(
            "Durée (mois)",
            min_value=1,
            max_value=120,
            value=12,
            step=1,
            help="Durée de validité de la garantie"
        )

        taux_commission = st.number_input(
            "Taux de commission (%)",
            min_value=0.0,
            max_value=10.0,
            value=2.0,
            step=0.1,
            help="Taux de commission de la banque"
        )

    if st.button("🔢 Calculer", type="primary", use_container_width=True, key="calc_garantie"):
        # Calculate
        montant_garantie = montant_marche * (taux_garantie / 100)
        commission_annuelle = montant_garantie * (taux_commission / 100)
        commission_totale = commission_annuelle * (duree_mois / 12)

        # Display results
        st.success("✅ Calcul effectué")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Montant Garanti", f"{montant_garantie:,.0f} XOF")
        with col2:
            st.metric("Commission Annuelle", f"{commission_annuelle:,.0f} XOF")
        with col3:
            st.metric("Commission Totale", f"{commission_totale:,.0f} XOF")

        st.markdown("---")

        # LLM Verification (if available)
        if st.session_state.initialized:
            with st.expander("🤖 Vérification par IA"):
                verification_prompt = f"""Tu es un expert en garanties bancaires.

CALCUL EFFECTUÉ:
Type de garantie: {guarantee_types[selected_guarantee]}
Montant du marché: {montant_marche:,.0f} XOF
Taux de garantie: {taux_garantie}%
Durée: {duree_mois} mois
Taux de commission: {taux_commission}%

RÉSULTATS:
- Montant garanti: {montant_garantie:,.0f} XOF
- Commission annuelle: {commission_annuelle:,.0f} XOF
- Commission totale: {commission_totale:,.0f} XOF

TÂCHES:
1. VÉRIFIER la cohérence des calculs
2. EXPLIQUER professionnellement le résultat au client
3. Donner des RECOMMANDATIONS sur ce type de garantie

Réponds en français, de manière professionnelle et concise."""

                with st.spinner("Analyse IA en cours..."):
                    try:
                        # Use LLM client directly - 14B for advanced analysis
                        llm_client = LMStudioClient(port=1235)
                        llm_response = llm_client.generate(
                            verification_prompt,
                            temperature=0.3,
                            max_tokens=500
                        )

                        st.write(llm_response)

                    except Exception as e:
                        st.error(f"Erreur IA: {str(e)}")

# =============================================================================
# TAB 7: LEGAL ANALYSIS
# =============================================================================

with tab7:
    st.header("⚖️ Analyse Juridique de Documents")
    st.caption("Analyse IA de contrats et documents juridiques")

    if not PDF_AVAILABLE:
        st.error("❌ Module d'extraction PDF non disponible. Installez les dépendances requises.")
    else:
        # PDF Upload
        st.subheader("📤 Upload de Document")

        uploaded_pdf = st.file_uploader(
            "Choisir un document PDF",
            type=['pdf'],
            help="Upload un contrat ou document juridique à analyser"
        )

        # Optional user context
        user_context = st.text_area(
            "Contexte additionnel (optionnel)",
            placeholder="Ex: Ce contrat concerne un partenariat technologique pour 3 ans...",
            help="Ajoutez du contexte pour améliorer l'analyse"
        )

        if uploaded_pdf:
            if st.button("🔍 Analyser le Document", type="primary", use_container_width=True):
                with st.spinner("Extraction et analyse en cours..."):
                    try:
                        # Save uploaded file temporarily
                        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                            tmp_file.write(uploaded_pdf.getvalue())
                            tmp_path = tmp_file.name

                        # Extract text
                        extracted_text = extract_pdf_text(tmp_path)

                        # Clean up temp file
                        os.unlink(tmp_path)

                        if not extracted_text or len(extracted_text) < 100:
                            st.error("❌ Impossible d'extraire le texte du PDF. Le document est peut-être vide ou protégé.")
                        else:
                            st.session_state.juridique_document_text = extracted_text
                            st.session_state.juridique_user_context = user_context

                            st.success(f"✅ Texte extrait: {len(extracted_text)} caractères")

                            # Chunk text for analysis
                            chunks = chunk_text_for_analysis(extracted_text, chunk_size=4000)

                            # Perform LLM analysis
                            if st.session_state.initialized:
                                analysis_prompt = f"""Tu es un expert juridique spécialisé dans l'analyse de contrats.

CONTEXTE UTILISATEUR:
{user_context if user_context else "Aucun contexte fourni"}

DOCUMENT À ANALYSER:
{extracted_text[:8000]}

TÂCHES:
1. Résumé exécutif du document
2. Identification des parties contractantes
3. Analyse des 12 clauses clés:
   - Durée et renouvellement
   - Objet et services
   - Tarifs et paiement
   - Résiliation
   - Responsabilité et indemnisation
   - Confidentialité
   - Protection des données
   - Loi applicable et juridiction
   - Niveaux de service (SLA)
   - Propriété intellectuelle
   - Sécurité et conformité
   - Sous-traitance et cession

4. Évaluation des risques (faible/moyen/élevé)
5. Recommandations pour négociation
6. Points à surveiller pendant l'exécution

Réponds en JSON structuré en français."""

                                with st.spinner("Analyse IA approfondie en cours..."):
                                    try:
                                        llm_client = LMStudioClient(model_name="qwen2.5-14b-instruct", port=1235)
                                        analysis_response = llm_client.generate(
                                            analysis_prompt,
                                            temperature=0.2,
                                            max_tokens=2000
                                        )

                                        # Store analysis
                                        st.session_state.juridique_analysis = {
                                            'ok': True,
                                            'raw_response': analysis_response,
                                            'timestamp': datetime.now().isoformat(),
                                            'file_name': uploaded_pdf.name
                                        }

                                        st.success("✅ Analyse terminée!")
                                        st.rerun()

                                    except Exception as e:
                                        st.error(f"❌ Erreur lors de l'analyse: {str(e)}")
                            else:
                                st.warning("⚠️ Assistant non initialisé - impossible d'analyser")

                    except Exception as e:
                        st.error(f"❌ Erreur lors de l'extraction: {str(e)}")

        st.markdown("---")

        # Display analysis results
        if st.session_state.juridique_analysis:
            analysis = st.session_state.juridique_analysis

            st.subheader("📋 Résultats de l'Analyse")
            st.caption(f"Document: {analysis.get('file_name', 'N/A')} | Analysé le: {datetime.fromisoformat(analysis['timestamp']).strftime('%Y-%m-%d %H:%M')}")

            # Display raw response
            st.write(analysis.get('raw_response', 'Aucune analyse disponible'))

            st.markdown("---")

            # Post-analysis chat
            st.subheader("💬 Questions sur l'Analyse")

            # Display chat history
            for msg in st.session_state.juridique_chat_history:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])

            # Chat input
            if question := st.chat_input("Posez une question sur le document analysé..."):
                # Add user message
                st.session_state.juridique_chat_history.append({"role": "user", "content": question})

                with st.chat_message("user"):
                    st.markdown(question)

                # Get AI response
                with st.chat_message("assistant"):
                    with st.spinner("Analyse..."):
                        try:
                            context_prompt = f"""Tu es un expert juridique. Voici le contexte:

DOCUMENT ANALYSÉ:
{st.session_state.juridique_document_text[:4000]}

ANALYSE PRÉCÉDENTE:
{analysis.get('raw_response', '')}

QUESTION DU CLIENT:
{question}

Réponds de manière précise et professionnelle en français."""

                            llm_client = LMStudioClient(port=1235)  # 14B for legal analysis
                            response = llm_client.generate(
                                context_prompt,
                                temperature=0.3,
                                max_tokens=500
                            )

                            st.markdown(response)
                            st.session_state.juridique_chat_history.append({"role": "assistant", "content": response})

                        except Exception as e:
                            st.error(f"Erreur: {str(e)}")

                st.rerun()

            # Clear analysis
            if st.button("🗑️ Effacer l'analyse", use_container_width=True):
                st.session_state.juridique_analysis = None
                st.session_state.juridique_document_text = ""
                st.session_state.juridique_chat_history = []
                st.session_state.juridique_user_context = ""
                st.rerun()

# =============================================================================
# FOOTER
# =============================================================================

st.markdown("---")
st.caption("© 2025 AFG Bank - Assistant Bancaire IA v4.0 | Powered by Qwen 2.5")
