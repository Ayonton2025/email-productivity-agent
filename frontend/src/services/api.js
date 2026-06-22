import axios from 'axios';

// Determine API base URL
// In development, use relative URL to leverage Vite proxy
// In production, use the full URL from environment variable
const getApiBaseUrl = () => {
  // Check if we're in development mode
  const isDevelopment = import.meta.env.DEV || import.meta.env.MODE === 'development';
  
  if (isDevelopment) {
    // Use relative URL in development to leverage Vite proxy
    // The proxy will forward /api requests to the backend
    return '/api/v1';
  } else {
    // In production, use the full URL from environment variable
    return import.meta.env.VITE_API_URL || "http://127.0.0.1:8000/api/v1";
  }
};

const API_BASE_URL = getApiBaseUrl();

console.log('🚀 [API] Initializing with base URL:', API_BASE_URL);
console.log('🔍 [API] Environment:', {
  mode: import.meta.env.MODE,
  dev: import.meta.env.DEV,
  viteApiUrl: import.meta.env.VITE_API_URL
});

export { API_BASE_URL };

// Create axios instance with interceptors
const DEFAULT_REQUEST_TIMEOUT_MS = 60000;
const LONG_AI_TIMEOUT_MS = 300000;

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: DEFAULT_REQUEST_TIMEOUT_MS,
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
        
        // Do NOT force a redirect to /login when the user is on public pages
        // (landing, register, verify, password flows). Only redirect when the
        // user is on a protected area of the app.
        if (typeof window !== 'undefined') {
          const pathname = window.location.pathname || '/';
          const publicPaths = ['/', '/landing', '/register', '/verify-email', '/forgot-password', '/reset-password', '/oauth/callback'];
          const isPublicPage = publicPaths.some(p => pathname === p || pathname.startsWith(p + '/')) || pathname.startsWith('/register') || pathname.startsWith('/login');

          // If we're already on login or a public page, do not perform automatic redirect.
          if (!isPublicPage && !pathname.includes('/login')) {
            console.log('🔄 [API Response] Redirecting to login page (protected area)');
            setTimeout(() => {
              window.location.href = '/login';
            }, 1000);
          } else {
            console.log('ℹ️ [API Response] 401 received on public page — not redirecting to /login');
          }
        }
      }
    } else if (error.response?.status === 403) {
      console.log('🚫 [API Response] 403 Forbidden - Insufficient permissions');
    } else if (error.code === 'NETWORK_ERROR' || error.message === 'Network Error') {
      console.error('🌐 [API Response] Network error - Backend might be down');
    } else if (error.code === 'ECONNABORTED') {
      console.error('⏱️ [API Response] Request timed out - AI generation may still be running');
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


  generateReply: async (emailId) => {
    console.log('📧 [Email] Generating reply for email:', emailId);
    try {
      const response = await apiClient.post(`/emails/${emailId}/generate-reply`);
      console.log('✅ [Email] Reply generated successfully');
      return response;
    } catch (error) {
      console.error('❌ [Email] Generate reply failed:', error.response?.data);
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
  },

  // Email Accounts API (IMAP/SMTP based - no OAuth)
  testConnection: (credentials) => apiClient.post('/email-accounts/test-connection', credentials),
  connectAccount: (credentials) => apiClient.post('/email-accounts/connect', credentials),
  getAccounts: () => apiClient.get('/email-accounts/list'),
  getAccountsList: () => apiClient.get('/email-accounts'),
  disconnectAccount: (accountId) => apiClient.delete(`/email-accounts/${accountId}`),
  syncEmails: (accountId, options = {}) => apiClient.post(`/email-accounts/${accountId}/sync`, options),
  getInbox: (accountId, page = 0, perPage = 50) => apiClient.get(`/email-accounts/${accountId}/inbox`, {
    timeout: 120000,
    params: { page, per_page: perPage }
  }),
  getEmailDetail: (accountId, emailId) => apiClient.get(`/email-accounts/${accountId}/email/${emailId}`),
  sendEmail: (accountId, emailData) => apiClient.post(`/email-accounts/${accountId}/send`, emailData),
  getFolders: (accountId) => apiClient.get(`/email-accounts/${accountId}/folders`),
};

// Email Accounts API (Legacy OAuth - deprecated)
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
  assistWorkspace: (payload, timeoutMs = LONG_AI_TIMEOUT_MS) =>
    apiClient.post('/ai/assistant/assist', payload, { timeout: timeoutMs }),
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

// Auto-Reply API (rules, away mode, approval queue)
export const autoReplyApi = {
  getRules: () => apiClient.get('/auto-reply/'),
  createRule: (data) => apiClient.post('/auto-reply/', data),
  updateRule: (ruleId, data) => apiClient.put(`/auto-reply/${ruleId}`, data),
  deleteRule: (ruleId) => apiClient.delete(`/auto-reply/${ruleId}`),
  getAwayMode: () => apiClient.get('/auto-reply/away'),
  setAwayMode: (data) => apiClient.put('/auto-reply/away', data),
  getApprovalQueue: () => apiClient.get('/auto-reply/approval-queue'),
  approveDraft: (draftId) => apiClient.post(`/auto-reply/approval-queue/${draftId}/approve`),
  rejectDraft: (draftId) => apiClient.post(`/auto-reply/approval-queue/${draftId}/reject`),
};

// Phase 1: Daily Briefing API
export const briefingsApi = {
  getToday: () => apiClient.get('/briefings/today'),
  regenerateToday: () => apiClient.post('/briefings/regenerate'),
  getPreferences: () => apiClient.get('/briefings/preferences'),
  updatePreferences: (data) => apiClient.put('/briefings/preferences', data),
};

// Phase 1: Follow-up API
export const followupsApi = {
  getPolicy: () => apiClient.get('/followups/policy'),
  updatePolicy: (data) => apiClient.put('/followups/policy', data),
  schedule: (emailId, delayHours = null) =>
    apiClient.post(`/followups/${emailId}/schedule`, { delay_hours: delayHours }),
  disable: (emailId) => apiClient.post(`/followups/${emailId}/disable`),
  getQueue: (status = 'pending_approval', limit = 50) =>
    apiClient.get('/followups/queue', { params: { status, limit } }),
  approveQueueItem: (executionId) => apiClient.post(`/followups/queue/${executionId}/approve`),
  processDue: () => apiClient.post('/followups/process-due'),
};

// Phase 2: Hosted email API
export const hostedEmailApi = {
  checkAvailability: (localPart) => apiClient.get('/hosted-email/availability', { params: { local_part: localPart } }),
  provision: (payload) => apiClient.post('/hosted-email/provision', payload),
  signup: (payload) => apiClient.post('/hosted-email/signup', payload),
  getLimits: () => apiClient.get('/hosted-email/limits'),
};

// Shared inbox API
export const sharedInboxApi = {
  list: () => apiClient.get('/shared-inboxes/'),
  create: (payload) => apiClient.post('/shared-inboxes/', payload),
  listMembers: (inboxId) => apiClient.get(`/shared-inboxes/${inboxId}/members`),
  addMember: (inboxId, payload) => apiClient.post(`/shared-inboxes/${inboxId}/members`, payload),
  listEmails: (inboxId, params = {}) => apiClient.get(`/shared-inboxes/${inboxId}/emails`, { params }),
  addEmail: (inboxId, emailId) => apiClient.post(`/shared-inboxes/${inboxId}/emails/${emailId}`),
  updateEmail: (inboxId, emailId, payload) => apiClient.patch(`/shared-inboxes/${inboxId}/emails/${emailId}`, payload),
};

// Deliverability API
export const deliverabilityApi = {
  getScore: (days = 30) => apiClient.get('/deliverability/score', { params: { days } }),
};

// Executive AI API
export const executiveApi = {
  getSummary: () => apiClient.get('/executive/summary'),
  command: (payload) => apiClient.post('/executive/command', payload),
};

// Insights API
export const insightsApi = {
  getRisks: (severity) => apiClient.get('/insights/risks', { params: { severity } }),
  getOpportunities: (status) => apiClient.get('/insights/opportunities', { params: { status } }),
  getDeadlines: (daysAhead = 7) => apiClient.get('/insights/deadlines', { params: { days_ahead: daysAhead } }),
  getRelationships: (status) => apiClient.get('/insights/relationships', { params: { status } }),
  getAnalytics: (days = 30) => apiClient.get('/insights/analytics', { params: { days } }),
  getContactDetails: (contactId) => apiClient.get(`/insights/contacts/${contactId}`),
  getCompanyDetails: (companyId) => apiClient.get(`/insights/companies/${companyId}`),
};

// Workflows API
export const workflowsApi = {
  getWorkflows: () => apiClient.get('/workflows/'),
  getWorkflow: (workflowId) => apiClient.get(`/workflows/${workflowId}`),
  createWorkflow: (data) => apiClient.post('/workflows/', data),
  updateWorkflow: (workflowId, data) => apiClient.put(`/workflows/${workflowId}`, data),
  deleteWorkflow: (workflowId) => apiClient.delete(`/workflows/${workflowId}`),
  createStep: (workflowId, data) => apiClient.post(`/workflows/${workflowId}/steps`, data),
  updateStep: (stepId, data) => apiClient.put(`/workflows/steps/${stepId}`, data),
  deleteStep: (stepId) => apiClient.delete(`/workflows/steps/${stepId}`),
  getExecutions: (workflowId, limit = 20) => apiClient.get(`/workflows/${workflowId}/executions`, { params: { limit } }),
  executeWorkflow: (workflowId, emailId = null) => apiClient.post(`/workflows/${workflowId}/execute`, { email_id: emailId }),
};

// Agents API
export const agentsApi = {
  getAgents: (agentType = null) => apiClient.get('/agents/', { params: agentType ? { agent_type: agentType } : {} }),
  getAgent: (agentId) => apiClient.get(`/agents/${agentId}`),
  createAgent: (data) => apiClient.post('/agents/', data),
  updateAgent: (agentId, data) => apiClient.put(`/agents/${agentId}`, data),
  deleteAgent: (agentId) => apiClient.delete(`/agents/${agentId}`),
  getActivities: (agentId, limit = 50) => apiClient.get(`/agents/${agentId}/activities`, { params: { limit } }),
  getMemory: (agentId, memoryType = null, limit = 100) => apiClient.get(`/agents/${agentId}/memory`, { 
    params: { memory_type: memoryType, limit } 
  }),
};

// Campaigns API
export const campaignsApi = {
  getCampaigns: (status = null) => apiClient.get('/campaigns/', { params: status ? { status } : {} }),
  getCampaign: (campaignId) => apiClient.get(`/campaigns/${campaignId}`),
  createCampaign: (data) => apiClient.post('/campaigns/', data),
  updateCampaign: (campaignId, data) => apiClient.put(`/campaigns/${campaignId}`, data),
  deleteCampaign: (campaignId) => apiClient.delete(`/campaigns/${campaignId}`),
  getRecommendedSender: () => apiClient.get('/campaigns/recommended-sender'),
  createSequence: (campaignId, data) => apiClient.post(`/campaigns/${campaignId}/sequences`, data),
  bulkCreateLeads: (campaignId, leads) => {
    const normalizedLeads = Array.isArray(leads) ? leads : (leads?.leads || []);
    return apiClient.post(`/campaigns/${campaignId}/leads/bulk`, { leads: normalizedLeads });
  },
  getLeads: (campaignId, status = null, limit = 100, offset = 0) => apiClient.get(`/campaigns/${campaignId}/leads`, {
    params: { status, limit, offset }
  }),
  startCampaign: (campaignId) => apiClient.post(`/campaigns/${campaignId}/start`),
  pauseCampaign: (campaignId) => apiClient.post(`/campaigns/${campaignId}/pause`),
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
  checkAIProviders: (checkLive = false) =>
    apiClient.get(`/ai/health?check_live=${checkLive ? 'true' : 'false'}`, {
      timeout: checkLive ? LONG_AI_TIMEOUT_MS : DEFAULT_REQUEST_TIMEOUT_MS,
    }),
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
