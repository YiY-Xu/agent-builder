import React, { useState, useEffect } from 'react';
import { useAgent } from '../context/AgentContext';
import YamlExport from './YamlExport';
import KnowledgeUpload from './KnowledgeUpload';
import useChat from '../hooks/useChat';
import '../styles/components.css';

/**
 * Component for the right panel with agent configuration
 */
const ConfigPanel = () => {
  const { 
    agentConfig, 
    showKnowledgeUpload, 
    setShowKnowledgeUpload
  } = useAgent();
  const { showYamlButton, yamlContent } = useChat();
  const [previousConfig, setPreviousConfig] = useState({});
  const [changedContent, setChangedContent] = useState({});

  // Watch for changes in agentConfig and update changedContent
  useEffect(() => {
    const newChanges = {};
    
    // Compare each field with its previous value
    if (agentConfig.name !== previousConfig.name) {
      const oldName = previousConfig.name || "";
      const newName = agentConfig.name || "";
      newChanges.name = findNewContent(oldName, newName);
    }
    
    if (agentConfig.description !== previousConfig.description) {
      const oldDesc = previousConfig.description || "";
      const newDesc = agentConfig.description || "";
      newChanges.description = findNewContent(oldDesc, newDesc);
    }
    
    if (agentConfig.instruction !== previousConfig.instruction) {
      const oldInstr = previousConfig.instruction || "";
      const newInstr = agentConfig.instruction || "";
      newChanges.instruction = findNewContent(oldInstr, newInstr);
    }
    
    if (agentConfig.memory_size !== previousConfig.memory_size) {
      newChanges.memory_size = String(agentConfig.memory_size);
    }
    
    // For tools, we'll highlight newly added tools
    if (agentConfig.tools?.length !== previousConfig.tools?.length) {
      const oldTools = previousConfig.tools || [];
      const newTools = agentConfig.tools || [];
      newChanges.tools = newTools.slice(oldTools.length);
    }
    
    setChangedContent(newChanges);
    setPreviousConfig(agentConfig);
  }, [agentConfig]);

  // Clear highlights after 2 seconds
  useEffect(() => {
    if (Object.keys(changedContent).length > 0) {
      const timer = setTimeout(() => {
        setChangedContent({});
      }, 2000);
      return () => clearTimeout(timer);
    }
  }, [changedContent]);

  // Helper function to find new content in a string
  const findNewContent = (oldStr, newStr) => {
    if (!oldStr) return newStr;
    if (newStr.includes(oldStr)) {
      return newStr.slice(oldStr.length).trim();
    }
    return newStr;
  };

  // Helper function to render content with highlights
  const renderWithHighlight = (content, changedPart) => {
    if (!changedPart) return content;
    
    const parts = content.split(changedPart);
    if (parts.length === 1) return content;
    
    return (
      <>
        {parts[0]}
        <span className="highlight-new">{changedPart}</span>
        {parts.slice(1).join(changedPart)}
      </>
    );
  };

  return (
    <div className="config-panel">
      <div className="config-header">
        <h2>Agent Configuration</h2>
      </div>
      
      {showKnowledgeUpload ? (
        <KnowledgeUpload />
      ) : (
        <div className="config-fields">
          {/* Agent Name */}
          <div className="config-field">
            <label className="field-label">Agent Name</label>
            <div className="field-content">
              {renderWithHighlight(agentConfig.name || "Not yet specified", changedContent.name)}
            </div>
          </div>
          
          {/* Agent Description */}
          <div className="config-field">
            <label className="field-label">Agent Description</label>
            <div className="field-content">
              {renderWithHighlight(agentConfig.description || "Not yet specified", changedContent.description)}
            </div>
          </div>
          
          {/* Agent Instruction */}
          <div className="config-field">
            <label className="field-label">Agent Instruction</label>
            <div className="field-content instruction-field">
              {renderWithHighlight(agentConfig.instruction || "Not yet specified", changedContent.instruction)}
            </div>
          </div>
          
          {/* Agent Memory Size */}
          <div className="config-field">
            <label className="field-label">Agent Memory Size</label>
            <div className="field-content">
              {changedContent.memory_size ? (
                <span className="highlight-new">{agentConfig.memory_size}</span>
              ) : (
                agentConfig.memory_size
              )}
            </div>
          </div>
          
          {/* Agent Tools */}
          <div className="config-field">
            <label className="field-label">Agent Tools</label>
            <div className="field-content tools-field">
              {agentConfig.tools.length > 0 ? (
                <ul className="tools-list">
                  {agentConfig.tools.map((tool, index) => (
                    <li key={index} className={changedContent.tools?.includes(tool) ? 'highlight-new' : ''}>
                      <strong>{tool.name}:</strong> {tool.endpoint}
                    </li>
                  ))}
                </ul>
              ) : (
                "No tools specified"
              )}
            </div>
          </div>
          
          {/* Knowledge Base */}
          <div className="config-field">
            <label className="field-label">Knowledge Base</label>
            <div className="field-content">
              {agentConfig.knowledge_base && agentConfig.knowledge_base.document_count > 0 ? (
                <div className="knowledge-info">
                  <p><strong>Documents:</strong> {agentConfig.knowledge_base.document_count}</p>
                  {agentConfig.knowledge_base.file_names && agentConfig.knowledge_base.file_names.length > 0 && (
                    <ul className="file-names-list">
                      {agentConfig.knowledge_base.file_names.map((name, index) => (
                        <li key={index}>{name}</li>
                      ))}
                    </ul>
                  )}
                  <button 
                    className="add-knowledge-button"
                    onClick={() => setShowKnowledgeUpload(true)}
                  >
                    Manage Documents
                  </button>
                </div>
              ) : (
                <div className="knowledge-empty">
                  <p>No knowledge documents added</p>
                  <button 
                    className="add-knowledge-button"
                    onClick={() => setShowKnowledgeUpload(true)}
                  >
                    Add Knowledge
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
      
      {/* YAML export */}
      {showYamlButton && yamlContent && !showKnowledgeUpload && (
        <YamlExport yamlContent={yamlContent} />
      )}
    </div>
  );
};

export default ConfigPanel;