import apiClient, { API_BASE_URL } from './client'
import { logger } from '../../utils/logger'
export const testConnection = async () => {
  try {
    logger.debug('🔍 [Connection Test] Testing connection to:', API_BASE_URL)
    const healthResponse = await apiClient.get('/health')
    // Test token storage
    const token = localStorage.getItem('auth_token')
    logger.debug('🔍 [Connection Test] Auth token in storage:', token ? 'Present' : 'Missing')
    return {
      success: true,
      data: healthResponse.data,
      tokenPresent: !!token,
      message: 'Backend is running and accessible',
    }
  } catch (error) {
    logger.error('❌ [Connection Test] Failed:', error)
    return {
      success: false,
      error: error.message,
      details: 'Backend might not be running or CORS issue',
    }
  }
}
