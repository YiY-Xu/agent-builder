/**
 * Utility functions for YAML generation and handling
 */

/**
 * Generate a YAML string from the agent configuration object
 * This function is a fallback if the backend YAML generation fails
 * @param {Object} agentConfig - The agent configuration object
 * @returns {String} - The generated YAML string
 */
export const generateYaml = (agentConfig) => {
    const timestamp = new Date().toISOString();
    
    let yaml = `# Agent Configuration\n`;
    yaml += `name: ${agentConfig.name || 'Unnamed Agent'}\n`;
    
    if (agentConfig.description) {
      yaml += `description: ${agentConfig.description}\n`;
    }
    
    yaml += `version: 1.0.0\n`;
    yaml += `created_at: ${timestamp}\n\n`;
    
    // Add instruction with proper indentation using pipe symbol
    if (agentConfig.instruction) {
      yaml += `instruction: |\n`;
      const lines = agentConfig.instruction.split('\n');
      lines.forEach(line => {
        yaml += `  ${line}\n`;
      });
      yaml += '\n';
    }
    
    // Add configuration section
    yaml += `# Configuration\n`;
    yaml += `config:\n`;
    yaml += `  memory_size: ${agentConfig.memory_size || 10}\n`;
    yaml += `  claude_model: "claude-3-7-sonnet-20250219"\n\n`;
    
    // Add tools if any
    if (agentConfig.tools && agentConfig.tools.length > 0) {
      yaml += `# Tools\ntools:\n`;
      agentConfig.tools.forEach(tool => {
        yaml += `  - name: ${tool.name}\n`;
        yaml += `    endpoint: ${tool.endpoint}\n`;
      });
    }
    
    return yaml;
  };
  
  /**
   * Download YAML as a file
   * @param {String} yamlContent - The YAML content to download
   * @param {String} filename - The name of the file to download
   */
  export const downloadYaml = (yamlContent, filename) => {
    const blob = new Blob([yamlContent], { type: 'text/yaml' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    
    link.href = url;
    link.download = filename || 'agent-config.yaml';
    document.body.appendChild(link);
    link.click();
    
    // Clean up
    setTimeout(() => {
      URL.revokeObjectURL(url);
      document.body.removeChild(link);
    }, 100);
  };