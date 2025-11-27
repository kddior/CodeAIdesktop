"""
Response Generator - LLM as the final "writer/explainer"
Similar to how Claude generates natural responses
"""

from typing import Dict, Any, Optional
import json

# Import credit simulator for SIMULATION_CREDIT flow
from .credit_simulator import CreditSimulator, CreditSlots
# Import card services for CARD_SERVICE_FLOW
from .card_services import CardServicesHandler, CardServiceSlots
# Import forex exchange for FOREX_FLOW
from .forex_exchange import ForexHandler, ForexSlots
# Import payment incidents for INCIDENT_FLOW
from .payment_incidents import PaymentIncidentsHandler, PaymentIncidentSlots


class ResponseGenerator:
    """
    Generate natural language responses using LLM
    The LLM only explains and formats - never invents data
    """

    def __init__(self, llm_model=None):
        self.llm_model = llm_model
        # Initialize credit simulator for SIMULATION_CREDIT flow
        self.credit_simulator = CreditSimulator()
        # Initialize card services handler for CARD_SERVICE_FLOW
        self.card_services_handler = CardServicesHandler()
        # Initialize forex handler for FOREX_FLOW
        self.forex_handler = ForexHandler()
        # Initialize payment incidents handler for INCIDENT_FLOW
        self.payment_incidents_handler = PaymentIncidentsHandler()

    def generate_slot_question(self, intent: str, slot_name: str, current_slots: Dict) -> str:
        """Generate a natural question to fill missing slot"""

        # Template-based questions (fast, no LLM needed)
        templates = {
            "FAIRE_VIREMENT": {
                "montant": "Quel montant souhaitez-vous virer ?",
                "devise": "Dans quelle devise ? (XOF, EUR, USD)",
                "beneficiaire_nom": "Quel est le nom du bénéficiaire ?",
                "beneficiaire_iban_ou_compte": "Quel est le numéro de compte ou IBAN du bénéficiaire ?",
                "motif": "Quel est le motif du virement ?",
            },
            "OBTENIR_RELEVE": {
                "compte_type": "Pour quel compte ? (courant, épargne, salaire)",
                "date_debut": "À partir de quelle date ?",
                "date_fin": "Jusqu'à quelle date ?",
                "format": "Quel format préférez-vous ? (PDF ou résumé dans le chat)",
            },
            "SIMULATION_CREDIT": {
                "montant_souhaite": "Quel montant souhaitez-vous emprunter ?",
                "duree_mois": "Sur combien de mois ?",
                "revenus_mensuels": "Quels sont vos revenus mensuels ?",
                "charges_mensuelles": "Quelles sont vos charges mensuelles (loyer, autres crédits, etc.) ?",
            }
        }

        # Get template
        question = templates.get(intent, {}).get(slot_name)

        if question:
            return question

        # Fallback: generic question
        return f"Pourriez-vous préciser : {slot_name} ?"

    def generate_confirmation_request(self, intent: str, slots: Dict) -> str:
        """Generate confirmation message before executing action"""

        if intent == "FAIRE_VIREMENT":
            montant = slots.get('montant', '?')
            devise = slots.get('devise', 'XOF')
            beneficiaire = slots.get('beneficiaire_nom', 'le bénéficiaire')

            return f"""Récapitulatif de votre virement :
• Montant : {montant:,.0f} {devise}
• Bénéficiaire : {beneficiaire}

Confirmez-vous cette opération ? (Répondez 'oui' pour confirmer)"""

        return "Confirmez-vous cette opération ?"

    def generate_action_response(self, intent: str, slots: Dict, result: Dict) -> str:
        """
        Generate final response using backend result
        This is where LLM acts like Claude - explaining clearly
        """

        if not result.get('success'):
            return self._generate_error_response(intent, result)

        # Use LLM for natural explanation if available
        if self.llm_model:
            return self._llm_generate_response(intent, slots, result)

        # Fallback: template-based responses
        return self._template_response(intent, slots, result)

    def _template_response(self, intent: str, slots: Dict, result: Dict) -> str:
        """Template-based responses (no LLM)"""

        # CODING mode responses
        if intent == "CODE_ASSIST":
            return self._format_code_assist_response(slots, result)

        # BANKING mode responses
        elif intent == "CONSULTER_SOLDE":
            solde = result['solde']
            devise = result['devise']
            compte_type = result['compte_type']

            return f"""Votre solde sur le compte {compte_type} :
💰 {solde:,.0f} {devise}

Mis à jour le {result['date']}"""

        elif intent == "FAIRE_VIREMENT":
            montant = result['montant']
            devise = result['devise']
            beneficiaire = result['beneficiaire']
            reference = result['reference']
            nouveau_solde = result['nouveau_solde']

            return f"""✅ Virement effectué avec succès !

• Montant : {montant:,.0f} {devise}
• Bénéficiaire : {beneficiaire}
• Référence : {reference}
• Nouveau solde : {nouveau_solde:,.0f} {devise}

Le virement sera traité dans les prochaines heures."""

        elif intent == "OBTENIR_RELEVE":
            nb_ops = result['nb_operations']
            format_type = result['format']

            if format_type == "PDF":
                url = result.get('url_pdf')
                return f"""✅ Votre relevé est prêt !

📄 Nombre d'opérations : {nb_ops}
📅 Période : du {result['date_debut']} au {result['date_fin']}

Télécharger : {url}"""
            else:
                transactions = result['transactions']
                trans_text = "\n".join([
                    f"• {t['date']} - {t['libelle']} : {t['montant']:,.0f} XOF"
                    for t in transactions[:5]
                ])
                return f"""Résumé de vos dernières opérations :

{trans_text}

Total : {nb_ops} opérations sur la période"""

        elif intent == "SIMULATION_CREDIT":
            montant = result['montant_demande']
            mensualite = result['mensualite']
            duree = result['duree_mois']
            taux = result['taux_annuel']
            cout_total = result['cout_total']
            cout_credit = result['cout_credit']
            taux_endettement = result['taux_endettement']
            possible = result['pret_possible']

            status = "✅ Crédit réalisable" if possible else "⚠️ Attention"

            # Note de simulation (fix backslash in f-string issue)
            note_simulation = 'Cette simulation est indicative. Pour une demande formelle, veuillez nous contacter.' if possible else 'Votre taux d\'endettement dépasse 33%. Nous vous recommandons d\'ajuster le montant ou la durée.'

            return f"""{status}

Simulation de crédit :
• Montant demandé : {montant:,.0f} XOF
• Durée : {duree} mois
• Taux annuel : {taux}%

💰 Mensualité : {mensualite:,.0f} XOF
📊 Coût total du crédit : {cout_credit:,.0f} XOF
💳 Taux d'endettement : {taux_endettement:.1f}%

{result['recommandation']}

{note_simulation}"""

        elif intent == "DISCUSSION_COMPTE":
            transactions = result.get('transactions', [])
            if transactions:
                trans_text = "\n".join([
                    f"• {t['date']} - {t['libelle']} : {t['montant']:,.0f} XOF ({t['type']})"
                    for t in transactions[:3]
                ])
                return f"""Voici vos dernières opérations :

{trans_text}

Avez-vous des questions sur une opération en particulier ?"""
            else:
                return "Aucune opération récente trouvée sur votre compte."

        return "Opération effectuée."

    def _generate_error_response(self, intent: str, result: Dict) -> str:
        """Generate error response"""
        error = result.get('error', 'Une erreur s\'est produite')

        if "Solde insuffisant" in error:
            solde_dispo = result.get('solde_disponible', 0)
            return f"""❌ {error}

Solde disponible : {solde_dispo:,.0f} XOF

Souhaitez-vous modifier le montant ?"""

        return f"❌ {error}"

    def _llm_generate_response(self, intent: str, slots: Dict, result: Dict) -> str:
        """Use LLM to generate natural response (Claude-like)"""

        prompt = f"""Tu es un agent bancaire virtuel francophone pour une banque en Afrique de l'Ouest.
Ton rôle : expliquer clairement au client, sans inventer d'informations ni de chiffres.

Contexte technique (à ne pas répéter tel quel) :
Intent: {intent}
Slots: {json.dumps(slots, ensure_ascii=False)}
Résultat backend: {json.dumps(result, ensure_ascii=False)}

Rédige une réponse courte (2-4 lignes), claire, polie, adaptée à un client francophone.
Utilise des emojis si pertinent (✅, 💰, 📄).
Présente les chiffres de manière lisible (séparateurs de milliers).

Réponse :"""

        try:
            response = self._call_llm(prompt)
            return response.strip()
        except Exception as e:
            print(f"LLM response generation error: {e}")
            # Fallback to template
            return self._template_response(intent, slots, result)

    def generate_other_response(self, message: str) -> str:
        """Handle OTHER intent (smalltalk, out of scope)"""

        message_lower = message.lower()

        # Greetings
        if any(word in message_lower for word in ['bonjour', 'salut', 'hello', 'bonsoir', 'allo']):
            return "Bonjour ! Je suis votre assistant bancaire. Comment puis-je vous aider aujourd'hui ?"

        # Thanks
        if any(word in message_lower for word in ['merci', 'thanks']):
            return "Avec plaisir ! Autre chose ?"

        # Goodbye
        if any(word in message_lower for word in ['au revoir', 'bye', 'à bientôt']):
            return "Au revoir ! À bientôt pour vos opérations bancaires."

        # Confirmation
        if message_lower in ['oui', 'ok', 'd\'accord', 'daccord']:
            return "Très bien ! Comment puis-je vous aider ?"

        # Help / menu
        if any(word in message_lower for word in ['aide', 'help', 'menu', 'que peux-tu faire']):
            return """Je peux vous aider avec :

• Consulter votre solde
• Faire un virement
• Obtenir un relevé de compte
• Simuler un crédit
• Discuter de vos opérations

Que souhaitez-vous faire ?"""

        # Default
        return """Je n'ai pas bien compris votre demande.

Je peux vous aider avec :
• Soldes et comptes
• Virements
• Relevés
• Simulations de crédit

Comment puis-je vous aider ?"""

    def _format_code_assist_response(self, slots: Dict, result: Dict) -> str:
        """Format CODE_ASSIST response"""
        data = result
        response_parts = []

        # Header
        if data.get('file_path'):
            response_parts.append(f"📄 **Analyse de**: {data['file_path']}")
        elif data.get('function_name'):
            response_parts.append(f"🔍 **Recherche de**: {data['function_name']}")
        else:
            response_parts.append(f"💻 **Assistance Code**: {data.get('language', 'Python')}")

        response_parts.append("")

        # Repo results
        if data.get('repo_results'):
            response_parts.append("📁 **Résultats du repository**:")
            for i, repo_result in enumerate(data['repo_results'][:3], 1):
                path = repo_result.get('path', 'unknown')
                content = repo_result.get('content', '')[:200]
                response_parts.append(f"\n{i}. `{path}`")
                response_parts.append(f"   ```{data.get('language', '')}")
                response_parts.append(f"   {content}...")
                response_parts.append(f"   ```")
            response_parts.append("")

        # Web results
        if data.get('web_results'):
            response_parts.append("🌐 **Documentation et bonnes pratiques**:")
            for i, web_result in enumerate(data['web_results'][:3], 1):
                title = web_result.get('title', '')
                snippet = web_result.get('snippet', '')[:150]
                url = web_result.get('url', '')
                response_parts.append(f"\n{i}. **{title}**")
                response_parts.append(f"   {snippet}")
                response_parts.append(f"   [Lien]({url})")
            response_parts.append("")

        # Note
        if data.get('has_repo_context') or data.get('has_web_context'):
            response_parts.append("💡 *Pour une analyse détaillée avec LLM, utilisez `--use-ollama`*")
        else:
            response_parts.append("⚠️ Aucun résultat trouvé. Vérifiez le chemin/nom ou la requête.")

        return "\n".join(response_parts)

    def _call_llm(self, prompt: str) -> str:
        """Call LLM for response generation"""
        if not self.llm_model:
            return "Service LLM non disponible."

        try:
            # Use 7B model for banking flow responses (backend results already have the data)
            result = self.llm_model.generate(
                prompt,
                force_model=self.llm_model.fast_model_name,  # Use 7B for speed
                temperature=0.7,
                max_tokens=500
            )

            if isinstance(result, dict):
                return result.get('response', 'Désolé, je ne peux pas répondre.')
            return str(result)

        except Exception as e:
            print(f"[ResponseGenerator] LLM call error: {e}")
            return "Désolé, une erreur est survenue."

    def _handle_credit_simulation(self, session, user_message: str) -> Dict[str, Any]:
        """
        Handle credit simulation flow with persistent slot tracking.

        Args:
            session: SessionState object with credit_slots
            user_message: Current user message

        Returns:
            Dictionary with 'response', 'model_used', 'flow_complete'
        """
        # Initialize or get existing credit slots from session
        if not hasattr(session, 'credit_slots') or session.credit_slots is None:
            session.credit_slots = CreditSlots()
            session.in_credit_flow = True
            is_first_message = True
        else:
            is_first_message = False

        # Extract slots from current message and merge with existing
        session.credit_slots = self.credit_simulator.extract_slots_from_message(
            user_message,
            session.credit_slots
        )

        # Generate response based on current state
        response, is_complete = self.credit_simulator.get_next_response(
            session.credit_slots,
            is_first_message=is_first_message
        )

        # If complete, reset credit flow
        if is_complete:
            session.credit_slots = None
            session.in_credit_flow = False

        return {
            'response': response,
            'model_used': 'credit_simulator',
            'flow_complete': is_complete
        }

    def _handle_card_service(self, session, user_message: str) -> Dict[str, Any]:
        """
        Handle card service flow with persistent slot tracking.
        Supports: block, unblock, PIN reset/change, limit change, reissue

        Args:
            session: SessionState object with card_service_slots
            user_message: Current user message

        Returns:
            Dictionary with 'response', 'model_used', 'flow_complete'
        """
        # Initialize or get existing card slots from session
        if not hasattr(session, 'card_service_slots') or session.card_service_slots is None:
            session.card_service_slots = CardServiceSlots()
            session.in_card_service_flow = True
            is_first_message = True
        else:
            is_first_message = False

        # Extract slots from current message and merge with existing
        session.card_service_slots = self.card_services_handler.extract_slots_from_message(
            user_message,
            session.card_service_slots
        )

        # Generate response based on current state
        response, is_complete = self.card_services_handler.get_next_response(
            session.card_service_slots,
            is_first_message=is_first_message
        )

        # If complete, reset card service flow
        if is_complete:
            session.card_service_slots = None
            session.in_card_service_flow = False

        return {
            'response': response,
            'model_used': 'card_services_handler',
            'flow_complete': is_complete
        }

    def _handle_forex(self, session, user_message: str) -> Dict[str, Any]:
        """
        Handle forex exchange flow with persistent slot tracking.
        Supports: buy currency, sell currency, rate info

        Args:
            session: SessionState object with forex_slots
            user_message: Current user message

        Returns:
            Dictionary with 'response', 'model_used', 'flow_complete'
        """
        # Initialize or get existing forex slots from session
        if not hasattr(session, 'forex_slots') or session.forex_slots is None:
            session.forex_slots = ForexSlots()
            session.in_forex_flow = True
            is_first_message = True
        else:
            is_first_message = False

        # Extract slots from current message and merge with existing
        session.forex_slots = self.forex_handler.extract_slots_from_message(
            user_message,
            session.forex_slots
        )

        # Generate response based on current state
        response, is_complete = self.forex_handler.get_next_response(
            session.forex_slots,
            is_first_message=is_first_message
        )

        # If complete, reset forex flow
        if is_complete:
            session.forex_slots = None
            session.in_forex_flow = False

        return {
            'response': response,
            'model_used': 'forex_handler',
            'flow_complete': is_complete
        }

    def _handle_payment_incident(self, session, user_message: str) -> Dict[str, Any]:
        """
        Handle payment incident flow with persistent slot tracking.
        Supports: cheque_impaye, virement_rejete, prelevement_rejete, atd, saisie, contestation

        Args:
            session: SessionState object with payment_incident_slots
            user_message: Current user message

        Returns:
            Dictionary with 'response', 'model_used', 'flow_complete'
        """
        # Initialize or get existing incident slots from session
        if not hasattr(session, 'payment_incident_slots') or session.payment_incident_slots is None:
            session.payment_incident_slots = PaymentIncidentSlots()
            session.in_payment_incident_flow = True
            is_first_message = True
        else:
            is_first_message = False

        # Extract slots from current message and merge with existing
        session.payment_incident_slots = self.payment_incidents_handler.extract_slots_from_message(
            user_message,
            session.payment_incident_slots
        )

        # Generate response based on current state
        response, is_complete = self.payment_incidents_handler.get_next_response(
            session.payment_incident_slots,
            is_first_message=is_first_message
        )

        # If complete, reset incident flow
        if is_complete:
            session.payment_incident_slots = None
            session.in_payment_incident_flow = False

        return {
            'response': response,
            'model_used': 'payment_incidents_handler',
            'flow_complete': is_complete
        }

    def generate(self, session, intent: str, confidence: float, slots: Dict,
                 dialogue_state: Dict, rag_context: str = None,
                 backend_result: Dict = None) -> Dict[str, Any]:
        """
        Main generate method - routes to appropriate response generation

        Args:
            session: SessionState object
            intent: Detected intent
            confidence: Intent confidence
            slots: Extracted slots
            dialogue_state: Current dialogue state
            rag_context: RAG retrieved context (optional)
            backend_result: Backend execution result (optional)

        Returns:
            Dictionary with 'response' and 'model_used'
        """
        model_used = "fast"

        # Get user message from session history
        user_message = ""
        if session.history:
            for item in reversed(session.history):
                if 'user' in item:
                    user_message = item.get('user', '')
                    break

        # =====================================================================
        # CREDIT SIMULATION - Use dedicated flow handler
        # =====================================================================
        credit_intents = {"SIMULATION_CREDIT", "CREDIT_SIMULATION"}

        # Check if already in credit flow OR new credit intent detected
        in_credit_flow = getattr(session, 'in_credit_flow', False)

        if intent in credit_intents or in_credit_flow:
            # Use credit simulator for complete flow management
            result = self._handle_credit_simulation(session, user_message)
            return result

        # =====================================================================
        # CARD SERVICE FLOW - Block, Unblock, PIN, Limit changes
        # =====================================================================
        card_service_intents = {"CARD_BLOCK", "CARD_UNBLOCK", "CARD_PIN", "CARD_LIMIT"}
        in_card_flow = getattr(session, 'in_card_service_flow', False)

        if intent in card_service_intents or in_card_flow:
            result = self._handle_card_service(session, user_message)
            return result

        # =====================================================================
        # FOREX EXCHANGE FLOW - Buy, Sell, Rate info
        # =====================================================================
        forex_intents = {"FOREX_BUY", "FOREX_SELL", "FOREX_RATE"}
        in_forex_flow = getattr(session, 'in_forex_flow', False)

        if intent in forex_intents or in_forex_flow:
            result = self._handle_forex(session, user_message)
            return result

        # =====================================================================
        # PAYMENT INCIDENT FLOW - Cheques, Virements, ATD, Saisies, Contestations
        # =====================================================================
        incident_intents = {
            "INCIDENT_CHEQUE", "INCIDENT_VIREMENT", "INCIDENT_PRELEVEMENT",
            "INCIDENT_ATD", "INCIDENT_SAISIE", "CONTESTATION"
        }
        in_incident_flow = getattr(session, 'in_payment_incident_flow', False)

        if intent in incident_intents or in_incident_flow:
            result = self._handle_payment_incident(session, user_message)
            return result

        # Handle OTHER intent (general chat)
        if intent == "OTHER":
            # Get user message from session history
            user_message = ""
            if session.history:
                for item in reversed(session.history):
                    if 'user' in item:
                        user_message = item.get('user', '')
                        break

            # Use LLM for general response if available
            if self.llm_model and user_message:
                try:
                    # Determine conversation mode from dialogue state
                    conversation_mode = dialogue_state.get('state', 'OTHER')
                    needs_rag_flag = bool(rag_context)

                    # SIMPLE QUERIES (GREETING, CHITCHAT, etc.) -> Force 7B model
                    is_simple_query = conversation_mode in [
                        'GREETING', 'CHITCHAT', 'GENERAL_QUESTION',
                        'ASK_CAPABILITIES', 'OTHER'
                    ] and not needs_rag_flag

                    # Build prompt based on whether we have RAG context
                    if needs_rag_flag:
                        # RAG QUERY: Include document context with clear instructions
                        prompt = f"""Tu es un assistant bancaire AFG Bank professionnel.

DOCUMENTS DE RÉFÉRENCE (utilise ces informations pour répondre):
{rag_context}

QUESTION DU CLIENT: {user_message}

INSTRUCTIONS:
- Réponds en utilisant UNIQUEMENT les informations des documents ci-dessus
- Si l'information est dans les documents, cite les montants/tarifs exacts
- Si l'information n'est pas dans les documents, dis-le clairement
- Réponds de manière concise et professionnelle en français"""
                    else:
                        # SIMPLE QUERY: No RAG context needed
                        prompt = f"""Tu es un assistant bancaire AFG Bank professionnel et poli.

Message du client: {user_message}

Réponds de manière concise et professionnelle en français."""

                    # ROUTING STRATEGY:
                    # - Simple queries: force 7B for speed
                    # - RAG queries: use needs_rag=True which routes to 14B
                    if is_simple_query:
                        # Force fast model (7B) for simple queries
                        llm_result = self.llm_model.generate(
                            prompt,
                            force_model=self.llm_model.fast_model_name,
                            temperature=0.7,
                            max_tokens=500
                        )
                    else:
                        # RAG or complex queries -> 14B via needs_rag routing
                        llm_result = self.llm_model.generate(
                            prompt,
                            needs_rag=needs_rag_flag,
                            temperature=0.5,  # Lower temp for factual RAG answers
                            max_tokens=800
                        )
                    # Handle Dict response from DualModelLMStudio
                    if isinstance(llm_result, dict):
                        response = llm_result.get('response', '')
                        model_used = llm_result.get('model_used', 'fast')
                    else:
                        response = str(llm_result)
                        model_used = 'fast'
                    return {'response': response, 'model_used': model_used}
                except Exception as e:
                    print(f"LLM error: {e}")

            # Fallback to template
            response = self.generate_other_response(user_message or "bonjour")
            return {'response': response, 'model_used': 'template'}

        # Handle backend results
        if backend_result:
            if backend_result.get('success'):
                response = self.generate_action_response(intent, slots, backend_result)
            else:
                response = self._generate_error_response(intent, backend_result)
            return {'response': response, 'model_used': model_used}

        # Handle slot filling state
        state = dialogue_state.get('state', 'start')
        missing_slots = dialogue_state.get('missing_slots', [])

        if state == 'slot_filling' and missing_slots:
            response = self.generate_slot_question(intent, missing_slots[0], slots)
            return {'response': response, 'model_used': 'template'}

        # Handle confirmation
        if dialogue_state.get('needs_confirmation'):
            response = self.generate_confirmation_request(intent, slots)
            return {'response': response, 'model_used': 'template'}

        # =====================================================================
        # INTENT ROUTING - Use LLM for all intents with proper model selection
        # =====================================================================

        # Get user message from session history
        user_message = ""
        if session.history:
            for item in reversed(session.history):
                if 'user' in item:
                    user_message = item.get('user', '')
                    break

        if self.llm_model and user_message:
            # Define which intents need the 14B model (complex reasoning)
            complex_intents = {
                "SIMULATION_CREDIT", "CREDIT_SIMULATION",  # Credit calculations
                "CODE_ASSIST",                              # Code assistance
                "ANALYSE_JURIDIQUE",                        # Legal analysis
                "DEMANDE_AIDE",                             # Help requests needing understanding
            }

            # Simple intents use 7B (fast model)
            simple_intents = {
                "CONSULTER_SOLDE", "FAIRE_VIREMENT", "OBTENIR_RELEVE",
                "DISCUSSION_COMPTE", "CHECK_BALANCE", "TRANSFER_MONEY",
                "GREETING", "SALUTATION", "THANKS", "REMERCIEMENT",
                "GOODBYE", "CHITCHAT",
            }

            # Build intent-specific prompts
            intent_prompts = {
                # Banking Flow Intents
                "CONSULTER_SOLDE": f"""Tu es un assistant bancaire AFG Bank. Le client veut consulter son solde.
Message: {user_message}
Réponds de manière professionnelle. Explique que pour voir le solde, tu as besoin de vérifier son identité. Demande s'il est connecté ou s'il souhaite se connecter à son espace client.""",

                "CHECK_BALANCE": f"""Tu es un assistant bancaire AFG Bank. Le client veut consulter son solde.
Message: {user_message}
Réponds de manière professionnelle. Explique que pour voir le solde, tu as besoin de vérifier son identité.""",

                "FAIRE_VIREMENT": f"""Tu es un assistant bancaire AFG Bank. Le client veut faire un virement.
Message: {user_message}
Réponds de manière professionnelle. Demande les informations nécessaires: le montant, le bénéficiaire (nom ou IBAN), et si c'est un virement ponctuel ou permanent.""",

                "TRANSFER_MONEY": f"""Tu es un assistant bancaire AFG Bank. Le client veut faire un virement.
Message: {user_message}
Réponds de manière professionnelle. Demande les informations nécessaires pour le transfert.""",

                "OBTENIR_RELEVE": f"""Tu es un assistant bancaire AFG Bank. Le client veut obtenir un relevé de compte.
Message: {user_message}
Réponds de manière professionnelle. Demande pour quelle période (dernier mois, trimestre, année) et sous quel format (PDF, papier).""",

                "SIMULATION_CREDIT": f"""Tu es un assistant bancaire AFG Bank expert en crédit. Le client veut faire une simulation de crédit ou prêt.
Message: {user_message}

Réponds de manière professionnelle et engageante. Demande les informations nécessaires pour la simulation:
- Le montant souhaité (en FCFA)
- La durée du prêt (en mois ou années)
- Le type de projet (immobilier, consommation, auto, etc.)
- Les revenus mensuels approximatifs

Propose d'aider à trouver la meilleure offre et mentionne les taux compétitifs d'AFG Bank.""",

                "CREDIT_SIMULATION": f"""Tu es un assistant bancaire AFG Bank expert en crédit. Le client veut faire une simulation de crédit ou prêt.
Message: {user_message}

Réponds de manière professionnelle et engageante. Demande les informations nécessaires pour la simulation:
- Le montant souhaité (en FCFA)
- La durée du prêt (en mois ou années)
- Le type de projet (immobilier, consommation, auto, etc.)
- Les revenus mensuels approximatifs

Propose d'aider à trouver la meilleure offre et mentionne les taux compétitifs d'AFG Bank.""",

                "DISCUSSION_COMPTE": f"""Tu es un assistant bancaire AFG Bank. Le client veut discuter de son compte.
Message: {user_message}
Réponds de manière professionnelle. Demande de quoi il souhaite discuter: solde, opérations récentes, frais, options du compte, etc.""",

                # Greeting/Chitchat Intents
                "GREETING": f"""Tu es un assistant bancaire AFG Bank poli et professionnel.
Message: {user_message}
Réponds avec une salutation chaleureuse et propose ton aide pour les services bancaires.""",

                "SALUTATION": f"""Tu es un assistant bancaire AFG Bank poli et professionnel.
Message: {user_message}
Réponds avec une salutation chaleureuse et propose ton aide pour les services bancaires.""",

                "THANKS": f"""Tu es un assistant bancaire AFG Bank poli.
Message: {user_message}
Réponds poliment au remerciement et propose ton aide pour d'autres besoins.""",

                "REMERCIEMENT": f"""Tu es un assistant bancaire AFG Bank poli.
Message: {user_message}
Réponds poliment au remerciement et propose ton aide pour d'autres besoins.""",

                "GOODBYE": f"""Tu es un assistant bancaire AFG Bank poli.
Message: {user_message}
Réponds avec un au revoir chaleureux et rappelle que tu es disponible pour toute question future.""",

                "CHITCHAT": f"""Tu es un assistant bancaire AFG Bank sympathique.
Message: {user_message}
Réponds de manière amicale tout en restant professionnel. Propose ton aide pour les services bancaires.""",
            }

            prompt = intent_prompts.get(intent, f"""Tu es un assistant bancaire AFG Bank professionnel.
Message du client: {user_message}
Réponds de manière concise et utile en français.""")

            try:
                # Route to appropriate model based on intent complexity
                if intent in complex_intents:
                    # Complex intents → Use 14B for better reasoning
                    llm_result = self.llm_model.generate(
                        prompt,
                        force_model=self.llm_model.quality_model_name,  # Use 14B
                        temperature=0.5,  # Lower temp for calculations
                        max_tokens=600
                    )
                else:
                    # Simple intents → Use 7B for speed
                    llm_result = self.llm_model.generate(
                        prompt,
                        force_model=self.llm_model.fast_model_name,  # Use 7B
                        temperature=0.7,
                        max_tokens=400
                    )

                if isinstance(llm_result, dict):
                    response = llm_result.get('response', '')
                    model_used = llm_result.get('model_used', 'fast')
                else:
                    response = str(llm_result)
                    model_used = 'fast'

                return {'response': response, 'model_used': model_used}
            except Exception as e:
                print(f"[ResponseGenerator] Intent LLM error: {e}")

        # Fallback: static template messages (only if LLM fails)
        intent_messages = {
            "CONSULTER_SOLDE": "Je vais vérifier votre solde. Êtes-vous connecté à votre espace client ?",
            "FAIRE_VIREMENT": "Je vais préparer votre virement. Quel montant souhaitez-vous transférer et à qui ?",
            "OBTENIR_RELEVE": "Je prépare votre relevé de compte. Pour quelle période le souhaitez-vous ?",
            "SIMULATION_CREDIT": "Je vais simuler votre crédit. Quel montant souhaitez-vous emprunter et sur quelle durée ?",
            "CREDIT_SIMULATION": "Je vais simuler votre crédit. Quel montant souhaitez-vous emprunter et sur quelle durée ?",
            "DISCUSSION_COMPTE": "Je consulte vos informations de compte. De quoi souhaitez-vous discuter ?"
        }

        response = intent_messages.get(intent, "Comment puis-je vous aider ?")
        return {'response': response, 'model_used': 'template'}
