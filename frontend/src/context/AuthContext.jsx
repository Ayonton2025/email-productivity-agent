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

  // Check authentication on app start
  useEffect(() => {
    checkAuth();
  }, []);

  const checkAuth = async () => {
    try {
      const token = localStorage.getItem('auth_token');
      console.log('🔍 [AuthContext] Checking authentication, token present:', !!token);
      
      if (token) {
        const response = await authApi.getCurrentUser();
        console.log('✅ [AuthContext] User authenticated:', response.data.email);
        setUser(response.data);
      } else {
        console.log('❌ [AuthContext] No token found');
      }
    } catch (error) {
      console.error('❌ [AuthContext] Auth check failed:', error);
      // Don't call logout here to avoid redirect loops
      localStorage.removeItem('auth_token');
      localStorage.removeItem('user');
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  const login = async (email, password) => {
    try {
      console.log('🔑 [AuthContext] Attempting login for:', email);
      const response = await authApi.login({ email, password });
      const { access_token, user: userData } = response.data;
      
      console.log('✅ [AuthContext] Login successful, storing token and user data');
      
      // Store token and user data
      localStorage.setItem('auth_token', access_token);
      localStorage.setItem('user', JSON.stringify(userData));
      setUser(userData);
      
      return { success: true, user: userData };
    } catch (error) {
      console.error('❌ [AuthContext] Login failed:', error);
      return { 
        success: false, 
        error: error.response?.data?.detail || 'Login failed' 
      };
    }
  };

  const register = async (userData) => {
    try {
      console.log('📝 [AuthContext] Attempting registration for:', userData.email);
      const response = await authApi.register(userData);
      const { access_token, user: newUser } = response.data;
      
      console.log('✅ [AuthContext] Registration successful, storing token and user data');
      
      // Store token and user data
      localStorage.setItem('auth_token', access_token);
      localStorage.setItem('user', JSON.stringify(newUser));
      setUser(newUser);
      
      return { success: true, user: newUser };
    } catch (error) {
      console.error('❌ [AuthContext] Registration failed:', error);
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
    localStorage.removeItem('auth_token');
    localStorage.removeItem('user');
    setUser(null);
    // Optional: Call backend logout
    authApi.logout().catch(error => {
      console.log('⚠️ [AuthContext] Backend logout failed (expected for in-memory storage):', error);
    });
  };

  const value = {
    user,
    loading,
    login,
    register,
    verifyEmail,
    forgotPassword,
    resetPassword,
    logout,
    checkAuth,
    isAuthenticated: !!user,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};