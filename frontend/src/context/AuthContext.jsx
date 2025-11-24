import React, { createContext, useState, useContext, useEffect } from 'react';
import { authApi } from '../services/api';

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
    checkAuth();
  }, []);

  const checkAuth = async () => {
    try {
      const storedToken = localStorage.getItem('auth_token');
      const storedUser = localStorage.getItem('user');
      
      console.log('🔍 [AuthContext] Checking authentication:');
      console.log('   - Token in localStorage:', storedToken ? `Present (${storedToken.substring(0, 20)}...)` : 'Not found');
      console.log('   - User in localStorage:', storedUser ? 'Present' : 'Not found');
      
      if (storedToken && storedUser) {
        try {
          // Verify the token is still valid by calling the backend
          console.log('🔄 [AuthContext] Validating token with backend...');
          const response = await authApi.getCurrentUser();
          console.log('✅ [AuthContext] Token is valid, user:', response.data.email);
          
          setUser(response.data);
          setToken(storedToken);
        } catch (error) {
          console.error('❌ [AuthContext] Token validation failed:', error);
          // Token is invalid, clear everything
          clearAuthData();
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
        localStorage.setItem('auth_token', access_token);
        localStorage.setItem('user', JSON.stringify(newUser));
        setUser(newUser);
        setToken(access_token);
        
        // Verify storage
        const storedToken = localStorage.getItem('auth_token');
        const storedUser = localStorage.getItem('user');
        console.log('🔍 [AuthContext] After storage - Token in localStorage:', !!storedToken);
        console.log('🔍 [AuthContext] After storage - User in localStorage:', !!storedUser);
        
        return { 
          success: true, 
          user: newUser, 
          autoLoggedIn: true,
          message: 'Registration successful! Welcome to InboxAI.'
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
