import axios from 'axios'
import { logger } from '../../utils/logger'

// Determine API base URL
// In development, use relative URL to leverage Vite proxy
// In production, use the full URL from environment variable
const getApiBaseUrl = () => {
  // Check if we're in development mode
  const isDevelopment = import.meta.env.DEV || import.meta.env.MODE === 'development'

  if (isDevelopment) {
    // Use relative URL in development to leverage Vite proxy
    // The proxy will forward /api requests to the backend
    return '/api/v1'
  } else {
    // In production, use the full URL from environment variable
    return import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api/v1'
  }
}

const API_BASE_URL = getApiBaseUrl()

logger.debug('🚀 [API] Initializing with base URL:', API_BASE_URL)
logger.debug('🔍 [API] Environment:', {
  mode: import.meta.env.MODE,
  dev: import.meta.env.DEV,
  viteApiUrl: import.meta.env.VITE_API_URL,
})

export { API_BASE_URL }

// Create axios instance with interceptors
export const DEFAULT_REQUEST_TIMEOUT_MS = 60000
export const LONG_AI_TIMEOUT_MS = 300000

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: DEFAULT_REQUEST_TIMEOUT_MS,
  withCredentials: false,
})

// Enhanced Request interceptor to add auth token with debugging
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('auth_token')

    logger.debug('🔐 [API Request]', {
      url: config.url,
      method: config.method?.toUpperCase(),
      tokenPresent: !!token,
    })

    if (token) {
      config.headers.Authorization = `Bearer ${token}`
      logger.debug('✅ [API Request] Authorization header set')
    } else {
      logger.debug('⚠️ [API Request] No auth token available for request')
    }

    return config
  },
  (error) => {
    logger.error('❌ [API Request] Interceptor error:', error)
    return Promise.reject(error)
  }
)

// Enhanced Response interceptor with better debugging
apiClient.interceptors.response.use(
  (response) => {
    logger.debug('✅ [API Response] Success:', {
      status: response.status,
      url: response.config.url,
      method: response.config.method?.toUpperCase(),
      data: response.data ? 'Received' : 'No data',
    })
    return response
  },
  (error) => {
    const errorDetails = {
      status: error.response?.status,
      url: error.config?.url,
      method: error.config?.method?.toUpperCase(),
      message: error.message,
      data: error.response?.data,
    }

    logger.error('❌ [API Response] Error:', errorDetails)

    // Handle specific error cases
    if (error.response?.status === 401) {
      logger.debug('🔄 [API Response] 401 Unauthorized - Token expired or invalid')

      // Clear auth data
      const currentToken = localStorage.getItem('auth_token')
      if (currentToken) {
        logger.debug('🗑️ [API Response] Clearing invalid token from storage')
        localStorage.removeItem('auth_token')
        localStorage.removeItem('user')

        // Do NOT force a redirect to /login when the user is on public pages
        // (landing, register, verify, password flows). Only redirect when the
        // user is on a protected area of the app.
        if (typeof window !== 'undefined') {
          const pathname = window.location.pathname || '/'
          const publicPaths = [
            '/',
            '/landing',
            '/register',
            '/verify-email',
            '/forgot-password',
            '/reset-password',
            '/oauth/callback',
          ]
          const isPublicPage =
            publicPaths.some((p) => pathname === p || pathname.startsWith(p + '/')) ||
            pathname.startsWith('/register') ||
            pathname.startsWith('/login')

          // If we're already on login or a public page, do not perform automatic redirect.
          if (!isPublicPage && !pathname.includes('/login')) {
            logger.debug('🔄 [API Response] Redirecting to login page (protected area)')
            setTimeout(() => {
              window.location.href = '/login'
            }, 1000)
          } else {
            logger.debug('ℹ️ [API Response] 401 received on public page — not redirecting to /login')
          }
        }
      }
    } else if (error.response?.status === 403) {
      logger.debug('🚫 [API Response] 403 Forbidden - Insufficient permissions')
    } else if (error.code === 'NETWORK_ERROR' || error.message === 'Network Error') {
      logger.error('🌐 [API Response] Network error - Backend might be down')
    } else if (error.code === 'ECONNABORTED') {
      logger.error('⏱️ [API Response] Request timed out - AI generation may still be running')
    }

    return Promise.reject(error)
  }
)

// Enhanced Authentication API with comprehensive debugging - CORRECTED ENDPOINTS

export default apiClient
