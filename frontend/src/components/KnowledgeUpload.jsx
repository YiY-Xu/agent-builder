import React, { useState, useRef, useEffect } from 'react';
import { Upload, X, FileText, RefreshCw, PlusCircle, Trash2, Database, HardDrive, Cloud } from 'lucide-react';
import { useAgent } from '../context/AgentContext';
import { uploadFile, getFiles, createIndex, removeFile } from '../services/api';
import { sanitizeAgentName } from '../utils/helpers';
import '../styles/components.css';

/**
 * Component for uploading knowledge documents to an agent
 */
const KnowledgeUpload = () => {
  const { 
    agentConfig, 
    updateKnowledgeBase,
    updateKnowledgeStorage,
    setShowKnowledgeUpload
  } = useAgent();
  
  const [files, setFiles] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [creatingIndex, setCreatingIndex] = useState(false);
  const [savingLocal, setSavingLocal] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);
  const [hasIndex, setHasIndex] = useState(false);
  
  const fileInputRef = useRef(null);
  
  // Load existing files when component mounts
  useEffect(() => {
    if (agentConfig.name) {
      loadFiles();
    }
  }, [agentConfig.name]);
  
  // Load files from backend
  const loadFiles = async () => {
    try {
      setError(null);
      
      const result = await getFiles(agentConfig.name);
      setFiles(result.files || []);
      setHasIndex(result.has_index || false);
      
      if (result.has_index) {
        // Create a sanitized version of the agent name for index_info consistency
        const sanitizedName = sanitizeAgentName(agentConfig.name);
        
        // Update agent configuration with knowledge base info
        updateKnowledgeBase({
          storage_type: result.storage_type,
          index_info: result.index_info,
          project_name: result.project_name,
          local_path: result.local_path,
          document_count: result.files.length,
          file_names: result.files,
          sanitized_name: sanitizedName
        });
      }
    } catch (err) {
      console.error('Error loading files:', err);
      setError(`Error loading files: ${err.message}`);
    }
  };
  
  // Handle file selection
  const handleFileSelect = async (event) => {
    const file = event.target.files[0];
    if (!file) return;
    
    // Check if agent has a name first
    if (!agentConfig.name || agentConfig.name.trim() === '') {
      setError('Please name your agent before uploading documents.');
      // Clear the input value
      event.target.value = '';
      return;
    }
    
    try {
      setUploading(true);
      setError(null);
      
      // Sanitize the agent name for consistency with backend
      const sanitizedName = sanitizeAgentName(agentConfig.name);
      
      // Create form data
      const formData = new FormData();
      formData.append('file', file);
      formData.append('agent_name', sanitizedName); // Use sanitized name
      
      // Upload file
      const result = await uploadFile(formData);
      
      if (result.success) {
        // Reload files
        await loadFiles();
      } else {
        setError(result.error || 'Failed to upload file');
      }
    } catch (err) {
      console.error('Error uploading file:', err);
      setError(`Error uploading file: ${err.message}`);
    } finally {
      setUploading(false);
      // Clear the input value so the same file can be selected again
      event.target.value = '';
    }
  };
  
  // Handle file removal
  const handleRemoveFile = async (fileName) => {
    try {
      setError(null);
      
      // Remove file
      const result = await removeFile(agentConfig.name, fileName);
      
      if (result.success) {
        // Reload files
        await loadFiles();
      } else {
        setError(result.error || 'Failed to remove file');
      }
    } catch (err) {
      console.error('Error removing file:', err);
      setError(`Error removing file: ${err.message}`);
    }
  };
  
  // Trigger file input click
  const triggerFileUpload = () => {
    fileInputRef.current?.click();
  };
  
  // Handle creating local index
  const handleCreateLocalIndex = async () => {
    if (files.length === 0) {
      setError('Please upload at least one file before saving');
      return;
    }
    
    try {
      setError(null);
      setSavingLocal(true);
      
      // Create a sanitized version of the agent name
      const sanitizedName = sanitizeAgentName(agentConfig.name);
      
      // Set storage type to local
      updateKnowledgeStorage({
        type: 'local'
      });
      
      // Save files to local storage
      const result = await createIndex(agentConfig.name, 'local');
      
      if (result.success) {
        console.log("Local index creation success:", result);
        
        // NEVER create dummy index_info, only use what the backend provides
        if (!result.index_info) {
          console.error("Backend did not return index_info in successful response", result);
          setError('Backend did not return a valid index_info. Please try again or contact support.');
          return;
        }
        
        console.log(`Using backend-provided index_info: ${result.index_info}`);
        
        // Update knowledge base info
        updateKnowledgeBase({
          storage_type: 'local',
          local_path: result.local_path,
          index_info: result.index_info,
          document_count: result.document_count,
          file_names: result.file_names,
          sanitized_name: sanitizedName
        });
        
        setSuccess(true);
        setHasIndex(true);
        
        // Hide the upload form after a successful save
        setTimeout(() => {
          setShowKnowledgeUpload(false);
        }, 3000);
      } else {
        setError(result.error || 'Failed to save to local storage');
      }
    } catch (err) {
      console.error('Error saving to local storage:', err);
      setError(`Error saving to local storage: ${err.message}`);
    } finally {
      setSavingLocal(false);
    }
  };
  
  // Handle creating LlamaCloud index
  const handleCreateLlamaIndex = async () => {
    if (files.length === 0) {
      setError('Please upload at least one file before creating an index');
      return;
    }
    
    try {
      setError(null);
      setCreatingIndex(true);
      
      // Create a sanitized version of the agent name
      const sanitizedName = sanitizeAgentName(agentConfig.name);
      
      // Set storage type to LlamaCloud
      updateKnowledgeStorage({
        type: 'llamacloud'
      });
      
      // Create index
      const result = await createIndex(agentConfig.name, 'llamacloud');
      
      if (result.success) {
        console.log("LlamaCloud index creation success:", result);
        
        // NEVER create dummy index_info, only use what the backend provides
        if (!result.index_info) {
          console.error("Backend did not return index_info in successful response", result);
          setError('Backend did not return a valid index_info. Please try again or contact support.');
          return;
        }
        
        console.log(`Using backend-provided index_info: ${result.index_info}`);
        
        // Update agent configuration with knowledge base info
        updateKnowledgeBase({
          storage_type: 'llamacloud',
          index_info: result.index_info,
          project_name: result.project_name,
          document_count: result.document_count,
          file_names: result.file_names,
          sanitized_name: sanitizedName
        });
        setSuccess(true);
        setHasIndex(true);
        
        // Hide the upload form after a successful upload
        setTimeout(() => {
          setShowKnowledgeUpload(false);
        }, 3000);
      } else {
        setError(result.error || 'LlamaIndex will be supported soon!');
      }
    } catch (err) {
      console.error('Error creating index:', err);
      setError(`Error creating index: ${err.message}`);
    } finally {
      setCreatingIndex(false);
    }
  };
  
  // Cancel upload
  const handleCancel = () => {
    setError(null);
    setShowKnowledgeUpload(false);
  };
  
  // Format file name (truncate if too long)
  const formatFileName = (fileName) => {
    if (fileName.length <= 30) return fileName;
    const ext = fileName.split('.').pop();
    const name = fileName.substring(0, fileName.length - ext.length - 1);
    return `${name.substring(0, 25)}...${ext}`;
  };

  return (
    <div className="knowledge-upload-container">
      <div className="knowledge-upload-header">
        <h3>Upload Knowledge Documents</h3>
        <button 
          className="close-button"
          onClick={handleCancel}
          disabled={uploading || creatingIndex || savingLocal}
        >
          <X size={18} />
        </button>
      </div>
      
      {success ? (
        <div className="upload-success">
          <p>Documents successfully processed! Your agent now has access to this knowledge.</p>
        </div>
      ) : (
        <>
          {!hasIndex && (
            <div className="file-drop-area">
              <div className="file-drop-content">
                <FileText size={48} />
                <p>Upload files one by one</p>
                <button 
                  className="select-files-button"
                  onClick={triggerFileUpload}
                  disabled={uploading}
                >
                  {uploading ? 'Uploading...' : 'Select File'}
                  {!uploading && <PlusCircle size={16} className="ml-2" />}
                </button>
                <input 
                  type="file" 
                  ref={fileInputRef}
                  onChange={handleFileSelect}
                  style={{ display: 'none' }}
                  disabled={uploading}
                />
                <p className="file-types">PDF, TXT, DOCX, etc.</p>
              </div>
            </div>
          )}
          
          {files.length > 0 && (
            <div className="selected-files-container">
              <div className="selected-files-header">
                <h4>Uploaded Files ({files.length})</h4>
                {!hasIndex && (
                  <button 
                    className="refresh-button"
                    onClick={loadFiles}
                    disabled={uploading}
                  >
                    <RefreshCw size={16} />
                  </button>
                )}
              </div>
              
              <ul className="selected-files-list">
                {files.map((fileName, index) => (
                  <li key={index} className="selected-file">
                    <div className="file-info">
                      <span className="file-name" title={fileName}>
                        {formatFileName(fileName)}
                      </span>
                    </div>
                    {!hasIndex && (
                      <button 
                        className="remove-file-button"
                        onClick={() => handleRemoveFile(fileName)}
                        disabled={uploading || creatingIndex || savingLocal}
                        title="Remove file"
                      >
                        <Trash2 size={16} />
                      </button>
                    )}
                  </li>
                ))}
              </ul>
              
              {!hasIndex && (
                <>
                  <div className="storage-options">
                    <h4>Choose Knowledge Storage Option:</h4>
                    <div className="storage-description">
                      <p>Select how you want your agent to access these documents:</p>
                    </div>
                  </div>
                  
                  <div className="knowledge-buttons">
                    <button 
                      className="create-local-index-button"
                      onClick={handleCreateLocalIndex}
                      disabled={savingLocal || creatingIndex || files.length === 0}
                    >
                      <HardDrive size={16} />
                      {savingLocal ? 'Creating...' : 'Create Local Index'}
                    </button>
                    
                    <button 
                      className="create-llamacloud-index-button"
                      onClick={handleCreateLlamaIndex}
                      disabled={creatingIndex || savingLocal || files.length === 0}
                    >
                      <Cloud size={16} />
                      {creatingIndex ? 'Creating Index...' : 'Create LlamaCloud Index'}
                    </button>
                  </div>
                  
                  <div className="cancel-button-container">
                    <button 
                      className="cancel-button"
                      onClick={handleCancel}
                      disabled={uploading || creatingIndex || savingLocal}
                    >
                      Cancel
                    </button>
                  </div>
                </>
              )}
            </div>
          )}
          
          {hasIndex && (
            <div className="index-info">
              <p>An index has already been created for this agent with {files.length} documents.</p>
              <button 
                className="close-button-primary"
                onClick={handleCancel}
              >
                Close
              </button>
            </div>
          )}
          
          {error && (
            <div className="error-message">
              {error}
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default KnowledgeUpload;