import React, { useEffect, useRef } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';

/**
 * OAuthCallback Component
 * Handles OAuth provider callbacks and redirects
 * Used for Google, Microsoft, and other OAuth providers
 */
const OAuthCallback = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { login } = useAuth();
  const hasHandledCallbackRef = useRef(false);

  useEffect(() => {
    const handleCallback = async () => {
      try {
        if (hasHandledCallbackRef.current) {
          return;
        }
        hasHandledCallbackRef.current = true;
        // Get the authorization code from URL params
        const code = searchParams.get('code');
        const state = searchParams.get('state');
        const error = searchParams.get('error');

        if (error) {
          console.error('OAuth error:', error);
          navigate('/login?error=oauth_failed');
          return;
        }

        if (!code) {
          console.error('No authorization code received');
          navigate('/login?error=no_code');
          return;
        }

        // In development, always use relative /api/v1 to leverage Vite proxy
        // In production, use VITE_API_URL or fallback to absolute backend URL
        let apiBaseUrl;
        if (import.meta.env.DEV) {
          apiBaseUrl = '/api/v1'; // Use Vite proxy
        } else {
          apiBaseUrl = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api/v1';
          if (!apiBaseUrl.endsWith('/api/v1')) {
            apiBaseUrl = apiBaseUrl.replace(/\/+$/, '') + '/api/v1';
          }
        }

        const authToken = localStorage.getItem('auth_token');
        const redirectUri = import.meta.env.VITE_OAUTH_REDIRECT_URI || `${window.location.origin}/oauth/callback`;

        // If user is already logged in, treat this as "link Gmail" not "login".
        if (authToken) {
          const response = await fetch(`${apiBaseUrl}/email-accounts/gmail/code`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              Authorization: `Bearer ${authToken}`,
            },
            body: JSON.stringify({
              code,
              redirect_uri: redirectUri,
            }),
          });

          const data = await response.json();
          if (!response.ok) {
            throw new Error(data?.detail || 'Failed to link Gmail');
          }

          // After linking, send user directly to Inbox.
          navigate('/inbox', { replace: true });
          return;
        }

        // Otherwise, keep legacy behavior (OAuth login) as fallback.
        const response = await fetch(`${apiBaseUrl}/oauth/callback`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ code, state, provider: 'google' }),
        });

        if (!response.ok) {
          throw new Error('OAuth callback failed');
        }

        const data = await response.json();

        // Store token and redirect to inbox.
        if (data.access_token) {
          localStorage.setItem('auth_token', data.access_token);
          navigate('/inbox', { replace: true });
        } else {
          navigate('/login?error=no_token');
        }
      } catch (error) {
        console.error('OAuth callback error:', error);
        const existingToken = localStorage.getItem('auth_token');
        if (existingToken) {
          navigate('/inbox?error=oauth_link_failed', { replace: true });
        } else {
          navigate('/login?error=callback_error');
        }
      }
    };

    handleCallback();
  }, [searchParams, navigate, login]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-indigo-500 to-purple-600">
      <div className="loading-container">
        <div className="logo-loader">✉️</div>
        <div className="loading-spinner"></div>
        <div className="loading-text">Bylix Email</div>
        <div className="loading-subtext">Completing OAuth authentication...</div>
      </div>
    </div>
  );
};

export default OAuthCallback;
