import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000/api/v1';

// Create axios instance with interceptors
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 15000,
  withCredentials: false, // CHANGED: Set to false for token-based auth (not cookie-based)
});

// Enhanced Request interceptor to add auth token with debugging
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('auth_token');
    console.log('🔐 [API Request] Adding token to request:', token ? `Yes (${token.substring(0, 20)}...)` : 'No token found');
    
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
      console.log('✅ [API Request] Authorization header set');
    } else {
      console.log('⚠️ [API Request] No auth token available');
    }
    
    console.log('📤 [API Request] Sending request to:', config.url);
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
    console.log('✅ [API Response] Success:', response.status, response.config.url);
    return response;
  },
  (error) => {
    console.error('❌ [API Response] Error:', {
      status: error.response?.status,
      url: error.config?.url,
      message: error.message,
      data: error.response?.data
    });
    
    if (error.response?.status === 401) {
      console.log('🔄 [API Response] Token expired or invalid, clearing local storage');
      localStorage.removeItem('auth_token');
      localStorage.removeItem('user');
      
      // Only redirect if we're not already on login page
      if (!window.location.pathname.includes('/login')) {
        console.log('🔄 [API Response] Redirecting to login page');
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

// Enhanced Authentication API with better error handling
export const authApi = {
  register: async (userData) => {
    console.log('📝 [Auth] Registering user:', userData.email);
    try {
      const response = await apiClient.post('/auth/register', userData);
      console.log('✅ [Auth] Registration successful');
      return response;
    } catch (error) {
      console.error('❌ [Auth] Registration failed:', error.response?.data);
      throw error;
    }
  },
  
  login: async (credentials) => {
    console.log('🔑 [Auth] Logging in user:', credentials.email);
    try {
      const response = await apiClient.post('/auth/login', credentials);
      console.log('✅ [Auth] Login successful');
      return response;
    } catch (error) {
      console.error('❌ [Auth] Login failed:', error.response?.data);
      throw error;
    }
  },
  
  logout: async () => {
    console.log('🚪 [Auth] Logging out');
    localStorage.removeItem('auth_token');
    localStorage.removeItem('user');
    try {
      const response = await apiClient.post('/auth/logout');
      console.log('✅ [Auth] Logout successful');
      return response;
    } catch (error) {
      console.error('❌ [Auth] Logout API call failed:', error);
      // Still proceed with local logout even if API call fails
      return { data: { message: 'Logged out locally' } };
    }
  },
  
  getCurrentUser: async () => {
    console.log('👤 [Auth] Getting current user');
    try {
      const response = await apiClient.get('/auth/me');
      console.log('✅ [Auth] Current user fetched successfully');
      return response;
    } catch (error) {
      console.error('❌ [Auth] Get current user failed:', error.response?.data);
      throw error;
    }
  },
  
  refreshToken: () => apiClient.post('/auth/refresh'),
  verifyEmail: (data) => apiClient.post('/auth/verify-email', data),
  forgotPassword: (data) => apiClient.post('/auth/forgot-password', data),
  resetPassword: (data) => apiClient.post('/auth/reset-password', data),
};

// Enhanced Email API with debugging
export const emailApi = {
  getUserInbox: async (filters = {}) => {
    console.log('📧 [Email] Fetching user inbox with filters:', filters);
    try {
      const response = await apiClient.get('/emails/my-inbox', { params: filters });
      console.log('✅ [Email] Inbox fetched successfully, emails count:', response.data?.length || 0);
      return response;
    } catch (error) {
      console.error('❌ [Email] Fetch inbox failed:', error.response?.data);
      throw error;
    }
  },
  
  getEmails: (limit = 50, offset = 0) => 
    apiClient.get(`/emails?limit=${limit}&offset=${offset}`),
  
  getEmail: (emailId) => apiClient.get(`/emails/${emailId}`),
  
  updateEmailCategory: (emailId, category) => 
    apiClient.put(`/emails/${emailId}/category`, { category }),
  
  syncUserEmails: () => apiClient.post('/emails/sync'),
  
  loadMockEmails: () => apiClient.post('/emails/load-mock'),
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
    console.log('🔍 [Connection Test] Auth token in storage:', token ? 'Present' : 'Missing');
    
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
  getToken: () => localStorage.getItem('auth_token'),
  
  setToken: (token) => {
    console.log('💾 [Token] Storing token in localStorage');
    localStorage.setItem('auth_token', token);
  },
  
  removeToken: () => {
    console.log('🗑️ [Token] Removing token from localStorage');
    localStorage.removeItem('auth_token');
    localStorage.removeItem('user');
  },
  
  isValid: () => {
    const token = localStorage.getItem('auth_token');
    return !!token; // Simple check - in production, you might decode and check expiration
  }
};

// WebSocket helper
export const createWebSocket = (clientId = 'default') => {
  const token = localStorage.getItem('auth_token');
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl = `${protocol}//localhost:8000/api/v1/ws/agent?client_id=${clientId}${token ? `&token=${token}` : ''}`;
  
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