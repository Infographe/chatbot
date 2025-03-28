from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import json
from pathlib import Path

app = FastAPI()

# Configuration CORS pour autoriser Angular
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Chargement des formations JSON
json_dir = Path("content/json_clean/formations")
formations = []
try:
    for file in json_dir.glob("*.json"):
        with open(file, "r") as f:
            data = json.load(f)
            formations.append(data)
except Exception as e:
    print(f"[ERREUR] Impossible de charger les formations : {e}")

# -------------------------------------
# Modèles
# -------------------------------------

class UserProfile(BaseModel):
    nom: str
    situation_actuelle: str
    objectif: str
    niveau_actuel: str
    connaissances: List[str]
    attentes: str

class MessageContext(BaseModel):
    sender: str
    text: str

class ChatContext(BaseModel):
    prompt: str
    role: Optional[str] = "user"
    context: Optional[str] = None

class ChatContextResponse(BaseModel):
    response: str
    source_documents: Optional[List[str]] = None

class RecommendationResponse(BaseModel):
    recommandation: str
    details: Optional[dict] = None
    formation_link: Optional[str] = None
    message: Optional[str] = None

# -------------------------------------
# Endpoint principal /query
# -------------------------------------
@app.post("/query", response_model=ChatContextResponse)
def query(chat: ChatContext):
    """
    Reçoit un 'prompt', un 'role' et un 'context' (historique + profil).
    Retourne une réponse simulée pour le moment.
    """
    prompt = chat.prompt
    role = chat.role
    context = chat.context

    # Log du contexte reçu
    print("\n[DEBUG] /query - Contexte reçu :")
    print(context)

    # Simulation d'une réponse (Mohammed branchera son LLM ici)
    fake_response = f"Réponse simulée pour : '{prompt}' (role={role}), tenant compte du contexte."
    fake_sources = [
        "Formation_Python_Data_Visualisation.json",
        "Formation_Power_BI.json"
    ]

    return ChatContextResponse(response=fake_response, source_documents=fake_sources)

# -------------------------------------
# Logique de Recommandation
# -------------------------------------

@app.post("/recommend", response_model=RecommendationResponse)
def recommend(profile: UserProfile):
    """
    Reçoit un profil utilisateur (POST),
    et renvoie la formation la plus adaptée ou un fallback.
    """
    criteres = extraire_criteres(profile)
    formation = match_formation(criteres, formations)

    if formation:
        return RecommendationResponse(
            recommandation=formation["titre"],
            details={
                "objectifs": formation.get("objectifs", []),
                "public": formation.get("public", [])
            },
            formation_link=formation.get("lien", "#")
        )
    else:
        return RecommendationResponse(
            recommandation="Aucune formation pertinente trouvée.",
            message="Proposer un bilan de compétences.",
            formation_link=None
        )


# -------------------------------------
# Fonctions utilitaires
# -------------------------------------

def extraire_criteres(profil: UserProfile) -> dict:
    """
    Extrait les critères utiles du profil :
     - objectifs
     - compétences (niveau + connaissances)
     - public
    """
    objectifs = [profil.objectif] + profil.attentes.split(",")
    objectifs = [o.strip().lower() for o in objectifs]

    competences = [profil.niveau_actuel.lower()] + [c.lower() for c in profil.connaissances]

    # Public 'étudiants' ou 'tout public'
    public = ["étudiants"] if "étudiant" in profil.situation_actuelle.lower() else ["tout public"]

    return {
        "objectifs": objectifs,
        "competences": competences,
        "public": public
    }

def match_formation(criteres: dict, formations: list) -> Optional[dict]:
    """
    Recherche la première formation qui correspond
    aux objectifs, prérequis ou public.
    """
    for formation in formations:
        # On fait un to-lower sur la formation pour comparer
        formation_objectifs = [obj.lower() for obj in formation.get("objectifs", [])]
        formation_prerequis = [pr.lower() for pr in formation.get("prerequis", [])]
        formation_public = [p.lower() for p in formation.get("public", [])]

        # Condition de match
        if any(obj in formation_objectifs for obj in criteres["objectifs"]) \
           or any(comp in formation_prerequis for comp in criteres["competences"]) \
           or any(pub in formation_public for pub in criteres["public"]):
            return formation
    return None
