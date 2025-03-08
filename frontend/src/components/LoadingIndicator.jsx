import React from 'react';
import '../styles/components.css';

/**
 * Component for showing a loading/typing animation
 */
const LoadingIndicator = () => {
  return (
    <div className="message-container bot-message">
      <div className="message-avatar">
        <div className="bot-avatar">A</div>
      </div>
      
      <div className="message-content">
        <div className="message-sender">
          Assistant
        </div>
        
        <div className="typing-indicator">
          <span></span>
          <span></span>
          <span></span>
        </div>
      </div>
    </div>
  );
};

export default LoadingIndicator;