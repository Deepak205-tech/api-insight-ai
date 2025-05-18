from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests

app = FastAPI(title="API Insight Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class APISpec(BaseModel):
    endpoints: list

@app.post("/analyze-api")
def analyze_api(spec: APISpec):
    try:
        # Get the first endpoint from the list
        if not spec.endpoints or len(spec.endpoints) == 0:
            return {"error": "No endpoints provided"}
            
        endpoint = spec.endpoints[0]  # Take the first endpoint
        
        # Format the request for the AI engine
        ai_response = requests.post(
            "http://ai-engine:8001/generate-testcases", 
            json={"prompt": endpoint}
        )
        ai_response.raise_for_status()
        return ai_response.json()
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}

@app.get("/health")
def health_check():
    return {"status": "ok"}
