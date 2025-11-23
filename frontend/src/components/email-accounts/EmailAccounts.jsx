import React, { useState, useEffect } from 'react';
import { 
  Mail, 
  Plus, 
  RefreshCw, 
  Trash2, 
  CheckCircle, 
  XCircle, 
  Clock,
  ExternalLink,
  AlertCircle
} from 'lucide-react';
import { useEmailAccounts } from '../../context/EmailAccountsContext';
import ConnectGmailModal from './ConnectGmailModal';
import ConnectOutlookModal from './ConnectOutlookModal';

const EmailAccounts = () => {
  const { 
    emailAccounts, 
    loading, 
    syncing, 
    loadEmailAccounts, 
    disconnectAccount,
    syncAccount 
  } = useEmailAccounts();
  
  const [showGmailModal, setShowGmailModal] = useState(false);
  const [showOutlookModal, setShowOutlookModal] = useState(false);

  useEffect(() => {
    loadEmailAccounts();
  }, []);

  const handleDisconnect = async (accountId) => {
    if (window.confirm('Are you sure you want to disconnect this email account?')) {
      const result = await disconnectAccount(accountId);
      if (!result.success) {
        alert(result.error);
      }
    }
  };

  const handleSync = async (accountId) => {
    const result = await syncAccount(accountId);
    if (!result.success) {
      alert(result.error);
    }
  };

  const getProviderIcon = (provider) => {
    switch (provider) {
      case 'gmail':
        return <Mail className="h-5 w-5 text-red-500" />;
      case 'outlook':
        return <Mail className="h-5 w-5 text-blue-500" />;
      default:
        return <Mail className="h-5 w-5 text-gray-500" />;
    }
  };

  const getProviderColor = (provider) => {
    switch (provider) {
      case 'gmail':
        return 'bg-red-100 text-red-800 border-red-200';
      case 'outlook':
        return 'bg-blue-100 text-blue-800 border-blue-200';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'Never';
    return new Date(dateString).toLocaleString();
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Email Accounts</h1>
          <p className="text-gray-600">Manage your connected email accounts</p>
        </div>
        
        <div className="flex gap-2">
          <button
            onClick={() => setShowGmailModal(true)}
            className="inline-flex items-center px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
          >
            <Mail className="h-4 w-4 mr-2" />
            Connect Gmail
          </button>
          
          <button
            onClick={() => setShowOutlookModal(true)}
            className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            <Mail className="h-4 w-4 mr-2" />
            Connect Outlook
          </button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <div className="text-2xl font-bold text-gray-900">{emailAccounts.length}</div>
          <div className="text-sm text-gray-600">Connected Accounts</div>
        </div>
        
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <div className="text-2xl font-bold text-green-600">
            {emailAccounts.filter(acc => acc.is_active).length}
          </div>
          <div className="text-sm text-gray-600">Active Accounts</div>
        </div>
        
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <div className="text-2xl font-bold text-blue-600">
            {emailAccounts.filter(acc => acc.last_sync).length}
          </div>
          <div className="text-sm text-gray-600">Synced Accounts</div>
        </div>
      </div>

      {/* Accounts List */}
      <div className="bg-white rounded-lg border border-gray-200">
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <RefreshCw className="h-8 w-8 animate-spin text-gray-400" />
          </div>
        ) : emailAccounts.length === 0 ? (
          <div className="text-center py-12 text-gray-500">
            <Mail className="h-12 w-12 mx-auto mb-4 text-gray-300" />
            <p className="text-lg font-medium text-gray-900 mb-2">No email accounts connected</p>
            <p className="text-gray-600 mb-6">
              Connect your email accounts to start using InboxAI with your real emails
            </p>
            <div className="flex gap-3 justify-center">
              <button
                onClick={() => setShowGmailModal(true)}
                className="inline-flex items-center px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
              >
                <Mail className="h-4 w-4 mr-2" />
                Connect Gmail
              </button>
              <button
                onClick={() => setShowOutlookModal(true)}
                className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                <Mail className="h-4 w-4 mr-2" />
                Connect Outlook
              </button>
            </div>
          </div>
        ) : (
          <div className="divide-y divide-gray-200">
            {emailAccounts.map((account) => (
              <div key={account.id} className="p-6">
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-center gap-3">
                    {getProviderIcon(account.provider)}
                    <div>
                      <h3 className="font-semibold text-gray-900">{account.email}</h3>
                      <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium border ${getProviderColor(account.provider)}`}>
                        {account.provider.charAt(0).toUpperCase() + account.provider.slice(1)}
                      </span>
                    </div>
                  </div>
                  
                  <div className="flex items-center gap-2">
                    {account.is_active ? (
                      <CheckCircle className="h-5 w-5 text-green-500" />
                    ) : (
                      <XCircle className="h-5 w-5 text-red-500" />
                    )}
                    
                    {account.is_primary && (
                      <span className="inline-flex items-center px-2 py-1 rounded-full bg-purple-100 text-purple-800 text-xs font-medium">
                        Primary
                      </span>
                    )}
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4 text-sm text-gray-600">
                  <div className="flex items-center gap-2">
                    <Clock className="h-4 w-4" />
                    <span>Last sync: {formatDate(account.last_sync)}</span>
                  </div>
                  
                  <div className="flex items-center gap-2">
                    <span>Status: </span>
                    {account.sync_enabled ? (
                      <span className="text-green-600">Sync enabled</span>
                    ) : (
                      <span className="text-gray-500">Sync disabled</span>
                    )}
                  </div>
                </div>

                <div className="flex gap-2">
                  <button
                    onClick={() => handleSync(account.id)}
                    disabled={syncing[account.id]}
                    className="inline-flex items-center px-3 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 disabled:opacity-50"
                  >
                    <RefreshCw className={`h-4 w-4 mr-2 ${syncing[account.id] ? 'animate-spin' : ''}`} />
                    {syncing[account.id] ? 'Syncing...' : 'Sync Now'}
                  </button>
                  
                  <button
                    onClick={() => handleDisconnect(account.id)}
                    className="inline-flex items-center px-3 py-2 border border-red-300 text-red-700 rounded-lg hover:bg-red-50"
                  >
                    <Trash2 className="h-4 w-4 mr-2" />
                    Disconnect
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Modals */}
      <ConnectGmailModal 
        isOpen={showGmailModal}
        onClose={() => setShowGmailModal(false)}
      />
      
      <ConnectOutlookModal
        isOpen={showOutlookModal}
        onClose={() => setShowOutlookModal(false)}
      />
    </div>
  );
};

export default EmailAccounts;