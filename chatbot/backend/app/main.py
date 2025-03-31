"""
main.py

Exemple d'API FastAPI utilisant pandas pour charger 
des fichiers JSON de formations et effectuer un 
"partial matching" sur l'objectif et les compétences 
de l'utilisateur.

Endpoints:
  - POST /recommend : reçoit un profil utilisateur, 
    renvoie la formation la plus adaptée (ou "Aucune formation...").
  - POST /query : simulation de conversation 
    (réponse fictive).

Nécessite:
  - fastapi, uvicorn, pydantic, pandas, openpyxl (en cas de manip xlsx), etc.
  - un dossier content/json_clean/formations contenant plusieurs fichiers .json
    au format:
      {
        "titre": "Formation Python Data",
        "objectifs": ["Analyser des données", "Maîtriser Python"],
        "prerequis": ["Python", "Bases de programmation"],
        "public": ["tout public"],
        "lien": "https://exemple.com/formation-python-data"
      }

Pour exécuter:
  uvicorn main:app --reload
Puis accéder aux endpoints via http://127.0.0.1:8000/docs
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import pandas as pd
import json
from pathlib import Path

# ===========================
# == Création de l'API    ==
# ===========================

app = FastAPI(
    title="Chatbot Formation API (Pandas version)",
    version="1.0.0",
    description="API de recommandation de formations utilisant pandas."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],  # Autorise le front Angular local
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =====================================
# == Chargement des formations via DF ==
# =====================================

def load_formations_to_df(json_dir: Path) -> pd.DataFrame:
    """
    Parcourt tous les fichiers *.json dans json_dir et construit 
    un DataFrame contenant des colonnes : 
      - titre
      - objectifs (liste)
      - prerequis (liste)
      - public (liste)
      - lien
    """
    records = []
    for file in json_dir.glob("*.json"):
        with open(file, "r", encoding="utf-8") as f:
            formation = json.load(f)
            records.append({
                "titre": formation.get("titre", ""),
                "objectifs": formation.get("objectifs", []),
                "prerequis": formation.get("prerequis", []),
                "public": formation.get("public", []),
                "lien": formation.get("lien", "")
            })
    if len(records) == 0:
        # On retourne un DF vide si aucun fichier trouvé
        return pd.DataFrame(columns=["titre", "objectifs", "prerequis", "public", "lien"])
    return pd.DataFrame(records)

# Dossier contenant les JSON
json_dir = Path("content/json_clean/formations")
df_formations = load_formations_to_df(json_dir)


# ======================================
# == Décomposition champ user          ==
# ======================================

def extract_keywords(objective: str, knowledge: str) -> List[str]:
    """
    Sépare l'objectif et les compétences (knowledge) 
    en une liste de mots-clés distincts.

    Exemple:
      objective = "Devenir Data Analyst"
      knowledge = "python, sql"
      => tokens = ["devenir", "data", "analyst", "python", "sql"]
    """
    # Mise en minuscules + remplacement de virgules par espaces
    obj_str = objective.lower().replace(",", " ")
    knw_str = knowledge.lower().replace(",", " ")

    # Séparation par espaces
    obj_tokens = obj_str.split()
    knw_tokens = knw_str.split()

    # Fusion
    all_tokens = obj_tokens + knw_tokens

    # On supprime les éventuels doublons
    unique_tokens = list(set(all_tokens))

    # On retire les tokens vides (dans le cas où l'utilisateur laisse un champ vide)
    unique_tokens = [t.strip() for t in unique_tokens if t.strip()]
    return unique_tokens

# ===========================================
# == Fonctions de matching dans le DF      ==
# ===========================================

def partial_match_formations(df: pd.DataFrame, tokens: List[str]) -> pd.DataFrame:
    """
    Filtre le DataFrame pour ne garder que les formations 
    dont 'objectifs' ou 'prerequis' contiennent 
    (en substring) au moins un des tokens donnés.

    :param df: Le DataFrame des formations
    :param tokens: Liste de mots-clés en minuscules
    :return: Sous-DataFrame des formations qui matchent
    """
    if df.empty or not tokens:
        return df.iloc[0:0]  # renvoie un df vide

    # Création de colonnes string pour les comparaisons substring
    # On regroupe les items (objectifs/prerequis) en une seule chaîne
    df = df.copy()
    df["objectifs_str"] = df["objectifs"].apply(lambda lst: " ".join(str(x).lower() for x in lst))
    df["prerequis_str"] = df["prerequis"].apply(lambda lst: " ".join(str(x).lower() for x in lst))

    def row_matches(row) -> bool:
        for token in tokens:
            # partial matching => "python" in "maîtriser python"
            if token in row["objectifs_str"] or token in row["prerequis_str"]:
                return True
        return False

    mask = df.apply(row_matches, axis=1)
    return df[mask]

# ===========================================
# == Schémas Pydantic pour l'API           ==
# ===========================================

class UserProfile(BaseModel):
    """
    Représente le profil utilisateur :
      - name : Nom
      - objective : Objectif / but
      - level : Niveau (ex: Débutant)
      - knowledge : Compétences (champ texte)
    """
    name: str
    objective: str
    level: str
    knowledge: str
    recommended_course: Optional[str] = None

class RecommendRequest(BaseModel):
    """
    Requête pour l'endpoint /recommend
    """
    profile: UserProfile

class RecommendResponse(BaseModel):
    """
    Réponse renvoyée par /recommend
    """
    recommended_course: str
    reply: str

class QueryRequest(BaseModel):
    """
    Requête pour l'endpoint /query
    (pas de logique LLM réelle ici, simple placeholder)
    """
    profile: UserProfile
    history: List[dict] = []
    question: str

class QueryResponse(BaseModel):
    """
    Réponse renvoyée par /query
    """
    reply: str

# ===========================================
# == Endpoint /query                       ==
# ===========================================

@app.post("/query", response_model=QueryResponse)
def query_endpoint(req: QueryRequest):
    """
    Simule une conversation. 
    Ne fait qu'écho de la question pour le moment.
    """
    question = req.question.strip()
    return QueryResponse(reply=f"Réponse fictive (pas de LLM) à la question '{question}'.")

# ===========================================
# == Endpoint /recommend                   ==
# ===========================================

@app.post("/recommend", response_model=RecommendResponse)
def recommend_endpoint(r: RecommendRequest):
    """
    Reçoit un profil utilisateur, extrait les mots-clés 
    depuis objective et knowledge, 
    puis effectue un partial matching dans le DataFrame df_formations.
    Retourne la première formation qui correspond, sinon un fallback.
    """
    p = r.profile
    tokens = extract_keywords(p.objective, p.knowledge)

    # Filtre des formations
    matched_df = partial_match_formations(df_formations, tokens)

    if not matched_df.empty:
        # On prend la première formation matchée, par exemple
        match = matched_df.iloc[0]
        titre = match["titre"]
        reply_message = (
            f"Formation trouvée: '{titre}'. "
            f"Objectifs: {match['objectifs']} "
            f"Prérequis: {match['prerequis']}"
        )
        return RecommendResponse(
            recommended_course=str(titre),
            reply=reply_message
        )
    else:
        return RecommendResponse(
            recommended_course="Aucune formation pertinente",
            reply="Aucune formation ne correspond aux mots-clés fournis (via pandas)."
        )
