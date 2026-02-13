import json
import re
import sys
import os
from neo4j import GraphDatabase

# Allow imports from sibling packages
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))
from config import NEO4J_URI, NEO4J_AUTH, DATA_DIR

class UETGraphLoader:
    def __init__(self, uri, auth):
        self.driver = GraphDatabase.driver(uri, auth=auth)

    def close(self):
        self.driver.close()

    def clean_db(self):
        """Wipes the database clean. USE WITH CAUTION."""
        print("Cleaning existing database...")
        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")

    def load_data(self, json_file):
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        with self.driver.session() as session:
            for dept in data:
                print(f"Loading: {dept.get('department')}")
                session.execute_write(self._create_department_graph, dept)

    @staticmethod
    def _create_department_graph(tx, dept_data):
        # 1. Create the Department Node
        dept_name = dept_data.get("department", "Unknown Department")
        intro = dept_data.get("Introduction") or dept_data.get("introduction", "")
        
        query_dept = """
        MERGE (d:Department {name: $name})
        SET d.introduction = $intro
        RETURN d
        """
        tx.run(query_dept, name=dept_name, intro=intro)

        # 2. Link Offered Programs
        # We assume programs are strings like "M.Sc. Electrical Engineering"
        programs = dept_data.get("offered_programs", [])
        if programs:
            query_prog = """
            MATCH (d:Department {name: $dept_name})
            UNWIND $programs AS prog_name
            MERGE (p:Program {name: prog_name})
            MERGE (d)-[:OFFERS]->(p)
            """
            tx.run(query_prog, dept_name=dept_name, programs=programs)

        # 3. Link Eligibility Criteria
        # We create specific nodes for criteria so we can search them later
        criteria = dept_data.get("eligibility_criteria", [])
        if criteria:
            query_criteria = """
            MATCH (d:Department {name: $dept_name})
            UNWIND $criteria AS text
            CREATE (e:Eligibility {text: text})
            MERGE (d)-[:HAS_CRITERIA]->(e)
            """
            tx.run(query_criteria, dept_name=dept_name, criteria=criteria)

        # 4. Link Faculty Members (with Role & Title Detection)
        faculty_groups = dept_data.get("faculty_members", {})
        
        # Map JSON keys to specific Neo4j Relationships
        role_map = {
            "professors": "HAS_PROFESSOR",
            "associate_professors": "HAS_ASSOCIATE_PROFESSOR",
            "assistant_professors": "HAS_ASSISTANT_PROFESSOR",
            "lecturers": "HAS_LECTURER",
            "lecturer": "HAS_LECTURER"
        }

        for group_key, relation_type in role_map.items():
            members = faculty_groups.get(group_key, [])
            for member_name in members:
                # A. Clean name and detect administrative roles
                clean_name = member_name
                is_dean = False
                is_chair = False

                if "(Dean)" in member_name:
                    is_dean = True
                    clean_name = member_name.replace("(Dean)", "").strip()
                if "(Chairman)" in member_name or "(Chairperson)" in member_name:
                    is_chair = True
                    clean_name = re.sub(r'\(Chair(man|person)\)', '', member_name).strip()

                # B. Create the Faculty Node and the Role Relationship
                query_fac = f"""
                MATCH (d:Department {{name: $dept_name}})
                MERGE (f:Faculty {{name: $name}})
                MERGE (d)-[:{relation_type}]->(f)
                """
                tx.run(query_fac, dept_name=dept_name, name=clean_name)

                # C. Add Administrative Relationships (Dean/Chair)
                if is_dean:
                    tx.run("""
                        MATCH (d:Department {name: $dept_name})
                        MATCH (f:Faculty {name: $name})
                        MERGE (f)-[:IS_DEAN_OF]->(d)
                    """, dept_name=dept_name, name=clean_name)
                
                if is_chair:
                    tx.run("""
                        MATCH (d:Department {name: $dept_name})
                        MATCH (f:Faculty {name: $name})
                        MERGE (f)-[:IS_CHAIRMAN_OF]->(d)
                    """, dept_name=dept_name, name=clean_name)

# --- Execution ---
if __name__ == "__main__":
    json_file = os.path.join(DATA_DIR, "uet_departments.json")
    
    loader = UETGraphLoader(NEO4J_URI, NEO4J_AUTH)
    
    try:
        # loader.clean_db()  # Uncomment this if you want to wipe the DB and start fresh
        loader.load_data(json_file)
        print("Graph loaded successfully! 🚀")
    except Exception as e:
        print(f"Error loading graph: {e}")
    finally:
        loader.close()