"""
main.py

Exemple d'API FastAPI + pandas, avec chargement de fichiers JSON 
depuis le dossier "content", puis partial matching sur 
l'objectif et les compétences de l'utilisateur.

- POST /recommend : reçoit un profil, renvoie une formation adaptée ou un fallback.
- POST /query : simulation de conversation (réponse fictive).

Nécessite: fastapi, uvicorn, pandas, etc.
Pour lancer:
    uvicorn main:app --reload
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

import pandas as pd
import json
from pathlib import Path

# ===========================================
# == Création de l'API FastAPI            ==
# ===========================================
app = FastAPI(
    title="Chatbot Formation API (Pandas + dossier content)",
    version="1.0.0",
    description="API de recommandation de formations utilisant pandas, avec chargement JSON depuis 'content'."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===========================================
# == Détermination du chemin absolu         ==
# ===========================================
# L'objectif est de pointer vers le dossier "content" 
# où se trouvent désormais tous les fichiers .json.

CURRENT_FILE = Path(__file__).resolve()
print("[DEBUG] __file__ =", __file__)
print("[DEBUG] CURRENT_FILE =", CURRENT_FILE)

# Supposons que main.py est dans 'app/' (ou la racine).
# .parent => dossier contenant main.py
# .parent.parent => si besoin de remonter un niveau supplémentaire
# Ajuster selon l'emplacement réel :
BASE_DIR = CURRENT_FILE.parent  # si main.py est à la racine, c'est suffisant
# Si main.py est dans 'app/', alors => BASE_DIR = CURRENT_FILE.parent.parent
# À adapter selon la hiérarchie exacte.

print("[DEBUG] BASE_DIR =", BASE_DIR)

DATA_FOLDER = BASE_DIR / "content"
print("[DEBUG] DATA_FOLDER =", DATA_FOLDER, "| exists?", DATA_FOLDER.exists())

# ============================================
# == Chargement des formations en DataFrame ==
# ============================================

def load_formations_to_df(json_dir: Path) -> pd.DataFrame:
    """
    Parcourt tous les fichiers *.json dans 'json_dir',
    et construit un DataFrame avec:
      - titre
      - objectifs (liste)
      - prerequis (liste)
      - programme (liste)
      - public (liste)
      - lien
    Ajoute des prints pour vérifier le contenu.
    """
    print("\n[DEBUG] Chargement des formations depuis:", json_dir)
    if not json_dir.exists():
        print("[WARNING] Le dossier n'existe pas. Aucun fichier JSON ne sera chargé.")
        return pd.DataFrame()

    records = []
    nb_files = 0

    for file in json_dir.glob("*.json"):
        nb_files += 1
        print("[DEBUG] Ouverture du fichier:", file)
        with open(file, "r", encoding="utf-8") as f:
            data = json.load(f)
            records.append({
                "titre": data.get("titre", ""),
                "objectifs": data.get("objectifs", []),
                "prerequis": data.get("prerequis", []),
                "programme": data.get("programme", []),
                "public": data.get("public", []),
                "lien": data.get("lien", "")
            })
        print("[DEBUG] Fichier chargé avec succès:", file.name)

    if nb_files == 0:
        print("[WARNING] Aucun fichier .json trouvé dans le dossier.")
        return pd.DataFrame()

    df = pd.DataFrame(records)
    print(f"[DEBUG] Nombre de formations chargées: {len(df)}")
    return df

# Chargement effectif
df_formations = load_formations_to_df(DATA_FOLDER)
print("\n[DEBUG] df_formations:\n", df_formations)

# ===========================================
# == Fonctions utilitaires (matching)      ==
# ===========================================

def extract_keywords(objective: str, knowledge: str) -> List[str]:
    """
    Transforme l'objectif et les compétences en liste de mots-clés distincts,
    tout en minuscules et sans doublons.
    Ex: "Devenir Data Analyst" + "python, sql" => ["devenir", "data", "analyst", "python", "sql"]
    Avec des prints pour le debug.
    """
    print("\n[DEBUG] Dans extract_keywords =>")
    print(" - objective reçu:", objective)
    print(" - knowledge reçu:", knowledge)

    obj_str = objective.lower().replace(",", " ")
    knw_str = knowledge.lower().replace(",", " ")

    obj_tokens = obj_str.split()
    knw_tokens = knw_str.split()

    # Fusion + élimination de doublons
    all_tokens = obj_tokens + knw_tokens
    unique_tokens = list(set(t.strip() for t in all_tokens if t.strip()))

    print(" - Mots-clés extraits:", unique_tokens)
    return unique_tokens


def partial_match_formations(df: pd.DataFrame, tokens: List[str]) -> pd.DataFrame:
    """
    Évalue chaque formation en fonction du nombre de correspondances partielles avec les mots-clés fournis.
    Retourne les formations triées par score décroissant.

    :param df: DataFrame contenant les formations
    :param tokens: Liste de mots-clés extraits du profil utilisateur
    :return: DataFrame trié par pertinence (score décroissant)
    """

    print("\n[DEBUG] Début du matching")
    print(f"[DEBUG] Nombre de formations à évaluer : {len(df)}")
    print(f"[DEBUG] Tokens utilisateur : {tokens}")

    # Si aucun token ou DF vide, retour vide
    if df.empty or not tokens:
        print("[WARNING] Aucun token ou DataFrame vide")
        return df.iloc[0:0]

    df = df.copy()

    # Fusionne les champs objectifs, prerequis, programme dans une seule chaîne pour chaque ligne
    df["corpus"] = df.apply(
        lambda row: " ".join(
            str(item).lower() for sublist in [row.get("objectifs", []), row.get("prerequis", []), row.get("programme", [])]
            for item in (sublist if isinstance(sublist, list) else [sublist])
        ),
        axis=1
    )

    print("\n[DEBUG] Exemple de corpus (première formation) :")
    if len(df) > 0:
        print(df.iloc[0]["corpus"][:200], "...")  # Affiche un extrait pour éviter les débordements

    # Fonction de scoring : compte les tokens présents dans le corpus
    def compute_score(text: str, tokens: List[str]) -> int:
        score = 0
        for token in tokens:
            if token in text:
                score += 1
        return score

    # Applique la fonction à chaque ligne
    df["score"] = df["corpus"].apply(lambda text: compute_score(text, tokens))

    print("\n[DEBUG] Scores calculés :")
    print(df[["titre", "score"]].sort_values(by="score", ascending=False).to_string(index=False))

    # Filtre uniquement les formations avec score > 0
    matched = df[df["score"] > 0].sort_values(by="score", ascending=False)

    print(f"\n[DEBUG] Formations retenues après filtrage : {len(matched)}")
    return matched



# ===========================================
# == Schémas Pydantic pour l'API           ==
# ===========================================

class UserProfile(BaseModel):
    name: str
    objective: str
    level: str
    knowledge: str
    recommended_course: Optional[str] = None

class RecommendRequest(BaseModel):
    profile: UserProfile

class RecommendResponse(BaseModel):
    recommended_course: str
    reply: str

class QueryRequest(BaseModel):
    profile: UserProfile
    history: List[dict] = []
    question: str

class QueryResponse(BaseModel):
    reply: str


# ===========================================
# == Endpoint /query                       ==
# ===========================================
@app.post("/query", response_model=QueryResponse)
def query_endpoint(req: QueryRequest):
    """
    Endpoint simulant une conversation. 
    Répond juste avec une phrase fictive.
    """
    question = req.question.strip()
    print("\n[DEBUG] /query => question =", question)
    return QueryResponse(reply=f"Réponse fictive à '{question}'. (Pas de LLM)")

# ===========================================
# == Endpoint /recommend                   ==
# ===========================================
@app.post("/recommend", response_model=RecommendResponse)
def recommend_endpoint(r: RecommendRequest):
    """
    Reçoit un profil utilisateur, extrait les mots-clés,
    puis cherche une formation correspondante.
    Retourne une réponse structurée avec détails séparés.
    """
    print("\n[DEBUG] /recommend => Profil =", r.profile)

    tokens = extract_keywords(r.profile.objective, r.profile.knowledge)
    matched_df = partial_match_formations(df_formations, tokens)

    if not matched_df.empty:
        match = matched_df.iloc[0]

        titre = match["titre"]
        objectifs = match["objectifs"]
        prerequis = match["prerequis"]
        programme = match["programme"]
        lien = match["lien"]

        return RecommendResponse(
            recommended_course=titre,
            reply=f"Voici une formation qui correspond à votre profil.",
            details={
                "objectifs": objectifs,
                "prerequis": prerequis,
                "programme": programme,
                "lien": lien
            }
        )
    else:
        return RecommendResponse(
            recommended_course="Aucune formation pertinente",
            reply="Aucune formation ne correspond aux mots-clés fournis.",
            details=None
        )

