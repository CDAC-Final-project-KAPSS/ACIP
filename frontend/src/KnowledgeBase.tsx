import { useState } from 'react';

export default function KnowledgeBase({ authToken }: { authToken: string }) {
  const [file, setFile] = useState<File | null>(null);
  const [tradeDirection, setTradeDirection] = useState('IMPORT');
  const [jurisdiction, setJurisdiction] = useState('Global');
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return;

    setUploading(true);
    setMessage('');
    setError('');

    const formData = new FormData();
    formData.append('file', file);
    formData.append('trade_direction', tradeDirection);
    formData.append('jurisdiction', jurisdiction);

    try {
      const res = await fetch('http://127.0.0.1:8000/api/v1/admin/knowledge/upload', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${authToken}`
        },
        body: formData
      });
      const data = await res.json();
      if (res.ok) {
        setMessage(data.message);
        setFile(null);
      } else {
        setError(data.detail || 'Failed to upload regulation.');
      }
    } catch (err) {
      setError('Network error during upload.');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="glass-card animate-fade-in container my-4 p-4 p-md-5" style={{ maxWidth: '800px' }}>
      <h2 className="mb-4 pb-3 border-bottom border-secondary">Regulation Knowledge Base</h2>
      <p className="text-secondary mb-4">
        Upload PDF documents containing customs regulations, trade restrictions, or compliance checklists. 
        These documents are vectorized and ingested into ChromaDB to power the Autonomous Compliance Agent's RAG system.
      </p>

      {message && <div className="alert alert-success py-2">{message}</div>}
      {error && <div className="alert alert-danger py-2">{error}</div>}

      <form onSubmit={handleUpload} className="d-flex flex-column gap-3">
        <div className="row">
          <div className="col-md-6">
            <div className="form-floating">
              <select 
                className="form-select bg-transparent text-body border-secondary" 
                id="tradeDirSelect"
                value={tradeDirection}
                onChange={e => setTradeDirection(e.target.value)}
              >
                <option value="IMPORT">IMPORT</option>
                <option value="EXPORT">EXPORT</option>
              </select>
              <label htmlFor="tradeDirSelect" className="text-secondary">Trade Direction Filter</label>
            </div>
          </div>
          <div className="col-md-6">
            <div className="form-floating">
              <input 
                type="text" 
                className="form-control bg-transparent text-body border-secondary" 
                id="jurisdictionInput"
                placeholder="Global"
                value={jurisdiction}
                onChange={e => setJurisdiction(e.target.value)}
                required
              />
              <label htmlFor="jurisdictionInput" className="text-secondary">Jurisdiction (e.g. EU, US, Global)</label>
            </div>
          </div>
        </div>

        <div>
          <label className="form-label text-secondary small mb-1">Regulation PDF Document</label>
          <input 
            type="file" 
            className="form-control bg-transparent text-body border-secondary py-3" 
            accept=".pdf"
            onChange={e => e.target.files && setFile(e.target.files[0])}
            required
          />
        </div>

        <button 
          type="submit" 
          className="btn btn-primary py-2 mt-3 fw-semibold shadow-sm rounded-3"
          disabled={uploading || !file}
        >
          {uploading ? (
            <><span className="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span> Ingesting into Vector DB...</>
          ) : (
            <><i className="bi bi-cloud-upload-fill me-2"></i> Ingest Document</>
          )}
        </button>
      </form>
    </div>
  );
}
