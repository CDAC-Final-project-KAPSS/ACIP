from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List
import uuid
import asyncio
import os
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.db.database import get_db, AsyncSessionLocal
from app.db.models.models import ProcessingCase, Document, TradeDirection, CaseStatus
from app.agents.workflow import run_acip_workflow
from app.utils.pdf_generator import generate_boe_pdf, generate_checklist_pdf

router = APIRouter(prefix="/api/v1/cases", tags=["cases"])

@router.get("/")
async def list_cases(db: AsyncSession = Depends(get_db)):
    """List recent processing cases."""
    stmt = select(ProcessingCase).order_by(ProcessingCase.created_at.desc()).limit(10)
    result = await db.execute(stmt)
    cases = result.scalars().all()
    
    return [
        {
            "processing_id": str(c.processing_id),
            "trade_direction": c.trade_direction.value,
            "status": (c.results or {}).get("ui_status") or c.status.value,
            "created_at": c.created_at
        } for c in cases
    ]

@router.post("/")
async def create_case(trade_direction: str, db: AsyncSession = Depends(get_db)):
    """Create a new processing case and return its ID."""
    if trade_direction not in ["IMPORT", "EXPORT"]:
        raise HTTPException(status_code=400, detail="Invalid trade direction")
    
    new_case = ProcessingCase(
        trade_direction=TradeDirection.IMPORT if trade_direction == "IMPORT" else TradeDirection.EXPORT,
        status=CaseStatus.UPLOADING,
        results={}
    )
    db.add(new_case)
    await db.commit()
    await db.refresh(new_case)
    
    return {"processing_id": str(new_case.processing_id), "status": new_case.status.value}

@router.post("/{processing_id}/documents")
async def upload_documents(processing_id: str, files: List[UploadFile] = File(...), db: AsyncSession = Depends(get_db)):
    """Upload documents to a specific case."""
    stmt = select(ProcessingCase).where(ProcessingCase.processing_id == uuid.UUID(processing_id))
    result = await db.execute(stmt)
    case = result.scalar_one_or_none()
    
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
        
    uploaded_docs = []
    save_dir = f"./storage/uploads/{processing_id}"
    os.makedirs(save_dir, exist_ok=True)
    
    for file in files:
        file_path = f"{save_dir}/{file.filename}"
        with open(file_path, "wb") as f:
            f.write(await file.read())
            
        ext = file.filename.split('.')[-1].upper() if '.' in file.filename else "UNKNOWN"
        new_doc = Document(
            processing_id=uuid.UUID(processing_id),
            file_name=file.filename,
            document_type=ext,
            storage_uri=file_path,
            parse_status="INGESTED"
        )
        db.add(new_doc)
        
        uploaded_docs.append({
            "filename": file.filename,
            "size": file.size,
            "status": "INGESTED"
        })
        
    case.status = CaseStatus.INGESTED
    await db.commit()
    
    return {
        "processing_id": processing_id,
        "message": f"Successfully uploaded {len(files)} documents",
        "documents": uploaded_docs
    }

@router.post("/{processing_id}/submit")
async def submit_case(processing_id: str, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    """Finalize upload and start the LangGraph workflow."""
    stmt = select(ProcessingCase).where(ProcessingCase.processing_id == uuid.UUID(processing_id))
    result = await db.execute(stmt)
    case = result.scalar_one_or_none()
    
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
        
    case.status = CaseStatus.OCR_RUNNING
    await db.commit()
    
    doc_stmt = select(Document).where(Document.processing_id == uuid.UUID(processing_id))
    docs_result = await db.execute(doc_stmt)
    docs = docs_result.scalars().all()
    file_paths = [doc.storage_uri for doc in docs]
    
    background_tasks.add_task(
        run_acip_workflow, 
        processing_id, 
        case.trade_direction.value, 
        file_paths
    )
    
    return {"processing_id": processing_id, "status": "OCR_RUNNING", "message": "Workflow started"}

from typing import Optional

class ResolveDecision(BaseModel):
    decision: str
    comments: str = ""
    updated_data: Optional[dict] = None

@router.post("/{processing_id}/resolve")
async def resolve_case(processing_id: str, payload: ResolveDecision, db: AsyncSession = Depends(get_db)):
    """Resume a workflow paused for Human-in-the-Loop review."""
    stmt = select(ProcessingCase).where(ProcessingCase.processing_id == uuid.UUID(processing_id))
    result = await db.execute(stmt)
    case = result.scalar_one_or_none()
    
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
        
    if not case.results:
        case.results = {}
        
    res = case.results.copy()
    res["human_decision"] = payload.decision
    res["human_comments"] = payload.comments
    res["human_updated_data"] = payload.updated_data
    res["ui_status"] = "RESUMED"
    
    case.results = res
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(case, "results")
    await db.commit()
    
    return {"status": "SUCCESS", "message": f"Case {payload.decision.lower()}d"}

@router.get("/stats")
async def get_case_stats(db: AsyncSession = Depends(get_db)):
    """Get aggregate statistics for the dashboard."""
    stmt = select(ProcessingCase)
    result = await db.execute(stmt)
    cases = result.scalars().all()
    
    total = len(cases)
    approved = 0
    rejected = 0
    
    for case in cases:
        status = case.status.value
        ui_status = (case.results or {}).get('ui_status')
        if status == "READY":
            approved += 1
        elif status in ["REJECTED", "FAILED"] or ui_status == "REJECTED":
            rejected += 1
            
    return {
        "total_shipments": total,
        "approved_shipments": approved,
        "rejected_shipments": rejected,
        "pending_shipments": total - approved - rejected
    }

@router.get("/{processing_id}")
async def get_case_status(processing_id: str, db: AsyncSession = Depends(get_db)):
    """Poll the current status of the processing case."""
    try:
        stmt = select(ProcessingCase).where(ProcessingCase.processing_id == uuid.UUID(processing_id))
        result = await db.execute(stmt)
        case = result.scalar_one_or_none()
        
        if not case:
            raise HTTPException(status_code=404, detail="Case not found")
            
        res = case.results or {}
        # Map backend state to frontend expectations seamlessly
        display_status = res.get('ui_status') or case.status.value
        
        return {
            "processing_id": str(case.processing_id),
            "trade_direction": case.trade_direction.value,
            "status": display_status,
            "reason": res.get("reason", ""),
            "slip": res.get("slip", {}),
            "extracted_data": res.get("extracted_data", {})
        }
    except Exception as e:
        raise HTTPException(status_code=404, detail="Case not found or invalid UUID")

@router.get("/{processing_id}/boe")
async def download_boe_pdf(processing_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(ProcessingCase).where(ProcessingCase.processing_id == uuid.UUID(processing_id))
    result = await db.execute(stmt)
    case = result.scalar_one_or_none()
    
    if not case or case.status != CaseStatus.READY:
        raise HTTPException(status_code=400, detail="Case is not READY yet")
        
    slip_data = case.results.get("slip", {"status": "FAILED"}) if case.results else {}
    pdf_buffer = generate_boe_pdf(slip_data)
    
    return StreamingResponse(
        pdf_buffer, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename=Bill_of_Entry_{processing_id}.pdf"}
    )

@router.get("/{processing_id}/checklist")
async def download_checklist_pdf(processing_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(ProcessingCase).where(ProcessingCase.processing_id == uuid.UUID(processing_id))
    result = await db.execute(stmt)
    case = result.scalar_one_or_none()
    
    if not case or case.status != CaseStatus.READY:
        raise HTTPException(status_code=400, detail="Case is not READY yet")
        
    slip_data = case.results.get("slip", {"status": "FAILED"}) if case.results else {}
    pdf_buffer = generate_checklist_pdf(slip_data)
    
    return StreamingResponse(
        pdf_buffer, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename=Customs_Checklist_{processing_id}.pdf"}
    )

from app.db.models.models import AuditEvent
import json



@router.get("/{processing_id}/audit")
async def get_audit_timeline(processing_id: str, db: AsyncSession = Depends(get_db)):
    """Get audit events for a specific case."""
    stmt = select(AuditEvent).where(
        AuditEvent.processing_id == uuid.UUID(processing_id)
    ).order_by(AuditEvent.created_at.asc())
    result = await db.execute(stmt)
    events = result.scalars().all()
    
    return [
        {
            "id": str(e.id),
            "event_type": e.event_type,
            "details": json.loads(e.details) if e.details else {},
            "created_at": e.created_at
        } for e in events
    ]

from app.db.models.models import OcrEvidence, DocumentPage

@router.delete("/{processing_id}")
async def delete_case(processing_id: str, db: AsyncSession = Depends(get_db)):
    """Hard delete a processing case and all its associated records."""
    stmt = select(ProcessingCase).where(ProcessingCase.processing_id == uuid.UUID(processing_id))
    result = await db.execute(stmt)
    case = result.scalar_one_or_none()
    
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
        
    # Delete Audit Events
    from sqlalchemy import delete
    await db.execute(delete(AuditEvent).where(AuditEvent.processing_id == uuid.UUID(processing_id)))
    
    # Get Documents
    doc_stmt = select(Document).where(Document.processing_id == uuid.UUID(processing_id))
    docs_result = await db.execute(doc_stmt)
    docs = docs_result.scalars().all()
    
    for doc in docs:
        await db.execute(delete(OcrEvidence).where(OcrEvidence.document_id == doc.document_id))
        await db.execute(delete(DocumentPage).where(DocumentPage.document_id == doc.document_id))
        
    await db.execute(delete(Document).where(Document.processing_id == uuid.UUID(processing_id)))
    await db.execute(delete(ProcessingCase).where(ProcessingCase.processing_id == uuid.UUID(processing_id)))
    
    await db.commit()
    return {"message": "Case deleted successfully"}
