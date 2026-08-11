from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Dict, Any
from app.api.v1.auth import get_current_admin_user
from app.agents.chat_agent import ask_chatbot, ingest_text_rule
from app.db.models.models import User

router = APIRouter(prefix="/api/v1/chat", tags=["Chatbot"])

class ChatQuery(BaseModel):
    query: str

class ChatIngest(BaseModel):
    rule_text: str

@router.post("/query")
async def chat_query(payload: ChatQuery) -> Dict[str, Any]:
    """
    Query the Chatbot using RAG. Accessible to all logged-in users (both Admin and Employee).
    """
    if not payload.query:
        raise HTTPException(status_code=400, detail="Query cannot be empty.")
    
    response_text = await ask_chatbot(payload.query)
    
    return {
        "status": "success",
        "reply": response_text
    }

@router.post("/ingest")
async def chat_ingest(payload: ChatIngest, current_user: User = Depends(get_current_admin_user)) -> Dict[str, Any]:
    """
    Ingest a new rule into the knowledge base. Restricted to Admins only.
    """
    if not payload.rule_text:
        raise HTTPException(status_code=400, detail="Rule text cannot be empty.")
    
    success, message = ingest_text_rule(payload.rule_text)
    
    if not success:
        raise HTTPException(status_code=500, detail=message)
        
    return {
        "status": "success",
        "message": message
    }
