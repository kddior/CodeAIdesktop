"""
Response Generator - LLM as the final "writer/explainer"
Similar to how Claude generates natural responses
"""

from typing import Dict, Any, Optional
import json


class ResponseGenerator:
    """
    Generate natural language responses using LLM
    The LLM only explains and formats - never invents data
    """

    def __init__(self, llm_model=None):
        self.llm_model = llm_model

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
        """Call LLM - placeholder"""
        # In production, this calls Qwen
        return "Réponse LLM placeholder"
