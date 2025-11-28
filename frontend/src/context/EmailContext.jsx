import React, { createContext, useState, useContext, useEffect } from 'react';
import { emailApi } from '../services/api';
import { useAuth } from './AuthContext';

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

  // REMOVED: Hardcoded mockEmails array - we'll use backend data only

  const loadEmails = async () => {
    setLoading(true);
    setError(null);
    try {
      if (isAuthenticated) {
        // Load real emails from backend
        const response = await emailApi.getUserInbox(filters);
        console.log('📧 [EmailContext] Loaded emails from backend:', {
          count: response.data?.length,
          ids: response.data?.map(e => e.id)
        });
        setEmails(response.data || []);
      } else {
        // For unauthenticated users, load mock data from backend
        const response = await emailApi.loadMockEmails();
        console.log('📧 [EmailContext] Loaded mock emails from backend:', {
          count: response.data?.emails?.length,
          ids: response.data?.emails?.map(e => e.id)
        });
        setEmails(response.data?.emails || []);
      }
    } catch (err) {
      console.error('❌ [EmailContext] Error loading emails:', err);
      setError('Failed to load emails');
      setEmails([]); // Set empty array instead of hardcoded mocks
    } finally {
      setLoading(false);
    }
  };

  const loadMockEmails = async () => {
    setLoading(true);
    setError(null);
    try {
      console.log('📧 [EmailContext] Loading mock emails from backend...');
      const response = await emailApi.loadMockEmails();
      console.log('✅ [EmailContext] Mock emails loaded:', {
        count: response.data?.emails?.length,
        ids: response.data?.emails?.map(e => e.id)
      });
      setEmails(response.data?.emails || []);
    } catch (err) {
      console.error('❌ [EmailContext] Failed to load mock emails:', err);
      setError('Failed to load mock emails');
      setEmails([]); // Set empty array on error
    } finally {
      setLoading(false);
    }
  };

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
        await emailApi.updateEmailCategory(emailId, category);
      }
      
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

  const filteredEmails = emails.filter(email => {
    const matchesCategory = filters.category === 'all' || email.category === filters.category;
    const matchesSearch = 
      email.subject.toLowerCase().includes(filters.search.toLowerCase()) ||
      email.sender.toLowerCase().includes(filters.search.toLowerCase()) ||
      email.body.toLowerCase().includes(filters.search.toLowerCase());
    
    return matchesCategory && matchesSearch;
  });

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

  // Debug effect to log email IDs
  useEffect(() => {
    if (emails.length > 0) {
      console.log('🔍 [EmailContext] Current email IDs:', emails.map(e => ({
        id: e.id,
        subject: e.subject,
        isUUID: e.id && e.id.length > 10
      })));
    }
  }, [emails]);

  useEffect(() => {
    loadEmails();
  }, [isAuthenticated]);

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
    setEmails,
  };

  return (
    <EmailContext.Provider value={value}>
      {children}
    </EmailContext.Provider>
  );
};

export { EmailContext };
