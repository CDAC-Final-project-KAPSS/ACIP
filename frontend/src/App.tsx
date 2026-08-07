import { useState, useCallback, useEffect, useRef } from 'react'
import './index.css'
import AuthScreen from './AuthScreen'
import AdminPortal from './AdminPortal'
import KnowledgeBase from './KnowledgeBase'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts'
import acipLogo from './assets/aciplogo.png'

function App() {
  const [authToken, setAuthToken] = useState<string | null>(localStorage.getItem('token'));
  const [userEmail, setUserEmail] = useState<string | null>(localStorage.getItem('userEmail'));
  const [userRole, setUserRole] = useState<string | null>(localStorage.getItem('userRole'));
  
  const [currentView, setCurrentView] = useState<'process' | 'metrics' | 'admin' | 'knowledge'>('metrics');
  const [tradeDirection, setTradeDirection] = useState<'IMPORT' | 'EXPORT'>('IMPORT');
  const [isDragging, setIsDragging] = useState(false);
  const [files, setFiles] = useState<File[]>([]);
  const [activeCaseId, setActiveCaseId] = useState<string | null>(null);
  const [caseData, setCaseData] = useState<any>(null);
  const [editData, setEditData] = useState<any>({});
  const [isPolling, setIsPolling] = useState(false);
  
  const [isProfileOpen, setIsProfileOpen] = useState(false);
  const profileRef = useRef<HTMLDivElement>(null);
  
  const [globalStats, setGlobalStats] = useState<any>(null);
  const [recentCases, setRecentCases] = useState<any[]>([]);
  const [auditTimeline, setAuditTimeline] = useState<any[]>([]);
  
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [theme, setTheme] = useState<'dark' | 'light'>('dark');
  const [resolvingAction, setResolvingAction] = useState<string | null>(null);

  // Handle clicking outside of profile dropdown
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (profileRef.current && !profileRef.current.contains(event.target as Node)) {
        setIsProfileOpen(false);
      }
    };
    
    if (isProfileOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isProfileOpen]);

  useEffect(() => {
    document.body.setAttribute('data-bs-theme', theme);
  }, [theme]);

  const showToast = useCallback((msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3000);
  }, []);

  useEffect(() => {
    if (currentView === 'metrics') {
      fetch('http://127.0.0.1:8000/api/v1/cases/stats')
        .then(res => res.json())
        .then(data => setGlobalStats(data))
        .catch(console.error);

      fetch('http://127.0.0.1:8000/api/v1/cases/')
        .then(res => res.json())
        .then(data => setRecentCases(data))
        .catch(console.error);
    }
  }, [currentView]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const newFiles = Array.from(e.dataTransfer.files);
      setFiles(prev => [...prev, ...newFiles]);
    }
  }, []);

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const newFiles = Array.from(e.target.files);
      setFiles(prev => [...prev, ...newFiles]);
    }
  };

  const removeFile = (indexToRemove: number) => {
    setFiles(files.filter((_, index) => index !== indexToRemove));
  };

  const processShipment = async () => {
    if (files.length === 0) return;
    
    try {
      // 1. Create a processing case
      const caseRes = await fetch(`http://127.0.0.1:8000/api/v1/cases/?trade_direction=${tradeDirection}`, {
        method: 'POST'
      });
      const caseData = await caseRes.json();
      const processingId = caseData.processing_id;

      // 2. Upload documents
      const formData = new FormData();
      files.forEach(f => formData.append('files', f));
      
      await fetch(`http://127.0.0.1:8000/api/v1/cases/${processingId}/documents`, {
        method: 'POST',
        body: formData
      });

      // 3. Submit workflow
      const submitRes = await fetch(`http://127.0.0.1:8000/api/v1/cases/${processingId}/submit`, {
        method: 'POST'
      });
      await submitRes.json();
      
      setActiveCaseId(processingId);
    } catch (error) {
      alert('Error processing shipment. Please ensure the backend is running. Details: ' + error);
    }
  };

  useEffect(() => {
    if (activeCaseId) {
      setIsPolling(true);
    } else {
      setIsPolling(false);
    }
  }, [activeCaseId]);

  useEffect(() => {
    if (!activeCaseId || !isPolling) return;
    
    const interval = setInterval(async () => {
      try {
        const res = await fetch(`http://127.0.0.1:8000/api/v1/cases/${activeCaseId}`);
        const data = await res.json();
        setCaseData(data);
        
        const auditRes = await fetch(`http://127.0.0.1:8000/api/v1/cases/${activeCaseId}/audit`);
        if (auditRes.ok) {
          setAuditTimeline(await auditRes.json());
        }
        
        if (data.status === 'READY' || data.status === 'FAILED' || data.status === 'REJECTED' || data.detail ||
            data.status === 'VALIDATION_REVIEW' || data.status === 'COMPLIANCE_REVIEW' ||
            data.status === 'NEEDS_REVIEW_VALIDATION' || data.status === 'NEEDS_REVIEW_COMPLIANCE') {
          setIsPolling(false);
          clearInterval(interval);
        }
      } catch (e) {
        console.error(e);
      }
    }, 2000);
    
    return () => clearInterval(interval);
  }, [activeCaseId, isPolling]);

  const downloadPdf = async (type: string) => {
    try {
      const res = await fetch(`http://127.0.0.1:8000/api/v1/cases/${activeCaseId}/${type}`);
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${type === 'boe' ? 'Bill_of_Entry' : 'Customs_Checklist'}_${activeCaseId?.split('-')[0]}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
    } catch (error) {
      alert("Failed to download " + type);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('userEmail');
    setAuthToken(null);
    setUserEmail(null);
    setIsProfileOpen(false);
  };

  const renderDashboard = () => {
    if (!caseData) return <div className="text-center py-5 text-secondary">Loading dashboard...</div>;
    
    if (caseData.detail) {
      return (
        <div className="glass-card animate-fade-in text-center p-5">
          <h3 className="text-danger mb-3">Error Loading Case</h3>
          <p className="text-secondary">{caseData.detail}</p>
          <button className="btn btn-outline-primary mt-4 px-4" onClick={() => setActiveCaseId(null)}>
            Go Back
          </button>
        </div>
      );
    }
    
    const steps = ['UPLOADING', 'INGESTED', 'OCR_RUNNING', 'VALIDATION_PENDING', 'COMPLIANCE_PENDING', 'READY'];
    
    let displayStatus = caseData.status;
    if (displayStatus === 'VALIDATION_REVIEW' || displayStatus === 'COMPLIANCE_REVIEW' || displayStatus === 'NEEDS_REVIEW_VALIDATION' || displayStatus === 'NEEDS_REVIEW_COMPLIANCE' || displayStatus === 'REJECTED' || displayStatus === 'RESUMED') {
      if (displayStatus === 'COMPLIANCE_REVIEW' || displayStatus === 'NEEDS_REVIEW_COMPLIANCE' || (caseData.reason && caseData.reason.includes("Compliance"))) {
        displayStatus = 'COMPLIANCE_PENDING';
      } else {
        displayStatus = 'VALIDATION_PENDING';
      }
    }
    const currentStepIndex = steps.indexOf(displayStatus);

    const resolveConflict = async (decision: string) => {
      setResolvingAction(decision);
      try {
        await fetch(`http://127.0.0.1:8000/api/v1/cases/${activeCaseId}/resolve`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ decision, updated_data: Object.keys(editData).length > 0 ? editData : undefined })
        });
        showToast("Response saved");
        setIsPolling(true);
      } catch (e) {
        showToast("Failed to resolve conflict");
      } finally {
        setResolvingAction(null);
      }
    };

    return (
      <div className="glass-card animate-fade-in p-4 p-md-5 container" style={{ maxWidth: '1000px' }}>
        <div className="d-flex justify-content-between align-items-center mb-5 flex-wrap gap-3">
          <h2 className="mb-0">Shipment Dashboard</h2>
          <span className="badge bg-secondary bg-opacity-10 text-secondary border border-secondary px-3 py-2 fs-6 rounded-pill">
            ID: <span className="font-monospace">{caseData.processing_id?.split('-')[0] || 'Unknown'}...</span>
          </span>
        </div>

        <div className="position-relative mb-5 px-3">
          <div className="position-absolute top-50 start-0 end-0 translate-middle-y" style={{ height: '4px', background: 'var(--bs-border-color)', zIndex: 0 }}>
            <div className="bg-primary h-100" style={{ width: `${(Math.max(0, currentStepIndex) / (steps.length - 1)) * 100}%`, transition: 'width 0.5s ease' }}></div>
          </div>
          
          <div className="d-flex justify-content-between position-relative z-1">
            {steps.map((step, idx) => {
              const isCompleted = currentStepIndex >= idx;
              const isActive = currentStepIndex === idx;
              return (
                <div key={step} className="d-flex flex-column align-items-center gap-2" style={{ width: '80px' }}>
                  <div className={`d-flex align-items-center justify-content-center rounded-circle ${isActive ? 'bg-primary text-white shadow-sm' : isCompleted ? 'bg-success text-white' : 'bg-body-secondary text-secondary'} border border-2 ${isCompleted || isActive ? 'border-transparent' : 'border-secondary'}`} style={{ width: '40px', height: '40px', transition: 'all 0.3s ease' }}>
                    {isCompleted && !isActive ? <i className="bi bi-check-lg"></i> : (isActive && displayStatus !== 'READY' && displayStatus !== 'VALIDATION_REVIEW' && displayStatus !== 'COMPLIANCE_REVIEW' && displayStatus !== 'NEEDS_REVIEW_VALIDATION' && displayStatus !== 'NEEDS_REVIEW_COMPLIANCE' ? <div className="spinner-border spinner-border-sm"></div> : idx + 1)}
                  </div>
                  <div className={`small text-center ${isActive ? 'fw-bold text-body' : 'text-secondary'}`} style={{ fontSize: '0.7rem' }}>
                    {step.replace(/_/g, ' ')}
                  </div>
                </div>
              )
            })}
          </div>
        </div>

        {(caseData.status === 'VALIDATION_REVIEW' || caseData.status === 'COMPLIANCE_REVIEW' || caseData.status === 'NEEDS_REVIEW_VALIDATION' || caseData.status === 'NEEDS_REVIEW_COMPLIANCE') && (
          <div className="alert alert-danger p-4 p-md-5 rounded-4 text-center shadow-sm">
            <h3 className="text-danger mb-4"><i className="bi bi-exclamation-triangle-fill me-2"></i>Human Review Required</h3>
            
            <div className="bg-body p-4 rounded-3 text-start mb-4 border-start border-4 border-danger shadow-sm">
              <h4 className="text-danger small fw-bold text-uppercase mb-2">AI Agent Remarks:</h4>
              <p className="mb-0 fw-medium text-body" style={{ whiteSpace: 'pre-wrap', lineHeight: '1.6' }}>{caseData.reason}</p>
            </div>
            
            {(caseData.status === 'VALIDATION_REVIEW' || caseData.status === 'NEEDS_REVIEW_VALIDATION') && caseData.extracted_data && (
              <div className="bg-body-tertiary p-4 rounded-3 text-start mb-4 border border-secondary shadow-sm">
                <h4 className="h6 mb-3">Extracted Data (Edit to correct)</h4>
                <div className="row g-3">
                  {['port_of_loading', 'vessel_name', 'gross_weight', 'supplier'].map(field => (
                    <div key={field} className="col-12 col-md-6">
                      <div className="form-floating">
                        <input 
                          type="text" 
                          className="form-control bg-transparent text-body border-secondary" 
                          id={field}
                          value={editData[field] !== undefined ? editData[field] : (caseData.extracted_data[field] || '')}
                          onChange={e => setEditData({ ...editData, [field]: e.target.value })}
                        />
                        <label htmlFor={field} className="text-secondary text-capitalize">{field.replace(/_/g, ' ')}</label>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
            
            <div className="d-flex justify-content-center gap-3 mt-4">
              <button className="btn btn-success px-4 shadow-sm" onClick={() => resolveConflict('APPROVE')} disabled={resolvingAction !== null}>
                {resolvingAction === 'APPROVE' ? <span className="spinner-border spinner-border-sm me-2"></span> : <i className="bi bi-check-circle me-2"></i>} Override & Approve
              </button>
              <button className="btn btn-outline-danger px-4" onClick={() => resolveConflict('REJECT')} disabled={resolvingAction !== null}>
                {resolvingAction === 'REJECT' ? <span className="spinner-border spinner-border-sm me-2"></span> : null} Reject Shipment
              </button>
            </div>
          </div>
        )}

        {caseData.status === 'REJECTED' && (
          <div className="alert alert-danger p-4 p-md-5 rounded-4 text-center shadow-sm">
            <h3 className="text-danger mb-3"><i className="bi bi-x-circle-fill me-2"></i>Shipment Rejected</h3>
            <p className="mb-4">The shipment was rejected due to compliance or validation failures.</p>
            <button className="btn btn-outline-danger px-4" onClick={() => { setActiveCaseId(null); setCaseData(null); setFiles([]); }}>
              Process Another Shipment
            </button>
          </div>
        )}

        {caseData.status === 'READY' && (
          <div className="alert alert-success p-4 p-md-5 rounded-4 text-center shadow-sm border border-success border-opacity-25 bg-success bg-opacity-10">
            <h3 className="text-success mb-4"><i className="bi bi-check-circle-fill me-2"></i>Shipment Cleared!</h3>
            
            <div className="bg-body p-4 rounded-3 text-start mb-4 border-start border-4 border-success shadow-sm">
              <h4 className="text-success small fw-bold text-uppercase mb-2">Generator Agent Final Report:</h4>
              <p className="mb-0 text-body" style={{ whiteSpace: 'pre-wrap', lineHeight: '1.6' }}>
                {caseData.slip?.generator_report || "All compliance checks passed. Documents generated successfully."}
              </p>
            </div>
            
            <div className="d-flex justify-content-center flex-wrap gap-3 mt-4">
              <button className="btn btn-success shadow-sm px-4 fw-medium" onClick={() => downloadPdf('boe')}>
                <i className="bi bi-file-earmark-pdf me-2"></i>Bill of Entry
              </button>
              <button className="btn btn-success shadow-sm px-4 fw-medium" onClick={() => downloadPdf('checklist')}>
                <i className="bi bi-list-check me-2"></i>Checklist
              </button>
              <button className="btn btn-outline-secondary w-100 mt-3" onClick={() => { setActiveCaseId(null); setCaseData(null); setFiles([]); }}>
                Process Another Shipment
              </button>
            </div>
          </div>
        )}
      </div>
    );
  };

  const renderMetrics = () => {
    const pieData = globalStats ? [
      { name: 'Approved', value: globalStats.approved_shipments, color: '#10b981' },
      { name: 'Rejected', value: globalStats.rejected_shipments, color: '#ef4444' },
      { name: 'Pending', value: globalStats.pending_shipments, color: '#f59e0b' }
    ] : [];

    const barData = globalStats ? [
      { name: 'Shipments', Approved: globalStats.approved_shipments, Rejected: globalStats.rejected_shipments, Pending: globalStats.pending_shipments }
    ] : [];

    return (
      <div className="glass-card animate-fade-in container my-4 p-4 p-md-5" style={{ maxWidth: '1320px', width: '100%' }}>
        <h2 className="mb-4 pb-3 border-bottom border-secondary">Platform Dashboard</h2>
        
        {globalStats ? (
          <>
            <div className="row g-4 mb-5">
              <div className="col-12 col-md-4">
                <div className="card h-100 bg-body-tertiary border-secondary text-center p-4 rounded-4 shadow-sm">
                  <h3 className="h6 text-secondary mb-3">Total Shipments</h3>
                  <div className="display-4 fw-bold">{globalStats.total_shipments}</div>
                </div>
              </div>
              <div className="col-12 col-md-4">
                <div className="card h-100 border-success bg-success bg-opacity-10 text-center p-4 rounded-4 shadow-sm">
                  <h3 className="h6 text-success mb-3">Approved</h3>
                  <div className="display-4 fw-bold text-success">{globalStats.approved_shipments}</div>
                </div>
              </div>
              <div className="col-12 col-md-4">
                <div className="card h-100 border-danger bg-danger bg-opacity-10 text-center p-4 rounded-4 shadow-sm">
                  <h3 className="h6 text-danger mb-3">Rejected / Failed</h3>
                  <div className="display-4 fw-bold text-danger">{globalStats.rejected_shipments}</div>
                </div>
              </div>
            </div>

            <div className="row g-4 mb-5">
              <div className="col-12 col-lg-6">
                <div className="card h-100 bg-body-tertiary border-secondary p-4 rounded-4 shadow-sm">
                  <h3 className="h6 mb-4">Processing Distribution</h3>
                  <div style={{ height: '280px' }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie data={pieData} cx="50%" cy="50%" innerRadius={70} outerRadius={95} paddingAngle={5} dataKey="value">
                          {pieData.map((entry, index) => <Cell key={`cell-${index}`} fill={entry.color} />)}
                        </Pie>
                        <Tooltip contentStyle={{ background: theme==='dark'?'#1f2937':'#fff', border: '1px solid var(--bs-border-color)', borderRadius: '8px' }} />
                      </PieChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              </div>
              <div className="col-12 col-lg-6">
                <div className="card h-100 bg-body-tertiary border-secondary p-4 rounded-4 shadow-sm">
                  <h3 className="h6 mb-4">Volume Breakdown</h3>
                  <div style={{ height: '280px' }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={barData}>
                        <XAxis dataKey="name" stroke="#9ca3af" />
                        <YAxis stroke="#9ca3af" />
                        <Tooltip cursor={{ fill: 'var(--bs-secondary-bg)' }} contentStyle={{ background: theme==='dark'?'#1f2937':'#fff', border: '1px solid var(--bs-border-color)', borderRadius: '8px' }} />
                        <Bar dataKey="Approved" fill="#10b981" radius={[4,4,0,0]} />
                        <Bar dataKey="Pending" fill="#f59e0b" radius={[4,4,0,0]} />
                        <Bar dataKey="Rejected" fill="#ef4444" radius={[4,4,0,0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              </div>
            </div>

            <div className="card bg-body-tertiary border-secondary p-4 rounded-4 shadow-sm">
              <h3 className="h6 mb-4">Recent Shipments</h3>
              <div className="table-responsive">
                <table className="table table-hover align-middle bg-transparent text-body">
                  <thead>
                    <tr className="border-secondary text-secondary">
                      <th className="py-3">ID</th>
                      <th className="py-3">Direction</th>
                      <th className="py-3">Date</th>
                      <th className="py-3">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {recentCases.map(c => (
                      <tr key={c.processing_id} className="border-secondary">
                        <td className="py-3 font-monospace small">{c.processing_id.split('-')[0]}</td>
                        <td className="py-3">{c.trade_direction}</td>
                        <td className="py-3">{new Date(c.created_at).toLocaleDateString()}</td>
                        <td className="py-3">
                          <span className={`badge rounded-pill px-3 py-2 ${c.status === 'READY' ? 'bg-success text-white' : c.status === 'REJECTED' ? 'bg-danger text-white' : 'bg-warning text-dark'}`}>
                            {c.status.replace(/_/g, ' ')}
                          </span>
                        </td>
                      </tr>
                    ))}
                    {recentCases.length === 0 && (
                      <tr>
                        <td colSpan={4} className="py-5 text-center text-secondary">No recent shipments found.</td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </>
        ) : (
          <div className="d-flex justify-content-center p-5">
            <div className="spinner-border text-primary" role="status"><span className="visually-hidden">Loading...</span></div>
          </div>
        )}
      </div>
    );
  };

  return (
    <>
      {!authToken ? (
        <AuthScreen showToast={showToast} onLogin={(token, email, role) => {
          localStorage.setItem('token', token);
          localStorage.setItem('userEmail', email);
          localStorage.setItem('userRole', role);
          setAuthToken(token);
          setUserEmail(email);
          setUserRole(role);
          showToast("Logged in successfully");
        }} />
      ) : (
        <div className="container py-4">
      <header className="d-flex flex-wrap justify-content-between align-items-center mb-5 border-bottom border-secondary pb-3 animate-fade-in position-relative" style={{ zIndex: 1050 }}>
        <div className="d-flex align-items-center gap-3">
          
          <div className="position-relative" ref={profileRef}>
            <button
              type="button"
              aria-expanded={isProfileOpen}
              className="btn btn-primary rounded-circle d-flex align-items-center justify-content-center shadow-sm fw-bold"
              style={{ width: '42px', height: '42px' }}
              onClick={(e) => {
                e.stopPropagation();
                setIsProfileOpen(prev => !prev);
              }}
            >
              {userEmail?.[0]?.toUpperCase() || 'A'}
            </button>
            
            {isProfileOpen && (
              <div className="position-absolute top-100 start-0 mt-2 bg-body border border-secondary rounded-4 p-3 shadow-lg" style={{ width: '280px', zIndex: 9999 }}>
                <div className="d-flex justify-content-between align-items-center mb-2">
                  <div className="fw-bold">Account</div>
                  <button type="button" className="btn-close" onClick={() => setIsProfileOpen(false)}></button>
                </div>
                <div className="text-secondary small text-break mb-3">{userEmail || 'admin@kargo.com'}</div>
                <div className="d-grid gap-2">
                  <button type="button" className="btn btn-outline-secondary btn-sm" onClick={() => setIsProfileOpen(false)}>Manage Account</button>
                  <button 
                    className="btn btn-danger btn-sm" 
                    onClick={() => {
                      setIsProfileOpen(false);
                      handleLogout();
                      showToast("Logged out successfully");
                    }}
                  >
                    Logout
                  </button>
                </div>
              </div>
            )}
          </div>
          
          <div className="d-flex align-items-center gap-2 m-0 fs-5 fw-bold text-body">
            <img src={acipLogo} alt="ACIP logo" style={{ height: '44px', width: 'auto', borderRadius: '10px' }} />
            <span className="d-none d-sm-inline">Autonomous Customs Intelligence Platform</span>
          </div>
        </div>
        
        <div className="d-flex gap-2 align-items-center mt-3 mt-md-0">
          <button 
            className="btn btn-outline-secondary border-0"
            onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
            title="Toggle Theme"
          >
            {theme === 'dark' ? <i className="bi bi-sun-fill fs-5"></i> : <i className="bi bi-moon-fill fs-5"></i>}
          </button>
          
          {userRole === 'admin' && (
            <>
              <button 
                className={`btn ${currentView === 'admin' ? 'btn-outline-primary fw-bold' : 'btn-outline-secondary border-0 fw-medium'}`} 
                onClick={() => setCurrentView('admin')}
              >
                Admin Portal
              </button>
              <button 
                className={`btn ${currentView === 'knowledge' ? 'btn-outline-primary fw-bold' : 'btn-outline-secondary border-0 fw-medium'}`} 
                onClick={() => setCurrentView('knowledge')}
              >
                Knowledge Base
              </button>
            </>
          )}
          <button 
            className={`btn ${currentView === 'metrics' ? 'btn-primary shadow-sm fw-semibold' : 'btn-outline-primary fw-semibold'}`}
            onClick={() => setCurrentView(currentView === 'metrics' ? 'process' : 'metrics')}
          >
            {currentView === 'metrics' ? 'Start Processing' : 'Back to Dashboard'}
          </button>
        </div>
      </header>

      <main className="animate-fade-in pb-5">
        {currentView === 'admin' ? <AdminPortal authToken={authToken} /> : (
        currentView === 'knowledge' ? <KnowledgeBase authToken={authToken} /> : (
        currentView === 'metrics' ? renderMetrics() : (
          activeCaseId ? renderDashboard() : (
            <div className="glass-card container p-4 p-md-5 text-center shadow-sm process-page-card" style={{ maxWidth: '1320px', width: '100%' }}>
              <h2 className="mb-3 fw-bold">New Shipment Processing</h2>
              <p className="text-secondary mb-4 px-lg-5">
                Upload shipment documents to extract canonical data, validate cross-consistency, and check regulatory compliance automatically.
              </p>

              <div className="d-flex justify-content-center mb-4 process-action-bar">
                <div className="btn-group shadow-sm" role="group" aria-label="Choose trade direction">
                  <button 
                    type="button" 
                    className={`btn px-4 py-2 fw-semibold ${tradeDirection === 'IMPORT' ? 'btn-primary' : 'btn-outline-secondary'}`}
                    onClick={() => setTradeDirection('IMPORT')}
                  >
                    Import
                  </button>
                  <button 
                    type="button" 
                    className={`btn px-4 py-2 fw-semibold ${tradeDirection === 'EXPORT' ? 'btn-primary' : 'btn-outline-secondary'}`}
                    onClick={() => setTradeDirection('EXPORT')}
                  >
                    Export
                  </button>
                </div>
              </div>

              <div 
                className={`upload-zone mb-4 shadow-sm ${isDragging ? 'drag-active' : ''}`}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                onClick={() => document.getElementById('file-upload')?.click()}
                role="button"
                aria-label="Upload shipment documents"
              >
                <i className="bi bi-cloud-arrow-up-fill upload-icon text-primary"></i>
                <h3 className="h5 fw-bold text-body">Drag & Drop Documents Here</h3>
                <p className="text-secondary small mt-2 mb-1">
                  Support for PDFs, XLSX, CSV, JSON, DOCX, and image files.
                </p>
                <p className="text-secondary small upload-hint mb-0">
                  Click here to choose files from your device.
                </p>
                <input 
                  type="file" 
                  id="file-upload" 
                  multiple 
                  className="d-none" 
                  onChange={handleFileInput}
                />
              </div>

              {files.length > 0 ? (
                <div className="mt-4 text-start file-list-section">
                  <h3 className="h6 mb-3 text-secondary text-uppercase fw-bold">Uploaded Files ({files.length})</h3>
                  <div className="d-flex flex-column gap-3">
                    {files.map((file, idx) => (
                      <div key={idx} className="card file-card shadow-sm">
                        <div className="card-body d-flex justify-content-between align-items-center py-3 px-3">
                          <div className="d-flex align-items-center gap-3">
                            <i className="bi bi-file-earmark-text fs-4 text-primary"></i>
                            <div>
                              <div className="fw-semibold text-dark file-name" title={file.name}>{file.name}</div>
                              <div className="small file-meta">
                                {(file.size / 1024 / 1024).toFixed(2)} MB • {file.type || 'Unknown Type'}
                              </div>
                            </div>
                          </div>
                          <button 
                            type="button"
                            className="btn btn-link text-danger p-0 border-0"
                            onClick={() => removeFile(idx)}
                          >
                            <i className="bi bi-x-lg"></i>
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>

                  <div className="d-flex justify-content-end mt-4">
                    <button 
                      type="button"
                      className="btn btn-primary px-4 py-2 shadow-sm fw-bold"
                      onClick={processShipment}
                      disabled={files.length === 0}
                    >
                      Start Processing Shipment <i className="bi bi-arrow-right ms-2"></i>
                    </button>
                  </div>
                </div>
              ) : (
                <div className="mt-4 text-secondary small empty-upload-note">
                  No files added yet. Add shipment documents to enable processing.
                </div>
              )}
            </div>
        ))))}
      </main>
      </div>
      )}

      {toastMessage && (
        <div className="toast-container-custom">
          <div className="toast-custom">{toastMessage}</div>
        </div>
      )}
    </>
  )
}

export default App
