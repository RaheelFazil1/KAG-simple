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

## Test Analysis

We verified the chatbot's accuracy using **30 documented test cases** across three categories. All test cases are stored in [`test_cases.json`](test_cases.json) for reproducibility.

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
- Ensure Neo4j is running and accessible at the URI specified in `kag_engine.py`.
- The `.gitignore` is set up to avoid tracking the `venv` folder and other unnecessary files.

## License
MIT License
