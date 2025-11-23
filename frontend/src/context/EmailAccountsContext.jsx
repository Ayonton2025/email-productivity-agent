import React, { createContext, useState, useContext } from 'react';
import { emailAccountsApi } from '../services/api';

const EmailAccountsContext = createContext();

export const useEmailAccounts = () => {
  const context = useContext(EmailAccountsContext);
  if (!context) {
    throw new Error('useEmailAccounts must be used within an EmailAccountsProvider');
  }
  return context;
};

export const EmailAccountsProvider = ({ children }) => {
  const [emailAccounts, setEmailAccounts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [syncing, setSyncing] = useState({});

  const loadEmailAccounts = async () => {
    setLoading(true);
    try {
      const response = await emailAccountsApi.getEmailAccounts();
      setEmailAccounts(response.data);
    } catch (error) {
      console.error('Failed to load email accounts:', error);
    } finally {
      setLoading(false);
    }
  };

  const connectGmail = async (authData) => {
    try {
      const response = await emailAccountsApi.connectGmail(authData);
      await loadEmailAccounts(); // Reload accounts
      return { success: true, data: response.data };
    } catch (error) {
      return { 
        success: false, 
        error: error.response?.data?.detail || 'Failed to connect Gmail' 
      };
    }
  };

  const connectOutlook = async (authData) => {
    try {
      const response = await emailAccountsApi.connectOutlook(authData);
      await loadEmailAccounts(); // Reload accounts
      return { success: true, data: response.data };
    } catch (error) {
      return { 
        success: false, 
        error: error.response?.data?.detail || 'Failed to connect Outlook' 
      };
    }
  };

  const disconnectAccount = async (accountId) => {
    try {
      await emailAccountsApi.disconnectAccount(accountId);
      await loadEmailAccounts(); // Reload accounts
      return { success: true };
    } catch (error) {
      return { 
        success: false, 
        error: error.response?.data?.detail || 'Failed to disconnect account' 
      };
    }
  };

  const syncAccount = async (accountId) => {
    setSyncing(prev => ({ ...prev, [accountId]: true }));
    try {
      const response = await emailAccountsApi.syncAccount(accountId);
      await loadEmailAccounts(); // Reload accounts to get updated last_sync
      return { success: true, data: response.data };
    } catch (error) {
      return { 
        success: false, 
        error: error.response?.data?.detail || 'Sync failed' 
      };
    } finally {
      setSyncing(prev => ({ ...prev, [accountId]: false }));
    }
  };

  const value = {
    emailAccounts,
    loading,
    syncing,
    loadEmailAccounts,
    connectGmail,
    connectOutlook,
    disconnectAccount,
    syncAccount,
  };

  return (
    <EmailAccountsContext.Provider value={value}>
      {children}
    </EmailAccountsContext.Provider>
  );
};