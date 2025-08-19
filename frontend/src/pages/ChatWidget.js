
import React, { useState, useRef, useEffect } from 'react';
import './ChatWidget.css';

const ChatWidget = () => {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState([
    { text: "Hi! I'm your BiGuard AI assistant. I can help you with:\n\n• **Transaction categorization**\n• **Budget tracking**\n• **Spending analysis**\n• **Fraud detection**\n• **Financial advice**\n\nAsk me anything about your finances!", sender: "bot" }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    if (open && messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, open]);

  // Simple markdown-like formatting
  const formatMessage = (text) => {
    if (!text) return '';
    
    // Convert markdown-style formatting to HTML
    let formatted = text
      // Bold text
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      // Italic text
      .replace(/\*(.*?)\*/g, '<em>$1</em>')
      // Bullet points
      .replace(/^•\s/gm, '• ')
      // Line breaks
      .replace(/\n/g, '<br />');
    
    return formatted;
  };

  const sendMessage = async () => {
    if (!input.trim()) return;
    
    const userMessage = input.trim();
    setMessages(msgs => [...msgs, { text: userMessage, sender: "user" }]);
    setInput('');
    setLoading(true);
    
    try {
      // Get user ID from localStorage or try to get it from the current session
      let user_id = localStorage.getItem('user_id');
      
      // If no user_id in localStorage, try to get it from the current session
      if (!user_id) {
        const token = localStorage.getItem('access_token');
        if (token) {
          try {
            const userResponse = await fetch('/api/auth/me', {
              headers: { 'Authorization': `Bearer ${token}` }
            });
            if (userResponse.ok) {
              const userData = await userResponse.json();
              user_id = userData.user?.id || userData.user_id || userData.id;
              if (user_id) {
                localStorage.setItem('user_id', user_id);
              }
            }
          } catch (err) {
            console.log('Could not get user ID from session:', err);
          }
        }
      }
      
      if (!user_id) {
        setMessages(msgs => [...msgs, { text: "Please log in to use the chatbot with personalized assistance.", sender: "bot" }]);
        setLoading(false);
        return;
      }
      
      const res = await fetch('/api/chatbot', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: userMessage, user_id })
      });
      
      if (!res.ok) {
        throw new Error(`HTTP error! status: ${res.status}`);
      }
      
      const data = await res.json();
      setMessages(msgs => [...msgs, { text: data.reply || "Sorry, I couldn't process that.", sender: "bot" }]);
    } catch (err) {
      console.error('Chatbot error:', err);
      setMessages(msgs => [...msgs, { text: "I'm having trouble connecting right now. Please try again in a moment.", sender: "bot" }]);
    }
    setLoading(false);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  // Theme colors from your design
  const accentColor = '#FF6A00';
  const bgColor = '#fff';
  const textColor = '#333333';

  return (
    <>
      <div
        className="chatbot-toggle"
        style={{ backgroundColor: accentColor, color: bgColor }}
        onClick={() => setOpen(o => !o)}
        title="Chat with BiGuard AI"
      >
        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke={bgColor} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="12" cy="12" r="10"/>
          <path d="M8 15h8M9 9h.01M15 9h.01"/>
        </svg>
      </div>
      {open && (
        <div className="chatbot-window" style={{ border: `2px solid ${accentColor}` }}>
          <div className="chatbot-header" style={{ backgroundColor: accentColor, color: bgColor, padding: '12px 16px', fontWeight: 'bold', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span>🤖 BiGuard AI Assistant</span>
            <button 
              onClick={() => setOpen(false)}
              style={{ background: 'none', border: 'none', color: bgColor, cursor: 'pointer', fontSize: '18px' }}
            >
              ×
            </button>
          </div>
          <div className="chatbot-messages" style={{ height: '400px', overflowY: 'auto', padding: '16px' }}>
            {messages.map((msg, i) => (
              <div
                key={i}
                className={`msg ${msg.sender}`}
                style={{
                  backgroundColor: msg.sender === 'bot' ? '#f8f9fa' : accentColor,
                  color: msg.sender === 'bot' ? textColor : bgColor,
                  padding: '12px 16px',
                  borderRadius: '12px',
                  marginBottom: '12px',
                  maxWidth: '85%',
                  alignSelf: msg.sender === 'bot' ? 'flex-start' : 'flex-end',
                  marginLeft: msg.sender === 'bot' ? 0 : 'auto',
                  marginRight: msg.sender === 'bot' ? 'auto' : 0,
                  boxShadow: msg.sender === 'bot' ? '0 2px 4px rgba(0,0,0,0.1)' : '0 2px 4px rgba(255,106,0,0.2)',
                  lineHeight: '1.5'
                }}
                dangerouslySetInnerHTML={{ __html: formatMessage(msg.text) }}
              />
            ))}
            {loading && (
              <div
                className="msg bot"
                style={{
                  backgroundColor: '#f8f9fa',
                  color: textColor,
                  padding: '12px 16px',
                  borderRadius: '12px',
                  marginBottom: '12px',
                  maxWidth: '85%',
                  alignSelf: 'flex-start',
                  marginLeft: 0,
                  marginRight: 'auto',
                  boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px'
                }}
              >
                <div className="typing-indicator">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
                Thinking...
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
          <div className="chatbot-input" style={{ borderTop: `1px solid ${accentColor}`, padding: '16px', display: 'flex', gap: '8px' }}>
            <input
              type="text"
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask me about your finances..."
              disabled={loading}
              style={{ 
                flex: 1,
                padding: '12px 16px',
                border: `1px solid ${accentColor}`,
                borderRadius: '8px',
                color: textColor,
                fontSize: '14px',
                outline: 'none'
              }}
            />
            <button
              onClick={sendMessage}
              disabled={loading || !input.trim()}
              style={{ 
                backgroundColor: accentColor, 
                color: bgColor, 
                border: 'none', 
                borderRadius: '8px', 
                padding: '12px 20px', 
                fontWeight: 'bold',
                cursor: loading || !input.trim() ? 'not-allowed' : 'pointer',
                opacity: loading || !input.trim() ? 0.6 : 1,
                transition: 'opacity 0.2s'
              }}
            >
              {loading ? '...' : 'Send'}
            </button>
          </div>
        </div>
      )}
      <style jsx>{`
        .typing-indicator {
          display: flex;
          gap: 4px;
        }
        
        .typing-indicator span {
          width: 8px;
          height: 8px;
          border-radius: 50%;
          background-color: #ccc;
          animation: typing 1.4s infinite ease-in-out;
        }
        
        .typing-indicator span:nth-child(1) {
          animation-delay: -0.32s;
        }
        
        .typing-indicator span:nth-child(2) {
          animation-delay: -0.16s;
        }
        
        @keyframes typing {
          0%, 80%, 100% {
            transform: scale(0.8);
            opacity: 0.5;
          }
          40% {
            transform: scale(1);
            opacity: 1;
          }
        }
      `}</style>
    </>
  );
};

export default ChatWidget;
