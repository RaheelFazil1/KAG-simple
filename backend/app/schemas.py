"""
Pydantic request/response schemas for the KAG Chatbot API.
"""

from pydantic import BaseModel


class QueryRequest(BaseModel):
    """Incoming question from the client."""
    question: str


class QueryResponse(BaseModel):
    """Structured answer returned to the client."""
    question: str
    answer: str
    generated_cypher: str
