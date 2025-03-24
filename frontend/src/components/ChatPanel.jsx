import React from 'react';
import { Send } from 'lucide-react';
import { useAgent } from '../context/AgentContext';
import useChat from '../hooks/useChat';
import ChatMessage from './ChatMessage';
import LoadingIndicator from './LoadingIndicator';
import '../styles/components.css';

/**
 * Component for the left panel with chat interface
 */
const ChatPanel = () => {
  const { messages } = useAgent();
  const {
    inputMessage,
    setInputMessage,
    handleSendMessage,
    handleKeyPress,
    isLoading,
    error,
    messagesEndRef
  } = useChat();

  return (
    <div className="chat-panel">
      <div className="chat-header">
        <h2>Agent Builder Chat</h2>
      </div>
      
      <div className="messages-container">
        {/* Chat messages */}
        {messages.map((message, index) => (
          <ChatMessage key={index} message={message} />
        ))}
        
        {/* Loading indicator */}
        {isLoading && <LoadingIndicator />}
        
        {/* Error message if any */}
        {error && (
          <div className="error-message">
            {error}
          </div>
        )}
        
        {/* Scroll anchor */}
        <div ref={messagesEndRef} />
      </div>
      
      <div className="chat-input-container">
        <textarea
          className="chat-input"
          placeholder="Type your message..."
          value={inputMessage}
          onChange={(e) => setInputMessage(e.target.value)}
          onKeyDown={handleKeyPress}
          disabled={isLoading}
          rows={1}
        />
        
        <button 
          className={`send-button ${!inputMessage.trim() || isLoading ? 'disabled' : ''}`}
          onClick={handleSendMessage}
          disabled={!inputMessage.trim() || isLoading}
        >
          <Send size={20} />
        </button>
      </div>
    </div>
  );
};

export default ChatPanel;