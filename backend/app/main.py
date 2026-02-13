from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager

from kag_engine import KAGEngine
from schemas import QueryRequest, QueryResponse

# --- Global Engine Instance ---
kag_engine = None

# --- Lifespan Manager ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    global kag_engine
    kag_engine = KAGEngine()
    yield
    kag_engine.close()
    print("KAG Engine shut down.")

# --- API Setup ---
app = FastAPI(title="UET KAG System", lifespan=lifespan)

# --- Endpoints ---
@app.get("/")
def read_root():
    return {"status": "System is running", "model": "Llama 3.2:1b"}

@app.post("/ask", response_model=QueryResponse)
def ask_question(request: QueryRequest):
    if not kag_engine:
        raise HTTPException(status_code=503, detail="Engine not initialized")

    try:
        result = kag_engine.query(request.question)
        return {
            "question": request.question,
            "answer": result["answer"],
            "generated_cypher": result["cypher"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
