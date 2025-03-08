import React from 'react';
import '../styles/components.css';

/**
 * Component for rendering a single chat message with image support
 */
const ChatMessage = ({ message }) => {
  const isUser = message.role === 'user';
  
  // Function to format message content with markdown-like syntax and image detection
  const formatContent = (content) => {
    if (!content) return '';
    
    // First, replace markdown image syntax with just the URL
    let processedContent = content.replace(/!\[(.*?)\]\((https?:\/\/\S+)\)/g, '$2');
    
    // Replace image URLs with image tags
    // This regex matches common image URLs and standalone URLs that likely point to images
    const imageUrlRegex = /(https?:\/\/\S+\.(jpg|jpeg|png|gif|bmp|webp)(\?\S*)?)|(\bhttps?:\/\/cataas\.com\/cat\S*)/gi;
    
    // Process each match individually to ensure URLs are correct
    let formattedContent = processedContent.replace(imageUrlRegex, (match) => {
      // Clean up URL by removing any closing parentheses or formatting artifacts
      let cleanUrl = match.replace(/\)$/, '');
      
      // Fix cataas.com URL if it's not working
      if (cleanUrl.includes('cataas.com/cat') && !cleanUrl.includes('cataas.com/cat/')) {
        cleanUrl = 'https://cataas.com/cat';
      }
      
      return `<div class="message-image-container"><img src="${cleanUrl}" alt="Image" class="message-image" onerror="this.onerror=null; this.src='https://cataas.com/cat'; this.alt='Cat Image';" /></div>`;
    });
    
    // Convert codeblocks
    formattedContent = formattedContent
      .replace(/```(.*?)\n([\s\S]*?)```/g, (match, language, code) => {
        return `<pre class="code-block"><code class="language-${language || 'text'}">${code}</code></pre>`;
      })
      // Convert bold text
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      // Convert italics
      .replace(/\*(.*?)\*/g, '<em>$1</em>')
      // Convert lists
      .replace(/^\s*-\s+(.*)/gm, '<li>$1</li>')
      // Convert line breaks
      .replace(/\n/g, '<br />');
    
    return formattedContent;
  };

  return (
    <div className={`message-container ${isUser ? 'user-message' : 'bot-message'}`}>
      <div className="message-avatar">
        {isUser ? (
          <div className="user-avatar">U</div>
        ) : (
          <div className="bot-avatar">A</div>
        )}
      </div>
      
      <div className="message-content">
        <div className="message-sender">
          {isUser ? 'You' : 'Assistant'}
        </div>
        
        <div 
          className="message-text"
          dangerouslySetInnerHTML={{ __html: formatContent(message.content) }}
        />
      </div>
    </div>
  );
};

export default ChatMessage;