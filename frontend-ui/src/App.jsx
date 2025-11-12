import React, { useState, useEffect, useRef } from 'react';
import './App.css';

const API_URL = 'http://127.0.0.1:8000';

function App() {
  const [history, setHistory] = useState([]);
  const [input, setInput] = useState('');
  const [sessionId, setSessionId] = useState(null);
  const [requiresApproval, setRequiresApproval] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isTyping, setIsTyping] = useState(false);

  const historyEndRef = useRef(null);

  useEffect(() => {
    historyEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [history]);

  const callApi = async (endpoint, payload) => {
    const response = await fetch(`${API_URL}${endpoint}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      throw new Error(`Error HTTP: ${response.status}`);
    }

    return response.json();
  };

  const handleSend = async (e) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage = { type: 'human', content: input };
    setHistory(prev => [...prev, userMessage]);
    setIsLoading(true);
    setIsTyping(true);
    setInput('');

    try {
      const payload = { message: input, session_id: sessionId };
      const data = await callApi('/chat', payload);
      
      setHistory(data.full_history);
      setSessionId(data.session_id);
      setRequiresApproval(data.requires_approval);


    } catch (error) {
      console.error("Error al comunicarse con la API:", error);
      setHistory(prev => [...prev, { 
        type: 'error', 
        content: `Error de conexión: ${error.message}` 
      }]);
    } finally {
      setIsLoading(false);
      setIsTyping(false);
    }
  };

  const handleApproval = async (approved) => {
    setIsLoading(true);
    setRequiresApproval(false);

    try {
      const payload = { session_id: sessionId, approved: approved };
      const data = await callApi('/approve', payload);
      
      setHistory(prev => [...prev, { type: 'ai', content: data.response }]);


    } catch (error) {
      console.error("Error al enviar la aprobación:", error);
      setHistory(prev => [...prev, { 
        type: 'error', 
        content: `Error en aprobación: ${error.message}` 
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const renderMessage = (msg, index) => {
    const isHuman = msg.type === 'human';
    const isError = msg.type === 'error';
    
    return (
      <div key={index} className={`message ${isHuman ? 'human' : isError ? 'error' : 'ai'}`}>
        <div className="message-avatar">
          {isHuman ? '👤' : isError ? '⚠️' : '🤖'}
        </div>
        <div className="message-content">
          <div className="message-sender">
            {isHuman ? 'Tú' : isError ? 'Error del sistema' : 'Asistente de Viajes'}
          </div>
          <div className="message-text">
            {msg.content.split('\n').map((line, i) => (
              <p key={i}>{line}</p>
            ))}
          </div>
          <div className="message-time">
            {new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="app">
      <header className="app-header">
        <div className="header-content">
          <div className="header-title">
            <h1>✈️ Asistente de Viajes IA</h1>
            <p>Planifica tu próximo viaje con inteligencia artificial</p>
          </div>
          <div className="session-info">
            <span className="session-badge">
              {sessionId ? `Sesión: ${sessionId.slice(0, 8)}...` : 'Nueva sesión'}
            </span>
          </div>
        </div>
      </header>

      <main className="chat-container">
        <div className="chat-window">
          {history.length === 0 ? (
            <div className="welcome-message">
              <div className="welcome-icon">🌍</div>
              <h2>¡Hola! Soy tu asistente de viajes</h2>
              <p>Puedo ayudarte con:</p>
              <ul>
                <li>🌤️ Información del clima en cualquier ciudad</li>
                <li>🎯 Actividades culturales, de aventura, gastronómicas...</li>
                <li>🗺️ Lugares de interés</li>
              </ul>
              <p className="welcome-example">
                <strong>Ejemplo:</strong> "¿Qué tiempo hace en Madrid?"
              </p>
            </div>
          ) : (
            history.map(renderMessage)
          )}
          
          {isTyping && (
            <div className="message ai typing">
              <div className="message-avatar">🤖</div>
              <div className="message-content">
                <div className="typing-indicator">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
              </div>
            </div>
          )}
          
          <div ref={historyEndRef} />
        </div>

        {requiresApproval && (
          <div className="approval-overlay">
            <div className="approval-modal">
              <div className="approval-header">
                <span className="approval-icon">🛑</span>
                <h3>Intervención Requerida</h3>
              </div>
              <p>¿Apruebas la propuesta final del asistente?</p>
              <div className="approval-actions">
                <button 
                  className="btn-approve"
                  onClick={() => handleApproval(true)}
                  disabled={isLoading}
                >
                  ✅ Aprobar Propuesta
                </button>
                <button 
                  className="btn-reject"
                  onClick={() => handleApproval(false)}
                  disabled={isLoading}
                >
                  ❌ Rechazar
                </button>
              </div>
            </div>
          </div>
        )}
      </main>

      <footer className="input-section">
        <form onSubmit={handleSend} className="input-form">
          <div className="input-container">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Pregunta sobre clima, actividades, presupuestos..."
              disabled={isLoading || requiresApproval}
              className="message-input"
            />
            <button 
              type="submit" 
              disabled={isLoading || requiresApproval || !input.trim()}
              className="send-button"
            >
              {isLoading ? (
                <div className="spinner"></div>
              ) : (
                <span>➤</span>
              )}
            </button>
          </div>
          <div className="input-hint">
            💡 Presiona Enter para enviar • Ej: "actividades cultura Barcelona"
          </div>
        </form>
      </footer>
    </div>
  );
}

export default App;
