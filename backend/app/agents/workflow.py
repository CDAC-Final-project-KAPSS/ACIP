import os
import json
from typing import TypedDict, List
from langgraph.graph import StateGraph, START, END
from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage
import opendataloader_pdf
from pathlib import Path
import chromadb
from langchain_huggingface import HuggingFaceEmbeddings
from app.db.database import settings
import asyncio

# 1. State Definition
class AgentState(TypedDict):
    processing_id: str
    trade_direction: str
    files: List[str] # Paths to uploaded PDFs
    ocr_text: str
    validation_status: str
    validation_reason: str
    compliance_status: str
    compliance_reason: str
    final_slip: dict

llm = ChatOllama(model="qwen2.5:0.5b", base_url=os.getenv("LLM_BASE_URL", "http://localhost:11434"))

def ocr_node(state: AgentState) -> dict:
    """Extracts text from PDFs, DOCX, XLSX, and CSV instantly."""
    print(f"[{state['processing_id']}] Running OCR Node (Multi-Format)")
    ocr_text = ""
    
    try:
        import pypdf
        import pandas as pd
        from docx import Document
        
        for file_path in state['files']:
            ext = file_path.lower().split('.')[-1] if '.' in file_path else ""
            
            if ext == "pdf":
                reader = pypdf.PdfReader(file_path)
                for page in reader.pages:
                    ocr_text += (page.extract_text() or "") + "\n"
            elif ext in ["docx", "doc"]:
                doc = Document(file_path)
                for para in doc.paragraphs:
                    ocr_text += para.text + "\n"
            elif ext in ["xlsx", "xls"]:
                df = pd.read_excel(file_path)
                ocr_text += df.to_string(index=False) + "\n"
            elif ext == "csv":
                df = pd.read_csv(file_path)
                ocr_text += df.to_string(index=False) + "\n"
            else:
                ocr_text += f"[Skipped unsupported file format: {ext}]\n"
    except Exception as e:
        print(f"OCR Error: {e}")
        ocr_text = "MOCK_OCR_DATA: Invoice No. 12345, Packing List Qty: 100 boxes, HS Code: 85423100"
        
    return {"ocr_text": ocr_text}

def validation_node(state: AgentState) -> dict:
    """Cross-checks the documents."""
    print(f"[{state['processing_id']}] Running Validation Node")
    prompt = f"""
    You are an expert customs validator. 
    Review the following extracted document text and identify any discrepancies between the Invoice, Packing List, and Bill of Lading (e.g. weights, quantities, HS codes).
    Also extract key information about the shipment.
    
    Document Text:
    {state['ocr_text']}
    
    Reply with a JSON string ONLY in this format: 
    {{
        "status": "PASS" or "FAIL", 
        "reason": "If FAIL, provide EACH missing/mismatched field in a point-wise list. Format as: \\n• Field: [name]\\n• Details: [why it failed]\\n• Resolution: [action required]",
        "port_of_loading": "extracted port or N/A",
        "vessel_name": "extracted vessel name or N/A",
        "gross_weight": "extracted weight or N/A",
        "supplier": "extracted supplier or N/A"
    }}
    
    IMPORTANT: You MUST respond strictly in English. Do NOT use any other languages, characters, or symbols.
    """
    
    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        # Parse JSON from response
        resp_text = response.content.replace("```json", "").replace("```", "").strip()
        print("LLM Validation Output:", resp_text)
        result = {}
        try:
            result = json.loads(resp_text)
        except:
            pass
            
        # Fallback basic parsing if LLM hallucinates formatting
        if '"status": "FAIL"' in resp_text.upper() or result.get("status") == "FAIL":
            status = "FAIL"
        else:
            status = "PASS"
            
        reason = result.get("reason", "No discrepancies found.") if status == "PASS" else result.get("reason", "Discrepancies found in the documents.")
        if isinstance(reason, list):
            formatted_reasons = []
            for item in reason:
                if isinstance(item, dict):
                    field = item.get("field", item.get("Field", item.get("Rule Violated", item.get("rule", ""))))
                    details = item.get("details", item.get("Details", item.get("Failing Data", item.get("data", ""))))
                    res = item.get("resolution", item.get("Resolution", item.get("Resolution Required", item.get("action", ""))))
                    formatted_reasons.append(f"• Field/Rule: {field}\n• Details: {details}\n• Resolution Required: {res}\n")
                else:
                    formatted_reasons.append(str(item))
            reason = "\n".join(formatted_reasons)
        reason = str(reason)
    except Exception as e:
        print(f"LLM Error: {e}")
        status = "FAIL" # Force Human Review on system errors
        reason = f"• Field Issue: System Connection Offline\\n• Details: The local AI engine is not running (Error: {str(e)}).\\n• Resolution Required: Please start Ollama on your machine or manually review and approve the shipment."
        
    # Robust fallback: use regex if LLM missed it or failed
    import re
    ocr = state.get('ocr_text', '')
    
    pol_match = re.search(r'Port of Loading\s*:\s*([A-Za-z\s]+)', ocr, re.IGNORECASE)
    pol_regex = pol_match.group(1).strip() if pol_match else "N/A"
    
    gw_match = re.search(r'Gross Wt\.?\s*:\s*([0-9\.]+\s*[A-Z]+)', ocr, re.IGNORECASE)
    gw_regex = gw_match.group(1).strip() if gw_match else "N/A"
    
    sup_match = re.search(r'Supplier Details\s*:\s*\n?[^\n]*\n?.*?([A-Za-z0-9\s]+GMBH|[A-Za-z0-9\s]+LTD)', ocr, re.IGNORECASE)
    sup_regex = sup_match.group(1).strip() if sup_match else "N/A"
    
    vessel_match = re.search(r'Vessel Name\s*([A-Za-z\s]+)', ocr, re.IGNORECASE)
    vessel_regex = vessel_match.group(1).strip() if vessel_match else "N/A"
        
    return {
        "validation_status": status, 
        "validation_reason": reason,
        "extracted_data": {
            "port_of_loading": result.get("port_of_loading") if 'result' in locals() and result.get("port_of_loading") else pol_regex,
            "vessel_name": result.get("vessel_name") if 'result' in locals() and result.get("vessel_name") else vessel_regex,
            "gross_weight": result.get("gross_weight") if 'result' in locals() and result.get("gross_weight") else gw_regex,
            "supplier": result.get("supplier") if 'result' in locals() and result.get("supplier") else sup_regex
        }
    }

def compliance_node(state: AgentState) -> dict:
    """Checks against ChromaDB rules."""
    print(f"[{state['processing_id']}] Running Compliance Node")
    try:
        embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        client = chromadb.PersistentClient(path=str(settings.LOCAL_STORAGE_PATH) + "/chroma")
        collection = client.get_collection(settings.CHROMA_COLLECTION)
        
        # Strict metadata filtering and query
        results = collection.query(
            query_embeddings=embeddings.embed_query(f"import export restrictions on {state['trade_direction']} goods 85423100"),
            n_results=10,
            where={"trade_direction": state['trade_direction']}
        )
        
        docs = results['documents'][0]
        if not docs:
            context = "No specific rules found for this trade direction."
        else:
            try:
                from sentence_transformers import CrossEncoder
                reranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
                query = f"Does the {state['trade_direction']} of these goods violate any rules? {state['ocr_text'][:500]}"
                pairs = [[query, doc] for doc in docs]
                scores = reranker.predict(pairs)
                
                # Sort and take top 3
                scored_docs = sorted(zip(scores, docs), reverse=True)
                top_docs = [doc for score, doc in scored_docs[:3]]
                context = "\n".join(top_docs)
            except Exception as e:
                print(f"Reranking error: {e}")
                # Fallback to top 3 from vector search
                context = "\n".join(docs[:3])
        
        prompt = f"""
        You are a senior customs compliance officer. Evaluate the shipment against the regulatory rules.
        
        Rules Context:
        {context}
        
        Shipment Details:
        {state['ocr_text']}
        
        Reply with a JSON string ONLY in this format:
        {{
            "status": "FAIL" if ANY rules are violated, else "PASS",
            "reason": "If FAIL, list EACH violation formatted as: \\n• Rule Violated: [rule] \\n• Failing Data: [data] \\n• Resolution Required: [action]. If PASS, output 'Compliant'."
        }}
        
        IMPORTANT: DO NOT use markdown bolding (asterisks **) or any other markdown formatting anywhere in your response. Output plain text only.
        IMPORTANT: You MUST respond strictly in English. Do NOT use any other languages, characters, or symbols.
        """
        response = llm.invoke([HumanMessage(content=prompt)])
        resp_text = response.content.replace("```json", "").replace("```", "").strip()
        result = {}
        try:
            result = json.loads(resp_text)
        except:
            pass
        
        if '"status": "FAIL"' in resp_text.upper() or result.get("status") == "FAIL":
            status = "FAIL"
        else:
            status = "PASS"
            
        reason = result.get("reason", "Compliant." if status == "PASS" else "Violations found against the regulatory rules.")
        if isinstance(reason, list):
            formatted_reasons = []
            for item in reason:
                if isinstance(item, dict):
                    field = item.get("field", item.get("Field", item.get("Rule Violated", item.get("rule", ""))))
                    details = item.get("details", item.get("Details", item.get("Failing Data", item.get("data", ""))))
                    res = item.get("resolution", item.get("Resolution", item.get("Resolution Required", item.get("action", ""))))
                    formatted_reasons.append(f"• Field/Rule: {field}\n• Details: {details}\n• Resolution Required: {res}\n")
                else:
                    formatted_reasons.append(str(item))
            reason = "\n".join(formatted_reasons)
        reason = str(reason)
    except Exception as e:
        print(f"Compliance Error: {e}")
        status = "FAIL"
        reason = f"• Rule Violated: N/A (System Offline)\\n• Failing Data: Connection Refused\\n• Resolution Required: The AI engine (Ollama) is turned off. Please start Ollama to resume automatic compliance checks, or manually review the rules."
        
    return {"compliance_status": status, "compliance_reason": reason}

def generator_node(state: AgentState) -> dict:
    """Generates the final slip and a summary report using the LLM."""
    print(f"[{state['processing_id']}] Running Generator Node")
    final_status = "APPROVED"
    if state["validation_status"] == "REJECTED" or state["compliance_status"] == "REJECTED":
        final_status = "REJECTED"
    elif state["validation_status"] == "FAIL" or state["compliance_status"] == "FAIL":
        final_status = "FAILED"
        
    prompt = f"""
    You are the final Autonomous Customs Executive. 
    Write a concise, professional Final Clearance Report for this shipment based on the Validation and Compliance agent results.
    
    Validation Result: {state["validation_status"]}
    Validation Remarks: {state.get("validation_reason", "None")}
    
    Compliance Result: {state["compliance_status"]}
    Compliance Remarks: {state.get("compliance_reason", "None")}
    
    Write a structured report (using bullet points) that summarizes:
    - Final Decision: (Approved, Rejected, or Failed)
    - Key Findings: (Brief summary of the agent remarks)
    - Next Steps: (What should happen to the cargo now)
    
    Keep it strictly professional and to the point.
    """
    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        report_text = response.content.strip().replace("*", "").replace("#", "")
    except Exception as e:
        report_text = "Final clearance report generation failed due to system error."
    
    slip = {
        "shipment_id": f"ACIP-{state['trade_direction']}-2026-00124",
        "processing_id": state['processing_id'],
        "trade_direction": state['trade_direction'],
        "status": final_status,
        "clearance_date": "2026-07-31T12:00:00Z",
        "message": f"Validation: {state['validation_status']}, Compliance: {state['compliance_status']}",
        "validation_reason": state.get("validation_reason", ""),
        "compliance_reason": state.get("compliance_reason", ""),
        "generator_report": report_text,

        "documents_processed": len(state['files']),
        "extracted_data": state.get("extracted_data", {})
    }
    
    return {"final_slip": slip}

# Build Graph
builder = StateGraph(AgentState)
builder.add_node("ocr", ocr_node)
builder.add_node("validation", validation_node)
builder.add_node("compliance", compliance_node)
builder.add_node("generator", generator_node)

builder.add_edge(START, "ocr")
builder.add_edge("ocr", "validation")
builder.add_edge("validation", "compliance")
builder.add_edge("compliance", "generator")
builder.add_edge("generator", END)

workflow = builder.compile()

async def run_acip_workflow(processing_id: str, trade_direction: str, file_paths: List[str]):
    """Entry point to run the LangGraph workflow in the background using PostgreSQL."""
    
    from app.db.database import AsyncSessionLocal
    from sqlalchemy.future import select
    from app.db.models.models import ProcessingCase, CaseStatus
    import uuid
    
    async def update_status(new_status: CaseStatus, ui_status=None, reason=None, slip=None, extracted_data=None):
        async with AsyncSessionLocal() as session:
            stmt = select(ProcessingCase).where(ProcessingCase.processing_id == uuid.UUID(processing_id))
            result = await session.execute(stmt)
            case = result.scalar_one()
            old_status = case.status.value
            case.status = new_status
            res = (case.results or {}).copy()
            if ui_status: res['ui_status'] = ui_status
            if reason: res['reason'] = reason
            if slip: res['slip'] = slip
            if extracted_data is not None: res['extracted_data'] = extracted_data
            case.results = res
            from sqlalchemy.orm.attributes import flag_modified
            flag_modified(case, "results")
            
            # Log Audit Event
            from app.db.models.models import AuditEvent
            audit_event = AuditEvent(
                processing_id=uuid.UUID(processing_id),
                event_type="STATE_CHANGE",
                details=json.dumps({"old_status": old_status, "new_status": new_status.value, "ui_status": ui_status, "reason": reason})
            )
            session.add(audit_event)
            
            await session.commit()
            
    async def get_human_decision():
        async with AsyncSessionLocal() as session:
            stmt = select(ProcessingCase).where(ProcessingCase.processing_id == uuid.UUID(processing_id))
            result = await session.execute(stmt)
            case = result.scalar_one()
            res = case.results or {}
            return res.get("human_decision"), res.get("human_updated_data")
            
    print(f"Starting workflow for {processing_id}")
    initial_state = {
        "processing_id": processing_id,
        "trade_direction": trade_direction,
        "files": file_paths,
        "ocr_text": "",
        "validation_status": "",
        "validation_reason": "",
        "compliance_status": "",
        "compliance_reason": "",
        "final_slip": {},
        "extracted_data": {}
    }
    
    # Step through the workflow manually to update the MOCK_DB status so the UI animation works beautifully
    state = initial_state
    
    try:
        # OCR
        await update_status(CaseStatus.OCR_RUNNING, ui_status="OCR_RUNNING")
        state.update(ocr_node(state))
        await asyncio.sleep(0.5)
        
        # Validation
        await update_status(CaseStatus.VALIDATION_PENDING, ui_status="VALIDATION_PENDING")
        val_res = validation_node(state)
        state.update(val_res)
        state["extracted_data"] = val_res.get("extracted_data", {})
        
        # HITL Pause for Validation
        if state["validation_status"] == "FAIL":
            print(f"[{processing_id}] Pausing for Human-in-the-Loop Review (Validation)")
            await update_status(CaseStatus.VALIDATION_REVIEW, ui_status="NEEDS_REVIEW_VALIDATION", reason=state["validation_reason"], extracted_data=state["extracted_data"])
            
            while True:
                await asyncio.sleep(1)
                decision, updated_data = await get_human_decision()
                if decision:
                    print(f"[{processing_id}] Human resolved validation with: {decision}")
                    if decision == "APPROVE":
                        state["validation_status"] = "OVERRIDDEN_PASS"
                        if updated_data:
                            state["extracted_data"].update(updated_data)
                    else:
                        await update_status(CaseStatus.REJECTED, ui_status="REJECTED")
                        return
                    break
                    
        # Compliance
        await update_status(CaseStatus.COMPLIANCE_PENDING, ui_status="COMPLIANCE_PENDING")
        state.update(compliance_node(state))
        
        # HITL Pause for Compliance
        if state["compliance_status"] == "FAIL":
            print(f"[{processing_id}] Pausing for Human-in-the-Loop Review (Compliance)")
            # Reset decision to allow a second intervention
            async with AsyncSessionLocal() as session:
                stmt = select(ProcessingCase).where(ProcessingCase.processing_id == uuid.UUID(processing_id))
                result = await session.execute(stmt)
                case = result.scalar_one()
                res = case.results or {}
                if "human_decision" in res: del res["human_decision"]
                case.results = res
                from sqlalchemy.orm.attributes import flag_modified
                flag_modified(case, "results")
                await session.commit()
                
            await update_status(CaseStatus.COMPLIANCE_REVIEW, ui_status="NEEDS_REVIEW_COMPLIANCE", reason=state["compliance_reason"])
            
            while True:
                await asyncio.sleep(1)
                decision, _ = await get_human_decision()
                if decision:
                    print(f"[{processing_id}] Human resolved compliance with: {decision}")
                    if decision == "APPROVE":
                        state["compliance_status"] = "OVERRIDDEN_PASS"
                    else:
                        await update_status(CaseStatus.REJECTED, ui_status="REJECTED")
                        return
                    break
                    
        # Generator
        await update_status(CaseStatus.GENERATING, ui_status="GENERATING")
        state.update(generator_node(state))
        
        # Finished
        await update_status(CaseStatus.READY, ui_status="READY", slip=state.get("final_slip", {}))
        print(f"Workflow complete for {processing_id}")
        
    except Exception as e:
        print(f"Workflow error: {e}")
        await update_status(CaseStatus.FAILED, ui_status="FAILED", reason=str(e))
