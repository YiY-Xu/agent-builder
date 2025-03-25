/**
 * Utility functions for YAML generation and handling
 */
import yaml from 'js-yaml';

/**
 * Generate a YAML string from the agent configuration object
 * This function is a fallback if the backend YAML generation fails
 * @param {Object} agentConfig - The agent configuration object
 * @returns {String} - The generated YAML string
 */
export const generateYaml = (agentConfig) => {
    // Create a clean configuration object
    const config = {
        name: agentConfig.name || 'Unnamed Agent',
        description: agentConfig.description || '',
        version: '1.0.0',
        created_at: new Date().toISOString(),
        instruction: agentConfig.instruction || '',
        config: {
            memory_size: agentConfig.memory_size || 10,
            claude_model: 'claude-3-7-sonnet-20250219'
        }
    };

    // Add tools if any
    if (agentConfig.tools?.length > 0) {
        config.tools = agentConfig.tools.map(tool => ({
            name: tool.name,
            endpoint: tool.endpoint
        }));
    }

    // Add MCP servers if any
    if (agentConfig.mcp_servers?.length > 0) {
        config.mcp_servers = agentConfig.mcp_servers;
    }

    // Add knowledge base if available
    if (agentConfig.knowledge_base) {
        config.knowledge_base = {
            storage_type: agentConfig.knowledge_base.storage_type,
            index_info: agentConfig.knowledge_base.index_info,
            document_count: agentConfig.knowledge_base.document_count || 0,
            project_name: agentConfig.knowledge_base.project_name || '__PROJECT_NAME__'
        };
    }

    // Convert to YAML with proper formatting
    return yaml.dump(config, {
        lineWidth: -1,
        noRefs: true,
        sortKeys: false,
        forceQuotes: true,
        quotingType: '"'
    });
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