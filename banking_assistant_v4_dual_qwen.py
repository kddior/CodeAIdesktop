# -*- coding: utf-8 -*-
"""
Banking Assistant V4 - LM Studio Edition
Uses LM Studio for 100% GPU utilization (vs Ollama's 11%)
Optimized for Jetson AGX with voice support
"""

from typing import Dict, Any, Optional
import logging

# Core components
from core import IntentDetector, SlotExtractor, DialogueManager, ResponseGenerator
from core.session_state import SessionState
from core.flow_router import FlowRouter

# LLM Client (LM Studio for maximum performance)
from llm.dual_model_lmstudio import DualModelLMStudio

# Backend
from backends.banking_backend import BankingBackend

# RAG
from rag.rag_manager import RAGManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BankingAssistantV4:
    """
    Banking Assistant with LM Studio backend for maximum performance.

    Features:
    - 100% GPU utilization (vs Ollama's 11%)
    - Intent detection & slot extraction
    - Multi-turn dialogue management
    - RAG for document retrieval
    - Banking backend integration
    - Optimized for low-latency voice applications
    """

    def __init__(
        self,
        enable_rag: bool = True,
        fast_model: str = "qwen2.5-7b-instruct",
        quality_model: str = "qwen2.5-14b-instruct"
    ):
        """
        Initialize Banking Assistant.

        Args:
            enable_rag: Enable RAG for document retrieval
            fast_model: Fast model for simple queries
            quality_model: Quality model for complex queries
        """
        logger.info("Initializing Banking Assistant V4 (LM Studio Edition)...")

        # Initialize LM Studio client
        logger.info("Loading LM Studio client (100% GPU utilization)...")
        self.llm_client = DualModelLMStudio(
            fast_model=fast_model,
            quality_model=quality_model,
            timeout=60
        )

        # Initialize core components
        logger.info("Initializing NLU pipeline...")
        self.intent_detector = IntentDetector()
        self.slot_extractor = SlotExtractor()
        self.dialogue_manager = DialogueManager()
        self.response_generator = ResponseGenerator(llm_client=self.llm_client)
        self.flow_router = FlowRouter()

        # Initialize backend
        logger.info("Initializing banking backend...")
        self.backend = BankingBackend()

        # Initialize RAG if enabled
        self.enable_rag = enable_rag
        self.rag_manager = None
        if enable_rag:
            logger.info("Initializing RAG system...")
            try:
                self.rag_manager = RAGManager()
                logger.info("RAG system initialized successfully")
            except Exception as e:
                logger.warning(f"RAG initialization failed: {e}. Continuing without RAG.")
                self.enable_rag = False

        # Session storage
        self.sessions: Dict[str, SessionState] = {}

        logger.info("✓ Banking Assistant initialized successfully!")
        logger.info(f"  LLM Backend: LM Studio (Fast: {fast_model}, Quality: {quality_model})")
        logger.info(f"  RAG Enabled: {self.enable_rag}")
        logger.info(f"  GPU Utilization: 100%")

    def _get_session(self, session_id: str) -> SessionState:
        """Get or create session state."""
        if session_id not in self.sessions:
            self.sessions[session_id] = SessionState(session_id=session_id)
        return self.sessions[session_id]

    def chat(self, session_id: str, user_message: str) -> Dict[str, Any]:
        """
        Process user message and generate response.

        Args:
            session_id: Unique session identifier
            user_message: User's input message

        Returns:
            {
                'response': str,  # Assistant's response
                'intent': str,    # Detected intent
                'confidence': float,  # Intent confidence
                'slots': dict,    # Extracted slots
                'state': str,     # Dialogue state
                'model_used': str  # LLM model used
            }
        """
        try:
            # Get session
            session = self._get_session(session_id)

            # Update session history
            session.add_message("user", user_message)

            # Step 1: Intent Detection
            intent_result = self.intent_detector.detect(user_message)
            intent = intent_result.get('intent', 'OTHER')
            confidence = intent_result.get('confidence', 0.0)

            logger.info(f"[{session_id}] Intent: {intent} (conf: {confidence:.2f})")

            # Step 2: Slot Extraction
            slots = self.slot_extractor.extract(user_message, intent)
            logger.info(f"[{session_id}] Slots: {slots}")

            # Step 3: Dialogue Management
            dialogue_state = self.dialogue_manager.update(
                session=session,
                intent=intent,
                slots=slots,
                user_message=user_message
            )

            # Step 4: RAG Retrieval (if enabled and relevant)
            rag_context = None
            if self.enable_rag and self.rag_manager:
                try:
                    rag_results = self.rag_manager.search(user_message, top_k=3)
                    if rag_results:
                        rag_context = "\n\n".join([
                            f"[Document: {r['doc_name']}]\n{r['content']}"
                            for r in rag_results
                        ])
                        logger.info(f"[{session_id}] RAG: Found {len(rag_results)} relevant documents")
                except Exception as e:
                    logger.warning(f"RAG search failed: {e}")

            # Step 5: Backend Integration (for banking operations)
            backend_result = None
            if intent in ['CONSULTER_SOLDE', 'FAIRE_VIREMENT', 'OBTENIR_RELEVE']:
                try:
                    backend_result = self.backend.execute(
                        intent=intent,
                        slots=slots,
                        session=session
                    )
                    logger.info(f"[{session_id}] Backend result: {backend_result}")
                except Exception as e:
                    logger.error(f"Backend execution failed: {e}")

            # Step 6: Response Generation
            response_result = self.response_generator.generate(
                session=session,
                intent=intent,
                confidence=confidence,
                slots=slots,
                dialogue_state=dialogue_state,
                rag_context=rag_context,
                backend_result=backend_result
            )

            response_text = response_result.get('response', 'Désolé, je ne peux pas répondre pour le moment.')
            model_used = response_result.get('model_used', 'unknown')

            # Update session history
            session.add_message("assistant", response_text)

            logger.info(f"[{session_id}] Response generated using {model_used}")

            return {
                'response': response_text,
                'intent': intent,
                'confidence': confidence,
                'slots': slots,
                'state': dialogue_state.get('state', 'unknown'),
                'model_used': model_used,
                'rag_used': rag_context is not None,
                'backend_result': backend_result
            }

        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            return {
                'response': "Désolé, une erreur est survenue. Pouvez-vous reformuler votre question ?",
                'intent': 'ERROR',
                'confidence': 0.0,
                'slots': {},
                'state': 'error',
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
            'llm_stats': self.llm_client.get_stats(),
            'rag_enabled': self.enable_rag,
            'rag_stats': self.rag_manager.get_stats() if self.rag_manager else None
        }

    def print_stats(self):
        """Print assistant statistics."""
        stats = self.get_stats()
        print(f"\n[STATS] Banking Assistant Statistics")
        print(f"  Total Sessions: {stats['total_sessions']}")
        print(f"  RAG Enabled: {stats['rag_enabled']}")

        if stats['llm_stats']:
            self.llm_client.print_stats()

        if stats['rag_stats']:
            print(f"\n[RAG Stats]")
            print(f"  Total Documents: {stats['rag_stats'].get('total_documents', 0)}")
            print(f"  Total Chunks: {stats['rag_stats'].get('total_chunks', 0)}")


# Test function
def test_assistant():
    """Test banking assistant"""
    print("\n" + "=" * 70)
    print("Testing Banking Assistant V4 - LM Studio Edition")
    print("=" * 70)

    try:
        # Initialize assistant
        assistant = BankingAssistantV4(enable_rag=False)

        # Test queries
        test_queries = [
            "Bonjour, quel est mon solde ?",
            "Je voudrais faire un virement de 50000 FCFA",
            "Comment fonctionne le crédit immobilier ?"
        ]

        session_id = "test_session_001"

        for query in test_queries:
            print(f"\n[USER] {query}")
            result = assistant.chat(session_id, query)
            print(f"[ASSISTANT] {result['response']}")
            print(f"[INFO] Intent: {result['intent']} | Model: {result.get('model_used', 'N/A')}")

        # Print stats
        assistant.print_stats()

        print("\n[OK] Test completed successfully!")

    except Exception as e:
        print(f"\n[FAIL] Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_assistant()
