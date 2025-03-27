from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import json
from pathlib import Path

# Initialisation de FastAPI
app = FastAPI()

# ✅ Configuration CORS pour permettre les requêtes depuis le frontend Angular
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Chargement des formations depuis des fichiers JSON
json_dir = Path("content/json_clean/formations")
formations = [json.load(open(file, "r")) for file in json_dir.glob("*.json")]

# --------------------------
# ✅ Schémas de données pour l'application
# --------------------------

# Modèle du profil utilisateur
class UserProfile(BaseModel):
    nom: str
    situation_actuelle: str
    objectif: str
    niveau_actuel: str
    connaissances: List[str]
    attentes: str

# Message contextuel pour historique conversationnel
class MessageContext(BaseModel):
    sender: str  # "Utilisateur" ou "Assistant"
    text: str

# Modèle de requête enrichi côté Angular avec prompt, rôle et contexte
class ChatContext(BaseModel):
    prompt: str
    role: Optional[str] = "user"
    context: Optional[str] = None  # Contexte conversationnel (historique enrichi)

# Modèle de réponse renvoyée par l'API après traitement du contexte
class ChatContextResponse(BaseModel):
    response: str
    source_documents: Optional[List[str]] = None

# Modèle de réponse pour la recommandation de formation
class RecommendationResponse(BaseModel):
    recommandation: str
    details: Optional[dict] = None
    formation_link: Optional[str] = None
    message: Optional[str] = None

# --------------------------
# ✅ Endpoint principal pour traitement des requêtes du chatbot
# --------------------------
@app.post("/query", response_model=ChatContextResponse)
def query(chat: ChatContext):
    # Extraction des données envoyées par Angular
    prompt = chat.prompt
    role = chat.role
    context = chat.context

    # 🖥️ Affichage dans la console du contexte reçu pour débogage ou validation
    print(f"\n📌 Contexte reçu depuis Angular :\n{context}\n")

    # ✅ À cet endroit Mohammed peut intégrer directement le modèle LLM/RAG
    # par exemple : llm.generate(prompt, context)

    # Réponse temporaire simulée en attendant l'intégration finale
    fake_response = f"Réponse simulée tenant compte du contexte pour : '{prompt}'"
    fake_sources = [
        "content/json_clean/formations/Formation_Python_Data_Visualisation.json",
        "content/json_clean/formations/Formation_Power_BI.json"
    ]

    # Retourner la réponse simulée
    return ChatContextResponse(
        response=fake_response,
        source_documents=fake_sources
    )

# --------------------------
# ✅ Logique avancée d'analyse et enrichissement du contexte conversationnel
# --------------------------
def enrichir_reponse_avec_contexte(prompt: str, context: Optional[List[MessageContext]]) -> str:
    """
    ⚙️ Fonction simulant une logique avancée qui intègre le contexte conversationnel
    au prompt avant de l'envoyer au modèle LLM/RAG.
    """

    # Construction du contexte historique à partir des échanges précédents
    if context:
        historique = "\n".join([f"{msg.sender}: {msg.text}" for msg in context])
        contexte_final = f"Historique conversationnel:\n{historique}\n\nQuestion actuelle: {prompt}"
    else:
        contexte_final = prompt

    # 🖨️ Affichage du contexte enrichi dans la console pour validation
    print("[🧠 Contexte enrichi pour le LLM]", contexte_final)

    # Retourne une réponse simulée enrichie avec le contexte
    return f"Voici une réponse contextualisée simulée pour : '{prompt}', tenant compte de l'historique."

# --------------------------
# ✅ Endpoint pour recommander une formation en fonction du profil utilisateur
# --------------------------
@app.post("/recommend", response_model=RecommendationResponse)
def recommend(profile: UserProfile):
    # Extraction des critères utilisateur depuis son profil
    criteres = extraire_criteres(profile)

    # Recherche d'une formation adaptée selon les critères du profil
    formation = match_formation(criteres, formations)

    # Vérification si une formation adaptée est trouvée
    if formation:
        return RecommendationResponse(
            recommandation=formation["titre"],
            details={
                "objectifs": formation.get("objectifs"),
                "public": formation.get("public")
            },
            formation_link=formation.get("lien", "#")
        )
    else:
        return RecommendationResponse(
            recommandation="Aucune formation pertinente trouvée.",
            message="Proposer un bilan de compétences.",
            formation_link=None
        )

# --------------------------
# ✅ Fonctions utilitaires pour l'analyse et la recommandation de formations
# --------------------------
def extraire_criteres(profil: UserProfile):
    """
    🛠️ Extrait les critères pertinents du profil utilisateur pour faciliter
    le matching avec les formations disponibles.
    """

    objectifs = [profil.objectif] + profil.attentes.split(",")
    objectifs = [o.strip() for o in objectifs]  # Nettoyage des objectifs

    competences = [profil.niveau_actuel] + profil.connaissances

    # Ciblage spécifique selon la situation actuelle (simplifié ici)
    public = ["étudiants"] if "étudiant" in profil.situation_actuelle.lower() else ["tout public"]

    return {
        "objectifs": objectifs,
        "competences": competences,
        "public": public
    }

def match_formation(criteres, formations):
    """
    🔍 Cherche parmi les formations disponibles une correspondance avec les critères.
    Retourne la première formation adaptée trouvée.
    """

    for formation in formations:
        if any(obj in formation.get("objectifs", []) for obj in criteres["objectifs"]) or \
           any(comp in formation.get("prerequis", []) for comp in criteres["competences"]) or \
           any(p in formation.get("public", []) for p in criteres["public"]):
            return formation
    return None
