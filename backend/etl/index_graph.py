import os
import sys
from neo4j import GraphDatabase
from sentence_transformers import SentenceTransformer

# Allow imports from sibling packages
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))
from config import NEO4J_URI, NEO4J_AUTH, EMBEDDING_MODEL

class GraphIndexer:
    def __init__(self):
        print(f"⏳ Loading embedding model: {EMBEDDING_MODEL}...")
        self.model = SentenceTransformer(EMBEDDING_MODEL)
        self.driver = GraphDatabase.driver(NEO4J_URI, auth=NEO4J_AUTH)

    def close(self):
        self.driver.close()

    def create_vector_index(self):
        """Creates the vector index in Neo4j if it doesn't exist."""
        print("⚙️ Checking/Creating Vector Index...")
        
        # We use a raw Cypher query to create the index
        query = """
        CREATE VECTOR INDEX department_intro_index IF NOT EXISTS
        FOR (d:Department)
        ON (d.embedding)
        OPTIONS {indexConfig: {
            `vector.dimensions`: 384,
            `vector.similarity_function`: 'cosine'
        }}
        """
        try:
            with self.driver.session() as session:
                session.run(query)
            print("✅ Vector Index 'department_intro_index' is ready.")
        except Exception as e:
            print(f"⚠️ Error creating index (might already exist): {e}")

    def index_data(self):
        """Fetches text, vectorizes it, and updates the nodes."""
        print("🔄 Indexing data...")
        
        # 1. Fetch data
        fetch_query = """
        MATCH (d:Department) 
        WHERE d.introduction IS NOT NULL 
        RETURN d.name as name, d.introduction as text
        """
        
        # 2. Update query
        update_query = """
        MATCH (d:Department {name: $name}) 
        SET d.embedding = $embedding
        """

        with self.driver.session() as session:
            nodes = session.run(fetch_query).data()
            print(f"Found {len(nodes)} departments to index.")

            for node in nodes:
                text = node['text']
                if not text: continue
                
                # Generate Embedding (List of 384 floats)
                vector = self.model.encode(text).tolist()
                
                # Save back to Neo4j
                session.run(update_query, name=node['name'], embedding=vector)
                print(f"   🔹 Indexed: {node['name']}")

if __name__ == "__main__":
    indexer = GraphIndexer()
    try:
        indexer.create_vector_index()
        indexer.index_data()
        print("\n🎉 Indexing Complete! Run this again only if you add new data.")
    finally:
        indexer.close()