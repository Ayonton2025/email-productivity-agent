import apiClient from './client'
import { logger } from '../../utils/logger'
export const authApi = {
  register: async (userData) => {
    logger.debug('📝 [Auth] Registering user:', {
      email: userData.email,
      fullName: userData.full_name,
    })

    // Make sure we're sending the correct data structure
    const registerData = {
      email: userData.email,
      password: userData.password,
      full_name: userData.full_name || userData.fullName,
    }

    logger.debug('📤 [Auth] Sending registration data:', registerData)

    try {
      // CORRECTED: Changed from '/auth/register' to '/register'
      const response = await apiClient.post('/register', registerData)
      logger.debug('✅ [Auth] Registration successful:', {
        userId: response.data.user_id,
        email: response.data.email,
        hasToken: !!response.data.access_token,
        message: response.data.message,
      })
      return response
    } catch (error) {
      logger.error('❌ [Auth] Registration failed:', {
        error: error.response?.data?.detail,
        status: error.response?.status,
        fullError: error.response?.data,
      })
      throw error
    }
  },

  login: async (credentials) => {
    logger.debug('🔑 [Auth] Logging in user:', { email: credentials.email })

    const loginData = {
      email: credentials.email,
      password: credentials.password,
    }

    try {
      // CORRECTED: Changed from '/auth/login' to '/login'
      const response = await apiClient.post('/login', loginData)
      logger.debug('✅ [Auth] Login successful:', {
        hasToken: !!response.data.access_token,
        tokenPreview: response.data.access_token ? `${response.data.access_token.substring(0, 20)}...` : 'None',
        userEmail: response.data.user?.email,
        userVerified: response.data.user?.is_verified,
      })

      // Validate response structure
      if (!response.data.access_token) {
        logger.error('❌ [Auth] Login response missing access_token!')
        throw new Error('No access token received from server')
      }

      if (!response.data.user) {
        logger.error('❌ [Auth] Login response missing user data!')
        throw new Error('No user data received from server')
      }

      return response
    } catch (error) {
      logger.error('❌ [Auth] Login failed:', {
        error: error.response?.data?.detail || error.message,
        status: error.response?.status,
        fullError: error.response?.data,
      })
      throw error
    }
  },

  logout: async () => {
    logger.debug('🚪 [Auth] Logging out')
    const tokenBefore = localStorage.getItem('auth_token')
    logger.debug('🔍 [Auth] Token before logout:', tokenBefore ? 'Present' : 'None')

    // Clear local storage first
    localStorage.removeItem('auth_token')
    localStorage.removeItem('user')

    try {
      // CORRECTED: Changed from '/auth/logout' to '/logout'
      const response = await apiClient.post('/logout')
      logger.debug('✅ [Auth] Backend logout successful')
      return response
    } catch (error) {
      logger.debug('⚠️ [Auth] Backend logout failed (may be expected):', error.message)
      // Still return success for local logout
      return { data: { message: 'Logged out locally' } }
    }
  },

  getCurrentUser: async () => {
    logger.debug('👤 [Auth] Getting current user')
    const token = localStorage.getItem('auth_token')
    logger.debug('🔍 [Auth] Using token:', token ? `${token.substring(0, 20)}...` : 'None')

    try {
      // CORRECTED: Changed from '/auth/me' to '/me'
      const response = await apiClient.get('/me')
      logger.debug('✅ [Auth] Current user fetched:', {
        email: response.data.email,
        id: response.data.id,
        verified: response.data.is_verified,
      })
      return response
    } catch (error) {
      logger.error('❌ [Auth] Get current user failed:', {
        error: error.response?.data?.detail,
        status: error.response?.status,
      })
      throw error
    }
  },

  refreshToken: async () => {
    logger.debug('🔄 [Auth] Refreshing token')
    try {
      // CORRECTED: Changed from '/auth/refresh' to '/refresh'
      const response = await apiClient.post('/refresh')
      logger.debug('✅ [Auth] Token refreshed successfully')
      return response
    } catch (error) {
      logger.error('❌ [Auth] Token refresh failed:', error.response?.data)
      throw error
    }
  },

  verifyEmail: async (data) => {
    logger.debug('📧 [Auth] Verifying email with token')
    try {
      // CORRECTED: Changed from '/auth/verify-email' to '/verify-email'
      const response = await apiClient.post('/verify-email', data)
      logger.debug('✅ [Auth] Email verification successful')
      return response
    } catch (error) {
      logger.error('❌ [Auth] Email verification failed:', error.response?.data)
      throw error
    }
  },

  forgotPassword: async (data) => {
    logger.debug('🔐 [Auth] Requesting password reset for:', data.email)
    try {
      // CORRECTED: Changed from '/auth/forgot-password' to '/forgot-password'
      const response = await apiClient.post('/forgot-password', data)
      logger.debug('✅ [Auth] Password reset request sent')
      return response
    } catch (error) {
      logger.error('❌ [Auth] Password reset request failed:', error.response?.data)
      throw error
    }
  },

  resetPassword: async (data) => {
    logger.debug('🔐 [Auth] Resetting password with token')
    try {
      // CORRECTED: Changed from '/auth/reset-password' to '/reset-password'
      const response = await apiClient.post('/reset-password', data)
      logger.debug('✅ [Auth] Password reset successful')
      return response
    } catch (error) {
      logger.error('❌ [Auth] Password reset failed:', error.response?.data)
      throw error
    }
  },
}
