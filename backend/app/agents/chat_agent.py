import os
import chromadb
import json
from datetime import datetime, timedelta
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage
from app.db.database import settings, AsyncSessionLocal
from app.db.models.models import ProcessingCase
from sqlalchemy.future import select

# Initialize LLM
llm = ChatOllama(model="qwen2.5:0.5b", base_url=os.getenv("LLM_BASE_URL", "http://localhost:11434"))

async def fetch_db_context() -> str:
    """Fetches operational stats from Postgres DB"""
    try:
        async with AsyncSessionLocal() as db:
            stmt = select(ProcessingCase)
            result = await db.execute(stmt)
            cases = result.scalars().all()
            
            now = datetime.utcnow()
            
            stats = {
                "today": {"total": 0, "approved": 0, "rejected": 0, "pending": 0},
                "yesterday": {"total": 0, "approved": 0, "rejected": 0, "pending": 0},
                "all_time": {"total": 0, "approved": 0, "rejected": 0, "pending": 0},
                "recent_failures": []
            }
            
            for case in cases:
                status = case.status.value
                ui_status = (case.results or {}).get('ui_status')
                
                is_approved = status == "READY"
                is_rejected = status in ["REJECTED", "FAILED"] or ui_status == "REJECTED"
                
                # Determine time bucket
                diff_days = (now - case.created_at).days
                buckets = ["all_time"]
                if diff_days == 0:
                    buckets.append("today")
                elif diff_days == 1:
                    buckets.append("yesterday")
                    
                for b in buckets:
                    stats[b]["total"] += 1
                    if is_approved:
                        stats[b]["approved"] += 1
                    elif is_rejected:
                        stats[b]["rejected"] += 1
                    else:
                        stats[b]["pending"] += 1
                        
                if status == "FAILED" and len(stats["recent_failures"]) < 5:
                    stats["recent_failures"].append(f"Shipment {case.processing_id} failed: {(case.results or {}).get('error', 'Unknown')}")
            
            db_summary = (
                f"Today: {stats['today']['total']} total shipments processed ({stats['today']['approved']} approved, {stats['today']['rejected']} rejected, {stats['today']['pending']} pending).\n"
                f"Yesterday: {stats['yesterday']['total']} total shipments processed ({stats['yesterday']['approved']} approved, {stats['yesterday']['rejected']} rejected, {stats['yesterday']['pending']} pending).\n"
                f"All Time: {stats['all_time']['total']} total shipments processed ({stats['all_time']['approved']} approved, {stats['all_time']['rejected']} rejected, {stats['all_time']['pending']} pending).\n"
            )
            
            if stats["recent_failures"] != "None":
                db_summary += "Recent Failures: " + ", ".join(stats["recent_failures"])
            else:
                db_summary += "Recent Failures: None."
                
            return db_summary
    except Exception as e:
        print(f"DB Context Fetch Error: {e}")
        return "Database statistics are currently unavailable."

async def ask_chatbot(query: str) -> str:
    """
    Retrieves context from ChromaDB (Rules) and PostgreSQL (Stats) 
    and passes it to the LLM to answer the user's query.
    Enforces dual-context guardrails.
    """
    try:
        client = chromadb.PersistentClient(path=str(settings.LOCAL_STORAGE_PATH) + "/chroma")
        collection = client.get_collection(settings.CHROMA_COLLECTION)
        
        # Query ChromaDB (Using query_texts as it's a simpler string query)
        results = collection.query(
            query_texts=[query],
            n_results=5
        )
        
        docs = results.get('documents', [])
        distances = results.get('distances', [])
        
        valid_rules = False
        context = "No relevant customs rules or regulations were found in the database."
        
        if docs and len(docs) > 0 and distances and len(distances) > 0:
            # Check if at least one result has a distance < 1.0 (a strict semantic match)
            if distances[0][0] < 1.0:
                valid_rules = True
                context_docs = docs[0]
                context = "\n".join(context_docs)
                
        # Check if the query is asking about DB stats
        db_keywords = ["shipment", "approved", "rejected", "pending", "today", "yesterday", "fail", "status", "total"]
        asking_about_stats = any(keyword in query.lower() for keyword in db_keywords)
        
        # Hard Python Guardrail: If neither rules nor stats are relevant, block it!
        if not valid_rules and not asking_about_stats:
            return "I am an ACIP Customs Assistant. I can only answer questions related to customs regulations or live system statistics."
            
            
        db_context = await fetch_db_context()
            
        prompt = f"""
        You are the ACIP Customs Assistant. 
        Your ONLY job is to answer the user's question directly and concisely.
        
        Available Knowledge:
        - Rules Context: {context}
        - Database Context (Live Stats):
        {db_context}
        
        User Question: {query}
        
        Strict Output Formatting Rules:
        1. OUTPUT ONLY THE FINAL ANSWER.
        2. DO NOT use introductory phrases.
        3. DO NOT output your thought process.
        4. If asked about today/yesterday statistics, quote the numbers directly from the Database Context.
        5. If asked about regulations, use the Rules Context.
        6. Keep the answer to a single short sentence.
        """
        
        response = llm.invoke([HumanMessage(content=prompt)])
        return response.content
        
    except Exception as e:
        print(f"Chatbot Agent Error: {e}")
        return "An error occurred while connecting to the knowledge base. Please try again."

def ingest_text_rule(rule_text: str):
    """
    Takes a plain text rule from the Admin and ingests it directly into ChromaDB.
    """
    try:
        from langchain_text_splitters import RecursiveCharacterTextSplitter
        
        client = chromadb.PersistentClient(path=str(settings.LOCAL_STORAGE_PATH) + "/chroma")
        collection = client.get_collection(settings.CHROMA_COLLECTION)
        
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=800,
            chunk_overlap=100,
            length_function=len,
        )
        
        chunks = splitter.split_text(rule_text)
        
        import uuid
        documents = []
        metadatas = []
        ids = []
        
        for i, chunk in enumerate(chunks):
            documents.append(chunk)
            metadatas.append({"source_file": "admin_chatbot_upload"})
            ids.append(f"chatbot_rule_{uuid.uuid4().hex}_{i}")
            
        collection.upsert(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
        return True, f"Successfully added {len(chunks)} chunks to the knowledge base."
    except Exception as e:
        print(f"Chatbot Ingestion Error: {e}")
        return False, str(e)
