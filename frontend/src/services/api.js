/**
 * API client for backend communication
 */

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';

/**
 * Send a message to Claude via the backend API
 * @param {Array} messages - Array of previous messages in the conversation
 * @param {Object} agentConfig - Current agent configuration
 * @returns {Promise} - Promise that resolves to the API response
 */
export const sendMessage = async (messages, agentConfig) => {
  try {
    // Format messages to match the expected format in the backend
    const formattedMessages = messages.map(msg => ({
      role: msg.role,
      content: msg.content
    }));

    // Format agent config to match backend's expectations
    const formattedAgentConfig = {
      name: agentConfig.name || '',
      description: agentConfig.description || '',
      instruction: agentConfig.instruction || '',
      memory_size: agentConfig.memory_size || 10,
      tools: agentConfig.tools || [],
      knowledge_base: agentConfig.knowledge_base || {
        storage_type: 'llamacloud',
        index_name: null,
        project_name: null,
        local_path: null,
        document_count: 0,
        file_names: []
      }
    };

    console.log('Sending to backend:', {
      messages: formattedMessages,
      agent_config: formattedAgentConfig
    });

    const response = await fetch(`${API_BASE_URL}/api/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        messages: formattedMessages,
        agent_config: formattedAgentConfig,
      }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error('API Error Response:', errorText);
      
      try {
        const errorData = JSON.parse(errorText);
        throw new Error(errorData.detail || 'Error communicating with the server');
      } catch (jsonError) {
        throw new Error(`Server error: ${response.status} ${response.statusText}`);
      }
    }

    return await response.json();
  } catch (error) {
    console.error('Error sending message:', error);
    throw error;
  }
};

/**
 * Upload a single file for an agent
 * @param {FormData} formData - Form data containing file and agent_name
 * @returns {Promise} - Promise that resolves to the API response
 */
export const uploadFile = async (formData) => {
  try {
    console.log('Uploading file');
    
    const response = await fetch(`${API_BASE_URL}/api/upload-file`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error('API Error Response:', errorText);
      
      try {
        const errorData = JSON.parse(errorText);
        throw new Error(errorData.detail || 'Error uploading file');
      } catch (jsonError) {
        throw new Error(`Server error: ${response.status} ${response.statusText}`);
      }
    }

    return await response.json();
  } catch (error) {
    console.error('Error uploading file:', error);
    throw error;
  }
};

/**
 * Get list of uploaded files for an agent
 * @param {string} agentName - Name of the agent
 * @returns {Promise} - Promise that resolves to the API response
 */
export const getFiles = async (agentName) => {
  try {
    console.log(`Getting files for agent: ${agentName}`);
    
    const response = await fetch(`${API_BASE_URL}/api/files/${encodeURIComponent(agentName)}`, {
      method: 'GET',
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error('API Error Response:', errorText);
      
      try {
        const errorData = JSON.parse(errorText);
        throw new Error(errorData.detail || 'Error getting files');
      } catch (jsonError) {
        throw new Error(`Server error: ${response.status} ${response.statusText}`);
      }
    }

    return await response.json();
  } catch (error) {
    console.error('Error getting files:', error);
    throw error;
  }
};

/**
 * Create index from uploaded files
 * @param {string} agentName - Name of the agent
 * @returns {Promise} - Promise that resolves to the API response
 */
export const createIndex = async (agentName) => {
  try {
    console.log(`Creating index for agent: ${agentName}`);
    
    const response = await fetch(`${API_BASE_URL}/api/create-index/${encodeURIComponent(agentName)}`, {
      method: 'POST',
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error('API Error Response:', errorText);
      
      try {
        const errorData = JSON.parse(errorText);
        throw new Error(errorData.detail || 'Error creating index');
      } catch (jsonError) {
        throw new Error(`Server error: ${response.status} ${response.statusText}`);
      }
    }

    return await response.json();
  } catch (error) {
    console.error('Error creating index:', error);
    throw error;
  }
};

/**
 * Save uploaded files to local storage
 * @param {string} agentName - Name of the agent
 * @returns {Promise} - Promise that resolves to the API response
 */
export const saveToLocal = async (agentName) => {
  try {
    console.log(`Saving to local storage for agent: ${agentName}`);
    
    const response = await fetch(`${API_BASE_URL}/api/save-local/${encodeURIComponent(agentName)}`, {
      method: 'POST',
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error('API Error Response:', errorText);
      
      try {
        const errorData = JSON.parse(errorText);
        throw new Error(errorData.detail || 'Error saving to local storage');
      } catch (jsonError) {
        throw new Error(`Server error: ${response.status} ${response.statusText}`);
      }
    }

    return await response.json();
  } catch (error) {
    console.error('Error saving to local storage:', error);
    throw error;
  }
};

/**
 * Remove a file from an agent's uploaded files
 * @param {string} agentName - Name of the agent
 * @param {string} fileName - Name of the file to remove
 * @returns {Promise} - Promise that resolves to the API response
 */
export const removeFile = async (agentName, fileName) => {
  try {
    console.log(`Removing file ${fileName} for agent: ${agentName}`);
    
    const response = await fetch(`${API_BASE_URL}/api/files/${encodeURIComponent(agentName)}/${encodeURIComponent(fileName)}`, {
      method: 'DELETE',
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error('API Error Response:', errorText);
      
      try {
        const errorData = JSON.parse(errorText);
        throw new Error(errorData.detail || 'Error removing file');
      } catch (jsonError) {
        throw new Error(`Server error: ${response.status} ${response.statusText}`);
      }
    }

    return await response.json();
  } catch (error) {
    console.error('Error removing file:', error);
    throw error;
  }
};

/**
 * Send a message to chat with a test agent
 * @param {Object} params - Chat parameters
 * @param {string} params.message - User message
 * @param {Object} params.agent_config - Agent configuration from YAML
 * @param {Array} params.history - Chat history
 * @returns {Promise} - Promise that resolves to the API response
 */
export const testAgentChat = async ({ message, agent_config, history }) => {
  try {
    // Format chat history to match the expected format in the backend
    const formattedHistory = history.map(msg => ({
      role: msg.role,
      content: msg.content
    }));

    console.log('Testing agent with message:', message);
    console.log('Agent config:', agent_config);

    const response = await fetch(`${API_BASE_URL}/api/test-agent`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        message: message,
        agent_config: agent_config,
        history: formattedHistory,
      }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error('API Error Response:', errorText);
      
      try {
        const errorData = JSON.parse(errorText);
        throw new Error(errorData.detail || 'Error communicating with the agent');
      } catch (jsonError) {
        throw new Error(`Server error: ${response.status} ${response.statusText}`);
      }
    }

    return await response.json();
  } catch (error) {
    console.error('Error testing agent:', error);
    throw error;
  }
};

/**
 * Generate YAML configuration from agent configuration
 * @param {Object} agentConfig - Complete agent configuration
 * @returns {Promise} - Promise that resolves to the generated YAML
 */
export const generateYaml = async (agentConfig) => {
  try {
    // Format agent config to match backend's expectations
    const formattedAgentConfig = {
      name: agentConfig.name || '',
      description: agentConfig.description || '',
      instruction: agentConfig.instruction || '',
      memory_size: agentConfig.memory_size || 10,
      tools: agentConfig.tools || [],
      knowledge_base: agentConfig.knowledge_base || {
        storage_type: 'llamacloud',
        index_name: null,
        project_name: null,
        local_path: null,
        document_count: 0
      }
    };

    const response = await fetch(`${API_BASE_URL}/api/yaml`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(formattedAgentConfig),
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error('API Error Response:', errorText);
      
      try {
        const errorData = JSON.parse(errorText);
        throw new Error(errorData.detail || 'Error generating YAML');
      } catch (jsonError) {
        throw new Error(`Server error: ${response.status} ${response.statusText}`);
      }
    }

    const data = await response.json();
    return data.yaml;
  } catch (error) {
    console.error('Error generating YAML:', error);
    throw error;
  }
};

/**
 * Check API health
 * @returns {Promise} - Promise that resolves to the health check response
 */
export const checkHealth = async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/health`);
    
    if (!response.ok) {
      throw new Error('API health check failed');
    }
    
    return await response.json();
  } catch (error) {
    console.error('API health check failed:', error);
    throw error;
  }
};

/**
 * Fetch the current system logs
 * @returns {Promise<Object>} - Promise resolving to logs object with logs array
 */
export const fetchLogs = async () => {
  try {
    const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';
    const response = await fetch(`${API_BASE_URL}/api/logs/current`);
    
    if (!response.ok) {
      const errorText = await response.text();
      console.error('API Error Response:', errorText);
      
      try {
        const errorData = JSON.parse(errorText);
        throw new Error(errorData.detail || 'Error fetching logs');
      } catch (jsonError) {
        throw new Error(`Server error: ${response.status} ${response.statusText}`);
      }
    }
    
    const data = await response.json();
    console.log('Logs fetched successfully:', data.logs.length);
    return data;
  } catch (error) {
    console.error('Error fetching logs:', error);
    throw error;
  }
};

/**
 * Establish SSE connection for logs
 * @param {Function} onMessage - Callback function to handle incoming log messages
 * @returns {EventSource} - EventSource instance
 */
export const connectToLogsSSE = (onMessage) => {
  const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';
  const eventSource = new EventSource(`${API_BASE_URL}/api/logs/stream`);
  
  eventSource.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      onMessage(data);
    } catch (error) {
      console.error('Error parsing SSE message:', error);
    }
  };
  
  eventSource.onerror = (error) => {
    console.error('SSE connection error:', error);
    // Don't close the connection immediately, let it try to reconnect
    if (eventSource.readyState === EventSource.CLOSED) {
      console.log('SSE connection closed, attempting to reconnect...');
      // Create a new connection
      const newEventSource = new EventSource(`${API_BASE_URL}/api/logs/stream`);
      newEventSource.onmessage = eventSource.onmessage;
      newEventSource.onerror = eventSource.onerror;
      return newEventSource;
    }
  };
  
  return eventSource;
};