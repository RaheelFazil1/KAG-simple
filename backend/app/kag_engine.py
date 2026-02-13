from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from neo4j import GraphDatabase
from sentence_transformers import SentenceTransformer
import json

# --- Configuration ---
NEO4J_URI = "bolt://localhost:7687"
NEO4J_AUTH = ("neo4j", "password") 
MODEL_NAME = "llama3.2:1b"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

class KAGEngine:
    def __init__(self):
        print("Initializing KAG Engine (Natural Response Mode)...")
        
        self.llm = ChatOllama(model=MODEL_NAME, temperature=0, format="json") 
        self.chat_llm = ChatOllama(model=MODEL_NAME, temperature=0)
        self.embedder = SentenceTransformer(EMBEDDING_MODEL)
        self.driver = GraphDatabase.driver(NEO4J_URI, auth=NEO4J_AUTH)

        # 1. ROUTER
        self.router_prompt = ChatPromptTemplate.from_template("""
        Analyze the question and extract INTENT and DEPARTMENT.
        
        Intents:
        - get_dean (Dean of Faculty ONLY)
        - get_chairman (Chairman, Head of Department, HOD)
        - get_eligibility (Criteria, apply, merit, eligible)
        - get_programs (Degrees, courses, offers, list programs)
        - vector_search (General info, location, ranking, comparison)

        Output JSON only: {{"intent": "...", "department": "..."}}
        Q: "{question}"
        """)

        # 2. RESPONSE PROMPT (Strict "No Graph Data" Rule)
        self.response_prompt = ChatPromptTemplate.from_template("""
        You are a UET Lahore Admission Assistant. Answer naturally based on the information provided.
        
        Information:
        {context}
        
        Question: {question}
        
        Instructions:
        {guidelines}
        - Answer directly and conversationally.
        - Do NOT mention "Graph Data", "Context", "database", or "records" in your answer.
        - List ALL programs found in the Information. Do not summarize or omit any.
        - Do NOT invent titles. A 'Chairman' is NOT a 'Dean'.
        
        Answer:
        """)

    def close(self):
        self.driver.close()

    def _apply_guardrails(self, question: str):
        q = question.lower()
        if any(x in q for x in ["fee", "tuition", "cost", "dues", "payment"]):
            return "BLOCKED_FEES"
        if any(x in q for x in ["hostel", "transport", "bus", "accommodation", "shuttle"]):
            return "BLOCKED_FACILITIES"
        if any(x in q for x in ["last date", "deadline", "schedule", "entry test", "admission form"]):
            return "BLOCKED_DATES"
        return None

    def _extract_all_departments(self, question: str):
        q_lower = question.lower()
        dept_map = {
            "geological": "Department of Geological Engineering",
            "geotechnical": "Department of Civil Engineering",
            "civil": "Department of Civil Engineering",
            "computer science": "Department of Computer Science",
            "electrical": "Department of Electrical Engineering",
            "mechanical": "Department of Mechanical Engineering",
            "mining": "Department of Mining Engineering",
            "chemical": "Department of Chemical Engineering",
            "petroleum": "Department of Petroleum & Gas Engineering",
            "architecture": "Department of Architecture",
            "business": "Institute of Business and Management",
            "mathematics": "Department of Mathematics",
            "data science": "Institute of Data Science"
        }
        found = []
        for key, full_name in dept_map.items():
            if key in q_lower:
                found.append(full_name)
        return list(set(found))

    def _get_intent(self, question: str):
        try:
            res = (self.router_prompt | self.llm).invoke({"question": question})
            return json.loads(res.content)
        except:
            return {"intent": "vector_search", "department": ""}

    def _check_global_program_match(self, question: str):
        """Checks if a program belongs to a specific department."""
        query = """
        MATCH (d:Department)-[:OFFERS]->(p:Program)
        WHERE toLower($question) CONTAINS toLower(p.name)
           OR toLower(p.name) CONTAINS toLower($question)
        RETURN d.name as Department, p.name as Program
        LIMIT 1
        """
        with self.driver.session() as session:
            result = session.run(query, question=question).single()
            if result:
                return {"found": True, "true_dept": result["Department"], "program": result["Program"]}
            return {"found": False}

    def _fetch_graph_context(self, intent, dept_name, question=""):
        if not dept_name: return []
        
        clean_dept = dept_name.replace("Department of", "").replace("Institute of", "").strip()

        queries = {
            "get_dean": "MATCH (f:Faculty)-[:IS_DEAN_OF]->(d:Department) WHERE d.name CONTAINS $dept RETURN f.name as Dean_Name",
            "get_chairman": "MATCH (f:Faculty)-[:IS_CHAIRMAN_OF]->(d:Department) WHERE d.name CONTAINS $dept RETURN f.name as Chairman_Name",
            "get_programs": "MATCH (d:Department)-[:OFFERS]->(p:Program) WHERE d.name CONTAINS $dept RETURN p.name as Program ORDER BY p.name",
            "get_eligibility": "MATCH (d:Department)-[:HAS_CRITERIA]->(e:Eligibility) WHERE d.name CONTAINS $dept RETURN e.text as Criteria",
            "get_faculty": "MATCH (d:Department)-[:HAS_PROFESSOR]->(f:Faculty) WHERE d.name CONTAINS $dept RETURN f.name as Professor"
        }
        
        query = queries.get(intent, queries["get_programs"])
        
        with self.driver.session() as session:
            data = [record.data() for record in session.run(query, dept=clean_dept)]
            
            # --- FILTER LOGIC ---
            if intent == "get_programs" and question:
                q_lower = question.lower()
                
                # 1. Hide Ph.D. ONLY if user explicitly asks for "Master's" or "M.Sc."
                # (Prevents missing Ph.D. on general "list all" queries)
                if "master" in q_lower or "m.sc" in q_lower:
                    data = [d for d in data if "ph.d" not in d['Program'].lower()]

                # 2. Safety/Specific Filter
                if "safety" in q_lower:
                    safety_matches = [d for d in data if "safety" in d['Program'].lower()]
                    if not safety_matches: return [] # Force Vector Search
                    return safety_matches

            # --- DEAN FALLBACK ---
            if intent == "get_dean" and not data:
                return [{"SYSTEM_NOTE": "Dean NOT found. Do NOT invent one."}]

            return data

    def query(self, user_question: str):
        # 1. GUARDRAILS
        block_reason = self._apply_guardrails(user_question)
        if block_reason:
            return {"answer": "I cannot answer questions about fees, hostels, transport, or admission dates as this information is out of scope.", "cypher": f"BLOCKED: {block_reason}"}

        # 2. Intent Analysis
        plan = self._get_intent(user_question)
        intent = plan.get("intent", "vector_search")
        
        context_messages = []
        is_correction = False
        target_depts = []

        # 3. Fact Check / Program Spotter
        prog_match = self._check_global_program_match(user_question)
        if prog_match["found"]:
            true_dept = prog_match["true_dept"]
            context_messages.append(f"FACT: The program '{prog_match['program']}' is officially offered by '{true_dept}' and NO other department.")
            
            user_mentioned_depts = self._extract_all_departments(user_question)
            if user_mentioned_depts:
                # If user said wrong dept (and isn't just checking eligibility), trigger correction
                if not any(true_dept in d for d in user_mentioned_depts):
                    if intent != "get_eligibility": 
                        is_correction = True
            
            # For Eligibility, ALWAYS look up the TRUE department
            target_depts = [true_dept]

        # 4. Multi-Department Extraction
        if not target_depts:
            target_depts = self._extract_all_departments(user_question)

        # 5. Fetch Context
        if target_depts:
            for dept in target_depts:
                # A. Fetch Primary Intent Data
                data = self._fetch_graph_context(intent, dept, user_question)
                if data: context_messages.append(f"Department Data ({dept}): {str(data)}")
                
                # B. Comparison Mode: Fetch Programs + Intro
                if len(target_depts) > 1:
                    prog_data = self._fetch_graph_context("get_programs", dept)
                    context_messages.append(f"Programs List ({dept}): {str(prog_data)}")
                    with self.driver.session() as session:
                        res = session.run("MATCH (d:Department) WHERE d.name = $d RETURN d.introduction as Intro", d=dept).single()
                        if res: context_messages.append(f"Description ({dept}): {res['Intro'][:300]}...")

        # 6. Vector Fallback
        trigger_vector = (intent == "vector_search") or (not context_messages) or ("rank" in user_question.lower())
        if trigger_vector:
            vector = self.embedder.encode(user_question).tolist()
            with self.driver.session() as session:
                res = session.run("""
                    CALL db.index.vector.queryNodes('document_chunk_index', 3, $vec)
                    YIELD node, score
                    WHERE score > 0.50
                    RETURN node.text as Info
                """, vec=vector).data()
                for r in res:
                    context_messages.append(f"Document Excerpt: {r['Info']}")

        # 7. Guidelines & Synthesis
        guidelines = ""
        if intent == "get_programs":
            guidelines = "List ALL programs found in the 'Department Data'. Do not summarize. If a program is not listed in the data, do NOT mention it."
        elif intent == "get_dean":
            guidelines = "Identify the 'Dean_Name'. If the data says 'Dean NOT found', state that the Dean is not listed. Do NOT use the Chairman's name."
        elif is_correction:
            guidelines = "The user mentioned the wrong department. Correct them explicitly based on the FACT provided."
        elif len(target_depts) > 1:
            guidelines = "Compare the departments based on their 'Programs List' and descriptions. State if they are same or different."

        response = (self.response_prompt | self.chat_llm).invoke({
            "question": user_question, 
            "context": "\n".join(context_messages),
            "guidelines": guidelines
        })
        
        return {
            "answer": response.content,
            "cypher": f"Intent: {intent} | Depts: {target_depts} | Correction: {is_correction}"
        }