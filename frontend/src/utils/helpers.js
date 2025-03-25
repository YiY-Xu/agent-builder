/**
 * Utility functions for the frontend application
 */

/**
 * Sanitize agent name for consistency with backend
 * This should match the sanitization logic in the backend's sanitize_agent_name function
 * @param {string} name - Original agent name
 * @returns {string} - Sanitized name
 */
export const sanitizeAgentName = (name) => {
  if (!name) return '';
  
  // Replace spaces with hyphens and remove special characters
  let sanitized = name.toLowerCase().replace(/\s+/g, '-');
  sanitized = sanitized.replace(/[^a-z0-9-]/g, '');
  
  // Limit length
  if (sanitized.length > 20) {
    sanitized = sanitized.substring(0, 20);
  }
  
  // Ensure it doesn't start or end with hyphen
  sanitized = sanitized.replace(/^-+|-+$/g, '');
  
  // If empty after sanitization, use default
  if (!sanitized) {
    sanitized = 'agent';
  }
  
  return sanitized;
};

/**
 * Format file size in human-readable format
 * @param {number} bytes - Size in bytes
 * @returns {string} - Formatted size (e.g., "2.5 MB")
 */
export const formatFileSize = (bytes) => {
  if (bytes < 1024) {
    return `${bytes} B`;
  } else if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`;
  } else if (bytes < 1024 * 1024 * 1024) {
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  } else {
    return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`;
  }
}; 