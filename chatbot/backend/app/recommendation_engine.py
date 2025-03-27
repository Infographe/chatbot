# recommendation_engine.py
import json
from pathlib import Path
from typing import List, Dict
import difflib

# Chargement des données de formation (version clean)
FORMATIONS_DIR = Path("content/json/formations_clean")


def load_formations() -> List[Dict]:
    formations = []
    for file in FORMATIONS_DIR.glob("*.json"):
        with open(file, "r", encoding="utf-8") as f:
            data = json.load(f)
            formations.append(data)
    return formations


# Recommandation simple par similarité (titre, objectifs, public)
def recommend_formations(profile: Dict, top_k: int = 3) -> List[Dict]:
    formations = load_formations()
    recommandations = []

    user_keywords = profile.get("objectifs", []) + profile.get("niveau", []) + profile.get("domaine", [])
    user_keywords = [kw.lower() for kw in user_keywords]

    for formation in formations:
        score = 0
        titre = formation.get("titre", "").lower()
        objectifs = " ".join(formation.get("objectifs", [])).lower()
        public = " ".join(formation.get("public", [])).lower()

        contenu = f"{titre} {objectifs} {public}"

        for keyword in user_keywords:
            if keyword in contenu:
                score += 1
            else:
                close_matches = difflib.get_close_matches(keyword, contenu.split(), n=1, cutoff=0.8)
                if close_matches:
                    score += 0.5

        recommandations.append({"formation": formation, "score": score})

    recommandations.sort(key=lambda x: x["score"], reverse=True)
    return recommandations[:top_k]


def recommend_or_suggest_bilan(profile, formations, seuil_score=1.5, top_k=3):
    """
    Logique de recommandation conditionnelle :
    - Si aucune formation ne dépasse le seuil de score, on suggère un bilan de compétences.
    - Sinon, on retourne les formations les mieux classées.

    Paramètres :
        profile (dict) : Profil de l'utilisateur (objectifs, domaine, niveau)
        formations (list) : Liste des formations disponibles
        seuil_score (float) : Score minimal de confiance requis
        top_k (int) : Nombre de formations à recommander si le seuil est atteint

    Retourne :
        dict : Recommandations ou suggestion de bilan
    """
    scored = []

    for formation in formations:
        score = 0
        contenu = (
            formation.get("titre", "") + " " +
            " ".join(formation.get("objectifs", [])) + " " +
            " ".join(formation.get("public", []))
        ).lower()

        # Calcul de similarité simple basée sur des mots-clés
        for objectif in profile.get("objectifs", []):
            if objectif.lower() in contenu:
                score += 1
        for domaine in profile.get("domaine", []):
            if domaine.lower() in contenu:
                score += 1
        for niveau in profile.get("niveau", []):
            if niveau.lower() in contenu:
                score += 0.5  # Poids plus léger pour le niveau

        scored.append({"formation": formation, "score": score})

    scored.sort(key=lambda x: x["score"], reverse=True)

    if not scored or scored[0]["score"] < seuil_score:
        return {
            "type": "suggestion_bilan",
            "message": "Aucune formation ne correspond clairement à votre profil. Un bilan de compétences est recommandé.",
            "score_max": scored[0]["score"] if scored else 0
        }

    return {
        "type": "recommandations",
        "formations": scored[:top_k]
    }
