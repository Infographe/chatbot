from fastapi import FastAPI
from pydantic import BaseModel
from typing import List

app = FastAPI()

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
