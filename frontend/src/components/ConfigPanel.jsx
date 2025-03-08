import React from 'react';
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
              {agentConfig.name || "Not yet specified"}
            </div>
          </div>
          
          {/* Agent Description */}
          <div className="config-field">
            <label className="field-label">Agent Description</label>
            <div className="field-content">
              {agentConfig.description || "Not yet specified"}
            </div>
          </div>
          
          {/* Agent Instruction */}
          <div className="config-field">
            <label className="field-label">Agent Instruction</label>
            <div className="field-content instruction-field">
              {agentConfig.instruction || "Not yet specified"}
            </div>
          </div>
          
          {/* Agent Memory Size */}
          <div className="config-field">
            <label className="field-label">Agent Memory Size</label>
            <div className="field-content">
              {agentConfig.memory_size}
            </div>
          </div>
          
          {/* Agent Tools */}
          <div className="config-field">
            <label className="field-label">Agent Tools</label>
            <div className="field-content tools-field">
              {agentConfig.tools.length > 0 ? (
                <ul className="tools-list">
                  {agentConfig.tools.map((tool, index) => (
                    <li key={index}>
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