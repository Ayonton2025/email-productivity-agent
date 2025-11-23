import React, { useState } from 'react';
import { Mail, ExternalLink, CheckCircle, XCircle, RefreshCw } from 'lucide-react';

const ProviderConnection = () => {
  const [activeTab, setActiveTab] = useState('gmail');
  const [isConnecting, setIsConnecting] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState({});

  const providers = [
    {
      id: 'gmail',
      name: 'Gmail',
      description: 'Connect your Gmail account to sync emails',
      icon: '📧',
      status: connectionStatus.gmail || 'disconnected'
    },
    {
      id: 'outlook',
      name: 'Outlook',
      description: 'Connect your Outlook/Microsoft 365 account',
      icon: '📨',
      status: connectionStatus.outlook || 'disconnected'
    }
  ];

  const handleConnect = async (provider) => {
    setIsConnecting(true);
    try {
      // Implementation for OAuth flow
      const response = await fetch(`/api/v1/providers/${provider}/authenticate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ /* credentials */ })
      });
      
      if (response.ok) {
        setConnectionStatus(prev => ({ ...prev, [provider]: 'connected' }));
      }
    } catch (error) {
      console.error('Connection failed:', error);
    } finally {
      setIsConnecting(false);
    }
  };

  const handleSync = async (provider) => {
    try {
      const response = await fetch(`/api/v1/providers/${provider}/sync`, {
        method: 'POST'
      });
      
      if (response.ok) {
        // Refresh email list
        window.location.reload();
      }
    } catch (error) {
      console.error('Sync failed:', error);
    }
  };

  return (
    <div className="provider-connection">
      <div className="connection-header">
        <h2>Connect Email Accounts</h2>
        <p>Sync your real emails for AI-powered management</p>
      </div>

      <div className="providers-grid">
        {providers.map(provider => (
          <div key={provider.id} className="provider-card">
            <div className="provider-header">
              <div className="provider-icon">{provider.icon}</div>
              <div className="provider-info">
                <h3>{provider.name}</h3>
                <p>{provider.description}</p>
              </div>
              <div className={`status-badge status-${provider.status}`}>
                {provider.status === 'connected' ? <CheckCircle size={16} /> : <XCircle size={16} />}
                {provider.status}
              </div>
            </div>
            
            <div className="provider-actions">
              {provider.status === 'connected' ? (
                <button 
                  onClick={() => handleSync(provider.id)}
                  className="btn btn-secondary"
                >
                  <RefreshCw size={16} />
                  Sync Emails
                </button>
              ) : (
                <button 
                  onClick={() => handleConnect(provider.id)}
                  disabled={isConnecting}
                  className="btn btn-primary"
                >
                  {isConnecting ? 'Connecting...' : 'Connect'}
                </button>
              )}
            </div>
          </div>
        ))}
      </div>

      <div className="connection-info">
        <h4>How it works:</h4>
        <ul>
          <li>Connect your email account securely via OAuth</li>
          <li>Emails are processed locally with AI analysis</li>
          <li>Your credentials are never stored on our servers</li>
          <li>You can disconnect at any time</li>
        </ul>
      </div>
    </div>
  );
};

export default ProviderConnection;