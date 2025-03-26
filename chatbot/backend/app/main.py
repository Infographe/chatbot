from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List

app = FastAPI()

# Autoriser le frontend Angular à communiquer avec l’API FastAPI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],  # Port Angular
    allow_credentials=True,
    allow_methods=["*"],  # Autoriser POST, GET, OPTIONS etc.
    allow_headers=["*"],  # Autoriser tous les headers
)


# Schéma de la requête (entrée)
class QueryRequest(BaseModel):
    prompt: str

# Schéma de la réponse (sortie)
class QueryResponse(BaseModel):
    response: str
    source_documents: List[str]

# Endpoint principal simulant une logique RAG
@app.post("/query", response_model=QueryResponse)
def query(request: QueryRequest):
    prompt = request.prompt

    # Réponse simulée (à remplacer plus tard par une vraie recherche)
    fake_response = f"Voici une réponse simulée pour : '{prompt}'"
    fake_sources = [
        "Formation_Power_BI.json",
        "Formation_Python_Data_Visualisation.json"
    ]

    return QueryResponse(response=fake_response, source_documents=fake_sources)
