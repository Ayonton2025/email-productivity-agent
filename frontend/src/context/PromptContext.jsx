import React, { createContext, useState, useContext } from 'react';
import { useAuth } from './AuthContext';

const PromptContext = createContext();

export const usePrompt = () => {
  const context = useContext(PromptContext);
  if (!context) {
    throw new Error('usePrompt must be used within a PromptProvider');
  }
  return context;
};

export const PromptProvider = ({ children }) => {
  const [prompts, setPrompts] = useState([]);
  const [loading, setLoading] = useState(false);
  const { token } = useAuth();

  const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v1';

  // Fetch prompts from API
  const fetchPrompts = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/prompts/my`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        throw new Error('Failed to fetch prompts');
      }

      const data = await response.json();
      setPrompts(data);
      return data;
    } catch (error) {
      console.error('Error fetching prompts:', error);
      throw error;
    } finally {
      setLoading(false);
    }
  };

  const createPrompt = async (promptData) => {
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/prompts`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(promptData)
      });

      if (!response.ok) {
        throw new Error('Failed to create prompt');
      }

      const newPrompt = await response.json();
      setPrompts(prev => [newPrompt, ...prev]);
      return newPrompt;
    } catch (error) {
      console.error('Error creating prompt:', error);
      throw error;
    } finally {
      setLoading(false);
    }
  };

  const updatePrompt = async (promptId, promptData) => {
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/prompts/${promptId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(promptData)
      });

      if (!response.ok) {
        throw new Error('Failed to update prompt');
      }

      const updatedPrompt = await response.json();
      setPrompts(prev => prev.map(prompt => 
        prompt.id === promptId ? updatedPrompt : prompt
      ));
      return updatedPrompt;
    } catch (error) {
      console.error('Error updating prompt:', error);
      throw error;
    } finally {
      setLoading(false);
    }
  };

  const deletePrompt = async (promptId) => {
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/prompts/${promptId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (!response.ok) {
        throw new Error('Failed to delete prompt');
      }

      setPrompts(prev => prev.filter(prompt => prompt.id !== promptId));
      return { success: true };
    } catch (error) {
      console.error('Error deleting prompt:', error);
      throw error;
    } finally {
      setLoading(false);
    }
  };

  const testPrompt = async (promptId, emailContent) => {
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/prompts/${promptId}/test`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ email_content: emailContent })
      });

      if (!response.ok) {
        throw new Error('Failed to test prompt');
      }

      const result = await response.json();
      return result;
    } catch (error) {
      console.error('Error testing prompt:', error);
      throw error;
    } finally {
      setLoading(false);
    }
  };

  // Initialize with API data
  React.useEffect(() => {
    if (token) {
      fetchPrompts();
    }
  }, [token]);

  const value = {
    prompts,
    loading,
    createPrompt,
    updatePrompt,
    deletePrompt,
    testPrompt,
    refreshPrompts: fetchPrompts
  };

  return (
    <PromptContext.Provider value={value}>
      {children}
    </PromptContext.Provider>
  );
};

export { PromptContext };
