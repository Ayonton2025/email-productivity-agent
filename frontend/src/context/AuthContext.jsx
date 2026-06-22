import React, { createContext, useState, useContext, useEffect } from 'react';
import { authApi, hostedEmailApi } from '../services/api';

const AuthContext = createContext();

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [token, setToken] = useState(null);

  // Check authentication on app start
  useEffect(() => {
    let completed = false;
    const watchdog = setTimeout(() => {
      if (!completed) {
        console.warn('⚠️ [AuthContext] Auth bootstrap watchdog triggered; forcing loading=false');
        setLoading(false);
      }
    }, 10000);

    (async () => {
      try {
        await checkAuth();
      } finally {
        completed = true;
        clearTimeout(watchdog);
      }
    })();

    return () => {
      completed = true;
      clearTimeout(watchdog);
    };
  }, []);

  const checkAuth = async () => {
    try {
      const storedToken = localStorage.getItem('auth_token');
      const storedUser = localStorage.getItem('user');
      
      console.log('🔍 [AuthContext] Checking authentication:');
      console.log('   - Token in localStorage:', storedToken ? `Present (${storedToken.substring(0, 20)}...)` : 'Not found');
      console.log('   - User in localStorage:', storedUser ? 'Present' : 'Not found');
      
      if (storedToken && storedUser) {
        let parsedStoredUser = null;
        try {
          parsedStoredUser = JSON.parse(storedUser);
        } catch (parseError) {
          console.error('❌ [AuthContext] Failed to parse stored user:', parseError);
          clearAuthData();
          return;
        }

        try {
          // Verify the token is still valid by calling the backend with timeout
          console.log('🔄 [AuthContext] Validating token with backend...');
          
          // Create a timeout promise
          const timeoutPromise = new Promise((_, reject) =>
            setTimeout(() => reject(new Error('Backend request timeout')), 5000)
          );
          
          // Race between the API call and timeout
          const response = await Promise.race([
            authApi.getCurrentUser(),
            timeoutPromise
          ]);
          
          console.log('✅ [AuthContext] Token is valid, user:', response.data.email);
          
          setUser(response.data);
          setToken(storedToken);
        } catch (error) {
          console.error('❌ [AuthContext] Token validation failed:', error.message);
          const isTransientTimeout =
            error?.message === 'Backend request timeout' ||
            error?.code === 'ECONNABORTED' ||
            String(error?.message || '').toLowerCase().includes('timeout');
          const isUnauthorized = error?.response?.status === 401;

          if (isTransientTimeout && parsedStoredUser) {
            // Keep existing local session if backend is temporarily slow/unreachable.
            console.warn('⚠️ [AuthContext] Backend validation timed out; preserving existing session');
            setUser(parsedStoredUser);
            setToken(storedToken);
          } else if (isUnauthorized) {
            clearAuthData();
          } else if (parsedStoredUser) {
            // Fail-open for non-auth transient errors to avoid forced logout loops.
            console.warn('⚠️ [AuthContext] Non-auth validation error; preserving local session');
            setUser(parsedStoredUser);
            setToken(storedToken);
          } else {
            clearAuthData();
          }
        }
      } else {
        console.log('❌ [AuthContext] No valid auth data found');
        clearAuthData();
      }
    } catch (error) {
      console.error('❌ [AuthContext] Auth check failed:', error);
      clearAuthData();
    } finally {
      setLoading(false);
    }
  };

  const clearAuthData = () => {
    localStorage.removeItem('auth_token');
    localStorage.removeItem('user');
    setUser(null);
    setToken(null);
  };

  const applyAuthSession = (accessToken, userData) => {
    if (!accessToken || !userData) return false;
    localStorage.setItem('auth_token', accessToken);
    localStorage.setItem('user', JSON.stringify(userData));
    setUser(userData);
    setToken(accessToken);
    return true;
  };

  const login = async (email, password) => {
    try {
      console.log('🔑 [AuthContext] Attempting login for:', email);
      const response = await authApi.login({ email, password });
      const { access_token, user: userData } = response.data;
      
      console.log('✅ [AuthContext] Login successful:');
      console.log('   - Token received:', access_token ? `Present (${access_token.substring(0, 20)}...)` : 'Missing!');
      console.log('   - User data:', userData);
      
      if (!access_token) {
        console.error('❌ [AuthContext] No access token in login response!');
        return { 
          success: false, 
          error: 'No access token received from server' 
        };
      }
      
      if (!userData) {
        console.error('❌ [AuthContext] No user data in login response!');
        return { 
          success: false, 
          error: 'No user data received from server' 
        };
      }
      
      // Store token and user data
      localStorage.setItem('auth_token', access_token);
      localStorage.setItem('user', JSON.stringify(userData));
      setUser(userData);
      setToken(access_token);
      
      console.log('💾 [AuthContext] Auth data stored in localStorage and state');
      console.log('🔍 [AuthContext] Current auth state - User:', !!userData, 'Token:', !!access_token);
      
      return { success: true, user: userData };
    } catch (error) {
      console.error('❌ [AuthContext] Login failed:', error);
      console.log('   - Error response:', error.response?.data);
      return { 
        success: false, 
        error: error.response?.data?.detail || 'Login failed' 
      };
    }
  };

  const register = async (userData) => {
    try {
      console.log('📝 [AuthContext] Attempting registration for:', userData.email);
      
      // Clear any existing auth data first
      clearAuthData();
      
      const response = await authApi.register(userData);
      
      console.log('✅ [AuthContext] Registration response received:', response.data);
      
      // Check if we got an access token for auto-login
      if (response.data.access_token && response.data.user) {
        const { access_token, user: newUser } = response.data;
        
        console.log('✅ [AuthContext] Auto-login after registration');
        console.log('🔍 [AuthContext] Token to store:', access_token ? `${access_token.substring(0, 20)}...` : 'None');
        console.log('🔍 [AuthContext] User to store:', newUser);
        
        // Store token and user data
        applyAuthSession(access_token, newUser);
        
        // Verify storage
        const storedToken = localStorage.getItem('auth_token');
        const storedUser = localStorage.getItem('user');
        console.log('🔍 [AuthContext] After storage - Token in localStorage:', !!storedToken);
        console.log('🔍 [AuthContext] After storage - User in localStorage:', !!storedUser);
        
        return { 
          success: true, 
          user: newUser, 
          autoLoggedIn: true,
          message: 'Registration successful! Welcome to Bylix Email.'
        };
      } else {
        // Registration successful but no auto-login
        console.log('⚠️ [AuthContext] Registration successful but no auto-login');
        return { 
          success: true, 
          user: null, 
          autoLoggedIn: false,
          message: response.data.message || 'Registration successful! Please check your email for verification.'
        };
      }
    } catch (error) {
      console.error('❌ [AuthContext] Registration failed:', error);
      console.log('   - Error response:', error.response?.data);
      return { 
        success: false, 
        error: error.response?.data?.detail || 'Registration failed' 
      };
    }
  };

  const registerHosted = async ({ local_part, full_name, password }) => {
    try {
      const response = await hostedEmailApi.signup({
        local_part,
        full_name: full_name || null,
        password: password || null,
      });
      const accessToken = response.data?.access_token;
      const userData = response.data?.user;
      if (!applyAuthSession(accessToken, userData)) {
        return { success: false, error: 'Hosted signup completed but no valid auth session was returned.' };
      }
      return {
        success: true,
        user: userData,
        autoLoggedIn: true,
        hostedAccount: response.data?.account,
        temporaryPassword: response.data?.temporary_password || null,
      };
    } catch (error) {
      return {
        success: false,
        error: error.response?.data?.detail || 'Hosted signup failed',
      };
    }
  };

  const verifyEmail = async (token) => {
    try {
      const response = await authApi.verifyEmail({ token });
      return { success: true, data: response.data };
    } catch (error) {
      return { 
        success: false, 
        error: error.response?.data?.detail || 'Email verification failed' 
      };
    }
  };

  const forgotPassword = async (email) => {
    try {
      const response = await authApi.forgotPassword({ email });
      return { success: true, data: response.data };
    } catch (error) {
      return { 
        success: false, 
        error: error.response?.data?.detail || 'Password reset request failed' 
      };
    }
  };

  const resetPassword = async (token, newPassword) => {
    try {
      const response = await authApi.resetPassword({ token, new_password: newPassword });
      return { success: true, data: response.data };
    } catch (error) {
      return { 
        success: false, 
        error: error.response?.data?.detail || 'Password reset failed' 
      };
    }
  };

  const logout = () => {
    console.log('🚪 [AuthContext] Logging out user');
    clearAuthData();
    
    // Optional: Call backend logout
    authApi.logout().catch(error => {
      console.log('⚠️ [AuthContext] Backend logout failed (may be expected):', error);
    });
  };

  const value = {
    user,
    token,
    loading,
    login,
    register,
    registerHosted,
    verifyEmail,
    forgotPassword,
    resetPassword,
    logout,
    checkAuth,
    isAuthenticated: !!user && !!token,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};
