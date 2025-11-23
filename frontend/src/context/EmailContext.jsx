import React, { createContext, useState, useContext, useEffect } from 'react';
import { emailApi } from '../services/api';
import { useAuth } from './AuthContext';

// Create and export the context
const EmailContext = createContext();

export const useEmail = () => {
  const context = useContext(EmailContext);
  if (!context) {
    throw new Error('useEmail must be used within an EmailProvider');
  }
  return context;
};

export const EmailProvider = ({ children }) => {
  const [emails, setEmails] = useState([]);
  const [selectedEmail, setSelectedEmail] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [filters, setFilters] = useState({
    category: 'all',
    search: '',
    sortBy: 'newest'
  });

  const { isAuthenticated, user } = useAuth();

  // Mock email data for demo (when not authenticated or for testing)
  const mockEmails = [
    {
      id: '1',
      sender: 'project.manager@company.com',
      subject: 'Q4 Project Review Meeting',
      body: 'Hi team, We need to schedule the Q4 project review meeting for next week. Please review the attached project report...',
      timestamp: '2024-01-08T10:30:00Z',
      category: 'Important',
      priority: 'high',
      is_read: false,
      is_archived: false,
      action_items: [
        { task: 'Review project report', deadline: '2024-01-12', priority: 'high' }
      ],
      summary: 'Meeting request for Q4 project review with attached report',
      metadata: {}
    },
    {
      id: '2',
      sender: 'newsletter@techdaily.com',
      subject: 'Tech Daily: AI Trends in 2024',
      body: 'Welcome to this week\'s Tech Daily newsletter! Featured Articles: - The Rise of Multimodal AI Systems...',
      timestamp: '2024-01-08T08:15:00Z',
      category: 'Newsletter',
      priority: 'low',
      is_read: true,
      is_archived: false,
      action_items: [],
      summary: 'Weekly tech newsletter featuring AI trends and developments',
      metadata: { type: 'newsletter' }
    },
    {
      id: '3',
      sender: 'hr@company.com',
      subject: 'ACTION REQUIRED: Benefits Enrollment Deadline',
      body: 'Dear Employee, This is a reminder that the benefits enrollment period closes this Friday...',
      timestamp: '2024-01-08T09:45:00Z',
      category: 'To-Do',
      priority: 'high',
      is_read: false,
      is_archived: false,
      action_items: [
        { task: 'Complete benefits enrollment', deadline: '2024-01-12', priority: 'high' }
      ],
      summary: 'Benefits enrollment reminder with Friday deadline',
      metadata: { action_required: true }
    }
  ];

  // Load user's real emails when authenticated
  const loadEmails = async () => {
    if (!isAuthenticated) {
      setEmails(mockEmails);
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const response = await emailApi.getUserInbox(filters);
      setEmails(response.data);
    } catch (err) {
      console.error('Error loading emails:', err);
      setError('Failed to load emails');
      // Fallback to mock data for demo
      setEmails(mockEmails);
    } finally {
      setLoading(false);
    }
  };

  // Load mock emails for demo purposes
  const loadMockEmails = async () => {
    setLoading(true);
    setError(null);
    try {
      // Simulate API call delay
      await new Promise(resolve => setTimeout(resolve, 500));
      setEmails(mockEmails);
    } catch (err) {
      setError('Failed to load mock emails');
    } finally {
      setLoading(false);
    }
  };

  // Sync real emails from connected accounts
  const syncUserEmails = async () => {
    if (!isAuthenticated) {
      setError('Please sign in to sync emails');
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const response = await emailApi.syncUserEmails();
      await loadEmails(); // Reload emails after sync
      return { success: true, data: response.data };
    } catch (err) {
      const errorMsg = err.response?.data?.detail || 'Failed to sync emails';
      setError(errorMsg);
      return { success: false, error: errorMsg };
    } finally {
      setLoading(false);
    }
  };

  const updateEmailCategory = async (emailId, category) => {
    try {
      if (isAuthenticated) {
        // Update via API for real emails
        await emailApi.updateEmailCategory(emailId, category);
      }
      
      // Update local state
      setEmails(prev => prev.map(email =>
        email.id === emailId ? { ...email, category } : email
      ));
      
      if (selectedEmail && selectedEmail.id === emailId) {
        setSelectedEmail(prev => ({ ...prev, category }));
      }
    } catch (err) {
      console.error('Error updating email category:', err);
      throw err;
    }
  };

  // Filter emails based on current filters
  const filteredEmails = emails.filter(email => {
    const matchesCategory = filters.category === 'all' || email.category === filters.category;
    const matchesSearch = 
      email.subject.toLowerCase().includes(filters.search.toLowerCase()) ||
      email.sender.toLowerCase().includes(filters.search.toLowerCase()) ||
      email.body.toLowerCase().includes(filters.search.toLowerCase());
    
    return matchesCategory && matchesSearch;
  });

  // Sort emails based on current sort
  const sortedEmails = [...filteredEmails].sort((a, b) => {
    if (filters.sortBy === 'newest') {
      return new Date(b.timestamp) - new Date(a.timestamp);
    } else if (filters.sortBy === 'oldest') {
      return new Date(a.timestamp) - new Date(b.timestamp);
    } else if (filters.sortBy === 'sender') {
      return a.sender.localeCompare(b.sender);
    }
    return 0;
  });

  // Load emails when component mounts or authentication changes
  useEffect(() => {
    if (isAuthenticated) {
      loadEmails();
    } else {
      setEmails(mockEmails);
    }
  }, [isAuthenticated]);

  // Reload emails when filters change
  useEffect(() => {
    if (isAuthenticated) {
      loadEmails();
    }
  }, [filters]);

  const value = {
    emails: sortedEmails,
    selectedEmail,
    setSelectedEmail,
    loading,
    error,
    filters,
    setFilters,
    loadEmails,
    loadMockEmails,
    syncUserEmails,
    updateEmailCategory,
    isUsingRealEmails: isAuthenticated,
    userEmail: user?.email,
  };

  return (
    <EmailContext.Provider value={value}>
      {children}
    </EmailContext.Provider>
  );
};

// Export the context for direct consumption
export { EmailContext };