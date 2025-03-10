import React, { useState, useRef, useEffect } from 'react';
import { Send, Upload, ArrowLeft, Database, Edit, Save, X, Terminal, RefreshCw } from 'lucide-react';
import { Link } from 'react-router-dom';
import ChatMessage from './ChatMessage';
import LoadingIndicator from './LoadingIndicator';
import { testAgentChat, generateYaml, fetchLogs } from '../services/api';
import yaml from 'js-yaml';
import '../styles/components.css';

/**
 * Component for testing an agent by loading a YAML configuration
 */
const TestAgent = () => {
  // State
  const [agentConfig, setAgentConfig] = useState(null);
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [yamlFile, setYamlFile] = useState(null);
  const [hasKnowledgeBase, setHasKnowledgeBase] = useState(false);
  const [knowledgeBaseType, setKnowledgeBaseType] = useState(null);
  const [isEditMode, setIsEditMode] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [activeTab, setActiveTab] = useState('info'); // 'info' or 'logs'
  const [logs, setLogs] = useState([]);
  const [isPolling, setIsPolling] = useState(false);
  const [isLoadingLogs, setIsLoadingLogs] = useState(false);
  
  // References
  const messagesEndRef = useRef(null);
  const fileInputRef = useRef(null);
  const logsContainerRef = useRef(null);
  const pollIntervalRef = useRef(null);
  
  // Auto-scroll chat to bottom
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);
  
  // Auto-scroll logs to bottom unless user has scrolled up
  useEffect(() => {
    if (logsContainerRef.current) {
      const element = logsContainerRef.current;
      const isScrolledToBottom = element.scrollHeight - element.clientHeight <= element.scrollTop + 50;
      
      if (isScrolledToBottom) {
        element.scrollTop = element.scrollHeight;
      }
    }
  }, [logs]);
  
  // Load logs when tab changes
  useEffect(() => {
    let isMounted = true;
    
    const loadLogs = async () => {
      if (activeTab !== 'logs') return;
      
      setIsLoadingLogs(true);
      try {
        const response = await fetchLogs();
        if (isMounted && response && response.logs) {
          setLogs(response.logs);
        }
      } catch (error) {
        console.error('Error loading logs:', error);
      } finally {
        if (isMounted) {
          setIsLoadingLogs(false);
        }
      }
    };
    
    loadLogs();
    
    // Start polling when on logs tab
    if (activeTab === 'logs') {
      // Initial load
      loadLogs();
      
      // Set up polling
      setIsPolling(true);
      pollIntervalRef.current = setInterval(loadLogs, 1000);
    } else {
      // Stop polling when not on logs tab
      setIsPolling(false);
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = null;
      }
    }
    
    // Cleanup
    return () => {
      isMounted = false;
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = null;
      }
    };
  }, [activeTab]);
  
  // Handle file upload
  const handleFileUpload = (event) => {
    const file = event.target.files[0];
    if (file) {
      setYamlFile(file);
      
      const reader = new FileReader();
      reader.onload = (e) => {
        try {
          const yamlContent = e.target.result;
          const parsedConfig = yaml.load(yamlContent);
          
          // Check if knowledge base exists
          const hasKnowledge = parsedConfig.knowledge_base && 
                             (parsedConfig.knowledge_base.index_name || 
                              parsedConfig.knowledge_base.local_path);
                              
          const knowledgeType = hasKnowledge ? 
                              (parsedConfig.knowledge_base.storage_type || 
                               (parsedConfig.knowledge_base.index_name ? 'llamacloud' : 'local')) : 
                              null;
          
          setAgentConfig(parsedConfig);
          setHasKnowledgeBase(hasKnowledge);
          setKnowledgeBaseType(knowledgeType);
          
          // Welcome message from the agent
          setMessages([{
            role: 'assistant',
            content: `Hello! I am ${parsedConfig.name || 'your agent'}. ${parsedConfig.description || 'How can I help you today?'}${hasKnowledge ? "\n\nI have access to a knowledge base that I can use to answer your questions." : ""}`
          }]);
          
          setError(null);
        } catch (err) {
          console.error('Error parsing YAML:', err);
          setError('Invalid YAML file. Please upload a valid agent configuration.');
        }
      };
      
      reader.onerror = () => {
        setError('Error reading file. Please try again.');
      };
      
      reader.readAsText(file);
    }
  };
  
  // Handle sending a message
  const handleSendMessage = async () => {
    if (!inputMessage.trim() || isLoading || !agentConfig) return;
    
    try {
      // Add user message to chat
      const userMessage = { role: 'user', content: inputMessage };
      setMessages(prev => [...prev, userMessage]);
      
      // Clear input
      setInputMessage('');
      
      // Set loading state
      setIsLoading(true);
      setError(null);
      
      // Send message to API
      const response = await testAgentChat({
        message: inputMessage,
        agent_config: agentConfig,
        history: messages
      });
      
      // Add bot response
      setMessages(prev => [...prev, { 
        role: 'assistant', 
        content: response.message 
      }]);
    } catch (err) {
      console.error('Error in chat:', err);
      setError(`Error communicating with the agent: ${err.message}`);
      
      // Add error message to chat
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `Sorry, I encountered an error: ${err.message}. Please try again.`
      }]);
    } finally {
      setIsLoading(false);
    }
  };
  
  // Handle Enter key press
  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };
  
  // Trigger file input click
  const triggerFileUpload = () => {
    fileInputRef.current?.click();
  };

  // Toggle edit mode
  const toggleEditMode = () => {
    if (isEditMode) {
      // Cancel edit mode, revert changes
      setIsEditMode(false);
    } else {
      setIsEditMode(true);
    }
  };

  // Save configuration changes
  // Save configuration changes
  // Save configuration changes
  // Save configuration changes
  const saveConfigChanges = async () => {
    try {
      setIsSaving(true);
      setError(null);

      // Generate new YAML
      const yamlContent = await generateYaml(agentConfig);
      
      // Create a new file object with the updated YAML
      const newYamlFile = new File(
        [yamlContent], 
        yamlFile ? yamlFile.name : 'agent-config.yaml', 
        { type: 'text/yaml' }
      );
      
      setYamlFile(newYamlFile);
      
      // Clear previous messages - this is important!
      setMessages([]);
      
      // Reset the chat with a welcome message to reinitialize the context
      setTimeout(() => {
        setMessages([{
          role: 'assistant',
          content: `Hello! I am ${agentConfig.name || 'your agent'}. ${agentConfig.description || 'How can I help you today?'}${hasKnowledgeBase ? "\n\nI have access to a knowledge base that I can use to answer your questions." : ""}`
        }, {
          role: 'assistant',
          content: 'Agent configuration updated successfully.'
        }]);
      }, 100);
      
      // Exit edit mode
      setIsEditMode(false);
    } catch (err) {
      console.error('Error saving configuration:', err);
      setError(`Error saving configuration: ${err.message}`);
    } finally {
      setIsSaving(false);
    }
  };

  // Update a field in the agent config
  const updateConfigField = (field, value) => {
    if (!isEditMode) return;
    
    setAgentConfig(prev => {
      // Handle nested fields
      if (field.includes('.')) {
        const [parent, child] = field.split('.');
        return {
          ...prev,
          [parent]: {
            ...prev[parent],
            [child]: value
          }
        };
      }
      
      // Handle top-level fields
      return {
        ...prev,
        [field]: value
      };
    });
  };

  // Render agent information tab content
  const renderAgentInfoTab = () => (
    <div className="config-fields">
      {/* Agent Name */}
      <div className="config-field">
        <label className="field-label">Agent Name</label>
        {isEditMode ? (
          <input 
            type="text" 
            className="field-input"
            value={agentConfig.name || ""}
            onChange={(e) => updateConfigField('name', e.target.value)}
            placeholder="Enter agent name"
          />
        ) : (
          <div className="field-content">
            {agentConfig.name || "Unnamed Agent"}
          </div>
        )}
      </div>
      
      {/* Agent Description */}
      <div className="config-field">
        <label className="field-label">Agent Description</label>
        {isEditMode ? (
          <textarea 
            className="field-textarea"
            value={agentConfig.description || ""}
            onChange={(e) => updateConfigField('description', e.target.value)}
            placeholder="Enter agent description"
            rows={2}
          />
        ) : (
          <div className="field-content">
            {agentConfig.description || "No description provided"}
          </div>
        )}
      </div>
      
      {/* Agent Instruction */}
      <div className="config-field">
        <label className="field-label">Agent Instruction</label>
        {isEditMode ? (
          <textarea 
            className="field-textarea instruction-textarea"
            value={agentConfig.instruction || ""}
            onChange={(e) => updateConfigField('instruction', e.target.value)}
            placeholder="Enter agent instruction"
            rows={5}
          />
        ) : (
          <div className="field-content instruction-field">
            {agentConfig.instruction || "No instructions provided"}
          </div>
        )}
      </div>
      
      {/* Agent Memory Size */}
      <div className="config-field">
        <label className="field-label">Memory Size</label>
        {isEditMode ? (
          <input 
            type="number" 
            className="field-input memory-input"
            value={agentConfig.config?.memory_size || agentConfig.memory_size || 10}
            onChange={(e) => {
              const value = parseInt(e.target.value);
              if (agentConfig.config) {
                updateConfigField('config.memory_size', value);
              } else {
                updateConfigField('memory_size', value);
              }
            }}
            min={1}
            max={100}
          />
        ) : (
          <div className="field-content">
            {agentConfig.config?.memory_size || agentConfig.memory_size || 10}
          </div>
        )}
      </div>
      
      {/* Agent Tools */}
      <div className="config-field">
        <label className="field-label">Tools</label>
        <div className="field-content tools-field">
          {agentConfig.tools && agentConfig.tools.length > 0 ? (
            <ul className="tools-list">
              {agentConfig.tools.map((tool, index) => (
                <li key={index}>
                  {isEditMode ? (
                    <div className="tool-edit">
                      <input 
                        type="text" 
                        className="tool-name-input"
                        value={tool.name}
                        onChange={(e) => {
                          const updatedTools = [...agentConfig.tools];
                          updatedTools[index] = {
                            ...updatedTools[index],
                            name: e.target.value
                          };
                          updateConfigField('tools', updatedTools);
                        }}
                        placeholder="Tool name"
                      />
                      <input 
                        type="text" 
                        className="tool-endpoint-input"
                        value={tool.endpoint}
                        onChange={(e) => {
                          const updatedTools = [...agentConfig.tools];
                          updatedTools[index] = {
                            ...updatedTools[index],
                            endpoint: e.target.value
                          };
                          updateConfigField('tools', updatedTools);
                        }}
                        placeholder="Tool endpoint"
                      />
                      <button 
                        className="remove-tool-button"
                        onClick={() => {
                          const updatedTools = agentConfig.tools.filter((_, i) => i !== index);
                          updateConfigField('tools', updatedTools);
                        }}
                      >
                        <X size={16} />
                      </button>
                    </div>
                  ) : (
                    <>
                      <strong>{tool.name}:</strong> {tool.endpoint}
                    </>
                  )}
                </li>
              ))}
              {isEditMode && (
                <li>
                  <button 
                    className="add-tool-button"
                    onClick={() => {
                      const updatedTools = [
                        ...(agentConfig.tools || []),
                        { name: "New Tool", endpoint: "https://" }
                      ];
                      updateConfigField('tools', updatedTools);
                    }}
                  >
                    + Add Tool
                  </button>
                </li>
              )}
            </ul>
          ) : (
            <div>
              {isEditMode ? (
                <button 
                  className="add-tool-button"
                  onClick={() => {
                    updateConfigField('tools', [
                      { name: "New Tool", endpoint: "https://" }
                    ]);
                  }}
                >
                  + Add Tool
                </button>
              ) : (
                "No tools specified"
              )}
            </div>
          )}
        </div>
      </div>
      
      {/* Knowledge Base */}
      {hasKnowledgeBase && (
        <div className="config-field">
          <label className="field-label">Knowledge Base</label>
          <div className="field-content knowledge-field">
            <div className="knowledge-info">
              <div className="knowledge-type">
                <Database size={16} />
                <span>
                  {knowledgeBaseType === 'llamacloud' ? 'LlamaCloud Storage' : 'Local Storage'}
                </span>
              </div>
              
              {knowledgeBaseType === 'llamacloud' && agentConfig.knowledge_base.index_name && (
                <div className="knowledge-detail">
                  <strong>Index:</strong> {agentConfig.knowledge_base.index_name}
                </div>
              )}
              
              {knowledgeBaseType === 'local' && agentConfig.knowledge_base.local_path && (
                <div className="knowledge-detail">
                  <strong>Path:</strong> {agentConfig.knowledge_base.local_path}
                </div>
              )}
              
              {agentConfig.knowledge_base.document_count && (
                <div className="knowledge-detail">
                  <strong>Documents:</strong> {agentConfig.knowledge_base.document_count}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
      
      {/* Current file */}
      {yamlFile && (
        <div className="config-field">
          <label className="field-label">Loaded File</label>
          <div className="field-content">
            {yamlFile.name}
          </div>
        </div>
      )}
    </div>
  );
  
  // Render system logs tab content
  // Render system logs tab content
  const renderSystemLogsTab = () => (
    <div className="system-logs-container" ref={logsContainerRef}>
      {isLoadingLogs && logs.length === 0 ? (
        <div className="logs-empty-state">
          <LoadingIndicator />
          <p>Loading system logs...</p>
        </div>
      ) : logs.length === 0 ? (
        <div className="logs-empty-state">
          <Terminal size={32} />
          <p>No system logs available</p>
        </div>
      ) : (
        <>
          {logs
            // Filter out unwanted log entries
            .filter(log => {
              // Skip log lines that contain "Returning X log lines"
              if (log.includes("app.routers.logs") && log.includes("Returning") && log.includes("log lines")) {
                return false;
              }
              return true;
            })
            .map((log, index) => {
              // Skip empty lines
              if (!log || !log.trim()) return null;
              
              // Process the log content
              let logClass = "log-entry";
              
              // Add color classes based on log content
              if (log.includes("INFO")) logClass += " log-info";
              if (log.includes("WARNING")) logClass += " log-warning";
              if (log.includes("ERROR")) logClass += " log-error";
              if (log.includes("DEBUG")) logClass += " log-debug";
              
              return (
                <div 
                  key={index} 
                  className={logClass}
                  dangerouslySetInnerHTML={{
                    __html: log
                      // Replace INFO, WARNING, ERROR with colored versions
                      .replace(/INFO/g, '<span class="log-level-info">INFO</span>')
                      .replace(/WARNING/g, '<span class="log-level-warning">WARNING</span>')
                      .replace(/ERROR/g, '<span class="log-level-error">ERROR</span>')
                      .replace(/DEBUG/g, '<span class="log-level-debug">DEBUG</span>')
                  }}
                />
              );
            })}
        </>
      )}
    </div>
  )

  return (
    <div className="agent-builder-container">
      {/* Left Panel: Chat Interface */}
      <div className="chat-panel">
        <div className="chat-header">
          <Link to="/" className="back-button">
            <ArrowLeft size={18} />
            <span>Back to Builder</span>
          </Link>
          <h2>{agentConfig?.name || 'Test Your Agent'}</h2>
        </div>
        
        <div className="messages-container">
          {/* Initial upload prompt */}
          {!agentConfig && !yamlFile && (
            <div className="upload-prompt">
              <h3>Upload Agent Configuration</h3>
              <p>Upload a YAML file to test your agent</p>
              <button 
                className="upload-button"
                onClick={triggerFileUpload}
              >
                <Upload size={20} />
                Upload YAML
              </button>
              <input 
                type="file" 
                ref={fileInputRef}
                onChange={handleFileUpload}
                accept=".yaml,.yml"
                style={{ display: 'none' }}
              />
            </div>
          )}
          
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
            placeholder={agentConfig ? "Type your message..." : "Upload a YAML file to start"}
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            onKeyPress={handleKeyPress}
            disabled={isLoading || !agentConfig || isEditMode}
            rows={1}
          />
          
          <button 
            className={`send-button ${!inputMessage.trim() || isLoading || !agentConfig || isEditMode ? 'disabled' : ''}`}
            onClick={handleSendMessage}
            disabled={!inputMessage.trim() || isLoading || !agentConfig || isEditMode}
          >
            <Send size={20} />
          </button>
        </div>
      </div>
      
      {/* Right Panel: Tabbed Interface */}
      <div className="config-panel">
        <div className="config-tabs">
          <button 
            className={`tab-button ${activeTab === 'info' ? 'active' : ''}`}
            onClick={() => setActiveTab('info')}
          >
            Agent Information
          </button>
          <button 
            className={`tab-button ${activeTab === 'logs' ? 'active' : ''}`}
            onClick={() => setActiveTab('logs')}
          >
            System Logs
          </button>
          
          {/* Action buttons that change based on the active tab */}
          <div className="config-actions">
            {activeTab === 'info' && agentConfig ? (
              isEditMode ? (
                <>
                  <button 
                    className="action-button save-button"
                    onClick={saveConfigChanges}
                    disabled={isSaving}
                  >
                    {isSaving ? <LoadingIndicator size={16} /> : <Save size={18} />}
                    <span>Save</span>
                  </button>
                  <button 
                    className="action-button cancel-button"
                    onClick={toggleEditMode}
                    disabled={isSaving}
                  >
                    <X size={18} />
                    <span>Cancel</span>
                  </button>
                </>
              ) : (
                <button 
                  className="action-button edit-button"
                  onClick={toggleEditMode}
                >
                  <Edit size={18} />
                  <span>Edit</span>
                </button>
              )
            ) : activeTab === 'logs' ? (
              <button 
                className="action-button refresh-button"
                onClick={async () => {
                  setIsLoadingLogs(true);
                  try {
                    const response = await fetchLogs();
                    if (response && response.logs) {
                      setLogs(response.logs);
                    }
                  } catch (error) {
                    console.error('Error refreshing logs:', error);
                  } finally {
                    setIsLoadingLogs(false);
                  }
                }}
                disabled={isLoadingLogs}
              >
                {isLoadingLogs ? <LoadingIndicator size={16} /> : <RefreshCw size={18} />}
                <span>{isLoadingLogs ? 'Loading...' : 'Refresh'}</span>
              </button>
            ) : null}
          </div>
        </div>
        
        <div className="tab-content">
          {!agentConfig && activeTab === 'info' ? (
            <div className="empty-state">
              <p>Upload a YAML file to view agent details</p>
            </div>
          ) : (
            activeTab === 'info' ? renderAgentInfoTab() : renderSystemLogsTab()
          )}
        </div>
      </div>
    </div>
  );
};

export default TestAgent;