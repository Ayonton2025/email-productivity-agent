import React, { useState, useEffect } from 'react';
import { X, Mail, Lock, AlertCircle, CheckCircle, Loader, LogIn, Key } from 'lucide-react';
import { emailApi } from '../../services/api';
import { useAuth } from '../../context/AuthContext';

const ConnectEmailModal = ({ isOpen, onClose, onSuccess }) => {
  const { isAuthenticated, user } = useAuth();
  const [connectionMode, setConnectionMode] = useState('select'); // select, oauth, manual
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    app_password: '',
    display_name: ''
  });
  const [selectedProvider, setSelectedProvider] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [successMessage, setSuccessMessage] = useState('');

  const handleYahooConnect = () => {
    // Use manual connect flow prefilled for Yahoo
    setSelectedProvider('yahoo');
    setFormData({ ...formData, email: '' });
    setConnectionMode('manual');
  };

  // Auto-show provider selection if authenticated
  useEffect(() => {
    if (isOpen && isAuthenticated) {
      setConnectionMode('select');
    } else if (isOpen && !isAuthenticated) {
      setConnectionMode('manual');
    }
  }, [isOpen, isAuthenticated]);

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
    setError('');
  };

  const handleOAuthConnect = async (provider) => {
    setLoading(true);
    setError('');
    
    try {
      // Use relative URL in development to leverage Vite proxy
      // Only use full URL in production
      let apiBaseUrl = '/api/v1';
      if (import.meta.env.MODE === 'production' && import.meta.env.VITE_API_URL) {
        let url = import.meta.env.VITE_API_URL;
        if (!url.endsWith('/api/v1')) {
          url = url.replace(/\/+$/, '') + '/api/v1';
        }
        apiBaseUrl = url;
      }

      const token = localStorage.getItem('auth_token');
      // Use environment variable for redirect URI, fallback to hardcoded value
      const redirectUri = import.meta.env.VITE_OAUTH_REDIRECT_URI || `${window.location.origin}/oauth/callback`;

      // Get OAuth URL from backend based on provider
      let endpoint;
      if (provider === 'gmail') {
        // Use public endpoint if no token, authenticated endpoint if token exists
        endpoint = token
          ? `${apiBaseUrl}/email-accounts/gmail/auth-url?redirect_uri=${encodeURIComponent(redirectUri)}`
          : `${apiBaseUrl}/email-accounts/gmail/auth-url/public?redirect_uri=${encodeURIComponent(redirectUri)}`;
      } else {
        endpoint = `${apiBaseUrl}/oauth/microsoft/auth-url`;
      }

      const response = await fetch(endpoint, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      const data = await response.json();
      
      if (data.auth_url) {
        // Redirect to OAuth provider
        window.location.href = data.auth_url;
      } else {
        setError(data?.detail || 'Failed to get OAuth URL from backend');
      }
    } catch (err) {
      setError(`OAuth connection failed: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleManualConnect = async (e) => {
    e.preventDefault();
    
    if (!formData.email || !formData.app_password) {
      setError('Please enter both email and password');
      return;
    }

    setLoading(true);
    setError('');
    
    try {
      const response = await emailApi.connectAccount({
        email: formData.email,
        password: formData.app_password,
        display_name: formData.display_name || formData.email,
        connection_type: 'smtp'
      });

      if (response.success) {
        setSuccessMessage('✅ Email account connected successfully!');
        
        setTimeout(() => {
          onClose();
          if (onSuccess) onSuccess(response.data);
          setFormData({
            email: '',
            password: '',
            app_password: '',
            display_name: ''
          });
          setConnectionMode('select');
          setSuccessMessage('');
        }, 2000);
      } else {
        setError(response.message || 'Failed to connect account');
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to connect account');
      console.error('Connection error:', err);
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
              <h2 className="text-lg font-semibold text-gray-900">Connect Email</h2>
              <p className="text-sm text-gray-600">Add your email account</p>
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

          {successMessage && (
            <div className="mb-4 p-3 bg-green-50 border border-green-200 rounded-md flex items-center gap-2">
              <CheckCircle className="h-4 w-4 text-green-500" />
              <span className="text-sm text-green-700">{successMessage}</span>
            </div>
          )}

          {/* Provider Selection (if authenticated) */}
          {connectionMode === 'select' && isAuthenticated && (
            <div className="space-y-4">
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <p className="text-sm text-blue-900 font-medium">
                  Connected as: <span className="font-bold">{user?.email}</span>
                </p>
                <p className="text-xs text-blue-700 mt-2">
                  Select a provider to connect your email account
                </p>
              </div>

              <div className="space-y-3">
                {/* Gmail OAuth */}
                <button
                  onClick={() => handleOAuthConnect('gmail')}
                  disabled={loading}
                  className="w-full p-4 border-2 border-red-200 rounded-lg hover:bg-red-50 hover:border-red-400 transition-all disabled:opacity-50 flex items-center gap-3"
                >
                  <Mail className="h-6 w-6 text-red-600" />
                  <div className="text-left">
                    <p className="font-medium text-red-700">Gmail</p>
                    <p className="text-xs text-red-600">Connect with Google Account</p>
                  </div>
                </button>

                {/* Outlook OAuth */}
                <button
                  onClick={() => handleOAuthConnect('outlook')}
                  disabled={loading}
                  className="w-full p-4 border-2 border-blue-200 rounded-lg hover:bg-blue-50 hover:border-blue-400 transition-all disabled:opacity-50 flex items-center gap-3"
                >
                  <Mail className="h-6 w-6 text-blue-600" />
                  <div className="text-left">
                    <p className="font-medium text-blue-700">Outlook</p>
                    <p className="text-xs text-blue-600">Connect with Microsoft Account</p>
                  </div>
                </button>

                {/* Yahoo (manual friendly) */}
                <button
                  onClick={() => handleYahooConnect()}
                  disabled={loading}
                  className="w-full p-4 border-2 border-purple-200 rounded-lg hover:bg-purple-50 hover:border-purple-400 transition-all disabled:opacity-50 flex items-center gap-3"
                >
                  <Mail className="h-6 w-6 text-purple-600" />
                  <div className="text-left">
                    <p className="font-medium text-purple-700">Yahoo</p>
                    <p className="text-xs text-purple-600">Connect with Yahoo (App Password recommended)</p>
                  </div>
                </button>

                {/* Manual Connection */}
                <button
                  onClick={() => { setSelectedProvider(null); setConnectionMode('manual') }}
                  disabled={loading}
                  className="w-full p-4 border-2 border-gray-200 rounded-lg hover:bg-gray-50 hover:border-gray-400 transition-all disabled:opacity-50 flex items-center gap-3"
                >
                  <Key className="h-6 w-6 text-gray-600" />
                  <div className="text-left">
                    <p className="font-medium text-gray-700">Other Email Providers</p>
                    <p className="text-xs text-gray-600">Connect with Email + Password</p>
                  </div>
                </button>
              </div>

              <div className="flex gap-2 pt-4">
                <button
                  onClick={onClose}
                  className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}

          {/* Manual Connection Form */}
          {connectionMode === 'manual' && (
            <form onSubmit={handleManualConnect} className="space-y-4">
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <p className="text-sm text-blue-800">
                  ✅ Supports Gmail, Yahoo, Outlook, and other IMAP providers
                </p>
                <p className="text-sm text-blue-800 mt-2">
                  💡 <strong>For Gmail:</strong> Use an <a href="https://support.google.com/accounts/answer/185833" target="_blank" rel="noopener noreferrer" className="underline">App Password</a>
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Email Address
                </label>
                <input
                  type="email"
                  name="email"
                  value={formData.email}
                  onChange={handleChange}
                  placeholder={selectedProvider === 'yahoo' ? 'you@yahoo.com' : 'you@gmail.com'}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  disabled={loading}
                  required
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
                  placeholder="••••••••"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  disabled={loading}
                  required
                />
              </div>

              {/* Provider specific hint */}
              {selectedProvider === 'yahoo' && (
                <div className="p-3 bg-yellow-50 border border-yellow-200 rounded-md text-sm text-yellow-800">
                  Yahoo often requires an <strong>App Password</strong> for IMAP/SMTP access. See Yahoo account security settings to generate an app password.
                </div>
              )}

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Display Name (optional)
                </label>
                <input
                  type="text"
                  name="display_name"
                  value={formData.display_name}
                  onChange={handleChange}
                  placeholder="My Email"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  disabled={loading}
                />
              </div>

              <div className="flex gap-2 pt-4">
                {isAuthenticated && (
                  <button
                    type="button"
                    onClick={() => setConnectionMode('select')}
                    className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
                  >
                    Back
                  </button>
                )}
                <button
                  onClick={onClose}
                  className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={loading}
                  className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 font-medium"
                >
                  {loading ? (
                    <span className="flex items-center justify-center gap-2">
                      <Loader className="h-4 w-4 animate-spin" />
                      Connecting...
                    </span>
                  ) : (
                    'Connect'
                  )}
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
};

export default ConnectEmailModal;
