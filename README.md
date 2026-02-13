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
KAG_CHATBOT/
├── .env.example              # Environment variable template (copy to .env)
├── .gitignore
├── README.md
├── requirements.txt
│
├── backend/
│   ├── __init__.py
│   ├── app/
│   │   ├── __init__.py
│   │   ├── config.py         # Centralized configuration (loads .env)
│   │   ├── schemas.py        # Pydantic request/response models
│   │   ├── kag_engine.py     # Core KAG engine (LLM, Neo4j, logic)
│   │   └── main.py           # FastAPI server entrypoint
│   ├── data/
│   │   ├── uet_departments.json
│   │   ├── UET_lahore_Document.pdf
│   │   └── UET Lahore_Questions Dataset (1).pdf
│   └── etl/
│       ├── __init__.py
│       ├── extract_data.py   # PDF → raw JSON extraction
│       ├── clean_data.py     # Raw JSON → cleaned JSON
│       ├── load_graph.py     # JSON → Neo4j graph nodes/edges
│       ├── index_graph.py    # Embed department intros → Neo4j vectors
│       └── index_documents.py # Embed full PDF chunks → Neo4j vectors
│
├── frontend/
│   └── app.py                # Streamlit chat UI
│
└── tests/
    ├── __init__.py
    └── test_cases.json       # 30 test cases (standard, tricky, out-of-scope)
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

### 4. Configure environment variables
```
copy .env.example .env
# Edit .env with your Neo4j credentials and model preferences
```

### 5. Run the ETL pipeline (first time only)
```bash
# Step 1: Extract data from PDF
python backend/etl/extract_data.py

# Step 2: Clean the extracted data
python backend/etl/clean_data.py

# Step 3: Load data into Neo4j graph
python backend/etl/load_graph.py

# Step 4: Create vector indexes
python backend/etl/index_graph.py
python backend/etl/index_documents.py
```

### 6. Start the FastAPI server
```
cd backend/app
uvicorn main:app --reload
```

### 7. Start the Streamlit client
```
streamlit run frontend/app.py
```

## Test Analysis

We verified the chatbot's accuracy using **30 documented test cases** across three categories. All test cases are stored in [`tests/test_cases.json`](tests/test_cases.json) for reproducibility.

### Test Categories

| Category | Count | Description |
|---|---|---|
| **Standard** | 15 | Normal questions about programs, eligibility, chairmen, and deans |
| **Tricky** | 8 | Questions that test correction logic and edge cases |
| **Out-of-Scope** | 7 | Blocked topics the system must refuse to answer |

### Standard Test Cases (STD-01 to STD-15)

These verify core functionality — program listings, faculty lookups, eligibility criteria, and general department info across departments including Computer Science, Electrical Engineering, Civil Engineering, Mechanical Engineering, Chemical Engineering, Mining, Architecture, Physics, and Business & Management.

**Key validations:**
- All programs for a department are listed without omissions
- Chairman and Dean roles are correctly distinguished
- Eligibility criteria match the official prospectus data
- Master's-only queries correctly filter out Ph.D. programs

### Tricky Test Cases (TRICKY-01 to TRICKY-08)

These test the system's **department correction logic** and edge-case handling:

| Test ID | Scenario | What It Validates |
|---|---|---|
| TRICKY-01 | "Does CS offer M.Sc. AI?" | System corrects: **M.Sc. Artificial Intelligence belongs to Electrical Engineering**, not Computer Science |
| TRICKY-02 | "I want to study AI at CS department" | Same correction, phrased as a user intent |
| TRICKY-03 | Eligibility for M.Sc. AI | System fetches criteria from **Electrical Engineering** (the true department) |
| TRICKY-04 | "Is Data Science under EE?" | System corrects: Data Science is under Institute of Data Science / CS |
| TRICKY-05 | "Who is the dean of CS?" | System returns **Dean** (Dr. Muhammad Shoaib), not the Chairman |
| TRICKY-06 | Compare CS vs EE programs | Both department programs listed; M.Sc. AI appears under EE only |
| TRICKY-07 | "Which dept offers Geotechnical?" | System identifies **Civil Engineering**, not Geological Engineering |
| TRICKY-08 | "Who heads Mining Engineering?" | Finds chairman Dr. Shahab Saqib despite his Assistant Professor rank |

> **Highlight — TRICKY-01 & TRICKY-02:** The `_check_global_program_match()` method in `kag_engine.py` queries Neo4j to find the true department that offers a program. If the user mentions a wrong department, the system sets `is_correction = True` and explicitly corrects the user in its response.

### Out-of-Scope Test Cases (OOS-01 to OOS-07)

These verify the **guardrail system** (`_apply_guardrails()` method) that blocks topics outside the chatbot's knowledge:

| Test ID | Blocked Topic | Trigger Keywords |
|---|---|---|
| OOS-01 | Fee structure for M.Sc. CS | `fee` |
| OOS-02 | Tuition fee for EE | `tuition` |
| OOS-03 | Hostel facilities | `hostel` |
| OOS-04 | Transport / shuttle bus | `transport`, `shuttle` |
| OOS-05 | Admission deadline | `last date` |
| OOS-06 | Entry test schedule | `entry test`, `schedule` |
| OOS-07 | Payment / accommodation dues | `payment`, `dues`, `accommodation` |

All out-of-scope queries return: *"I cannot answer questions about fees, hostels, transport, or admission dates as this information is out of scope."*

### How the Correction Logic Works

```
User asks: "Does CS offer M.Sc. AI?"
    │
    ├─ _check_global_program_match() → queries Neo4j
    │   └─ Result: M.Sc. AI is offered by Dept. of Electrical Engineering
    │
    ├─ _extract_all_departments() → user mentioned "Computer Science"
    │   └─ Mismatch detected: CS ≠ Electrical Engineering
    │
    ├─ is_correction = True
    │
    └─ LLM Response: "M.Sc. Artificial Intelligence is offered by the
       Department of Electrical Engineering, not Computer Science."
```

## Notes
- All configuration (Neo4j URI, credentials, model names) is managed via `.env` and `backend/app/config.py`.
- Never commit the `.env` file — only `.env.example` is tracked in git.
- Ensure Neo4j is running before starting the server.
- The `.gitignore` is set up to avoid tracking `venv/`, `.env`, `__pycache__/`, and other build artifacts.


## Contributed By
- ADEEL-308
- RaheelFazil1
- engrfaizan99
- Sabaattiq

## License
MIT License
