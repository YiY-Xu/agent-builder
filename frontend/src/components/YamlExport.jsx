import React from 'react';
import { downloadYaml } from '../services/yamlGenerator';
import { useAgent } from '../context/AgentContext';
import '../styles/components.css';

/**
 * Component for displaying and exporting YAML
 */
const YamlExport = ({ yamlContent }) => {
  const { agentConfig } = useAgent();
  
  /**
   * Handle download button click
   */
  const handleDownload = () => {
    const fileName = `${agentConfig.name?.replace(/\s+/g, '_').toLowerCase() || 'agent'}_config.yaml`;
    downloadYaml(yamlContent, fileName);
  };
  
  /**
   * Handle copy button click
   */
  const handleCopy = () => {
    navigator.clipboard.writeText(yamlContent);
    alert('YAML copied to clipboard!');
  };

  return (
    <div className="yaml-export-container">
      <h3 className="yaml-title">Generated YAML Configuration</h3>
      
      <div className="yaml-content">
        <pre>{yamlContent}</pre>
      </div>
      
      <div className="yaml-actions">
        <button 
          className="download-button"
          onClick={handleDownload}
        >
          Download YAML
        </button>
        
        <button 
          className="copy-button"
          onClick={handleCopy}
        >
          Copy to Clipboard
        </button>
      </div>
    </div>
  );
};

export default YamlExport;