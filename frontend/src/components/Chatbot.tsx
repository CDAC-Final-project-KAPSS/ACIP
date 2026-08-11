import React, { useState, useRef, useEffect } from 'react';

interface ChatbotProps {
  userRole: string | null;
  authToken: string | null;
}

interface Message {
  role: 'user' | 'bot';
  content: string;
}

const Chatbot: React.FC<ChatbotProps> = ({ userRole, authToken }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([
    { role: 'bot', content: 'Hello! I am your ACIP Customs Assistant. Ask me any questions about customs rules and regulations.' }
  ]);
  const [input, setInput] = useState('');
  const [ingestInput, setIngestInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [isIngesting, setIsIngesting] = useState(false);
  const [showIngest, setShowIngest] = useState(false);
  
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    if (isOpen) {
      scrollToBottom();
    }
  }, [messages, isOpen, showIngest]);

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || !authToken) return;

    const userMessage = input.trim();
    setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
    setInput('');
    setIsTyping(true);

    try {
      const response = await fetch('http://localhost:8000/api/v1/chat/query', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${authToken}`
        },
        body: JSON.stringify({ query: userMessage })
      });

      if (!response.ok) throw new Error('Network response was not ok');
      const data = await response.json();
      
      setMessages(prev => [...prev, { role: 'bot', content: data.reply }]);
    } catch (error) {
      setMessages(prev => [...prev, { role: 'bot', content: 'Sorry, I encountered an error connecting to the intelligence server.' }]);
    } finally {
      setIsTyping(false);
    }
  };

  const handleIngestRule = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!ingestInput.trim() || userRole !== 'admin' || !authToken) return;

    setIsIngesting(true);
    try {
      const response = await fetch('http://localhost:8000/api/v1/chat/ingest', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${authToken}`
        },
        body: JSON.stringify({ rule_text: ingestInput.trim() })
      });

      const data = await response.json();
      
      if (!response.ok) throw new Error(data.detail || 'Failed to add rule');
      
      setMessages(prev => [...prev, { role: 'bot', content: `✅ System Update: ${data.message}` }]);
      setIngestInput('');
      setShowIngest(false);
    } catch (error: any) {
      setMessages(prev => [...prev, { role: 'bot', content: `❌ Ingest Error: ${error.message}` }]);
    } finally {
      setIsIngesting(false);
    }
  };

  return (
    <div style={{ position: 'fixed', bottom: '20px', right: '20px', zIndex: 9999 }}>
      {/* Floating Action Button */}
      {!isOpen && (
        <button
          onClick={() => setIsOpen(true)}
          className="btn btn-primary rounded-circle shadow-lg d-flex align-items-center justify-content-center"
          style={{ width: '60px', height: '60px' }}
        >
          <i className="bi bi-chat-dots-fill" style={{ fontSize: '24px' }}></i>
        </button>
      )}

      {/* Chat Window */}
      {isOpen && (
        <div className="card shadow-lg border-0" style={{ width: '380px', height: '550px', display: 'flex', flexDirection: 'column', borderRadius: '15px', overflow: 'hidden' }}>
          
          {/* Header */}
          <div className="bg-primary text-white p-3 d-flex justify-content-between align-items-center">
            <div className="d-flex align-items-center gap-2">
              <i className="bi bi-chat-dots-fill"></i>
              <h6 className="mb-0 fw-bold">ACIP Assistant</h6>
            </div>
            <div className="d-flex gap-2">
              {userRole === 'admin' && (
                <button 
                  onClick={() => setShowIngest(!showIngest)}
                  className="btn btn-sm btn-outline-light border-0 p-1"
                  title="Add to Knowledge Base"
                >
                  <i className="bi bi-database-fill-add" style={{ fontSize: '18px' }}></i>
                </button>
              )}
              <button 
                onClick={() => setIsOpen(false)}
                className="btn btn-sm btn-outline-light border-0 p-1"
              >
                <i className="bi bi-x-lg" style={{ fontSize: '18px' }}></i>
              </button>
            </div>
          </div>

          {/* Admin Ingest Area */}
          {showIngest && userRole === 'admin' && (
            <div className="bg-light p-3 border-bottom">
              <p className="small text-muted mb-2"><strong>Admin Tools:</strong> Add a new text rule to the knowledge base.</p>
              <form onSubmit={handleIngestRule}>
                <textarea 
                  className="form-control text-white bg-dark border-secondary mb-2" 
                  rows={3}
                  placeholder="Paste new regulation text here..."
                  value={ingestInput}
                  onChange={(e) => setIngestInput(e.target.value)}
                  style={{ fontSize: '0.85rem' }}
                />
                <button 
                  type="submit" 
                  className="btn btn-warning btn-sm w-100 fw-bold"
                  disabled={isIngesting || !ingestInput.trim()}
                >
                  {isIngesting ? <><i className="bi bi-arrow-repeat spin me-2"></i> Ingesting...</> : 'Inject into ChromaDB'}
                </button>
              </form>
            </div>
          )}

          {/* Messages Area */}
          <div className="flex-grow-1 p-3 bg-dark" style={{ overflowY: 'auto' }}>
            {messages.map((msg, idx) => (
              <div key={idx} className={`d-flex mb-3 ${msg.role === 'user' ? 'justify-content-end' : 'justify-content-start'}`}>
                <div 
                  className={`p-2 px-3 rounded-3 shadow-sm ${msg.role === 'user' ? 'bg-primary text-white' : 'bg-secondary text-light'}`}
                  style={{ maxWidth: '85%', fontSize: '0.9rem', whiteSpace: 'pre-wrap' }}
                >
                  {msg.content}
                </div>
              </div>
            ))}
            {isTyping && (
              <div className="d-flex justify-content-start mb-3">
                <div className="bg-secondary text-light p-2 px-3 rounded-3 shadow-sm" style={{ fontSize: '0.9rem' }}>
                  <i className="bi bi-arrow-repeat spin"></i> Thinking...
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input Area */}
          <div className="bg-dark p-2 border-top border-secondary">
            <form onSubmit={handleSendMessage} className="d-flex gap-2">
              <input
                type="text"
                className="form-control bg-dark text-white border-secondary rounded-pill"
                placeholder="Ask about customs rules..."
                value={input}
                onChange={(e) => setInput(e.target.value)}
              />
              <button 
                type="submit" 
                className="btn btn-primary rounded-circle d-flex align-items-center justify-content-center p-0"
                style={{ width: '40px', height: '40px', minWidth: '40px' }}
                disabled={isTyping || !input.trim()}
              >
                <i className="bi bi-send-fill"></i>
              </button>
            </form>
          </div>

        </div>
      )}
      <style>{`
        .spin { animation: spin 1s linear infinite; }
        @keyframes spin { 100% { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
};

export default Chatbot;
