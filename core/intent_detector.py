import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import re
from typing import Dict, List, Tuple, Optional
import json

import sys
sys.path.append('..')
from config.config import *
from data.intent_examples import INTENT_EXAMPLES
from utils.text_normalizer import TextNormalizer


class IntentDetector:
    """
    Multi-layer Intent Detection:
    1. Embedding-based similarity (BGE-M3)
    2. Rule-based keyword matching
    3. Fusion of scores
    4. Fallback to LLM (Qwen) for ambiguous cases
    """

    def __init__(self, embedding_model_name: str = EMBEDDING_MODEL, llm_model=None):
        self.normalizer = TextNormalizer()

        # Load embedding model - silent for Streamlit
        self.embedding_model = SentenceTransformer(embedding_model_name)

        # Store LLM reference for fallback
        self.llm_model = llm_model

        # Pre-compute embeddings for all intent examples
        self.intent_embeddings = {}
        self._prepare_intent_embeddings()

        # Define keyword rules
        self.keyword_rules = self._build_keyword_rules()

    def _prepare_intent_embeddings(self):
        """Pre-compute and store embeddings for all intent examples"""
        for intent, examples in INTENT_EXAMPLES.items():
            # Normalize all examples
            normalized_examples = [self.normalizer.normalize(ex) for ex in examples]

            # Compute embeddings
            embeddings = self.embedding_model.encode(normalized_examples, convert_to_tensor=False)

            self.intent_embeddings[intent] = {
                'examples': normalized_examples,
                'embeddings': embeddings
            }

        # Silent - embeddings prepared for Streamlit

    def _build_keyword_rules(self) -> Dict[str, List[str]]:
        """Define high-precision keyword rules for each intent"""
        return {
            "CONSULTER_SOLDE": [
                r'\bsolde\b',
                r'\bbalance\b',
                r'\bcombien\s+(j\'?ai|il\s+me\s+reste)',
                r'\bmon\s+compte\s+c\'?est\s+combien\b',
                r'\baffiche.*solde\b',
                r'\bconsultation\b',
            ],
            "DISCUSSION_COMPTE": [
                r'\bpourquoi.*debit\b',
                r'\bpourquoi.*retrait\b',
                r'\bc\'?est\s+quoi.*operation\b',
                r'\bc\'?est\s+quoi.*frais\b',
                r'\btransaction\s+suspecte\b',
                r'\bexplique.*mouvement\b',
                r'\bhistorique\b',
                r'\bdernieres?\s+transactions?\b',
            ],
            "FAIRE_VIREMENT": [
                r'\bvirement\b',
                r'\btransfert?\b',
                r'\btransfer\b',
                r'\benvoyer.*argent\b',
                r'\bpayer\b',
                r'\bvirer\b',
                r'\bmobile\s+money\b',
                r'\borange\s+money\b',
                r'\bwave\b',
            ],
            "OBTENIR_RELEVE": [
                r'\breleve\b',
                r'\bextrait\b',
                r'\bpdf\b',
                r'\bdocument\b',
                r'\breleve.*compte\b',
                r'\bhistorique\s+complet\b',
            ],
            "SIMULATION_CREDIT": [
                r'\bemprunter\b',
                r'\bpret\b',
                r'\bcredit\b',
                r'\bcapacite.*emprunt\b',
                r'\bmensualite\b',
                r'\bsimulation\b',
                r'\btaux.*interet\b',
                r'\bfinancement\b',
            ],
        }

    def _compute_embedding_scores(self, text_norm: str) -> Dict[str, float]:
        """Compute similarity scores using embeddings"""
        # Get embedding for the input text
        text_embedding = self.embedding_model.encode([text_norm], convert_to_tensor=False)[0]

        scores = {}
        for intent, data in self.intent_embeddings.items():
            # Compute cosine similarity with all examples
            similarities = cosine_similarity(
                [text_embedding],
                data['embeddings']
            )[0]

            # Take the maximum similarity
            scores[intent] = float(np.max(similarities))

        return scores

    def _compute_rule_scores(self, text_norm: str) -> Dict[str, float]:
        """Compute scores based on keyword rules"""
        scores = {intent: 0.0 for intent in INTENTS}

        for intent, patterns in self.keyword_rules.items():
            for pattern in patterns:
                if re.search(pattern, text_norm):
                    scores[intent] = 1.0
                    break  # One match is enough

        return scores

    def _fuse_scores(self, emb_scores: Dict[str, float], rule_scores: Dict[str, float]) -> Dict[str, float]:
        """Combine embedding and rule-based scores"""
        fused = {}
        for intent in INTENTS:
            emb = emb_scores.get(intent, 0.0)
            rule = rule_scores.get(intent, 0.0)
            fused[intent] = INTENT_WEIGHT_EMB * emb + INTENT_WEIGHT_RULES * rule

        return fused

    def _llm_fallback(self, text: str) -> str:
        """Use LLM to determine intent when ambiguous"""
        if self.llm_model is None:
            return "OTHER"

        prompt = f"""Tu es un routeur d'intentions pour un assistant bancaire.
Intents possibles :
- CONSULTER_SOLDE
- DISCUSSION_COMPTE
- FAIRE_VIREMENT
- OBTENIR_RELEVE
- SIMULATION_CREDIT
- OTHER

Message client : "{text}"

Réponds UNIQUEMENT par le nom exact d'un intent (sans explication)."""

        try:
            # Call LLM (implementation depends on your LLM setup)
            response = self._call_llm(prompt)
            response = response.strip().upper()

            if response in INTENTS:
                return response
            else:
                return "OTHER"
        except Exception as e:
            # Silent - LLM fallback error
            return "OTHER"

    def _call_llm(self, prompt: str) -> str:
        """Call the LLM model - Ollama implementation"""
        if self.llm_model is None:
            return "OTHER"

        try:
            # Check if it's an Ollama client
            if hasattr(self.llm_model, 'generate'):
                response = self.llm_model.generate(prompt, temperature=0.3)
                response = response.strip().upper()

                if response in INTENTS:
                    return response
                else:
                    return "OTHER"
            else:
                # Fallback for other LLM types
                return "OTHER"

        except Exception as e:
            # Silent - LLM fallback error
            return "OTHER"

    def detect(self, text: str) -> Dict:
        """
        Main detection method

        Returns:
            {
                'intent': str,
                'confidence': float,
                'scores_emb': dict,
                'scores_rules': dict,
                'scores_fused': dict,
                'method': 'embeddings' | 'rules' | 'llm_fallback'
            }
        """
        # Step 1: Normalize
        text_norm = self.normalizer.normalize(text)

        # Step 2: Compute embedding scores
        scores_emb = self._compute_embedding_scores(text_norm)

        # Step 3: Compute rule-based scores
        scores_rules = self._compute_rule_scores(text_norm)

        # Step 4: Fuse scores
        scores_fused = self._fuse_scores(scores_emb, scores_rules)

        # Step 5: Find best intent
        best_intent = max(scores_fused, key=scores_fused.get)
        best_score = scores_fused[best_intent]

        # Step 6: Apply thresholds
        if best_score >= INTENT_THRESHOLD_HIGH:
            # High confidence - accept
            return {
                'intent': best_intent,
                'confidence': best_score,
                'scores_emb': scores_emb,
                'scores_rules': scores_rules,
                'scores_fused': scores_fused,
                'method': 'embeddings+rules',
                'text_normalized': text_norm
            }
        elif best_score >= INTENT_THRESHOLD_LOW:
            # Ambiguous - use LLM fallback
            fallback_intent = self._llm_fallback(text)
            return {
                'intent': fallback_intent,
                'confidence': best_score,
                'scores_emb': scores_emb,
                'scores_rules': scores_rules,
                'scores_fused': scores_fused,
                'method': 'llm_fallback',
                'text_normalized': text_norm
            }
        else:
            # Low confidence - mark as OTHER
            return {
                'intent': 'OTHER',
                'confidence': best_score,
                'scores_emb': scores_emb,
                'scores_rules': scores_rules,
                'scores_fused': scores_fused,
                'method': 'low_confidence',
                'text_normalized': text_norm
            }
