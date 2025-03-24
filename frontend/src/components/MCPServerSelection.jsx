import React, { useState, useEffect } from 'react';
import { X, RefreshCw, Check, Server, Plus } from 'lucide-react';
import '../styles/components.css';

/**
 * Component for selecting MCP servers
 */
const MCPServerSelection = ({ mcpServers, selectedServers, onSelectServers, onCancel }) => {
  const [selection, setSelection] = useState([...selectedServers]);
  const [loading, setLoading] = useState(false);
  const [showAddModal, setShowAddModal] = useState(false);
  const [newServer, setNewServer] = useState({ name: '', sse_url: '' });
  const [addingServer, setAddingServer] = useState(false);
  const [error, setError] = useState(null);
  
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
  
  // Handle adding a new server
  const handleAddServer = async () => {
    if (!newServer.name || !newServer.sse_url) {
      setError('Both Server Name and SSE URL are required');
      return;
    }
    
    try {
      setAddingServer(true);
      setError(null);
      
      // Call the backend API to add a new server
      const response = await fetch('http://localhost:8000/api/mcp-servers/add', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        },
        body: JSON.stringify(newServer)
      });
      
      if (response.ok) {
        // Close modal and reset form
        setShowAddModal(false);
        setNewServer({ name: '', sse_url: '' });
        
        // Refresh the server list
        // In a real implementation, you might want to update the mcpServers list
        // by receiving the updated list from the parent component or refetching it
        window.location.reload(); // Simple solution for demo
      } else {
        const error = await response.text();
        setError(`Failed to add server: ${error}`);
      }
    } catch (err) {
      setError(`Error: ${err.message}`);
    } finally {
      setAddingServer(false);
    }
  };
  
  // Handle input change for new server form
  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setNewServer(prev => ({
      ...prev,
      [name]: value
    }));
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
            className="add-server-button"
            onClick={() => setShowAddModal(true)}
            disabled={loading}
          >
            <Plus size={16} />
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
      
      {/* Add Server Modal */}
      {showAddModal && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div className="modal-header">
              <h3>Add MCP Server</h3>
              <button 
                className="close-button"
                onClick={() => setShowAddModal(false)}
              >
                <X size={18} />
              </button>
            </div>
            
            <div className="modal-body">
              <div className="form-group">
                <label htmlFor="server-name">Server Name</label>
                <input
                  type="text"
                  id="server-name"
                  name="name"
                  value={newServer.name}
                  onChange={handleInputChange}
                  placeholder="e.g., Weather Forecast Service"
                  className="form-input"
                />
              </div>
              
              <div className="form-group">
                <label htmlFor="server-url">SSE URL</label>
                <input
                  type="text"
                  id="server-url"
                  name="sse_url"
                  value={newServer.sse_url}
                  onChange={handleInputChange}
                  placeholder="e.g., http://localhost:5003/api/events"
                  className="form-input"
                />
              </div>
              
              {error && (
                <div className="error-message">
                  {error}
                </div>
              )}
            </div>
            
            <div className="modal-footer">
              <button 
                className="cancel-button"
                onClick={() => setShowAddModal(false)}
                disabled={addingServer}
              >
                Cancel
              </button>
              
              <button 
                className="create-index-button"
                onClick={handleAddServer}
                disabled={addingServer}
              >
                {addingServer ? 'Adding...' : 'Add Server'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default MCPServerSelection;