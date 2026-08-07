from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from pydantic import BaseModel

from app.db.database import get_db
from app.db.models.models import User
from app.api.v1.auth import get_current_admin_user
import uuid

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])

@router.get("/users")
async def list_users(db: AsyncSession = Depends(get_db), admin_user: User = Depends(get_current_admin_user)):
    """List all registered users for the admin portal."""
    stmt = select(User).order_by(User.email)
    result = await db.execute(stmt)
    users = result.scalars().all()
    
    return [
        {
            "id": str(user.id),
            "email": user.email,
            "role": user.role.value,
            "approval_status": user.approval_status,
            "is_verified": user.is_verified,
            "active": user.active
        }
        for user in users if user.id != admin_user.id
    ]

class StatusUpdate(BaseModel):
    status: str # "APPROVED", "REJECTED", "PAUSED"

@router.post("/users/{user_id}/status")
async def update_user_status(user_id: str, payload: StatusUpdate, db: AsyncSession = Depends(get_db), admin_user: User = Depends(get_current_admin_user)):
    """Update a user's approval status."""
    if payload.status not in ["APPROVED", "REJECTED", "PAUSED", "PENDING"]:
        raise HTTPException(status_code=400, detail="Invalid status")
        
    stmt = select(User).where(User.id == uuid.UUID(user_id))
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    user.approval_status = payload.status
    await db.commit()
    
    return {"message": f"User {user.email} status updated to {payload.status}"}

@router.delete("/users/{user_id}")
async def delete_user(user_id: str, db: AsyncSession = Depends(get_db), admin_user: User = Depends(get_current_admin_user)):
    """Delete a user."""
    stmt = select(User).where(User.id == uuid.UUID(user_id))
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    # Nullify any foreign key relationships in processing_cases
    from app.db.models.models import ProcessingCase
    from sqlalchemy import update
    await db.execute(
        update(ProcessingCase)
        .where(ProcessingCase.created_by == user.id)
        .values(created_by=None)
    )
        
    await db.delete(user)
    await db.commit()
    return {"message": f"User {user.email} deleted successfully"}

from fastapi import UploadFile, File, Form
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
import chromadb
from app.db.database import settings
import tempfile
import os

@router.post("/knowledge/upload")
async def upload_knowledge(
    file: UploadFile = File(...),
    trade_direction: str = Form(...),
    jurisdiction: str = Form(...),
    admin_user: User = Depends(get_current_admin_user)
):
    """Upload a regulation PDF to ChromaDB."""
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")
        
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name
        
    try:
        loader = PyPDFLoader(tmp_path)
        docs = loader.load()
        
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        splits = text_splitter.split_documents(docs)
        
        client = chromadb.PersistentClient(path=str(settings.LOCAL_STORAGE_PATH) + "/chroma")
        collection = client.get_or_create_collection(settings.CHROMA_COLLECTION)
        
        embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        
        ids = [str(uuid.uuid4()) for _ in splits]
        texts = [doc.page_content for doc in splits]
        metadatas = [{"trade_direction": trade_direction, "jurisdiction": jurisdiction, "source": file.filename} for _ in splits]
        
        embedded = embeddings.embed_documents(texts)
        
        collection.add(
            ids=ids,
            embeddings=embedded,
            metadatas=metadatas,
            documents=texts
        )
        
        return {"message": f"Successfully ingested {len(splits)} chunks into Knowledge Base."}
    finally:
        os.unlink(tmp_path)

