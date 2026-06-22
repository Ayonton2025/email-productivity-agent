import React, { useState, useEffect } from 'react';
import { X, Mail, Key, AlertCircle, CheckCircle, LogIn } from 'lucide-react';
import { useEmailAccounts } from '../../context/EmailAccountsContext';
import { useAuth } from '../../context/AuthContext';

const ConnectOutlookModal = ({ isOpen, onClose }) => {
  const { connectAccount } = useEmailAccounts();
  const { isAuthenticated, user } = useAuth();
  const [connectionMode, setConnectionMode] = useState('oauth'); // 'oauth' or 'manual'
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    app_password: ''
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // Auto-initiate OAuth flow if user is authenticated
  useEffect(() => {
    if (isOpen && isAuthenticated && user?.email) {
      handleOAuthConnect();
    }
  }, [isOpen, isAuthenticated, user?.email]);

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
    setError('');
    setSuccess('');
  };

  const handleOAuthConnect = async () => {
    setLoading(true);
    setError('');
    
    try {
      // Get OAuth URL from backend (respect VITE_API_URL)
      const apiBaseUrl = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';
      const response = await fetch(`${apiBaseUrl}/api/v1/oauth/microsoft/auth-url`);
      const data = await response.json();
      
      if (data.auth_url) {
        // Redirect to Microsoft OAuth
        window.location.href = data.auth_url;
      } else {
        setError('Failed to get OAuth URL from backend');
      }
    } catch (err) {
      setError(`OAuth connection failed: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleManualConnect = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const result = await connectAccount({
        provider: 'outlook',
        email: formData.email,
        password: formData.app_password || formData.password,
        connection_type: 'smtp' // Use SMTP/IMAP instead of OAuth
      });
      
      if (result.success) {
        setSuccess('Outlook account connected successfully!');
        setTimeout(() => {
          onClose();
          setFormData({ email: '', password: '', app_password: '' });
          setSuccess('');
          setConnectionMode('oauth');
        }, 2000);
      } else {
        setError(result.error);
      }
    } catch (err) {
      setError(`Connection failed: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-lg max-w-md w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
              <Mail className="h-6 w-6 text-blue-600" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-gray-900">Connect Outlook</h2>
              <p className="text-sm text-gray-600">Add your Outlook to Bylix Email</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6">
          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-md flex items-center gap-2">
              <AlertCircle className="h-4 w-4 text-red-500" />
              <span className="text-sm text-red-700">{error}</span>
            </div>
          )}

          {success && (
            <div className="mb-4 p-3 bg-green-50 border border-green-200 rounded-md flex items-center gap-2">
              <CheckCircle className="h-4 w-4 text-green-500" />
              <span className="text-sm text-green-700">{success}</span>
            </div>
          )}

          {/* Connection Mode Toggle */}
          {!isAuthenticated && (
            <div className="mb-4 flex gap-2">
              <button
                onClick={() => setConnectionMode('oauth')}
                className={`flex-1 py-2 px-3 rounded-lg text-sm font-medium transition-colors ${
                  connectionMode === 'oauth'
                    ? 'bg-blue-100 text-blue-700 border border-blue-300'
                    : 'bg-gray-100 text-gray-700 border border-gray-300 hover:bg-gray-200'
                }`}
              >
                <LogIn className="h-4 w-4 inline mr-1" /> OAuth
              </button>
              <button
                onClick={() => setConnectionMode('manual')}
                className={`flex-1 py-2 px-3 rounded-lg text-sm font-medium transition-colors ${
                  connectionMode === 'manual'
                    ? 'bg-blue-100 text-blue-700 border border-blue-300'
                    : 'bg-gray-100 text-gray-700 border border-gray-300 hover:bg-gray-200'
                }`}
              >
                <Key className="h-4 w-4 inline mr-1" /> Manual
              </button>
            </div>
          )}

          {/* OAuth Mode */}
          {connectionMode === 'oauth' && (
            <>
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
                <div className="flex items-start gap-2">
                  <LogIn className="h-4 w-4 text-blue-600 mt-0.5 flex-shrink-0" />
                  <div>
                    <p className="text-sm font-medium text-blue-900">
                      {isAuthenticated 
                        ? `Connect as ${user?.email}` 
                        : 'Sign in with your Microsoft account'}
                    </p>
                    <p className="text-xs text-blue-700 mt-1">
                      We'll securely access your Outlook using OAuth 2.0
                    </p>
                  </div>
                </div>
              </div>

              <div className="flex gap-2 pt-4">
                <button
                  type="button"
                  onClick={onClose}
                  className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleOAuthConnect}
                  disabled={loading}
                  className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center justify-center gap-2"
                >
                  {loading ? 'Connecting...' : 'Connect with Microsoft'}
                </button>
              </div>
            </>
          )}

          {/* Manual Mode */}
          {connectionMode === 'manual' && (
            <form onSubmit={handleManualConnect} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Outlook Email
                </label>
                <input
                  type="email"
                  name="email"
                  value={formData.email}
                  onChange={handleChange}
                  required
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  placeholder="your.email@outlook.com"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  App Password
                </label>
                <input
                  type="password"
                  name="app_password"
                  value={formData.app_password}
                  onChange={handleChange}
                  required
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  placeholder="Enter your Outlook app password"
                />
                <p className="mt-1 text-xs text-gray-500">
                  Generate an App Password in your Outlook security settings
                </p>
              </div>

              <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                <div className="flex items-center gap-2 mb-2">
                  <AlertCircle className="h-4 w-4 text-yellow-600" />
                  <span className="text-sm font-medium text-yellow-800">Note</span>
                </div>
                <p className="text-xs text-yellow-700">
                  We recommend using OAuth (above) for better security. Only use App Passwords if OAuth is not available.
                </p>
              </div>

              <div className="flex gap-2 pt-4">
                <button
                  type="button"
                  onClick={onClose}
                  className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={loading}
                  className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
                >
                  {loading ? 'Connecting...' : 'Connect Outlook'}
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
};

export default ConnectOutlookModal;
