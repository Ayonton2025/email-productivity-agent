import axios from 'axios';

// Make sure this environment variable is set correctly
const API_BASE_URL = import.meta.env.VITE_API_URL || 'https://sunny-recreation-production.up.railway.app/api/v1';

console.log('🚀 [API] Initializing with base URL:', API_BASE_URL);

// Create axios instance with interceptors
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 15000,
  withCredentials: false,
});

// Enhanced Request interceptor to add auth token with debugging
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('auth_token');
    
    console.log('🔐 [API Request]', {
      url: config.url,
      method: config.method?.toUpperCase(),
      tokenPresent: !!token,
      tokenPreview: token ? `${token.substring(0, 20)}...` : 'None'
    });
    
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
      console.log('✅ [API Request] Authorization header set');
    } else {
      console.log('⚠️ [API Request] No auth token available for request');
    }
    
    return config;
  },
  (error) => {
    console.error('❌ [API Request] Interceptor error:', error);
    return Promise.reject(error);
  }
);

// Enhanced Response interceptor with better debugging
apiClient.interceptors.response.use(
  (response) => {
    console.log('✅ [API Response] Success:', {
      status: response.status,
      url: response.config.url,
      method: response.config.method?.toUpperCase(),
      data: response.data ? 'Received' : 'No data'
    });
    return response;
  },
  (error) => {
    const errorDetails = {
      status: error.response?.status,
      url: error.config?.url,
      method: error.config?.method?.toUpperCase(),
      message: error.message,
      data: error.response?.data
    };
    
    console.error('❌ [API Response] Error:', errorDetails);
    
    // Handle specific error cases
    if (error.response?.status === 401) {
      console.log('🔄 [API Response] 401 Unauthorized - Token expired or invalid');
      
      // Clear auth data
      const currentToken = localStorage.getItem('auth_token');
      if (currentToken) {
        console.log('🗑️ [API Response] Clearing invalid token from storage');
        localStorage.removeItem('auth_token');
        localStorage.removeItem('user');
        
        // Only redirect if we're not already on login page and this is a browser environment
        if (typeof window !== 'undefined' && !window.location.pathname.includes('/login')) {
          console.log('🔄 [API Response] Redirecting to login page');
          setTimeout(() => {
            window.location.href = '/login';
          }, 1000);
        }
      }
    } else if (error.response?.status === 403) {
      console.log('🚫 [API Response] 403 Forbidden - Insufficient permissions');
    } else if (error.code === 'NETWORK_ERROR' || error.message === 'Network Error') {
      console.error('🌐 [API Response] Network error - Backend might be down');
    }
    
    return Promise.reject(error);
  }
);

// Enhanced Authentication API with comprehensive debugging - CORRECTED ENDPOINTS
export const authApi = {
  register: async (userData) => {
    console.log('📝 [Auth] Registering user:', { 
      email: userData.email, 
      fullName: userData.full_name 
    });
    
    // Make sure we're sending the correct data structure
    const registerData = {
      email: userData.email,
      password: userData.password,
      full_name: userData.full_name || userData.fullName
    };
    
    console.log('📤 [Auth] Sending registration data:', registerData);
    
    try {
      // CORRECTED: Changed from '/auth/register' to '/register'
      const response = await apiClient.post('/register', registerData);
      console.log('✅ [Auth] Registration successful:', {
        userId: response.data.user_id,
        email: response.data.email,
        hasToken: !!response.data.access_token,
        message: response.data.message
      });
      return response;
    } catch (error) {
      console.error('❌ [Auth] Registration failed:', {
        error: error.response?.data?.detail,
        status: error.response?.status,
        fullError: error.response?.data
      });
      throw error;
    }
  },
  
  login: async (credentials) => {
    console.log('🔑 [Auth] Logging in user:', { email: credentials.email });
    
    const loginData = {
      email: credentials.email,
      password: credentials.password
    };
    
    try {
      // CORRECTED: Changed from '/auth/login' to '/login'
      const response = await apiClient.post('/login', loginData);
      console.log('✅ [Auth] Login successful:', {
        hasToken: !!response.data.access_token,
        tokenPreview: response.data.access_token ? `${response.data.access_token.substring(0, 20)}...` : 'None',
        userEmail: response.data.user?.email,
        userVerified: response.data.user?.is_verified
      });
      
      // Validate response structure
      if (!response.data.access_token) {
        console.error('❌ [Auth] Login response missing access_token!');
        throw new Error('No access token received from server');
      }
      
      if (!response.data.user) {
        console.error('❌ [Auth] Login response missing user data!');
        throw new Error('No user data received from server');
      }
      
      return response;
    } catch (error) {
      console.error('❌ [Auth] Login failed:', {
        error: error.response?.data?.detail || error.message,
        status: error.response?.status,
        fullError: error.response?.data
      });
      throw error;
    }
  },
  
  logout: async () => {
    console.log('🚪 [Auth] Logging out');
    const tokenBefore = localStorage.getItem('auth_token');
    console.log('🔍 [Auth] Token before logout:', tokenBefore ? 'Present' : 'None');
    
    // Clear local storage first
    localStorage.removeItem('auth_token');
    localStorage.removeItem('user');
    
    try {
      // CORRECTED: Changed from '/auth/logout' to '/logout'
      const response = await apiClient.post('/logout');
      console.log('✅ [Auth] Backend logout successful');
      return response;
    } catch (error) {
      console.log('⚠️ [Auth] Backend logout failed (may be expected):', error.message);
      // Still return success for local logout
      return { data: { message: 'Logged out locally' } };
    }
  },
  
  getCurrentUser: async () => {
    console.log('👤 [Auth] Getting current user');
    const token = localStorage.getItem('auth_token');
    console.log('🔍 [Auth] Using token:', token ? `${token.substring(0, 20)}...` : 'None');
    
    try {
      // CORRECTED: Changed from '/auth/me' to '/me'
      const response = await apiClient.get('/me');
      console.log('✅ [Auth] Current user fetched:', {
        email: response.data.email,
        id: response.data.id,
        verified: response.data.is_verified
      });
      return response;
    } catch (error) {
      console.error('❌ [Auth] Get current user failed:', {
        error: error.response?.data?.detail,
        status: error.response?.status
      });
      throw error;
    }
  },
  
  refreshToken: async () => {
    console.log('🔄 [Auth] Refreshing token');
    try {
      // CORRECTED: Changed from '/auth/refresh' to '/refresh'
      const response = await apiClient.post('/refresh');
      console.log('✅ [Auth] Token refreshed successfully');
      return response;
    } catch (error) {
      console.error('❌ [Auth] Token refresh failed:', error.response?.data);
      throw error;
    }
  },
  
  verifyEmail: async (data) => {
    console.log('📧 [Auth] Verifying email with token');
    try {
      // CORRECTED: Changed from '/auth/verify-email' to '/verify-email'
      const response = await apiClient.post('/verify-email', data);
      console.log('✅ [Auth] Email verification successful');
      return response;
    } catch (error) {
      console.error('❌ [Auth] Email verification failed:', error.response?.data);
      throw error;
    }
  },
  
  forgotPassword: async (data) => {
    console.log('🔐 [Auth] Requesting password reset for:', data.email);
    try {
      // CORRECTED: Changed from '/auth/forgot-password' to '/forgot-password'
      const response = await apiClient.post('/forgot-password', data);
      console.log('✅ [Auth] Password reset request sent');
      return response;
    } catch (error) {
      console.error('❌ [Auth] Password reset request failed:', error.response?.data);
      throw error;
    }
  },
  
  resetPassword: async (data) => {
    console.log('🔐 [Auth] Resetting password with token');
    try {
      // CORRECTED: Changed from '/auth/reset-password' to '/reset-password'
      const response = await apiClient.post('/reset-password', data);
      console.log('✅ [Auth] Password reset successful');
      return response;
    } catch (error) {
      console.error('❌ [Auth] Password reset failed:', error.response?.data);
      throw error;
    }
  }
};

// Enhanced Email API with debugging
export const emailApi = {
  getUserInbox: async (filters = {}) => {
    console.log('📧 [Email] Fetching user inbox with filters:', filters);
    try {
      const response = await apiClient.get('/emails/my-inbox', { params: filters });
      console.log('✅ [Email] Inbox fetched successfully:', {
        emailsCount: response.data?.length || 0,
        hasEmails: !!response.data && response.data.length > 0
      });
      return response;
    } catch (error) {
      console.error('❌ [Email] Fetch inbox failed:', error.response?.data);
      throw error;
    }
  },
  
  getEmails: async (limit = 50, offset = 0) => {
    console.log('📧 [Email] Fetching emails:', { limit, offset });
    try {
      const response = await apiClient.get(`/emails?limit=${limit}&offset=${offset}`);
      console.log('✅ [Email] Emails fetched successfully');
      return response;
    } catch (error) {
      console.error('❌ [Email] Fetch emails failed:', error.response?.data);
      throw error;
    }
  },
  
  getEmail: async (emailId) => {
    console.log('📧 [Email] Fetching email:', emailId);
    try {
      const response = await apiClient.get(`/emails/${emailId}`);
      console.log('✅ [Email] Email fetched successfully');
      return response;
    } catch (error) {
      console.error('❌ [Email] Fetch email failed:', error.response?.data);
      throw error;
    }
  },
  
  updateEmailCategory: async (emailId, category) => {
    console.log('📧 [Email] Updating category:', { emailId, category });
    try {
      const response = await apiClient.put(`/emails/${emailId}/category`, { category });
      console.log('✅ [Email] Category updated successfully');
      return response;
    } catch (error) {
      console.error('❌ [Email] Update category failed:', error.response?.data);
      throw error;
    }
  },
  
  syncUserEmails: async () => {
    console.log('📧 [Email] Syncing user emails');
    try {
      const response = await apiClient.post('/emails/sync');
      console.log('✅ [Email] Email sync initiated');
      return response;
    } catch (error) {
      console.error('❌ [Email] Email sync failed:', error.response?.data);
      throw error;
    }
  },
  
  loadMockEmails: async () => {
    console.log('📧 [Email] Loading mock emails');
    try {
      const response = await apiClient.post('/emails/load-mock');
      console.log('✅ [Email] Mock emails loaded');
      return response;
    } catch (error) {
      console.error('❌ [Email] Load mock emails failed:', error.response?.data);
      throw error;
    }
  }
};

// Email Accounts API
export const emailAccountsApi = {
  connectGmail: (authData) => apiClient.post('/email-accounts/gmail', authData),
  connectOutlook: (authData) => apiClient.post('/email-accounts/outlook', authData),
  getEmailAccounts: () => apiClient.get('/email-accounts'),
  disconnectAccount: (accountId) => apiClient.delete(`/email-accounts/${accountId}`),
  syncAccount: (accountId) => apiClient.post(`/email-accounts/${accountId}/sync`),
  getAccount: (accountId) => apiClient.get(`/email-accounts/${accountId}`),
};

// AI Processing API
export const aiApi = {
  categorizeEmail: (emailId) => apiClient.post('/agent/process', { 
    email_id: emailId, 
    prompt_type: 'categorization' 
  }),
  summarizeEmail: (emailId) => apiClient.post('/agent/process', { 
    email_id: emailId, 
    prompt_type: 'summary' 
  }),
  generateReply: (emailId, options = {}) => 
    apiClient.post('/agent/process', { 
      email_id: emailId, 
      prompt_type: 'reply_draft',
      ...options 
    }),
  extractActions: (emailId) => apiClient.post('/agent/process', { 
    email_id: emailId, 
    prompt_type: 'action_extraction' 
  }),
};

// Prompt API
export const promptApi = {
  getPrompts: () => apiClient.get('/prompts'),
  getUserPrompts: () => apiClient.get('/prompts/my'),
  createPrompt: (promptData) => apiClient.post('/prompts', promptData),
  updatePrompt: (promptId, promptData) => 
    apiClient.put(`/prompts/${promptId}`, promptData),
  deletePrompt: (promptId) => apiClient.delete(`/prompts/${promptId}`),
};

// Agent API
export const agentApi = {
  processEmail: (requestData) => apiClient.post('/agent/process', requestData),
  chatWithAgent: (message) => apiClient.post('/agent/chat', { message }),
  getAgentStatus: () => apiClient.get('/agent/status'),
};

// Draft API
export const draftApi = {
  getDrafts: () => apiClient.get('/drafts'),
  createDraft: (draftData) => apiClient.post('/drafts', draftData),
  updateDraft: (draftId, draftData) => apiClient.put(`/drafts/${draftId}`, draftData),
  deleteDraft: (draftId) => apiClient.delete(`/drafts/${draftId}`),
};

// Analytics API
export const analyticsApi = {
  getStats: () => apiClient.get('/analytics/stats'),
  getProductivity: (period = 'week') => 
    apiClient.get('/analytics/productivity', { params: { period } }),
};

// Health check endpoints
export const healthApi = {
  checkAPI: () => apiClient.get('/health'),
  checkDatabase: () => apiClient.get('/health/db'),
  checkAI: () => apiClient.get('/health/ai'),
};

// Enhanced test connection to backend
export const testConnection = async () => {
  try {
    console.log('🔍 [Connection Test] Testing connection to:', API_BASE_URL);
    
    const healthResponse = await apiClient.get('/health');
    
    // Test token storage
    const token = localStorage.getItem('auth_token');
    console.log('🔍 [Connection Test] Auth token in storage:', token ? `Present (${token.substring(0, 20)}...)` : 'Missing');
    
    return { 
      success: true, 
      data: healthResponse.data,
      tokenPresent: !!token,
      message: 'Backend is running and accessible'
    };
  } catch (error) {
    console.error('❌ [Connection Test] Failed:', error);
    return { 
      success: false, 
      error: error.message,
      details: 'Backend might not be running or CORS issue'
    };
  }
};

// Token management utilities
export const tokenUtils = {
  getToken: () => {
    const token = localStorage.getItem('auth_token');
    console.log('🔍 [Token] Retrieved token:', token ? `${token.substring(0, 20)}...` : 'None');
    return token;
  },
  
  setToken: (token) => {
    console.log('💾 [Token] Storing token in localStorage:', token ? `${token.substring(0, 20)}...` : 'Empty token!');
    if (!token) {
      console.error('❌ [Token] Attempted to store empty token!');
      return;
    }
    localStorage.setItem('auth_token', token);
  },
  
  removeToken: () => {
    console.log('🗑️ [Token] Removing token from localStorage');
    localStorage.removeItem('auth_token');
    localStorage.removeItem('user');
  },
  
  isValid: () => {
    const token = localStorage.getItem('auth_token');
    const isValid = !!token;
    console.log('🔍 [Token] Validation check:', isValid ? 'Valid' : 'Invalid');
    return isValid;
  }
};

// WebSocket helper
export const createWebSocket = (clientId = 'default') => {
  const token = localStorage.getItem('auth_token');
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const baseUrl = import.meta.env.VITE_API_URL?.replace(/^https?/, protocol);
  const wsUrl = `${baseUrl}/ws/agent?client_id=${clientId}${token ? `&token=${token}` : ''}`;
  
  console.log('🔌 [WebSocket] Connecting to:', wsUrl);
  return new WebSocket(wsUrl);
};

// Connection status monitor
export const monitorConnection = () => {
  const checkInterval = setInterval(async () => {
    const status = await testConnection();
    if (!status.success) {
      console.warn('⚠️ [Monitor] Backend connection lost');
    }
  }, 30000);
  
  return () => clearInterval(checkInterval);
};

export default apiClient;
