# KAG Chatbot

KAG Chatbot is an intelligent admission assistant for UET Lahore, designed to answer questions about departments, programs, eligibility, and more. It leverages LLMs, Neo4j graph database, and advanced embeddings to provide accurate, context-aware responses.

## Features
- Natural language question answering about UET Lahore admissions
- Department and program correction logic
- Eligibility and program information (on request)
- Neo4j graph database integration
- Streamlit client for user-friendly interaction

## Project Structure
```
requirements.txt
client/
    app.py           # Streamlit client app
server/
    app/
        kag_engine.py  # Core engine (LLM, Neo4j, logic)
        main.py        # FastAPI server entrypoint
    data/
        uet_departments.json
    etl/
        cleanData.py, extractData.py, graph.py
```

## Getting Started

### 1. Clone the repository
```
git clone <your-repo-url>
cd KAG_CHATBOT
```

### 2. Set up the virtual environment
```
python -m venv venv
venv\Scripts\activate  # On Windows
```

### 3. Install dependencies
```
pip install -r requirements.txt
```

### 4. Start the FastAPI server
```
uvicorn server.app.main:app --reload
```

### 5. Start the Streamlit client
```
streamlit run client/app.py
```

## Notes
- Ensure Neo4j is running and accessible at the URI specified in `kag_engine.py`.
- The `.gitignore` is set up to avoid tracking the `venv` folder and other unnecessary files.

## License
MIT License
