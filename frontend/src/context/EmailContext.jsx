import React, { createContext, useState, useContext, useEffect } from 'react';
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

  // Email loading is now handled per-account in Inbox component
  const loadEmails = async () => {
    console.log('ℹ️ [EmailContext] Email loading is handled per-account in Inbox component');
    return;
  };

  const syncEmails = async () => {
    console.log('⚠️ [EmailContext] Sync is handled per-account in Inbox component');
    return { success: false, error: 'Use account-specific sync' };
  };

  const updateEmailCategory = async (emailId, category) => {
    console.log('⚠️ [EmailContext] Category update moved to backend AI pipeline');
    setEmails(prev => prev.map(email =>
      email.id === emailId ? { ...email, ai_category: category } : email
    ));
    
    if (selectedEmail && selectedEmail.id === emailId) {
      setSelectedEmail(prev => ({ ...prev, ai_category: category }));
    }
  };

  const filteredEmails = emails.filter(email => {
    const matchesCategory = filters.category === 'all' || email.ai_category === filters.category;
    const matchesSearch = 
      (email.subject?.toLowerCase() || '').includes(filters.search.toLowerCase()) ||
      (email.sender?.toLowerCase() || '').includes(filters.search.toLowerCase()) ||
      (email.body_text?.toLowerCase() || '').includes(filters.search.toLowerCase());
    
    return matchesCategory && matchesSearch;
  });

  const sortedEmails = [...filteredEmails].sort((a, b) => {
    if (filters.sortBy === 'newest') {
      return new Date(b.received_at) - new Date(a.received_at);
    } else if (filters.sortBy === 'oldest') {
      return new Date(a.received_at) - new Date(b.received_at);
    } else if (filters.sortBy === 'sender') {
      return (a.sender || '').localeCompare(b.sender || '');
    }
    return 0;
  });

  const value = {
    emails: sortedEmails,
    selectedEmail,
    setSelectedEmail,
    loading,
    error,
    filters,
    setFilters,
    loadEmails,
    syncEmails,
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
