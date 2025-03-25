import React, { createContext, useContext, useState } from 'react';
import { sanitizeAgentName } from '../utils/helpers';

// Create context
const AgentContext = createContext();

/**
 * AgentProvider component that manages the agent configuration state
 * and provides it to all child components
 */
export const AgentProvider = ({ children }) => {
  // Initial agent configuration state
  const [agentConfig, setAgentConfig] = useState({
    name: '',
    description: '',
    instruction: '',
    memory_size: 10,
    mode: 'debug', // Set default mode to debug
    tools: [],
    mcp_servers: [],  // Add MCP servers to agent config
    knowledge_base: {
      storage_type: null,  // Default to LlamaCloud storage
      index_info: null,
      project_name: null,
      local_path: null,
      document_count: 0,
      file_names: []
    }
  });

  // Messages state
  const [messages, setMessages] = useState([]);

  // Loading state
  const [isLoading, setIsLoading] = useState(false);

  // YAML generation state
  const [showYamlButton, setShowYamlButton] = useState(false);
  const [yamlContent, setYamlContent] = useState('');
  
  // Knowledge upload state
  const [showKnowledgeUpload, setShowKnowledgeUpload] = useState(false);
  const [uploadingKnowledge, setUploadingKnowledge] = useState(false);

  // Add MCP server state
  const [mcpServers, setMcpServers] = useState([]);
  const [selectedServers, setSelectedServers] = useState([]);
  const [showMcpServerSelection, setShowMcpServerSelection] = useState(false);

  /**
   * Update a single field in the agent configuration
   * @param {String} field - The field to update
   * @param {Any} value - The new value for the field
   */
  const updateAgentConfig = (field, value) => {
    if (field === 'name' && value && agentConfig.knowledge_base) {
      // When the name changes, update the sanitized name in the knowledge base
      const sanitizedName = sanitizeAgentName(value);
      
      setAgentConfig(prev => ({
        ...prev,
        [field]: value,
        knowledge_base: {
          ...prev.knowledge_base,
          sanitized_name: sanitizedName
        }
      }));
    } else {
      setAgentConfig(prev => ({
        ...prev,
        [field]: value
      }));
    }
  };

  /**
   * Add a message to the chat history
   * @param {String} role - The role of the sender (user or assistant)
   * @param {String} content - The message content
   */
  const addMessage = (role, content) => {
    setMessages(prev => [...prev, { role, content }]);
  };

  /**
   * Update the agent configuration based on received config updates
   * @param {Object|Array} configUpdates - The configuration updates to apply
   */
  const applyConfigUpdates = (configUpdates) => {
    if (!configUpdates) return;

    let updatedConfig = { ...agentConfig };

    // Handle array of updates
    if (Array.isArray(configUpdates)) {
      configUpdates.forEach(update => {
        if (update.field === 'tools') {
          updatedConfig.tools = update.value;
        } else if (update.field === 'knowledge_base') {
          updatedConfig.knowledge_base = {
            ...updatedConfig.knowledge_base,
            ...update.value
          };
        } else {
          updatedConfig[update.field] = update.value;
        }
      });
    } 
    // Handle single update
    else {
      if (configUpdates.field === 'tools') {
        updatedConfig.tools = configUpdates.value;
      } else if (configUpdates.field === 'knowledge_base') {
        updatedConfig.knowledge_base = {
          ...updatedConfig.knowledge_base,
          ...configUpdates.value
        };
      } else {
        updatedConfig[configUpdates.field] = configUpdates.value;
      }
    }

    setAgentConfig(updatedConfig);
  };
  
  /**
   * Update the knowledge storage type
   * @param {Object} storageInfo - Information about the storage type
   */
  const updateKnowledgeStorage = (storageInfo) => {
    setAgentConfig(prev => ({
      ...prev,
      knowledge_base: {
        ...prev.knowledge_base,
        storage_type: storageInfo.type,
        local_path: storageInfo.type === 'local' ? (storageInfo.local_path) : null
      }
    }));
  };
  
  /**
   * Update the knowledge base information after a successful upload
   * @param {Object} knowledgeInfo - Information about the uploaded knowledge
   */
  const updateKnowledgeBase = (knowledgeInfo) => {
    // Get or compute the sanitized name
    const sanitizedName = knowledgeInfo.sanitized_name || 
                         (agentConfig.name ? sanitizeAgentName(agentConfig.name) : null);
    
    // Never create fallback index_info - only use what the backend provides
    // If no index_info is provided, something is wrong with the backend
    if (!knowledgeInfo.index_info) {
      console.error('Cannot update knowledge base - missing index_info from backend');
    }
    
    setAgentConfig(prev => ({
      ...prev,
      knowledge_base: {
        ...prev.knowledge_base,
        storage_type: knowledgeInfo.storage_type,
        index_info: knowledgeInfo.index_info,
        document_count: knowledgeInfo.document_count,
        project_name: knowledgeInfo.project_name,
        file_names: knowledgeInfo.file_names || [],
        sanitized_name: sanitizedName
      }
    }));
  };

  /**
   * Reset the entire application state
   */
  const resetState = () => {
    setAgentConfig({
      name: '',
      description: '',
      instruction: '',
      memory_size: 10,
      mode: 'debug', // Set default mode to debug
      tools: [],
      mcp_servers: [],
      knowledge_base: {
        storage_type: 'llamacloud',
        index_info: null,
        project_name: null,
        local_path: null,
        document_count: 0,
        file_names: [],
        sanitized_name: null
      }
    });
    setMessages([]);
    setShowYamlButton(false);
    setYamlContent('');
    setShowKnowledgeUpload(false);
    setMcpServers([]);
    setSelectedServers([]);
  };

  /**
   * Update MCP server selection
   * @param {Array} servers - Array of selected server names
   */
  const updateMcpServers = (servers) => {
    console.log('Updating MCP servers in agent config:', servers);
    setSelectedServers(servers);
    setAgentConfig(prev => {
      console.log('Previous agent config:', prev);
      const updated = {
        ...prev,
        mcp_servers: servers
      };
      console.log('Updated agent config with MCP servers:', updated);
      return updated;
    });
  };

  // Context value
  const value = {
    agentConfig,
    setAgentConfig,
    messages,
    setMessages,
    isLoading,
    setIsLoading,
    showYamlButton,
    setShowYamlButton,
    yamlContent,
    setYamlContent,
    showKnowledgeUpload,
    setShowKnowledgeUpload,
    uploadingKnowledge,
    setUploadingKnowledge,
    mcpServers,
    setMcpServers,
    selectedServers,
    setSelectedServers,
    showMcpServerSelection,
    setShowMcpServerSelection,
    updateAgentConfig,
    addMessage,
    applyConfigUpdates,
    updateKnowledgeStorage,
    updateKnowledgeBase,
    resetState,
    updateMcpServers
  };

  return (
    <AgentContext.Provider value={value}>
      {children}
    </AgentContext.Provider>
  );
};

/**
 * Custom hook to use the agent context
 */
export const useAgent = () => {
  const context = useContext(AgentContext);
  
  if (!context) {
    throw new Error('useAgent must be used within an AgentProvider');
  }
  
  return context;
};

export default AgentContext;