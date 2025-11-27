# -*- coding: utf-8 -*-
"""
Banking Assistant V4 - HYBRID ARCHITECTURE

FLOW:
User Input → FAST CLASSIFIER (keywords, instant)
           → RAG Match? → Skip LLM → Go to RAG → QWEN RESPONDER
           → No Match? → QWEN CLASSIFIER (LLM, accurate) → Route → QWEN RESPONDER

HYBRID APPROACH:
- RAG questions: Keyword detection (~1ms) - instant
- Complex questions: LLM classifier (~3-4s) - accurate

Uses llama-cpp-python server with Mistral 7B for fast inference
Optimized for Jetson AGX with voice support
"""

from typing import Dict, Any, Optional
import logging
import time

# Core components
from core.qwen_classifier import QwenClassifier
from core.fast_classifier import FastClassifier  # NEW: Keyword-based classifier
from core.slot_extractor import SlotExtractor
from core.dialogue_manager import DialogueManager
from core.response_generator import ResponseGenerator
from core.session_state import SessionState
from core.flow_router import FlowRouter

# LLM Client (llama-cpp-python server for maximum performance)
from llm.dual_model_lmstudio import DualModelLMStudio

# Backend
from backends.banking_backend import BankingBackend

# RAG
from rag.rag_manager import RAGManager

# Utils
from utils.text_normalizer import TextNormalizer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BankingAssistantV4:
    """
    Banking Assistant with HYBRID Architecture.

    FLOW:
    1. FAST CLASSIFIER (keyword-based, ~1ms)
       - RAG Match? → Skip LLM classifier → Go to RAG
       - No Match? → Use LLM classifier
    2. LLM CLASSIFIER (for complex cases, ~3-4s)
    3. Conditional RAG with Parent-Child retrieval
    4. Conditional Backend
    5. QWEN RESPONDER (response generation)

    Features:
    - HYBRID classification: keywords for RAG, LLM for complex cases
    - Parent-Child RAG retrieval for better context
    - Multi-turn dialogue management
    - Banking backend integration
    - 100% GPU utilization on Jetson AGX
    """

    def __init__(
        self,
        enable_rag: bool = True,
        fast_model: str = "mistral-7b-instruct",  # Changed to Mistral
        quality_model: str = "qwen2.5-14b-instruct"
    ):
        """
        Initialize Banking Assistant with Hybrid Architecture.

        Args:
            enable_rag: Enable RAG for document retrieval
            fast_model: Fast model for simple queries (Mistral 7B)
            quality_model: Quality model for complex queries (QWEN 14B)
        """
        logger.info("Initializing Banking Assistant V4 (HYBRID Architecture)...")

        # Initialize LLM client (llama-cpp-python server on port 1234)
        logger.info("Loading LLM client (llama-cpp-python server, 100% GPU)...")
        self.llm_client = DualModelLMStudio(
            fast_model=fast_model,
            quality_model=quality_model,
            timeout=60
        )

        # Initialize text normalizer
        logger.info("Initializing text normalizer...")
        self.text_normalizer = TextNormalizer()

        # Initialize FAST CLASSIFIER (keyword-based, instant)
        logger.info("Initializing Fast Classifier (keyword-based)...")
        self.fast_classifier = FastClassifier()

        # Initialize LLM CLASSIFIER (for complex cases only)
        logger.info("Initializing LLM Classifier (fallback for complex cases)...")
        self.qwen_classifier = QwenClassifier(
            llm_client=self.llm_client,
            text_normalizer=self.text_normalizer
        )

        # Initialize slot extractor (for additional slot filling)
        self.slot_extractor = SlotExtractor()

        # Initialize QWEN RESPONDER
        logger.info("Initializing Response Generator...")
        self.response_generator = ResponseGenerator(llm_model=self.llm_client)

        # Initialize flow router
        self.flow_router = FlowRouter()

        # Initialize backend
        logger.info("Initializing banking backend...")
        self.backend = BankingBackend()

        # Initialize dialogue manager
        self.dialogue_manager = DialogueManager(
            intent_detector=None,  # Not using IntentDetector anymore
            slot_extractor=self.slot_extractor,
            backend=self.backend,
            response_generator=self.response_generator
        )

        # Initialize RAG if enabled
        self.enable_rag = enable_rag
        self.rag_manager = None
        if enable_rag:
            logger.info("Initializing RAG system with Parent-Child retrieval...")
            try:
                self.rag_manager = RAGManager()
                logger.info("RAG system initialized successfully")
            except Exception as e:
                logger.warning(f"RAG initialization failed: {e}. Continuing without RAG.")
                self.enable_rag = False

        # Session storage
        self.sessions: Dict[str, SessionState] = {}

        # Stats tracking
        self.stats = {
            'fast_classifier_hits': 0,
            'llm_classifier_calls': 0,
            'rag_queries': 0,
            'total_requests': 0
        }

        logger.info("Banking Assistant initialized successfully!")
        logger.info(f"  Architecture: HYBRID (Fast Keywords + LLM Fallback)")
        logger.info(f"  LLM Backend: llama-cpp-python (Fast: {fast_model})")
        logger.info(f"  RAG: Parent-Child retrieval enabled")
        logger.info(f"  GPU Utilization: 100%")

    def _get_session(self, session_id: str) -> SessionState:
        """Get or create session state."""
        if session_id not in self.sessions:
            self.sessions[session_id] = SessionState(user_id=session_id, session_id=session_id)
        return self.sessions[session_id]

    def _get_rag_document_summaries(self) -> list:
        """Get RAG document summaries for classifier context."""
        if not self.enable_rag or not self.rag_manager:
            return []
        try:
            return self.rag_manager.get_document_summaries()
        except Exception:
            return []

    def _map_conversation_mode_to_intent(self, classification: Dict) -> str:
        """Map QWEN #1 classification to legacy intent format."""
        mode = classification.get('conversation_mode', 'UNKNOWN')
        flow_name = classification.get('flow_name')

        # If we have a specific flow, use it
        if flow_name:
            # Map flow names to intents
            flow_to_intent = {
                'CHECK_BALANCE': 'CONSULTER_SOLDE',
                'TRANSFER_MONEY': 'FAIRE_VIREMENT',
                'CREDIT_SIMULATION': 'SIMULATION_CREDIT',
                'GET_STATEMENT': 'OBTENIR_RELEVE',
                'ACCOUNT_HISTORY': 'DISCUSSION_COMPTE'
            }
            return flow_to_intent.get(flow_name, 'OTHER')

        # Map modes to intents
        mode_to_intent = {
            'RAG_QUESTION': 'OTHER',  # Will use RAG for response
            'BANKING_FLOW': 'OTHER',  # Should have flow_name
            'GREETING': 'OTHER',
            'CHITCHAT': 'OTHER',
            'GENERAL_QUESTION': 'OTHER',
            'ASK_CAPABILITIES': 'OTHER',
            'UNKNOWN': 'OTHER'
        }
        return mode_to_intent.get(mode, 'OTHER')

    def chat(self, session_id: str, user_message: str) -> Dict[str, Any]:
        """
        Process user message using HYBRID Architecture.

        FLOW:
        1. FAST CLASSIFIER (keyword-based, ~1ms)
           - RAG Match? → Skip LLM classifier → Go to RAG
           - No Match? → Use LLM classifier
        2. LLM CLASSIFIER (for complex cases, ~3-4s)
        3. Conditional RAG with Parent-Child retrieval
        4. Conditional Backend
        5. Response Generation

        Args:
            session_id: Unique session identifier
            user_message: User's input message

        Returns:
            {
                'response': str,
                'conversation_mode': str,
                'flow_name': str or None,
                'needs_rag': bool,
                'needs_backend': bool,
                'slots': dict,
                'model_used': str,
                'classifier_used': str  # 'fast' or 'llm'
            }
        """
        try:
            # Start timing
            start_time = time.time()
            self.stats['total_requests'] += 1

            # Get session
            session = self._get_session(session_id)

            # Update session history
            session.add_message("user", user_message)

            # Build session context for classifier
            session_context = {
                'current_flow': getattr(session, 'current_flow', None),
                'last_intent': getattr(session, 'last_intent', None),
                'pending_slots': getattr(session, 'missing_slots', [])
            }

            # ===========================================================
            # STEP 1: FAST CLASSIFIER (keyword-based, ~1ms)
            # ===========================================================
            fast_start = time.time()
            fast_result = self.fast_classifier.classify(user_message)
            fast_time_ms = (time.time() - fast_start) * 1000

            logger.info(f"[{session_id}] Fast Classifier: intent={fast_result.intent}, route={fast_result.route}, needs_rag={fast_result.needs_rag} ({fast_time_ms:.1f}ms)")

            # Decide: Use fast classifier result or fallback to LLM?
            use_llm_classifier = (fast_result.route == "LLM_CLASSIFY")
            classifier_used = "fast"

            if use_llm_classifier:
                # ===========================================================
                # STEP 2: LLM CLASSIFIER (fallback for complex cases)
                # ===========================================================
                logger.info(f"[{session_id}] Using LLM Classifier (no keyword match)...")
                self.stats['llm_classifier_calls'] += 1

                # Get RAG document summaries for classifier context
                rag_summaries = self._get_rag_document_summaries()

                # Call LLM Classifier
                classification = self.qwen_classifier.classify(
                    user_message=user_message,
                    top_flow_candidates=[],
                    rag_document_summaries=rag_summaries,
                    session_context=session_context
                )

                # Convert dataclass to dict if needed
                if hasattr(classification, '__dataclass_fields__'):
                    classification = {
                        'conversation_mode': classification.conversation_mode,
                        'flow_name': classification.flow_name,
                        'slots': classification.slots,
                        'needs_backend': classification.needs_backend,
                        'needs_rag': classification.needs_rag,
                        'needs_expert_model': classification.needs_expert_model,
                        'reason': classification.reason,
                        'confidence': classification.confidence
                    }

                conversation_mode = classification.get('conversation_mode', 'UNKNOWN')
                flow_name = classification.get('flow_name')
                needs_rag = classification.get('needs_rag', False)
                needs_backend = classification.get('needs_backend', False)
                extracted_slots = classification.get('slots', {})
                classification_reason = classification.get('reason', '')
                classifier_used = "llm"

            else:
                # Use fast classifier result directly
                self.stats['fast_classifier_hits'] += 1

                # Map fast classifier result to classification format
                conversation_mode = "RAG_QUESTION" if fast_result.needs_rag else "GENERAL_QUESTION"
                if fast_result.intent:
                    if fast_result.intent.startswith("GREETING"):
                        conversation_mode = "GREETING"
                    elif fast_result.intent.startswith("THANKS") or fast_result.intent.startswith("GOODBYE"):
                        conversation_mode = "CHITCHAT"
                    elif fast_result.intent.startswith("CHECK_BALANCE") or fast_result.intent.startswith("TRANSFER"):
                        conversation_mode = "BANKING_FLOW"

                flow_name = fast_result.intent
                needs_rag = fast_result.needs_rag
                needs_backend = (fast_result.route == "BACKEND")
                extracted_slots = {}
                classification_reason = f"Fast classifier: matched keywords {fast_result.keywords_matched}"

            logger.info(f"[{session_id}] Classification ({classifier_used}): mode={conversation_mode}, flow={flow_name}, needs_rag={needs_rag}")
            logger.info(f"[{session_id}] Reason: {classification_reason}")

            # Build classification dict for legacy compatibility
            classification = {
                'conversation_mode': conversation_mode,
                'flow_name': flow_name,
                'needs_rag': needs_rag,
                'needs_backend': needs_backend,
                'slots': extracted_slots,
                'reason': classification_reason,
                'confidence': fast_result.confidence if not use_llm_classifier else 0.8
            }

            # Map to legacy intent for compatibility
            intent = self._map_conversation_mode_to_intent(classification)

            # ===========================================================
            # STEP 3: CONDITIONAL RAG RETRIEVAL with Parent-Child
            # ===========================================================
            rag_context = None
            rag_results = []

            if needs_rag and self.enable_rag and self.rag_manager:
                self.stats['rag_queries'] += 1
                logger.info(f"[{session_id}] RAG retrieval with Parent-Child (needs_rag=true)")
                try:
                    # Use parent-child retrieval for better context
                    rag_results = self.rag_manager.search(user_message, top_k=5)  # Increased to 5
                    if rag_results:
                        rag_context = "\n\n".join([
                            f"[Document: {r['doc_name']}]\n{r['content']}"
                            for r in rag_results
                        ])
                        logger.info(f"[{session_id}] RAG: Found {len(rag_results)} relevant documents")
                except Exception as e:
                    logger.warning(f"RAG search failed: {e}")
            else:
                logger.info(f"[{session_id}] RAG skipped (needs_rag=false or RAG disabled)")

            # ===========================================================
            # STEP 4: CONDITIONAL BACKEND CALL (only if needs_backend=true)
            # ===========================================================
            backend_result = None

            if needs_backend and flow_name:
                logger.info(f"[{session_id}] Backend call triggered for flow: {flow_name}")
                try:
                    backend_result = self.backend.execute(
                        intent=intent,
                        slots=extracted_slots,
                        session=session
                    )
                    logger.info(f"[{session_id}] Backend result: {backend_result}")
                except Exception as e:
                    logger.error(f"Backend execution failed: {e}")
            else:
                logger.info(f"[{session_id}] Backend skipped (needs_backend=false)")

            # ===========================================================
            # STEP 5: RESPONSE GENERATION
            # ===========================================================
            logger.info(f"[{session_id}] QWEN #2 Response generation...")

            # Prepare dialogue state for response generator
            dialogue_state = {
                'state': conversation_mode,
                'flow_name': flow_name,
                'classification': classification
            }

            response_result = self.response_generator.generate(
                session=session,
                intent=intent,
                confidence=classification.get('confidence', 0.8),
                slots=extracted_slots,
                dialogue_state=dialogue_state,
                rag_context=rag_context,
                backend_result=backend_result
            )

            # Handle Dict response from DualModelLMStudio
            if isinstance(response_result, dict):
                response_text = response_result.get('response', 'Desole, je ne peux pas repondre pour le moment.')
                model_used = response_result.get('model_used', 'unknown')
            else:
                response_text = str(response_result)
                model_used = 'unknown'

            # Update session history
            session.add_message("assistant", response_text)

            # Update session state
            session.last_intent = intent
            if flow_name:
                session.current_flow = flow_name

            logger.info(f"[{session_id}] Response generated using {model_used}")

            # Calculate total time
            total_time_ms = (time.time() - start_time) * 1000

            return {
                'response': response_text,
                'conversation_mode': conversation_mode,
                'flow_name': flow_name,
                'intent': intent,
                'confidence': classification.get('confidence', 0.8),
                'slots': extracted_slots,
                'needs_rag': needs_rag,
                'needs_backend': needs_backend,
                'rag_used': rag_context is not None,
                'rag_results_count': len(rag_results),
                'backend_result': backend_result,
                'model_used': model_used,
                'classifier_used': classifier_used,
                'classification_reason': classification_reason,
                'timing_ms': {
                    'fast_classifier': fast_time_ms,
                    'total': total_time_ms
                }
            }

        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            return {
                'response': "Desole, une erreur est survenue. Pouvez-vous reformuler votre question ?",
                'conversation_mode': 'ERROR',
                'flow_name': None,
                'intent': 'ERROR',
                'confidence': 0.0,
                'slots': {},
                'needs_rag': False,
                'needs_backend': False,
                'error': str(e)
            }

    def clear_history(self, session_id: str):
        """Clear conversation history for a session."""
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.info(f"[{session_id}] Session history cleared")

    def get_stats(self) -> Dict[str, Any]:
        """Get assistant statistics."""
        return {
            'total_sessions': len(self.sessions),
            'architecture': 'QWEN #1 Classifier -> Route -> QWEN #2 Responder',
            'llm_stats': self.llm_client.get_stats() if hasattr(self.llm_client, 'get_stats') else None,
            'rag_enabled': self.enable_rag,
            'rag_conditional': True,  # RAG is conditional based on needs_rag
            'rag_stats': self.rag_manager.get_stats() if self.rag_manager else None
        }

    def print_stats(self):
        """Print assistant statistics."""
        stats = self.get_stats()
        print(f"\n[STATS] Banking Assistant Statistics")
        print(f"  Architecture: {stats['architecture']}")
        print(f"  Total Sessions: {stats['total_sessions']}")
        print(f"  RAG Enabled: {stats['rag_enabled']}")
        print(f"  RAG Conditional: {stats['rag_conditional']}")

        if stats['llm_stats'] and hasattr(self.llm_client, 'print_stats'):
            self.llm_client.print_stats()

        if stats['rag_stats']:
            print(f"\n[RAG Stats]")
            print(f"  Total Documents: {stats['rag_stats'].get('total_documents', 0)}")
            print(f"  Total Chunks: {stats['rag_stats'].get('total_chunks', 0)}")


# Test function
def test_assistant():
    """Test banking assistant with original architecture"""
    print("\n" + "=" * 70)
    print("Testing Banking Assistant V4 - Original Architecture")
    print("FLOW: QWEN #1 Classifier -> Conditional RAG -> QWEN #2 Responder")
    print("=" * 70)

    try:
        # Initialize assistant
        assistant = BankingAssistantV4(enable_rag=True)

        # Test queries demonstrating conditional RAG
        test_queries = [
            ("Bonjour", "GREETING - no RAG needed"),
            ("Quel est mon solde ?", "BANKING_FLOW - backend needed, no RAG"),
            ("Quels sont les frais de carte bancaire ?", "RAG_QUESTION - needs_rag=true"),
            ("Je voudrais faire un virement de 50000 FCFA", "BANKING_FLOW - slots + backend"),
        ]

        session_id = "test_session_001"

        for query, expected in test_queries:
            print(f"\n{'='*50}")
            print(f"[USER] {query}")
            print(f"[EXPECTED] {expected}")
            result = assistant.chat(session_id, query)
            print(f"[ASSISTANT] {result['response']}")
            print(f"[CLASSIFICATION] mode={result['conversation_mode']}, flow={result['flow_name']}")
            print(f"[FLAGS] needs_rag={result['needs_rag']}, needs_backend={result['needs_backend']}")
            print(f"[RAG USED] {result['rag_used']} ({result.get('rag_results_count', 0)} results)")
            print(f"[MODEL] {result.get('model_used', 'N/A')}")

        # Print stats
        assistant.print_stats()

        print("\n[OK] Test completed successfully!")

    except Exception as e:
        print(f"\n[FAIL] Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_assistant()
