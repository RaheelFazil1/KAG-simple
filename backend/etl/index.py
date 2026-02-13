import os
import pdfplumber
from neo4j import GraphDatabase
from sentence_transformers import SentenceTransformer

# --- Configuration ---
URI = "bolt://localhost:7687"
AUTH = ("neo4j", "password") 
MODEL_NAME = "all-MiniLM-L6-v2"
PDF_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "UET_lahore_Document.pdf")

class FullDocIndexer:
    def __init__(self):
        print(f"⏳ Loading model: {MODEL_NAME}...")
        self.model = SentenceTransformer(MODEL_NAME)
        self.driver = GraphDatabase.driver(URI, auth=AUTH)

    def close(self):
        self.driver.close()

    def create_chunk_index(self):
        """Creates a Vector Index on the generic DocumentChunk nodes."""
        print("⚙️ Creating 'document_chunk_index'...")
        query = """
        CREATE VECTOR INDEX document_chunk_index IF NOT EXISTS
        FOR (c:DocumentChunk)
        ON (c.embedding)
        OPTIONS {indexConfig: {
            `vector.dimensions`: 384,
            `vector.similarity_function`: 'cosine'
        }}
        """
        with self.driver.session() as session:
            session.run(query)

    def ingest_pdf(self):
        print(f"📖 Reading PDF: {PDF_PATH}")
        chunks = []
        
        # 1. Extract Text & Chunk It
        with pdfplumber.open(PDF_PATH) as pdf:
            for i, page in enumerate(pdf.pages):
                text = page.extract_text()
                if not text: continue
                
                # Simple Chunking: Split by paragraphs or fixed size
                # Here we use a sliding window of paragraphs for better context
                paragraphs = text.split('\n\n')
                for para in paragraphs:
                    clean_text = " ".join(para.split()) # Normalize whitespace
                    if len(clean_text) > 50: # Ignore tiny headers/footers
                        chunks.append({
                            "text": clean_text,
                            "page": i + 1,
                            "source": "UET_lahore_Document.pdf"
                        })

        print(f"🔹 Generated {len(chunks)} text chunks. Embedding now...")

        # 2. Embed & Save to Neo4j
        write_query = """
        CREATE (c:DocumentChunk {text: $text, page: $page, source: $source})
        SET c.embedding = $embedding
        """
        
        with self.driver.session() as session:
            for i, chunk in enumerate(chunks):
                # Vectorize
                vector = self.model.encode(chunk["text"]).tolist()
                
                # Write
                session.run(write_query, 
                            text=chunk["text"], 
                            page=chunk["page"], 
                            source=chunk["source"], 
                            embedding=vector)
                
                if i % 50 == 0: print(f"   Saved {i}/{len(chunks)} chunks...")

        print("✅ Full Document Indexing Complete!")

if __name__ == "__main__":
    indexer = FullDocIndexer()
    try:
        indexer.create_chunk_index()
        indexer.ingest_pdf()
    finally:
        indexer.close()