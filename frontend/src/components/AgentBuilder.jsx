import React, { useEffect } from 'react';
import ChatPanel from './ChatPanel';
import ConfigPanel from './ConfigPanel';
import { useAgent } from '../context/AgentContext';
import { checkHealth } from '../services/api';
import '../styles/components.css';

/**
 * Main component for the Agent Builder application
 * Combines the chat panel and configuration panel in a split view
 */
const AgentBuilder = () => {
  const { setIsLoading } = useAgent();

  // Check API health on component mount
  useEffect(() => {
    const verifyApiConnection = async () => {
      try {
        setIsLoading(true);
        await checkHealth();
      } catch (error) {
        console.error('Failed to connect to API:', error);
        alert('Could not connect to API server. Please ensure the backend is running.');
      } finally {
        setIsLoading(false);
      }
    };

    verifyApiConnection();
  }, [setIsLoading]);

  return (
    <div className="agent-builder-container">
      {/* Left panel - Chat */}
      <ChatPanel />
      
      {/* Right panel - Configuration */}
      <ConfigPanel />
    </div>
  );
};

export default AgentBuilder;