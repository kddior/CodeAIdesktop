# -*- coding: utf-8 -*-
"""
Comprehensive Question Generation Prompts
Section-specific prompts covering ALL sections of AFG Bank tariff document

Document Structure:
1. Conditions Générales du Compte (50 questions)
2. Moyens de Paiement (100 questions)
3. Services Bancaires (80 questions)
4. Banque à Distance (40 questions)
5. Incidents de Paiements (30 questions)
6. Opérations sur Titres (30 questions)
7. Opérations de Change (40 questions)
8. Opérations de Crédit (120 questions)
9. Opérations avec l'Étranger (80 questions)
10. Autres Services Divers (50 questions)

Total: 620 questions covering full document
"""

# Prompt categories with specialized instructions
COMPREHENSIVE_PROMPTS = {
    "section1_compte": {
        "name": "Section 1: Conditions Générales du Compte",
        "count": 50,
        "prompt": """
Génère 50 questions variées sur la Section 1 du document AFG Bank : "Conditions Générales du Compte".

Cette section couvre :
- Ouverture de compte (frais, documents requis)
- Clôture de compte (procédure, attestation)
- Attestation de clôture de compte (50 000 FCFA)
- Attestation de clôture (50 000 FCFA)
- Changement de signature (Gratuit)
- Modification de spécimen de signature
- Carte d'identité bancaire
- Documents administratifs liés au compte

Contraintes :
- 20% clean (français parfait)
- 40% moderate (fautes légères, sans accents)
- 40% extreme (style WhatsApp, vocal transcrit, fautes lourdes)
- Styles : whatsapp, vocal, corporate, casual
- Interjections ivoiriennes : "hein", "svp", "là même", "ou bien"
- Reformulations : "le papier pour fermer compte", "le truc d'ouverture", "changer signature"

Format JSON:
{{
  "questions": [
    {{
      "text": "la question ici",
      "noise_level": "clean|moderate|extreme",
      "style": "whatsapp|vocal|corporate|casual",
      "expected_keywords": ["mot1", "mot2"],
      "expected_doc_type": "tarif"
    }}
  ]
}}

Retourne UNIQUEMENT le JSON, rien d'autre.
        """
    },

    "section2_paiements": {
        "name": "Section 2: Moyens de Paiement",
        "count": 100,
        "prompt": """
Génère 100 questions sur la Section 2 : "Services Rattachés au Fonctionnement du Compte - Moyens de Paiement".

Sous-sections à couvrir :
1. Chèques (carnet, formule, opposition, rejet)
2. Cartes bancaires :
   - Visa Business (tarifs, 2ème carte, renouvellement)
   - Cartes prépayées
   - Frais annuels, opposition, retrait
3. Virements :
   - Locaux (en agence, e-banking)
   - UEMOA (vers autres pays CEDEAO)
   - SEPA / Swift (international)
   - Frais par tranche de montant
4. Prélèvements automatiques
5. Effets de commerce (LCN, traite, etc.)

Inclure :
- Variantes : "virement", "transfert", "envoi argent", "passer de l'argent"
- Fautes : "vizaa", "carnai de chek", "viremant", "oposition"
- Questions précises : "combien coûte un virement Swift de 10 millions ?"
- Questions vagues : "envoyer de l'argent à l'étranger c combien ?"

Format JSON:
{{
  "questions": [
    {{
      "text": "la question ici",
      "noise_level": "clean|moderate|extreme",
      "style": "whatsapp|vocal|corporate|casual",
      "expected_keywords": ["mot1", "mot2"],
      "expected_doc_type": "tarif"
    }}
  ]
}}

Retourne UNIQUEMENT le JSON.
        """
    },

    "section3_services": {
        "name": "Section 3: Services Bancaires",
        "count": 80,
        "prompt": """
Génère 80 questions sur la Section 3 : "Services Bancaires".

Couvre :
- Dates de valeur (compensation, encaissement)
- Frais de gestion et tenue de compte
- Relevés de compte (papier, électronique, duplicata)
- Attestations diverses (solde, IBAN, RIB)
- Recherche de documents anciens
- Photocopies / duplicatas
- Commissions de mouvement
- Frais de tenue de dossier
- Redevance trimestrielle / annuelle
- Inactivité de compte

Variantes :
- "relevé de compte", "papier du compte", "voir mes mouvements"
- "attestation IBAN", "le code du compte", "RIB"
- "combien pour avoir mes anciens relevés ?"
- "frais de garde du compte", "tenir le dossier"

Inclure toutes difficultés : clean, moderate, extreme.

Format JSON:
{{
  "questions": [
    {{
      "text": "la question ici",
      "noise_level": "clean|moderate|extreme",
      "style": "whatsapp|vocal|corporate|casual",
      "expected_keywords": ["mot1", "mot2"],
      "expected_doc_type": "tarif"
    }}
  ]
}}

Retourne UNIQUEMENT le JSON.
        """
    },

    "section4_distance": {
        "name": "Section 4: Banque à Distance",
        "count": 40,
        "prompt": """
Génère 40 questions sur la Section 4 : "Services de Banque à Distance".

Couvre :
- e-Bank / e-Banking (accès en ligne)
- Virements électroniques via internet
- Consultation de solde en ligne
- Mobile banking (AFG Mobile)
- SMS banking
- Frais d'abonnement / activation
- Frais de transaction en ligne
- Aide technique / support

Variantes :
- "banque en ligne", "internet banking", "voir mon compte sur le téléphone"
- "faire virement par internet", "envoyer argent en ligne"
- "application mobile", "AFG app", "mobile money"
- "c combien pour utiliser le site web ?"

Format JSON:
{{
  "questions": [
    {{
      "text": "la question ici",
      "noise_level": "clean|moderate|extreme",
      "style": "whatsapp|vocal|corporate|casual",
      "expected_keywords": ["mot1", "mot2"],
      "expected_doc_type": "tarif"
    }}
  ]
}}

Retourne UNIQUEMENT le JSON.
        """
    },

    "section5_incidents": {
        "name": "Section 5: Gestion des Incidents de Paiements",
        "count": 30,
        "prompt": """
Génère 30 questions sur la Section 5 : "Gestion des Incidents de Paiements".

Couvre :
- Rejet de chèque (insuffisance de provision)
- Frais d'incident (commission, pénalité)
- Opposition sur chèque / carte
- Fraude bancaire (déclaration, frais)
- Régularisation de compte
- Lettre d'incident / mise en demeure
- Clôture de compte pour incident

Variantes :
- "mon chèque a été rejeté, c combien les frais ?"
- "opposition carte volée"
- "incident de paiement", "chèque sans provision"
- "combien ça coûte quand le chèque passe pas ?"

Format JSON:
{{
  "questions": [
    {{
      "text": "la question ici",
      "noise_level": "clean|moderate|extreme",
      "style": "whatsapp|vocal|corporate|casual",
      "expected_keywords": ["mot1", "mot2"],
      "expected_doc_type": "tarif"
    }}
  ]
}}

Retourne UNIQUEMENT le JSON.
        """
    },

    "section6_titres": {
        "name": "Section 6: Opérations sur Titres",
        "count": 30,
        "prompt": """
Génère 30 questions sur la Section 6 : "Opérations sur Titres".

Couvre :
- Achat / vente d'actions
- Obligations (souscription, cession)
- Bons du Trésor
- Titres BRVM (Bourse Régionale des Valeurs Mobilières)
- Frais de courtage
- Garde de titres
- Dividendes (perception, virement)

Variantes :
- "acheter des actions", "investir en bourse"
- "bons du trésor", "obligations d'état"
- "combien coûte le courtage ?"
- "frais pour garder mes titres"

Format JSON:
{{
  "questions": [
    {{
      "text": "la question ici",
      "noise_level": "clean|moderate|extreme",
      "style": "whatsapp|vocal|corporate|casual",
      "expected_keywords": ["mot1", "mot2"],
      "expected_doc_type": "tarif"
    }}
  ]
}}

Retourne UNIQUEMENT le JSON.
        """
    },

    "section7_change": {
        "name": "Section 7: Opérations de Change",
        "count": 40,
        "prompt": """
Génère 40 questions sur la Section 7 : "Opérations de Change".

Couvre :
- Achat / vente de devises (EUR, USD, GBP, etc.)
- Taux de change (commission, marge)
- Change manuel (espèces)
- Change scripturaire (virement en devises)
- Frais de conversion
- Change pour voyage / import / export

Variantes :
- "changer FCFA en euros", "acheter des dollars"
- "taux de change", "combien vaut 1 euro ?"
- "commission sur le change"
- "frais pour convertir mon argent en USD"

Format JSON:
{{
  "questions": [
    {{
      "text": "la question ici",
      "noise_level": "clean|moderate|extreme",
      "style": "whatsapp|vocal|corporate|casual",
      "expected_keywords": ["mot1", "mot2"],
      "expected_doc_type": "tarif"
    }}
  ]
}}

Retourne UNIQUEMENT le JSON.
        """
    },

    "section8_credit": {
        "name": "Section 8: Opérations de Crédit",
        "count": 120,
        "prompt": """
Génère 120 questions sur la Section 8 : "Opérations de Crédit".

Sous-sections complètes :
1. Découvert autorisé (frais, taux d'intérêt)
2. Crédit court terme (moins de 1 an)
   - Facilité de caisse
   - Crédit de campagne
   - Crédit de trésorerie
3. Crédit moyen terme (1-5 ans)
   - Équipement
   - Véhicules
   - Matériel informatique
4. Crédit long terme (5+ ans)
   - Immobilier
   - Investissement lourd
5. Cautions et garanties
   - Caution de marché
   - Caution douanière
   - Caution fiscale
   - Garantie bancaire
6. Crédit documentaire (import/export)
7. Affacturage
8. Leasing / crédit-bail

Variantes :
- "prêt", "emprunt", "financement", "crédit"
- "découvert sur mon compte"
- "caution pour marché public"
- "crédit pour acheter un véhicule"
- "financement équipement industriel"

Inclure questions sur :
- Taux d'intérêt
- Frais de dossier
- Assurance emprunteur
- Garanties requises
- Durée de crédit

Format JSON:
{{
  "questions": [
    {{
      "text": "la question ici",
      "noise_level": "clean|moderate|extreme",
      "style": "whatsapp|vocal|corporate|casual",
      "expected_keywords": ["mot1", "mot2"],
      "expected_doc_type": "tarif"
    }}
  ]
}}

Retourne UNIQUEMENT le JSON.
        """
    },

    "section9_etranger": {
        "name": "Section 9: Opérations avec l'Étranger",
        "count": 80,
        "prompt": """
Génère 80 questions sur la Section 9 : "Opérations avec l'Étranger".

Couvre :
1. Encaissement de chèques étrangers
2. Transferts internationaux (Swift, Western Union, MoneyGram)
3. Rapatriement de fonds
4. Opérations documentaires :
   - Crédit documentaire import
   - Crédit documentaire export
   - Remise documentaire
5. Commerce international
   - Lettre de crédit stand-by
   - Garantie internationale
6. Domiciliation import/export
7. Envoi / réception argent depuis l'étranger

Variantes :
- "recevoir argent de France", "envoyer argent au Canada"
- "encaisser chèque américain"
- "Western Union frais"
- "crédit documentaire pour importer"
- "swift transfer cost"
- "combien pour domicilier une facture d'import ?"

Format JSON:
{{
  "questions": [
    {{
      "text": "la question ici",
      "noise_level": "clean|moderate|extreme",
      "style": "whatsapp|vocal|corporate|casual",
      "expected_keywords": ["mot1", "mot2"],
      "expected_doc_type": "tarif"
    }}
  ]
}}

Retourne UNIQUEMENT le JSON.
        """
    },

    "section10_autres": {
        "name": "Section 10: Autres Services Divers",
        "count": 50,
        "prompt": """
Génère 50 questions sur la Section 10 : "Autres Services Divers".

Couvre :
- Recherche de documents (chèques anciens, relevés, historique)
- Succession (ouverture dossier, déblocage fonds)
- Procuration sur compte
- Saisie / blocage de compte (justice)
- Coffre-fort (location, accès)
- Conseil financier / consulting
- Audit de compte
- Attestation fiscale
- Service premium / VIP
- Formation bancaire entreprise

Variantes :
- "rechercher un vieux chèque de 2018"
- "ouvrir succession de mon père décédé"
- "louer un coffre à la banque"
- "procuration pour ma femme"
- "combien coûte un audit de mes comptes ?"

Format JSON:
{{
  "questions": [
    {{
      "text": "la question ici",
      "noise_level": "clean|moderate|extreme",
      "style": "whatsapp|vocal|corporate|casual",
      "expected_keywords": ["mot1", "mot2"],
      "expected_doc_type": "tarif"
    }}
  ]
}}

Retourne UNIQUEMENT le JSON.
        """
    },

    # Auxiliary prompts for stress testing
    "cross_section_fuzzy": {
        "name": "Questions Floues Inter-Sections",
        "count": 50,
        "prompt": """
Génère 50 questions floues qui mélangent plusieurs sections du document AFG Bank.

Style :
- Questions vagues qui ne mentionnent pas exactement les termes techniques
- Mélange de services (ex: "je veux changer signature et fermer compte en même temps")
- Confusion entre services similaires
- Style WhatsApp/vocal très désordonné

Exemples :
- "le papier la pour cloturer le compte et changer signature c combien tout ?"
- "visa business la avec virement international c possible ?"
- "si je veux credit et ouvrir compte entreprise ya des frais ?"

Format JSON:
{{
  "questions": [
    {{
      "text": "la question ici",
      "noise_level": "extreme",
      "style": "whatsapp|vocal",
      "expected_keywords": ["mot1", "mot2"],
      "expected_doc_type": "tarif"
    }}
  ]
}}

Retourne UNIQUEMENT le JSON.
        """
    },

    "extreme_noise_stt": {
        "name": "Bruit Extrême + STT Errors",
        "count": 30,
        "prompt": """
Génère 30 questions avec bruit maximal + erreurs de transcription vocale automatique.

Caractéristiques :
- Erreurs STT : "clôture" → "clau tur" / "close tour" / "klo tour"
- Mots fusionnés : "combiencoute", "lespapiers"
- Accents manquants à 100%
- Fautes graves : "attestasion", "signatir", "carnai chek"
- Hésitations vocales : "heu", "donc", "attends", "bon voilà"
- Répétitions
- Ponctuation absente

Exemples :
- "heu donc voila je voulais savoir pour lattesta attestation de clau tur la"
- "bon attends le papier pour ferme le cont entreprise c combien déjà"

Format JSON:
{{
  "questions": [
    {{
      "text": "la question ici",
      "noise_level": "extreme",
      "style": "vocal",
      "expected_keywords": ["mot1"],
      "expected_doc_type": "tarif"
    }}
  ]
}}

Retourne UNIQUEMENT le JSON.
        """
    }
}


def get_prompt(category: str) -> dict:
    """Get prompt configuration by category"""
    return COMPREHENSIVE_PROMPTS.get(category, None)


def get_all_categories() -> list:
    """Get list of all prompt categories"""
    return list(COMPREHENSIVE_PROMPTS.keys())


def get_total_question_count() -> int:
    """Get total number of questions across all prompts"""
    return sum(p['count'] for p in COMPREHENSIVE_PROMPTS.values())
