import React, { createContext, useState, useContext, useEffect } from 'react';
import { emailApi } from '../services/api';
import { useAuth } from './AuthContext';

const EmailAccountsContext = createContext();

export const useEmailAccounts = () => {
  const context = useContext(EmailAccountsContext);
  if (!context) {
    throw new Error('useEmailAccounts must be used within an EmailAccountsProvider');
  }
  return context;
};

export const EmailAccountsProvider = ({ children }) => {
  const [accounts, setAccounts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [syncing, setSyncing] = useState({});
  const [error, setError] = useState(null);
  const { isAuthenticated } = useAuth();

  const loadAccounts = async () => {
    if (!isAuthenticated) return;
    setLoading(true);
    setError(null);
    try {
      const response = await emailApi.getAccounts();
      console.log('✅ Loaded email accounts:', response.data);
      setAccounts(response.data?.accounts || []);
    } catch (error) {
      console.error('❌ Failed to load email accounts:', error);
      setError(error.message);
      setAccounts([]);
    } finally {
      setLoading(false);
    }
  };

  // Load accounts on auth change
  useEffect(() => {
    if (isAuthenticated) {
      loadAccounts();
    } else {
      setAccounts([]);
    }
  }, [isAuthenticated]);

  const testConnection = async (credentials) => {
    try {
      const response = await emailApi.testConnection(credentials);
      return { success: true, data: response.data };
    } catch (error) {
      return { 
        success: false, 
        error: error.response?.data?.message || 'Connection test failed' 
      };
    }
  };

  const connectAccount = async (credentials) => {
    try {
      const response = await emailApi.connectAccount(credentials);
      await loadAccounts(); // Reload accounts
      return { success: true, data: response.data };
    } catch (error) {
      return { 
        success: false, 
        error: error.response?.data?.detail || error.response?.data?.message || 'Failed to connect account' 
      };
    }
  };

  const disconnectAccount = async (accountId) => {
    try {
      await emailApi.disconnectAccount(accountId);
      await loadAccounts(); // Reload accounts
      return { success: true };
    } catch (error) {
      return { 
        success: false, 
        error: error.response?.data?.detail || error.response?.data?.message || 'Failed to disconnect account' 
      };
    }
  };

  const syncAccount = async (accountId) => {
    setSyncing(prev => ({ ...prev, [accountId]: true }));
    try {
      const response = await emailApi.syncEmails(accountId);
      await loadAccounts(); // Reload to update sync status
      return { success: true, data: response.data };
    } catch (error) {
      return { 
        success: false, 
        error: error.response?.data?.detail || error.response?.data?.message || 'Sync failed' 
      };
    } finally {
      setSyncing(prev => ({ ...prev, [accountId]: false }));
    }
  };

  const value = {
    emailAccounts: accounts,
    loading,
    error,
    syncing,
    loadEmailAccounts: loadAccounts,
    testConnection,
    connectAccount,
    disconnectAccount,
    syncAccount,
  };

  return (
    <EmailAccountsContext.Provider value={value}>
      {children}
    </EmailAccountsContext.Provider>
  );
};

export { EmailAccountsContext };
