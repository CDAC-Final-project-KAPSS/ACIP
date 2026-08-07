<div align="center">
  <h1>🚢 Autonomous Customs Intelligence Platform (ACIP)</h1>
  <p>An AI-powered, multi-agent enterprise platform designed to automate customs clearance, document validation, and regulatory compliance checking for international trade.</p>
</div>

---

## 🌟 Key Features

- **🧠 Multi-Agent LangGraph Workflow**: Autonomous agents (OCR, Validator, Compliance, Generator) work sequentially to process shipments.
- **📄 Universal Document Extraction**: Natively extracts text and structured data from PDFs, Word Documents (`.docx`), and Excel Sheets (`.xlsx`, `.csv`).
- **🔍 RAG-powered Compliance**: Uses ChromaDB and HuggingFace Embeddings to semantically query thousands of pages of customs regulations in milliseconds.
- **🛡️ Enterprise Role-Based Access Control (RBAC)**: Secure Master Admin portal to approve, reject, or pause user accounts.
- **🎨 Modern Glassmorphic UI**: Built with React, featuring real-time visual step tracking, interactive metrics dashboards, and beautiful animations.
- **👨‍💻 Human-in-the-Loop (HITL)**: Intelligently pauses the automated workflow and requests human intervention if discrepancies or compliance violations are found.
- **📑 Automated Document Generation**: Generates compliant Bills of Entry and Vessel Checklists instantly as downloadable PDFs.

## 🛠️ Technology Stack

- **Frontend**: React 18, Vite, TypeScript, Vanilla CSS (Glassmorphism design)
- **Backend**: FastAPI, Python 3.12, SQLAlchemy, Alembic
- **Database**: PostgreSQL
- **AI & LLMs**: LangChain, LangGraph, Ollama (`qwen2.5:0.5b`), HuggingFace, ChromaDB Vector Store
- **Data Processing**: pandas, pypdf, python-docx, openpyxl

## 🚀 Getting Started

### Prerequisites
- Node.js (v18+)
- Python (3.11+)
- PostgreSQL (running locally)
- [Ollama](https://ollama.ai/) installed and running on your machine.

### 1. Database Setup
Create a PostgreSQL database named `acip_platform_db`. Update your environment variables with the database credentials.

### 2. Backend Setup
```bash
cd backend
python -m venv venv
# Activate virtual environment
# Windows:
.\venv\Scripts\Activate.ps1
# Mac/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start the FastAPI Server
uvicorn app.main:app --reload
```

### 3. Frontend Setup
```bash
cd frontend
npm install

# Start the Vite development server
npm run dev
```

### 4. Local AI Setup
Make sure Ollama is running in the background, and pull the required lightweight model:
```bash
ollama run qwen2.5:0.5b
```

## 🔐 Default Admin Credentials

Upon the very first launch, the system automatically seeds a Master Admin account. Use this account to access the Admin Portal and approve new user registrations.

- **Email**: `p4shinde2003@gmail.com`
- **Password**: `Admin@100`

## 📁 Architecture Overview

1. **Ingestion Node**: Users drag and drop shipment files.
2. **OCR Node**: Extracts tables and text dynamically depending on the file format.
3. **Validation Node (AI)**: Cross-checks Invoice, Packing List, and Bill of Lading data for consistency.
4. **Compliance Node (RAG)**: Queries local vector stores to ensure goods aren't restricted.
5. **Generator Node (AI)**: Drafts the final clearance report and generates PDFs.

---
<div align="center">
  <i>Built for the future of international trade compliance.</i>
</div>
