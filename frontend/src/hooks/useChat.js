import { useState, useEffect, useRef } from 'react';
import { useAgent } from '../context/AgentContext';
import { sendMessage, generateYaml as fetchYaml } from '../services/api';
import { generateYaml as localGenerateYaml } from '../services/yamlGenerator';

/**
 * Custom hook for chat functionality
 */
const useChat = () => {
  const {
    agentConfig,
    messages,
    setMessages,
    isLoading,
    setIsLoading,
    showYamlButton,
    setShowYamlButton,
    yamlContent,
    setYamlContent,
    setShowKnowledgeUpload,
    applyConfigUpdates,
    updateKnowledgeStorage,
    setShowMcpServerSelection
  } = useAgent();

  const [inputMessage, setInputMessage] = useState('');
  const [error, setError] = useState(null);
  
  // Reference for auto-scrolling
  const messagesEndRef = useRef(null);
  // Reference for the input field
  const inputRef = useRef(null);

  // Auto-scroll when messages change
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);

  // Initialize conversation if empty
  useEffect(() => {
    if (messages.length === 0) {
      // Add initial bot message
      setMessages([{
        role: 'assistant',
        content: 'Welcome to the Agent Builder! I\'ll help you create a custom agent. Let\'s start with the basics - what would you like to name your agent?'
      }]);
    }
  }, [messages.length, setMessages]);

  /**
   * Send a message to Claude via the backend
   */
  const handleSendMessage = async () => {
    if (!inputMessage.trim() || isLoading) return;

    try {
      // Add user message to chat
      const userMessage = { role: 'user', content: inputMessage };
      const updatedMessages = [...messages, userMessage];
      setMessages(updatedMessages);
      
      // Clear input field
      setInputMessage('');
      
      // Set loading state
      setIsLoading(true);
      setError(null);
      
      // Focus back on the input field
      if (inputRef.current) {
        setTimeout(() => {
          inputRef.current.focus();
        }, 0);
      }
      
      console.log("Sending messages to backend:", updatedMessages);
      console.log("Current agent config:", agentConfig);
      
      // Send message to backend
      const response = await sendMessage(
        updatedMessages,
        agentConfig
      );
      
      console.log("Backend response:", response);
      
      // Process response
      const botMessage = { role: 'assistant', content: response.message };
      setMessages(prev => [...prev, botMessage]);
      
      // Apply any configuration updates
      if (response.config_updates) {
        console.log("Applying config updates:", response.config_updates);
        applyConfigUpdates(response.config_updates);
      }
      
      // Check if knowledge upload should be prompted
      const promptKnowledgeUpload = /\[PROMPT_KNOWLEDGE_UPLOAD\].*?true.*?\[\/PROMPT_KNOWLEDGE_UPLOAD\]/s.test(response.message);
      if (promptKnowledgeUpload) {
        console.log("Should prompt for knowledge upload");
        setShowKnowledgeUpload(true);
      }
      
      // Check if MCP server configuration should be prompted
      const promptMcpServer = /\[PROMPT_MCP_SERVER\].*?true.*?\[\/PROMPT_MCP_SERVER\]/s.test(response.message);
      if (promptMcpServer) {
        console.log("Should prompt for MCP server configuration");
        setShowMcpServerSelection(true);
      }
      
      // Check for knowledge storage preference
      const knowledgeStorageMatch = response.message.match(/\[KNOWLEDGE_STORAGE\]([\s\S]*?)\[\/KNOWLEDGE_STORAGE\]/);
      if (knowledgeStorageMatch) {
        try {
          const storagePreference = JSON.parse(knowledgeStorageMatch[1].trim());
          console.log("Knowledge storage preference:", storagePreference);
          updateKnowledgeStorage(storagePreference);
        } catch (err) {
          console.error("Error parsing knowledge storage preference:", err);
        }
      }
      
      // Check if YAML should be generated
      if (response.generate_yaml) {
        console.log("Should generate YAML");
        setShowYamlButton(true);
        
        try {
          // Try to get YAML from backend
          const yaml = await fetchYaml(agentConfig);
          setYamlContent(yaml);
        } catch (yamlError) {
          // Fallback to local generation
          console.warn('Error fetching YAML from backend, using local generation:', yamlError);
          const localYaml = localGenerateYaml(agentConfig);
          setYamlContent(localYaml);
        }
      }
    } catch (err) {
      console.error('Error in chat:', err);
      setError(`Error communicating with Claude: ${err.message}`);
      
      // Add error message to chat
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `Sorry, I encountered an error processing your request: ${err.message}. Please try again.`
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  /**
   * Handle key press event (Enter to send)
   */
  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return {
    inputMessage,
    setInputMessage,
    handleSendMessage,
    handleKeyPress,
    isLoading,
    error,
    messagesEndRef,
    showYamlButton,
    yamlContent,
    inputRef
  };
};

export default useChat;