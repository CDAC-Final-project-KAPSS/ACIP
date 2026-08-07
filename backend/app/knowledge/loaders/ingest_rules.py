import os
import sys
from pathlib import Path
import chromadb
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings

# Add backend directory to sys path so we can import app settings
sys.path.append(str(Path(__file__).parent.parent.parent.parent))
from app.db.database import settings

RULES_DIR = Path("D:/ACIP_Platform_Project/Rules and Regulation")
CHROMA_DIR = Path("D:/ACIP_Platform_Project/acip/backend/storage/chroma")

def ingest_regulations():
    print("Initializing embedding model...")
    # Use HuggingFace embeddings locally
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    
    print(f"Connecting to ChromaDB at {CHROMA_DIR}...")
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    
    # Create or get collection
    collection = client.get_or_create_collection(
        name=settings.CHROMA_COLLECTION,
        metadata={"hnsw:space": "cosine"}
    )
    
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=100,
        length_function=len,
    )
    
    if not RULES_DIR.exists():
        print(f"Error: Rules directory {RULES_DIR} not found.")
        return
        
    pdf_files = list(RULES_DIR.glob("*.pdf"))
    print(f"Found {len(pdf_files)} PDF files for ingestion.")
    
    for pdf_path in pdf_files:
        print(f"Processing {pdf_path.name}...")
        try:
            loader = PyPDFLoader(str(pdf_path))
            docs = loader.load()
            
            chunks = splitter.split_documents(docs)
            print(f"  -> Generated {len(chunks)} chunks.")
            
            # Prepare for Chroma ingestion
            documents = []
            metadatas = []
            ids = []
            
            for i, chunk in enumerate(chunks):
                documents.append(chunk.page_content)
                metadata = chunk.metadata.copy()
                metadata["source_file"] = pdf_path.name
                metadatas.append(metadata)
                ids.append(f"{pdf_path.stem}_chunk_{i}")
                
            # Batch upsert to ChromaDB in chunks of 100 to avoid memory issues
            batch_size = 100
            for i in range(0, len(documents), batch_size):
                collection.upsert(
                    documents=documents[i:i+batch_size],
                    metadatas=metadatas[i:i+batch_size],
                    ids=ids[i:i+batch_size]
                )
                
            print(f"  -> Successfully ingested {pdf_path.name}.")
        except Exception as e:
            print(f"  -> Error processing {pdf_path.name}: {e}")

    print(f"Ingestion complete. Vector database is ready at {CHROMA_DIR}.")

if __name__ == "__main__":
    ingest_regulations()
