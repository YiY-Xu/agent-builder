import React, { useState, useEffect } from 'react';
import { X, RefreshCw, Check, Server, Plus } from 'lucide-react';
import '../styles/components.css';

/**
 * Component for selecting MCP servers
 */
const MCPServerSelection = ({ mcpServers, selectedServers, onSelectServers, onCancel }) => {
  const [selection, setSelection] = useState([...selectedServers]);
  const [loading, setLoading] = useState(false);
  
  // Handle server selection
  const toggleServerSelection = (serverName) => {
    setSelection(prev => {
      if (prev.includes(serverName)) {
        return prev.filter(name => name !== serverName);
      } else {
        return [...prev, serverName];
      }
    });
  };
  
  // Handle confirmation of selection
  const handleConfirm = () => {
    onSelectServers(selection);
  };
  
  // Handle cancellation
  const handleCancel = () => {
    onCancel();
  };
  
  // Format server name if needed
  const formatServerName = (name) => {
    if (name.length <= 30) return name;
    return `${name.substring(0, 27)}...`;
  };
  
  // Refresh server list
  const refreshServerList = async () => {
    setLoading(true);
    try {
      // Simulate API call - in a real app, you'd call your API here
      await new Promise(resolve => setTimeout(resolve, 500));
      // You would update mcpServers here with the response
    } catch (error) {
      console.error("Error refreshing server list:", error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="knowledge-upload-container">
      <div className="knowledge-upload-header">
        <h3>Select MCP Servers</h3>
        <button 
          className="close-button"
          onClick={handleCancel}
          disabled={loading}
        >
          <X size={18} />
        </button>
      </div>
      
      <div className="selected-files-container">
        <div className="selected-files-header">
          <h4>Available Servers ({mcpServers.length})</h4>
          <button 
            className="refresh-button"
            onClick={refreshServerList}
            disabled={loading}
          >
            <RefreshCw size={16} />
          </button>
        </div>
        
        {mcpServers && mcpServers.length > 0 ? (
          <div className="knowledge-info">
            {mcpServers.map((server, index) => (
              <div key={index} className="mcp-server-item">
                <input
                  type="checkbox"
                  id={`server-${index}`}
                  checked={selection.includes(server.name)}
                  onChange={() => toggleServerSelection(server.name)}
                />
                <label htmlFor={`server-${index}`} style={{ marginLeft: '8px' }}>{formatServerName(server.name)}</label>
              </div>
            ))}
          </div>
        ) : (
          <div className="knowledge-empty">
            <p>No MCP servers available</p>
          </div>
        )}
      </div>
      
      <div className="knowledge-buttons">
        <button 
          className="cancel-button"
          onClick={handleCancel}
          disabled={loading}
        >
          Cancel
        </button>
        
        <button 
          className="create-index-button"
          onClick={handleConfirm}
          disabled={loading}
        >
          <Check size={16} />
          Select Servers
        </button>
      </div>
    </div>
  );
};

export default MCPServerSelection;