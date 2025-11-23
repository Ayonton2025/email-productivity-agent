import React, { createContext, useState, useContext } from 'react';

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

  // Mock prompts data
  const mockPrompts = [
    {
      id: 'prompt-1',
      name: 'Smart Categorization',
      description: 'Intelligently categorize emails into relevant categories',
      template: 'Categorize this email into one of: Important, Newsletter, Spam, To-Do...',
      category: 'categorization',
      version: 1,
      is_active: true,
      is_system: true,
      parameters: {},
      examples: [],
      created_at: '2024-01-08T10:00:00Z',
      updated_at: '2024-01-08T10:00:00Z'
    },
    {
      id: 'prompt-2',
      name: 'Action Item Extractor',
      description: 'Extract specific tasks and action items from emails',
      template: 'Extract all actionable tasks from this email. For each item, identify the task, deadline, and priority...',
      category: 'action_extraction',
      version: 1,
      is_active: true,
      is_system: true,
      parameters: {},
      examples: [],
      created_at: '2024-01-08T10:00:00Z',
      updated_at: '2024-01-08T10:00:00Z'
    },
    {
      id: 'prompt-3',
      name: 'Professional Reply Drafter',
      description: 'Draft professional email responses',
      template: 'Draft a professional email reply based on the original email. Be polite and address all points...',
      category: 'reply_draft',
      version: 1,
      is_active: true,
      is_system: true,
      parameters: {},
      examples: [],
      created_at: '2024-01-08T10:00:00Z',
      updated_at: '2024-01-08T10:00:00Z'
    }
  ];

  const createPrompt = async (promptData) => {
    return new Promise((resolve) => {
      setTimeout(() => {
        const newPrompt = {
          ...promptData,
          id: `prompt-${Date.now()}`,
          version: 1,
          is_system: false,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString()
        };
        setPrompts(prev => [newPrompt, ...prev]);
        resolve(newPrompt);
      }, 500);
    });
  };

  const updatePrompt = async (promptId, promptData) => {
    return new Promise((resolve) => {
      setTimeout(() => {
        setPrompts(prev => prev.map(prompt => 
          prompt.id === promptId 
            ? { ...prompt, ...promptData, version: prompt.version + 1, updated_at: new Date().toISOString() }
            : prompt
        ));
        resolve();
      }, 500);
    });
  };

  const deletePrompt = async (promptId) => {
    return new Promise((resolve) => {
      setTimeout(() => {
        setPrompts(prev => prev.filter(prompt => prompt.id !== promptId));
        resolve();
      }, 500);
    });
  };

  // Initialize with mock data
  React.useEffect(() => {
    setPrompts(mockPrompts);
  }, []);

  const value = {
    prompts,
    createPrompt,
    updatePrompt,
    deletePrompt
  };

  return (
    <PromptContext.Provider value={value}>
      {children}
    </PromptContext.Provider>
  );
};

export { PromptContext };